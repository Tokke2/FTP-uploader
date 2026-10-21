#!/usr/bin/env python3
# ============================================================
# Plugin: Bildgalleri
# ============================================================
# FIL:       plugins/gallery_view.py
# PLATS:     plugins/ (ftp_gallery_uploader/plugins/gallery_view.py)
# Klass:     GalleryView(GalleryViewMixin, BasePlugin)
# PRIORITY:  5
# VERSION:   2.6.0
# AUTHOR:    Rickard Längkvist
# COPYRIGHT: Copyright (c) <år> Rickard Längkvist (dynamiskt år,
#            se COPYRIGHT-konstanten nedan)
#
# ÄNDRINGAR v2.4.0 → v2.5.0 (DESIGN-SYSTEM-integration, spec v4.6.0):
#   [C1]      Fargerna hamtas nu fran ThemeEngine-designsystemet
#             (helpers v1.3.0, 58 nycklar/tema) via _THEME_KEYS:
#               COLOR_BG           <- "bg"
#               COLOR_BG_MID       <- "surface_alt"
#               COLOR_BG_ITEM      <- "card_bg"
#               COLOR_SEL          <- "selection_bg"
#               COLOR_SEL_B        <- "accent_hover"
#               COLOR_ROT          <- "warning"
#               COLOR_FG           <- "fg"
#               COLOR_MUTED        <- "muted"
#               COLOR_BTN_FG (NY)  <- "selection_fg"  (vit knapptext)
#               COLOR_ACCENT       <- "accent"
#               COLOR_GREEN        <- "success"
#               COLOR_GREEN_DARK   <- "success"
#               COLOR_RED          <- "error"
#               COLOR_ORANGE       <- "warning"
#               COLOR_PURPLE       <- "accent_active"
#               COLOR_CYAN         <- "info"
#               COLOR_PINK         <- "warning"
#               COLOR_GRAY_BTN     <- "button_bg"
#               COLOR_GRAY_MID     <- "button_bg"
#               COLOR_DRAG         <- "success"
#               COLOR_DRAG_FG      <- "inverse_text"
#               COLOR_THUMB_BG     <- "bg_secondary"
#               COLOR_TOOLTIP_BG   <- "tooltip_bg"
#               COLOR_TOOLTIP_FG   <- "tooltip_fg"  (NY)
#   [C1]      _load_theme_colors(): hamtar farger fran
#             app.theme_engine.get_color() med fallback
#   [C1]      _restyle_all(): applicerar aktuella farger pa alla
#             befintliga widgets och ritar om galleriet
#   [C1]      on_theme_changed(): uppdaterar allt vid tema-byte
#             (utan omstart); register_theme_callback() i init()
#   [C1]      _btn(): bg ar nu ATTRIBUTNAMN (strang) - hamtas
#             via getattr() sa att knapparna foljer temat
#   [C4]      Alla fargvarden via COLOR_*-attribut (uppdateras
#             dynamiskt fran temat); "white" ersatt av
#             COLOR_BTN_FG (checkmark + rotationsbadge)
#   [C4]      Tooltips anvander COLOR_TOOLTIP_BG/FG fran temat
#
# ÄNDRINGAR v2.5.0 → v2.6.0 (snabbhet/minne/loggning, icke-brytande):
#   refresh_gallery O(n^2)->O(n) (path-indexkarta); canvas-resize-
#   debounce; deterministisk PIL-stangning + delad _build_photoimage();
#   tooltip-lifecycle utan Toplevel-ackumulering; timer-avbrott i
#   cleanup; VARNING-logg nar thumbnails misslyckas.
#   (Thumbnail-/builder-metoderna ligger i gallery_view_helpers.)
#
# BEVARAT FRÅN v2.4.0:
#   Alla B1/A9/A10-krav (inga f-strings, atomisk save_config med
#   fsync, config/ via helpers, AUTHOR + COPYRIGHT + PLATS),
#   loggning via self.log() utan print(), load_config/save_config
#   egna metoder, widget_exists()/safe_after()/safe_widget_config(),
#   tk.Frame-baserade verktygsrader, Popen for extern oppning,
#   tysta _load_thumbnails/refresh_gallery, atomisk save_config.
#
# KLASSER I DENNA FIL:
#   GalleryView(GalleryViewMixin, BasePlugin) - PRIORITY=5
#
# IMPORTER:
#   tkinter as tk, ttk, filedialog, messagebox
#   pathlib.Path
#   json, shutil, time, subprocess, sys, random, os, tempfile
#   datetime
#   PIL: Image, ImageTk, ImageOps
#   .base_plugin: BasePlugin
#   .gallery_view_helpers: GalleryViewMixin
#   helpers: get_config_path (valfritt, A10)
#
# CONTEXT SOM LASES:
#   '_tab_manager'   - add_tab()
#   '_settings'      - folder_var
#   '_logger'        - log()
#
# CONTEXT SOM SATTS:
#   '_gallery_view'      - self
#   'get_gallery_images' - self.get_sorted_images
#   'gallery_images'     - [Path]
#   'sorted_images'      - [Path] (alias)
#   'gallery_order'      - bool
#   'image_rotations'    - dict {Path: int}
#
# JSON: config/gallery_settings.json
#   thumbnail_size, show_filenames, show_numbers, show_filesize,
#   show_dimensions, confirm_delete, auto_save, animation_enabled,
#   double_click_preview, rotation_saves_file,
#   load_last_folder_on_start, last_folder
#
# SORTERINGSFIL: <mapp>/.gallery_sort.json
#   { "order": [...], "rotations": {...}, "updated": "..." }
#
# OBS: gallery_view_helpers.py (GalleryViewMixin) i samma mapp.
# ============================================================

import app_paths
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path
import json
import os
import shutil
import time
import subprocess
import sys
import random
import tempfile
from datetime import datetime
from PIL import Image, ImageTk, ImageOps

from .base_plugin import BasePlugin
from .gallery_view_helpers import GalleryViewMixin

# -- Helpers (valfritt – för config-sökväg, A10) ---------------
try:
    from helpers import get_config_path
    _HAS_HELPERS = True
except ImportError:
    _HAS_HELPERS = False


