#!/usr/bin/env python3
# ============================================================
# Plugin: HTML-generator
# ============================================================
# FIL:       plugins/html_generator.py
# PLATS:     plugins/ (ftp_gallery_uploader/plugins/html_generator.py)
# Klass:     HtmlGenerator(HtmlTemplatesMixin, BasePlugin)
# PRIORITY:  30
# VERSION:   3.5.0
# AUTHOR:    Rickard Längkvist
# COPYRIGHT: Copyright (c) <år> Rickard Längkvist (dynamiskt år,
#            se COPYRIGHT-konstanten nedan)
#
# ÄNDRINGAR v3.5.0 → v3.5.1:
#   Mindre thumbnails: 6 kolumner default, lagre radhojd i radjamnt.
#
# ÄNDRINGAR v3.4.0 → v3.5.0 (export-design):
#   Mall+CSS: FTP-Galleri-tema, aurora-header, kicker, lyftta kort,
#   filmisk video, glas-lightbox. Logik oforandrad.
#
# ÄNDRINGAR v3.3.1 → v3.4.0 (FS-24 inkrementell HTML):
#   [FS-24]   Omgenerering av samma mapp: _safe_copy hoppar over
#             oforandrade image/+thumb/ (storlek+mtime). Efter kopiering
#             raderas overblivna bilder/thumbs som inte langre finns i
#             kallan (anvandaren tog bort dem). Ror inte video/pdf/HTML.
#
# ÄNDRINGAR v3.2.2 → v3.3.0 (videolänkar + thumbnails):
#   [V5]      Videolänkarna under titeln (video1..video7) tas bort.
#             PDF-länkar under titeln är kvar. Videorna syns bara som
#             kort i videoremsan (galleriet).
#   [V6]      Videokort får riktiga thumbnails: en JPEG-ruta (1 s in)
#             via ffmpeg eller OpenCV. Saknas båda används <video>
#             med första bildrutan i webbläsaren som fallback.
#
# ÄNDRINGAR v3.2.1 → v3.2.2 (synlig versionsrad):
#   [B7]      execute() loggar "HTML-generator v3.2.2" forst, sa det
#             gar att se att ratt fil ar kopierad (AttributeError pa
#             render_template kom fran en aldre kopia pa D:\\).
#
# ÄNDRINGAR v3.2.0 → v3.2.1 (BUGFIX Generera HTML):
#   [B6]      render_template() ligger NU pa HtmlGenerator sjalv, inte
#             bara i mixinen. Aldre html_generator_templates.py utan K8
#             orsakade: 'HtmlGenerator' object has no attribute
#             'render_template' vid klick pa Generera HTML.
#
# ÄNDRINGAR v3.1.0 → v3.2.0 (L4: bildproportioner till mallen):
#   [L4]      _build_gallery_cards injicerar style="--ar:1.5" per kort
#             (bredd/höjd) så att mallarnas radjämnt-motor (L1) kan räkna
#             ut layouten FÖRE bilderna laddats - ingen reflow-flash.
#             Mätning: entry['width'/'height'] om de finns, annars PIL-
#             huvudläsning av minsta filen (thumb → full → original) med
#             EXIF-orientation beaktad (5-8 = sidled → w/h byts).
#   [L4b]     _image_ratio() cachar per sökväg och är helt fel-säker:
#             utan PIL eller vid trasig fil blir det 0.0 (ingen --ar) och
#             JS mäter naturalWidth/Height i efterhand istället.
#   [Q4]      Logg: "+ index.html (N bilder, M med känd proportion)".
#
# ÄNDRINGAR v3.0.0 → v3.1.0 (K8: render via mixinen):
#   [K8]      _generate_index_html/_generate_slideshow_html anropar nu
#             self.render_template(which, values, log) istallet for 20
#             kedjade .replace()-anrop. Resultatet ar byte-identiskt
#             (verifierat), men saknade varden loggas nu explicit.
#   [D13/14]  Mallarna v3.1.0 ger besokaren tema- och densitetsvaxlare,
#             delbara djuplankar (#bild-7 / #video-2) och delningsknapp.
#             Ingen andring av context-nycklar eller publik API.
#
# ÄNDRINGAR v2.9.0 → v3.0.0 (designlyft i mallarna - fyra filer):
#   [D0]      Mallarna (html_generator_templates.py v3.0.0) ar uppdelade i
#             html_generator_css.py (design-tokens/teman) och
#             html_generator_js.py (galleri/lightbox/slideshow). ALLA FYRA
#             filer hor ihop - ingen nar 1200-gransen (spec §20/KRAV 17).
#   [K4]      execute() anropar asset_warning(log): saknas css/js-filen
#             genereras en fungerande reservsida och felet loggas.
#   [D2]      theme="system" (det ui_settings skickar) renderade forut
#             ALLTID dark - nu blir sidan adaptiv (foljer besokarens OS).
#             Ovriga forandringar i denna fil: enbart VERSION.
#
# ÄNDRINGAR v2.8.0 → v2.9.0 (video→video-bläddring i genererad HTML):
#   [V1]      Video-remsa OVANFÖR bildgalleriet: videor visas som egna
#             klickbara kort med placeholder-play-thumbnail + synligt
#             namn, placerade före <main class="gallery"> i index.html.
#   [V2]      Åtskild lightbox-navigering: bilder och videor hålls i
#             separata listor (IMAGES respektive VIDEOS). När en video
#             är öppen går prev/next, piltangenter (←/→, a/d) och svep
#             video→video - aldrig in i bildgalleriet. Bild-bläddring
#             från bildkort är oförändrad.
#   [V3]      _build_js_media ersätts av _build_js_images + _build_js_videos
#             + _build_video_strip (videor slutar dubbleras i bild-stegningen).
#   [V4]      Ursprungligen generiska play-ikoner; v3.3.0 ger riktiga
#             thumbnails (V6) med play-ikon som overlay.
#
# ÄNDRINGAR v2.7.0 → v2.8.0 (media-nav/mobil/kod/mime/cpu):
#   [M1]      Lightbox-stegning kombinerar BILDER + VIDEOER:
#             _build_js_media() bygger en MEDIA-array med typ/titel/source
#             (bilder + uppladdade video-länkar), sa hoger/vänster-knapp
#             och svep nu skiftar genom BADA. Video spelas inbäddat i
#             lightboxen (pausas/släcks vid byte till bild).
#   [M2]      Mobil-/skärm-stod: mallarna (html_generator_templates.py)
#             far förbättrade media-frågor + touch-vänliga knappar och
#             responsiv grid (2 kol -> 1 kol på smal mobil).
#   [Q1]      Loggning/felsökning: videor som läggs i lightbox-stegningen
#             loggas explicit (antal + förstagångsvalidering), sa en
#             olycklig (t.ex. saknad video-/undermapp) syns direkt i
#             loggen vid felsökning.
#   [Q2]      CPU/IO: _copy_images/_safe_copy hoppar över kopiering nar
#             målfilen redan finns med samma storlek+mtime (idempotent
#             regenerering -> ingen onödig disk-I/O vid upprepad generering).
#   [Q3]      Inga ändringar i public-API/signaturer (icke-brytande).
#
# ÄNDRINGAR v2.6.0 → v2.7.0 (krav från spec v4.5.0):
#   [B1]      Inga f-strings – ALL %-formatering (även
#             strängkonkateneringar i logganrop konverterade)
#   [B3]      AUTHOR + COPYRIGHT (dynamiskt år) + PLATS i header
#   [A9]      _write_file: komplett atomiskt monster
#             (mkstemp -> fdopen -> flush -> fsync -> os.replace)
#   [A10]     _get_output_format anvander helpers.get_config_path()
#             (fallback till projektrotens config/ om helpers saknas)
#
# BEVARAT FRÅN v2.6.0:
#   Uppdelad (BUG-023, > 1800 rader):
#     plugins/html_generator.py           = huvudfil (logik)
#     plugins/html_generator_templates.py = HtmlTemplatesMixin (mallar)
#     class HtmlGenerator(HtmlTemplatesMixin, BasePlugin)
#     OBS: html_generator_templates.py ska klistras in/uppdateras i
#     samma mapp innan vi gar vidare (regeln: alla filer i samma mapp).
#
#   Ansvar:
#   - Generera index.html med galleri + lightbox
#   - Generera slideshow.html med auto-play
#   - Kopiera bilder till output-mapp
#   - Kopiera + DÖPA OM PDF:er (pdf1, pdf2 ...) och videor (video1, video2 ...)
#   - Länka PDF under titeln; videor som kort i galleriet (V5)
#   - Stöd för standard + flat output-struktur
#   - 3 teman: dark / light / colorful
#   - Injicera custom CSS från custom_css_editor
#   - Injicera custom HTML header/footer
#   - Sätta files_to_upload för FTPUploader (inkl. pdf/ och video/)
#   - Tydliga thumbnails med hover-zoom
#   - Titel = mappnamn som fallback (BUG-019)
#
# VIKTIG DESIGN:
#   html_generator innehåller BAS-CSS (layout, grid, lightbox).
#   custom_css_editor tillför extra CSS/override via context.
#
#   Alla HTML-templates använder str.replace() istf f-strings
#   för att undvika Python 3.12+ f-string/brace-konflikter
#   med JavaScript-kod (löser tidigare KeyError 'bg_primary', BUG-016).
#
# CONTEXT SOM LÄSES:
#   'gallery'            dict
#   'processed_images'   [dict]
#   'sorted_images'      [Path]
#   'gallery_order'      bool
#   'custom_css'         str
#   'custom_html_header' str
#   'custom_html_footer' str
#   'output_format'      str
#   'pdf_files'          [dict|str|Path]   (eller 'gallery_pdfs')
#   'video_files'        [dict|str|Path]   (eller 'gallery_videos')
#
# CONTEXT SOM SÄTTS:
#   'html_output'        Path
#   'output_path'        str
#   'files_to_upload'    [str]
#   'processed_pdfs'     [dict]   (name, filename, relative_path, original_name)
#   'processed_videos'   [dict]   (name, filename, relative_path, original_name)
#
# IMPORTER:
#   os, json, shutil, re, tempfile, subprocess
#   pathlib.Path
#   datetime.datetime
#   .base_plugin: BasePlugin
#   .html_generator_templates: HtmlTemplatesMixin
#   helpers: get_config_path (valfritt, A10)
# ============================================================

