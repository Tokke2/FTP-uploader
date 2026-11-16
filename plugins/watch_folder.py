#!/usr/bin/env python3
# ============================================================
# Plugin: Mappovervakare
# ============================================================
# FIL:       plugins/watch_folder.py
# PLATS:     plugins/ (ftp_gallery_uploader/plugins/watch_folder.py)
# Syfte:     Overvaka flera mappar och auto-lagg till nya bilder
# PLUGIN_NAME: "Mappovervakare"
# PRIORITY:  6
# VERSION:   2.4.0
# AUTHOR:    Rickard Längkvist
# COPYRIGHT: Copyright (c) <år> Rickard Längkvist (dynamiskt år,
#            se COPYRIGHT-konstanten nedan)
#
# ÄNDRINGAR v2.3.0 → v2.4.0 (snabbhet + minne, icke-brytande):
#   [P]       update_stats(): skannar inte langre HELA loggtexten pa
#             varje filhandelse (get("1.0", END) + 3x .count()).
#             Ersatt med inkrementella rakare i minnet (_stats) som
#             okar i _handle_file_event och aterstalls av clear_log().
#             Stor vinst vid manga handelser och lang logg.
#   [P]       ImageFileHandler._last_event_time: begransad + rensas
#             (pruning av aldre an 30 s) sa att dict inte vaxer
#             obegransat under langa sessioner (minneslack).
#   [K]       Inga API-namn eller beteenden andras; statistik- och
#             logg-visning identisk.
#
# ÄNDRINGAR v2.2.0 → v2.3.0 (DESIGN-SYSTEM-integration, spec v4.6.0):
#   [C1]      Fargerna hamtas fran ThemeEngine-designsystemet
#             (helpers v1.3.0, 58 nycklar/tema) via _THEME_KEYS:
#               COLOR_BG/COLOR_BG_MID      <- "bg"/"surface_alt"
#               COLOR_FG/COLOR_MUTED       <- "fg"/"muted"
#               COLOR_ACTIVE/COLOR_INACTIVE<- "success"/"muted"
#               COLOR_ERROR/COLOR_WARNING  <- "error"/"warning"
#               COLOR_INFO/COLOR_FOLDER    <- "info"/"accent"
#               COLOR_TIME                 <- "muted"
#               COLOR_LIST_BG (NY)         <- "bg_secondary"
#               COLOR_LIST_SEL (NY)        <- "accent_soft"
#               COLOR_LOG_BG (NY)          <- "bg_secondary"
#               COLOR_LOG_FG (NY)          <- "text_secondary"
#   [B1]      Hardkodade hex-farger i Listbox/Text ersatta:
#             listbox bg "#1e1e1e" -> COLOR_LIST_BG,
#             selectbackground "#264f78" -> COLOR_LIST_SEL,
#             logg bg "#1e1e1e" -> COLOR_LOG_BG,
#             logg fg "#c9d1d9" -> COLOR_LOG_FG
#   [C1]      _load_theme_colors() + _restyle_all() +
#             on_theme_changed() + register_theme_callback():
#             alla widgets (inkl. listbox, logg-text med taggar,
#             statuslampa) uppdateras vid tema-byte
#   [C1]      super().init(app) tillagt - satter is_active (kravs
#             for _restyle_all) och app-referens enligt kontrakt
#   [C1]      _setup_log_tags(): loggens fargtaggar satts fran
#             aktuella tema-farger (flyttad ur _build_log_panel)
#   [C1]      Nya hjälpare: _ensure_theme_lists, _reg_panels,
#             _reg_labels, _mk_label, _safe_cfg
#   [C4]      status_label hanteras separat (fg foljer watching-
#             tillstandet, ej fast COLOR_*-attribut)
#
# BEVARAT FRÅN v2.2.0:
#   Ingen print() - all loggning via write_log() / log_action()
#   create_ui: tk.Frame istf ttk.Frame -> ingen gra bakgrund
#   _build_header: tk.Frame(bg=COLOR_BG) + tk.Label(bg=...)
#   _build_folder_panel: tk.LabelFrame(bg=...)
#   _build_settings_panel: tk.LabelFrame(bg=...)
#   _build_control_buttons: tk.Frame(bg=...)
#   _build_log_panel: tk.LabelFrame(bg=...)
#   stop_watching registreras ej med app.protocol()
#       (system_tray-plugin ager WM_DELETE_WINDOW)
#   open_selected_folder: subprocess.Popen (blockerar ej)
#   Mushjul i listbox och logg: 3 enheter per klick
#   config/watch_config.json (A10/BUG-011), atomisk sparning (A9),
#   pip-installation i bakgrundstrad (A12)
#   Alla except-block loggar via write_log()
#
# KLASSER I DENNA FIL:
#   ImageFileHandler(FileSystemEventHandler) - filsystemhandelser
#   WatchFolder(BasePlugin) - PRIORITY=6
#
# IMPORTER:
#   tkinter as tk, ttk, messagebox, filedialog
#   pathlib.Path
#   threading, time, json, subprocess, platform, os, sys, tempfile
#   datetime.datetime
#   .base_plugin: BasePlugin
#   helpers: get_config_path, get_base_path (valfritt)
#   watchdog: Observer, FileSystemEventHandler (valfritt)
#
# CONTEXT SOM LASES:
#   '_tab_manager'   - add_tab()
#   '_gallery_view'  - current_folder, selected_indices, load_images()
#   '_logger'        - log()
#
# CONTEXT SOM SATTS:
#   '_watch_folder'  - self
#
# JSON: config/watch_config.json (fallback: projektrot/watch_config.json)
#   { folders, auto_reload, notify, recursive, auto_start }
# ============================================================

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from pathlib import Path
import threading
import time
import json
import os
import sys
import tempfile
import subprocess
import platform
from datetime import datetime