class GalleryView(GalleryViewMixin, BasePlugin):
    """
    Bildgalleri-plugin med sortering, rotation, multi-select
    och drag & drop.

    Autostart: om 'load_last_folder_on_start' ar True laddas
    senast oppnade mapp automatiskt vid init().

    v2.6.0:
    - refresh_gallery O(n^2)->O(n), canvas-resize-debounce,
      deterministisk PIL-stangning, tooltip-lifecycle, timer-avbrott
      i cleanup, thumbnailfel-logg.
    """

    PLUGIN_NAME = "Bildgalleri"
    PRIORITY    = 5
    VERSION     = "2.6.0"
    AUTHOR      = "Rickard Längkvist"
    COPYRIGHT   = "Copyright (c) %d %s" % (datetime.now().year, "Rickard Längkvist")
    TAB_NAME    = "Galleri"

    # -- Konfiguration -----------------------------------------
    CONFIG_FILENAME = "gallery_settings.json"
    SORT_FILENAME   = ".gallery_sort.json"
    MAX_HISTORY     = 50

    # -- Bildformat --------------------------------------------
    IMAGE_FORMATS = {
        ".jpg": "JPEG", ".jpeg": "JPEG",
        ".png": "PNG",  ".gif":  "GIF",
        ".webp": "WebP", ".bmp": "BMP",
        ".tiff": "TIFF", ".tif": "TIFF",
    }

    # -- Standardinstallningar ---------------------------------
    DEFAULTS = {
        "thumbnail_size":            120,
        "show_filenames":            True,
        "show_numbers":              True,
        "show_filesize":             False,
        "show_dimensions":           False,
        "confirm_delete":            True,
        "auto_save":                 True,
        "animation_enabled":         True,
        "double_click_preview":      True,
        "rotation_saves_file":       False,
        "load_last_folder_on_start": False,
        "last_folder":               "",
    }

    # -- Farger (uppdateras fran ThemeEngine, C1) --------------
    COLOR_BG      = "#1a1a2e"
    COLOR_BG_MID  = "#16213e"
    COLOR_BG_ITEM = "#252542"
    COLOR_SEL     = "#3b82f6"
    COLOR_SEL_B   = "#60a5fa"
    COLOR_ROT     = "#ec4899"
    COLOR_FG      = "#ffffff"
    COLOR_MUTED   = "#888888"

    # -- Fargkonstanter (B1/C1: tema-styrbara) -----------------
    COLOR_ACCENT      = "#4a90d9"
    COLOR_GREEN       = "#22c55e"
    COLOR_GREEN_DARK  = "#059669"
    COLOR_RED         = "#dc2626"
    COLOR_ORANGE      = "#f59e0b"
    COLOR_PURPLE      = "#7c3aed"
    COLOR_CYAN        = "#0891b2"
    COLOR_PINK        = "#ec4899"
    COLOR_GRAY_BTN    = "#4b5563"
    COLOR_GRAY_MID    = "#6b7280"
    COLOR_DRAG        = "#4ade80"
    COLOR_DRAG_FG     = "#000000"
    COLOR_THUMB_BG    = "#1a1a1a"
    COLOR_BTN_FG      = "#ffffff"
    COLOR_TOOLTIP_BG  = "#222222"
    COLOR_TOOLTIP_FG  = "#e2e8f0"

    # -- Tema-nyckelmappning (C1) ------------------------------
    _THEME_KEYS = {
        "COLOR_BG":          "bg",
        "COLOR_BG_MID":      "surface_alt",
        "COLOR_BG_ITEM":     "card_bg",
        "COLOR_SEL":         "selection_bg",
        "COLOR_SEL_B":       "accent_hover",
        "COLOR_ROT":         "warning",
        "COLOR_FG":          "fg",
        "COLOR_MUTED":       "muted",
        "COLOR_BTN_FG":      "selection_fg",
        "COLOR_ACCENT":      "accent",
        "COLOR_GREEN":       "success",
        "COLOR_GREEN_DARK":  "success",
        "COLOR_RED":         "error",
        "COLOR_ORANGE":      "warning",
        "COLOR_PURPLE":      "accent_active",
        "COLOR_CYAN":        "info",
        "COLOR_PINK":        "warning",
        "COLOR_GRAY_BTN":    "button_bg",
        "COLOR_GRAY_MID":    "button_bg",
        "COLOR_DRAG":        "success",
        "COLOR_DRAG_FG":     "inverse_text",
        "COLOR_THUMB_BG":    "bg_secondary",
        "COLOR_TOOLTIP_BG":  "tooltip_bg",
        "COLOR_TOOLTIP_FG":  "tooltip_fg",
    }

    # ==========================================================================
    # INITIERING
    # ==========================================================================

    def init(self, app) -> None:
        """
        Initialisera plugin och skapa tabb.

        Steg:
          1. Initiera state
          2. Ladda tema-farger (C1)
          3. Ladda installningar
          4. Bygg UI
          5. Registrera i context
          6. Registrera tema-callback
          7. Autostart (om installt)
        """
        self.app       = app
        self.is_active = True

        # -- State ---------------------------------------------
        self.thumbnails          = {}
        self.image_files         = []
        self.filtered_files      = []
        self.selected_indices    = set()
        self.last_clicked_index  = None
        self.current_folder      = None
        self.item_widgets        = {}
        self.cols                = 6
        self.image_rotations     = {}

        # Drag & drop
        self.drag_start_index    = None
        self.drag_start_pos      = None
        self.is_dragging         = False
        self.drop_target_index   = None
        self.drag_threshold      = 8
        self._pending_toggle     = None

        # Undo/Redo
        self.history             = []
        self.history_index       = -1
        self.sort_changed        = False

        # Debounce
        self._zoom_after_id      = None
        self._resize_after_id    = None   # v2.6.0: reflow vid storleksandring

        # -- Tema-omstylingslistor (C1) ------------------------
        self._panels  = []   # ramar/LabelFrames med bg=COLOR_BG
        self._buttons = []   # (widget, bg-attributnamn)
        self._labels  = []   # (widget, fg-attributnamn)
        self._scales  = []   # tk.Scale-widgets

        # -- Tema-farger (C1) ----------------------------------
        self._load_theme_colors()

        # -- Installningar -------------------------------------
        self.settings = self._load_settings()

        # -- Bygg UI -------------------------------------------
        tab_manager = app.context.get("_tab_manager")
        if tab_manager:
            gallery_frame = tab_manager.add_tab(
                "gallery", "Bildgalleri"
            )
        else:
            gallery_frame = tk.Frame(
                app.main_frame, bg=self.COLOR_BG
            )
            gallery_frame.pack(fill=tk.BOTH, expand=True)

        if gallery_frame:
            self._build_ui(gallery_frame)
            self._create_context_menu()
            self._bind_keyboard_shortcuts()
        else:
            self.log("FEL", "Kunde inte skapa galleri-tabb")
            return

        # -- Registrera ----------------------------------------
        app.context["_gallery_view"]      = self
        app.context["get_gallery_images"] = self.get_sorted_images

        # -- Tema-lyssnare (C1) --------------------------------
        self.register_theme_callback()

        # -- Autostart -----------------------------------------
        if self.settings.get("load_last_folder_on_start", False):
            last = self.settings.get("last_folder", "")
            if last and Path(last).exists():
                self.log("INFO", "Autostart: %s" % Path(last).name)
                self.safe_after(
                    500, lambda: self._load_images_from_folder(Path(last))
                )

        self.log("OK", "+ %s v%s" % (self.PLUGIN_NAME, self.VERSION))

    def _load_settings(self) -> dict:
        """Ladda config/gallery_settings.json med DEFAULTS som fallback."""
        data  = self.DEFAULTS.copy()
        saved = self.load_config(self.CONFIG_FILENAME, default={})
        data.update(saved)
        return data

    def _save_settings(self) -> None:
        """Spara installningar atomiskt."""
        self.save_config(self.CONFIG_FILENAME, self.settings)

    # ==========================================================================
    # TEMA-FARGER (C1)
    # ==========================================================================

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
                current   = getattr(self, attr, None)
                fallback  = current if current else "#888888"
                setattr(self, attr, te.get_color(key, fallback))
        except Exception as e:
            self.log("FEL", "Tema-farger kunde inte laddas: %s" % e)

    def _restyle_all(self) -> None:
        """
        Applicera aktuella farger pa alla befintliga widgets
        (paneler, knappar, labels, skalor, canvas, drag-remsa).
        """
        if not self.is_active:
            return
        try:
            # -- Paneler (ramar + LabelFrames) -----------------
            alive = []
            for w in self._panels:
                if self.widget_exists(w):
                    try:
                        w.configure(bg=self.COLOR_BG)
                    except Exception:
                        pass
                    if isinstance(w, tk.LabelFrame):
                        try:
                            w.configure(fg=self.COLOR_FG)
                        except Exception:
                            pass
                    alive.append(w)
            self._panels = alive

            # -- Knappar ---------------------------------------
            alive = []
            for btn, bg_attr in self._buttons:
                if self.widget_exists(btn):
                    try:
                        b = getattr(self, bg_attr, "#4b5563")
                        btn.configure(
                            bg=b,
                            fg=self.COLOR_BTN_FG,
                            activebackground=self._darken(b),
                            activeforeground=self.COLOR_BTN_FG,
                        )
                    except Exception:
                        pass
                    alive.append((btn, bg_attr))
            self._buttons = alive

            # -- Labels ----------------------------------------
            alive = []
            for lbl, fg_attr in self._labels:
                if self.widget_exists(lbl):
                    try:
                        lbl.configure(
                            bg=self.COLOR_BG,
                            fg=getattr(self, fg_attr, "#888888"),
                        )
                    except Exception:
                        pass
                    alive.append((lbl, fg_attr))
            self._labels = alive

            # -- Skalor ----------------------------------------
            alive = []
            for sc in self._scales:
                if self.widget_exists(sc):
                    try:
                        sc.configure(
                            bg=self.COLOR_BG,
                            fg=self.COLOR_FG,
                            troughcolor=self.COLOR_BG_MID,
                        )
                    except Exception:
                        pass
                    alive.append(sc)
            self._scales = alive

            # -- Canvas / galleri-yta --------------------------
            for w in (
                getattr(self, "canvas", None),
                getattr(self, "inner_frame", None),
            ):
                if self.widget_exists(w):
                    try:
                        w.configure(bg=self.COLOR_BG)
                    except Exception:
                        pass

            # -- Drag-remsa ------------------------------------
            if self.widget_exists(self._drag_info_frame):
                try:
                    self._drag_info_frame.configure(bg=self.COLOR_DRAG)
                except Exception:
                    pass
            if self.widget_exists(self._drag_info_label):
                try:
                    self._drag_info_label.configure(
                        bg=self.COLOR_DRAG,
                        fg=self.COLOR_DRAG_FG,
                    )
                except Exception:
                    pass
            if self.widget_exists(self._drop_indicator):
                try:
                    self._drop_indicator.configure(bg=self.COLOR_DRAG)
                except Exception:
                    pass

            # -- Galleri-items (rita om med nya farger) --------
            if self.image_files:
                self.refresh_gallery()
            else:
                self._show_instructions()
        except Exception:
            pass

    def on_theme_changed(self, event=None) -> None:
        """
        Ladda nya farger fran ThemeEngine och applicera dem
        pa alla befintliga widgets utan omstart.
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

    # ==========================================================================
    # UI-BYGGANDE
    # ==========================================================================

    def _build_ui(self, parent: tk.Widget) -> None:
        """Bygg hela granssnittet."""
        self._build_toolbar1(parent)
        self._build_toolbar2(parent)
        self._build_toolbar3(parent)
        self._build_drag_info(parent)
        self._build_gallery_canvas(parent)
        self._build_statusbar(parent)
        self._show_instructions()

    def _build_toolbar1(self, parent: tk.Widget) -> None:
        """Atgarder / Markera / Sortera / Raknare."""
        bg  = self.COLOR_BG
        bar = tk.Frame(parent, bg=bg)
        bar.pack(fill=tk.X, pady=(5, 2), padx=5)
        self._panels.append(bar)

        # Atgarder
        af = tk.LabelFrame(
            bar, text="Atgarder", bg=bg, fg=self.COLOR_FG,
            font=("Segoe UI", 8), padx=3, pady=2
        )
        af.pack(side=tk.LEFT, padx=(0, 6))
        self._panels.append(af)
        self._btn(af, "Oppna mapp", self.load_images,
                  bg="COLOR_SEL", bold=True)
        from .export_editor import open_editor
        self._btn(af, "Öppna export", lambda: open_editor(self.app),
                  bg="COLOR_SEL", tooltip="Redigera en exporterad gallerimapp")
        self.generate_btn = self._btn(
            af, "Generera HTML", self.generate_html,
            bg="COLOR_GREEN", bold=True, state=tk.DISABLED
        )
        self._btn(af, "R", self.refresh_gallery, bg="COLOR_GRAY_MID",
                  tooltip="Uppdatera (F5)", width=3)

        # Markera
        sf = tk.LabelFrame(
            bar, text="Markera", bg=bg, fg=self.COLOR_FG,
            font=("Segoe UI", 8), padx=3, pady=2
        )
        sf.pack(side=tk.LEFT, padx=(0, 6))
        self._panels.append(sf)
        self._btn(sf, "Alla",      lambda: self.select_all(None),
                  tooltip="Ctrl+A")
        self._btn(sf, "Inga",      lambda: self.clear_selection(None),
                  tooltip="Escape")
        self._btn(sf, "Invertera", self.invert_selection, width=7)
        self._btn(sf, "Varannan",  self.select_every_other, width=7)

        # Sortera
        sof = tk.LabelFrame(
            bar, text="Sortera", bg=bg, fg=self.COLOR_FG,
            font=("Segoe UI", 8), padx=3, pady=2
        )
        sof.pack(side=tk.LEFT, padx=(0, 6))
        self._panels.append(sof)
        for label, cmd, tip in [
            ("A-O",  self.sort_az,       None),
            ("O-A",  self.sort_za,       None),
            ("Dat",  self.sort_date,     "Datum"),
            ("Strl", self.sort_size,     "Storlek"),
            ("Slmp", self.sort_random,   "Slumpa"),
            ("Vand", self.reverse_order, "Vand"),
        ]:
            self._btn(sof, label, cmd, bg="COLOR_PURPLE", tooltip=tip)

        # Raknare
        cf = tk.Frame(bar, bg=bg)
        cf.pack(side=tk.RIGHT, padx=5)
        self._panels.append(cf)
        self.selected_label = tk.Label(
            cf, text="0 valda",
            bg=bg, fg=self.COLOR_ACCENT,
            font=("Segoe UI", 10, "bold"),
        )
        self.selected_label.pack(side=tk.RIGHT, padx=5)
        self._labels.append((self.selected_label, "COLOR_ACCENT"))
        av_lbl = tk.Label(cf, text="av", bg=bg, fg=self.COLOR_MUTED,
                          font=("Segoe UI", 9))
        av_lbl.pack(side=tk.RIGHT)
        self._labels.append((av_lbl, "COLOR_MUTED"))
        self.count_label = tk.Label(
            cf, text="0",
            bg=bg, fg=self.COLOR_FG,
            font=("Segoe UI", 10, "bold"),
        )
        self.count_label.pack(side=tk.RIGHT, padx=5)
        self._labels.append((self.count_label, "COLOR_FG"))
        self.save_indicator = tk.Label(
            cf, text="", bg=bg, fg=self.COLOR_MUTED,
            font=("Segoe UI", 9),
        )
        self.save_indicator.pack(side=tk.RIGHT, padx=10)
        self._labels.append((self.save_indicator, "COLOR_MUTED"))

    def _build_toolbar2(self, parent: tk.Widget) -> None:
        """Flytta / Rotera / Redigera / Visa."""
        bg  = self.COLOR_BG
        bar = tk.Frame(parent, bg=bg)
        bar.pack(fill=tk.X, pady=(0, 2), padx=5)
        self._panels.append(bar)

        # Flytta
        mf = tk.LabelFrame(
            bar, text="Flytta markerade", bg=bg, fg=self.COLOR_FG,
            font=("Segoe UI", 8), padx=3, pady=2
        )
        mf.pack(side=tk.LEFT, padx=(0, 6))
        self._panels.append(mf)
        for label, cmd, tip in [
            ("Upp",   self.move_up,        "Alt+Up"),
            ("Ner",   self.move_down,      "Alt+Down"),
            ("Forst", self.move_to_top,    "Ctrl+Home"),
            ("Sist",  self.move_to_bottom, "Ctrl+End"),
        ]:
            self._btn(mf, label, cmd, bg="COLOR_CYAN", tooltip=tip)

        # Rotera
        rf = tk.LabelFrame(
            bar, text="Rotera", bg=bg, fg=self.COLOR_FG,
            font=("Segoe UI", 8), padx=3, pady=2
        )
        rf.pack(side=tk.LEFT, padx=(0, 6))
        self._panels.append(rf)
        for label, cmd, tip in [
            ("V 90",  self.rotate_left,    "Ctrl+L"),
            ("H 90",  self.rotate_right,   "Ctrl+R"),
            ("180",   self.rotate_180,     "Ctrl+U"),
            ("Spara", self.save_rotations, "Spara till disk"),
        ]:
            self._btn(rf, label, cmd, bg="COLOR_PINK", tooltip=tip)

        # Redigera
        ef = tk.LabelFrame(
            bar, text="Redigera", bg=bg, fg=self.COLOR_FG,
            font=("Segoe UI", 8), padx=3, pady=2
        )
        ef.pack(side=tk.LEFT, padx=(0, 6))
        self._panels.append(ef)
        self._btn(ef, "Ta bort",
                  lambda: self.delete_selected(None),
                  bg="COLOR_RED", tooltip="Delete")
        self._btn(ef, "Angra",  self.undo, tooltip="Ctrl+Z")
        self._btn(ef, "Gor om", self.redo, tooltip="Ctrl+Y")

        # Visa
        vf = tk.LabelFrame(
            bar, text="Visa", bg=bg, fg=self.COLOR_FG,
            font=("Segoe UI", 8), padx=3, pady=2
        )
        vf.pack(side=tk.LEFT, padx=(0, 6))
        self._panels.append(vf)
        self._btn(vf, "Visa", self.preview_selected,
                  bg="COLOR_GREEN_DARK", tooltip="Enter")
        self._btn(vf, "Mapp", self.show_in_folder,
                  bg="COLOR_GREEN_DARK", tooltip="Visa i mappen")
        self._btn(vf, "Inst.", self.show_settings_dialog,
                  width=4, tooltip="Installningar")

        # Spara-knapp
        self._btn(bar, "Spara ordning",
                  self.save_sort_order,
                  bg="COLOR_ORANGE", tooltip="Ctrl+S", side=tk.RIGHT)

    def _build_toolbar3(self, parent: tk.Widget) -> None:
        """Sok / Filter / Zoom."""
        bg  = self.COLOR_BG
        bar = tk.Frame(parent, bg=bg)
        bar.pack(fill=tk.X, pady=(0, 5), padx=5)
        self._panels.append(bar)

        # Sok
        sf = tk.LabelFrame(
            bar, text="Sok", bg=bg, fg=self.COLOR_FG,
            font=("Segoe UI", 8), padx=3, pady=2
        )
        sf.pack(side=tk.LEFT, padx=(0, 6))
        self._panels.append(sf)
        self._search_var = tk.StringVar()
        self._search_var.trace_add("write", self._on_search_changed)
        self.search_entry = ttk.Entry(
            sf, textvariable=self._search_var, width=20
        )
        self.search_entry.pack(side=tk.LEFT, padx=2)
        self._btn(sf, "X", self.clear_search, bg="COLOR_GRAY_BTN", width=2)

        # Filter
        ff = tk.LabelFrame(
            bar, text="Filter", bg=bg, fg=self.COLOR_FG,
            font=("Segoe UI", 8), padx=3, pady=2
        )
        ff.pack(side=tk.LEFT, padx=(0, 6))
        self._panels.append(ff)
        self._filter_var = tk.StringVar(value="Alla")
        fcb = ttk.Combobox(
            ff, textvariable=self._filter_var,
            values=["Alla", "JPEG", "PNG", "GIF", "WebP", "Andra"],
            state="readonly", width=8,
        )
        fcb.pack(side=tk.LEFT, padx=2)
        fcb.bind("<<ComboboxSelected>>", self._on_filter_changed)

        # Zoom
        zf = tk.LabelFrame(
            bar, text="Storlek", bg=bg, fg=self.COLOR_FG,
            font=("Segoe UI", 8), padx=3, pady=2
        )
        zf.pack(side=tk.LEFT, padx=(0, 6))
        self._panels.append(zf)
        minus_lbl = tk.Label(zf, text="-", bg=bg, fg=self.COLOR_MUTED,
                             font=("Segoe UI", 9))
        minus_lbl.pack(side=tk.LEFT)
        self._labels.append((minus_lbl, "COLOR_MUTED"))
        self._zoom_var = tk.IntVar(
            value=self.settings.get("thumbnail_size", 120)
        )
        zoom_scale = tk.Scale(
            zf, from_=60, to=200,
            variable=self._zoom_var, orient=tk.HORIZONTAL,
            length=100,
            bg=bg, fg=self.COLOR_FG,
            troughcolor=self.COLOR_BG_MID,
            highlightthickness=0,
            showvalue=False,
            command=self._on_zoom_changed,
        )
        zoom_scale.pack(side=tk.LEFT, padx=2)
        self._scales.append(zoom_scale)
        plus_lbl = tk.Label(zf, text="+", bg=bg, fg=self.COLOR_MUTED,
                            font=("Segoe UI", 9))
        plus_lbl.pack(side=tk.LEFT)
        self._labels.append((plus_lbl, "COLOR_MUTED"))
        self._zoom_label = tk.Label(
            zf, text="%dpx" % self._zoom_var.get(),
            bg=bg, fg=self.COLOR_MUTED,
            font=("Segoe UI", 8), width=5,
        )
        self._zoom_label.pack(side=tk.LEFT, padx=4)
        self._labels.append((self._zoom_label, "COLOR_MUTED"))

        # Progress
        self._loading_label = tk.Label(
            bar, text="", bg=bg, fg=self.COLOR_MUTED,
            font=("Segoe UI", 8),
        )
        self._loading_label.pack(side=tk.RIGHT, padx=4)
        self._labels.append((self._loading_label, "COLOR_MUTED"))
        self._loading_bar = ttk.Progressbar(
            bar, length=100, mode="determinate"
        )

    def _build_drag_info(self, parent: tk.Widget) -> None:
        """Gron info-remsa som visas under drag."""
        self._drag_info_frame = tk.Frame(parent, bg=self.COLOR_DRAG, height=0)
        self._drag_info_label = tk.Label(
            self._drag_info_frame, text="",
            bg=self.COLOR_DRAG, fg=self.COLOR_DRAG_FG,
            font=("Segoe UI", 10, "bold"), padx=10, pady=3,
        )
        self._drag_info_label.pack()

    def _build_gallery_canvas(self, parent: tk.Widget) -> None:
        """Canvas med scrollbars for thumbnail-grid."""
        bg = self.COLOR_BG
        container = tk.Frame(parent, bg=bg)
        container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self._panels.append(container)

        vbar = ttk.Scrollbar(container, orient=tk.VERTICAL)
        hbar = ttk.Scrollbar(container, orient=tk.HORIZONTAL)
        vbar.pack(side=tk.RIGHT,  fill=tk.Y)
        hbar.pack(side=tk.BOTTOM, fill=tk.X)

        self.canvas = tk.Canvas(
            container, bg=bg, highlightthickness=0,
            yscrollcommand=vbar.set,
            xscrollcommand=hbar.set,
        )
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        vbar.config(command=self.canvas.yview)
        hbar.config(command=self.canvas.xview)

        self.inner_frame = tk.Frame(self.canvas, bg=bg)
        self._canvas_window = self.canvas.create_window(
            (0, 0), window=self.inner_frame, anchor=tk.NW
        )

        self._drop_indicator = tk.Frame(
            self.inner_frame, bg=self.COLOR_DRAG, width=4
        )

        self.inner_frame.bind("<Configure>", self._on_frame_configure)
        self.canvas.bind("<Configure>",      self._on_canvas_configure)
        self.canvas.bind("<Button-1>",       self._on_canvas_click)

        # Mushjul via Enter/Leave
        self.canvas.bind("<Enter>",   self._bind_wheel)
        self.canvas.bind("<Leave>",   self._unbind_wheel)
        self.canvas.bind("<Button-4>",
                         lambda e: self._scroll_canvas(-3))
        self.canvas.bind("<Button-5>",
                         lambda e: self._scroll_canvas(3))

    def _build_statusbar(self, parent: tk.Widget) -> None:
        """Statusrad langst ned."""
        bg  = self.COLOR_BG
        bar = tk.Frame(parent, bg=bg)
        bar.pack(fill=tk.X, pady=2, padx=5)
        self._panels.append(bar)

        self.status_label = tk.Label(
            bar,
            text="Redo - Klicka Oppna mapp for att borja",
            bg=bg, fg=self.COLOR_MUTED,
            font=("Segoe UI", 9),
        )
        self.status_label.pack(side=tk.LEFT)
        self._labels.append((self.status_label, "COLOR_MUTED"))

        self.folder_label = tk.Label(
            bar, text="", bg=bg, fg=self.COLOR_ACCENT,
            font=("Segoe UI", 8),
        )
        self.folder_label.pack(side=tk.RIGHT)
        self._labels.append((self.folder_label, "COLOR_ACCENT"))

        self._help_label = tk.Label(
            bar, text="", bg=bg, fg=self.COLOR_MUTED,
            font=("Segoe UI", 8),
        )
        self._help_label.pack(side=tk.RIGHT, padx=20)
        self._labels.append((self._help_label, "COLOR_MUTED"))

    def _btn(
        self, parent, text: str, command,
        bg: str    = "COLOR_GRAY_BTN",
        fg: str    = None,
        bold: bool = False,
        width: int = None,
        tooltip: str = None,
        state      = tk.NORMAL,
        side: str  = tk.LEFT,
    ) -> tk.Button:
        """
        Intern knapp-fabrik med hover och tooltip.

        bg ar ett ATTRIBUTNAMN (strang) - vardet hamtas via
        getattr() sa att knappen alltid foljer aktuella
        tema-farger och kan omstylas vid tema-byte (C1).
        """
        if fg is None:
            fg_value = self.COLOR_BTN_FG
        else:
            fg_value = fg
        bg_value = getattr(self, bg, "#4b5563")
        hover    = self._darken(bg_value)
        kwargs = dict(
            text=text, command=command,
            bg=bg_value, fg=fg_value,
            activebackground=hover, activeforeground=fg_value,
            font=("Segoe UI", 8, "bold" if bold else "normal"),
            cursor="hand2", relief=tk.FLAT, state=state,
        )
        if width:
            kwargs["width"] = width
        btn = tk.Button(parent, **kwargs)
        btn.pack(side=side, padx=1, pady=1)
        btn.bind("<Enter>", lambda e: btn.config(bg=hover))
        btn.bind("<Leave>", lambda e: btn.config(bg=bg_value))
        self._buttons.append((btn, bg))
        if tooltip:
            self._add_tooltip(btn, tooltip)
        return btn

    @staticmethod
    def _darken(hex_color: str, factor: float = 0.78) -> str:
        """Morkna hex-farg for hover-effekt."""
        try:
            h = hex_color.lstrip("#")
            r = max(0, int(int(h[0:2], 16) * factor))
            g = max(0, int(int(h[2:4], 16) * factor))
            b = max(0, int(int(h[4:6], 16) * factor))
            return "#%02x%02x%02x" % (r, g, b)
        except Exception:
            return hex_color

    def _add_tooltip(self, widget: tk.Widget, text: str) -> None:
        """Enkel tooltip (2.5s) med tema-farger (C4).

        v2.6.0: forhindrar Toplevel-ackumulering vid snabbt hover
        - en befintlig tooltip forstors innan en ny skapas och den
        schemalagda doldningen avbryts (efter-cancel) sa ingen
        gammal tooltip lamnas kvar.
        """
        tip_ref = [None]
        hide_id = [None]

        def _hide(event=None):
            if hide_id[0] is not None:
                try:
                    widget.after_cancel(hide_id[0])
                except Exception:
                    pass
                hide_id[0] = None
            if tip_ref[0]:
                try:
                    tip_ref[0].destroy()
                except Exception:
                    pass
                tip_ref[0] = None

        def _show(event):
            if not self.is_active:
                return
            if tip_ref[0]:
                try:
                    tip_ref[0].destroy()
                except Exception:
                    pass
                tip_ref[0] = None
            tip = tk.Toplevel(widget)
            tip.wm_overrideredirect(True)
            tip.wm_geometry(
                "+%d+%d" % (event.x_root + 12, event.y_root + 12)
            )
            tk.Label(
                tip, text=text,
                bg=self.COLOR_TOOLTIP_BG, fg=self.COLOR_TOOLTIP_FG,
                font=("Segoe UI", 9), padx=8, pady=4,
                relief="solid", borderwidth=1,
            ).pack()
            tip_ref[0] = tip
            hide_id[0] = widget.after(2500, _hide)

        widget.bind("<Enter>", _show)
        widget.bind("<Leave>", _hide)

    def _bind_wheel(self, event=None) -> None:
        if self.widget_exists(self.canvas):
            self.canvas.bind("<MouseWheel>",         self._on_wheel)
            self.canvas.bind("<Control-MouseWheel>", self._on_ctrl_wheel)

    def _unbind_wheel(self, event=None) -> None:
        if self.widget_exists(self.canvas):
            try:
                self.canvas.unbind("<MouseWheel>")
                self.canvas.unbind("<Control-MouseWheel>")
            except Exception:
                pass

    def _on_wheel(self, event) -> None:
        if sys.platform == "win32":
            units = -3 if event.delta > 0 else 3
        elif sys.platform == "darwin":
            units = -1 if event.delta > 0 else 1
        else:
            units = -3 if event.num == 4 else 3
        self._scroll_canvas(units)

    def _on_ctrl_wheel(self, event) -> None:
        """Ctrl+scroll -> zoom."""
        delta = 10 if event.delta > 0 else -10
        new   = max(60, min(200, self._zoom_var.get() + delta))
        self._zoom_var.set(new)
        self._on_zoom_changed(None)

    def _scroll_canvas(self, units: int) -> None:
        if self.widget_exists(self.canvas):
            try:
                self.canvas.yview_scroll(units, "units")
            except tk.TclError:
                pass

    def _on_zoom_changed(self, event=None) -> None:
        size = self._zoom_var.get()
        self.safe_widget_config(self._zoom_label, text="%dpx" % size)
        self.settings["thumbnail_size"] = size
        if self._zoom_after_id:
            try:
                self.app.after_cancel(self._zoom_after_id)
            except Exception:
                pass
        self._zoom_after_id = self.safe_after(300, self._apply_zoom)

    def _apply_zoom(self) -> None:
        if self.image_files:
            self._load_thumbnails()
            self.refresh_gallery()

    def load_images(self) -> None:
        """Oppna mappval-dialog och ladda bilder."""
        settings = self.app.context.get("_settings")
        folder   = None
        if settings and hasattr(settings, "folder_var"):
            folder = settings.folder_var.get()
        if not folder:
            folder = filedialog.askdirectory(title="Valj bildmapp")
            if folder and settings and hasattr(settings, "folder_var"):
                settings.folder_var.set(folder)
        if not folder:
            return
        self.settings["last_folder"] = str(folder)
        self._save_settings()
        self._load_images_from_folder(Path(folder))

    def _load_images_from_folder(self, folder: Path) -> None:
        """Ladda bilder fran en specifik mapp (intern)."""
        self.current_folder     = folder
        self.selected_indices   = set()
        self.last_clicked_index = None
        self.history            = []
        self.history_index      = -1
        self.item_widgets       = {}
        self.image_rotations    = {}

        self._set_status("Laddar bilder...")
        self.safe_widget_config(self.folder_label, text=str(folder))
        try:
            self.app.update_idletasks()
        except Exception:
            pass

        try:
            (folder / "Removed").mkdir(exist_ok=True)
        except Exception:
            pass

        # Hitta bildfiler
        all_files = [
            f for f in folder.iterdir()
            if f.is_file()
            and f.suffix.lower() in self.IMAGE_FORMATS
            and not f.name.startswith(".")
            and "Removed" not in str(f)
        ]

        if not all_files:
            self.image_files    = []
            self.filtered_files = []
            self._show_instructions()
            self._set_status("Inga bilder hittades")
            self.safe_widget_config(
                self.generate_btn, state=tk.DISABLED
            )
            return

        # Ladda sparad sortering
        saved = self._load_sort_order()
        if saved:
            order     = []
            remaining = list(all_files)
            for name in saved:
                p = folder / name
                if p in remaining:
                    order.append(p)
                    remaining.remove(p)
            order.extend(
                sorted(remaining, key=lambda x: x.name.lower())
            )
            self.image_files = order
            self._set_status(
                "%d bilder - Sparad ordning" % len(self.image_files)
            )
        else:
            self.image_files = sorted(
                all_files, key=lambda x: x.name.lower()
            )
            self._set_status(
                "%d bilder - Alfabetisk ordning" % len(self.image_files)
            )

        self.filtered_files = self.image_files.copy()
        self._save_to_history()
        self._load_thumbnails()
        self.refresh_gallery()
        self.safe_widget_config(self.generate_btn, state=tk.NORMAL)
        self._update_context()

        # Navigera till galleri-tabben
        tm = self.app.context.get("_tab_manager")
        if tm and hasattr(tm, "select_tab"):
            try:
                tm.select_tab("gallery")
            except Exception:
                pass

    def _update_rotated_thumbnail(
        self, img_path: Path, rotation: int
    ) -> None:
        """Uppdatera en enskild thumbnail med ny rotation."""
        try:
            size  = self.settings.get("thumbnail_size", 120)
            photo = self._build_photoimage(img_path, size, rotation)
            if photo is not None:
                self.thumbnails[img_path] = photo
        except Exception as e:
            self.log(
                "DEBUG",
                "Rotation-thumbnail %s: %s" % (img_path.name, e)
            )

    def refresh_gallery(self) -> None:
        """Rita om hela galleriet."""
        if not self.is_active:
            return
        for w in self.inner_frame.winfo_children():
            if w != self._drop_indicator:
                try:
                    w.destroy()
                except Exception:
                    pass
        self.item_widgets.clear()

        files = self.filtered_files
        if not files:
            if self.image_files:
                tk.Label(self.inner_frame, text="Inga bilder matchar sökningen. Rensa sök/filter för att visa alla.",
                         bg=self.COLOR_BG, fg=self.COLOR_MUTED, pady=35).pack()
                self._update_counters()
            else:
                self._show_instructions()
            return

        cw = self.canvas.winfo_width()
        if cw < 100:
            cw = 800
        from .gallery_layout import column_count
        self.cols = column_count(cw, self.settings.get("thumbnail_size", 120))

        # v2.6.0: bygg indexkarta EN gång istället for .index() per item
        # (som var O(n^2) vid stora mappar).
        orig_map = {p: k for k, p in enumerate(self.image_files)}

        for i, path in enumerate(files):
            r, c = divmod(i, self.cols)
            self._create_item(path, i, r, c, orig_map.get(path, i))

        self._update_counters()
        self._update_context()

    def _create_item(
        self, img_path: Path, index: int, row: int, col: int,
        original_index: int = None,
    ) -> None:
        """Skapa ett bild-item i galleriet."""
        if original_index is None:
            original_index = index

        is_selected = original_index in self.selected_indices
        is_rotated  = img_path in self.image_rotations

        bg     = self.COLOR_SEL     if is_selected else self.COLOR_BG_ITEM
        border = self.COLOR_SEL_B   if is_selected else (
            self.COLOR_ROT if is_rotated else self.COLOR_BG_ITEM
        )
        fg = self.COLOR_FG if is_selected else self.COLOR_MUTED

        outer = tk.Frame(self.inner_frame, bg=border, padx=3, pady=3)
        outer.grid(row=row, column=col, padx=4, pady=4, sticky="n")
        inner = tk.Frame(outer, bg=bg, padx=4, pady=4)
        inner.pack()

        # Equal image wells keep portrait/landscape cards aligned without cropping.
        size = self.settings.get("thumbnail_size", 120)
        well = tk.Frame(inner, width=size, height=size, bg=self.COLOR_THUMB_BG)
        well.pack()
        well.pack_propagate(False)
        if img_path in self.thumbnails:
            img_lbl = tk.Label(
                well, image=self.thumbnails[img_path],
                bg=self.COLOR_THUMB_BG, cursor="hand2",
            )
        else:
            img_lbl = tk.Label(
                well, text="[bild]", font=("Segoe UI", 14),
                bg=self.COLOR_THUMB_BG, fg=self.COLOR_MUTED,
                width=8, height=4, cursor="hand2",
            )
        img_lbl.pack(expand=True)
        self._add_tooltip(img_lbl, img_path.name)

        # Rotationsindikator
        if is_rotated:
            tk.Label(
                inner,
                text="R%d" % self.image_rotations[img_path],
                bg=self.COLOR_ROT, fg=self.COLOR_BTN_FG,
                font=("Segoe UI", 7, "bold"), padx=3,
            ).place(relx=1.0, rely=0, anchor="ne")

        # Events
        for ev, fn in [
            ("<Button-1>",
             lambda e, i=original_index: self._on_mouse_down(e, i)),
            ("<B1-Motion>",
             lambda e, i=original_index: self._on_mouse_move(e, i)),
            ("<ButtonRelease-1>",
             lambda e, i=original_index: self._on_mouse_up(e, i)),
            ("<Double-Button-1>",
             lambda e, i=original_index: self.preview_image_at_index(i)),
            ("<Button-3>",
             lambda e, i=original_index: self._on_right_click(e, i)),
        ]:
            img_lbl.bind(ev, fn)

        # Info-rad
        info = tk.Frame(inner, bg=bg)
        info.pack(fill=tk.X)

        check_lbl = tk.Label(
            info, text="✓" if is_selected else "",
            bg=bg, fg=self.COLOR_BTN_FG,
            font=("Segoe UI", 9, "bold"), width=2,
        )
        check_lbl.pack(side=tk.LEFT)

        num_lbl = tk.Label(
            info,
            text="#%d" % (original_index + 1)
            if self.settings.get("show_numbers") else "",
            bg=bg, fg=fg,
            font=("Segoe UI", 8, "bold"),
        )
        num_lbl.pack(side=tk.LEFT)

        fmt_color = {
            ".jpg": self.COLOR_GREEN, ".jpeg": self.COLOR_GREEN,
            ".png": self.COLOR_SEL, ".gif": self.COLOR_ORANGE,
            ".webp": self.COLOR_PURPLE,
        }.get(img_path.suffix.lower(), self.COLOR_MUTED)
        tk.Label(
            info,
            text=img_path.suffix[1:].upper(),
            bg=bg, fg=fmt_color,
            font=("Segoe UI", 7, "bold"),
        ).pack(side=tk.RIGHT)

        # Filnamn
        name_lbl = None
        if self.settings.get("show_filenames", True):
            sz    = self.settings.get("thumbnail_size", 120)
            maxc  = max(10, sz // 8)
            nm    = img_path.stem
            if len(nm) > maxc:
                nm = nm[:maxc] + "..."
            name_lbl = tk.Label(
                inner, text=nm,
                bg=bg, fg=fg,
                font=("Segoe UI", 8),
                wraplength=sz,
            )
            name_lbl.pack()
            for ev, fn in [
                ("<Button-1>",
                 lambda e, i=original_index: self._on_mouse_down(e, i)),
                ("<B1-Motion>",
                 lambda e, i=original_index: self._on_mouse_move(e, i)),
                ("<ButtonRelease-1>",
                 lambda e, i=original_index: self._on_mouse_up(e, i)),
            ]:
                name_lbl.bind(ev, fn)

        self.item_widgets[index] = {
            "outer":          outer,
            "inner":          inner,
            "img_label":      img_lbl,
            "info":           info,
            "check":          check_lbl,
            "num":            num_lbl,
            "name":           name_lbl,
            "original_index": original_index,
        }

    def _show_instructions(self) -> None:
        """Visa valkomstskarm."""
        bg = self.COLOR_BG
        for w in self.inner_frame.winfo_children():
            if w != self._drop_indicator:
                try:
                    w.destroy()
                except Exception:
                    pass
        self.item_widgets.clear()

        frame = tk.Frame(self.inner_frame, bg=bg)
        frame.pack(expand=True, pady=60)
        tk.Label(
            frame, text="[ Bildgalleri ]", font=("Segoe UI", 40),
            bg=bg, fg=self.COLOR_ACCENT,
        ).pack()
        tk.Label(
            frame, text="Bildgalleri",
            font=("Segoe UI", 22, "bold"),
            bg=bg, fg=self.COLOR_FG,
        ).pack(pady=8)

        tips = [
            ("Oppna mapp",    "Valj en mapp med bilder"),
            ("Markera",       "Klick - Ctrl+klick - Shift+klick"),
            ("Dra & slapp",   "Flytta bilder genom att dra"),
            ("Rotera",        "Ctrl+L / Ctrl+R / Ctrl+U"),
            ("Generera HTML", "Skapa webbgalleri (Ctrl+G)"),
            ("Zoom",          "Ctrl+scroll eller slider"),
        ]
        hf = tk.Frame(frame, bg=bg)
        hf.pack(pady=16)
        for title, desc in tips:
            row = tk.Frame(hf, bg=bg)
            row.pack(fill=tk.X, pady=4)
            tk.Label(row, text="%s:" % title,
                     font=("Segoe UI", 10, "bold"),
                     bg=bg, fg=self.COLOR_FG).pack(side=tk.LEFT, padx=(0, 8))
            tk.Label(row, text=desc, font=("Segoe UI", 10),
                     bg=bg, fg=self.COLOR_MUTED).pack(side=tk.LEFT)

    def _on_canvas_click(self, event) -> None:
        if event.widget == self.canvas:
            self.clear_selection(None)

    def _on_frame_configure(self, event=None) -> None:
        if self.is_active and self.widget_exists(self.canvas):
            try:
                self.canvas.configure(
                    scrollregion=self.canvas.bbox("all")
                )
            except Exception:
                pass

    def _on_canvas_configure(self, event=None) -> None:
        if not self.is_active or not event:
            return
        try:
            self.canvas.itemconfig(
                self._canvas_window, width=event.width
            )
            if self.image_files:
                sz   = self.settings.get("thumbnail_size", 120) + 30
                cols = max(1, event.width // sz)
                if cols != self.cols:
                    self.cols = cols
                    # v2.6.0: debounce omritning - live-resize avger
                    # MANGD <Configure>-events som tidigare triggade
                    # refresh_gallery() for varje event.
                    aid = self._resize_after_id
                    if aid is not None:
                        try:
                            self.app.after_cancel(aid)
                        except Exception:
                            pass
                    self._resize_after_id = self.safe_after(
                        120, self._flush_resize_refresh
                    )
        except Exception:
            pass

    def _flush_resize_refresh(self) -> None:
        """Körs när resize-debounce-tiden gått ut (v2.6.0)."""
        self._resize_after_id = None
        if self.is_active and self.image_files:
            self.refresh_gallery()

    def _open_external(self) -> None:
        if not self.selected_indices:
            return
        path = self.image_files[min(self.selected_indices)]
        try:
            if sys.platform == "win32":
                os.startfile(str(path))
            elif sys.platform == "darwin":
                subprocess.Popen(["open", str(path)])
            else:
                subprocess.Popen(["xdg-open", str(path)])
        except Exception as e:
            self.log_error("Oppna externt", e)

    def _copy_filename(self) -> None:
        if not self.selected_indices:
            return
        names = [
            self.image_files[i].name
            for i in sorted(self.selected_indices)
        ]
        try:
            self.app.clipboard_clear()
            self.app.clipboard_append("\n".join(names))
            self._set_status("Kopierade %d filnamn" % len(names))
        except Exception:
            pass

    def show_in_folder(self) -> None:
        """Oppna mapp/fil i OS-filhanterare (Popen - blockerar ej)."""
        target = (
            self.image_files[min(self.selected_indices)]
            if self.selected_indices
            else self.current_folder
        )
        if not target:
            return
        try:
            if sys.platform == "win32":
                if self.selected_indices:
                    subprocess.Popen(
                        ["explorer", "/select,", str(target)]
                    )
                else:
                    subprocess.Popen(["explorer", str(target)])
            elif sys.platform == "darwin":
                if self.selected_indices:
                    subprocess.Popen(["open", "-R", str(target)])
                else:
                    subprocess.Popen(["open", str(target)])
            else:
                folder = target.parent \
                         if self.selected_indices else target
                subprocess.Popen(["xdg-open", str(folder)])
        except Exception as e:
            self.log_error("Visa i mappen", e)

    def _set_status(self, text: str) -> None:
        self.safe_widget_config(self.status_label, text=text)

    def _update_context(self) -> None:
        """Synka bildlistan till app.context."""
        if self.image_files:
            self.app.context["gallery_images"]   = self.image_files.copy()
            self.app.context["sorted_images"]     = self.image_files.copy()
            self.app.context["gallery_order"]     = True
            self.app.context["image_rotations"]   = (
                self.image_rotations.copy()
            )

    def get_sorted_images(self) -> list:
        """Publik: returnera aktuell bildordning."""
        return self.image_files.copy()

    def generate_html(self) -> None:
        """Kor pipeline och oppna galleriet i webblasaren."""
        if not self.image_files:
            self._set_status("Inga bilder att generera")
            return

        if self.sort_changed:
            self._save_sort_silent()

        if self.image_rotations:
            if messagebox.askyesno(
                "Osparade rotationer",
                "%d osparade rotationer.\n"
                "Spara permanent till bildfilerna nu?"
                % len(self.image_rotations),
            ):
                self.save_rotations()

        self._update_context()

        try:
            self._set_status("Genererar HTML...")
            try:
                self.app.update_idletasks()
            except Exception:
                pass

            self.app.run_pipeline()

            output = self.app.context.get("output_path")
            if output and Path(output).exists():
                self._set_status("HTML genererat: %s" % output)
                if messagebox.askyesno(
                    "Klart", "Galleriet genererat!\n\nOppna i webblasare?"
                ):
                    idx = Path(output) / "index.html"
                    if idx.exists():
                        try:
                            if sys.platform == "win32":
                                subprocess.Popen(
                                    ["cmd", "/c", "start", "", str(idx)],
                                    shell=False,
                                    creationflags=(
                                        subprocess.CREATE_NO_WINDOW
                                        if hasattr(subprocess, "CREATE_NO_WINDOW")
                                        else 0
                                    ),
                                )
                            elif sys.platform == "darwin":
                                subprocess.Popen(["open", str(idx)])
                            else:
                                subprocess.Popen(["xdg-open", str(idx)])
                        except Exception as e:
                            self.log_error("Oppna webblasare", e)
            else:
                self._set_status("Pipeline klar")
        except Exception as e:
            self._set_status("Fel: %s" % e)
            self.log_error("generate_html", e)
            messagebox.showerror("Fel", str(e))

    def show_settings_dialog(self) -> None:
        """Installningsdialog med autostart-alternativ."""
        if not self.is_active:
            return
        dlg = tk.Toplevel(self.app)
        dlg.title("Galleriinstallningar")
        dlg.geometry("480x560")
        dlg.configure(bg=self.COLOR_BG)
        dlg.transient(self.app)
        dlg.grab_set()
        dlg.resizable(False, False)

        # Centrera
        try:
            dlg.update_idletasks()
            x = self.app.winfo_x() + (self.app.winfo_width()  - 480) // 2
            y = self.app.winfo_y() + (self.app.winfo_height() - 560) // 2
            dlg.geometry("+%d+%d" % (x, y))
        except Exception:
            pass

        tk.Label(
            dlg, text="Galleriinstallningar",
            font=("Segoe UI", 15, "bold"),
            bg=self.COLOR_BG, fg=self.COLOR_FG,
        ).pack(pady=16)

        body = tk.Frame(dlg, bg=self.COLOR_BG)
        body.pack(fill=tk.BOTH, expand=True, padx=30)

        # -- Checkboxar ----------------------------------------
        options = [
            ("show_filenames",
             "Visa filnamn under thumbnail"),
            ("show_numbers",
             "Visa bildnummer (#1, #2, ...)"),
            ("show_filesize",
             "Visa filstorlek"),
            ("show_dimensions",
             "Visa bilddimensioner"),
            ("confirm_delete",
             "Bekrafta innan borttagning"),
            ("auto_save",
             "Auto-spara ordning vid stangning"),
            ("animation_enabled",
             "Aktivera animationer"),
            ("double_click_preview",
             "Dubbelklick = forhandsgranska"),
            ("rotation_saves_file",
             "Rotation sparar direkt till disk"),
            # -- AUTOSTART -------------------------------------
            ("load_last_folder_on_start",
             "Ladda senaste mapp automatiskt vid start"),
        ]

        vars_dict = {}
        for key, label in options:
            var = tk.BooleanVar(
                value=self.settings.get(key, False)
            )
            vars_dict[key] = var
            if key == "load_last_folder_on_start":
                tk.Frame(body, bg=self.COLOR_BG_MID, height=1).pack(
                    fill=tk.X, pady=8
                )
            cb = tk.Checkbutton(
                body, text=label, variable=var,
                bg=self.COLOR_BG, fg=self.COLOR_FG,
                selectcolor=self.COLOR_SEL,
                activebackground=self.COLOR_BG,
                activeforeground=self.COLOR_FG,
                font=(
                    "Segoe UI", 10,
                    "bold"
                    if key == "load_last_folder_on_start"
                    else "normal"
                ),
                cursor="hand2",
            )
            cb.pack(anchor=tk.W, pady=4)
            self._labels.append((cb, "COLOR_FG"))

        # Senaste mapp (info)
        last = self.settings.get("last_folder", "")
        if last:
            short = ("..." + last[-45:]) if len(last) > 48 else last
            tk.Label(
                body,
                text="  Senaste mapp: %s" % short,
                bg=self.COLOR_BG, fg=self.COLOR_GRAY_MID,
                font=("Segoe UI", 8),
            ).pack(anchor=tk.W, pady=(0, 8))

        # Thumbnail-storlek
        tk.Frame(body, bg=self.COLOR_BG_MID, height=1).pack(
            fill=tk.X, pady=8
        )
        sz_frame = tk.Frame(body, bg=self.COLOR_BG)
        sz_frame.pack(fill=tk.X)
        tk.Label(
            sz_frame, text="Thumbnail-storlek:",
            bg=self.COLOR_BG, fg=self.COLOR_FG,
            font=("Segoe UI", 10),
        ).pack(side=tk.LEFT)
        size_var = tk.IntVar(
            value=self.settings.get("thumbnail_size", 120)
        )
        sz_lbl = tk.Label(
            sz_frame,
            text="%dpx" % size_var.get(),
            bg=self.COLOR_BG, fg=self.COLOR_ACCENT,
            font=("Segoe UI", 10, "bold"), width=6,
        )
        sz_lbl.pack(side=tk.RIGHT)
        self._labels.append((sz_lbl, "COLOR_ACCENT"))
        size_scale = tk.Scale(
            body, from_=60, to=200,
            variable=size_var, orient=tk.HORIZONTAL,
            length=340,
            bg=self.COLOR_BG, fg=self.COLOR_FG,
            troughcolor=self.COLOR_BG_MID,
            highlightthickness=0,
            showvalue=False,
            command=lambda v: sz_lbl.config(
                text="%dpx" % int(float(v))
            ),
        )
        size_scale.pack(fill=tk.X, pady=4)
        self._scales.append(size_scale)

        # Knappar
        btn_row = tk.Frame(dlg, bg=self.COLOR_BG)
        btn_row.pack(pady=16)

        def _save():
            for key, var in vars_dict.items():
                self.settings[key] = var.get()
            self.settings["thumbnail_size"] = int(size_var.get())
            self._save_settings()
            try:
                self._zoom_var.set(self.settings["thumbnail_size"])
            except Exception:
                pass
            self._apply_zoom()
            dlg.destroy()
            self._set_status("Installningar sparade")

        def _reset():
            default_true = {
                "show_filenames", "show_numbers",
                "confirm_delete", "auto_save",
                "animation_enabled", "double_click_preview",
            }
            for key, var in vars_dict.items():
                var.set(key in default_true)
            size_var.set(120)

        self._btn(btn_row, "Spara",     _save,       bg="COLOR_GREEN",
                  bold=True, side=tk.LEFT)
        self._btn(btn_row, "Avbryt",    dlg.destroy, bg="COLOR_GRAY_BTN",
                  side=tk.LEFT)
        self._btn(btn_row, "Aterstall", _reset,      bg="COLOR_ORANGE",
                  side=tk.LEFT)

    def execute(self, context: dict, log=None) -> dict:
        """Pipeline-steg: injicera bildfiler i context."""
        if (
            self.current_folder
            and self.image_files
            and self.sort_changed
        ):
            try:
                self._save_sort_silent()
            except Exception:
                pass

        if self.image_files:
            context["gallery_images"]   = self.image_files.copy()
            context["sorted_images"]    = self.image_files.copy()
            context["gallery_order"]    = True
            context["image_rotations"]  = self.image_rotations.copy()
            if log:
                log(
                    "%d bilder i galleriordning"
                    % len(self.image_files)
                )
                if self.image_rotations:
                    log(
                        "%d med rotation" % len(self.image_rotations)
                    )
        return context

    def cleanup(self) -> None:
        """Spara installningar och sortering vid avslutning."""
        if (
            self.current_folder
            and self.image_files
            and self.sort_changed
            and self.settings.get("auto_save", True)
        ):
            try:
                self._save_sort_silent()
            except Exception:
                pass
        self._save_settings()
        self.is_active = False
        # v2.6.0: avbryt schemalagda timers sa inga callbacks kor
        # efter stangning.
        for attr in (
            "_zoom_after_id", "_resize_after_id",
            "_refresh_after_id",
        ):
            aid = getattr(self, attr, None)
            if aid is not None:
                try:
                    self.app.after_cancel(aid)
                except Exception:
                    pass
                setattr(self, attr, None)

    def log(self, level: str, message: str) -> None:
        """Logga via advanced_logger om tillganglig. Ingen print()."""
        try:
            logger = self.app.context.get("_logger")
            if logger and hasattr(logger, "log"):
                logger.log(level, message)
        except Exception:
            pass

    def log_error(self, message: str, exc: Exception = None) -> None:
        """Logga ett fel med valfritt undantag."""
        full = "%s: %s" % (message, exc) if exc else message
        self.log("FEL", full)

    def load_config(self, filename: str, default=None):
        """
        Ladda JSON fran config/-mappen (A10).

        Anvander helpers.get_config_path() om tillgangligt,
        annars projektrotens config/.
        """
        try:
            if _HAS_HELPERS:
                cfg = get_config_path() / filename
            else:
                cfg = app_paths.config_dir() / filename
            if cfg.exists():
                return json.loads(cfg.read_text(encoding="utf-8"))
        except Exception as e:
            self.log("DEBUG", "load_config(%s): %s" % (filename, e))
        return default if default is not None else {}

    def save_config(self, filename: str, data: dict) -> None:
        """
        Spara JSON till config/-mappen (A9 + A10).

        Monster: mkstemp -> fdopen -> flush -> fsync -> os.replace.
        """
        tmp_path = None
        try:
            if _HAS_HELPERS:
                config_dir = get_config_path()
            else:
                config_dir = app_paths.config_dir()
            config_dir.mkdir(parents=True, exist_ok=True)

            cfg = config_dir / filename
            fd, tmp_str = tempfile.mkstemp(
                dir=config_dir,
                prefix=".%s_" % cfg.stem,
                suffix=".tmp",
            )
            tmp_path = Path(tmp_str)

            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
                f.flush()
                os.fsync(f.fileno())   # A9

            os.replace(tmp_path, cfg)
        except Exception as e:
            if tmp_path and tmp_path.exists():
                try:
                    tmp_path.unlink()
                except OSError:
                    pass
            self.log("DEBUG", "save_config(%s): %s" % (filename, e))

    def widget_exists(self, widget) -> bool:
        """Returnerar True om widget finns och inte ar forstord."""
        try:
            return bool(widget and widget.winfo_exists())
        except tk.TclError:
            return False

    def safe_widget_config(self, widget, **kwargs) -> None:
        """Konfigurera widget tyst om den inte finns."""
        if self.widget_exists(widget):
            try:
                widget.config(**kwargs)
            except tk.TclError:
                pass

    def safe_after(self, ms: int, func):
        """Schemalagg func via app.after() om is_active."""
        if self.is_active:
            try:
                return self.app.after(ms, func)
            except Exception:
                pass
        return None
