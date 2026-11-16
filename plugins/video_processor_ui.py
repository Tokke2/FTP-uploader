#!/usr/bin/env python3
# ============================================================
# Hjalpmodul (mixin) for plugins/video_processor.py
# ============================================================
# FIL:       plugins/video_processor_ui.py
# PLATS:     plugins/ (ftp_gallery_uploader/plugins/video_processor_ui.py)
# Klass:     VideoProcessorUIMixin
# VERSION:   3.5.0
# AUTHOR:    Rickard Längkvist
# COPYRIGHT: Copyright (c) <år> Rickard Längkvist (dynamiskt år,
#            se COPYRIGHT-konstanten nedan)
# Syfte:     Innehaller VideoProcessor:s UI-byggare och UI-hjalpare
#            for att halla huvudfilen video_processor.py under 1800 rader.
#            VideoProcessor arver fran denna mixin:
#                class VideoProcessor(VideoProcessorUIMixin, BasePlugin)
#
#            OBS: Denna fil definierar INGEN PLUGIN_NAME och ignoreras
#            darfor av plugin-loadern (laddas bara som import).
#
# ÄNDRINGAR v3.4.0 → v3.5.0 (kvalitet/minne/snabbhet, icke-brytande):
#   [Q1]      Ny fabrik _mk_section(): all LabelFrame-boilerplate
#             (bg/fg/font/padx/pady/pack/registrering) samlad pa ETT
#             stalle -> mindre kod + identiskt utseende i alla sektioner.
#             Alla _build_*-metoder anvander den.
#   [Q2]      _make_colored_button(): hover/leave loses nu dynamiskt ur
#             aktuell tema-farg (color_attr + _darken) istallet for att
#             binda fast gamla bygg-tidsfarger. Felrattat: efter tema-byte
#             återställde hover inte langre det nya temat.
#   [Q3]      Tooltip-livscykel: after-id sparas + raderas vid hide;
#             befintlig tooltip förstörs före en ny visas -> inga
#             foraldrade Toplevel-fonster/after-callbacks kvar (minne).
#   [Q4]      _VIDEO_PRESETS flyttas till klassattribut (skapas en gang,
#             inte per anrop i apply_preset) -> mindre allokering + snabbare.
#   [Q5]      _ensure_theme_lists() skyddar aven _labels-skapande mot
#             dubbla registreringar; _reg_panels/_reg_labels de-duplicerar.
#
# ÄNDRINGAR v3.3.0 → v3.4.0 (DESIGN-SYSTEM-integration, spec v4.6.0):
#   [C1]      Fargerna hamtas fran ThemeEngine-designsystemet
#             (helpers v1.3.0) via _THEME_KEYS: bg, surface_alt,
#             fg, muted, success, error, warning, info,
#             COLOR_BTN_RUN/PAU/STP -> success/warning/error,
#             selection_fg (COLOR_BTN_FG, NY - vit knapptext),
#             bg_secondary (COLOR_LOG_BG), tooltip_bg/tooltip_fg
#   [C1]      Hela tema-monstret ligger i mixinen (arvs av
#             VideoProcessor - inga andra filer kraver andring):
#             _load_theme_colors, _restyle_all, on_theme_changed,
#             register_theme_callback (anropas i create_ui)
#   [C1]      _make_colored_button(): color ar nu ATTRIBUTNAMN -
#             hamtas via getattr() och registreras for omstyling
#   [C1]      Nya hjälpare: _ensure_theme_lists, _reg_panels,
#             _reg_labels, _mk_label (skapar+registrerar labels),
#             _safe_cfg (tyst config), widget_exists
#   [C4]      Alla ramar/labels registreras for tema-omstyling;
#             log-taggar satts via _setup_log_tags(); tooltips
#             far COLOR_TOOLTIP_FG; fargade knappar far
#             COLOR_BTN_FG (vit text i BADA teman)
#
# BEVARAT FRÅN v3.1.0–v3.3.0:
#   tk.Frame/tk.Canvas istf ttk (ingen gra bakgrund i morkt tema)
#   _make_colored_button + _darken (hover-effekt)
#   _add_tooltip (2.5s), toggle_paths, toggle_audio,
#   _toggle_image_compression_ui, apply_preset,
#   update_size_label, update_image_quality_label
#
# INNEHALLER METODER FOR:
#   - Tema-styrning (C1): _load_theme_colors, _restyle_all,
#     _setup_log_tags, on_theme_changed, register_theme_callback,
#     _ensure_theme_lists, _reg_panels, _reg_labels, _mk_label,
#     _safe_cfg, widget_exists
#   - create_ui + alla _build_*-sektioner (ffmpeg_status, image_compression,
#     quick_presets, video_settings, progress_section, video_list, log_section)
#   - Knapp-fabrik (_make_colored_button, _darken, _add_hover, _add_tooltip)
#   - UI-helpers (toggle_paths, toggle_audio, _toggle_image_compression_ui,
#     apply_preset, update_size_label, update_image_quality_label)
#
# BEROENDEN (forvantas pa self via VideoProcessor):
#   self.app, self.is_active, self.settings, self.canvas, self.ffmpeg_available,
#   self.ffmpeg_path, self.ffprobe_path, self.hardware_encoders,
#   self.queue_log, self.save_settings, self.start_processing,
#   self.toggle_pause, self.cancel_processing, self.refresh_video_list,
#   self.show_video_info, self.preview_video, self.remove_from_list,
#   self.auto_find_ffmpeg, self.test_ffmpeg_connection, self.download_ffmpeg,
#   self.browse_ffmpeg, self.browse_ffprobe, self.log, samt alla tk-variabler
#   som skapas i dessa byggare.
#
# IMPORTER:
#   tkinter as tk, ttk
# ============================================================

import tkinter as tk
from tkinter import ttk
from datetime import datetime