from .base_plugin import BasePlugin

# -- Helpers (valfritt – för config-migrering, A10/BUG-011) -----
try:
    from helpers import get_config_path, get_base_path
    _HAS_HELPERS = True
except ImportError:
    _HAS_HELPERS = False

# -- Watchdog (valfritt) ---------------------------------------
WATCHDOG_AVAILABLE = False
try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler
    WATCHDOG_AVAILABLE = True
except ImportError:
    FileSystemEventHandler = object


# ==============================================================================
# FILSYSTEMSHANDELSE-HANTERARE
# ==============================================================================

class ImageFileHandler(FileSystemEventHandler):
    """
    Hanterar filsystemhandelser fran watchdog.

    Filtrerar pa bildformat och debouncar handelser
    for att undvika dubbla callbacks.
    """

    DEFAULT_FORMATS = {
        ".jpg", ".jpeg", ".png", ".gif",
        ".webp", ".bmp", ".tiff", ".tif", ".heic", ".heif",
    }

    def __init__(self, callback, image_formats, folder_path):
        """
        Parametrar:
            callback:       funktion(event_type, file_path, folder_path)
            image_formats:  set med suffix
            folder_path:    Path - mappen som bevakas
        """
        super().__init__()
        self.callback          = callback
        self.image_formats     = (
            set(image_formats) if image_formats else self.DEFAULT_FORMATS
        )
        self.folder_path       = folder_path
        self.debounce_seconds  = 1.0
        self._last_event_time  = {}
        # v2.4.0: rensa aldre poster nar dictet vuxit sig stort
        self._prune_age        = 30.0     # sekunder
        self._prune_at_size    = 4096     # antal poster innan rensning

    def _prune_debounce(self) -> None:
        """
        Begransa minnesanvandningen for debounce-dictet (v2.4.0).

        Tar bort poster vars senaste handelse ar aldre an _prune_age
        sekunder. Kor endast da dictet vuxit sig stort, sa overheaden
        blir forsumbar vid normal belastning.
        """
        try:
            if len(self._last_event_time) < self._prune_at_size:
                return
            cutoff = time.time() - self._prune_age
            stale = [
                k for k, ts in self._last_event_time.items()
                if ts < cutoff
            ]
            for k in stale:
                del self._last_event_time[k]
        except Exception:
            pass

    def on_created(self, event):
        if not event.is_directory:
            self._handle_event("created", Path(event.src_path))

    def on_deleted(self, event):
        if not event.is_directory:
            self._handle_event("deleted", Path(event.src_path))

    def on_modified(self, event):
        if not event.is_directory:
            self._handle_event("modified", Path(event.src_path))

    def _handle_event(self, event_type: str, file_path: Path) -> None:
        """
        Filtrera pa bildformat och debounca.
        Vantar 0.5s vid 'created' for att filen ska skrivas klart.
        """
        if file_path.suffix.lower() not in self.image_formats:
            return

        now  = time.time()
        last = self._last_event_time.get(file_path, 0)
        if now - last < self.debounce_seconds:
            return
        self._last_event_time[file_path] = now
        self._prune_debounce()

        if event_type == "created":
            time.sleep(0.5)

        self.callback(event_type, file_path, self.folder_path)


# ==============================================================================
# PLUGIN-KLASS
# ==============================================================================

