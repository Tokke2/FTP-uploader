#!/usr/bin/env python3
# ============================================================
# Plugin: Kontroller och Logg
# ============================================================
# FIL:       plugins/ui_controls.py
# PLATS:     plugins/ (ftp_gallery_uploader/plugins/ui_controls.py)
# Syfte:     Knappar, progress, logg och statistik i egen flik
# PLUGIN_NAME: "Kontroller"
# PRIORITY:  2
# VERSION:   2.4.1
# AUTHOR:    Rickard Längkvist
# COPYRIGHT: Copyright (c) <år> Rickard Längkvist (dynamiskt år,
#            se COPYRIGHT-konstanten nedan)
#
# ÄNDRINGAR v2.4.0 → v2.4.1 (KRASCHFIXAR — Python 3.14 / Tcl-Tk 9.0):
#   [P14-1]   ROTORSAK: search_var.trace("w", ...) → trace_add("write", ...).
#             Tcl/Tk 9.0 (som följer med Python 3.14 på Windows) tog bort
#             det gamla "trace variable"-kommandot; Python 3.14:s
#             Variable.trace()/trace_variable() skickar fortfarande
#             "trace variable" till Tk → TclError: bad option "variable":
#             must be add, info, or remove. Felet avbröt create_ui() i
#             _build_log_section() och hela pluginet init-failade.
#             trace_add() fungerar på både Tcl/Tk 8.6 och 9.0 (och har
#             funnits sedan Python 3.0) — samma callback-signatur (*args).
#   [P14-2]   ALLA widget-attribut har nu klassnivå-default (None):
#             log_text, search_var, filter_var, auto_scroll_var,
#             stats_labels, status_label, time_label, folder_label,
#             images/videos_count_label, size_label, progress_var,
#             knappar, recent_menu/recent_var. Om UI-bygget ändå avbryts
#             halvvags kan inget senare anrop resa AttributeError —
#             widget_exists(None) → False och metoden avslutas lugnt.
#             (Fixar kedjan: AttributeError: 'ControlsUI' object has no
#             attribute 'log_text' → tk-callback → print till stderr →
#             OSError WinError 6 → mainloop avbruten.)
#   [P14-3]   write_log/_trim_log/on_search_changed/on_filter_changed/
#             clear_log/copy_log/save_log/update_status/update_counts/
#             _setup_log_tags: "except tk.TclError: pass" → "except
#             Exception" + log_error() (INGA tysta undantag, spec B1/19A).
#             auto_scroll_var läses via getattr-guard.
#   [P14-4]   _ui_ready(): run_generate()/preview/open_output kontrollerar
#             att UI:t verkligen byggts klart och visar i stället ett tydligt
#             meddelande + loggrad om en sektion saknas (aldrig krasch).
#   [P14-5]   widget_exists() fångar Exception (inte bara TclError) så att
#             trasiga/stängda widgetreferenser aldrig propagerar.
#
# ÄNDRINGAR v2.3.0 → v2.4.0 (kvalitet/minne/snabbhet, icke-brytande):
#   [Q1]      Ny fabrik _mk_section(): LabelFrame-boilerplate samlad
#             (bg/fg/font/padx/pady/pack/registrering) -> identiskt
#             utseende i alla fem sektioner + mindre kod.
#   [Q2]      _make_btn(): tar nu ATTRIBUTNAMN (color_attr) och loser
#             hover/leave dynamiskt ur aktuell tema-farg. Felrattat:
#             efter tema-byte återställde hover inte langre det nya
#             temat. _restyle_all() refaktoreras till en data-driven
#             knapp-loop (ingen fyrdubbling av nästan identisk kod).
#   [Q3]      _trim_log(): loggens text-widget OCH self.log_entries
#             begransas till _MAX_LOG_ENTRIES (2000) rader -> ingen
#             oandlig minnestillvaxt vid langa korningar.
#
# ÄNDRINGAR v2.2.0 → v2.3.0 (DESIGN-SYSTEM-integration, spec v4.6.0):
#   [C1]      Fargerna hamtas nu fran ThemeEngine-designsystemet
#             (helpers v1.3.0, 58 nycklar/tema) via _THEME_KEYS:
#               COLOR_BG           <- "bg"
#               COLOR_BG_MID       <- "surface_alt"
#               COLOR_FG           <- "fg"            (paneltext)
#               COLOR_BTN_FG (NY)  <- "selection_fg"  (vit knapptext)
#               COLOR_MUTED        <- "muted"
#               COLOR_SUCCESS      <- "success"
#               COLOR_WARNING      <- "warning"
#               COLOR_INFO         <- "info"
#               COLOR_HEADER       <- "accent"
#               COLOR_DIM          <- "text_secondary"
#               COLOR_LOG_BG       <- "bg_secondary"
#               COLOR_HIGHLIGHT_BG <- "accent_soft"
#               COLOR_HIGHLIGHT_FG <- "fg"
#               COLOR_GREEN        <- "success"
#               COLOR_BLUE         <- "accent"
#               COLOR_GRAY         <- "muted"
#               COLOR_DARK         <- "surface_alt"
#               COLOR_RED          <- "error"
#   [C1]      _load_theme_colors(): hamtar farger fran
#             app.theme_engine.get_color() med fallback till
#             klassattributen (fungerar aven utan tema-engine)
#   [C1]      on_theme_changed(): lyssnar pa <<ThemeChanged>> och
#             uppdaterar alla paneler, knappar, labels och loggen
#             vid tema-byte (utan omstart)
#   [C1]      _restyle_all(): applicerar aktuella farger pa alla
#             befintliga widgets (paneler registreras i self._panels)
#   [C1]      _setup_log_tags(): loggens fargtaggar satts via
#             tema-farger (bryts ut for att kunna koras om)
#   [C1]      COLOR_BTN_FG: ny konstant for text pa fargade knappar
#             (vit i bada teman via "selection_fg")
#   [C4]      register_theme_callback() anropas i init()
#
# BEVARAT FRÅN v2.2.0:
#   Inga f-strings (B1), atomisk save_recent_folders med fsync (A9),
#   config/ via helpers (A10), alla atgarder, logg, progress,
#   statistik, pipeline-trad, tangentbordsgenvagar.
#
# KLASSER I DENNA FIL:
#   ControlsUI(BasePlugin) - PRIORITY=2
#
# IMPORTER:
#   tkinter as tk, ttk, messagebox, filedialog
#   webbrowser
#   pathlib.Path
#   datetime
#   threading
#   json, subprocess, sys, shutil, traceback, os, tempfile
#   .base_plugin: BasePlugin
#   helpers: get_config_path (valfritt, A10)
#
# CONTEXT SOM LASES:
#   '_settings'      - folder_var, refresh_gallery
#   '_gallery_view'  - image_files
#   '_tab_manager'   - add_tab()
#   'processed_videos' - lista
#   'output_path'    - str
#
# CONTEXT SOM SATTS:
#   '_controls'          - self
#   'progress_callback'  - funktion(value, msg)
#   'cancel_check'       - funktion() -> bool
#
# TANGENTBORDSGENVAGAR:
#   Ctrl+G / F5   - Generera
#   Ctrl+P        - Forhandsgranska
#   Ctrl+O        - Oppna output
#   Escape        - Avbryt
#
# JSON: config/recent_folders.json
#   { "folders": [...] }  max 10 poster
# ============================================================

import app_paths
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import webbrowser
from pathlib import Path
from datetime import datetime
import threading
import json
import quiet_process as subprocess
import sys
import shutil
import traceback
import os
import tempfile

