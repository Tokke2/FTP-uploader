#!/usr/bin/env python3
# ============================================================
# Plugin: CSS-redigerare
# ============================================================
# FIL:       plugins/custom_css_editor.py
# PLATS:     plugins/ (ftp_gallery_uploader/plugins/custom_css_editor.py)
# Klass:     CustomCSSEditor(BasePlugin)
# PRIORITY:  32
# VERSION:   2.4.0
# AUTHOR:    Rickard Längkvist
# COPYRIGHT: Copyright (c) <år> Rickard Längkvist (dynamiskt år,
#            se COPYRIGHT-konstanten nedan)
#
# ÄNDRINGAR v2.3.0 → v2.4.0 (arv från BasePlugin):
#   [A1]      Tar bort dubblerade hjälpmetoder (log/log_error/
#             load_config/save_config/widget_exists/safe_after/
#             safe_widget_config) - filen ärver dem nu från
#             BasePlugin v1.3.0 och får log_ui()/log_lifecycle()
#             gratis. Privata _bind_mousewheel/_make_button/_darken
#             behålls (olika namn/signatur än basklassen).
#
# ÄNDRINGAR v2.2.0 → v2.3.0 (krav från spec v4.5.0):
#   [B1]      Inga f-strings – ALL %-formatering (logganrop,
#             dialoger, statusmeddelanden, HTML-byggare,
#             _darken-retur, insert_at_cursor/_insert_snippet)
#   [B1]      Inga hardkodade hex-farger i widgets – nya konstanter
#             COLOR_PREVIEW_BANNER, COLOR_SNIPPET, COLOR_TEMPLATE,
#             COLOR_BTN_IMPORT/EXPORT, COLOR_EXAMPLE_BTN;
#             "white" -> COLOR_FG i _make_button
#   [B3]      AUTHOR + COPYRIGHT (dynamiskt år) + PLATS i header
#   [A9]      save_config: komplett atomiskt monster
#             (mkstemp -> fdopen -> flush -> fsync -> os.replace)
#   [A10]     load_config/save_config anvander helpers.get_config_path()
#             (fallback till projektrotens config/ om helpers saknas)
#   [C4]      Emoji borttagen ur tabb-ikon (add_tab utan icon -
#             konsekvent med tab_manager v2.2.0)
#
# BEVARAT FRÅN v2.2.0:
#   Ingen print() - all loggning via self.log()
#   log() och log_error() egna metoder
#   load_config/save_config egna metoder (atomisk)
#   widget_exists() egen metod
#   safe_after() egen metod
#   safe_widget_config() egen metod
#   bind_mousewheel() egen metod
#   make_button() -> _make_button() (intern standard)
#   register_theme_callback() -> app.bind("<<ThemeChanged>>")
#   _build_toolbar: tk.Frame(bg=...) istf ttk.Frame
#   _build_snippets_tab: tk.Frame(bg=...) container
#   subprocess.Popen for webblasare (ej webbrowser direkt)
#   _preview: Popen istf webbrowser.open (blockerar ej)
#   save_config: atomisk skrivning (tmp -> replace)
#   cleanup: is_active=False
#   is_active initieras i init()
#   Alla except-block loggar via self.log()
#   PRIORITY 32 (efter html_generator=30)
#
# ANSVARAR FOR:
#   - CSS-redigering med syntax-highlighting
#   - HTML header/footer-injektion
#   - CSS-mallar (default/dark/light/minimal/colorful)
#   - Import/Export av CSS-filer
#   - Snippets (fardiga CSS-bitar)
#   - Forhandsgranskning i webblasare
#   - CSS-minifiering (auto + manuell)
#   - Sparar till config/css_templates.json
#
# CONTEXT SOM LASES:
#   'processed_images'   - for forhandsgranskning
#
# CONTEXT SOM SATTS:
#   'custom_css'         - CSS-strang (minifierad om aktiverat)
#   'custom_html_header' - HTML for <head>
#   'custom_html_footer' - HTML for </body>
#   '_css_editor'        - self
#
# IMPORTER:
#   tkinter as tk, ttk, messagebox, filedialog, simpledialog
#   json, os, subprocess, sys, tempfile
#   pathlib.Path
#   datetime.datetime
#   re
#   .base_plugin: BasePlugin
#   helpers: get_config_path (valfritt, A10)
# ============================================================


import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog
import json
import os
import re
import sys
import subprocess
import tempfile
from pathlib import Path
from datetime import datetime

from .base_plugin import BasePlugin

# -- Helpers (valfritt – för config-sökväg, A10) ---------------
try:
    from helpers import get_config_path
    _HAS_HELPERS = True
except ImportError:
    _HAS_HELPERS = False


