#!/usr/bin/env python3
# ============================================================
# Plugin: Bildbehandling - resize, thumbnails, EXIF
# ============================================================
# FIL:       plugins/image_processor.py
# PLATS:     plugins/ (ftp_gallery_uploader/plugins/image_processor.py)
# Syfte:     Bearbeta bilder - respekteringsordning, stora bilder,
#            EXIF-rotation. HUVUDLOST plugin (ingen flik) -
#            "anpassad text" = strukturerade loggmeddelanden (E5).
# PLUGIN_NAME: "Bildbehandling"
# PRIORITY:  20
# VERSION:   2.3.0
# AUTHOR:    Rickard Längkvist
# COPYRIGHT: Copyright (c) <år> Rickard Längkvist (dynamiskt år,
#            se COPYRIGHT-konstanten nedan)
#
# ÄNDRINGAR v2.2.0 → v2.3.0 (MINNE/SNABBHET/KOD-pass):
#   [E1]      load_settings/save_settings BORTTAGNA (~60 rader
#             duplikat) - config arvs fran base_plugin v1.4.1
#             load_config/save_config (atomisk + .bak-rotation +
#             korrupt-karantan + schema-meta). CONFIG_FILE kvar.
#   [E2]      _log()-hjalpare: pipeline-callback eller self.log -
#             EN kalla for alla meddelanden. Progress-% raknas nu
#             pa (index+1)/total (var index/total = 0% pa bild 1).
#   [E3]      MINNE: engangsnedskalning - thumbnailen gors fran den
#             redan nedskalade fullsize-bilden, inte fran originalet
#             (tva img.copy() pa jattebilder borttagna: ~3 stora
#             bitmaps samtidigt -> ~2 sma). EXIF-rotation fore
#             fargkonvertering (RGBA roteras nu ocksa korrekt).
#             progressive=True pa fullsize-JPEG.
#   [E4]      SNABBHET: (a) JPEG draft() redan vid inlasning nar
#             bilden ar >2x malet (tidigast bara vid >10000 px);
#             (b) parallell bearbetning med ThreadPoolExecutor
#             (1-3 workers efter CPU), ordning bevaras via index,
#             cancel_check pollas per slutford bild, sekventiell
#             fallback om poolen inte kan skapas.
#   [E5]      TEXT/DESIGN: _progress() saker wrapper, enhetliga
#             [OK]/[FEL]/[VARNING]/[AVBRUTEN]-prefix, slutsummering
#             med atgangstid + bilder/s.
#
# BEVARAT FRÅN v2.2.0:
#   Inga f-strings (B1), ingen print() - loggning via log-callback
#   safe_filename / create_title / _resolve_image_path / _to_rgb
#   load_image_safely: draft(), DecompressionBombError-hantering
#   execute: progress_callback + cancel_check, returnerar ALLTID
#   context: processed_images (samma nycklar) + temp_dir
#
# BEVARAT FRÅN v2.0.0:
#   ImageOps.exif_transpose for EXIF-rotation
#   Filnamn i header
#   Forbattrad safe_filename - hanterar svenska tecken
#   draft(), DecompressionBombError-hantering
#   temp_dir, processed_images
#
# KLASSER I DENNA FIL:
#   ImageProcessor(BasePlugin) - PRIORITY=20
#
# IMPORTER:
#   pathlib.Path
#   PIL: Image, ImageOps
#   tempfile, re, os, time
#   concurrent.futures: ThreadPoolExecutor, as_completed
#   datetime
#   .base_plugin: BasePlugin
#
# CONTEXT-NYCKLAR SOM LASES:
#   'gallery'            dict - images_path, thumbnail_size,
#                               fullsize_max, jpeg_quality, auto_rotate
#   'sorted_images'     [Path] - fran image_sorter (prio)
#   'progress_callback' funktion(value, msg) - valfritt
#   'cancel_check'      funktion() -> bool   - valfritt
#
# CONTEXT-NYCKLAR SOM SATTS:
#   'processed_images'  [dict] - lista med bearbetade bilder
#   'temp_dir'          str    - sokvag till temp-mapp
# ============================================================

from pathlib import Path
from PIL import Image, ImageOps
import tempfile
import re
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