from .base_plugin import BasePlugin

# -- Helpers (valfritt – för config-sökväg, A10) ---------------
try:
    from helpers import get_config_path
    _HAS_HELPERS = True
except ImportError:
    _HAS_HELPERS = False


class ControlsUI(BasePlugin):
    """
    Kontrollpanel med knappar, progress-bar, logg och statistik.

    Kor pipeline i bakgrundstrad for att aldrig frysa UI.
    Loggen stoder fargtaggar, sokning och filtrering.
    Senaste 10 mappar sparas i config/recent_folders.json.

    v2.4.0:
    - _mk_section()-fabrik: identiskt sektionsutseende, mindre kod
    - _make_btn(): hover foljer tema via color_attr (felrattat)
    - Logg begransas till 2000 rader (ingen minnestillvaxt)

    v2.3.0:
    - Fargerna foljer ThemeEngine-designsystemet (58 nycklar/tema)
    - Uppdateras dynamiskt vid tema-byte (on_theme_changed)
    - Inga f-strings (B1) - all %-formatering
    """

    PLUGIN_NAME  = "Kontroller"
    PRIORITY     = 2
    VERSION      = "2.4.1"
    AUTHOR       = "Rickard Längkvist"
    COPYRIGHT    = "Copyright (c) %d %s" % (datetime.now().year, "Rickard Längkvist")

    # -- Knappfarger (uppdateras fran temat) -------------------
    COLOR_GREEN  = "#22c55e"
    COLOR_BLUE   = "#4a9eff"
    COLOR_GRAY   = "#64748b"
    COLOR_DARK   = "#263449"
    COLOR_RED    = "#ef4444"
    COLOR_BG     = "#0f172a"
    COLOR_BG_MID = "#263449"

    # -- Fargkonstanter (B1/C1: tema-styrbara) -----------------
    COLOR_FG           = "#e2e8f0"
    COLOR_BTN_FG       = "#ffffff"
    COLOR_MUTED        = "#64748b"
    COLOR_SUCCESS      = "#22c55e"
    COLOR_WARNING      = "#f59e0b"
    COLOR_INFO         = "#38bdf8"
    COLOR_HEADER       = "#4a9eff"
    COLOR_DIM          = "#94a3b8"
    COLOR_LOG_BG       = "#0b1120"
    COLOR_HIGHLIGHT_BG = "#1e3a5f"
    COLOR_HIGHLIGHT_FG = "#e2e8f0"

    # -- Tema-nyckelmappning (C1) ------------------------------
    _THEME_KEYS = {
        "COLOR_BG":           "bg",
        "COLOR_BG_MID":       "surface_alt",
        "COLOR_FG":           "fg",
        "COLOR_BTN_FG":       "selection_fg",
        "COLOR_MUTED":        "muted",
        "COLOR_SUCCESS":      "success",
        "COLOR_WARNING":      "warning",
        "COLOR_INFO":         "info",
        "COLOR_HEADER":       "accent",
        "COLOR_DIM":          "text_secondary",
        "COLOR_LOG_BG":       "bg_secondary",
        "COLOR_HIGHLIGHT_BG": "accent_soft",
        "COLOR_HIGHLIGHT_FG": "fg",
        "COLOR_GREEN":        "success",
        "COLOR_BLUE":         "accent",
        "COLOR_GRAY":         "muted",
        "COLOR_DARK":         "surface_alt",
        "COLOR_RED":          "error",
    }

    # -- Loggbegransning (Q3: undviker oandlig minnestillvaxt) ---
    _MAX_LOG_ENTRIES = 2000

    # -- Widget-referenser (P14-2) -----------------------------
    # ALLA widget-attribut som skapas i create_ui() har en default pa
    # klassniva. Om UI-bygget avbryts halvvags (t.ex. TclError i en
    # sektion) kan senare anrop (write_log, update_status, update_counts,
    # _restyle_all, run_generate ...) aldrig resa AttributeError -
    # widget_exists(None) returnerar False och metoden avslutas lugnt
    # (och loggat). Instansattribut skuggar dessa sa fort widgeten finns.
    #
    # Bakgrund: utan dessa defaults gav ett avbrutet create_ui()
    #   AttributeError: 'ControlsUI' object has no attribute 'log_text'
    #   inne i en tk-callback -> Tk:s report_callback_exception skrev till
    #   stderr -> under pythonw (ingen konsol) blev det
    #   OSError: [WinError 6] Referensen (handle) ar felaktig
    #   -> mainloop avbrots. En enda saknad widget blev alltsa en appkrasch.
    log_text           = None
    search_var         = None
    filter_var         = None
    auto_scroll_var    = None
    stats_labels       = None
    status_label       = None
    time_label         = None
    folder_label       = None
    images_count_label = None
    videos_count_label = None
    size_label         = None
    progress_var       = None
    progress_bar       = None
    generate_btn       = None
    cancel_btn         = None
    preview_btn        = None
    open_folder_btn    = None
    recent_menu        = None
    recent_var         = None

    # Rapportera saknad loggwidget EN gang (P14-3)
    _log_widget_warned = False

    def _history_file(self) -> Path:
        """Returnera sökväg till recent_folders.json (A10)."""
        if _HAS_HELPERS:
            return get_config_path() / "recent_folders.json"
        return app_paths.config_dir() / "recent_folders.json"

    # ==========================================================================
    # TEMA-FARGER (C1)
    # ==========================================================================

    def _load_theme_colors(self) -> None:
        """
        Hamta farger fran ThemeEngine-designsystemet.

        Uppdaterar alla COLOR_*-attribut med tema-varden.
        Fallback: behaller klassattributen om theme_engine saknas.
        """
        if not self.app or not hasattr(self.app, "theme_engine"):
            return
        te = getattr(self.app, "theme_engine", None)
        if te is None or not hasattr(te, "get_color"):
            return
        try:
            for attr, key in self._THEME_KEYS.items():
                current = getattr(self, attr, None)
                fallback = current if current else "#888888"
                setattr(self, attr, te.get_color(key, fallback))
        except Exception as e:
            self.write_log("Tema-farger kunde inte laddas: %s" % e, "error")

    def _restyle_all(self) -> None:
        """
        Applicera aktuella farger pa alla befintliga widgets.

        Uppdaterar paneler, labels, knappar och loggen.
        Anropas vid tema-byte.
        """
        if not self.is_active:
            return
        try:
            # -- Paneler (LabelFrames + rader) -----------------
            for w in self._panels:
                if self.widget_exists(w):
                    try:
                        w.configure(bg=self.COLOR_BG)
                    except Exception:
                        pass

            # -- Huvudlabels -----------------------------------
            for lbl in (
                getattr(self, "status_label", None),
                getattr(self, "time_label", None),
                getattr(self, "folder_label", None),
                getattr(self, "images_count_label", None),
                getattr(self, "videos_count_label", None),
                getattr(self, "size_label", None),
            ):
                if self.widget_exists(lbl):
                    try:
                        lbl.configure(bg=self.COLOR_BG)
                    except Exception:
                        pass

            # -- Statistik-labels ------------------------------
            for lbl in (getattr(self, "stats_labels", None) or {}).values():
                if self.widget_exists(lbl):
                    try:
                        lbl.configure(bg=self.COLOR_BG)
                    except Exception:
                        pass

            # -- Knappar (data-driven, Q2) ---------------------
            for btn, color_attr in (
                (self.generate_btn,     "COLOR_GREEN"),
                (self.preview_btn,      "COLOR_BLUE"),
                (self.open_folder_btn,  "COLOR_GRAY"),
                (self.cancel_btn,       "COLOR_RED"),
            ):
                if self.widget_exists(btn):
                    try:
                        c = getattr(self, color_attr, "#64748b")
                        btn.configure(
                            bg=c,
                            fg=self.COLOR_BTN_FG,
                            activebackground=self._darken(c),
                            activeforeground=self.COLOR_BTN_FG,
                        )
                    except Exception:
                        pass

            # -- Logg ------------------------------------------
            if self.widget_exists(self.log_text):
                try:
                    self.log_text.configure(
                        bg=self.COLOR_LOG_BG,
                        fg=self.COLOR_SUCCESS,
                        insertbackground=self.COLOR_SUCCESS,
                        selectbackground=self.COLOR_BLUE,
                    )
                except Exception:
                    pass
                self._setup_log_tags()

            self.safe_update()
        except Exception:
            pass

    def _setup_log_tags(self) -> None:
        """Satt loggens fargtaggar fran aktuella tema-farger."""
        if not self.widget_exists(self.log_text):
            return
        try:
            self.log_text.tag_configure("error",
                foreground=self.COLOR_RED)
            self.log_text.tag_configure("warning",
                foreground=self.COLOR_WARNING)
            self.log_text.tag_configure("success",
                foreground=self.COLOR_SUCCESS)
            self.log_text.tag_configure("info",
                foreground=self.COLOR_INFO)
            self.log_text.tag_configure("header",
                foreground=self.COLOR_HEADER,
                font=("Consolas", 10, "bold"))
            self.log_text.tag_configure("highlight",
                background=self.COLOR_HIGHLIGHT_BG,
                foreground=self.COLOR_HIGHLIGHT_FG)
            self.log_text.tag_configure("dim",
                foreground=self.COLOR_DIM)
        except Exception as exc:
            self._ui_error("_setup_log_tags", exc)

    def on_theme_changed(self, event=None) -> None:
        """
        Uppdatera alla farger vid tema-byte.

        Laddar nya farger fran ThemeEngine och applicerar dem
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
    # PLUGIN-LIVSCYKEL
    # ==========================================================================

    def init(self, app):
        """
        Plugin-initiering.

        Steg:
          1. Spara app-referens och initiera state
          2. Ladda tema-farger (C1)
          3. Ladda senaste mappar
          4. Skapa UI
          5. Registrera i context
          6. Bind tangentbordsgenvagar
          7. Registrera tema-callback
        """
        self.app              = app
        self.is_active        = True
        self.is_generating    = False
        self.cancel_requested = False
        self.start_time       = None
        self.log_entries      = []

        # Paneler som tema-uppdateras (C1)
        self._panels = []

        # Tema-farger (C1)
        self._load_theme_colors()

        self.recent_folders   = self.load_recent_folders()

        self.create_ui()
        app.context["_controls"] = self
        self.setup_shortcuts()

        # Tema-callback (C1)
        self.register_theme_callback()

    def execute(self, context, log=None) -> dict:
        """Pipeline-passthrough."""
        return context

    # ==========================================================================
    # SENASTE MAPPAR
    # ==========================================================================

    def load_recent_folders(self) -> list:
        """
        Ladda config/recent_folders.json.
        Filtrerar bort mappar som inte finns.
        Returnerar max 10 poster.
        """
        try:
            history = self._history_file()
            if history.exists():
                with open(history, "r", encoding="utf-8") as f:
                    data = json.load(f)
                return [
                    f for f in data.get("folders", [])
                    if Path(f).exists()
                ][:10]
        except Exception:
            pass
        return []

    def save_recent_folders(self) -> None:
        """
        Spara config/recent_folders.json (A9: atomiskt med fsync).
        """
        tmp_path = None
        try:
            history = self._history_file()
            history.parent.mkdir(parents=True, exist_ok=True)

            fd, tmp_str = tempfile.mkstemp(
                dir=history.parent,
                prefix=".%s_" % history.stem,
                suffix=".tmp",
            )
            tmp_path = Path(tmp_str)

            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(
                    {"folders": self.recent_folders[:10]},
                    f, indent=2, ensure_ascii=False
                )
                f.flush()
                os.fsync(f.fileno())   # A9

            os.replace(tmp_path, history)
        except Exception:
            if tmp_path and tmp_path.exists():
                try:
                    tmp_path.unlink()
                except OSError:
                    pass

    def add_recent_folder(self, folder: str) -> None:
        """
        Lagg till mapp i historiken.
        Duplikat tas bort och mappen laggs forst.
        """
        folder = str(folder)
        if folder in self.recent_folders:
            self.recent_folders.remove(folder)
        self.recent_folders.insert(0, folder)
        self.recent_folders = self.recent_folders[:10]
        self.save_recent_folders()
        self.update_recent_menu()

    # ==========================================================================
    # TANGENTBORDSGENVAGAR
    # ==========================================================================

    def setup_shortcuts(self) -> None:
        """
        Bind globala tangentbordsgenvagar.

        Ctrl+G / F5   - Generera
        Ctrl+P        - Forhandsgranska
        Ctrl+O        - Oppna output
        Escape        - Avbryt
        """
        bindings = {
            "<Control-g>": lambda e: self.run_generate(),
            "<Control-G>": lambda e: self.run_generate(),
            "<F5>":        lambda e: self.run_generate(),
            "<Control-p>": lambda e: self.open_preview(),
            "<Control-P>": lambda e: self.open_preview(),
            "<Control-o>": lambda e: self.open_output_folder(),
            "<Control-O>": lambda e: self.open_output_folder(),
            "<Escape>":    lambda e: self.cancel_generation(),
        }
        for key, func in bindings.items():
            try:
                self.app.bind(key, func)
            except Exception:
                pass

    # ==========================================================================
    # UI-BYGGARE
    # ==========================================================================

    def _mk_section(self, parent, text, fill=tk.X, expand=False,
                    pady=(5, 5), padx=10) -> tk.LabelFrame:
        """
        Skapa en standardiserad titulerad sektion (Q1).

        Samlar LabelFrame-boilerplate (bg/fg/font/padx/pady/pack +
        tema-registrering) sa att alla sektioner far identiskt
        utseende utan att upprepa koden.
        """
        f = tk.LabelFrame(
            parent, text=text,
            bg=self.COLOR_BG, fg=self.COLOR_FG,
            font=("Segoe UI", 9),
            padx=12, pady=8,
        )
        f.pack(fill=fill, expand=expand, padx=padx, pady=pady)
        self._panels.append(f)
        return f

    def create_ui(self) -> None:
        """Bygg hela granssnittet och placera i ratt tabb."""
        tab_manager = self.app.context.get("_tab_manager")
        if tab_manager:
            parent = tab_manager.add_tab("controls", "Kontroller")
        else:
            parent = self.app.main_frame

        self._build_main_buttons(parent)
        self._build_quick_actions(parent)
        self._build_progress_section(parent)
        self._build_log_section(parent)
        self._build_stats_section(parent)

    def _build_main_buttons(self, parent) -> None:
        """
        Rad 1: Generera, Avbryt (dold), Forhandsgranska, Oppna output.
        Generera ar gron och stor (primar atgard).
        Avbryt visas bara under aktiv generering.
        """
        frame = self._mk_section(parent, "Atgarder", pady=(8, 4))

        row = tk.Frame(frame, bg=self.COLOR_BG)
        row.pack(fill=tk.X, pady=5)
        self._panels.append(row)

        # Generera (primar)
        self.generate_btn = self._make_btn(
            row,
            "Generera Galleri  (Ctrl+G)",
            self.run_generate,
            "COLOR_GREEN",
            font_size=12, bold=True,
            padx=25, pady=10,
        )
        self.generate_btn.pack(side=tk.LEFT, padx=5)

        # Avbryt (dold tills generering startar)
        self.cancel_btn = self._make_btn(
            row, "Avbryt",
            self.cancel_generation,
            "COLOR_RED",
            padx=15, pady=6,
        )

        # Forhandsgranska
        self.preview_btn = self._make_btn(
            row,
            "Forhandsgranska  (Ctrl+P)",
            self.open_preview,
            "COLOR_BLUE",
            padx=15, pady=6,
        )
        self.preview_btn.pack(side=tk.LEFT, padx=5)

        # Oppna output
        self.open_folder_btn = self._make_btn(
            row,
            "Output  (Ctrl+O)",
            self.open_output_folder,
            "COLOR_GRAY",
            padx=15, pady=6,
        )
        self.open_folder_btn.pack(side=tk.RIGHT, padx=5)

    def _build_quick_actions(self, parent) -> None:
        """
        Rad 2: Senaste mappar (Combobox), Rensa cache, Regenerera.
        """
        frame = self._mk_section(parent, "Snabbatgarder", pady=4)

        row = tk.Frame(frame, bg=self.COLOR_BG)
        row.pack(fill=tk.X)
        self._panels.append(row)

        tk.Label(
            row, text="Senaste mappar:",
            bg=self.COLOR_BG, fg=self.COLOR_MUTED,
            font=("Segoe UI", 9),
        ).pack(side=tk.LEFT, padx=5)

        self.recent_var  = tk.StringVar(value="Valj senaste mapp...")
        self.recent_menu = ttk.Combobox(
            row,
            textvariable=self.recent_var,
            values=self.get_recent_display(),
            state="readonly",
            width=35,
        )
        self.recent_menu.pack(side=tk.LEFT, padx=5)
        self.recent_menu.bind(
            "<<ComboboxSelected>>", self.on_recent_selected
        )

        for text, cmd in [
            ("Regenerera thumbnails", self.regenerate_thumbnails),
            ("Rensa cache",           self.clear_cache),
        ]:
            self._make_btn(row, text, cmd, "COLOR_DARK").pack(
                side=tk.RIGHT, padx=3
            )

    def _build_progress_section(self, parent) -> None:
        """Status-label, progress-bar, info-rad."""
        frame = self._mk_section(parent, "Status", pady=4)

        # Status + tid
        status_row = tk.Frame(frame, bg=self.COLOR_BG)
        status_row.pack(fill=tk.X, pady=(0, 5))
        self._panels.append(status_row)

        self.status_label = tk.Label(
            status_row,
            text="Redo att generera",
            bg=self.COLOR_BG, fg=self.COLOR_MUTED,
            font=("Segoe UI", 10),
        )
        self.status_label.pack(side=tk.LEFT, padx=5)

        self.time_label = tk.Label(
            status_row, text="",
            bg=self.COLOR_BG, fg=self.COLOR_MUTED,
            font=("Segoe UI", 9),
        )
        self.time_label.pack(side=tk.RIGHT, padx=5)

        # Progress-bar
        self.progress_var = tk.DoubleVar()
        ttk.Progressbar(
            frame,
            variable=self.progress_var,
            maximum=100,
            mode="determinate",
            length=400,
        ).pack(fill=tk.X, pady=5)

        # Info-rad
        info_row = tk.Frame(frame, bg=self.COLOR_BG)
        info_row.pack(fill=tk.X, pady=(5, 0))
        self._panels.append(info_row)

        self.folder_label = tk.Label(
            info_row, text="Mapp: -",
            bg=self.COLOR_BG, fg=self.COLOR_MUTED,
            font=("Segoe UI", 9),
        )
        self.folder_label.pack(side=tk.LEFT, padx=5)

        self.images_count_label = tk.Label(
            info_row, text="Bilder: -",
            bg=self.COLOR_BG, fg=self.COLOR_MUTED,
            font=("Segoe UI", 9),
        )
        self.images_count_label.pack(side=tk.LEFT, padx=15)

        self.videos_count_label = tk.Label(
            info_row, text="Videor: -",
            bg=self.COLOR_BG, fg=self.COLOR_MUTED,
            font=("Segoe UI", 9),
        )
        self.videos_count_label.pack(side=tk.LEFT, padx=15)

        self.size_label = tk.Label(
            info_row, text="Storlek: -",
            bg=self.COLOR_BG, fg=self.COLOR_MUTED,
            font=("Segoe UI", 9),
        )
        self.size_label.pack(side=tk.RIGHT, padx=5)

    def _build_log_section(self, parent) -> None:
        """
        Loggfonster med:
        - Rensa / Kopiera / Spara-knappar
        - Sokning (highlight i realtid)
        - Filter per tag
        - Auto-scroll checkbox
        - Text-widget med fargtaggar
        - Mushjul-stod
        """
        frame = self._mk_section(parent, "Logg", fill=tk.BOTH,
                                 expand=True, pady=4)

        # -- Kontroll-rad --------------------------------------
        controls = tk.Frame(frame, bg=self.COLOR_BG)
        controls.pack(fill=tk.X, pady=(0, 5))
        self._panels.append(controls)

        for text, cmd in [
            ("Rensa",    self.clear_log),
            ("Kopiera",  self.copy_log),
            ("Spara",    self.save_log),
        ]:
            self._make_btn(controls, text, cmd, "COLOR_DARK").pack(
                side=tk.LEFT, padx=2
            )

        # Sok
        tk.Label(
            controls, text="Sok:",
            bg=self.COLOR_BG, fg=self.COLOR_MUTED,
            font=("Segoe UI", 10),
        ).pack(side=tk.LEFT, padx=(20, 2))

        self.search_var = tk.StringVar()
        # P14-1: trace_add() istf det borttagna trace("w", ...).
        # Tcl/Tk 9.0 (Python 3.14) stoder inte langre "trace variable".
        self.search_var.trace_add("write", self.on_search_changed)
        ttk.Entry(
            controls, textvariable=self.search_var, width=20
        ).pack(side=tk.LEFT, padx=2)

        # Filter
        tk.Label(
            controls, text="Filter:",
            bg=self.COLOR_BG, fg=self.COLOR_MUTED,
            font=("Segoe UI", 9),
        ).pack(side=tk.LEFT, padx=(15, 2))

        self.filter_var = tk.StringVar(value="Alla")
        filter_combo = ttk.Combobox(
            controls,
            textvariable=self.filter_var,
            values=["Alla", "Info", "Success", "Varningar", "Fel"],
            state="readonly",
            width=10,
        )
        filter_combo.pack(side=tk.LEFT, padx=2)
        filter_combo.bind("<<ComboboxSelected>>", self.on_filter_changed)

        # Auto-scroll
        self.auto_scroll_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            controls,
            text="Auto-scroll",
            variable=self.auto_scroll_var,
        ).pack(side=tk.RIGHT, padx=5)

        # -- Text + scrollbar ----------------------------------
        log_container = tk.Frame(frame, bg=self.COLOR_BG)
        log_container.pack(fill=tk.BOTH, expand=True)
        self._panels.append(log_container)

        self.log_text = tk.Text(
            log_container,
            height=12,
            bg=self.COLOR_LOG_BG,
            fg=self.COLOR_SUCCESS,
            font=("Consolas", 10),
            wrap=tk.WORD,
            insertbackground=self.COLOR_SUCCESS,
            selectbackground=self.COLOR_BLUE,
            relief="flat",
        )
        self.log_text.pack(fill=tk.BOTH, expand=True, side=tk.LEFT)

        sb = ttk.Scrollbar(log_container, command=self.log_text.yview)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_text.config(yscrollcommand=sb.set)

        # Mushjul (3 enheter)
        self.log_text.bind(
            "<MouseWheel>",
            lambda e: self.log_text.yview_scroll(
                -1 * (e.delta // 120) * 3 if hasattr(e, "delta") else -3,
                "units"
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

        # -- Fargtaggar (tema-styrda, C1) ----------------------
        self._setup_log_tags()

        # -- Initial logg --------------------------------------
        self.write_log("=" * 50, "header")
        self.write_log("Galleri Generator", "header")
        self.write_log("=" * 50, "header")
        self.write_log("")
        self.write_log(
            "+ %d plugins laddade" % len(self.app.plugins), "success"
        )
        self.write_log(
            "Genvagar: Ctrl+G = Generera  |  Ctrl+P = Forhandsgranska  "
            "|  Ctrl+O = Output  |  Escape = Avbryt",
            "dim"
        )
        self.write_log("")
        self.write_log(
            "Redo. Valj bildmapp i Installningar och klicka Generera.",
            "info"
        )
        self.write_log("")

    def _build_stats_section(self, parent) -> None:
        """Statistikrad: Bilder | Videor | Tid | Output-storlek."""
        frame = self._mk_section(parent, "Senaste generering",
                                 pady=(4, 8))

        row = tk.Frame(frame, bg=self.COLOR_BG)
        row.pack(fill=tk.X)
        self._panels.append(row)

        self.stats_labels = {}
        for stat in ("Bilder", "Videor", "Tid", "Output-storlek"):
            col = tk.Frame(row, bg=self.COLOR_BG)
            col.pack(side=tk.LEFT, padx=15)
            self._panels.append(col)
            tk.Label(
                col, text="%s:" % stat,
                bg=self.COLOR_BG, fg=self.COLOR_MUTED,
                font=("Segoe UI", 9),
            ).pack(side=tk.LEFT)
            lbl = tk.Label(
                col, text="-",
                bg=self.COLOR_BG, fg=self.COLOR_FG,
                font=("Segoe UI", 10, "bold"),
            )
            lbl.pack(side=tk.LEFT, padx=5)
            self.stats_labels[stat] = lbl

    # ==========================================================================
    # KNAPP-HJALPARE
    # ==========================================================================

    def _make_btn(
        self, parent, text, command, color_attr,
        font_size=9, bold=False, **kwargs
    ) -> tk.Button:
        """
        Gemensam knapp-fabrik med hover-effekt.

        color_attr ar ATTRIBUTNAMN (strang) - vardet hamtas via
        getattr() sa att knappen foljer aktuella tema-farger.
        Textfarg: COLOR_BTN_FG (vit via "selection_fg" - lasbar pa
        fargade knappar i bada teman).

        Q2: hover/leave loser fargen dynamiskt ur nyaste temat, sa att
        en hover efter tema-byte aldrig återstaller en gammal bygg-farg.

        Parametrar:
            parent:     foraldra-widget
            text:       knapptexten
            command:    callback
            color_attr: attributnamn (strang) for bakgrundsfargen
            font_size:  teckenstorlek
            bold:       fet stil
            **kwargs:   padx, pady, width etc.
        """
        color  = getattr(self, color_attr, "#64748b")
        weight = "bold" if bold else "normal"
        darker = self._darken(color)

        def _resolved():
            c = getattr(self, color_attr, "#64748b")
            return c, self._darken(c)

        btn = tk.Button(
            parent,
            text=text,
            command=command,
            bg=color,
            fg=self.COLOR_BTN_FG,
            font=("Segoe UI", font_size, weight),
            cursor="hand2",
            relief="flat",
            activebackground=darker,
            activeforeground=self.COLOR_BTN_FG,
            **kwargs,
        )
        btn.bind("<Enter>", lambda e: btn.config(bg=_resolved()[1]))
        btn.bind("<Leave>", lambda e: btn.config(bg=_resolved()[0]))
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

    # ==========================================================================
    # SENASTE MAPPAR - UI
    # ==========================================================================

    def get_recent_display(self) -> list:
        """Hamta visningsnamn (mappnamn) for senaste mappar."""
        return [Path(f).name for f in self.recent_folders]

    def update_recent_menu(self) -> None:
        """Uppdatera combobox med aktuella senaste mappar."""
        if self.widget_exists(self.recent_menu):
            self.recent_menu["values"] = self.get_recent_display()

    def on_recent_selected(self, event) -> None:
        """Hantera val fran senaste mappar-comboboxen."""
        idx = self.recent_menu.current()
        if 0 <= idx < len(self.recent_folders):
            folder = self.recent_folders[idx]
            settings = self.app.context.get("_settings")
            if settings and hasattr(settings, "folder_var"):
                settings.folder_var.set(folder)
                if hasattr(settings, "refresh_gallery"):
                    try:
                        settings.refresh_gallery()
                    except Exception:
                        pass
            self.write_log("Valde mapp: %s" % folder, "info")
            self.update_counts()
        self.recent_var.set("Valj senaste mapp...")

    # ==========================================================================
    # LOGG
    # ==========================================================================

    def write_log(self, message: str, tag: str = None) -> None:
        """
        Skriv en rad till loggen med valfri farg-tag.
        Tradsaker: om anropad utanfor main thread anvands app.after(0, ...).
        Taggar: error, warning, success, info, header, dim
        Tidsstampel lagras for sokning/filtrering.

        P14-3: kan aldrig resa undantag. Om loggwidgeten saknas (UI:t
        avbrutet/avstangt) rapporteras det EN gang till filloggaren och
        anropet returnerar tyst - ingen tk-callback-krasch, ingen
        stderr-skrivning (WinError 6 under pythonw).
        """
        if not self.is_active:
            return

        # Tradsaker routing
        if threading.current_thread() is not threading.main_thread():
            try:
                self.app.after(
                    0, lambda m=message, t=tag: self.write_log(m, t)
                )
            except Exception:
                pass
            return

        try:
            if not self.widget_exists(self.log_text):
                self._ui_error(
                    "Loggwidgeten saknas - UI-sektionen 'Logg' byggdes "
                    "aldrig klart. Meddelanden gar endast till logs/."
                )
                return
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            display   = (
                "[%s] %s" % (timestamp, message)
                if tag in ("error", "warning", "success")
                else message
            )
            self.log_entries.append({
                "message":   display,
                "tag":       tag,
                "timestamp": timestamp,
                "raw":       message,
            })
            if tag:
                self.log_text.insert(tk.END, "%s\n" % display, tag)
            else:
                self.log_text.insert(tk.END, "%s\n" % display)
            auto = getattr(self, "auto_scroll_var", None)
            if auto is not None and auto.get():
                self.log_text.see(tk.END)
            self._trim_log()
            self.safe_update()
        except Exception as exc:
            # Aldrig tyst (B1/19A) - men aldrig heller en ny krasch:
            # rapporten gar till filloggaren, inte tillbaka till UI:t.
            self._ui_error("write_log", exc)

    def _ui_error(self, where: str, exc=None) -> None:
        """
        Rapportera ett UI-fel EN gang per plats (P14-3).

        Skriver till filloggaren (advanced_logger via BasePlugin.log_error)
        - ALDRIG till en tk-widget och ALDRIG till stderr. Darmed kan ett
        trasigt/halvbyggt UI inte orsaka en ny krasch (tk-callback ->
        print -> OSError WinError 6) och inte heller loggspam.

        Parametrar:
            where: var felet skedde (metodnamn/beskrivning)
            exc:   undantag (valfritt - None ger en ren FEL-rad)
        """
        try:
            seen = getattr(self, "_ui_error_seen", None)
            if seen is None:
                seen = set()
                self._ui_error_seen = seen
            if where in seen:
                return
            seen.add(where)
            if exc is None:
                self.log_error(where)
            else:
                self.log_error("%s: %s" % (where, exc), exc)
        except Exception:
            pass

    def _trim_log(self) -> None:
        """
        Begransa loggen till _MAX_LOG_ENTRIES rader (Q3).

        Raderar de aldsta raderna i text-widgeten och motsvarande
        aldsta poster i self.log_entries sa att filtrering/spara
        forblir konsekventa - ingen oandlig minnestillvaxt vid
        langa korningar.
        """
        if not self.is_active:
            return
        try:
            if not self.widget_exists(self.log_text):
                return
            line_count = int(self.log_text.index("end-1c").split(".")[0])
            excess     = line_count - self._MAX_LOG_ENTRIES
            if excess > 0:
                self.log_text.delete("1.0", "%d.0" % (excess + 1))
                if excess < len(self.log_entries):
                    del self.log_entries[:excess]
                else:
                    self.log_entries.clear()
        except Exception as exc:
            self._ui_error("_trim_log", exc)

    def on_search_changed(self, *args) -> None:
        """
        Realtids-sokning i loggen - highlight pa traffar.

        P14-1: anropas nu via trace_add("write", ...) som skickar
        (variabelnamn, index, mode) - darfor *args.
        P14-3: gardad mot saknad widget (halvbyggt/avstangt UI).
        """
        try:
            if not self.widget_exists(self.log_text):
                return
            if getattr(self, "search_var", None) is None:
                return
            self.log_text.tag_remove("highlight", "1.0", tk.END)
            query = self.search_var.get().lower().strip()
            if not query:
                return
            start = "1.0"
            while True:
                pos = self.log_text.search(
                    query, start, tk.END, nocase=True
                )
                if not pos:
                    break
                end   = "%s+%dc" % (pos, len(query))
                self.log_text.tag_add("highlight", pos, end)
                start = end
        except Exception as exc:
            self._ui_error("on_search_changed", exc)

    def on_filter_changed(self, event) -> None:
        """Filtrera loggen per tag-typ (P14-3: gardad)."""
        tag_map = {
            "Alla":      None,
            "Info":      "info",
            "Success":   "success",
            "Varningar": "warning",
            "Fel":       "error",
        }
        if getattr(self, "filter_var", None) is None:
            return
        selected = tag_map.get(self.filter_var.get())
        try:
            if not self.widget_exists(self.log_text):
                return
            self.log_text.delete("1.0", tk.END)
            for entry in self.log_entries:
                if selected is None or entry.get("tag") == selected:
                    t = entry.get("tag")
                    if t:
                        self.log_text.insert(
                            tk.END, "%s\n" % entry["message"], t
                        )
                    else:
                        self.log_text.insert(
                            tk.END, "%s\n" % entry["message"]
                        )
        except Exception as exc:
            self._ui_error("on_filter_changed", exc)

    def clear_log(self) -> None:
        """Rensa logg-textfaltet och log_entries."""
        if not self.is_active:
            return
        try:
            if self.widget_exists(self.log_text):
                self.log_text.delete("1.0", tk.END)
                self.log_entries.clear()
                self.write_log("Logg rensad", "info")
        except Exception as exc:
            self._ui_error("clear_log", exc)

    def copy_log(self) -> None:
        """Kopiera hela loggens innehall till urklipp."""
        if not self.is_active:
            return
        try:
            if self.widget_exists(self.log_text):
                content = self.log_text.get("1.0", tk.END)
                self.app.clipboard_clear()
                self.app.clipboard_append(content)
                self.write_log("Logg kopierad till urklipp", "success")
        except Exception as exc:
            self._ui_error("copy_log", exc)

    def save_log(self) -> None:
        """Spara loggen till .txt eller .html."""
        if not self.is_active:
            return
        try:
            filename = filedialog.asksaveasfilename(
                defaultextension=".txt",
                filetypes=[
                    ("Textfil", "*.txt"),
                    ("HTML",    "*.html"),
                    ("Alla",    "*.*"),
                ],
                initialfile=(
                    "gallery_log_%s.txt"
                    % datetime.now().strftime("%Y%m%d_%H%M%S")
                ),
            )
            if not filename:
                return
            if filename.endswith(".html"):
                self.save_log_as_html(filename)
            else:
                content = (
                    self.log_text.get("1.0", tk.END)
                    if self.widget_exists(self.log_text)
                    else "\n".join(
                        e.get("message", "") for e in self.log_entries
                    )
                )
                with open(filename, "w", encoding="utf-8") as f:
                    f.write(content)
            self.write_log("Logg sparad: %s" % filename, "success")
        except Exception as e:
            self.write_log("Kunde inte spara logg: %s" % e, "error")
            self._ui_error("save_log", e)

    def save_log_as_html(self, filename: str) -> None:
        """Exportera loggen som HTML-fil med CSS-farger."""
        html = (
            "<!DOCTYPE html>\n<html>\n<head>\n"
            '<meta charset="UTF-8">\n'
            "<title>Galleri Generator Logg</title>\n"
            "<style>\n"
            "body{background:%s;color:%s;"
            "font-family:Consolas,monospace;padding:20px}\n"
            ".error{color:%s}.warning{color:%s}"
            ".success{color:%s}\n"
            ".info{color:%s}.header{color:%s;"
            "font-weight:bold}.dim{color:%s}\n"
            "</style>\n</head>\n<body>\n<pre>\n"
            % (
                self.COLOR_LOG_BG,
                self.COLOR_SUCCESS,
                self.COLOR_RED,
                self.COLOR_WARNING,
                self.COLOR_SUCCESS,
                self.COLOR_INFO,
                self.COLOR_HEADER,
                self.COLOR_DIM,
            )
        )
        for entry in self.log_entries:
            tag = entry.get("tag", "")
            msg = (
                entry["message"]
                .replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
            )
            if tag:
                html += '<span class="%s">%s</span>\n' % (tag, msg)
            else:
                html += "%s\n" % msg
        html += "</pre>\n</body>\n</html>"
        with open(filename, "w", encoding="utf-8") as f:
            f.write(html)

    # ==========================================================================
    # STATUS OCH PROGRESS
    # ==========================================================================

    def update_status(self, message: str, status_type: str = "info") -> None:
        """
        Uppdatera statuslabeln med ikon och farg.
        status_type: info | success | warning | error | working
        """
        if not self.is_active:
            return
        icons  = {
            "info": "*", "success": "OK",
            "warning": "!", "error": "X", "working": ">",
        }
        colors = {
            "info": self.COLOR_MUTED, "success": self.COLOR_SUCCESS,
            "warning": self.COLOR_WARNING, "error": self.COLOR_RED,
            "working": self.COLOR_BLUE,
        }
        try:
            if self.widget_exists(self.status_label):
                self.status_label.config(
                    text="%s %s" % (icons.get(status_type, "*"), message),
                    fg=colors.get(status_type, self.COLOR_MUTED),
                )
        except Exception as exc:
            self._ui_error("update_status", exc)

    def update_counts(self) -> None:
        """Uppdatera info-rad: mapp, bilder, videor, total storlek."""
        if not self.is_active:
            return
        try:
            gallery_view = self.app.context.get("_gallery_view")
            settings     = self.app.context.get("_settings")

            if gallery_view and hasattr(gallery_view, "image_files"):
                if self.widget_exists(self.images_count_label):
                    self.images_count_label.config(
                        text="Bilder: %d" % len(gallery_view.image_files)
                    )

            if settings and hasattr(settings, "folder_var"):
                folder = settings.folder_var.get()
                if folder and Path(folder).exists():
                    p = Path(folder)
                    if self.widget_exists(self.folder_label):
                        self.folder_label.config(text="Mapp: %s" % p.name)

                    video_exts = {".mp4", ".avi", ".mov", ".qt", ".mkv", ".webm"}
                    n_videos = sum(
                        1 for f in p.iterdir()
                        if f.is_file()
                        and f.suffix.lower() in video_exts
                    )
                    if self.widget_exists(self.videos_count_label):
                        self.videos_count_label.config(
                            text="Videor: %d" % n_videos
                        )

                    total_bytes = sum(
                        f.stat().st_size
                        for f in p.iterdir() if f.is_file()
                    )
                    mb = total_bytes / (1024 * 1024)
                    if self.widget_exists(self.size_label):
                        if mb > 1024:
                            self.size_label.config(
                                text="Storlek: %.1f GB" % (mb / 1024)
                            )
                        else:
                            self.size_label.config(
                                text="Storlek: %.1f MB" % mb
                            )
        except Exception as exc:
            self._ui_error("update_counts", exc)

    def update_progress(self, value: float, message: str = None) -> None:
        """
        Uppdatera progress-bar och tid-label.
        Beraknar ETA om start_time ar satt och value > 0.
        """
        if not self.is_active:
            return
        try:
            if getattr(self, "progress_var", None) is not None:
                self.progress_var.set(value)
            if message:
                self.update_status(message, "working")
            if self.start_time and value > 0 and self.widget_exists(
                self.time_label
            ):
                elapsed   = (datetime.now() - self.start_time).total_seconds()
                estimated = elapsed / (value / 100)
                remaining = estimated - elapsed
                if remaining > 60:
                    self.time_label.config(
                        text="%d:%02d kvar"
                        % (int(remaining // 60), int(remaining % 60))
                    )
                else:
                    self.time_label.config(
                        text="%ds kvar" % int(remaining)
                    )
            self.safe_update()
        except Exception as exc:
            self._ui_error("update_progress", exc)

    # ==========================================================================
    # ATGARDER
    # ==========================================================================

    def open_output_folder(self) -> None:
        """Oppna output-mappen i OS-filhanterare."""
        try:
            settings = self.app.context.get("_settings")
            folder   = (
                settings.folder_var.get()
                if settings and hasattr(settings, "folder_var") else None
            )
            if folder:
                output = (
                    Path(__file__).parent.parent / "out" / Path(folder).name
                )
                if output.exists():
                    self._open_in_os(output)
                    return
            out = Path(__file__).parent.parent / "out"
            out.mkdir(parents=True, exist_ok=True)
            self._open_in_os(out)
        except Exception as e:
            self.write_log("Kunde inte oppna mapp: %s" % e, "error")

    def open_preview(self) -> None:
        """Oppna index.html i webblasaren."""
        try:
            settings = self.app.context.get("_settings")
            folder   = (
                settings.folder_var.get()
                if settings and hasattr(settings, "folder_var") else None
            )
            if not folder:
                messagebox.showwarning(
                    "Varning", "Valj en bildmapp i Installningar."
                )
                return
            index = (
                Path(__file__).parent.parent
                / "out" / Path(folder).name / "index.html"
            )
            if index.exists():
                webbrowser.open(index.as_uri())
                self.write_log(
                    "Oppnar forhandsgranskning i webblasare", "info"
                )
            else:
                messagebox.showinfo(
                    "Info",
                    "Galleriet ar inte genererat annu.\n\n"
                    "Klicka 'Generera Galleri' forst."
                )
        except Exception as e:
            self.write_log(
                "Kunde inte oppna forhandsgranskning: %s" % e, "error"
            )

    def clear_cache(self) -> None:
        """Rensa thumbnails/-mappen for aktuellt galleri."""
        try:
            settings = self.app.context.get("_settings")
            folder   = (
                settings.folder_var.get()
                if settings and hasattr(settings, "folder_var") else None
            )
            if not folder:
                self.write_log("Ingen mapp vald - inget att rensa", "info")
                return
            thumb_dir = (
                Path(__file__).parent.parent
                / "out" / Path(folder).name / "thumbnails"
            )
            if thumb_dir.exists():
                shutil.rmtree(thumb_dir)
                self.write_log("Cache rensad: %s" % thumb_dir, "success")
                messagebox.showinfo("Klart", "Thumbnail-cache rensad!")
            else:
                self.write_log("Ingen cache hittades", "info")
        except Exception as e:
            self.write_log("Kunde inte rensa cache: %s" % e, "error")

    def regenerate_thumbnails(self) -> None:
        """Rensa cache och kor om generering."""
        if messagebox.askyesno(
            "Bekrafta",
            "Regenerera alla thumbnails?\n"
            "Detta raderar cachen och genererar galleriet igen.",
        ):
            self.clear_cache()
            self.run_generate()

    def cancel_generation(self) -> None:
        """Avbryt pagaende generering."""
        if self.is_generating:
            self.cancel_requested = True
            self.write_log("Avbryter...", "warning")
            self.update_status("Avbryter...", "warning")

    # ==========================================================================
    # PIPELINE
    # ==========================================================================

    def _ui_ready(self, action: str) -> bool:
        """
        Kontrollera att alla widgets som atgarden behover faktiskt finns (P14-4).

        Returnerar True om UI:t ar komplett. Annars visas EN tydlig
        felruta (namngiven atgard + vilken widget som saknas) och felet
        loggas till logs/ - i stallet for en AttributeError inne i en
        tk-callback som under pythonw slutar i OSError WinError 6.
        """
        needed = {
            "progress_var": self.progress_var,
            "cancel_btn":   self.cancel_btn,
            "generate_btn": self.generate_btn,
        }
        missing = [
            name for name, widget in needed.items()
            if widget is None
        ]
        if not missing:
            return True

        detail = "Saknade UI-delar: %s" % ", ".join(missing)
        self._ui_error("%s avbrots - %s" % (action, detail))
        try:
            messagebox.showerror(
                "Ofullstandigt granssnitt",
                "%s kan inte starta.\n\n%s\n\n"
                "Orsaken star i loggen (flik Logg eller logs/).\n"
                "Starta om programmet - om felet kvarstar, klistra in\n"
                "loggfilen i chatten."
                % (action, detail)
            )
        except Exception:
            pass
        return False

    def run_generate(self) -> None:
        """
        Starta galleri-generering.
        Validerar mapp, lagger till i historik och
        startar pipeline i bakgrundstrad.
        """
        if not self.is_active or self.is_generating:
            if self.is_generating:
                self.write_log("Generering pagar redan!", "warning")
            return

        # P14-4: utan komplett UI blir det en tydlig rapport i stallet
        # for en krasch i tk-callbacken.
        if not self._ui_ready("Generering"):
            return

        settings = self.app.context.get("_settings")
        if not settings or not hasattr(settings, "folder_var"):
            messagebox.showwarning("Varning", "Installningsplugin saknas.")
            return

        folder = settings.folder_var.get()
        if not folder or not Path(folder).exists():
            messagebox.showwarning(
                "Varning", "Valj en giltig bildmapp i Installningar."
            )
            return

        self.add_recent_folder(folder)

        self.is_generating    = True
        self.cancel_requested = False
        self.start_time       = datetime.now()

        self.update_counts()
        self.update_status("Startar...", "working")
        self.progress_var.set(0)

        # Visa Avbryt
        self.cancel_btn.pack(side=tk.LEFT, padx=5)
        self._set_buttons_state("disabled")
        self.cancel_btn.config(state="normal")

        self.write_log("")
        self.write_log("=" * 50, "header")
        self.write_log("Genererar: %s" % Path(folder).name, "header")
        self.write_log("=" * 50, "header")

        threading.Thread(
            target=self._generate_thread,
            daemon=True,
            name="GenerateThread",
        ).start()

    def _generate_thread(self) -> None:
        """
        Worker-trad for pipeline-korning.
        Pipeline kors DIREKT i traden (inte via app.after).
        All UI-uppdatering via app.after(0, ...).
        """
        try:
            def progress_callback(value, msg=None):
                if self.cancel_requested:
                    raise RuntimeError("Avbrutet av anvandaren")
                self.app.after(
                    0, lambda v=value, m=msg: self.update_progress(v, m)
                )

            self.app.context["progress_callback"] = progress_callback
            self.app.context["cancel_check"]      = lambda: self.cancel_requested

            # A previous export on disk is not evidence this run succeeded.
            self.app.context['_gallery_generated'] = False
            self.app.run_pipeline(self.write_log)
            generated = self.app.context.get('html_output')
            if not self.app.context.get('_gallery_generated') or not generated or not Path(generated).is_file():
                raise RuntimeError('Inget nytt galleri skapades. Kontrollera källmapp och att HTML-generatorn är aktiverad.')

            self.app.after(0, self._on_generation_complete)
        except Exception as e:
            self.app.after(
                0, lambda err=e: self._on_generation_error(err)
            )

    def _on_generation_complete(self) -> None:
        """Hantera slutford generering (kors i main thread)."""
        if not self.is_active:
            return
        elapsed = (datetime.now() - self.start_time).total_seconds()

        self.write_log("")
        self.write_log("KLART!", "success")
        self.write_log(
            "Tid: %d:%02d" % (int(elapsed // 60), int(elapsed % 60)),
            "info"
        )

        self.update_stats(elapsed)
        self.update_status("Klart!", "success")
        if getattr(self, "progress_var", None) is not None:
            self.progress_var.set(100)
        if self.widget_exists(self.time_label):
            self.time_label.config(text="%ds" % int(elapsed))

        self._finish_generation()

        # Oppna webblasare med fordrojning for stabilitet
        output = self.app.context.get("output_path")
        if output:
            index = Path(output) / "index.html"
            if index.exists():
                self.app.after(
                    100, lambda: webbrowser.open(index.as_uri())
                )

        messagebox.showinfo(
            "Klart!",
            "Galleriet har genererats!\n\nTid: %ds" % int(elapsed)
        )

    def _on_generation_error(self, error: Exception) -> None:
        """Hantera fel under generering (kors i main thread)."""
        if not self.is_active:
            return
        self.write_log("\nFEL: %s" % error, "error")
        self.write_log(traceback.format_exc(), "error")
        self.update_status("Fel: %s" % error, "error")
        self._finish_generation()

        if "Avbrutet" in str(error):
            messagebox.showinfo(
                "Avbrutet", "Genereringen avbrots av anvandaren."
            )
        else:
            messagebox.showerror("Fel", str(error))

    def _finish_generation(self) -> None:
        """Aterstall UI-state efter generering."""
        self.is_generating    = False
        self.cancel_requested = False
        self.start_time       = None
        try:
            if self.widget_exists(self.cancel_btn):
                self.cancel_btn.pack_forget()
            self._set_buttons_state("normal")
        except Exception as exc:
            self._ui_error("_finish_generation", exc)

    def update_stats(self, elapsed: float) -> None:
        """Uppdatera statistik-labels efter generering."""
        try:
            gallery_view = self.app.context.get("_gallery_view")
            settings     = self.app.context.get("_settings")

            if gallery_view and hasattr(gallery_view, "image_files"):
                self.stats_labels["Bilder"].config(
                    text=str(len(gallery_view.image_files))
                )

            processed_videos = self.app.context.get("processed_videos", [])
            self.stats_labels["Videor"].config(
                text=str(len(processed_videos))
            )

            if elapsed > 60:
                time_str = "%dm %ds" % (int(elapsed // 60), int(elapsed % 60))
            else:
                time_str = "%ds" % int(elapsed)
            self.stats_labels["Tid"].config(text=time_str)

            if settings and hasattr(settings, "folder_var"):
                folder = settings.folder_var.get()
                if folder:
                    output = (
                        Path(__file__).parent.parent
                        / "out" / Path(folder).name
                    )
                    if output.exists():
                        total = sum(
                            f.stat().st_size
                            for f in output.rglob("*") if f.is_file()
                        )
                        mb = total / (1024 * 1024)
                        if mb > 1024:
                            self.stats_labels["Output-storlek"].config(
                                text="%.1f GB" % (mb / 1024)
                            )
                        else:
                            self.stats_labels["Output-storlek"].config(
                                text="%.1f MB" % mb
                            )
        except Exception as e:
            self.write_log(
                "Statistik-uppdatering misslyckades: %s" % e, "warning"
            )

    # ==========================================================================
    # HJALPMETODER
    # ==========================================================================

    def _set_buttons_state(self, state: str) -> None:
        """Aktivera/inaktivera primarknappar."""
        for btn in (
            self.generate_btn,
            self.preview_btn,
            self.open_folder_btn,
        ):
            if self.widget_exists(btn):
                try:
                    btn.config(state=state)
                except tk.TclError:
                    pass

    def _open_in_os(self, path: Path) -> None:
        """
        Oppna en sokvag i OS-filhanteraren.
        Anvander Popen (blockerar inte).
        """
        try:
            if sys.platform == "win32":
                subprocess.Popen(["explorer", str(path)])
            elif sys.platform == "darwin":
                subprocess.Popen(["open", str(path)])
            else:
                subprocess.Popen(["xdg-open", str(path)])
        except Exception as e:
            self.write_log("Kunde inte oppna %s: %s" % (path.name, e), "error")

    def widget_exists(self, widget) -> bool:
        """
        Returnerar True om widget ar skapad och inte forstord.

        P14-5: fangar Exception (inte bara TclError) - en trasig eller
        redan forstord referens ska aldrig propagera ut i en tk-callback.
        """
        try:
            return bool(widget and widget.winfo_exists())
        except Exception:
            return False

    def safe_update(self) -> None:
        """Saker update_idletasks - faller tyst om fonstret stangs."""
        if self.is_active and self.app:
            try:
                if self.app.winfo_exists():
                    self.app.update_idletasks()
            except tk.TclError:
                pass

    def cleanup(self) -> None:
        """Stada upp vid stangning."""
        self.is_active        = False
        self.cancel_requested = True