class WatchFolder(BasePlugin):
    """
    Plugin for mappovervakning.

    Later anvandaren lagga till flera mappar som overvakas
    i realtid med watchdog. Kraver pip install watchdog.
    Graceful fallback utan watchdog.

    v2.3.0:
    - Fargerna foljer ThemeEngine-designsystemet och uppdateras
      dynamiskt vid tema-byte (on_theme_changed + _restyle_all)
    - Hardkodade hex-farger i Listbox/Text ersatta (B1)

    v2.2.0:
    - config/watch_config.json (fallback till projektrot, BUG-011)
    - Atomisk skrivning med fsync (A9)
    - pip-installation i bakgrundstrad (A12)
    - Inga f-strings i logganrop (B1)
    """

    PLUGIN_NAME = "Mappovervakare"
    PRIORITY    = 6
    VERSION     = "2.4.0"
    AUTHOR      = "Rickard Längkvist"
    COPYRIGHT   = "Copyright (c) %d %s" % (datetime.now().year, "Rickard Längkvist")

    # -- Konfigurationsfil -------------------------------------
    CONFIG_FILENAME = "watch_config.json"

    # -- Farger (uppdateras fran ThemeEngine, C1) --------------
    COLOR_BG       = "#1a1a2e"
    COLOR_BG_MID   = "#16213e"
    COLOR_FG       = "#ffffff"
    COLOR_ACTIVE   = "#3fb950"
    COLOR_INACTIVE = "#888888"
    COLOR_ERROR    = "#f85149"
    COLOR_WARNING  = "#ffa657"
    COLOR_INFO     = "#58a6ff"
    COLOR_FOLDER   = "#a371f7"
    COLOR_TIME     = "#6e7681"
    COLOR_MUTED    = "#888888"

    # -- Listbox/logg-farger (NYA: ersatter hardkodade hex, B1) -
    COLOR_LIST_BG   = "#1e1e1e"
    COLOR_LIST_SEL  = "#264f78"
    COLOR_LOG_BG    = "#1e1e1e"
    COLOR_LOG_FG    = "#c9d1d9"

    # -- Tema-nyckelmappning (C1) ------------------------------
    _THEME_KEYS = {
        "COLOR_BG":        "bg",
        "COLOR_BG_MID":    "surface_alt",
        "COLOR_FG":        "fg",
        "COLOR_MUTED":     "muted",
        "COLOR_ACTIVE":    "success",
        "COLOR_INACTIVE":  "muted",
        "COLOR_ERROR":     "error",
        "COLOR_WARNING":   "warning",
        "COLOR_INFO":      "info",
        "COLOR_FOLDER":    "accent",
        "COLOR_TIME":      "muted",
        "COLOR_LIST_BG":   "bg_secondary",
        "COLOR_LIST_SEL":  "accent_soft",
        "COLOR_LOG_BG":    "bg_secondary",
        "COLOR_LOG_FG":    "text_secondary",
    }

    # ==========================================================================
    # TEMA-FARGER (C1)
    # ==========================================================================

    def _ensure_theme_lists(self) -> None:
        """Initiera tema-omstylingslistor (defensivt)."""
        for name in ("_panels", "_labels"):
            if not hasattr(self, name):
                setattr(self, name, [])

    def _reg_panels(self, *widgets) -> None:
        """Registrera ramar/LabelFrames/Canvas for tema-omstyling."""
        self._panels.extend(widgets)

    def _reg_labels(self, *pairs) -> None:
        """Registrera (widget, fg-attribut)-par for tema-omstyling."""
        self._labels.extend(pairs)

    def _mk_label(self, parent, text="", fg_attr="COLOR_FG", **kwargs):
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
            self.write_log("Tema-farger kunde inte laddas: %s" % e, "error")

    def _restyle_all(self) -> None:
        """
        Applicera aktuella farger pa alla befintliga widgets
        (paneler, labels, listbox, logg-text, statuslampa) vid tema-byte.
        """
        if not self.is_active:
            return
        try:
            # -- Paneler (ramar + LabelFrames + canvas) ---------
            for w in self._panels:
                if self.widget_exists(w):
                    self._safe_cfg(w, bg=self.COLOR_BG)
                    if isinstance(w, tk.LabelFrame):
                        self._safe_cfg(w, fg=self.COLOR_FG)
            # -- Labels -----------------------------------------
            for lbl, fg_attr in self._labels:
                if self.widget_exists(lbl):
                    self._safe_cfg(
                        lbl, bg=self.COLOR_BG,
                        fg=getattr(self, fg_attr, "#888888"),
                    )
            # -- Status-label (fg foljer watching-tillstand) ----
            if self.widget_exists(getattr(self, "status_label", None)):
                color = (
                    self.COLOR_ACTIVE if self.watching
                    else self.COLOR_INACTIVE
                )
                self._safe_cfg(
                    self.status_label, bg=self.COLOR_BG, fg=color
                )
            # -- Mapplista --------------------------------------
            if self.widget_exists(
                getattr(self, "folder_listbox", None)
            ):
                self._safe_cfg(
                    self.folder_listbox,
                    bg=self.COLOR_LIST_BG,
                    fg=self.COLOR_FG,
                    selectbackground=self.COLOR_LIST_SEL,
                    selectforeground=self.COLOR_FG,
                )
            # -- Logg -------------------------------------------
            if self.widget_exists(getattr(self, "log_text", None)):
                self._safe_cfg(
                    self.log_text,
                    bg=self.COLOR_LOG_BG,
                    fg=self.COLOR_LOG_FG,
                    insertbackground=self.COLOR_LOG_FG,
                    selectbackground=self.COLOR_LIST_SEL,
                )
                self._setup_log_tags()
        except Exception:
            pass

    def _setup_log_tags(self) -> None:
        """Satt loggens fargtaggar fran aktuella tema-farger."""
        if not self.widget_exists(getattr(self, "log_text", None)):
            return
        try:
            self.log_text.tag_config(
                "created",  foreground=self.COLOR_ACTIVE
            )
            self.log_text.tag_config(
                "deleted",  foreground=self.COLOR_ERROR
            )
            self.log_text.tag_config(
                "modified", foreground=self.COLOR_WARNING
            )
            self.log_text.tag_config(
                "info",     foreground=self.COLOR_INFO
            )
            self.log_text.tag_config(
                "time",     foreground=self.COLOR_TIME
            )
            self.log_text.tag_config(
                "folder",   foreground=self.COLOR_FOLDER
            )
            self.log_text.tag_config(
                "error",    foreground=self.COLOR_ERROR
            )
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

    # ==========================================================================
    # PLUGIN-LIVSCYKEL
    # ==========================================================================

    def init(self, app) -> None:
        """
        Plugin-initiering.

        Steg:
          1. Spara app-referens, initiera state (super().init)
          2. Ladda tema-farger (C1)
          3. Bestam konfigurationsfilsokvag (A10/BUG-011)
          4. Skapa UI
          5. Ladda sparad konfiguration
          6. Registrera i context
          7. Registrera tema-callback
        """
        super().init(app)
        self.app = app
        self.observers       = {}   # Path -> Observer
        self.watched_folders = []   # [Path]
        self.watching        = False

        # v2.4.0: inkrementella handelse-rakare (slipper skanna loggen)
        self._stats = {"created": 0, "deleted": 0, "modified": 0}

        # -- Tema-farger (C1) ----------------------------------
        self._ensure_theme_lists()
        self._load_theme_colors()

        self.config_file = self._resolve_config_file()

        tab_manager = app.context.get("_tab_manager")
        if tab_manager:
            parent = tab_manager.add_tab("watch", "Overvakare")
        else:
            parent = tk.Frame(app.main_frame, bg=self.COLOR_BG)
            parent.pack(fill=tk.BOTH, expand=True)

        self.create_ui(parent)
        self.load_config()

        app.context["_watch_folder"] = self

        # -- Tema-callback (C1) --------------------------------
        self.register_theme_callback()

        self.write_log("Mappovervakare redo", "info")

    def execute(self, context: dict, log=None) -> dict:
        """Pipeline-passthrough."""
        return context

    # ==========================================================================
    # KONFIGURATIONSFIL-SOKVAG (A10/BUG-011)
    # ==========================================================================

    def _resolve_config_file(self) -> Path:
        """
        Bestam konfigurationsfilens sokvag.

        Regel (A10/Z):
          - Ny sokvag:  config/watch_config.json
          - Fallback:   projektrot/watch_config.json (las om ny saknas)
          - Sparning:   ALLTID till config/watch_config.json
        """
        if _HAS_HELPERS:
            new_path = get_config_path() / self.CONFIG_FILENAME
            old_path = get_base_path() / self.CONFIG_FILENAME
            if new_path.exists():
                return new_path
            if old_path.exists():
                # Fallback-lasning (loggas en gang, migreras vid spara)
                return old_path
            return new_path
        return Path(__file__).parent.parent / self.CONFIG_FILENAME

    def _save_target(self) -> Path:
        """Returnera spar-sokvag: ALLTID config/watch_config.json."""
        if _HAS_HELPERS:
            return get_config_path() / self.CONFIG_FILENAME
        return Path(__file__).parent.parent / self.CONFIG_FILENAME

    # ==========================================================================
    # UI-BYGGARE
    # ==========================================================================

    def create_ui(self, parent) -> None:
        """
        Bygg hela granssnittet.

        v2.1.0: container = tk.Frame(bg=COLOR_BG) istf ttk.Frame
        -> ingen gra bakgrund.
        """
        container = tk.Frame(parent, bg=self.COLOR_BG)
        container.pack(fill=tk.BOTH, expand=True, padx=20, pady=15)
        self._reg_panels(container)

        self._build_header(container)
        if not WATCHDOG_AVAILABLE:
            self._build_watchdog_warning(container)
        self._build_folder_panel(container)
        self._build_settings_panel(container)
        self._build_control_buttons(container)
        self._build_log_panel(container)

    def _build_header(self, parent) -> None:
        """Header med titel, statuslampa och watchdog-badge."""
        bg     = self.COLOR_BG
        header = tk.Frame(parent, bg=bg)
        header.pack(fill=tk.X, pady=(0, 15))
        self._reg_panels(header)

        self._mk_label(
            header, "Mappovervakare",
            font=("Segoe UI", 14, "bold"),
            pack={"side": tk.LEFT},
        )

        # Statuslampa (Canvas-cirkel)
        self.status_canvas = tk.Canvas(
            header, width=22, height=22,
            highlightthickness=0, bg=bg,
        )
        self.status_canvas.pack(side=tk.LEFT, padx=(12, 4))
        self._reg_panels(self.status_canvas)
        self.status_circle = self.status_canvas.create_oval(
            2, 2, 20, 20, fill=self.COLOR_INACTIVE, outline=""
        )

        self.status_label = tk.Label(
            header, text="Inaktiv",
            bg=bg, fg=self.COLOR_INACTIVE,
            font=("Segoe UI", 9),
        )
        self.status_label.pack(side=tk.LEFT)

        # Watchdog-badge
        badge_text  = (
            "watchdog tillganglig" if WATCHDOG_AVAILABLE
            else "watchdog saknas"
        )
        badge_attr  = (
            "COLOR_ACTIVE" if WATCHDOG_AVAILABLE else "COLOR_WARNING"
        )
        self._mk_label(
            header, badge_text, badge_attr,
            pack={"side": tk.RIGHT},
        )

    def _build_watchdog_warning(self, parent) -> None:
        """Varning och installationsknapp om watchdog saknas."""
        bg    = self.COLOR_BG
        frame = tk.LabelFrame(
            parent, text="Saknat beroende",
            bg=bg, fg=self.COLOR_WARNING,
            font=("Segoe UI", 9),
            padx=10, pady=8,
        )
        frame.pack(fill=tk.X, pady=(0, 12))
        self._reg_panels(frame)

        self._mk_label(
            frame,
            "watchdog-biblioteket saknas - "
            "realtidsovervakning ar inte mojlig.",
            "COLOR_ERROR",
            font=("Segoe UI", 10, "bold"),
            pack={"anchor": "w"},
        )

        self._mk_label(
            frame,
            "Installera med:  pip install watchdog",
            "COLOR_INACTIVE",
            font=("Consolas", 10),
            pack={"anchor": "w", "pady": (4, 0)},
        )

        ttk.Button(
            frame, text="Installera watchdog nu",
            command=self.install_watchdog,
        ).pack(anchor="w", pady=(8, 0))

    def _build_folder_panel(self, parent) -> None:
        """Mapplista med knappar och mushjul-stod."""
        bg    = self.COLOR_BG
        frame = tk.LabelFrame(
            parent, text="Bevakade mappar",
            bg=bg, fg=self.COLOR_FG,
            font=("Segoe UI", 9),
            padx=10, pady=8,
        )
        frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        self._reg_panels(frame)

        # Knappar
        btn_row = tk.Frame(frame, bg=bg)
        btn_row.pack(fill=tk.X, pady=(0, 8))
        self._reg_panels(btn_row)
        for text, cmd in [
            ("Lagg till mapp...", self.add_folder),
            ("Lagg till aktuell", self.add_current_folder),
            ("Ta bort vald",      self.remove_selected_folder),
            ("Ta bort alla",      self.remove_all_folders),
        ]:
            ttk.Button(btn_row, text=text, command=cmd).pack(
                side=tk.LEFT, padx=2
            )

        # Listbox
        list_frame = tk.Frame(frame, bg=bg)
        list_frame.pack(fill=tk.BOTH, expand=True)
        self._reg_panels(list_frame)

        self.folder_listbox = tk.Listbox(
            list_frame,
            bg=self.COLOR_LIST_BG,
            fg=self.COLOR_FG,
            selectmode=tk.EXTENDED,
            height=6,
            font=("Consolas", 10),
            activestyle="dotbox",
            selectbackground=self.COLOR_LIST_SEL,
            selectforeground=self.COLOR_FG,
        )
        self.folder_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        sb = ttk.Scrollbar(list_frame, command=self.folder_listbox.yview)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        self.folder_listbox.config(yscrollcommand=sb.set)

        self.folder_listbox.bind("<Double-1>", self.open_selected_folder)

        # Mushjul (3 enheter)
        self.folder_listbox.bind(
            "<MouseWheel>",
            lambda e: self.folder_listbox.yview_scroll(
                -1 * (e.delta // 120) * 3, "units"
            )
        )
        self.folder_listbox.bind(
            "<Button-4>",
            lambda e: self.folder_listbox.yview_scroll(-3, "units")
        )
        self.folder_listbox.bind(
            "<Button-5>",
            lambda e: self.folder_listbox.yview_scroll(3, "units")
        )

        # Raknare
        self.folder_count_label = self._mk_label(
            frame, "0 mappar", "COLOR_INACTIVE",
            pack={"anchor": "w", "pady": (6, 0)},
        )

    def _build_settings_panel(self, parent) -> None:
        """Installnings-checkboxar."""
        bg    = self.COLOR_BG
        frame = tk.LabelFrame(
            parent, text="Installningar",
            bg=bg, fg=self.COLOR_FG,
            font=("Segoe UI", 9),
            padx=10, pady=8,
        )
        frame.pack(fill=tk.X, pady=(0, 10))
        self._reg_panels(frame)

        self.auto_reload_var = tk.BooleanVar(value=True)
        self.notify_var      = tk.BooleanVar(value=True)
        self.recursive_var   = tk.BooleanVar(value=False)
        self.auto_start_var  = tk.BooleanVar(value=False)

        checkboxes = [
            (
                self.auto_reload_var,
                "Ladda om galleriet automatiskt nar nya bilder hittas",
                None,
            ),
            (
                self.notify_var,
                "Visa notifikation i titelraden nar nya bilder hittas",
                None,
            ),
            (
                self.recursive_var,
                "Inkludera undermappar vid bevakning",
                None,
            ),
            (
                self.auto_start_var,
                "Starta overvakning automatiskt vid programstart",
                self.save_config,
            ),
        ]

        for var, label, cmd in checkboxes:
            kwargs = {"text": label, "variable": var}
            if cmd:
                kwargs["command"] = cmd
            ttk.Checkbutton(frame, **kwargs).pack(anchor="w", pady=2)

    def _build_control_buttons(self, parent) -> None:
        """Start/stopp/spara-knappar."""
        bg    = self.COLOR_BG
        frame = tk.Frame(parent, bg=bg)
        frame.pack(fill=tk.X, pady=8)
        self._reg_panels(frame)

        self.start_btn = ttk.Button(
            frame, text="Starta overvakning",
            command=self.start_watching,
        )
        self.start_btn.pack(side=tk.LEFT, padx=4)

        self.stop_btn = ttk.Button(
            frame, text="Stoppa overvakning",
            command=self.stop_watching,
            state="disabled",
        )
        self.stop_btn.pack(side=tk.LEFT, padx=4)

        ttk.Button(
            frame, text="Spara installningar",
            command=self.save_config,
        ).pack(side=tk.RIGHT, padx=4)

    def _build_log_panel(self, parent) -> None:
        """Aktivitetslogg med fargkodade handelser och mushjul."""
        bg    = self.COLOR_BG
        frame = tk.LabelFrame(
            parent, text="Aktivitetslogg",
            bg=bg, fg=self.COLOR_FG,
            font=("Segoe UI", 9),
            padx=10, pady=8,
        )
        frame.pack(fill=tk.BOTH, expand=True, pady=(8, 0))
        self._reg_panels(frame)

        # Text + scrollbar
        text_frame = tk.Frame(frame, bg=bg)
        text_frame.pack(fill=tk.BOTH, expand=True)
        self._reg_panels(text_frame)

        self.log_text = tk.Text(
            text_frame,
            height=10,
            bg=self.COLOR_LOG_BG,
            fg=self.COLOR_LOG_FG,
            font=("Consolas", 9),
            wrap=tk.WORD,
            state="normal",
            relief="flat",
        )
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        sb = ttk.Scrollbar(text_frame, command=self.log_text.yview)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_text.config(yscrollcommand=sb.set)

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

        # Fargtaggar (fran aktuella tema-farger, C1)
        self._setup_log_tags()

        # Knappar + statistik
        bottom = tk.Frame(frame, bg=bg)
        bottom.pack(fill=tk.X, pady=(6, 0))
        self._reg_panels(bottom)

        ttk.Button(
            bottom, text="Rensa logg",
            command=self.clear_log,
        ).pack(side=tk.LEFT, padx=2)

        self.stats_label = self._mk_label(
            bottom, "", "COLOR_INACTIVE",
            pack={"side": tk.RIGHT, "padx": 8},
        )

        self.update_stats()

    # ==========================================================================
    # KONFIGURATION
    # ==========================================================================

    def load_config(self) -> None:
        """
        Ladda watch_config.json.

        Regel (A10/BUG-011):
          - Ny sokvag: config/watch_config.json
          - Fallback: projektrot/watch_config.json (loggas INFO)
        Lagger till sparade mappar om de fortfarande finns.
        Kor auto-start om installt.
        """
        if not self.config_file.exists():
            return

        # Fallback-info (migreras vid nasta spara)
        if (
            _HAS_HELPERS
            and self.config_file == get_base_path() / self.CONFIG_FILENAME
        ):
            self.write_log(
                "Laser fran gammal sokvag (projektrot) - "
                "migreras till config/ vid nasta spara",
                "info",
            )

        try:
            config = json.loads(
                self.config_file.read_text(encoding="utf-8")
            )
        except Exception as e:
            self.write_log(
                "Kunde inte ladda konfiguration: %s" % e, "error"
            )
            return

        loaded = 0
        for folder_str in config.get("folders", []):
            folder_path = Path(folder_str)
            if (
                folder_path.exists()
                and folder_path not in self.watched_folders
            ):
                self.watched_folders.append(folder_path)
                self.folder_listbox.insert(tk.END, str(folder_path))
                loaded += 1

        self.auto_reload_var.set(config.get("auto_reload", True))
        self.notify_var.set(config.get("notify",       True))
        self.recursive_var.set(config.get("recursive",  False))
        self.auto_start_var.set(config.get("auto_start", False))

        self.update_folder_count()
        self.write_log(
            "Laddade %s sparade mappar" % loaded, "info"
        )

        if (
            self.auto_start_var.get()
            and self.watched_folders
            and WATCHDOG_AVAILABLE
        ):
            self.app.after(1200, self.start_watching)

    # ==========================================================================
    # KONFIGURATION - SPARA
    # ==========================================================================

    def save_config(self) -> None:
        """
        Spara watch_config.json atomiskt (A9).

        Monster: mkstemp -> fdopen -> flush -> fsync -> os.replace.
        Sparning sker ALLTID till config/watch_config.json (A10).
        Tyst felhantering - loggar via write_log().
        """
        config = {
            "folders":     [str(f) for f in self.watched_folders],
            "auto_reload": self.auto_reload_var.get(),
            "notify":      self.notify_var.get(),
            "recursive":   self.recursive_var.get(),
            "auto_start":  self.auto_start_var.get(),
        }
        tmp_path = None
        try:
            target = self._save_target()
            target.parent.mkdir(parents=True, exist_ok=True)

            fd, tmp_str = tempfile.mkstemp(
                dir=target.parent,
                prefix=".%s_" % target.stem,
                suffix=".tmp",
            )
            tmp_path = Path(tmp_str)

            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
                f.flush()
                os.fsync(f.fileno())   # A9

            os.replace(tmp_path, target)
            self.config_file = target
            self.write_log("Installningar sparade", "info")
        except Exception as e:
            if tmp_path and tmp_path.exists():
                try:
                    tmp_path.unlink()
                except OSError:
                    pass
            self.write_log(
                "Kunde inte spara konfiguration: %s" % e, "error"
            )

    # ==========================================================================
    # MAPPHANTERING
    # ==========================================================================

    def add_folder(self) -> None:
        """Lagg till mapp via OS-dialog."""
        folder = filedialog.askdirectory(title="Valj mapp att overvaka")
        if folder:
            self._add_folder_path(Path(folder))

    def add_current_folder(self) -> None:
        """Lagg till aktuell gallerimapp fran gallery_view."""
        gallery_view = self.app.context.get("_gallery_view")
        if not (
            gallery_view
            and hasattr(gallery_view, "current_folder")
            and gallery_view.current_folder
        ):
            messagebox.showwarning(
                "Varning",
                "Ingen mapp ar oppnad i Bildgalleriet.\n"
                "Oppna en mapp i galleriet forst."
            )
            return
        self._add_folder_path(gallery_view.current_folder)

    def _add_folder_path(self, folder_path: Path) -> None:
        """
        Validera och lagg till en mappsokvag.
        Startar observer om overvakning redan ar aktiv.
        """
        if not folder_path.exists():
            messagebox.showerror(
                "Fel", "Mappen finns inte:\n%s" % folder_path
            )
            return

        if folder_path in self.watched_folders:
            messagebox.showwarning(
                "Varning",
                "Mappen bevakas redan:\n%s" % folder_path.name
            )
            return

        self.watched_folders.append(folder_path)
        self.folder_listbox.insert(tk.END, str(folder_path))
        self.update_folder_count()
        self.save_config()
        self.write_log(
            "Lade till mapp: %s" % folder_path.name, "folder"
        )

        if self.watching:
            self.add_observer(folder_path)

    def remove_selected_folder(self) -> None:
        """Ta bort valda mappar och stoppa deras observers."""
        selections = self.folder_listbox.curselection()
        if not selections:
            messagebox.showinfo("Info", "Valj minst en mapp i listan.")
            return

        for i in reversed(selections):
            folder_path = self.watched_folders[i]
            self.remove_observer(folder_path)
            self.watched_folders.pop(i)
            self.folder_listbox.delete(i)
            self.write_log(
                "Tog bort mapp: %s" % folder_path.name, "info"
            )

        self.update_folder_count()
        self.save_config()
        self._update_status_after_change()

    def remove_all_folders(self) -> None:
        """Ta bort alla mappar efter bekraftelse."""
        if not self.watched_folders:
            return
        if not messagebox.askyesno(
            "Bekrafta",
            "Ta bort alla bevakade mappar?\nOvervakning stoppas."
        ):
            return
        self.stop_watching()
        self.watched_folders.clear()
        self.folder_listbox.delete(0, tk.END)
        self.update_folder_count()
        self.save_config()
        self.write_log("Tog bort alla mappar", "info")

    def open_selected_folder(self, event=None) -> None:
        """Oppna vald mapp i OS-filhanterare (Popen - blockerar ej)."""
        selections = self.folder_listbox.curselection()
        if not selections:
            return
        folder_path = self.watched_folders[selections[0]]
        if not folder_path.exists():
            messagebox.showerror(
                "Fel", "Mappen finns inte langre:\n%s" % folder_path
            )
            return
        try:
            os_name = platform.system()
            if os_name == "Windows":
                subprocess.Popen(["explorer", str(folder_path)])
            elif os_name == "Darwin":
                subprocess.Popen(["open", str(folder_path)])
            else:
                subprocess.Popen(["xdg-open", str(folder_path)])
        except Exception as e:
            messagebox.showerror(
                "Fel", "Kunde inte oppna mappen:\n%s" % e
            )

    def update_folder_count(self) -> None:
        """Uppdatera mappraknare-label."""
        count = len(self.watched_folders)
        s     = "ar" if count != 1 else ""
        self.folder_count_label.config(
            text="%d mapp%s" % (count, s)
        )

    def _update_status_after_change(self) -> None:
        """Uppdatera statustext efter antal mappar andrats."""
        if self.watching:
            self.update_status_indicator(
                active=True,
                text="Aktiv (%d mappar)" % len(self.observers)
            )

    # ==========================================================================
    # WATCHDOG INSTALLATION (A12: bakgrundstrad - UI blockeras aldrig)
    # ==========================================================================

    def install_watchdog(self) -> None:
        """
        Installera watchdog via pip i BAKGRUNDSTRAD.

        Bekraftelsedialog -> trad startas -> resultat visas via
        app.after() i main thread. UI blockeras aldrig (A12).
        """
        if not messagebox.askyesno(
            "Installera watchdog",
            "Vill du installera watchdog-biblioteket?\n\n"
            "Kommando: pip install watchdog\n\n"
            "Programmet maste startas om efter installation."
        ):
            return
        try:
            self.write_log(
                "Installerar watchdog... (bakgrund)", "info"
            )
            thread = threading.Thread(
                target=self._install_watchdog_worker,
                daemon=True,
                name="WatchdogInstallThread",
            )
            thread.start()
        except Exception as e:
            self.write_log("install_watchdog: %s" % e, "error")
            messagebox.showerror(
                "Fel", "Kunde inte starta installationen:\n%s" % e
            )

    def _install_watchdog_worker(self) -> None:
        """
        Kor pip i bakgrundstraden.

        Resultatet skickas till main thread via app.after(0, ...).
        """
        result = None
        try:
            result = subprocess.run(
                [sys.executable, "-m", "pip", "install", "watchdog"],
                capture_output=True, text=True, timeout=180,
            )
        except subprocess.TimeoutExpired:
            result = None
        except Exception as e:
            self.write_log("install_watchdog: %s" % e, "error")
        try:
            self.app.after(0, self._show_install_result, result)
        except Exception:
            pass

    def _show_install_result(self, result) -> None:
        """Visa installationsresultat i main thread."""
        if result is None:
            messagebox.showerror(
                "Timeout", "Installationen tog for lang tid."
            )
            return
        if result.returncode == 0:
            messagebox.showinfo(
                "Klart",
                "watchdog installerades!\n\nStarta om programmet."
            )
        else:
            messagebox.showerror(
                "Fel",
                "Installationen misslyckades:\n\n%s" % result.stderr
            )

    # ==========================================================================
    # OBSERVER-HANTERING
    # ==========================================================================

    def add_observer(self, folder_path: Path) -> None:
        """Starta watchdog-observer for en mapp."""
        if not WATCHDOG_AVAILABLE:
            return
        if folder_path in self.observers:
            return
        if not folder_path.exists():
            self.write_log(
                "Mappen finns inte, kan inte bevaka: %s" % folder_path,
                "error"
            )
            return

        try:
            gallery_view  = self.app.context.get("_gallery_view")
            image_formats = (
                gallery_view.image_formats
                if gallery_view and hasattr(gallery_view, "image_formats")
                else ImageFileHandler.DEFAULT_FORMATS
            )
            handler  = ImageFileHandler(
                self.on_file_event, image_formats, folder_path
            )
            observer = Observer()
            observer.schedule(
                handler, str(folder_path),
                recursive=self.recursive_var.get()
            )
            observer.start()
            self.observers[folder_path] = observer
            self.write_log("Bevakar: %s" % folder_path, "folder")
        except Exception as e:
            self.write_log(
                "Kunde inte starta bevakning av %s: %s"
                % (folder_path.name, e),
                "error"
            )

    def remove_observer(self, folder_path: Path) -> None:
        """Stoppa och ta bort observer for en mapp."""
        if folder_path not in self.observers:
            return
        try:
            observer = self.observers.pop(folder_path)
            observer.stop()
            observer.join(timeout=3)
        except Exception as e:
            self.write_log(
                "Fel vid stopp av observer for %s: %s"
                % (folder_path.name, e),
                "error"
            )

    def start_watching(self) -> None:
        """Starta overvakning av alla mappar."""
        if not WATCHDOG_AVAILABLE:
            messagebox.showerror(
                "Saknar beroende",
                "watchdog kravs for realtidsovervakning.\n\n"
                "Installera med: pip install watchdog"
            )
            return
        if not self.watched_folders:
            messagebox.showwarning(
                "Varning", "Lagg till minst en mapp innan du startar."
            )
            return
        if self.watching:
            return

        started = 0
        for folder_path in self.watched_folders:
            if folder_path.exists():
                self.add_observer(folder_path)
                started += 1
            else:
                self.write_log(
                    "Hoppar over (finns inte): %s" % folder_path,
                    "error"
                )

        self.watching = True
        self.start_btn.config(state="disabled")
        self.stop_btn.config(state="normal")
        self.update_status_indicator(
            active=True,
            text="Aktiv (%d mappar)" % started
        )
        self.write_log(
            "Overvakning startad - %d/%d mappar"
            % (started, len(self.watched_folders)),
            "info"
        )
        self.log_action("Mappovervakning startad")

    def stop_watching(self) -> None:
        """Stoppa all mappovervakning."""
        if not self.watching:
            return
        for folder_path in list(self.observers.keys()):
            self.remove_observer(folder_path)

        self.watching = False
        self.start_btn.config(state="normal")
        self.stop_btn.config(state="disabled")
        self.update_status_indicator(active=False, text="Inaktiv")
        self.write_log("Overvakning stoppad", "info")
        self.log_action("Mappovervakning stoppad")

    # ==========================================================================
    # FILHANDELSE-HANTERING
    # ==========================================================================

    def on_file_event(
        self, event_type: str, file_path: Path, folder_path: Path
    ) -> None:
        """
        Callback fran watchdog (bakgrundstrad).
        Delegerar till main thread via app.after().
        """
        try:
            self.app.after(
                0,
                self._handle_file_event,
                event_type, file_path, folder_path
            )
        except Exception:
            pass

    def _handle_file_event(
        self, event_type: str, file_path: Path, folder_path: Path
    ) -> None:
        """Hantera filhandelse i main thread."""
        folder_name = folder_path.name
        messages = {
            "created":  "[%s] Ny bild:   %s" % (folder_name, file_path.name),
            "deleted":  "[%s] Borttagen: %s" % (folder_name, file_path.name),
            "modified": "[%s] Andrad:    %s" % (folder_name, file_path.name),
        }
        tag = event_type if event_type in messages else "info"
        # v2.4.0: uppdatera in-memory-rakare (snabbare an logg-skanning)
        if event_type in self._stats:
            self._stats[event_type] += 1
        self.write_log(
            messages.get(
                event_type,
                "[%s] %s" % (event_type, file_path.name)
            ),
            tag
        )

        if self.notify_var.get() and event_type == "created":
            original = self.app.title()
            self.app.title(
                "Gallery Uploader  -  Ny: %s" % file_path.name
            )
            self.app.after(4000, lambda: self.app.title(original))

        if self.auto_reload_var.get():
            self.reload_gallery_if_current(folder_path)

        self.update_stats()

    def reload_gallery_if_current(self, folder_path: Path) -> None:
        """Ladda om galleriet om det visar folder_path."""
        gallery_view = self.app.context.get("_gallery_view")
        if not (
            gallery_view
            and hasattr(gallery_view, "current_folder")
            and gallery_view.current_folder == folder_path
        ):
            return
        try:
            old_selected = (
                gallery_view.selected_indices.copy()
                if hasattr(gallery_view, "selected_indices") else []
            )
            gallery_view.load_images()
            if old_selected and hasattr(gallery_view, "image_files"):
                max_idx = len(gallery_view.image_files)
                gallery_view.selected_indices = [
                    i for i in old_selected if i < max_idx
                ]
                if hasattr(gallery_view, "refresh_gallery"):
                    gallery_view.refresh_gallery()
            self.write_log("Galleri omladdad automatiskt", "info")
        except Exception as e:
            self.write_log("Fel vid auto-omladdning: %s" % e, "error")

    # ==========================================================================
    # LOGG
    # ==========================================================================

    def write_log(self, message: str, tag: str = "info") -> None:
        """
        Skriv tidsstamplat meddelande i aktivitetsloggen.
        Tradsaker: anropas alltid fran main thread
        (watchdog-callbacks routas via app.after()).
        """
        try:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.log_text.insert(tk.END, "[%s] " % timestamp, "time")
            self.log_text.insert(tk.END, "%s\n" % message, tag)
            self.log_text.see(tk.END)
            try:
                if self.app.winfo_exists():
                    self.app.update_idletasks()
            except Exception:
                pass
        except Exception:
            pass

    def clear_log(self) -> None:
        """Rensa loggfonstret och aterstall handelse-rakare (v2.4.0)."""
        try:
            self.log_text.delete("1.0", tk.END)
            self._stats = {"created": 0, "deleted": 0, "modified": 0}
            self._refresh_stats_label()
            self.write_log("Logg rensad", "info")
        except Exception:
            pass

    def update_stats(self) -> None:
        """
        Uppdatera statistik-label.

        v2.4.0: laser in-memory-rakare i stallet for att skanna hela
        loggtexten pa varje handelse (snabbt aven vid lang logg).
        """
        self._refresh_stats_label()

    def _refresh_stats_label(self) -> None:
        """Satt statistik-label fran _stats-rakarna (tyst vid saknad UI)."""
        try:
            self.stats_label.config(
                text=(
                    "Nya: %d  |  Borttagna: %d  |  Andrade: %d"
                    % (
                        self._stats["created"],
                        self._stats["deleted"],
                        self._stats["modified"],
                    )
                )
            )
        except Exception:
            pass

    # ==========================================================================
    # STATUS OCH LOGGNING
    # ==========================================================================

    def update_status_indicator(self, active: bool, text: str) -> None:
        """Uppdatera statuslampa och text."""
        color = self.COLOR_ACTIVE if active else self.COLOR_INACTIVE
        try:
            self.status_canvas.itemconfig(self.status_circle, fill=color)
            self.status_label.config(text=text, fg=color)
        except Exception:
            pass

    def log_action(self, message: str) -> None:
        """
        Logga via advanced_logger om tillganglig.
        Ingen print() - tyst fallback.
        """
        try:
            logger = self.app.context.get("_logger")
            if logger and hasattr(logger, "log"):
                logger.log("INFO", "[Overvakare] %s" % message)
        except Exception:
            pass