from .base_plugin import BasePlugin

# === Oka PIL:s sakerhetsgrans for stora bilder ===
Image.MAX_IMAGE_PIXELS = 300_000_000  # 300 megapixels


class ImageProcessor(BasePlugin):
    """
    Bildbehandling - resize, thumbnails, EXIF-rotation.

    Respekterar sorteringsordning fran image_sorter.
    Hanterar extremt stora bilder via draft() och
    DecompressionBombError-skydd.
    Stoder progress_callback och cancel_check fran context.

    Anvander ALDRIG print() - all loggning via log-callback.

    v2.3.0:
    - E1 config via base_plugin (sjalvlakande, ingen duplikat)
    - E2 _log()/-progress(): en kalla for meddelanden, saker wrapper
    - E3 minne: engangsnedskalning, thumb ur fullsize, EXIF fore RGB
    - E4 snabbhet: draft() mot malet + parallella workers (1-3)
    - E5 text: enhetliga prefix + tid/bilder-s i summeringen
    """

    PLUGIN_NAME = "Bildbehandling"
    PRIORITY    = 20
    VERSION     = "2.3.0"
    AUTHOR      = "Rickard Längkvist"
    COPYRIGHT   = "Copyright (c) %d %s" % (datetime.now().year, "Rickard Längkvist")

    # Maximal storlek for inlasning (pixlar pa langsta sidan)
    MAX_DIMENSION = 10_000

    # Config-filnamn (under config/) - hanteras av base_plugin (E1)
    CONFIG_FILE = "gallery_settings.json"

    # Bildformat som stods
    IMAGE_FORMATS = {
        ".jpg", ".jpeg", ".png", ".gif",
        ".webp", ".bmp", ".tiff", ".tif", ".heic", ".heif",
    }

    # Parallell bearbetning (E4): max 3 workers, minst 4 bilder
    MAX_WORKERS = 3
    MIN_PARALLEL = 4

    # ==========================================================================
    # LOGG-/PROGRESS-HJALPARE (E2/E5)
    # ==========================================================================

    def _log(self, log_func, message):
        """
        Logga via pipeline-callback om sadan finns, annars self.log().
        EN kalla for alla meddelanden (E2). Kraschar aldrig.
        """
        if log_func:
            try:
                log_func(message)
                return
            except Exception:
                pass
        try:
            self.log(message)
        except Exception:
            pass

    def _progress(self, progress_cb, pct, msg):
        """Saker progress-callback-wrapper (E5). Kraschar aldrig."""
        if not progress_cb:
            return
        try:
            progress_cb(pct, msg)
        except Exception:
            pass

    # ==========================================================================
    # EXECUTE - PIPELINE-INGANG
    # ==========================================================================

    def execute(self, context, log=None):
        """
        Bearbeta bilder i pipeline.

        Steg:
          1. Las gallery-installningar fran context
          2. Hamta bildlista (sorterad ordning prioriteras)
          3. Skapa temp-mapp (thumbnails/ + images/)
          4. Processa varje bild: EXIF-rotation, resize, thumbnail
             - parallellt med ThreadPoolExecutor nar det lonar sig (E4)
          5. Satt context['processed_images'] och context['temp_dir']

        Stoder:
          context['progress_callback'](value, msg) - 0-100
          context['cancel_check']()                - bool

        Returnerar context (alltid).
        """
        gallery         = context.get("gallery", {})
        tray_status = context.get('_tray_status')
        progress_cb     = context.get("progress_callback")
        cancel_check    = context.get("cancel_check")
        images_path_str = gallery.get("images_path", "")

        if not images_path_str:
            self._log(log, "  [!] Ingen images_path i context - hoppar over")
            context["processed_images"] = []
            return context

        input_path = Path(images_path_str)
        if not input_path.exists():
            self._log(log, "  [!] Sokvag finns inte: %s" % input_path)
            context["processed_images"] = []
            return context

        # -- Hamta bildlista ------------------------------------------------
        images = self._get_image_list(context, input_path, log)
        if not images:
            self._log(log, "  [VARNING] Inga bilder hittades!")
            context["processed_images"] = []
            return context

        from .logo_watermark import validate as validate_watermark
        watermark = validate_watermark(gallery)

        # -- Skapa temp-mapp ------------------------------------------------
        temp_dir   = Path(tempfile.mkdtemp(prefix="gallery_"))
        thumbs_dir = temp_dir / "thumbnails"
        full_dir   = temp_dir / "images"
        thumbs_dir.mkdir(exist_ok=True)
        full_dir.mkdir(exist_ok=True)

        # -- Installningar --------------------------------------------------
        thumb_size   = gallery.get("thumbnail_size", (300, 300))
        fullsize_max = gallery.get("fullsize_max",   (1920, 1080))
        quality      = gallery.get("jpeg_quality",   85)
        auto_rotate  = gallery.get("auto_rotate",    True)

        total = len(images)
        cfg = {
            "thumbs_dir":   thumbs_dir,
            "full_dir":     full_dir,
            "thumb_size":   tuple(thumb_size) if thumb_size else None,
            "fullsize_max": tuple(fullsize_max) if fullsize_max else None,
            "quality":      quality,
            "auto_rotate":  auto_rotate,
            "tray_status": tray_status,
            "watermark": watermark,
        }

        if tray_status is not None:
            tray_status.stage('Bearbetar')
            tray_status.progress(0, total)
        self._log(log, "  Bearbetar %d bilder..." % total)
        t0 = time.time()

        # -- Bearbeta (parallellt eller sekventiellt, E4) ------------------
        workers = self._worker_count(total)
        if workers > 1:
            results = self._process_parallel(
                images, cfg, log, progress_cb, cancel_check,
            )
        else:
            results = self._process_sequential(
                images, cfg, log, progress_cb, cancel_check,
            )

        processed = [r for r in results if r]
        if tray_status is not None and len(processed) < total and not cfg.get('cancelled'):
            tray_status.issue()

        # Slutlig progress
        self._progress(
            progress_cb, 100,
            "Klart - %d/%d bearbetade" % (len(processed), total),
        )

        context["processed_images"] = processed
        context["temp_dir"]         = str(temp_dir)

        # E5: summering med tid + hastighet
        elapsed = time.time() - t0
        if elapsed > 0.001 and processed:
            self._log(
                log,
                "  [OK] %d/%d bilder bearbetade pa %.1f s (%.1f bilder/s)"
                % (len(processed), total, elapsed,
                   len(processed) / elapsed),
            )
        else:
            self._log(
                log, "  [OK] %d/%d bilder bearbetade"
                % (len(processed), total),
            )

        return context

    # ==========================================================================
    # BEARBETNING - SEKVENTIELL / PARALLELL (E4)
    # ==========================================================================

    def _worker_count(self, total):
        """
        Antal workers (E4).

        <4 bilder: sekventiellt (thread-overhead lonar sig inte).
        Annars: 1-3 efter CPU-antal.
        """
        if total < self.MIN_PARALLEL:
            return 1
        try:
            cpu = os.cpu_count() or 1
        except Exception:
            cpu = 1
        return max(1, min(self.MAX_WORKERS, cpu))

    def _process_sequential(self, images, cfg, log, progress_cb,
                            cancel_check):
        """Sekventiell bearbetning (faller ocksa tillbaka vid fel)."""
        results = []
        total   = len(images)
        for index, img_source in enumerate(images):
            if cancel_check and cancel_check():
                cfg['cancelled'] = True
                if cfg.get('tray_status') is not None:
                    cfg['tray_status'].cancelled()
                self._log(
                    log,
                    "  [AVBRUTEN] Bildbearbetning avbruten av anvandaren",
                )
                break

            # Progress-loggning var 10:e bild
            if index == 0 or (index + 1) % 10 == 0 or index + 1 == total:
                self._log(
                    log, "  [%d/%d]" % (index + 1, total),
                )

            # E2: progress pa (index+1)/total
            self._progress(
                progress_cb,
                int(((index + 1) / total) * 100),
                "%d/%d" % (index + 1, total),
            )

            results.append(self._process_one(img_source, index, cfg, log))
            if cfg.get('tray_status') is not None:
                cfg['tray_status'].progress(index + 1, total)
        return results

    def _process_parallel(self, images, cfg, log, progress_cb,
                          cancel_check):
        """
        Parallell bearbetning med ThreadPoolExecutor (E4).

        - Ordning bevaras: resultat lagras per index.
        - cancel_check pollas per slutford bild; aterstaende avbokas.
        - Per-bild-fel isoleras (results[i] = None).
        - Faller tillbaka till sekventiell om poolen inte kan skapas.
        """
        total   = len(images)
        results = [None] * total
        try:
            workers = self._worker_count(total)
        except Exception:
            workers = 1
        try:
            with ThreadPoolExecutor(
                max_workers=workers,
                thread_name_prefix="imgproc",
            ) as pool:
                futures = {}
                for i, src in enumerate(images):
                    fut = pool.submit(self._process_one, src, i, cfg, log)
                    futures[fut] = i

                done = 0
                aborted = False
                for fut in as_completed(futures):
                    if cancel_check and cancel_check():
                        cfg['cancelled'] = True
                        if cfg.get('tray_status') is not None:
                            cfg['tray_status'].cancelled()
                        aborted = True
                        for f in futures:
                            f.cancel()
                        self._log(
                            log,
                            "  [AVBRUTEN] Bildbearbetning avbruten "
                            "av anvandaren",
                        )
                        break
                    i = futures[fut]
                    try:
                        results[i] = fut.result()
                    except Exception as e:
                        self._log(log, "  [FEL] bild %d: %s" % (i + 1, e))
                    done += 1
                    if cfg.get('tray_status') is not None:
                        cfg['tray_status'].progress(done, total)
                    if done % 10 == 0 or done == total:
                        self._log(log, "  [%d/%d]" % (done, total))
                    self._progress(
                        progress_cb,
                        int((done / total) * 100),
                        "%d/%d" % (done, total),
                    )

                # Vid avbrott: samla in redan slutforda (aven de som
                # hann bli klara innan break)
                if aborted:
                    for fut, i in futures.items():
                        if fut.done() and not fut.cancelled():
                            try:
                                if results[i] is None:
                                    results[i] = fut.result()
                            except Exception:
                                pass
        except Exception as e:
            self._log(
                log,
                "  [VARNING] Parallell bearbetning misslyckades (%s) "
                "- kor sekventiellt" % e,
            )
            return self._process_sequential(
                images, cfg, log, progress_cb, cancel_check,
            )
        return results

    # ==========================================================================
    # BEARBETNING - EN BILD (E3/E4)
    # ==========================================================================

    def _process_one(self, img_source, index, cfg, log=None):
        """
        Bearbeta EN bild (kors i worker-trad vid parallell kornig, E4).

        Minnesvag (E3):
          ladda (draft mot malet) -> EXIF-rotation -> RGB ->
          nedskalning EN gang till fullsize -> thumbnail ur den
          nedskalade bilden. Inga img.copy() pa originalet.

        Returnerar dict (samma nycklar som forr) eller None vid fel.
        """
        img_path = self._resolve_image_path(img_source)
        if img_path is None or not img_path.exists():
            self._log(log, "  [VARNING] Saknas: %s" % img_source)
            return None

        try:
            safe_name = self.safe_filename(img_path.stem)
            out_name  = "%04d_%s.jpg" % (index + 1, safe_name)

            # Ladda - draft() direkt mot fullsize-malet (E4)
            img = self.load_image_safely(
                img_path, log, target=cfg["fullsize_max"],
            )
            if img is None:
                self._log(
                    log, "  [FEL] Kunde inte ladda: %s" % img_path.name,
                )
                return None

            try:
                # EXIF-rotation FORE fargkonvertering (E3-fix:
                # RGBA/P-bilders EXIF forsvann tidigare vid convert)
                if cfg["auto_rotate"]:
                    try:
                        img = ImageOps.exif_transpose(img)
                    except Exception:
                        pass

                # Konvertera till RGB
                img = self._to_rgb(img)

                # Fullsize: nedskalning EN gang (E3)
                if cfg["fullsize_max"]:
                    img.thumbnail(
                        cfg["fullsize_max"], Image.Resampling.LANCZOS,
                    )
                from .logo_watermark import apply_logo
                marked = apply_logo(img, cfg.get('watermark'))
                if marked is not img:
                    img.close()
                    img = marked
                full_path = cfg["full_dir"] / out_name
                img.save(
                    full_path, "JPEG",
                    quality=cfg["quality"], progressive=True,   # E3
                )

                # Thumbnail ur den redan nedskalade bilden (E3:
                # ingen img.copy() pa originalet langre)
                thumb = img.copy()
                try:
                    if cfg["thumb_size"]:
                        thumb.thumbnail(
                            cfg["thumb_size"], Image.Resampling.LANCZOS,
                        )
                    thumb_path = cfg["thumbs_dir"] / out_name
                    thumb.save(
                        thumb_path, "JPEG", quality=cfg["quality"],
                    )
                finally:
                    thumb.close()

                return {
                    "index":         index + 1,
                    "filename":      out_name,
                    "thumbnail":     str(thumb_path),
                    "fullsize":      str(full_path),
                    "title":         self.create_title(img_path.stem),
                    "original_path": str(img_path),
                    "original_name": img_path.name,
                }
            finally:
                img.close()

        except Exception as e:
            self._log(log, "  [FEL] %s: %s" % (img_path.name, e))
            return None

    # ==========================================================================
    # PRIVATA HJALPMETODER
    # ==========================================================================

    def _get_image_list(self, context, input_path, log=None):
        """
        Hamta bildlista i ratt ordning.

        Prioritetsordning:
          1. context['sorted_images']  - fran image_sorter
          2. Alfabetisk glob fran input_path
        """
        sorted_images = context.get("sorted_images", [])
        if sorted_images:
            self._log(
                log,
                "  Anvander sorterad ordning: %d bilder"
                % len(sorted_images),
            )
            return sorted_images

        images = sorted(
            [
                f for f in input_path.glob("*")
                if f.suffix.lower() in self.IMAGE_FORMATS
                and not f.name.startswith(".")
            ],
            key=lambda x: x.name.lower(),
        )
        self._log(
            log,
            "  Laser fran mapp (alfabetisk): %d bilder" % len(images),
        )
        return images

    def _resolve_image_path(self, img_source):
        """
        Konvertera img_source till Path.

        Hanterar:
          - Path      -> direkt
          - str       -> Path(str)
          - dict      -> Path(original_path) eller Path(fullsize)
          - Ovrigt    -> None
        """
        if isinstance(img_source, Path):
            return img_source
        if isinstance(img_source, str):
            return Path(img_source)
        if isinstance(img_source, dict):
            raw = img_source.get(
                "original_path",
                img_source.get("fullsize", ""),
            )
            return Path(raw) if raw else None
        return None

    def _to_rgb(self, img):
        """
        Konvertera PIL-bild till RGB.

        Hanterar RGBA, P (palette), LA (grayscale+alpha)
        och godtyckliga andra lagen.
        """
        if img.mode in ("RGBA", "LA"):
            bg = Image.new("RGB", img.size, (255, 255, 255))
            bg.paste(img, mask=img.split()[-1])
            return bg
        if img.mode == "P":
            converted = img.convert("RGBA")
            bg = Image.new("RGB", img.size, (255, 255, 255))
            bg.paste(converted, mask=converted.split()[-1])
            return bg
        if img.mode != "RGB":
            return img.convert("RGB")
        return img

    # ==========================================================================
    # SAKER BILDINLASNING
    # ==========================================================================

    def load_image_safely(self, img_path, log=None, target=None):
        """
        Ladda bild sakert.

        - Loggar om bilden ar >50 megapixels
        - E4: JPEG draft() direkt mot target (fullsize-malet) nar
          bilden ar >2x malet - avsevart snabbare decode
        - Skalar ner om langsta sidan > MAX_DIMENSION (10000px)
        - Hanterar DecompressionBombError med aggressiv nedskalning
        - Returnerar PIL.Image eller None vid fel
        - Anvander ALDRIG print()
        """
        try:
            img            = Image.open(img_path)
            width, height  = img.size
            pixels         = width * height

            if pixels > 50_000_000 and log:
                self._log(
                    log,
                    "    [INFO] Stor bild: %dx%d (%.1f MP)"
                    % (width, height, pixels / 1_000_000),
                )

            # -- E4: draft() mot malet for stora JPEG ------------------
            drafted = False
            if (img.format == "JPEG" and target
                    and max(width, height) > 2 * max(target)):
                try:
                    draft_box = (
                        max(1, int(target[0] * 2)),
                        max(1, int(target[1] * 2)),
                    )
                    img.draft("RGB", draft_box)
                    width, height = img.size
                    drafted = True
                    self._log(
                        log,
                        "    [INFO] draft() direkt: -> %dx%d"
                        % (width, height),
                    )
                except Exception:
                    pass

            max_dim = max(width, height)
            if max_dim > self.MAX_DIMENSION:
                scale      = self.MAX_DIMENSION / max_dim
                new_width  = int(width  * scale)
                new_height = int(height * scale)
                self._log(
                    log,
                    "    [INFO] Skalar ner: %dx%d -> %dx%d"
                    % (width, height, new_width, new_height),
                )
                if img.format == "JPEG" and not drafted:
                    img.draft("RGB", (new_width, new_height))
                    img.load()
                else:
                    img.load()
                    img = img.resize(
                        (new_width, new_height),
                        Image.Resampling.LANCZOS,
                    )
            else:
                img.load()

            return img

        except Image.DecompressionBombError:
            self._log(
                log,
                "    [VARNING] DecompressionBomb - "
                "forsoker med reducerad storlek",
            )
            old_limit = Image.MAX_IMAGE_PIXELS
            try:
                Image.MAX_IMAGE_PIXELS = 500_000_000  # 500MP temporart
                img                    = Image.open(img_path)
                width, height          = img.size
                scale                  = 4000 / max(width, height)
                new_size               = (
                    int(width * scale),
                    int(height * scale),
                )
                if img.format == "JPEG":
                    img.draft("RGB", new_size)
                    img.load()
                else:
                    img.load()
                    img = img.resize(
                        new_size, Image.Resampling.LANCZOS
                    )
                self._log(
                    log,
                    "    [OK] Laddade reducerad: %dx%d"
                    % (new_size[0], new_size[1]),
                )
                return img
            except Exception as e2:
                self._log(
                    log,
                    "    [FEL] Kunde inte ladda stor bild: %s" % e2,
                )
                return None
            finally:
                Image.MAX_IMAGE_PIXELS = old_limit

        except Exception as e:
            self._log(log, "    [FEL] Kunde inte ladda bild: %s" % e)
            return None

    # ==========================================================================
    # HJALPMETODER - FILNAMN OCH TITEL
    # ==========================================================================

    def safe_filename(self, name):
        """
        Skapa sakert filnamn.

        - Bevarar unicode-bokstaver (aao fungerar)
        - Ersatter specialtecken med underscore
        - Kollapsar multipla underscores
        - Max 40 tecken
        """
        safe = re.sub(r"[^\w\-]", "_", name, flags=re.UNICODE)
        safe = re.sub(r"_+", "_", safe)
        return safe[:40].strip("_") or "bild"

    def create_title(self, stem):
        """
        Skapa lasbar titel fran filnamns-stem.

        Tar bort ledande siffror/bindestreck/punkter,
        ersatter bindestreck/underscore med mellanslag,
        kapitaliserar.
        """
        title = re.sub(r"^[\d\-\._]+", "", stem)
        title = re.sub(r"[\-_]+", " ", title)
        return title.strip().title() or stem

    # ==========================================================================
    # JSON-INSTALLNINGAR (E1)
    # ==========================================================================
    # OBS: load_settings/save_settings fran v2.2.0 ar BORTTAGNA.
    # Config (gallery_settings.json) skots av base_plugin v1.4.1:
    #   self.load_config(self.CONFIG_FILE)   -> dict (sjalvlakande)
    #   self.save_config(self.CONFIG_FILE, data) -> bool (atomisk,
    #                                            .bak-rotation)
    # Atomiskt monster, .bak och korrupt-karantan finns dar - ingen
    # anledning att duplicera ~60 rader har.
    # ==========================================================================