# HAS_PIL aterimporteras fran huvudmodulen vid runtime via self,
# men vi behover flaggan i UI-byggarna. Importera defensivt.
try:
    from PIL import Image  # noqa: F401
    HAS_PIL = True
except ImportError:
    HAS_PIL = False


class VideoProcessorUIMixin:
    """UI-byggare och UI-hjalpare for VideoProcessor (se filhuvud)."""

    VERSION   = "3.5.0"
    AUTHOR    = "Rickard Längkvist"
    COPYRIGHT = "Copyright (c) %d %s" % (datetime.now().year, "Rickard Längkvist")

    # -- Extra fargkonstanter (B1/C1: tema-styrbara) -----------
    COLOR_LOG_BG      = "#0f0f1a"
    COLOR_TOOLTIP_BG  = "#222222"
    COLOR_TOOLTIP_FG  = "#e2e8f0"
    COLOR_BTN_FG      = "#ffffff"

    # -- Tema-nyckelmappning (C1) ------------------------------
    _THEME_KEYS = {
        "COLOR_BG":          "bg",
        "COLOR_BG_MID":      "surface_alt",
        "COLOR_FG":          "fg",
        "COLOR_MUTED":       "muted",
        "COLOR_SUCCESS":     "success",
        "COLOR_ERROR":       "error",
        "COLOR_WARNING":     "warning",
        "COLOR_INFO":        "info",
        "COLOR_BTN_RUN":     "success",
        "COLOR_BTN_PAU":     "warning",
        "COLOR_BTN_STP":     "error",
        "COLOR_BTN_FG":      "selection_fg",
        "COLOR_LOG_BG":      "bg_secondary",
        "COLOR_TOOLTIP_BG":  "tooltip_bg",
        "COLOR_TOOLTIP_FG":  "tooltip_fg",
    }

    # -- Snabbpresets (Q4: klassattribut -> skapas en gang, ej per anrop) ---
    _VIDEO_PRESETS = {
        "ultrafast": {
            "quality": "ultrafast", "crf": 30,
            "max_width": 960,  "max_fps": 24,
            "audio_bitrate": 64,  "target_size": 8.0,
            "two_pass": False,
        },
        "balanced": {
            "quality": "faster",    "crf": 26,
            "max_width": 1280, "max_fps": 30,
            "audio_bitrate": 96,  "target_size": 12.0,
            "two_pass": False,
        },
        "quality": {
            "quality": "medium",    "crf": 22,
            "max_width": 1920, "max_fps": 30,
            "audio_bitrate": 128, "target_size": 20.0,
            "two_pass": True,
        },
        "web": {
            "quality": "fast",      "crf": 26,
            "max_width": 1280, "max_fps": 30,
            "audio_bitrate": 96,  "target_size": 10.0,
            "two_pass": False, "format": "mp4", "codec": "h264",
        },
        "mobile": {
            "quality": "faster",    "crf": 28,
            "max_width": 720,  "max_fps": 30,
            "audio_bitrate": 64,  "target_size": 5.0,
            "two_pass": False,
        },
    }

    # ==========================================================================
    # TEMA-FARGER (C1)
    # ==========================================================================

    def _ensure_theme_lists(self) -> None:
        """Initiera tema-omstylingslistor (defensivt for mixin)."""
        for name in ("_panels", "_buttons", "_labels"):
            if not hasattr(self, name):
                setattr(self, name, [])

    def _reg_panels(self, *widgets) -> None:
        """Registrera ramar/LabelFrames for tema-omstyling (de-duplicerat)."""
        for w in widgets:
            if w is not None and w not in self._panels:
                self._panels.append(w)

    def _reg_labels(self, *pairs) -> None:
        """Registrera (widget, fg-attribut)-par for tema-omstyling (de-dup)."""
        for pair in pairs:
            if pair and pair not in self._labels:
                self._labels.append(pair)

    def _mk_section(self, parent, text, fill=tk.X, expand=False,
                    padx=10, pady=5) -> tk.LabelFrame:
        """
        Skapa en standardiserad LabelFrame-sektion (Q1).

        Samlar all LabelFrame-boilerplate (bg/fg/font/padx/pady/
        pack/tema-registrering) pa en plats sa att alla byggare far
        identiskt utseende utan att upprepa koden.
        """
        f = tk.LabelFrame(
            parent, text=text,
            bg=self.COLOR_BG, fg=self.COLOR_FG,
            font=("Segoe UI", 9),
            padx=10, pady=8,
        )
        f.pack(fill=fill, expand=expand, padx=padx, pady=pady)
        self._reg_panels(f)
        return f

    def _mk_label(self, parent, text, fg_attr="COLOR_FG", **kwargs):
        """
        Skapa tk.Label med tema-registrering.

        Packas direkt om pack-kwargs skickas via 'pack'-nyckeln,
        t.ex. _mk_label(f, "Text", pack={"side": tk.LEFT}).
        """
        pack_kw = kwargs.pop("pack", None) or {}
        kwargs.setdefault("bg", self.COLOR_BG)
        kwargs.setdefault("font", ("Segoe UI", 9))
        lbl = tk.Label(
            parent, text=text,
            fg=getattr(self, fg_attr, "#888888"),
            **kwargs,
        )
        if pack_kw:
            lbl.pack(**pack_kw)
        self._labels.append((lbl, fg_attr))
        return lbl

    def _safe_cfg(self, widget, **kwargs) -> None:
        """Konfigurera widget tyst om den inte finns."""
        if self.widget_exists(widget):
            try:
                widget.config(**kwargs)
            except Exception:
                pass

    def _load_theme_colors(self) -> None:
        """
        Hamta farger fran ThemeEngine-designsystemet och
        uppdatera alla COLOR_*-attribut (fallback till
        klassattributen om theme_engine saknas).
        """
        if not self.app or not hasattr(self.app, "theme_engine"):
            return
        te = getattr(self.app, "theme_engine", None)
        if te is None or not hasattr(te, "get_color"):
            return
        try:
            for attr, key in self._THEME_KEYS.items():
                current  = getattr(self, attr, None)
                fallback = current if current else "#888888"
                setattr(self, attr, te.get_color(key, fallback))
        except Exception as e:
            self.log("FEL", "Tema-farger kunde inte laddas: %s" % e)

    def _restyle_all(self) -> None:
        """
        Applicera aktuella farger pa alla befintliga widgets
        (paneler, knappar, labels, canvas, logg) vid tema-byte.
        """
        if not self.is_active:
            return
        self._ensure_theme_lists()
        try:
            # -- Paneler (ramar + LabelFrames) -----------------
            for w in self._panels:
                if self.widget_exists(w):
                    self._safe_cfg(w, bg=self.COLOR_BG)
                    if isinstance(w, tk.LabelFrame):
                        self._safe_cfg(w, fg=self.COLOR_FG)
            # -- Fargade knappar --------------------------------
            for btn, color_attr in self._buttons:
                if self.widget_exists(btn):
                    c = getattr(self, color_attr, "#4b5563")
                    self._safe_cfg(
                        btn, bg=c, fg=self.COLOR_BTN_FG,
                        activebackground=self._darken(c),
                        activeforeground=self.COLOR_BTN_FG,
                    )
            # -- Labels -----------------------------------------
            for lbl, fg_attr in self._labels:
                if self.widget_exists(lbl):
                    self._safe_cfg(
                        lbl, bg=self.COLOR_BG,
                        fg=getattr(self, fg_attr, "#888888"),
                    )
            # -- Canvas -----------------------------------------
            self._safe_cfg(self.canvas, bg=self.COLOR_BG)
            # -- Logg -------------------------------------------
            if self.widget_exists(self.log_text):
                self._safe_cfg(
                    self.log_text, bg=self.COLOR_LOG_BG,
                    fg=self.COLOR_SUCCESS,
                    insertbackground=self.COLOR_SUCCESS,
                    selectbackground=self.COLOR_INFO,
                )
                self._setup_log_tags()
        except Exception:
            pass

    def _setup_log_tags(self) -> None:
        """Satt loggens fargtaggar fran aktuella tema-farger."""
        if not self.widget_exists(self.log_text):
            return
        try:
            self.log_text.tag_configure("error",   foreground=self.COLOR_ERROR)
            self.log_text.tag_configure("success", foreground=self.COLOR_SUCCESS)
            self.log_text.tag_configure("info",    foreground=self.COLOR_INFO)
            self.log_text.tag_configure("warning", foreground=self.COLOR_WARNING)
        except tk.TclError:
            pass

    def on_theme_changed(self, event=None) -> None:
        """
        Uppdatera alla farger vid tema-byte (utan omstart).

        Laddar nya farger fran ThemeEngine och applicerar dem
        pa alla befintliga widgets.
        """
        if not self.is_active:
            return
        self._load_theme_colors()
        self._restyle_all()

    def register_theme_callback(self) -> None:
        """Registrera on_theme_changed() for <<ThemeChanged>>-event."""
        if self.app:
            try:
                self.app.bind(
                    "<<ThemeChanged>>", self.on_theme_changed
                )
            except Exception:
                pass

    def widget_exists(self, widget) -> bool:
        """Returnerar True om widget finns och inte ar forstord."""
        try:
            return bool(widget and widget.winfo_exists())
        except tk.TclError:
            return False

    # ==========================================================================
    # UI-BYGGANDE
    # ==========================================================================

    def create_ui(self, parent) -> None:
        """
        Bygg hela granssnittet.

        VIKTIGT v3.1.0:
          Canvas och container = tk.Frame/tk.Canvas (inte ttk)
          -> ingen gra bakgrund i morkt tema.

        v3.4.0:
          Tema-farger laddas fore bygget och tema-callback
          registreras i slutet (C1).
        """
        self._ensure_theme_lists()
        self._load_theme_colors()

        bg = self.COLOR_BG

        self.canvas = tk.Canvas(parent, bg=bg, highlightthickness=0)
        scrollbar   = ttk.Scrollbar(
            parent, orient="vertical", command=self.canvas.yview
        )
        container = tk.Frame(self.canvas, bg=bg)

        container.bind(
            "<Configure>",
            lambda e: self.canvas.configure(
                scrollregion=self.canvas.bbox("all")
            ),
        )

        self.canvas.create_window((0, 0), window=container, anchor="nw")
        self.canvas.configure(yscrollcommand=scrollbar.set)

        scrollbar.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)

        self.canvas.bind("<Enter>", self._bind_mousewheel)
        self.canvas.bind("<Leave>", self._unbind_mousewheel)

        self._build_ffmpeg_status(container)
        self._build_image_compression(container)
        self._build_quick_presets(container)
        self._build_video_settings(container)
        self._build_progress_section(container)
        self._build_video_list(container)
        self._build_log_section(container)

        self.register_theme_callback()

    def _build_ffmpeg_status(self, parent) -> None:
        """FFmpeg-status + knappar + sokvagar."""
        bg    = self.COLOR_BG
        frame = self._mk_section(parent, "FFmpeg Status", pady=(10, 5))

        # Status-rad
        status_row = tk.Frame(frame, bg=bg)
        status_row.pack(fill=tk.X)
        self._reg_panels(status_row)

        status_color = (
            self.COLOR_SUCCESS if self.ffmpeg_available else self.COLOR_ERROR
        )
        status_text = (
            "FFmpeg hittad" if self.ffmpeg_available else "FFmpeg saknas"
        )
        self.ffmpeg_status = tk.Label(
            status_row, text=status_text,
            bg=bg, fg=status_color,
            font=("Segoe UI", 10, "bold"),
        )
        self.ffmpeg_status.pack(side=tk.LEFT)
        self._reg_labels((
            self.ffmpeg_status,
            "COLOR_SUCCESS" if self.ffmpeg_available else "COLOR_ERROR",
        ))

        hw_text = (
            " | HW: %s" % ", ".join(self.hardware_encoders[:3])
            if self.hardware_encoders
            else " | Ingen hardvaruacceleration"
        )
        if len(self.hardware_encoders) > 3:
            hw_text += "..."
        self.hw_label = self._mk_label(
            status_row, hw_text, "COLOR_MUTED",
            pack={"side": tk.LEFT, "padx": (10, 0)},
        )

        # Knappar
        btn_row = tk.Frame(status_row, bg=bg)
        btn_row.pack(side=tk.RIGHT)
        self._reg_panels(btn_row)
        for text, cmd in [
            ("Sok",       self.auto_find_ffmpeg),
            ("Testa",     self.test_ffmpeg_connection),
            ("Ladda ner", self.download_ffmpeg),
        ]:
            ttk.Button(btn_row, text=text, command=cmd).pack(
                side=tk.LEFT, padx=2
            )

        # Sokvagar (dolda som standard)
        self.paths_frame = tk.Frame(frame, bg=bg)
        self._reg_panels(self.paths_frame)
        for label_text, attr, browse_cmd in [
            ("FFmpeg:",  "ffmpeg_path_var",  self.browse_ffmpeg),
            ("FFprobe:", "ffprobe_path_var", self.browse_ffprobe),
        ]:
            self._mk_label(
                self.paths_frame, label_text,
                pack={"anchor": "w", "pady": (5, 0)},
            )

            row = tk.Frame(self.paths_frame, bg=bg)
            row.pack(fill=tk.X)
            self._reg_panels(row)

            raw  = attr.replace("_var", "")
            val  = getattr(self, raw, "") or ""
            var  = tk.StringVar(value=val)
            setattr(self, attr, var)

            ttk.Entry(row, textvariable=var, width=50).pack(
                side=tk.LEFT, fill=tk.X, expand=True
            )
            ttk.Button(row, text="...", command=browse_cmd, width=3).pack(
                side=tk.LEFT, padx=2
            )

        if not self.ffmpeg_available:
            self._mk_label(
                frame,
                "FFmpeg kravs for videokomprimering. "
                "Klicka 'Ladda ner' for instruktioner.",
                "COLOR_WARNING",
                pack={"anchor": "w", "pady": (5, 0)},
            )

        self.show_paths_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            frame, text="Visa sokvagar",
            variable=self.show_paths_var,
            command=self.toggle_paths,
        ).pack(anchor="w", pady=(5, 0))

    def _build_image_compression(self, parent) -> None:
        """Bildkomprimerings-sektion."""
        bg    = self.COLOR_BG
        frame = self._mk_section(parent, "Bildkomprimering")

        # Aktivera
        self.compress_images_var = tk.BooleanVar(
            value=self.settings.get("compress_images", True)
        )
        ttk.Checkbutton(
            frame, text="Komprimera bilder vid export",
            variable=self.compress_images_var,
            command=self._toggle_image_compression_ui,
        ).pack(anchor="w")

        if not HAS_PIL:
            self._mk_label(
                frame,
                "Pillow saknas (pip install Pillow) - "
                "bildkomprimering ej tillganglig",
                "COLOR_WARNING",
                pack={"anchor": "w", "pady": (2, 0)},
            )

        # Installningar-container
        self._img_settings_frame = tk.Frame(frame, bg=bg)
        self._img_settings_frame.pack(fill=tk.X, pady=(8, 0))
        self._reg_panels(self._img_settings_frame)

        # Rad 1: Kvalitet + Max bredd
        r1 = tk.Frame(self._img_settings_frame, bg=bg)
        r1.pack(fill=tk.X, pady=3)
        self._mk_label(r1, "Kvalitet:", pack={"side": tk.LEFT})

        self.image_quality_var = tk.IntVar(
            value=self.settings.get("image_quality", 82)
        )
        self.img_quality_scale = ttk.Scale(
            r1, from_=10, to=95,
            variable=self.image_quality_var,
            orient=tk.HORIZONTAL, length=140,
            command=self.update_image_quality_label,
        )
        self.img_quality_scale.pack(side=tk.LEFT, padx=(5, 0))
        self.img_quality_label = tk.Label(
            r1, text="%d%%" % self.image_quality_var.get(),
            width=5, bg=bg, fg=self.COLOR_FG,
            font=("Segoe UI", 9),
        )
        self.img_quality_label.pack(side=tk.LEFT, padx=(3, 15))
        self._reg_labels((self.img_quality_label, "COLOR_FG"))

        self._mk_label(r1, "Max bredd:", pack={"side": tk.LEFT})

        self.image_max_width_var = tk.IntVar(
            value=self.settings.get("image_max_width", 1920)
        )
        img_width_combo = ttk.Combobox(
            r1, textvariable=self.image_max_width_var,
            values=[800, 1024, 1280, 1600, 1920, 2560, 0],
            width=6,
        )
        img_width_combo.pack(side=tk.LEFT, padx=5)
        self._add_tooltip(img_width_combo, "0 = behall originalstorlek")

        # Rad 2: Format och optioner
        r2 = tk.Frame(self._img_settings_frame, bg=bg)
        r2.pack(fill=tk.X, pady=3)
        self._mk_label(r2, "Utdataformat:", pack={"side": tk.LEFT})

        self.image_format_var = tk.StringVar(
            value=self.settings.get("image_format", "jpg")
        )
        ttk.Combobox(
            r2, textvariable=self.image_format_var,
            values=["jpg", "png", "webp"],
            state="readonly", width=6,
        ).pack(side=tk.LEFT, padx=5)

        self.image_strip_exif_var = tk.BooleanVar(
            value=self.settings.get("image_strip_exif", False)
        )
        ttk.Checkbutton(
            r2, text="Ta bort EXIF-data",
            variable=self.image_strip_exif_var,
        ).pack(side=tk.LEFT, padx=(15, 0))

        self.image_progressive_var = tk.BooleanVar(
            value=self.settings.get("image_progressive", True)
        )
        ttk.Checkbutton(
            r2, text="Progressive JPEG",
            variable=self.image_progressive_var,
        ).pack(side=tk.LEFT, padx=(15, 0))

        # Rad 3: Info
        r3 = tk.Frame(self._img_settings_frame, bg=bg)
        r3.pack(fill=tk.X, pady=(5, 0))
        info_text = (
            "Pillow: JPG, PNG, WebP, BMP, TIFF  |  "
            "WebP ger 25-35% battre komprimering an JPEG"
            if HAS_PIL
            else "Installera Pillow: pip install Pillow"
        )
        self._mk_label(
            r3, info_text, "COLOR_MUTED", pack={"anchor": "w"}
        )
        self._reg_panels(r1, r2, r3)

        if not HAS_PIL:
            self.compress_images_var.set(False)
            self._toggle_image_compression_ui()

    def _build_quick_presets(self, parent) -> None:
        """Snabbpresets for video."""
        bg    = self.COLOR_BG
        frame = self._mk_section(parent, "Snabbinstallningar Video")

        row = tk.Frame(frame, bg=bg)
        row.pack(fill=tk.X)
        self._reg_panels(row)

        presets = [
            ("Snabb",      "ultrafast", "Snabbast, lagre kvalitet"),
            ("Balanserad", "balanced",  "Bra balans (rekommenderad)"),
            ("Kvalitet",   "quality",   "Bast kvalitet, langsammare"),
            ("Webb",       "web",       "Optimerad for webben"),
            ("Mobil",      "mobile",    "Liten filstorlek for mobil"),
        ]
        for text, preset_id, tip in presets:
            btn = ttk.Button(
                row, text=text,
                command=lambda p=preset_id: self.apply_preset(p),
            )
            btn.pack(side=tk.LEFT, padx=3, pady=2)
            self._add_tooltip(btn, tip)

    def _build_video_settings(self, parent) -> None:
        """Detaljerade videoinstallningar."""
        bg    = self.COLOR_BG
        frame = self._mk_section(parent, "Videoinstallningar")

        # Rad 1: Storlek / Hastighet / CRF
        r1 = tk.Frame(frame, bg=bg)
        r1.pack(fill=tk.X, pady=3)
        self._mk_label(r1, "Malstorlek:", pack={"side": tk.LEFT})

        self.target_size_var = tk.DoubleVar(
            value=self.settings.get("target_size_mb", 12.0)
        )
        sf = tk.Frame(r1, bg=bg)
        sf.pack(side=tk.LEFT, padx=5)
        ttk.Scale(
            sf, from_=1, to=25,
            variable=self.target_size_var,
            orient=tk.HORIZONTAL, length=120,
            command=self.update_size_label,
        ).pack(side=tk.LEFT)
        self.size_label = tk.Label(
            sf, text="%.0f MB" % self.target_size_var.get(),
            width=6, bg=bg, fg=self.COLOR_FG,
            font=("Segoe UI", 9),
        )
        self.size_label.pack(side=tk.LEFT)
        self._reg_labels((self.size_label, "COLOR_FG"))

        self._mk_label(
            r1, "Hastighet:", pack={"side": tk.LEFT, "padx": (15, 5)}
        )
        self.quality_var = tk.StringVar(
            value=self.settings.get("quality", "faster")
        )
        ttk.Combobox(
            r1, textvariable=self.quality_var,
            values=["ultrafast", "superfast", "veryfast",
                    "faster", "fast", "medium"],
            state="readonly", width=10,
        ).pack(side=tk.LEFT)

        self._mk_label(
            r1, "CRF:", pack={"side": tk.LEFT, "padx": (15, 5)}
        )
        self.crf_var = tk.IntVar(value=self.settings.get("crf", 28))
        crf = ttk.Spinbox(r1, from_=18, to=35,
                          textvariable=self.crf_var, width=4)
        crf.pack(side=tk.LEFT)
        self._add_tooltip(crf, "Lagre = battre kvalitet (18-35)")

        # Rad 2: Bredd / FPS / Format / Codec
        r2 = tk.Frame(frame, bg=bg)
        r2.pack(fill=tk.X, pady=3)
        self._mk_label(r2, "Max bredd:", pack={"side": tk.LEFT})
        self.max_width_var = tk.IntVar(
            value=self.settings.get("max_width", 1280)
        )
        ttk.Combobox(
            r2, textvariable=self.max_width_var,
            values=[480, 640, 720, 960, 1280, 1920],
            width=6,
        ).pack(side=tk.LEFT, padx=5)

        self._mk_label(
            r2, "Max FPS:", pack={"side": tk.LEFT, "padx": (10, 5)}
        )
        self.fps_var = tk.IntVar(value=self.settings.get("max_fps", 30))
        ttk.Combobox(
            r2, textvariable=self.fps_var,
            values=[15, 24, 25, 30, 60],
            state="readonly", width=4,
        ).pack(side=tk.LEFT)

        self._mk_label(
            r2, "Format:", pack={"side": tk.LEFT, "padx": (10, 5)}
        )
        self.format_var = tk.StringVar(
            value=self.settings.get("format", "mp4")
        )
        ttk.Combobox(
            r2, textvariable=self.format_var,
            values=["mp4", "webm"], state="readonly", width=6,
        ).pack(side=tk.LEFT)

        self._mk_label(
            r2, "Codec:", pack={"side": tk.LEFT, "padx": (10, 5)}
        )
        self.codec_var = tk.StringVar(
            value=self.settings.get("codec", "h264")
        )
        ttk.Combobox(
            r2, textvariable=self.codec_var,
            values=["h264", "h265", "vp9"],
            state="readonly", width=6,
        ).pack(side=tk.LEFT)

        # Rad 3: Ljud
        r3 = tk.Frame(frame, bg=bg)
        r3.pack(fill=tk.X, pady=3)

        self.keep_audio_var = tk.BooleanVar(
            value=self.settings.get("keep_audio", True)
        )
        ttk.Checkbutton(
            r3, text="Behall ljud",
            variable=self.keep_audio_var,
            command=self.toggle_audio,
        ).pack(side=tk.LEFT)

        self._mk_label(
            r3, "Bitrate:", pack={"side": tk.LEFT, "padx": (10, 5)}
        )
        self.audio_bitrate_var = tk.IntVar(
            value=self.settings.get("audio_bitrate", 96)
        )
        self.audio_bitrate_combo = ttk.Combobox(
            r3, textvariable=self.audio_bitrate_var,
            values=[48, 64, 96, 128, 192],
            state="readonly", width=5,
        )
        self.audio_bitrate_combo.pack(side=tk.LEFT)
        self._mk_label(r3, "kbps", "COLOR_MUTED", pack={"side": tk.LEFT})

        # Rad 4: Thumbnail / 2-pass / Hardvara / Tradar
        r4 = tk.Frame(frame, bg=bg)
        r4.pack(fill=tk.X, pady=3)

        self.generate_thumbnail_var = tk.BooleanVar(
            value=self.settings.get("generate_thumbnail", True)
        )
        ttk.Checkbutton(
            r4, text="Skapa thumbnail",
            variable=self.generate_thumbnail_var,
        ).pack(side=tk.LEFT)

        self.two_pass_var = tk.BooleanVar(
            value=self.settings.get("two_pass", False)
        )
        ttk.Checkbutton(
            r4, text="2-pass (langsammare)",
            variable=self.two_pass_var,
        ).pack(side=tk.LEFT, padx=10)

        self.use_hardware_var = tk.BooleanVar(
            value=self.settings.get("use_hardware_accel", False)
        )
        hw_check = ttk.Checkbutton(
            r4, text="Hardvaruaccel.",
            variable=self.use_hardware_var,
        )
        hw_check.pack(side=tk.LEFT, padx=10)
        if not self.hardware_encoders:
            hw_check.config(state="disabled")
            self._add_tooltip(hw_check, "Ingen hardvaruacceleration hittad")

        self._mk_label(
            r4, "Tradar:", pack={"side": tk.LEFT, "padx": (10, 5)}
        )
        self.threads_var = tk.IntVar(
            value=self.settings.get("threads", 0)
        )
        ts = ttk.Spinbox(r4, from_=0, to=16,
                         textvariable=self.threads_var, width=3)
        ts.pack(side=tk.LEFT)
        self._add_tooltip(ts, "0 = automatiskt")

        # Rad 5: Extra FFmpeg-argument
        r5 = tk.Frame(frame, bg=bg)
        r5.pack(fill=tk.X, pady=3)
        self._mk_label(r5, "Extra FFmpeg-arg:", pack={"side": tk.LEFT})
        self.extra_args_var = tk.StringVar(
            value=self.settings.get("extra_args", "")
        )
        ttk.Entry(
            r5, textvariable=self.extra_args_var, width=40
        ).pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        ttk.Button(
            r5, text="Spara allt", command=self.save_settings
        ).pack(side=tk.RIGHT)

        self._reg_panels(r1, r2, r3, r4, r5, sf)

    def _build_progress_section(self, parent) -> None:
        """Progress-sektion med knappar."""
        bg    = self.COLOR_BG
        frame = self._mk_section(parent, "Bearbetning")

        # Total progress
        r1 = tk.Frame(frame, bg=bg)
        r1.pack(fill=tk.X, pady=2)
        self._mk_label(r1, "Totalt:", pack={"side": tk.LEFT})
        self.overall_label = tk.Label(
            r1, text="0/0", width=10,
            bg=bg, fg=self.COLOR_FG,
            font=("Segoe UI", 9),
        )
        self.overall_label.pack(side=tk.LEFT, padx=5)
        self.total_progress_var = tk.DoubleVar()
        style = ttk.Style()
        style.configure('Video.Horizontal.TProgressbar', thickness=22, background='#19b9d0', troughcolor='#17213a')
        self.total_progress_bar = ttk.Progressbar(
            r1, variable=self.total_progress_var, style='Video.Horizontal.TProgressbar',
            maximum=100, length=300, mode="determinate",
        )
        self.total_progress_bar.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        self.eta_label = self._mk_label(
            r1, "", "COLOR_MUTED", width=12,
            pack={"side": tk.RIGHT},
        )

        # Aktuell fil
        r2 = tk.Frame(frame, bg=bg)
        r2.pack(fill=tk.X, pady=2)
        self._mk_label(r2, "Aktuell:", pack={"side": tk.LEFT})
        self.current_file_label = tk.Label(
            r2, text="-", width=30, anchor="w",
            bg=bg, fg=self.COLOR_FG,
            font=("Segoe UI", 9),
        )
        self.current_file_label.pack(side=tk.LEFT, padx=5)
        self.current_progress_var = tk.DoubleVar()
        self.current_progress_bar = ttk.Progressbar(
            r2, variable=self.current_progress_var, style='Video.Horizontal.TProgressbar',
            maximum=100, length=240, mode="determinate",
        )
        self.current_progress_bar.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        self.current_percent_label = tk.Label(
            r2, text="0%", width=10,
            bg=bg, fg=self.COLOR_FG,
            font=("Segoe UI", 9),
        )
        self.current_percent_label.pack(side=tk.RIGHT)

        # Status + hastighet
        r3 = tk.Frame(frame, bg=bg)
        r3.pack(fill=tk.X, pady=5)
        self.status_label = self._mk_label(
            r3, "Redo", "COLOR_MUTED",
            font=("Segoe UI", 10), pack={"side": tk.LEFT},
        )
        self.speed_label = self._mk_label(
            r3, "", "COLOR_MUTED", pack={"side": tk.RIGHT},
        )

        # Knappar
        btn_row = tk.Frame(frame, bg=bg)
        btn_row.pack(fill=tk.X, pady=(10, 0))

        self.process_btn = self._make_colored_button(
            btn_row, "Bearbeta video + bilder",
            self.start_processing, "COLOR_BTN_RUN",
            font_size=10, bold=True, padx=15, pady=5,
        )
        self.process_btn.pack(side=tk.LEFT, padx=2)

        self.pause_btn = self._make_colored_button(
            btn_row, "Pausa",
            self.toggle_pause, "COLOR_BTN_PAU",
            padx=10, pady=5,
        )
        self.pause_btn.pack(side=tk.LEFT, padx=2)
        self.pause_btn.config(state="disabled")

        self.cancel_btn = self._make_colored_button(
            btn_row, "Avbryt",
            self.cancel_processing, "COLOR_BTN_STP",
            padx=10, pady=5,
        )
        self.cancel_btn.pack(side=tk.LEFT, padx=2)
        self.cancel_btn.config(state="disabled")

        self._reg_panels(r1, r2, r3, btn_row)
        self._reg_labels(
            (self.overall_label, "COLOR_FG"),
            (self.current_file_label, "COLOR_FG"),
            (self.current_percent_label, "COLOR_FG"),
        )

    def _build_video_list(self, parent) -> None:
        """Videolista med Treeview."""
        bg    = self.COLOR_BG
        frame = self._mk_section(parent, "Videofiler", fill=tk.BOTH,
                                 expand=True)

        # Toolbar
        tb = tk.Frame(frame, bg=bg)
        tb.pack(fill=tk.X, pady=(0, 5))
        for text, cmd in [
            ("Uppdatera", self.refresh_video_list),
            ("Info",      self.show_video_info),
            ("Spela",     self.preview_video),
            ("Ta bort",   self.remove_from_list),
        ]:
            ttk.Button(tb, text=text, command=cmd).pack(side=tk.LEFT, padx=2)

        self.video_count_label = self._mk_label(
            tb, "0 videor", "COLOR_MUTED", pack={"side": tk.RIGHT},
        )

        # Treeview
        list_container = tk.Frame(frame, bg=bg)
        list_container.pack(fill=tk.BOTH, expand=True)
        self._reg_panels(frame, tb, list_container)

        columns = ("name", "size", "duration", "status")
        self.video_tree = ttk.Treeview(
            list_container, columns=columns, show="headings", height=6
        )
        for col, heading, width in [
            ("name",     "Filnamn",  250),
            ("size",     "Storlek",   80),
            ("duration", "Langd",     80),
            ("status",   "Status",   120),
        ]:
            self.video_tree.heading(col, text=heading)
            self.video_tree.column(col, width=width)

        sb = ttk.Scrollbar(
            list_container, orient=tk.VERTICAL,
            command=self.video_tree.yview
        )
        self.video_tree.configure(yscrollcommand=sb.set)
        self.video_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb.pack(side=tk.RIGHT, fill=tk.Y)

        self.video_tree.bind(
            "<Double-1>", lambda e: self.show_video_info()
        )

        # Mushjul i treeview (3 enheter)
        self.video_tree.bind(
            "<MouseWheel>",
            lambda e: self.video_tree.yview_scroll(
                -1 * (e.delta // 120) * 3, "units"
            )
        )
        self.video_tree.bind(
            "<Button-4>",
            lambda e: self.video_tree.yview_scroll(-3, "units")
        )
        self.video_tree.bind(
            "<Button-5>",
            lambda e: self.video_tree.yview_scroll(3, "units")
        )

    def _build_log_section(self, parent) -> None:
        """Loggsektion."""
        bg    = self.COLOR_BG
        frame = self._mk_section(parent, "Logg", pady=(5, 10))

        lc = tk.Frame(frame, bg=bg)
        lc.pack(fill=tk.X)
        self._reg_panels(lc)

        self.log_text = tk.Text(
            lc, height=5,
            bg=self.COLOR_LOG_BG, fg=self.COLOR_SUCCESS,
            font=("Consolas", 9), wrap=tk.WORD,
            relief="flat",
        )
        sb = ttk.Scrollbar(lc, orient=tk.VERTICAL,
                           command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=sb.set)
        self.log_text.pack(side=tk.LEFT, fill=tk.X, expand=True)
        sb.pack(side=tk.RIGHT, fill=tk.Y)

        # Fargtaggar
        self._setup_log_tags()

        # Mushjul (3 enheter)
        self.log_text.bind(
            "<MouseWheel>",
            lambda e: self.log_text.yview_scroll(
                -1 * (e.delta // 120) * 3, "units"
            )
        )
        self.log_text.bind(
            "<Button-4>",
            lambda e: self.log_text.yview_scroll(-3, "units")
        )
        self.log_text.bind(
            "<Button-5>",
            lambda e: self.log_text.yview_scroll(3, "units")
        )

        # Rensa-knapp
        ttk.Button(
            frame, text="Rensa logg",
            command=lambda: self.log_text.delete("1.0", tk.END)
        ).pack(anchor="w", pady=(5, 0))

    def _make_colored_button(
        self, parent, text, command, color_attr,
        font_size=9, bold=False, **pack_kwargs
    ) -> tk.Button:
        """
        Skapa fargad knapp med hover-effekt.

        color_attr ar ATTRIBUTNAMN (strang) - vardet hamtas via
        getattr() sa att knappen foljer aktuella tema-farger och
        registreras for omstyling vid tema-byte (C1).
        """
        color  = getattr(self, color_attr, "#4b5563")
        weight = "bold" if bold else "normal"
        darker = self._darken(color)

        def _resolved():
            # Q2: los aktuell tema-farg dynamiskt sa att hover/leave
            # alltid foljer nyaste temat (annars fastnar gamla bygg-farger).
            c = getattr(self, color_attr, "#4b5563")
            return c, self._darken(c)

        btn = tk.Button(
            parent, text=text, command=command,
            bg=color, fg=self.COLOR_BTN_FG,
            font=("Segoe UI", font_size, weight),
            cursor="hand2", relief="flat",
            activebackground=darker,
            activeforeground=self.COLOR_BTN_FG,
            **pack_kwargs,
        )
        btn.bind("<Enter>", lambda e: btn.config(bg=_resolved()[1]))
        btn.bind("<Leave>", lambda e: btn.config(bg=_resolved()[0]))
        self._buttons.append((btn, color_attr))
        return btn

    @staticmethod
    def _darken(hex_color: str, factor: float = 0.80) -> str:
        """Morknar en hex-farg for hover-effekter."""
        try:
            h = hex_color.lstrip("#")
            r = int(int(h[0:2], 16) * factor)
            g = int(int(h[2:4], 16) * factor)
            b = int(int(h[4:6], 16) * factor)
            return "#%02x%02x%02x" % (r, g, b)
        except Exception:
            return hex_color

    def _add_hover(self, btn: tk.Button,
                   hover_color: str, normal_color: str) -> None:
        """Lagg till hover-effekt."""
        btn.bind("<Enter>", lambda e: btn.config(bg=hover_color))
        btn.bind("<Leave>", lambda e: btn.config(bg=normal_color))

    def _add_tooltip(self, widget, text: str) -> None:
        """Visa tooltip vid hover (2.5s) med tema-farger (C4)."""
        # Q3: after-id sparas + Toplevel destroyas innan en ny visas,
        # och efter-callbacken avbryts vid hide -> inga foraldrade
        # Toplevel-fonster eller after-callbacks kan lämnas kvar.
        def _destroy():
            if getattr(widget, "_tooltip", None):
                try:
                    widget._tooltip.destroy()
                except Exception:
                    pass
                widget._tooltip = None
            if getattr(widget, "_tooltip_after", None):
                try:
                    widget.after_cancel(widget._tooltip_after)
                except Exception:
                    pass
                widget._tooltip_after = None

        def show(event):
            if not self.is_active:
                return
            _destroy()  # ingen gammal tooltip kvar innan en ny visas
            tip = tk.Toplevel(widget)
            tip.wm_overrideredirect(True)
            tip.wm_geometry(
                "+%d+%d" % (event.x_root + 12, event.y_root + 12)
            )
            tk.Label(
                tip, text=text,
                bg=self.COLOR_TOOLTIP_BG, fg=self.COLOR_TOOLTIP_FG,
                font=("Segoe UI", 9), padx=6, pady=3,
                relief="solid", borderwidth=1,
            ).pack()
            widget._tooltip = tip
            widget._tooltip_after = widget.after(2500, _destroy)

        def hide(event):
            _destroy()

        widget.bind("<Enter>", show)
        widget.bind("<Leave>", hide)

    def toggle_paths(self) -> None:
        """Visa/dolj FFmpeg-sokvagar."""
        if self.show_paths_var.get():
            self.paths_frame.pack(fill=tk.X, pady=(5, 0))
        else:
            self.paths_frame.pack_forget()

    def toggle_audio(self) -> None:
        """Aktivera/inaktivera ljud-installningar."""
        state = "readonly" if self.keep_audio_var.get() else "disabled"
        self.audio_bitrate_combo.config(state=state)

    def _toggle_image_compression_ui(self) -> None:
        """Aktivera/inaktivera bildkomprimerings-installningar."""
        enabled = self.compress_images_var.get() and HAS_PIL

        def _set_state(widget, state):
            try:
                widget.config(state=state)
            except Exception:
                pass
            for child in widget.winfo_children():
                _set_state(child, state)

        _set_state(
            self._img_settings_frame,
            "normal" if enabled else "disabled"
        )

    def apply_preset(self, preset_name: str) -> None:
        """Applicera snabbpreset for video."""
        p = self._VIDEO_PRESETS.get(preset_name)
        if not p:
            return

        self.quality_var.set(p.get("quality", "faster"))
        self.crf_var.set(p.get("crf", 26))
        self.max_width_var.set(p.get("max_width", 1280))
        self.fps_var.set(p.get("max_fps", 30))
        self.audio_bitrate_var.set(p.get("audio_bitrate", 96))
        self.target_size_var.set(p.get("target_size", 12.0))
        self.two_pass_var.set(p.get("two_pass", False))
        if "format" in p:
            self.format_var.set(p["format"])
        if "codec" in p:
            self.codec_var.set(p["codec"])
        self.update_size_label()
        self.queue_log("Preset '%s' vald" % preset_name, "info")

    def update_size_label(self, *args) -> None:
        """Uppdatera MB-label vid slider."""
        try:
            self.size_label.config(
                text="%.0f MB" % self.target_size_var.get()
            )
        except Exception:
            pass

    def update_image_quality_label(self, *args) -> None:
        """Uppdatera bildkvalitets-label vid slider."""
        try:
            self.img_quality_label.config(
                text="%d%%" % self.image_quality_var.get()
            )
        except Exception:
            pass