class CustomCSSEditor(BasePlugin):
    """
    CSS- och HTML-editor for gallerianpassning.

    Skapar en tabb med:
      - CSS-textredigerare (morkt tema, Consolas, syntax-hl)
      - HTML header/footer-redigerare
      - Fardiga mallar (default/dark/light/minimal/colorful)
      - Snippets-panel
      - Import/export
      - CSS-minifiering (auto + manuell)
      - Forhandsgranskning i webblasare

    v2.4.0:
    - Arver logg-/config-/widget-hjälpmetoder från BasePlugin

    v2.3.0:
    - Inga f-strings / hardkodade farger (B1) - COLOR_*-konstanter
    - Atomisk skrivning med fsync (A9)
    - config/ via helpers (A10)
    """

    PLUGIN_NAME = "CSS-redigerare"
    PRIORITY    = 32
    VERSION     = "2.4.0"
    AUTHOR      = "Rickard Längkvist"
    COPYRIGHT   = "Copyright (c) %d %s" % (datetime.now().year, "Rickard Längkvist")
    TAB_NAME    = "CSS"

    # -- Konfiguration -----------------------------------------
    PREVIEW_FILE = Path("temp_preview.html")

    # -- Editor-farger -----------------------------------------
    EDITOR_BG    = "#0d1117"
    EDITOR_FG    = "#c9d1d9"
    EDITOR_SEL   = "#264f78"
    EDITOR_FONT  = ("Consolas", 10)
    EDITOR_CARET = "#ffffff"

    # -- Syntax-highlighting -----------------------------------
    SYN_SELECTOR = "#d7ba7d"
    SYN_PROPERTY = "#9cdcfe"
    SYN_VALUE    = "#ce9178"
    SYN_COMMENT  = "#6a9955"
    SYN_BRACE    = "#ffd700"
    SYN_UNIT     = "#b5cea8"

    # -- UI-farger ---------------------------------------------
    COLOR_TOOLBAR = "#161b22"
    COLOR_BG      = "#0d1117"
    COLOR_BG_MID  = "#161b22"
    COLOR_FG      = "#c9d1d9"
    COLOR_MUTED   = "#6e7681"
    COLOR_SEP     = "#30363d"

    # -- Fargkonstanter (B1: inga hardkodade hex i widgets) ----
    COLOR_BTN_PRIMARY    = "#1f6feb"
    COLOR_BTN_SUCCESS    = "#238636"
    COLOR_BTN_NEUTRAL    = "#374151"
    COLOR_BTN_MINIFY     = "#b45309"
    COLOR_BTN_PREVIEW    = "#6e40c9"
    COLOR_BTN_RESET      = "#b91c1c"
    COLOR_SNIPPET_TITLE  = "#d2a8ff"
    COLOR_TEMPLATE_LABEL = "#d2a8ff"
    COLOR_PREVIEW_BANNER = "#f59e0b"
    COLOR_PREVIEW_BANNER_FG = "#000000"
    COLOR_EXAMPLE_BTN    = "#1f2937"

    # ==========================================================================
    # INITIERING
    # ==========================================================================

    def init(self, app) -> None:
        """
        Initialisera plugin och skapa tabb.

        Steg:
          1. Initiera state
          2. Ladda inbyggda och sparade mallar
          3. Bygg UI
          4. Registrera i context
          5. Ladda senaste session
          6. Registrera tema-callback
        """
        self.app       = app
        self.is_active = True

        # -- State ---------------------------------------------
        self.custom_css         = ""
        self.custom_html_header = ""
        self.custom_html_footer = ""
        self._highlight_after   = None
        self._minify_enabled    = tk.BooleanVar(value=True)

        # -- Mallar --------------------------------------------
        self._load_builtin_presets()
        self._load_saved_templates()

        # -- Bygg UI -------------------------------------------
        tab_manager = app.context.get("_tab_manager")
        if tab_manager:
            editor_frame = tab_manager.add_tab(
                "css_editor", "CSS-redigerare"
            )
        else:
            editor_frame = tk.Frame(app.main_frame, bg=self.COLOR_BG)
            editor_frame.pack(fill=tk.BOTH, expand=True)

        if editor_frame:
            self._build_ui(editor_frame)
        else:
            self.log("FEL", "Kunde inte skapa CSS-editor tabb")
            return

        # -- Registrera ----------------------------------------
        app.context["_css_editor"] = self

        # -- Session -------------------------------------------
        self._load_last_session()
        self._saved_editor_content = self._get_editor_content()

        # -- Tema-callback -------------------------------------
        try:
            app.bind("<<ThemeChanged>>", self.on_theme_changed)
        except Exception:
            pass

        self.log("OK", "+ %s v%s" % (self.PLUGIN_NAME, self.VERSION))

    # ==========================================================================
    # UI - BYGG
    # ==========================================================================

    def _build_ui(self, parent: tk.Widget) -> None:
        """Bygg hela redigeringsgranssnittet."""
        self._build_toolbar(parent)

        self._inner_nb = ttk.Notebook(parent)
        self._inner_nb.pack(
            fill=tk.BOTH, expand=True, padx=8, pady=(0, 8)
        )

        self._build_css_tab()
        self._build_header_tab()
        self._build_footer_tab()
        self._build_snippets_tab()

    def _build_toolbar(self, parent: tk.Widget) -> None:
        """
        Verktygsfalt.

        tk.Frame(bg=COLOR_TOOLBAR) - INTE ttk.Frame
        -> ingen gra bakgrund.
        """
        bar = tk.Frame(parent, bg=self.COLOR_TOOLBAR, pady=6)
        bar.pack(fill=tk.X)

        # -- Mall-valjare --------------------------------------
        tk.Label(
            bar, text="Mall:",
            bg=self.COLOR_TOOLBAR, fg=self.COLOR_MUTED,
            font=("Segoe UI", 9),
        ).pack(side=tk.LEFT, padx=(10, 4))

        self.template_var = tk.StringVar(value="default")
        self._template_combo = ttk.Combobox(
            bar,
            textvariable=self.template_var,
            values=self._get_template_names(),
            state="readonly",
            width=14,
        )
        self._template_combo.pack(side=tk.LEFT, padx=(0, 4))

        # -- Knappar -------------------------------------------
        for text, cmd, bg in [
            ("Ladda",       self._load_selected_template,
             self.COLOR_BTN_PRIMARY),
            ("Spara mall",  self._save_current_template,
             self.COLOR_BTN_SUCCESS),
            ("Importera",   self._import_css, self.COLOR_BTN_NEUTRAL),
            ("Exportera",   self._export_css, self.COLOR_BTN_NEUTRAL),
        ]:
            self._make_button(
                bar, text, cmd, bg=bg, side=tk.LEFT, padx=(0, 3)
            )

        # Separator
        tk.Frame(bar, bg=self.COLOR_SEP, width=1).pack(
            side=tk.LEFT, fill=tk.Y, padx=8, pady=4
        )

        for text, cmd, bg in [
            ("Minifiera",       self._minify_css,   self.COLOR_BTN_MINIFY),
            ("Forhandsgranska", self._preview,      self.COLOR_BTN_PREVIEW),
            ("Applicera",       self._apply_css,    self.COLOR_BTN_SUCCESS),
            ("Aterstall",       self._reset_css,    self.COLOR_BTN_RESET),
        ]:
            self._make_button(
                bar, text, cmd, bg=bg, side=tk.LEFT, padx=(0, 3)
            )

        # Separator
        tk.Frame(bar, bg=self.COLOR_SEP, width=1).pack(
            side=tk.LEFT, fill=tk.Y, padx=8, pady=4
        )

        # Auto-minifiera checkbox
        tk.Checkbutton(
            bar,
            text="Auto-minifiera",
            variable=self._minify_enabled,
            bg=self.COLOR_TOOLBAR, fg=self.COLOR_FG,
            selectcolor=self.COLOR_TOOLBAR,
            activebackground=self.COLOR_TOOLBAR,
            activeforeground=self.COLOR_FG,
            font=("Segoe UI", 8),
            cursor="hand2",
        ).pack(side=tk.LEFT, padx=(4, 0))

        # Statusindikatorer (hoger)
        self._css_size_label = tk.Label(
            bar, text="",
            bg=self.COLOR_TOOLBAR, fg=self.COLOR_SNIPPET_TITLE,
            font=("Segoe UI", 8),
        )
        self._css_size_label.pack(side=tk.RIGHT, padx=6)

        self._status_label = tk.Label(
            bar, text="",
            bg=self.COLOR_TOOLBAR, fg="#3fb950",
            font=("Segoe UI", 9),
        )
        self._status_label.pack(side=tk.RIGHT, padx=10)

        self._char_count = tk.Label(
            bar, text="0 tecken",
            bg=self.COLOR_TOOLBAR, fg=self.COLOR_MUTED,
            font=("Segoe UI", 8),
        )
        self._char_count.pack(side=tk.RIGHT, padx=4)

    # -- CSS-flik ----------------------------------------------

    def _build_css_tab(self) -> None:
        """Bygg CSS-redigeringsflik."""
        frame = tk.Frame(self._inner_nb, bg=self.COLOR_BG)
        self._inner_nb.add(frame, text="  CSS  ")

        lf = tk.LabelFrame(
            frame, text=" Anpassad CSS ",
            bg=self.COLOR_BG, fg=self.COLOR_FG,
            font=("Segoe UI", 9),
            padx=4, pady=4,
        )
        lf.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)

        tk.Label(
            lf,
            text="CSS laggs in direkt i gallerisidans <style>-block.",
            bg=self.COLOR_BG, fg=self.COLOR_MUTED,
            font=("Segoe UI", 8),
        ).pack(anchor=tk.W, pady=(0, 2))

        # Text-widget + scrollbars
        container = tk.Frame(lf, bg=self.EDITOR_BG)
        container.pack(fill=tk.BOTH, expand=True)

        vbar = ttk.Scrollbar(container, orient=tk.VERTICAL)
        vbar.pack(side=tk.RIGHT, fill=tk.Y)
        hbar = ttk.Scrollbar(container, orient=tk.HORIZONTAL)
        hbar.pack(side=tk.BOTTOM, fill=tk.X)

        self.css_text = tk.Text(
            container,
            bg=self.EDITOR_BG,
            fg=self.EDITOR_FG,
            insertbackground=self.EDITOR_CARET,
            selectbackground=self.EDITOR_SEL,
            font=self.EDITOR_FONT,
            wrap=tk.NONE,
            undo=True,
            yscrollcommand=vbar.set,
            xscrollcommand=hbar.set,
            relief=tk.FLAT,
            padx=8, pady=6,
        )
        self.css_text.pack(fill=tk.BOTH, expand=True)
        vbar.config(command=self.css_text.yview)
        hbar.config(command=self.css_text.xview)

        self._setup_css_tags()
        self.css_text.bind("<KeyRelease>", self._on_key_release)
        self.css_text.bind("<ButtonRelease>", self._update_char_count)
        self.css_text.bind("<Tab>", self._on_tab_key)
        self.css_text.bind(
            "<Control-z>", lambda e: self.css_text.edit_undo()
        )
        self.css_text.bind(
            "<Control-y>", lambda e: self.css_text.edit_redo()
        )
        self._bind_mousewheel(self.css_text)

    def _setup_css_tags(self) -> None:
        """Konfigurera syntax-highlighting-taggar."""
        self.css_text.tag_configure(
            "selector", foreground=self.SYN_SELECTOR,
            font=(self.EDITOR_FONT[0], self.EDITOR_FONT[1], "bold"),
        )
        self.css_text.tag_configure(
            "property", foreground=self.SYN_PROPERTY
        )
        self.css_text.tag_configure(
            "value", foreground=self.SYN_VALUE
        )
        self.css_text.tag_configure(
            "comment", foreground=self.SYN_COMMENT,
            font=(self.EDITOR_FONT[0], self.EDITOR_FONT[1], "italic"),
        )
        self.css_text.tag_configure(
            "brace", foreground=self.SYN_BRACE
        )
        self.css_text.tag_configure(
            "unit", foreground=self.SYN_UNIT
        )

    # -- HTML Header-flik --------------------------------------

    def _build_header_tab(self) -> None:
        """Bygg HTML header-flik."""
        frame = tk.Frame(self._inner_nb, bg=self.COLOR_BG)
        self._inner_nb.add(frame, text="  HTML Head  ")

        lf = tk.LabelFrame(
            frame, text=" Extra HTML i <head> ",
            bg=self.COLOR_BG, fg=self.COLOR_FG,
            font=("Segoe UI", 9),
            padx=4, pady=4,
        )
        lf.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)

        tk.Label(
            lf,
            text=(
                "Lagg till meta-taggar, Google Fonts, "
                "externa stilmallar, etc."
            ),
            bg=self.COLOR_BG, fg=self.COLOR_MUTED,
            font=("Segoe UI", 8),
        ).pack(anchor=tk.W, pady=(0, 2))

        self.html_header_text = self._make_editor(lf)
        self._bind_mousewheel(self.html_header_text)

        # Snabbexempel
        ex_row = tk.Frame(lf, bg=self.COLOR_BG_MID)
        ex_row.pack(fill=tk.X, pady=(4, 0))
        tk.Label(
            ex_row, text="Snabbinfoga:",
            bg=self.COLOR_BG_MID, fg=self.COLOR_MUTED,
            font=("Segoe UI", 8),
        ).pack(side=tk.LEFT, padx=(0, 6))

        examples = [
            ("Google Fonts",
             '<link href="https://fonts.googleapis.com/css2?'
             'family=Inter&display=swap" rel="stylesheet">'),
            ("Viewport",
             '<meta name="viewport" '
             'content="width=device-width, initial-scale=1">'),
            ("OG-taggar",
             '<meta property="og:title" content="Mitt galleri">\n'
             '<meta property="og:type" content="website">'),
        ]
        for label, html in examples:
            self._make_button(
                ex_row, label,
                lambda h=html: self._insert_at_cursor(
                    self.html_header_text, h
                ),
                bg=self.COLOR_EXAMPLE_BTN, side=tk.LEFT,
            )

    # -- HTML Footer-flik --------------------------------------

    def _build_footer_tab(self) -> None:
        """Bygg HTML footer-flik."""
        frame = tk.Frame(self._inner_nb, bg=self.COLOR_BG)
        self._inner_nb.add(frame, text="  HTML Footer  ")

        lf = tk.LabelFrame(
            frame, text=" Extra HTML fore </body> ",
            bg=self.COLOR_BG, fg=self.COLOR_FG,
            font=("Segoe UI", 9),
            padx=4, pady=4,
        )
        lf.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)

        tk.Label(
            lf,
            text=(
                "Lagg till JavaScript, analytics, "
                "extra innehall, etc."
            ),
            bg=self.COLOR_BG, fg=self.COLOR_MUTED,
            font=("Segoe UI", 8),
        ).pack(anchor=tk.W, pady=(0, 2))

        self.html_footer_text = self._make_editor(lf)
        self._bind_mousewheel(self.html_footer_text)

        # Snabbexempel
        ex_row = tk.Frame(lf, bg=self.COLOR_BG_MID)
        ex_row.pack(fill=tk.X, pady=(4, 0))
        tk.Label(
            ex_row, text="Snabbinfoga:",
            bg=self.COLOR_BG_MID, fg=self.COLOR_MUTED,
            font=("Segoe UI", 8),
        ).pack(side=tk.LEFT, padx=(0, 6))

        examples = [
            ("GA4",
             "<!-- Google Analytics -->\n"
             '<script async src="https://www.googletagmanager.com/'
             'gtag/js?id=G-XXXXXXXX"></script>'),
            ("Lightbox JS",
             '<script src="https://cdnjs.cloudflare.com/ajax/libs/'
             'lightbox2/2.11.4/js/lightbox.min.js"></script>'),
        ]
        for label, html in examples:
            self._make_button(
                ex_row, label,
                lambda h=html: self._insert_at_cursor(
                    self.html_footer_text, h
                ),
                bg=self.COLOR_EXAMPLE_BTN, side=tk.LEFT,
            )

    # -- Snippets-flik -----------------------------------------

    def _build_snippets_tab(self) -> None:
        """Bygg snippets-flik med kategoriserade CSS-bitar."""
        frame = tk.Frame(self._inner_nb, bg=self.COLOR_BG)
        self._inner_nb.add(frame, text="  Snippets  ")

        canvas = tk.Canvas(
            frame, bg=self.COLOR_BG, highlightthickness=0
        )
        vbar = ttk.Scrollbar(
            frame, orient=tk.VERTICAL, command=canvas.yview
        )
        canvas.configure(yscrollcommand=vbar.set)

        vbar.pack(side=tk.RIGHT, fill=tk.Y)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        inner = tk.Frame(canvas, bg=self.COLOR_BG)
        canvas_win = canvas.create_window(
            (0, 0), window=inner, anchor=tk.NW
        )

        def _on_configure(event):
            canvas.configure(scrollregion=canvas.bbox("all"))
            canvas.itemconfig(canvas_win, width=canvas.winfo_width())

        inner.bind("<Configure>", _on_configure)
        canvas.bind("<Configure>", _on_configure)
        self._bind_mousewheel(canvas)

        # -- Snippet-kategorier --------------------------------
        categories = [
            ("Bild-effekter", [
                ("Runda horn",
                 ".item img { border-radius: 15px; }"),
                ("Djup skugga",
                 ".item { box-shadow: 0 10px 30px rgba(0,0,0,0.4); }"),
                ("Svartvit",
                 ".item img { filter: grayscale(100%); }\n"
                 ".item:hover img { filter: grayscale(0%); "
                 "transition: filter 0.5s; }"),
                ("Sepia",
                 ".item img { filter: sepia(80%); }"),
                ("Kontrast-boost",
                 ".item img { filter: contrast(1.2) saturate(1.1); }"),
                ("Blur pa hover",
                 ".item:hover img { filter: blur(3px); "
                 "transition: filter 0.3s; }"),
            ]),
            ("Animationer", [
                ("Lyft pa hover",
                 ".item { transition: transform 0.3s ease; }\n"
                 ".item:hover { transform: translateY(-8px); }"),
                ("Zoom pa hover",
                 ".item { overflow: hidden; }\n"
                 ".item img { transition: transform 0.4s ease; }\n"
                 ".item:hover img { transform: scale(1.1); }"),
                ("Rotera pa hover",
                 ".item { transition: transform 0.3s; }\n"
                 ".item:hover { transform: rotate(2deg) scale(1.03); }"),
                ("Fade-in",
                 ".item { opacity: 0; animation: fadeIn 0.5s ease "
                 "forwards; }\n"
                 "@keyframes fadeIn { to { opacity: 1; } }"),
            ]),
            ("Bakgrunder", [
                ("Gradient (lila-bla)",
                 "body { background: linear-gradient(135deg, "
                 "#667eea, #764ba2) !important; }"),
                ("Gradient (kvall)",
                 "body { background: linear-gradient(to bottom, "
                 "#0f0c29, #302b63, #24243e) !important; }"),
                ("Mork solid",
                 "body { background: #0d1117 !important; }"),
                ("Vit solid",
                 "body { background: #ffffff !important; "
                 "color: #24292f !important; }"),
                ("Animerad gradient",
                 "body {\n"
                 "  background: linear-gradient(-45deg, "
                 "#ee7752, #e73c7e, #23a6d5, #23d5ab);\n"
                 "  background-size: 400% 400%;\n"
                 "  animation: gradientBG 12s ease infinite;\n"
                 "}\n"
                 "@keyframes gradientBG {\n"
                 "  0%, 100% { background-position: 0% 50%; }\n"
                 "  50% { background-position: 100% 50%; }\n"
                 "}"),
            ]),
            ("Layout", [
                ("3 kolumner fast",
                 ".gallery { grid-template-columns: repeat(3, 1fr) "
                 "!important; }"),
                ("5 kolumner fast",
                 ".gallery { grid-template-columns: repeat(5, 1fr) "
                 "!important; }"),
                ("Masonry (approx)",
                 ".gallery { columns: 4; gap: 16px; }\n"
                 ".item { break-inside: avoid; }"),
                ("Stor gap",
                 ".gallery { gap: 32px !important; }"),
                ("Ingen gap",
                 ".gallery { gap: 0 !important; }"),
            ]),
            ("Item-stilar", [
                ("Glassmorfism",
                 ".item {\n"
                 "  background: rgba(255,255,255,0.05) !important;\n"
                 "  backdrop-filter: blur(10px);\n"
                 "  border: 1px solid rgba(255,255,255,0.1);\n"
                 "  border-radius: 16px !important;\n"
                 "}"),
                ("Neon glow",
                 ".item {\n"
                 "  border: 1px solid #58a6ff;\n"
                 "  box-shadow: 0 0 20px rgba(88,166,255,0.4);\n"
                 "  border-radius: 8px;\n"
                 "}"),
                ("Polaroid",
                 ".item {\n"
                 "  background: #fff !important;\n"
                 "  padding: 8px 8px 40px !important;\n"
                 "  box-shadow: 3px 3px 10px rgba(0,0,0,0.3);\n"
                 "  transform: rotate(-1deg);\n"
                 "}\n"
                 ".item:nth-child(even) { transform: rotate(1deg); }"),
                ("Ingen border-radius",
                 ".item { border-radius: 0 !important; }"),
            ]),
        ]

        for cat_title, snippets in categories:
            tk.Label(
                inner, text=cat_title,
                bg=self.COLOR_BG, fg=self.COLOR_SNIPPET_TITLE,
                font=("Segoe UI", 10, "bold"), anchor=tk.W,
            ).pack(fill=tk.X, padx=12, pady=(16, 4))

            for name, css in snippets:
                row = tk.Frame(inner, bg=self.COLOR_BG_MID)
                row.pack(fill=tk.X, padx=8, pady=2)

                preview = css.split("\n")[0][:55]
                if len(css) > 55 or "\n" in css:
                    preview += "..."

                tk.Label(
                    row, text=name,
                    bg=self.COLOR_BG_MID, fg=self.COLOR_FG,
                    font=("Segoe UI", 9),
                    width=22, anchor=tk.W,
                ).pack(side=tk.LEFT, padx=(8, 4), pady=4)

                tk.Label(
                    row, text=preview,
                    bg=self.COLOR_BG_MID, fg=self.COLOR_MUTED,
                    font=("Consolas", 8), anchor=tk.W,
                ).pack(
                    side=tk.LEFT, padx=4, fill=tk.X, expand=True
                )

                self._make_button(
                    row, "Infoga",
                    lambda c=css: self._insert_snippet(c),
                    bg=self.COLOR_BTN_PRIMARY, side=tk.RIGHT, padx=(4, 8),
                )

    # ==========================================================================
    # EDITOR-HJALPARE
    # ==========================================================================

    def _make_editor(self, parent: tk.Widget) -> tk.Text:
        """Skapa textredigerare med morkt tema."""
        container = tk.Frame(parent, bg=self.EDITOR_BG)
        container.pack(fill=tk.BOTH, expand=True)

        vbar = ttk.Scrollbar(container, orient=tk.VERTICAL)
        vbar.pack(side=tk.RIGHT, fill=tk.Y)

        text = tk.Text(
            container,
            bg=self.EDITOR_BG,
            fg=self.EDITOR_FG,
            insertbackground=self.EDITOR_CARET,
            selectbackground=self.EDITOR_SEL,
            font=self.EDITOR_FONT,
            wrap=tk.WORD,
            undo=True,
            yscrollcommand=vbar.set,
            relief=tk.FLAT,
            padx=8, pady=6,
        )
        text.pack(fill=tk.BOTH, expand=True)
        vbar.config(command=text.yview)

        text.bind("<Control-z>", lambda e: text.edit_undo())
        text.bind("<Control-y>", lambda e: text.edit_redo())

        return text

    def _on_tab_key(self, event) -> str:
        """Ersatt Tab med 2 mellanslag."""
        self.css_text.insert(tk.INSERT, "  ")
        return "break"

    def _insert_at_cursor(self, widget: tk.Text, text: str) -> None:
        """Infoga text vid markorpositionen."""
        widget.insert(tk.INSERT, "\n%s\n" % text)
        widget.see(tk.INSERT)

    def _insert_snippet(self, css: str) -> None:
        """Infoga CSS-snippet i huvudredigeraren."""
        self.css_text.insert(tk.INSERT, "\n%s\n" % css)
        self.css_text.see(tk.INSERT)
        self._inner_nb.select(0)
        self._schedule_highlight()
        self.log("INFO", "Snippet infogat")

    # ==========================================================================
    # SYNTAX-HIGHLIGHTING
    # ==========================================================================

    def _on_key_release(self, event=None) -> None:
        """Debounce-trigger for syntax-highlighting."""
        self._update_char_count()
        self._schedule_highlight()

    def _schedule_highlight(self) -> None:
        """Schemalagg syntax-highlighting med 300ms debounce."""
        if self._highlight_after:
            try:
                self.app.after_cancel(self._highlight_after)
            except Exception:
                pass
        self._highlight_after = self.safe_after(
            300, self._highlight_css
        )

    def _highlight_css(self) -> None:
        """
        Enkel CSS-syntax-highlighting.

        Stoder: kommentarer, selektorer, egenskaper,
        varden, klamrar, enheter.
        """
        if not self.widget_exists(self.css_text):
            return

        text   = self.css_text
        source = text.get("1.0", tk.END)

        for tag in (
            "selector", "property", "value",
            "comment", "brace", "unit"
        ):
            text.tag_remove(tag, "1.0", tk.END)

        def _tag(tag: str, start: int, end: int):
            try:
                text.tag_add(
                    tag, "1.0+%dc" % start, "1.0+%dc" % end
                )
            except Exception:
                pass

        # Kommentarer
        for m in re.finditer(r"/\*.*?\*/", source, re.DOTALL):
            _tag("comment", m.start(), m.end())

        # Klamrar
        for m in re.finditer(r"[{}]", source):
            _tag("brace", m.start(), m.end())

        # Selektorer
        for m in re.finditer(r"([^{};\n]+)\s*\{", source):
            _tag("selector", m.start(1), m.end(1))

        # Egenskaper
        for m in re.finditer(r"\{([^}]*)\}", source, re.DOTALL):
            block = m.group(1)
            off   = m.start(1)
            for prop in re.finditer(r"([\w-]+)\s*:", block):
                _tag("property", off + prop.start(1), off + prop.end(1))

        # Varden
        for m in re.finditer(r":\s*([^;}\n]+)", source):
            _tag("value", m.start(1), m.end(1))

        # Enheter
        for m in re.finditer(
            r"\d+\.?\d*(px|em|rem|%|vh|vw|fr|ch|ex|pt|cm|mm|in)",
            source
        ):
            _tag("unit", m.start(), m.end())

    def _update_char_count(self, event=None) -> None:
        """Uppdatera tecken-raknaren och visa minifieringsestimat."""
        if not (
            self.widget_exists(self._char_count)
            and self.widget_exists(self.css_text)
        ):
            return
        try:
            css     = self.css_text.get("1.0", tk.END).strip()
            raw_len = len(css)

            minified = self._minify_css_string(css)
            min_len  = len(minified)
            saved    = raw_len - min_len
            pct      = (saved / raw_len * 100) if raw_len > 0 else 0

            self._char_count.config(text="%d tecken" % raw_len)
            if saved > 0:
                self._css_size_label.config(
                    text="-> %d minifierad (-%.0f%%)"
                    % (min_len, pct)
                )
            else:
                self._css_size_label.config(text="")
        except tk.TclError:
            pass

    # ==========================================================================
    # CSS-MINIFIERING
    # ==========================================================================

    def _minify_css(self) -> None:
        """
        Minifiera CSS i editorn (manuell knapp).

        Uppdaterar editorn med minifierad version.
        Visar sparad storlek i statusraden.
        """
        css = self.css_text.get("1.0", tk.END).strip()
        if not css:
            self._set_status("Ingen CSS att minifiera", self.COLOR_MUTED)
            return

        orig_len = len(css)
        minified = self._minify_css_string(css)
        new_len  = len(minified)
        saved    = orig_len - new_len
        pct      = (saved / orig_len * 100) if orig_len > 0 else 0

        self.css_text.delete("1.0", tk.END)
        self.css_text.insert("1.0", minified)
        self._schedule_highlight()
        self._update_char_count()

        self._set_status(
            "Minifierad: %d -> %d (-%.0f%%)"
            % (orig_len, new_len, pct),
            "#3fb950"
        )
        self.log(
            "INFO",
            "CSS minifierad: %d -> %d tecken (%.0f%% mindre)"
            % (orig_len, new_len, pct)
        )

    def _minify_css_string(self, css: str) -> str:
        """
        Minifiera en CSS-strang.

        Tar bort:
          - Kommentarer (/* ... */)
          - Onodiga mellanslag och radbrytningar
          - Overflodiga semikolon (;; -> ;)
          - Sista semikolon fore } (;}  -> })
          - Onodiga enheter pa noll (0px -> 0)
          - Onodiga nollor (0.5 -> .5)
          - Tomma regelblock

        Returnerar minifierad CSS. Oforandrad om tom.
        """
        if not css or not css.strip():
            return css

        # 1. Ta bort kommentarer
        css = re.sub(r"/\*.*?\*/", "", css, flags=re.DOTALL)

        # 2. Sla ihop rader
        lines = [l.strip() for l in css.split("\n") if l.strip()]
        css   = " ".join(lines)

        # 3. Ta bort mellanslag runt specialtecken
        for char in ("{", "}", ":", ";", ",", ">", "+", "~"):
            css = css.replace(" %s " % char, char)
            css = css.replace(" %s" % char,  char)
            css = css.replace("%s " % char,  char)

        # 4. Flera semikolon -> ett
        css = re.sub(r";+", ";", css)

        # 5. Sista ; fore }
        css = css.replace(";}", "}")

        # 6. 0px -> 0 etc.
        css = re.sub(
            r"\b0(px|em|rem|%|vh|vw|pt|cm|mm|in|ch|ex)\b", "0", css
        )

        # 7. 0.5 -> .5
        css = re.sub(r"\b0\.(\d)", r".\1", css)

        # 8. Tomma regelblock
        css = re.sub(r"[^{}]+\{\s*\}", "", css)

        # 9. Flera mellanslag -> ett
        css = re.sub(r"\s+", " ", css)

        # 10. Mellanslag runt parenteser
        css = re.sub(r"\(\s+", "(", css)
        css = re.sub(r"\s+\)", ")", css)

        # 11. !important
        css = re.sub(r"\s*!\s*important", "!important", css)

        return css.strip()

    # ==========================================================================
    # MALLAR
    # ==========================================================================

    def _load_builtin_presets(self) -> None:
        """Ladda inbyggda CSS-mallar."""
        self.presets = {
            "default": {
                "css": (
                    "/* Standard - subtil hover-effekt */\n"
                    ".item {\n"
                    "    transition: transform 0.3s ease,"
                    " box-shadow 0.3s ease;\n"
                    "}\n\n"
                    ".item:hover {\n"
                    "    transform: translateY(-5px);\n"
                    "    box-shadow: 0 12px 24px rgba(0,0,0,0.3);\n"
                    "}"
                ),
                "header": "",
                "footer": "",
            },
            "dark": {
                "css": (
                    "/* Morkt tema */\n"
                    "body { background: #0d1117 !important; }\n\n"
                    "header {\n"
                    "    background: linear-gradient(135deg,"
                    " #1a1a2e, #16213e) !important;\n"
                    "}\n\n"
                    ".item {\n"
                    "    background: #161b22 !important;\n"
                    "    border: 1px solid #30363d;\n"
                    "    transition: border-color 0.3s, box-shadow 0.3s;\n"
                    "}\n\n"
                    ".item:hover {\n"
                    "    border-color: #58a6ff;\n"
                    "    box-shadow: 0 0 20px rgba(88,166,255,0.3);\n"
                    "}"
                ),
                "header": "",
                "footer": "",
            },
            "light": {
                "css": (
                    "/* Ljust tema */\n"
                    "body { background: #f6f8fa !important;"
                    " color: #24292f !important; }\n\n"
                    "header {\n"
                    "    background: linear-gradient(135deg,"
                    " #fff, #e1e4e8) !important;\n"
                    "    color: #24292f !important;\n"
                    "}\n\n"
                    ".item {\n"
                    "    background: #ffffff !important;\n"
                    "    border: 1px solid #d0d7de;\n"
                    "    box-shadow: 0 1px 3px rgba(0,0,0,0.1);\n"
                    "}\n\n"
                    ".item p { color: #24292f !important; }"
                ),
                "header": "",
                "footer": "",
            },
            "minimal": {
                "css": (
                    "/* Minimalistiskt */\n"
                    "* { font-family: 'Helvetica Neue', Arial, sans-serif; }\n\n"
                    "body { background: #fff !important;"
                    " color: #000 !important; }\n\n"
                    "header {\n"
                    "    background: #000 !important;\n"
                    "    color: #fff !important;\n"
                    "    border-bottom: 2px solid #000;\n"
                    "}\n\n"
                    ".item {\n"
                    "    background: #fff !important;\n"
                    "    border: 1px solid #000;\n"
                    "    border-radius: 0 !important;\n"
                    "    transition: background 0.2s;\n"
                    "}\n\n"
                    ".item:hover { background: #000 !important; }\n"
                    ".item:hover p { color: #fff !important; }"
                ),
                "header": "",
                "footer": "",
            },
            "colorful": {
                "css": (
                    "/* Fargglatt */\n"
                    "body {\n"
                    "    background: linear-gradient(-45deg,\n"
                    "        #ee7752, #e73c7e, #23a6d5, #23d5ab);\n"
                    "    background-size: 400% 400%;\n"
                    "    animation: bgAnim 12s ease infinite;\n"
                    "}\n\n"
                    "@keyframes bgAnim {\n"
                    "    0%, 100% { background-position: 0% 50%; }\n"
                    "    50%      { background-position: 100% 50%; }\n"
                    "}\n\n"
                    "header {\n"
                    "    background: rgba(255,255,255,0.9) !important;\n"
                    "    backdrop-filter: blur(10px);\n"
                    "    color: #2d3436 !important;\n"
                    "}\n\n"
                    ".item {\n"
                    "    background: rgba(255,255,255,0.85) !important;\n"
                    "    border-radius: 20px !important;\n"
                    "    box-shadow: 0 8px 32px rgba(0,0,0,0.15);\n"
                    "    transition: transform 0.3s;\n"
                    "}\n\n"
                    ".item:hover {"
                    " transform: translateY(-10px) rotate(1deg); }"
                ),
                "header": "",
                "footer": "",
            },
        }

    def _load_saved_templates(self) -> None:
        """Ladda anvandarens sparade mallar fran JSON."""
        try:
            saved = self.load_config("css_templates.json", default={})
            self.presets.update(saved)
        except Exception as e:
            self.log("VARNING", "css_templates.json: %s" % e)

    def _save_templates_to_disk(self) -> None:
        """Spara egna mallar (ej inbyggda) till JSON atomiskt."""
        builtin = {"default", "dark", "light", "minimal", "colorful"}
        custom  = {
            k: v for k, v in self.presets.items()
            if k not in builtin
        }
        self.save_config("css_templates.json", custom)

    def _get_template_names(self) -> list:
        """Returnera sorterad lista med mallnamn."""
        builtin = ["default", "dark", "light", "minimal", "colorful"]
        custom  = sorted(k for k in self.presets if k not in builtin)
        return builtin + (["---------"] + custom if custom else [])

    def _update_template_combo(self) -> None:
        """Uppdatera combobox-listan."""
        if self.widget_exists(self._template_combo):
            self._template_combo.config(
                values=self._get_template_names()
            )

    def _get_editor_content(self) -> tuple:
        """Hamta innehall fran alla tre redigerare."""
        css    = self.css_text.get("1.0",         tk.END).strip()
        header = self.html_header_text.get("1.0", tk.END).strip()
        footer = self.html_footer_text.get("1.0", tk.END).strip()
        return css, header, footer

    def _set_editor_content(
        self, css: str, header: str, footer: str
    ) -> None:
        """Fyll alla tre redigerare."""
        for widget, content in [
            (self.css_text,         css),
            (self.html_header_text, header),
            (self.html_footer_text, footer),
        ]:
            widget.delete("1.0", tk.END)
            if content:
                widget.insert("1.0", content)
        self._schedule_highlight()
        self._update_char_count()

    # -- Mallar - handelsehanterare ----------------------------

    def _load_selected_template(self) -> None:
        name = self.template_var.get()
        if name == "---------":
            return
        preset = self.presets.get(name)
        if not preset:
            messagebox.showwarning(
                "Okand mall", "Mallen '%s' hittades inte." % name
            )
            return
        self._set_editor_content(
            preset.get("css",    ""),
            preset.get("header", ""),
            preset.get("footer", ""),
        )
        self._set_status("Mall laddad: %s" % name, "#3fb950")
        self.log("INFO", "Mall laddad: %s" % name)

    def _save_current_template(self) -> None:
        name = simpledialog.askstring(
            "Spara mall", "Namn pa mallen:", parent=self.app
        )
        if not name or not name.strip():
            return
        name = name.strip()
        css, header, footer = self._get_editor_content()
        self.presets[name] = {
            "css":    css,
            "header": header,
            "footer": footer,
        }
        self._save_templates_to_disk()
        self._save_last_session()
        self._update_template_combo()
        self.template_var.set(name)
        self._set_status("Mall sparad: %s" % name, "#3fb950")
        self.log("INFO", "Mall sparad: %s" % name)
        messagebox.showinfo(
            "Sparat", "Mallen '%s' har sparats." % name
        )

    # ==========================================================================
    # IMPORT / EXPORT
    # ==========================================================================

    def _import_css(self) -> None:
        """Importera CSS fran fil."""
        path = filedialog.askopenfilename(
            title="Valj CSS-fil",
            filetypes=[("CSS-filer", "*.css"), ("Alla filer", "*.*")],
        )
        if not path:
            return
        try:
            css = Path(path).read_text(encoding="utf-8")
            self.css_text.delete("1.0", tk.END)
            self.css_text.insert("1.0", css)
            self.template_var.set("default")
            self._schedule_highlight()
            self._update_char_count()
            self._set_status(
                "Importerad: %s" % Path(path).name, "#3fb950"
            )
            self.log("INFO", "CSS importerad: %s" % Path(path).name)
        except Exception as e:
            messagebox.showerror(
                "Importfel", "Kunde inte lasa:\n%s" % e
            )
            self.log_error("CSS-import", e)

    def _export_css(self) -> None:
        """Exportera CSS till fil."""
        path = filedialog.asksaveasfilename(
            title="Spara CSS",
            defaultextension=".css",
            filetypes=[("CSS-filer", "*.css"), ("Alla filer", "*.*")],
            initialfile=(
                "gallery_style_%s.css"
                % datetime.now().strftime("%Y%m%d")
            ),
        )
        if not path:
            return
        try:
            css = self.css_text.get("1.0", tk.END)
            Path(path).write_text(css, encoding="utf-8")
            self._set_status(
                "Exporterad: %s" % Path(path).name, "#3fb950"
            )
            self.log("INFO", "CSS exporterad: %s" % Path(path).name)
            messagebox.showinfo("Exporterad", "CSS sparad:\n%s" % path)
        except Exception as e:
            messagebox.showerror(
                "Exportfel", "Kunde inte spara:\n%s" % e
            )
            self.log_error("CSS-export", e)

    # ==========================================================================
    # FORHANDSGRANSKNING
    # ==========================================================================

    def _preview(self) -> None:
        """
        Oppna forhandsgranskning i webblasare.

        Anvander subprocess.Popen (blockerar ej UI).
        Minifierar CSS om auto-minifiering ar aktiverad.
        """
        css, header, footer = self._get_editor_content()

        if self._minify_enabled.get():
            css = self._minify_css_string(css)

        html = self._build_preview_html(css, header, footer)

        try:
            preview_path = self.PREVIEW_FILE.resolve()
            preview_path.write_text(html, encoding="utf-8")

            url = preview_path.as_uri()
            if sys.platform == "win32":
                flags = (
                    subprocess.CREATE_NO_WINDOW
                    if hasattr(subprocess, "CREATE_NO_WINDOW") else 0
                )
                subprocess.Popen(
                    ["cmd", "/c", "start", "", url],
                    shell=False, creationflags=flags,
                )
            elif sys.platform == "darwin":
                subprocess.Popen(["open", url])
            else:
                subprocess.Popen(["xdg-open", url])

            self.log(
                "INFO",
                "Forhandsgranskning: %s" % preview_path.name
            )
            self._set_status("Forhandsgranskning oppnad", "#3fb950")

        except Exception as e:
            messagebox.showerror(
                "Forhandsgranskningsfel",
                "Kunde inte skapa forhandsgranskning:\n%s" % e,
            )
            self.log_error("Forhandsgranskning", e)

    def _build_preview_html(
        self, custom_css: str, custom_header: str, custom_footer: str
    ) -> str:
        """
        Bygg en komplett HTML-forhandsgranskningssida.

        Anvander processed_images fran context om tillgangliga,
        annars fargade platshallare.
        """
        images = self.app.context.get("processed_images", [])

        items_html = []
        if images:
            for img in list(images)[:16]:
                if isinstance(img, dict):
                    src  = img.get("thumbnail") or img.get("path", "")
                    name = img.get("title") or Path(str(src)).stem
                else:
                    src  = str(img)
                    name = Path(str(img)).stem
                items_html.append(
                    '<div class="item">'
                    '<img src="%s" alt="%s" loading="lazy">'
                    '<p>%s</p>'
                    '</div>' % (src, name, name)
                )
        else:
            colors = [
                "#1e40af", "#065f46", "#7c2d12", "#4c1d95",
                "#831843", "#1e3a5f", "#064e3b", "#422006",
            ]
            for i, color in enumerate(colors):
                items_html.append(
                    '<div class="item" style="background:%s">'
                    '<div style="height:140px;background:%s;'
                    'display:flex;align-items:center;'
                    'justify-content:center;font-size:2em">&#128444;</div>'
                    '<p>Bild %d</p>'
                    '</div>' % (color, color, i + 1)
                )

        ts = datetime.now().strftime("%Y-%m-%d %H:%M")
        no_images = not images
        banner_extra = (
            " |  Platshallar-bilder" if no_images else ""
        )
        return """<!DOCTYPE html>
<html lang="sv">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>CSS-forhandsgranskning - %s</title>
%s
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:system-ui,-apple-system,sans-serif;
background:#1a1a2e;color:#fff;min-height:100vh}
header{background:linear-gradient(135deg,#667eea,#764ba2);
padding:28px;text-align:center}
header h1{font-size:2em;margin-bottom:8px}
header p{opacity:.8;font-size:.9em}
.gallery{display:grid;
grid-template-columns:repeat(auto-fill,minmax(200px,1fr));
gap:20px;padding:28px;max-width:1400px;margin:0 auto}
.item{background:#16213e;border-radius:12px;overflow:hidden;
cursor:pointer;transition:transform .3s}
.item:hover{transform:translateY(-5px)}
.item img{width:100%%;aspect-ratio:1;object-fit:cover;display:block}
.item p{padding:10px;text-align:center;font-size:.85em;
color:#8b949e;white-space:nowrap;overflow:hidden;
text-overflow:ellipsis}
.preview-banner{background:%s;color:%s;text-align:center;
padding:6px;font-size:.85em;font-weight:bold;
position:sticky;top:0;z-index:100}
%s
</style>
</head>
<body>
<div class="preview-banner">
CSS-FORHANDSGRANSKNING - %s%s
</div>
<header>
<h1>Gallery Uploader</h1>
<p>Forhandsgranskning av CSS-styling</p>
</header>
<div class="gallery">
%s
</div>
%s
</body>
</html>""" % (
            ts,
            custom_header,
            self.COLOR_PREVIEW_BANNER,
            self.COLOR_PREVIEW_BANNER_FG,
            custom_css,
            ts,
            banner_extra,
            "".join(items_html),
            custom_footer,
        )

    # ==========================================================================
    # APPLICERA / ATERSTALL
    # ==========================================================================

    def _apply_css(self) -> None:
        """
        Applicera nuvarande CSS till context.

        Minifierar automatiskt om auto-minifiering ar aktiverad.
        html_generator laser context['custom_css'] vid generering.
        """
        css, header, footer = self._get_editor_content()

        if self._minify_enabled.get() and css:
            orig_len = len(css)
            css      = self._minify_css_string(css)
            new_len  = len(css)
            saved    = orig_len - new_len
            pct      = (saved / orig_len * 100) if orig_len > 0 else 0
            if saved > 0:
                self.log(
                    "INFO",
                    "CSS auto-minifierad: %d -> %d tecken (-%.0f%%)"
                    % (orig_len, new_len, pct)
                )

        self.custom_css         = css
        self.custom_html_header = header
        self.custom_html_footer = footer

        self.app.context["custom_css"]         = css
        self.app.context["custom_html_header"] = header
        self.app.context["custom_html_footer"] = footer

        size_info = " (%d tecken)" % len(css) if css else ""
        self._set_status("CSS applicerad%s" % size_info, "#3fb950")
        self.log("OK", "Custom CSS applicerad%s" % size_info)
        messagebox.showinfo(
            "Applicerad",
            "CSS har applicerats!\n\n"
            "Generera galleriet nu for att se resultatet."
        )

    def _reset_css(self) -> None:
        """Rensa alla redigerare efter bekraftelse."""
        if not messagebox.askyesno(
            "Aterstall CSS",
            "Rensa all CSS, header och footer?\n\n"
            "Mallar paverkas inte."
        ):
            return
        self._set_editor_content("", "", "")
        self.template_var.set("default")
        self._set_status("CSS aterstalld", self.COLOR_MUTED)
        self.log("INFO", "CSS aterstalld")

    # ==========================================================================
    # SESSION
    # ==========================================================================

    def _load_last_session(self) -> None:
        """Ladda senaste CSS fran config/css_last_session.json."""
        try:
            data = self.load_config("css_last_session.json", default={})
            if data:
                self._set_editor_content(
                    data.get("css",    ""),
                    data.get("header", ""),
                    data.get("footer", ""),
                )
                self.log("DEBUG", "Senaste CSS-session aterstalld")
        except Exception:
            pass

    def has_unsaved_changes(self):
        return self._get_editor_content() != getattr(self, '_saved_editor_content', None)

    def _save_last_session(self) -> None:
        """Spara nuvarande CSS vid avslutning."""
        try:
            css, header, footer = self._get_editor_content()
            saved = self.save_config("css_last_session.json", {
                "css":    css,
                "header": header,
                "footer": footer,
            })
            if saved is not False:
                self._saved_editor_content = (css, header, footer)
        except Exception:
            pass

    # ==========================================================================
    # STATUS
    # ==========================================================================

    def _set_status(self, message: str, color: str = None) -> None:
        """Uppdatera statuslabel. Aterstalls efter 4 sekunder."""
        if color is None:
            color = self.COLOR_MUTED
        if self.widget_exists(self._status_label):
            try:
                self._status_label.config(text=message, fg=color)
                self.safe_after(
                    4000,
                    lambda: self.safe_widget_config(
                        self._status_label,
                        text="", fg=self.COLOR_MUTED
                    )
                )
            except tk.TclError:
                pass

    # ==========================================================================
    # PLUGIN-KONTRAKT
    # ==========================================================================

    def execute(self, context: dict, log=None) -> dict:
        """
        Injicera custom CSS i context for html_generator.

        Minifierar CSS om auto-minifiering ar aktiverad.
        Rensar gammal CSS fran context om redigeraren ar tom.
        """
        css, header, footer = self._get_editor_content()

        if self._minify_enabled.get() and css:
            css = self._minify_css_string(css)

        if css or header or footer:
            context["custom_css"]         = css
            context["custom_html_header"] = header
            context["custom_html_footer"] = footer
            size_info = " (%d tecken)" % len(css) if css else ""
            self.log("INFO", "Custom CSS injicerad%s" % size_info)
            if log:
                log("  [CSS] %d tecken custom CSS" % len(css))
        else:
            context.pop("custom_css",         None)
            context.pop("custom_html_header", None)
            context.pop("custom_html_footer", None)

        return context

    def cleanup(self) -> None:
        """Spara session och satt is_active=False."""
        self._save_last_session()
        self.is_active = False

    def on_theme_changed(self, event=None) -> None:
        """Editorn behaller alltid morkt tema (kodredigerare)."""
        pass

    # ==========================================================================
    # INTERNA HJALPMETODER
    # ==========================================================================

    def _bind_mousewheel(self, widget: tk.Widget) -> None:
        """Bind mushjul till widget (Windows/Mac/Linux)."""
        def _scroll(event):
            try:
                if sys.platform == "win32":
                    widget.yview_scroll(
                        -1 * (event.delta // 120) * 3, "units"
                    )
                elif sys.platform == "darwin":
                    widget.yview_scroll(-1 * event.delta, "units")
                else:
                    widget.yview_scroll(
                        -3 if event.num == 4 else 3, "units"
                    )
            except (tk.TclError, AttributeError):
                pass

        widget.bind("<MouseWheel>", _scroll)
        widget.bind("<Button-4>", _scroll)
        widget.bind("<Button-5>", _scroll)

    def _make_button(
        self, parent, text: str, command,
        bg: str   = None,
        fg: str   = None,
        side: str = tk.LEFT,
        padx      = (0, 3),
        **kwargs,
    ) -> tk.Button:
        """Intern knapp-fabrik med hover-effekt."""
        if bg is None:
            bg = self.COLOR_BTN_NEUTRAL
        if fg is None:
            fg = self.COLOR_FG
        darker = self._darken(bg)
        btn    = tk.Button(
            parent, text=text, command=command,
            bg=bg, fg=fg,
            activebackground=darker, activeforeground=fg,
            font=("Segoe UI", 8, "bold"),
            relief=tk.FLAT, cursor="hand2",
            **kwargs,
        )
        btn.pack(side=side, padx=padx, pady=2)
        btn.bind("<Enter>", lambda e: btn.config(bg=darker))
        btn.bind("<Leave>", lambda e: btn.config(bg=bg))
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