import app_paths
import os
import json
import shutil
import re
import tempfile
import quiet_process as subprocess
from pathlib import Path
from datetime import datetime

from .base_plugin import BasePlugin
from .html_generator_templates import HtmlTemplatesMixin

# -- Helpers (valfritt – för config-sökväg, A10) ---------------
try:
    from helpers import get_config_path
    _HAS_HELPERS = True
except ImportError:
    _HAS_HELPERS = False


class HtmlGenerator(HtmlTemplatesMixin, BasePlugin):
    """
    Genererar HTML-galleri från processade eller sorterade bilder.

    Funktioner:
    - Responsivt galleri (2-8 kolumner)
    - Tydliga thumbnails med hover-zoom och bildnummer
    - Lightbox med tangentbord + touch-svep + preload
    - Slideshow med auto-play, hastighetsreglage, progress
    - Standard + flat output-struktur
    - 3 teman (dark / light / colorful)
    - Custom CSS + HTML header/footer
    - Automatisk kopiering och omdöpning av PDF:er (länkar under titeln)
      och videor (kort i galleriet med thumbnails)
    - FTP-fillista (inkl. pdf/ och video/)

    TEKNISK DETALJ:
      Alla HTML-templates använder str.replace() istf f-strings
      för att undvika Python 3.12+ f-string/brace-konflikter
      med JavaScript { } .
    """

    PLUGIN_NAME = "HTML-generator"
    PRIORITY    = 30
    VERSION     = "3.5.1"
    AUTHOR      = "Rickard Längkvist"
    COPYRIGHT   = "Copyright (c) %d %s" % (datetime.now().year, "Rickard Längkvist")

    IMAGE_FORMATS = {
        ".jpg", ".jpeg", ".png", ".gif",
        ".webp", ".bmp", ".tiff", ".tif", ".heic", ".heif",
    }

    PDF_FORMATS = {".pdf"}

    VIDEO_FORMATS = {
        ".mp4", ".webm", ".mov", ".qt", ".avi", ".mkv",
        ".m4v", ".ogv", ".wmv", ".flv", ".mpg", ".mpeg", ".3gp", ".ts",
    }

    #: Cache för bildproportioner (L4b) - {sökväg: bredd/höjd eller 0.0}
    _RATIO_CACHE = {}

    # ==========================================================================
    # PIPELINE
    # ==========================================================================
    def execute(self, context: dict, log=None) -> dict:
        if context.get('_export_transaction') is not None:
            return self._execute_unstaged(context, log)
        gallery = context.get('gallery', {})
        if not gallery.get('images_path'):
            return self._execute_unstaged(context, log)
        from export_transaction import ExportTransaction
        destination = gallery.get('output_path') or (Path(__file__).parent.parent / 'out' / Path(gallery['images_path']).name)
        transaction = ExportTransaction(destination)
        context['_export_transaction'] = transaction
        gallery['output_path'] = str(transaction.stage)
        try:
            result = self._execute_unstaged(context, log)
            transaction.publish(result)
            return result
        finally:
            context.pop('_export_transaction', None)
            if not transaction.committed:
                transaction.relocate(context, transaction.stage, transaction.destination)
                context['_gallery_generated'] = False
                transaction.abort()

    def _execute_unstaged(self, context: dict, log=None) -> dict:
        """
        Generera HTML-galleri.

        Steg:
          1. Läs galleri-inställningar
          2. Bestäm output-format (standard/flat)
          3. Bygg bildlista
          4. Kopiera bilder till output
          5. Kopiera + döp om PDF/Video (pdf1.., video1..)
          6. Generera index.html (med PDF & Video-länkar under titeln)
          7. Generera slideshow.html
          8. Sätt context-nycklar
        """
        context['_gallery_generated'] = False
        gallery = context.get("gallery", {})

        from delivery_options import validate as delivery_options
        delivery = delivery_options(gallery.get('delivery'))
        title         = gallery.get("title", "")
        description   = gallery.get("description", "")
        theme         = gallery.get("theme", "dark")
        try:
            columns = max(2, min(12, int(gallery.get("columns", 6) or 6)))
        except Exception:
            columns = 6
        images_path_s = gallery.get("images_path", "")
        output_path_s = gallery.get("output_path", "")

        from layout_designer import css as layout_css
        custom_css = layout_css(gallery.get('layout')) + '\n' + context.get("custom_css", "")
        custom_head   = context.get("custom_html_header", "")
        custom_footer = context.get("custom_html_footer", "")

        from .visitor_tools import TOOLS_HTML, TOOLS_JS
        custom_footer = custom_footer + TOOLS_HTML + '<script>' + TOOLS_JS + '</script>'

        output_format = self._get_output_format(context)

        if log:
            log("  HTML-generator v%s" % self.VERSION)

        # ── Validering ────────────────────────────────────────
        if not images_path_s:
            raise ValueError('Källmapp saknas. Välj en mapp med bilder eller originalvideor i Inställningar.')

        images_path = Path(images_path_s)

        # Titel = mappnamn som fallback (BUG-019)
        if not title:
            title = images_path.name or "Bildgalleri"

        if output_path_s:
            output_path = Path(output_path_s)
        else:
            output_path = (
                Path(__file__).parent.parent / "out" / images_path.name
            )

        context["output_path"] = str(output_path)

        if log:
            log("  Titel:  %s" % title)
            log("  Output: %s" % output_path)
            log("  Tema:   %s" % theme)
            log("  Format: %s" % output_format)

        # K4: varna (en gang) om css/js-hjalpmodulerna saknas pa disken
        try:
            self.asset_warning(log)
        except Exception:
            pass

        # ── Bildlista ─────────────────────────────────────────
        entries = self._get_image_entries(
            context, images_path, output_path, output_format, log,
        )

        if entries and gallery.get('watermark_enabled') is True and not context.get('processed_images'):
            raise ValueError('Logotyp som vattenstämpel kräver aktiverad bildprocessor. Generera om från källbilderna.')

        if not entries:
            video_inputs = self._collect_media(context, images_path, ['video_files', 'gallery_videos', 'video'], self.VIDEO_FORMATS)
            pdf_inputs = self._collect_media(context, images_path, ['pdf_files', 'gallery_pdfs', 'pdf'], self.PDF_FORMATS)
            if not video_inputs and not pdf_inputs:
                raise ValueError('Inga bilder, videor eller PDF-filer att generera ett galleri av.')
            if log:
                log('  Galleri utan stillbilder: %d videor, %d PDF-filer.' % (len(video_inputs), len(pdf_inputs)))

        # ── Output-mappar ─────────────────────────────────────
        output_path.mkdir(parents=True, exist_ok=True)
        if output_format == "standard":
            (output_path / "image").mkdir(parents=True, exist_ok=True)
            (output_path / "thumb").mkdir(parents=True, exist_ok=True)

        from app_icon import resolve_icon_file
        brand_icon = resolve_icon_file("icon_64.png", "icon.png")
        if brand_icon is not None:
            self._safe_copy(brand_icon, output_path / "app-icon.png")

        from .gallery_checks import cover_options
        cover_number, _ = cover_options(gallery)
        if entries and cover_number > len(entries):
            raise ValueError('Omslagsbildens nummer överstiger antalet bilder.')

        # ── Kopiera bilder ────────────────────────────────────
        self._copy_images(entries, output_path, output_format, log)

        from .web_image_assets import prepare_assets
        context['optimization_report'] = prepare_assets(
            entries, output_path, output_format, gallery, context, log)
        context['optimization_report_path'] = str(output_path / 'optimization-report.html')
        from .gallery_checks import prepare_cover
        cover_meta = prepare_cover(entries, output_path, gallery, title, description) if entries else ''
        custom_head = cover_meta + '\n' + custom_head
        if entries and not gallery.get('public_url') and log:
            log('  Omslag skapat; ange publik galleri-URL för bild vid länkdelning.')


        # ── PDF & Video: samla, kopiera, döp om, länka ────────
        pdf_sources = self._collect_media(
            context, images_path,
            ["pdf_files", "gallery_pdfs", "pdf"],
            self.PDF_FORMATS,
        )
        video_sources = self._collect_media(
            context, images_path,
            ["video_files", "gallery_videos", "video"],
            self.VIDEO_FORMATS,
        )

        pdf_links = self._copy_and_rename_media(
            pdf_sources, output_path, output_format,
            prefix="pdf", subdir="pdf", log=log,
        )
        self._media_progress_callback = context.get('progress_callback')
        self._media_cancel_check = lambda: bool(context.get('cancel_check') and context['cancel_check']())
        self._export_ffmpeg = getattr(context.get('_video_processor'), 'ffmpeg_path', None)
        video_links = self._copy_and_rename_media(
            video_sources, output_path, output_format,
            prefix="video", subdir="video", log=log,
        )

        self._make_video_thumbs(video_links, output_path, log)
        if delivery['qualities']:
            from video_renditions import create_renditions
            create_renditions(video_links, output_path, delivery['qualities'], self._find_ffmpeg(),
                              self._media_cancel_check, self._media_progress_callback)
        from gallery_delivery import quality_markup
        custom_footer += quality_markup(video_links)
        if delivery['panorama_auto']:
            from panorama_viewer import export_panoramas
            custom_footer += export_panoramas(entries, output_path)

        context["processed_pdfs"]   = pdf_links
        context["processed_videos"] = video_links

        if log:
            log("  Videor i lightbox-stegning: %d" % len(video_links))

        # ── Generera HTML ─────────────────────────────────────
        index_file = self._generate_index_html(
            entries=entries,
            output_path=output_path,
            title=title,
            description=description,
            theme=theme,
            columns=columns,
            output_format=output_format,
            custom_css=custom_css,
            custom_head=custom_head,
            custom_footer=custom_footer,
            pdf_files=pdf_links,
            video_files=video_links,
            log=log,
        )

        self._generate_slideshow_html(
            entries=entries,
            output_path=output_path,
            title=title,
            description=description,
            theme=theme,
            output_format=output_format,
            custom_css=custom_css,
            custom_head=custom_head,
            custom_footer=custom_footer,
            pdf_files=pdf_links,
            video_files=video_links,
            log=log,
        )

        from gallery_delivery import localized_pages
        localized_pages(output_path, delivery['languages'], title, description)

        # Portable editor metadata: only exported relative paths, no source paths.
        from .export_editor import write_manifest
        write_manifest(output_path, entries, dict(gallery, title=title,
                       theme=theme, columns=columns, description=description),
                       output_format, context)

        from .gallery_checks import check_links
        link_report = check_links(output_path)
        context['link_report'] = link_report
        context['link_report_path'] = str(output_path / 'link-report.html')
        if log:
            log('  Länkkontroll: %d referenser, %d fel.' % (link_report['checked'], len(link_report['errors'])))
        if not link_report['ok']:
            raise ValueError('Exportens länkkontroll hittade trasiga lokala länkar. Se link-report.html.')

        # ── Context ───────────────────────────────────────────
        context["html_output"]     = index_file
        context["files_to_upload"] = self._build_files_to_upload(
            output_path
        )

        if log:
            log("  [OK] HTML klar: %s" % index_file.name)
            n = len(context["files_to_upload"])
            log("  [OK] FTP-lista: %d filer" % n)

        try:
            rec = context.get("_settings")
            if rec is not None and hasattr(rec, "record_generated_gallery"):
                transaction = context.get('_export_transaction')
                rec.record_generated_gallery(
                    transaction.destination if transaction is not None else output_path, title,
                    len(entries), len(video_links),
                )
        except Exception:
            pass

        context['_gallery_generated'] = True
        if not context.get('_defer_learning'):
            from local_learning import record_export
            record_export(gallery, context['optimization_report'], log)
        return context

    # ==========================================================================
    # OUTPUT-FORMAT
    # ==========================================================================
    def _get_output_format(self, context: dict) -> str:
        """
        Hämta output-format.

        Prioritet:
          1. context['output_format']
          2. config/gallery_settings.json
          3. 'standard'
        """
        fmt = context.get("output_format")
        if fmt in ("standard", "flat"):
            return fmt

        try:
            if _HAS_HELPERS:
                cfg = get_config_path() / "gallery_settings.json"
            else:
                cfg = (
                    app_paths.config_dir() / "gallery_settings.json"
                )
            if cfg.exists():
                data = json.loads(cfg.read_text(encoding="utf-8"))
                cfg_fmt = data.get("output_format", "standard")
                if cfg_fmt in ("standard", "flat"):
                    return cfg_fmt
        except Exception:
            pass

        return "standard"

    # ==========================================================================
    # BILDLISTA
    # ==========================================================================
    def _get_image_entries(
        self, context, images_path, output_path,
        output_format, log=None,
    ) -> list:
        """
        Bygg intern bildlista.

        Prioritet:
          1. processed_images (från image_processor)
          2. sorted_images (från gallery_view/image_sorter)
          3. alfabetisk glob
        """
        processed = context.get("processed_images", [])
        if processed:
            entries = []
            for item in processed:
                idx = item.get("index", 0)
                # Genererat filnamn = löpnummer (1.jpg, 2.jpg, ...)
                src_name = item.get(
                    "filename",
                    item.get("original_name", ""),
                )
                ext = Path(src_name).suffix.lower() or ".jpg"
                entries.append({
                    "index":         idx,
                    "filename":      str(idx) + ext,
                    "title":         item.get("title", "Bild " + str(idx)),
                    "thumb_src":     item.get("thumbnail", ""),
                    "full_src":      item.get("fullsize", ""),
                    "original_path": item.get("original_path", ""),
                    "original_name": item.get(
                        "original_name",
                        item.get("filename", "")
                    ),
                })
            if log:
                log(
                    "  Kalla: processed_images (%d st)" % len(entries)
                )
            return entries

        sorted_images = context.get("sorted_images", [])
        if not sorted_images:
            sorted_images = sorted(
                [
                    f for f in images_path.glob("*")
                    if f.is_file()
                    and f.suffix.lower() in self.IMAGE_FORMATS
                    and not f.name.startswith(".")
                ],
                key=lambda x: x.name.lower(),
            )
            if log:
                log("  Kalla: glob (%d st)" % len(sorted_images))
        else:
            if log:
                log(
                    "  Kalla: sorted_images (%d st)"
                    % len(sorted_images)
                )

        entries = []
        for i, img_path in enumerate(sorted_images, 1):
            if isinstance(img_path, str):
                img_path = Path(img_path)
            if not isinstance(img_path, Path) or not img_path.exists():
                continue

            ext = img_path.suffix.lower() or ".jpg"
            # Genererat filnamn = löpnummer (1.jpg, 2.jpg, ...)
            filename = str(i) + ext

            entries.append({
                "index":         i,
                "filename":      filename,
                "title":         self._make_title(img_path.stem),
                "thumb_src":     str(img_path),
                "full_src":      str(img_path),
                "original_path": str(img_path),
                "original_name": img_path.name,
            })

        return entries

    # ==========================================================================
    # KOPIERA BILDER
    # ==========================================================================
    def _copy_images(
        self, entries, output_path, output_format, log=None,
    ) -> None:
        """
        Kopiera bilder till output.

        Standard: image/<fname> + thumb/<fname>
        Flat: full_NNN_namn.ext + thumb_NNN_namn.ext
        """
        copied = 0
        for entry in entries:
            idx       = entry["index"]
            filename  = entry["filename"]
            full_src  = Path(entry["full_src"])
            thumb_src = Path(entry["thumb_src"])

            if output_format == "standard":
                full_dst  = output_path / "image" / filename
                thumb_dst = output_path / "thumb" / filename
            else:
                # Flat-format: löpnummer (full_1.jpg, thumb_1.jpg, ...)
                ext = (
                    Path(filename).suffix
                    or Path(entry.get("original_name", "")).suffix
                    or ".jpg"
                )
                full_dst  = output_path / ("full_" + str(idx) + ext)
                thumb_dst = output_path / ("thumb_" + str(idx) + ext)

            self._safe_copy(full_src, full_dst)
            self._safe_copy(thumb_src, thumb_dst)

            entry["full_dst"]  = str(full_dst)
            entry["thumb_dst"] = str(thumb_dst)
            copied += 1

        if log:
            log("  Kopierade/uppdaterade %d bildposter" % copied)
        self._prune_stale_images(
            entries, output_path, output_format, log,
        )

    def _prune_stale_images(
        self, entries, output_path, output_format, log=None,
    ) -> None:
        """
        FS-24: ta bort bilder/thumbs i output som inte langre finns
        i kallan (anvandaren raderade dem). Ror INTE video/, pdf/ eller
        HTML. Gor ingenting om entries ar tom (skydd mot att toma mappen).
        """
        if not entries:
            return
        keep = set()
        for entry in entries:
            for key in ("filename", "full_dst", "thumb_dst"):
                val = entry.get(key) or ""
                if val:
                    keep.add(Path(val).name)
        if not keep:
            return

        if output_format == "standard":
            dirs = [output_path / "image", output_path / "thumb"]
        else:
            dirs = [output_path]

        removed = 0
        for folder in dirs:
            try:
                if not folder.is_dir():
                    continue
                for f in list(folder.iterdir()):
                    try:
                        if not f.is_file():
                            continue
                        if f.suffix.lower() not in self.IMAGE_FORMATS:
                            continue
                        if output_format != "standard":
                            n = f.name.lower()
                            if not (
                                n.startswith("full_")
                                or n.startswith("thumb_")
                            ):
                                continue
                        if f.name in keep:
                            continue
                        f.unlink()
                        removed += 1
                    except Exception:
                        continue
            except Exception:
                continue
        if log and removed:
            log(
                "  Tog bort %d overblivna bilder/thumbs (borttagna av anvandaren)"
                % removed,
            )

    @staticmethod
    def _should_copy(src: Path, dst: Path) -> bool:
        """
        True om mål saknas eller skiljer sig (storlek+mtime) fran källa.

        Gor regenerering idempotent: oforandrade bilder kopieras inte om
        (Q2 - sparar disk-I/O och CPU vid upprepad generering).
        """
        try:
            if not dst.exists():
                return True
            if not src.exists():
                return False
            s = src.stat()
            d = dst.stat()
            return s.st_size != d.st_size or s.st_mtime != d.st_mtime
        except Exception:
            return True

    def _safe_copy(self, src: Path, dst: Path) -> None:
        """
        Kopiera fil om den andrats (idempotent, Q2). Tyst om källa saknas.
        """
        try:
            if src.exists() and self._should_copy(src, dst):
                dst.parent.mkdir(parents=True, exist_ok=True)
                if src.resolve() != dst.resolve():
                    shutil.copy2(src, dst)
        except Exception:
            pass

    # ==========================================================================
    # BILDPROPORTIONER (L4) - för mallarnas radjämnt-layout
    # ==========================================================================
    def _image_ratio(self, path) -> float:
        """
        Läs bredd/höjd-förhållande ur en bildfil (endast huvudet läses).

        EXIF-orientation 5-8 betyder att bilden visas roterad 90 grader,
        därför byts w/h i de fallen (L4).

        Returnerar:
            float > 0, eller 0.0 om filen saknas/PIL saknas/fehl.
        """
        key = str(path or "")
        if not key:
            return 0.0
        cached = self._RATIO_CACHE.get(key)
        if cached is not None:
            return cached

        ratio = 0.0
        try:
            p = Path(key)
            if p.exists():
                from PIL import Image      # lazy: PIL är valfritt här
                with Image.open(p) as im:
                    w, h = im.size
                    orient = 0
                    try:
                        exif = im.getexif()
                        if exif:
                            orient = int(exif.get(274, 0) or 0)
                    except Exception:
                        orient = 0
                if orient in (5, 6, 7, 8):
                    w, h = h, w
                if w > 0 and h > 0:
                    ratio = w / float(h)
        except Exception:
            ratio = 0.0

        self._RATIO_CACHE[key] = ratio
        return ratio

    def _entry_ratio(self, entry: dict) -> float:
        """
        Bildpostens proportion (0.0 = okänd).

        Prioritet:
          1. entry['width'] / entry['height'] (om image_processor satt dem)
          2. minsta tillgängliga filen: thumb_dst -> full_dst ->
             original_path -> thumb_src -> thumbnail -> fullsize
             (PIL-huvudläsning, L4)
        """
        try:
            w = float(entry.get("width") or 0)
            h = float(entry.get("height") or 0)
            if w > 0 and h > 0:
                return w / h
        except Exception:
            pass

        for key in ("thumb_dst", "full_dst", "original_path", "thumb_src",
                    "thumbnail", "fullsize"):
            ratio = self._image_ratio(entry.get(key) or "")
            if ratio > 0:
                return ratio
        return 0.0

    # ==========================================================================
    # PDF / VIDEO – SAMLA, KOPIERA, DÖP OM
    # ==========================================================================
    def _collect_media(
        self, context, images_path, context_keys, formats,
    ) -> list:
        """
        Samla källfiler för en mediatyp (PDF eller video).

        Prioritet:
          1. context[context_keys[*]] (dict/str/Path accepteras)
          2. glob i bildmappen efter rätt filändelser

        Returnerar en lista av Path (källfiler), naturligt sorterade.
        """
        sources = []
        seen = set()

        for key in context_keys:
            items = context.get(key)
            if not items:
                continue
            for item in items:
                p = self._normalize_media_item(item)
                if p is None:
                    continue
                rp = str(p)
                if rp in seen:
                    continue
                if p.exists() and p.suffix.lower() in formats:
                    sources.append(p)
                    seen.add(rp)
            if sources:
                return self._natural_sort_paths(sources)

        if images_path and images_path.exists():
            for f in images_path.glob("*"):
                if (
                    f.is_file()
                    and f.suffix.lower() in formats
                    and not f.name.startswith(".")
                ):
                    rp = str(f)
                    if rp not in seen:
                        sources.append(f)
                        seen.add(rp)

        return self._natural_sort_paths(sources)

    def _normalize_media_item(self, item):
        """Normalisera en media-post (dict/str/Path) till en Path eller None."""
        try:
            if isinstance(item, Path):
                return item
            if isinstance(item, str):
                return Path(item)
            if isinstance(item, dict):
                for k in (
                    "original_path", "path", "source",
                    "src", "full_src", "file", "filename",
                ):
                    v = item.get(k)
                    if v:
                        return Path(v)
        except Exception:
            return None
        return None

    def _copy_and_rename_media(
        self, sources, output_path, output_format,
        prefix, subdir, log=None,
    ) -> list:
        """
        Kopiera och döp om mediafiler.

        Standard: <subdir>/<prefix><N>.<ext>   (ex: pdf/pdf1.pdf)
        Flat:     <prefix><N>.<ext>            (ex: video1.mp4)

        Returnerar lista av dict:
          { name, filename, relative_path, original_name }
        """
        links = []
        if not sources:
            return links

        if output_format == "standard":
            target_dir = output_path / subdir
            target_dir.mkdir(parents=True, exist_ok=True)
            rel_prefix = subdir + "/"
        else:
            target_dir = output_path
            rel_prefix = ""

        source_paths = {Path(source).resolve() for source in sources}
        for i, src in enumerate(sources, 1):
            ext = src.suffix.lower() or ""
            convert_video = prefix == 'video'
            new_name = prefix + str(i) + ('.mp4' if convert_video else ext)
            dst = target_dir / new_name
            if convert_video:
                # Reopening an export must never replace one of its input videos.
                while dst.resolve() in source_paths:
                    dst = dst.with_name(dst.stem + '_web.mp4')
                new_name = dst.name
                from media_support import video_to_web_mp4
                if log:
                    log('  Kontrollerar video – återanvänd, packa om eller konvertera: %s' % src.name)
                progress_callback = getattr(self, '_media_progress_callback', None)
                if callable(progress_callback):
                    progress_callback(None, 'Förbereder webbvideo %d/%d – %s' % (i, len(sources), src.name))
                cancel = getattr(self, '_media_cancel_check', None)
                if cancel is None:
                    video_to_web_mp4(src, dst, self._find_ffmpeg())
                else:
                    video_to_web_mp4(src, dst, self._find_ffmpeg(), cancelled=cancel)
            else:
                self._safe_copy(src, dst)
            links.append({
                "name":          prefix + str(i),
                "filename":      new_name,
                "relative_path": rel_prefix + new_name,
                "original_name": src.name,
                "original_path": str(src),
                "thumb_rel":     "",
            })

        if log:
            log("  %s: %d filer kopierade" % (prefix, len(links)))

        return links

    def _find_ffmpeg(self) -> str:
        """Hitta ffmpeg.exe (PATH, vanliga mappar, imageio-ffmpeg)."""
        selected = getattr(self, '_export_ffmpeg', None)
        if selected and Path(selected).is_file():
            return str(selected)
        cached = getattr(self, "_ffmpeg_exe", None)
        if cached is not None:
            return cached
        found = ""
        try:
            found = shutil.which("ffmpeg") or shutil.which("ffmpeg.exe") or ""
        except Exception:
            found = ""
        if not found:
            cands = [
                Path(os.environ.get("PROGRAMFILES", "")) / "ffmpeg/bin/ffmpeg.exe",
                Path(os.environ.get("PROGRAMFILES(X86)", "")) / "ffmpeg/bin/ffmpeg.exe",
                Path(os.environ.get("LOCALAPPDATA", "")) / "ffmpeg/bin/ffmpeg.exe",
                Path.home() / "ffmpeg/bin/ffmpeg.exe",
                Path("C:/ffmpeg/bin/ffmpeg.exe"),
                Path("/usr/local/bin/ffmpeg"),
                Path("/opt/homebrew/bin/ffmpeg"),
            ]
            for p in cands:
                try:
                    if p and p.is_file():
                        found = str(p)
                        break
                except Exception:
                    continue
        if not found:
            try:
                import imageio_ffmpeg
                found = imageio_ffmpeg.get_ffmpeg_exe() or ""
            except Exception:
                found = ""
        self._ffmpeg_exe = found or ""
        return self._ffmpeg_exe

    def _extract_video_thumb(self, src: Path, dst: Path) -> bool:
        """
        Spara en JPEG-ruta (~1 s in) fran videon.

        Ordning: ffmpeg -> OpenCV. Returnerar True om dst skrevs.
        """
        try:
            if not src or not src.exists():
                return False
            dst.parent.mkdir(parents=True, exist_ok=True)
            if dst.exists() and dst.stat().st_size > 200 and dst.stat().st_mtime_ns >= src.stat().st_mtime_ns:
                return True
        except Exception:
            return False

        ffmpeg = self._find_ffmpeg()
        if ffmpeg:
            flags = {}
            try:
                if os.name == "nt":
                    flags["creationflags"] = getattr(
                        subprocess, "CREATE_NO_WINDOW", 0
                    )
            except Exception:
                flags = {}
            for ss in ("1", "0"):
                try:
                    cmd = [
                        ffmpeg, "-hide_banner", "-loglevel", "error",
                        "-y", "-ss", ss, "-i", str(src),
                        "-frames:v", "1", "-vf", "scale=640:-2",
                        "-q:v", "4", str(dst),
                    ]
                    subprocess.run(
                        cmd, timeout=20, check=False,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        **flags
                    )
                    if dst.exists() and dst.stat().st_size > 200:
                        return True
                except Exception:
                    continue

        try:
            import cv2
            cap = cv2.VideoCapture(str(src))
            if not cap.isOpened():
                return False
            cap.set(cv2.CAP_PROP_POS_MSEC, 1000)
            ok, frame = cap.read()
            if not ok:
                cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                ok, frame = cap.read()
            cap.release()
            if not ok or frame is None:
                return False
            h, w = frame.shape[:2]
            if w > 640 and w > 0:
                nh = max(1, int(h * 640 / float(w)))
                frame = cv2.resize(frame, (640, nh))
            cv2.imwrite(str(dst), frame, [int(cv2.IMWRITE_JPEG_QUALITY), 85])
            return dst.exists() and dst.stat().st_size > 200
        except Exception:
            return False

    def _make_video_thumbs(self, video_links, output_path, log=None) -> None:
        """Skapa JPEG-thumbnail bredvid varje videofil (video1.jpg)."""
        if not video_links:
            return
        n_ok = 0
        for vid in video_links:
            rel = vid.get("relative_path", "")
            if not rel:
                continue
            copied = output_path / rel.replace("/", os.sep)
            dst = copied.with_suffix(".jpg")
            src = copied if copied.exists() else Path(vid.get("original_path") or "")
            cancel = getattr(self, '_media_cancel_check', None)
            if cancel and cancel():
                raise RuntimeError('Skapande av videominiatyrer avbrutet')
            # Always refresh from this export's actual video, never stale JPEGs.
            dst.unlink(missing_ok=True)
            from video_thumbnails import choose_video_thumbnail
            if choose_video_thumbnail(src, dst, self._find_ffmpeg(), cancel) or self._extract_video_thumb(src, dst):
                try:
                    vid["thumb_rel"] = str(
                        dst.relative_to(output_path)
                    ).replace("\\", "/")
                except Exception:
                    vid["thumb_rel"] = dst.name
                n_ok += 1
            else:
                vid["thumb_rel"] = ""
        if log:
            log("  Videothumbnails: %d/%d" % (n_ok, len(video_links)))
            if n_ok == 0 and video_links:
                log("  [i] Ingen ffmpeg/OpenCV - webblasaren visar forsta rutan")

    def _natural_sort_paths(self, paths: list) -> list:
        """Naturlig sortering av Path-lista (1, 2, 10 - inte 1, 10, 2)."""
        def key(p):
            return [
                int(t) if t.isdigit() else t.lower()
                for t in re.split(r"(\d+)", p.name)
            ]
        try:
            return sorted(paths, key=key)
        except Exception:
            return sorted(paths, key=lambda x: x.name.lower())

    # ==========================================================================
    # FTP-LISTA
    # ==========================================================================
    def _build_files_to_upload(self, output_path: Path) -> list:
        """Relativa sökvägar för FTP-plugin (inkl. image/, thumb/, pdf/, video/)."""
        if not output_path.exists():
            return []
        return [
            str(f.relative_to(output_path)).replace("\\", "/")
            for f in output_path.rglob("*")
            if f.is_file()
        ]

    # ==========================================================================
    # ATTACHMENT-LÄNKAR (PDF / VIDEO)
    # ==========================================================================
    def _build_attachment_links(
        self, pdf_files, video_files, wrapper_style="", link_style="",
    ) -> str:
        """
        Bygg HTML för länkfält under titeln (endast PDF, v3.3.0).

        video_files behålls i signaturen men ignoreras (videor är kort).
        """
        if not pdf_files:
            return ""

        style_attr = ' style="' + wrapper_style + '"' if wrapper_style else ""
        link_attr  = ' style="' + link_style + '"' if link_style else ""

        html = '  <div class="attachments"' + style_attr + '>\n'
        for pdf in pdf_files:
            href = self._esc(pdf.get("relative_path", ""))
            name = self._esc(pdf.get("name", "pdf"))
            html += (
                '    <a href="' + href + '" class="attachment-link" '
                + 'target="_blank"' + link_attr + '>&#128196; '
                + name + '</a>\n'
            )
        html += '  </div>\n'
        return html

    # ==========================================================================
    # index.html
    # ==========================================================================
    def render_template(self, which: str, values: dict, log=None) -> str:
        """
        Rendera mall via {{NYCKEL}} (K8).

        Mixinen har samma metod, men om html_generator_templates.py
        ar en aldre kopia UTAN render_template kraschade
        'Generera HTML' med AttributeError. Denna implementation
        pa HtmlGenerator sjalv gor att knappen alltid fungerar.
        """
        slide = str(which or "").lower().startswith("slide")
        attr = "_SLIDESHOW_TEMPLATE" if slide else "_INDEX_TEMPLATE"
        template = getattr(self, attr, "") or ""
        if not template:
            msg = (
                "HTML-mall saknas (%s). Kopiera html_generator_templates.py."
                % which
            )
            try:
                if log:
                    log("  [!] %s" % msg)
                else:
                    self.log("FEL", msg)
            except Exception:
                pass
            return (
                "<!DOCTYPE html><html><body><p>%s</p></body></html>" % msg
            )

        html = template
        for key, value in (values or {}).items():
            html = html.replace(
                "{{%s}}" % str(key).upper(),
                "" if value is None else str(value),
            )
        leftover = re.findall(r"\{\{[A-Z0-9_]+\}\}", html)
        if leftover:
            try:
                if log:
                    log(
                        "  [!] %s: platthallare utan varde: %s"
                        % (which, ", ".join(leftover))
                    )
            except Exception:
                pass
            for ph in leftover:
                html = html.replace(ph, "")
        return html

    def _generate_index_html(
        self, entries, output_path, title, description,
        theme, columns, output_format, custom_css,
        custom_head, custom_footer, pdf_files, video_files, log=None,
    ) -> Path:
        """Generera index.html med galleri + lightbox. PDF under titel, videor som kort."""
        cards_html = self._build_gallery_cards(entries, output_format)
        # v2.9.0: bilder och videor separeras. Videor visas som en remsa
        # i galleriet och bläddras video→video i lightboxen.
        images_js  = self._build_js_images(entries, output_format)
        videos_html = self._build_video_strip(video_files, output_format)
        videos_js  = self._build_js_videos(video_files)
        theme_css  = self._get_theme_css(theme)
        now        = datetime.now().strftime("%Y-%m-%d %H:%M")
        folder     = output_path.name
        n          = len(entries)

        desc_html = ""
        if description:
            desc_html = (
                '<p class="description">'
                + self._esc(description)
                + "</p>"
            )

        # PDF-länkar under titeln. Videor bara som kort (V5).
        attachments_html = self._build_attachment_links(pdf_files, [])

        c4 = str(min(columns, 6))
        c3 = str(min(columns, 4))

        # ── Render (K8: render_template i mixinen, INGEN f-string) ─
        html = self.render_template("index", {
            "VERSION":          self.VERSION,
            "META_DESC":        self._esc(description or title),
            "TITLE":            self._esc(title),
            "TITLE_RAW":        title,
            "CUSTOM_HEAD":      custom_head or "",
            "THEME_CSS":        theme_css,
            "COLUMNS":          str(columns),
            "COLUMNS_4":        c4,
            "COLUMNS_3":        c3,
            "CUSTOM_CSS":       custom_css or "",
            "DESC_HTML":        desc_html,
            "ATTACHMENTS_HTML": attachments_html,
            "IMG_COUNT":        str(n),
            "FOLDER":           folder,
            "NOW":              now,
            "CARDS_HTML":       cards_html,
            "VIDEOS_HTML":      videos_html,
            "IMAGES_JS":        images_js,
            "VIDEOS_JS":        videos_js,
            "CUSTOM_FOOTER":    custom_footer or "",
        }, log=log)

        index_path = output_path / "index.html"
        self._write_file(index_path, html)

        if log:
            known = sum(1 for e in entries if self._entry_ratio(e) > 0)
            log(
                "  + index.html (%d bilder, %d med kand proportion)"
                % (n, known)
            )

        return index_path

    # ── INDEX TEMPLATE ────────────────────────────────────────
    # Vanlig sträng - INTE f-string.
    # Python-variabler injiceras via .replace()
    # JavaScript-braces {} fungerar korrekt.
    # (Själva mallen ligger i html_generator_templates.py)

    # ==========================================================================
    # slideshow.html
    # ==========================================================================
    def _generate_slideshow_html(
        self, entries, output_path, title, description,
        theme, output_format, custom_css, custom_head,
        custom_footer, pdf_files, video_files, log=None,
    ) -> Path:
        """Generera slideshow.html."""
        slides_html = self._build_slides(entries, output_format)
        theme_css   = self._get_theme_css(theme)
        n           = len(entries)

        # PDF-länkar under titeln även på slideshow. Inga videolänkar (V5).
        attachments_html = self._build_attachment_links(
            pdf_files, [],
            wrapper_style="margin: 0; padding: 0;",
            link_style="padding: 4px 10px; font-size: 0.78rem;",
        )

        html = self.render_template("slideshow", {
            "TITLE":            self._esc(title),
            "CUSTOM_HEAD":      custom_head or "",
            "THEME_CSS":        theme_css,
            "CUSTOM_CSS":       custom_css or "",
            "ATTACHMENTS_HTML": attachments_html,
            "IMG_COUNT":        str(n),
            "SLIDES_HTML":      slides_html,
            "CUSTOM_FOOTER":    custom_footer or "",
        }, log=log)

        ss_path = output_path / "slideshow.html"
        self._write_file(ss_path, html)

        if log:
            log("  + slideshow.html (%d bilder)" % n)

        return ss_path

    # ── SLIDESHOW TEMPLATE ────────────────────────────────────
    # (Själva mallen ligger i html_generator_templates.py)

    # ==========================================================================
    # HTML-BYGGARE
    # ==========================================================================
    def _build_gallery_cards(
        self, entries: list, output_format: str,
    ) -> str:
        """Bygg HTML för galleri-bildkorten.

        OBS: Korten laddar FULLSTORLEKSBILDEN (samma som lightboxen)
        istället för den lilla thumbnailen. Det ger skarpa, icke-gryniga
        kort även på HiDPI-skärmar. loading="lazy" + decoding="async"
        håller uppe prestandan vid många bilder.
        """
        from .web_image_assets import responsive_attributes
        cards = []
        for entry in entries:
            idx         = entry["index"]
            title       = self._esc(entry.get("title", "Bild " + str(idx)))
            orig_name   = entry.get("original_name", entry["filename"])
            ext_display = ""
            if Path(orig_name).suffix:
                ext_display = Path(orig_name).suffix[1:].upper()

            if output_format == "standard":
                # Full bild för skärpa (thumb/ är för liten -> grynig)
                src = "image/" + entry["filename"]
            else:
                src = Path(entry.get("full_dst", "")).name
                if not src:
                    e   = Path(entry["filename"]).suffix or ".jpg"
                    src = "full_" + str(idx) + e

            # L4: proportion som CSS/JS använder för radjämn layout
            ratio = self._entry_ratio(entry)
            style = ' style="--ar:%.4f"' % ratio if ratio > 0 else ""

            card = (
                '    <div class="card" data-index="'
                + str(idx - 1) + '"' + style + ' '
                + 'tabindex="0" role="button" '
                + 'aria-label="' + title + '">\n'
                + '      <img src="' + src + '" '
                + responsive_attributes(entry, src)
                + ' alt="' + title + '" loading="lazy" '
                + 'decoding="async">\n'
                + '      <span class="card-num">#'
                + str(idx) + '</span>\n'
                + '      <span class="card-fmt">'
                + ext_display + '</span>\n'
                + '      <div class="card-overlay">'
                + title + '</div>\n'
                + '    </div>'
            )
            cards.append(card)

        return "\n".join(cards)

    def _build_slides(
        self, entries: list, output_format: str,
    ) -> str:
        """Bygg HTML för slideshow-slides."""
        from .web_image_assets import responsive_attributes
        slides = []
        for i, entry in enumerate(entries):
            idx    = entry["index"]
            title  = self._esc(entry.get("title", "Bild " + str(idx)))
            active = " active" if i == 0 else ""

            if output_format == "standard":
                full = "image/" + entry["filename"]
            else:
                full = Path(entry.get("full_dst", "")).name
                if not full:
                    ext  = Path(entry["filename"]).suffix or ".jpg"
                    full = "full_" + str(idx) + ext

            slide = (
                '    <div class="slide' + active + '">\n'
                + '      <img src="' + full + '" '
                + responsive_attributes(entry, full, '100vw')
                + ' alt="' + title + '" loading="lazy">\n'
                + '      <div class="caption">' + title + '</div>\n'
                + '    </div>'
            )
            slides.append(slide)

        return "\n".join(slides)

    def _build_js_images(
        self, entries: list, output_format: str,
    ) -> str:
        """
        Bygg IMAGES-array (endast bilder) for lightbox (v2.9.0).

        Ordningen matchar bildkortens data-index (0-baserad), sa att
        bild→bild-bladrningen i lightboxen fortsatt fungerar som forut.
        Varje post: {src, thumb, title} (utan type - listan ar ren).
        """
        from .web_image_assets import responsive_srcset
        items = []

        for entry in entries:
            idx   = entry["index"]
            title = entry.get("title", "Bild " + str(idx))

            if output_format == "standard":
                full  = "image/" + entry["filename"]
                thumb = "thumb/" + entry["filename"]
            else:
                full  = Path(entry.get("full_dst", "")).name
                thumb = Path(entry.get("thumb_dst", "")).name
                if not full:
                    ext   = Path(entry["filename"]).suffix or ".jpg"
                    full  = "full_" + str(idx) + ext
                    thumb = "thumb_" + str(idx) + ext

            item = {'srcset': responsive_srcset(entry, full), 'src': full, 'thumb': thumb, 'title': title,
                    'download': entry.get('download', ''),
                    'downloadLabel': entry.get('download_label', '')}
            # Script-safe JSON: titles must never terminate the script element.
            encoded = json.dumps(item, ensure_ascii=False)
            for character, escape in (('<', 'u003c'), ('>', 'u003e'), ('&', 'u0026')):
                encoded = encoded.replace(character, chr(92) + escape)
            items.append(encoded)

        return "[\n    " + ",\n    ".join(items) + "\n  ]"

    def _build_js_videos(self, video_files: list) -> str:
        """
        Bygg VIDEOS-array (endast videor) for lightbox (v2.9.0).

        Varje post: {src, title}. När en video är öppen bläddrar
        prev/next, piltangenter och svep video→video - aldrig in i
        bildgalleriet.
        """
        items = []

        for vid in video_files:
            rel  = vid.get("relative_path", "")
            if not rel:
                continue
            name = vid.get("name", "video")
            items.append(
                '{"src":"' + self._esc_js(rel) + '",'
                + '"title":"' + self._esc_js(name) + '"}'
            )

        return "[\n    " + ",\n    ".join(items) + "\n  ]"

    def _build_video_strip(
        self, video_files: list, output_format: str,
    ) -> str:
        """
        Bygg video-remsan i galleriet (v2.9.0 / v3.3.0).

        Kortet visar JPEG-thumbnail om den skapats (V6), annars en
        video-ruta som webblasaren soker till ~1 s. Play-ikon ovanpa.
        Klick oppnar videon i lightbox (video->video).
        """
        if not video_files:
            return ""

        cards = []
        v_idx = 0
        for vid in video_files:
            rel = vid.get("relative_path", "")
            if not rel:
                continue
            name = self._esc(vid.get("name", "video"))
            thumb = vid.get("thumb_rel", "") or ""
            if thumb:
                media = (
                    '        <img src="' + self._esc(thumb)
                    + '" alt="" loading="lazy">\n'
                )
            else:
                media = (
                    '        <video src="' + self._esc(rel)
                    + '" muted playsinline preload="metadata" '
                    + 'onloadedmetadata="try{this.currentTime='
                    + 'Math.min(1,this.duration/4||0)}catch(e){}">'
                    + '</video>\n'
                )
            cards.append(
                '      <div class="vcard" data-video-index="'
                + str(v_idx) + '" tabindex="0" role="button" '
                + 'aria-label="' + name + '">\n'
                + '        <span class="vthumb">\n'
                + media
                + '        <span class="play">&#9654;</span></span>\n'
                + '        <span class="vname">' + name + '</span>\n'
                + '      </div>'
            )
            v_idx += 1

        return (
            '  <div class="video-strip" id="video-strip" '
            + 'role="region" aria-label="Videor">\n'
            + '    <h2>&#127916; Videor (' + str(v_idx) + ')</h2>\n'
            + '    <div class="video-grid">\n'
            + "\n".join(cards)
            + '\n    </div>\n  </div>'
        )

    # ==========================================================================
    # TEMA-CSS
    # ==========================================================================
    # (_get_theme_css ligger i html_generator_templates.py)

    # ==========================================================================
    # HJÄLPMETODER
    # ==========================================================================
    def _write_file(self, path: Path, content: str) -> None:
        """
        Skriv fil atomiskt (A9).

        Monster: mkstemp -> fdopen -> flush -> fsync -> os.replace.
        """
        tmp_path = None
        try:
            path.parent.mkdir(parents=True, exist_ok=True)

            fd, tmp_str = tempfile.mkstemp(
                dir=path.parent,
                prefix=".%s_" % path.stem,
                suffix=".tmp",
            )
            tmp_path = Path(tmp_str)

            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(content)
                f.flush()
                os.fsync(f.fileno())   # A9

            os.replace(tmp_path, path)
        except Exception:
            # Städa tmp + fallback: direkt skrivning
            try:
                if tmp_path and tmp_path.exists():
                    tmp_path.unlink()
            except Exception:
                pass
            try:
                path.write_text(content, encoding="utf-8")
            except Exception:
                pass

    def _safe_stem(self, name: str) -> str:
        """
        Säkert filnamns-stem.

        Bevarar unicode (åäö), ersätter specialtecken med underscore.
        Max 40 tecken.
        """
        safe = re.sub(r"[^\w\-]", "_", name, flags=re.UNICODE)
        safe = re.sub(r"_+", "_", safe)
        return safe[:40].strip("_") or "bild"

    def _make_title(self, stem: str) -> str:
        """
        Skapa läsbar titel från filnamns-stem.

        Tar bort ledande siffror, ersätter bindestreck/underscore.
        """
        title = re.sub(r"^[\d\-\._]+", "", stem)
        title = re.sub(r"[\-_]+", " ", title)
        return title.strip().title() or stem

    def _esc(self, text: str) -> str:
        """HTML-escapning."""
        return (
            str(text)
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&#39;")
        )

    def _esc_js(self, text: str) -> str:
        """JavaScript-sträng-escapning."""
        return (
            str(text)
            .replace("\\", "\\\\")
            .replace('"', '\\"')
            .replace("\n", "\\n")
            .replace("\r", "\\r")
        )
