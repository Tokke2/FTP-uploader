#!/usr/bin/env python3
# ============================================================
# Plugin: Bildsorterare med drag & drop och multi-select
# ============================================================
# FIL:       plugins/image_sorter.py
# PLATS:     plugins/ (ftp_gallery_uploader/plugins/image_sorter.py)
# Syfte:     Sortera bilder manuellt innan uppladdning
# PLUGIN_NAME: "Bildsorterare"
# PRIORITY:  11
# VERSION:   4.3.0
# AUTHOR:    Rickard Längkvist
# COPYRIGHT: Copyright (c) <år> Rickard Längkvist (dynamiskt år,
#            se COPYRIGHT-konstanten nedan)
#
# ÄNDRINGAR v4.2.1 → v4.3.0 (BUG-021 kant-auto-scroll):
#   [B21]     Auto-scroll vid drag mot canvas-kant anvander LIVE
#             pekarposition (winfo_pointery) + poll 30 ms, sa den
#             fortsatter nar musen lamnar thumb-widgeten. get_drop_index
#             anvander winfo_rootx for X (var felaktigt rooty).
#
# ÄNDRINGAR v4.2.0 → v4.2.1 (KRASCHFIX — Python 3.14 / Tcl-Tk 9.0):
#   [P14-1]   search_var.trace("w", ...) → trace_add("write", ...).
#             Tcl/Tk 9.0 (Python 3.14 på Windows) tog bort det gamla
#             "trace variable"-kommandot, så Python 3.14:s legacy
#             Variable.trace() reser TclError: bad option "variable":
#             must be add, info, or remove. Samma rotorsak som kraschen i
#             ui_controls.py (samma fix, samma callback-signatur *args).
#             Bildsorteraren byggdes aldrig klart på 3.14 utan denna fix.
#
# ÄNDRINGAR v4.1.0 → v4.2.0 (krav från spec v4.5.0):
#   [B1]      Inga f-strings – ALL %-formatering (logganrop, labels,
#             tooltip-geometri, drop-indikator, _darken-retur)
#   [B3]      AUTHOR + COPYRIGHT (dynamiskt år) + PLATS i header;
#             header-label anvander self.VERSION
#
# BEVARAT FRÅN v4.1.0:
#   Inga ttk.LabelFrame i toolbar -> ingen gra ram/gap
#   Toolbar helt i COLOR_TOOLBAR - somlost mot header
#   Inga print() - safe_write() eller tyst
#   main-frame: tk.Frame(bg=COLOR_BG) istf ttk.Frame
#   Kompaktare sorteringssektion - tydligare gruppering
#   Separator-linjer ersatter LabelFrame-rutor
#   Zoom-label inline utan ram
#   Sokning utan LabelFrame-ram
#   Autoscroll-sakring: timer avbryts och nollstalls nu
#       konsekvent for att undvika overlappande animationer.
#   Emoji borttagna ur Tkinter-knappar/menyer (Tkinter
#       renderar farg-emoji inkonsekvent pa Windows)
#
# BEVARAT FRÅN v4.0.0:
#   PRIORITY andrad 10->11 (BUG-009 fix)
#   Forenklad bildsortering - farre knappar, tydligare UI
#   Inget gratt tomt falt mellan toolbar och header
#   Header + toolbar sammanfogade med enhetlig bakgrund
#   COLOR_TOOLBAR = "#1e2a3a" - genomgaende farg
#   Snabb-feedback 1.0s (var 1.5s)
#   Kompaktare layout - farre pixlar mellan element
#
# BEVARAT FRÅN v3.1.0:
#   Auto-scroll vid drag mot canvas-kant (accelererande)
#   Preview-fonster: ta bort bild utan att stanga,
#       hopar till foregaende bild
#
# KLASSER I DENNA FIL:
#   ImageSorter(BasePlugin)   - Plugin-klass (PRIORITY=11)
#   SorterWindow              - Sorteringsfonster med drag & drop
#
# MODUL-FUNKTIONER:
#   natural_sort_key(text)    - Naturlig sorteringsnyckel
#       (importeras fran image_sorter_helpers, aterexporteras)
#
# IMPORTER:
#   tkinter as tk, ttk
#   pathlib.Path
#   datetime
#   .base_plugin: BasePlugin
#   .image_sorter_helpers: SorterWindowMixin, natural_sort_key
#
# NOTE v4.1.0 (split): De tunga SorterWindow-metoderna (thumbnail-
#   laddning, rendering, undo/redo, flytta, sortering, preview) ligger
#   i image_sorter_helpers.py (SorterWindowMixin). Bada filerna MASTE
#   ligga i plugins/ tillsammans. natural_sort_key definieras i
#   helpers och aterexporteras har.
#   OBS: image_sorter_helpers.py ska klistras in/uppdateras i samma
#   mapp innan vi gar vidare (regeln: alla filer i samma mapp).
# ============================================================

import tkinter as tk
from tkinter import ttk
from pathlib import Path
from datetime import datetime
from .base_plugin import BasePlugin
from .image_sorter_helpers import SorterWindowMixin, natural_sort_key


# ==============================================================================
# HJALPFUNKTION - NATURLIG SORTERING
# ==============================================================================
# natural_sort_key importeras fran image_sorter_helpers (definieras dar
# for att undvika cirkular import). Aterexporteras har sa att
# `from .image_sorter import natural_sort_key` fortsatter fungera.


# ==============================================================================
# PLUGIN-KLASS
# ==============================================================================

class ImageSorter(BasePlugin):
    """
    Plugin for bildsortering.

    Hoppar AUTOMATISKT over sorteringsfonstret om:
    - context['gallery_order'] == True  (galleriets ordning anvands)
    - context['sorted_images'] redan finns och ar giltiga Path-objekt

    Oppnar sorteringsfonstret om ingen ordning finns.

    PRIORITY=11 (BUG-009: gallery_view=10, image_sorter=11)
    """

    PLUGIN_NAME = "Bildsorterare"
    PRIORITY    = 11
    VERSION     = "4.3.0"
    AUTHOR      = "Rickard Längkvist"
    COPYRIGHT   = "Copyright (c) %d %s" % (datetime.now().year, "Rickard Längkvist")

    def execute(self, context, log=None):
        """
        Kor bildsorterare.

        Kontrollerar context och oppnar sorteringsfonster vid behov.

        Returnerar:
            context med 'sorted_images' och 'manual_sort' satta
        """
        # Kontrollera om galleriordning redan finns
        gallery_images = context.get("gallery_images")
        gallery_order  = context.get("gallery_order", False)
        sorted_images  = context.get("sorted_images")

        if gallery_images and gallery_order:
            if log:
                log(
                    "  [OK] Anvander galleriets ordning (%d bilder)"
                    % len(gallery_images)
                )
                log("    Hoppar over sorteringsfonster")
            return context

        if sorted_images and len(sorted_images) > 0:
            if all(isinstance(img, Path) for img in sorted_images):
                if log:
                    log(
                        "  [OK] Bilder redan sorterade (%d st)"
                        % len(sorted_images)
                    )
                    log("    Hoppar over sorteringsfonster")
                return context

        # Hamta bildkatalog
        gallery = context.get("gallery", {})
        images_path_str = gallery.get("images_path", "")

        if not images_path_str:
            if log:
                log("  [!] Ingen images_path i context - hoppar over")
            return context

        images_path = Path(images_path_str)
        if not images_path.exists():
            if log:
                log("  [!] Sokvag finns inte: %s" % images_path)
            return context

        # Hitta bildfiler
        formats = {
            ".jpg", ".jpeg", ".png", ".gif",
            ".webp", ".bmp", ".tiff", ".tif", ".heic", ".heif"
        }
        image_files = [
            f for f in images_path.glob("*")
            if f.suffix.lower() in formats
            and not f.name.startswith(".")
        ]

        if not image_files:
            if log:
                log("  [!] Inga bilder hittades - hoppar over")
            return context

        if log:
            log("  Hittade %d bilder" % len(image_files))
            log("  Oppnar sorteringsfonster...")

        # Oppna sorteringsfonster
        sorter = SorterWindow(image_files)

        if sorter.result:
            context["sorted_images"] = sorter.result
            context["manual_sort"]   = True
            if log:
                log(
                    "  [OK] %d bilder sorterade manuellt"
                    % len(sorter.result)
                )
        else:
            # Fallback: naturlig sortering
            context["sorted_images"] = sorted(
                image_files,
                key=lambda x: natural_sort_key(x.name)
            )
            if log:
                log(
                    "  [!] Sortering avbruten - "
                    "anvander naturlig filnamnsordning"
                )

        return context


# ==============================================================================
# SORTERINGSFONSTER
# ==============================================================================

class SorterWindow(SorterWindowMixin):
    """
    Sorteringsfonster med drag & drop och multi-select.

    Funktioner:
    - Visuellt rutnat med thumbnails
    - Drag & drop for att flytta bilder
    - Auto-scroll vid drag mot canvas-kant (accelererande)
    - Multi-select: klick, Ctrl+klick, Shift+klick
    - Sokning i filnamn
    - Zoom pa thumbnails (slider)
    - Snabbsortering: naturlig, A-O, O-A, datum, storlek, typ, shuffle
    - Undo/Redo (Ctrl+Z / Ctrl+Y)
    - Piltangent-navigation
    - Forhandsgranskning (dubbelklick / Enter)
    - Hogerklick-kontextmeny
    - Tooltips
    - Progress-indikator under thumbnail-laddning

    v4.2.0:
    - Inga f-strings (B1) - all %-formatering
    - Inga ttk.LabelFrame -> ingen gra ram
    - Toolbar = ren tk.Frame med COLOR_TOOLBAR
    - Somlost med header (samma farg)
    - Inga print() - tyst felhantering
    """

    # -- Fargkonstanter --------------------------------------------------------
    COLOR_BG         = "#1a1a2e"
    COLOR_BG_DARK    = "#16213e"
    COLOR_TOOLBAR    = "#1e2a3a"    # Header + toolbar - SAMMA farg -> ingen gap
    COLOR_BG_ITEM    = "#252542"
    COLOR_SELECTED   = "#4a90d9"
    COLOR_SELECTED_B = "#60a5fa"
    COLOR_ACCENT     = "#22c55e"
    COLOR_WARNING    = "#f59e0b"
    COLOR_DANGER     = "#ef4444"
    COLOR_TEXT       = "#ffffff"
    COLOR_MUTED      = "#8892b0"
    COLOR_BORDER     = "#252542"
    COLOR_SEP        = "#2e3e50"    # Separator-linje i toolbar

    VERSION = "4.3.0"

    # -- Auto-scroll-konstanter (BUG-021) --------------------------------------
    AUTOSCROLL_ZONE       = 72
    AUTOSCROLL_MIN_SPEED  = 2
    AUTOSCROLL_MAX_SPEED  = 24
    AUTOSCROLL_INTERVAL   = 30

    def __init__(self, image_files):
        """Initiera sorteringsfonster."""
        self.images          = list(image_files)
        self.filtered_images = self.images.copy()
        self.thumbs          = {}
        self.selected        = set()
        self.last_clicked    = None
        self.shift_anchor    = None
        self.result          = None
        self.item_widgets    = {}
        self.cols            = 6
        self.thumb_size      = 100
        self.history         = []
        self.history_index   = -1
        self.max_history     = 50

        self.drag_data = {
            "active":         False,
            "start_index":    None,
            "start_x":        0,
            "start_y":        0,
            "threshold":      8,
            "pending_toggle": None,
        }

        self._autoscroll_timer = None
        self._autoscroll_dir   = 0
        self._last_drag_event  = None
        self._edge_poll        = None
        self.loading           = False
        self.is_open           = True

        # -- Fonster -----------------------------------------------------------
        self.win = tk.Toplevel()
        self.win.title("Sortera bilder - Drag & Drop")
        self.win.geometry("1100x750")
        self.win.configure(bg=self.COLOR_BG)
        self.win.minsize(800, 500)
        self.win.transient()
        self.win.grab_set()
        self.win.protocol("WM_DELETE_WINDOW", self.cancel)

        self.build_ui()
        self.save_state()
        self.load_thumbs_async()

        self.win.focus_force()
        self.win.wait_window()

    def build_ui(self):
        """
        Bygg hela granssnittet.

        Ordning:
          1. _build_header()   - titel + filnamn (COLOR_TOOLBAR)
          2. _build_toolbar()  - sok, zoom, sort, markera (COLOR_TOOLBAR)
          3. main-frame        - tk.Frame(bg=COLOR_BG)  <- INTE ttk.Frame
          4. _build_gallery()  - canvas + scrollbars
          5. _build_sidebar()  - preview + move + undo
          6. _build_footer()   - avbryt + bekrafta
        """
        self._build_header()
        self._build_toolbar()

        # tk.Frame - inte ttk.Frame, annars far vi ttk-bakgrundsfarg
        main = tk.Frame(self.win, bg=self.COLOR_BG)
        main.pack(fill=tk.BOTH, expand=True, padx=8, pady=4)

        self._build_gallery(main)
        self._build_sidebar(main)
        self._build_footer()
        self._bind_shortcuts()

    def _build_header(self):
        """
        Header - COLOR_TOOLBAR, kompakt.
        Samma bakgrund som toolbar -> SOMLOS overgang, ingen gra linje.
        """
        header = tk.Frame(
            self.win,
            bg=self.COLOR_TOOLBAR,
            padx=14,
            pady=0,     # 0 nedat, toolbar tar vid direkt
        )
        header.pack(fill=tk.X)

        inner = tk.Frame(header, bg=self.COLOR_TOOLBAR)
        inner.pack(fill=tk.X, pady=(8, 0))

        tk.Label(
            inner,
            text="Bildsorterare",
            font=("Segoe UI", 13, "bold"),
            bg=self.COLOR_TOOLBAR,
            fg=self.COLOR_TEXT,
        ).pack(side=tk.LEFT)

        tk.Label(
            inner,
            text="plugins/image_sorter.py  v%s" % self.VERSION,
            font=("Segoe UI", 8),
            bg=self.COLOR_TOOLBAR,
            fg="#445566",
        ).pack(side=tk.RIGHT)

    def _build_toolbar(self):
        """
        Toolbar - COLOR_TOOLBAR, INGA ttk.LabelFrame.
        Gruppering via tk.Label-rubriker + tk.Frame-sektioner.
        Somlost mot header (samma farg).
        """
        # Ytterram - fortsattning av header
        toolbar = tk.Frame(
            self.win,
            bg=self.COLOR_TOOLBAR,
            padx=14,
            pady=6,
        )
        toolbar.pack(fill=tk.X)

        # -- Rad 1: sok + zoom + sort + markera + raknare ---------------------
        row1 = tk.Frame(toolbar, bg=self.COLOR_TOOLBAR)
        row1.pack(fill=tk.X)

        # --- Sok ---
        self._tb_label(row1, "Sok:")
        self.search_var = tk.StringVar()
        # P14-1: trace_add() istf det borttagna trace("w", ...).
        # Tcl/Tk 9.0 (Python 3.14) stoder inte langre "trace variable".
        self.search_var.trace_add("write", self.on_search_changed)
        self.search_entry = tk.Entry(
            row1,
            textvariable=self.search_var,
            width=14,
            bg="#0f1923",
            fg=self.COLOR_TEXT,
            insertbackground=self.COLOR_TEXT,
            relief="flat",
            font=("Segoe UI", 9),
        )
        self.search_entry.pack(side=tk.LEFT, ipady=3, padx=(0, 2))
        self._make_button(
            row1, "X", self.clear_search, "#374151", w=2, font_size=8
        ).pack(side=tk.LEFT, padx=(0, 8))

        # Separator
        self._tb_sep(row1)

        # --- Zoom ---
        self._tb_label(row1, "-")
        self.zoom_var = tk.IntVar(value=100)
        tk.Scale(
            row1,
            from_=60, to=160,
            variable=self.zoom_var,
            orient=tk.HORIZONTAL,
            length=80,
            bg=self.COLOR_TOOLBAR,
            fg=self.COLOR_TEXT,
            highlightthickness=0,
            troughcolor="#0f1923",
            activebackground=self.COLOR_SELECTED,
            command=self.on_zoom_changed,
            showvalue=False,
        ).pack(side=tk.LEFT)
        self._tb_label(row1, "+")
        self.zoom_label = tk.Label(
            row1, text="100px", width=5,
            bg=self.COLOR_TOOLBAR, fg=self.COLOR_MUTED,
            font=("Segoe UI", 8),
        )
        self.zoom_label.pack(side=tk.LEFT, padx=(2, 8))

        # Separator
        self._tb_sep(row1)

        # --- Sortering ---
        self._tb_label(row1, "Sortera:")
        sort_options = [
            ("1,2,10", self.sort_natural,      "#1d4ed8",
             "Naturlig sortering (1, 2, 10 - inte 1, 10, 2)"),
            ("A-O",    self.sort_az,            "#6d28d9",
             "Alfabetisk A-O"),
            ("O-A",    self.sort_za,            "#6d28d9",
             "Alfabetisk O-A"),
            ("Dat+",   self.sort_date,          "#0e7490",
             "Aldst fil forst"),
            ("Dat-",   self.sort_date_created,  "#0e7490",
             "Nyast fil forst"),
            ("Stl+",   self.sort_size,          "#065f46",
             "Minst fil forst"),
            ("Stl-",   self.sort_size_desc,     "#065f46",
             "Storst fil forst"),
            ("Typ",    self.sort_type,          "#92400e",
             "Sortera efter filtyp"),
            ("Slump",  self.shuffle,            "#6b21a8",
             "Slumpa ordning"),
        ]
        for text, cmd, color, tip in sort_options:
            btn = self._make_button(
                row1, text, cmd, color, w=4, font_size=9
            )
            btn.pack(side=tk.LEFT, padx=1)
            self._add_tooltip(btn, tip)

        # Separator
        self._tb_sep(row1)

        # --- Markera ---
        self._tb_label(row1, "Markera:")
        for text, cmd, tip in [
            ("Alla",  self.select_all,       "Ctrl+A - Markera alla"),
            ("Inga",  self.deselect_all,     "Ctrl+D - Avmarkera alla"),
            ("Inv",   self.invert_selection, "Ctrl+I - Invertera markering"),
        ]:
            btn = self._make_button(row1, text, cmd, "#374151", font_size=9)
            btn.pack(side=tk.LEFT, padx=1)
            self._add_tooltip(btn, tip)

        # --- Raknare (hoger) ---
        counter_frame = tk.Frame(row1, bg=self.COLOR_TOOLBAR)
        counter_frame.pack(side=tk.RIGHT)

        self.selected_label = tk.Label(
            counter_frame, text="0 valda",
            bg=self.COLOR_TOOLBAR, fg=self.COLOR_SELECTED,
            font=("Segoe UI", 9),
        )
        self.selected_label.pack(side=tk.RIGHT, padx=(6, 0))

        self.count_label = tk.Label(
            counter_frame, text="%d bilder" % len(self.images),
            bg=self.COLOR_TOOLBAR, fg=self.COLOR_TEXT,
            font=("Segoe UI", 9, "bold"),
        )
        self.count_label.pack(side=tk.RIGHT, padx=(0, 4))

        # -- Tunn avskiljare mot galleriet ------------------------------------
        tk.Frame(
            self.win, bg=self.COLOR_SEP, height=1
        ).pack(fill=tk.X)

    def _tb_label(self, parent, text):
        """Skapa en liten etikett i toolbar."""
        tk.Label(
            parent, text=text,
            bg=self.COLOR_TOOLBAR, fg=self.COLOR_MUTED,
            font=("Segoe UI", 9),
        ).pack(side=tk.LEFT, padx=(0, 3))

    def _tb_sep(self, parent):
        """Skapa en vertikal separator-linje i toolbar."""
        tk.Frame(
            parent, bg=self.COLOR_SEP, width=1
        ).pack(side=tk.LEFT, fill=tk.Y, padx=6, pady=2)

    def _build_gallery(self, parent):
        """Bygg galleriet med canvas och scrollbars."""
        gallery_frame = tk.Frame(parent, bg=self.COLOR_BG)
        gallery_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.canvas = tk.Canvas(
            gallery_frame, bg=self.COLOR_BG, highlightthickness=0
        )
        scroll_y = ttk.Scrollbar(
            gallery_frame, orient=tk.VERTICAL, command=self.canvas.yview
        )
        scroll_x = ttk.Scrollbar(
            gallery_frame, orient=tk.HORIZONTAL, command=self.canvas.xview
        )

        self.inner = tk.Frame(self.canvas, bg=self.COLOR_BG)
        self.inner.bind(
            "<Configure>",
            lambda e: self.canvas.configure(
                scrollregion=self.canvas.bbox("all")
            ),
        )

        self.canvas_window = self.canvas.create_window(
            (0, 0), window=self.inner, anchor="nw"
        )
        self.canvas.configure(
            yscrollcommand=scroll_y.set,
            xscrollcommand=scroll_x.set,
        )

        self.canvas.bind("<Configure>", self.on_canvas_resize)
        self.canvas.bind("<Button-1>",  self.on_canvas_click)
        self.canvas.bind("<Enter>",     self._bind_mousewheel)
        self.canvas.bind("<Leave>",     self._unbind_mousewheel)

        scroll_y.pack(side=tk.RIGHT,  fill=tk.Y)
        scroll_x.pack(side=tk.BOTTOM, fill=tk.X)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.drop_indicator = tk.Frame(
            self.inner, bg=self.COLOR_ACCENT, height=4
        )

    def _build_sidebar(self, parent):
        """Bygg sidopanel med preview och move-knappar."""
        ctrl = tk.Frame(
            parent, bg=self.COLOR_BG_DARK, padx=12, pady=12
        )
        ctrl.pack(side=tk.RIGHT, fill=tk.Y, padx=(8, 0))

        # -- Forhandsgranskning -----------------------------------------------
        tk.Label(
            ctrl, text="Forhandsgranska",
            bg=self.COLOR_BG_DARK, fg=self.COLOR_MUTED,
            font=("Segoe UI", 9),
        ).pack()

        preview_container = tk.Frame(
            ctrl, bg="#252542", width=130, height=130
        )
        preview_container.pack(pady=4)
        preview_container.pack_propagate(False)
        self.preview_label = tk.Label(preview_container, bg="#252542")
        self.preview_label.pack(expand=True)

        self.preview_name = tk.Label(
            ctrl, text="Ingen vald",
            bg=self.COLOR_BG_DARK, fg=self.COLOR_TEXT,
            font=("Segoe UI", 9, "bold"), wraplength=140,
        )
        self.preview_name.pack()

        self.preview_info = tk.Label(
            ctrl, text="",
            bg=self.COLOR_BG_DARK, fg="#888",
            font=("Segoe UI", 8),
        )
        self.preview_info.pack()

        # -- Flytta ------------------------------------------------------------
        tk.Frame(ctrl, bg=self.COLOR_SEP, height=1).pack(
            fill=tk.X, pady=8
        )
        tk.Label(
            ctrl, text="Flytta markerade:",
            bg=self.COLOR_BG_DARK, fg=self.COLOR_MUTED,
            font=("Segoe UI", 9),
        ).pack(anchor="w")

        move_frame = tk.Frame(ctrl, bg=self.COLOR_BG_DARK)
        move_frame.pack(fill=tk.X, pady=4)

        for text, cmd, color, tip in [
            ("Upp",   self.move_up,   "#0891b2", "Flytta upp (Alt+Up)"),
            ("Ner",   self.move_down, "#0891b2", "Flytta ner (Alt+Down)"),
            ("Topp",  self.to_top,    "#0e7490", "Flytta till toppen (Home)"),
            ("Botten", self.to_bottom, "#0e7490", "Flytta till botten (End)"),
        ]:
            btn = self._make_button(move_frame, text, cmd, color, w=4)
            btn.pack(side=tk.LEFT, padx=2)
            self._add_tooltip(btn, tip)

        # -- Undo/Redo ---------------------------------------------------------
        undo_frame = tk.Frame(ctrl, bg=self.COLOR_BG_DARK)
        undo_frame.pack(fill=tk.X, pady=4)

        self.undo_btn = self._make_button(
            undo_frame, "Angra", self.undo, "#374151"
        )
        self.undo_btn.pack(
            side=tk.LEFT, padx=2, expand=True, fill=tk.X
        )
        self.undo_btn.config(state="disabled")
        self._add_tooltip(self.undo_btn, "Angra (Ctrl+Z)")

        self.redo_btn = self._make_button(
            undo_frame, "Gor om", self.redo, "#374151"
        )
        self.redo_btn.pack(
            side=tk.LEFT, padx=2, expand=True, fill=tk.X
        )
        self.redo_btn.config(state="disabled")
        self._add_tooltip(self.redo_btn, "Gor om (Ctrl+Y)")

        # -- Verktyg -----------------------------------------------------------
        tk.Frame(ctrl, bg=self.COLOR_SEP, height=1).pack(
            fill=tk.X, pady=8
        )
        tk.Label(
            ctrl, text="Verktyg:",
            bg=self.COLOR_BG_DARK, fg=self.COLOR_MUTED,
            font=("Segoe UI", 9),
        ).pack(anchor="w")

        for text, cmd, tip in [
            ("Forhandsgranska",   self.preview_selected,
             "Forhandsgranska vald (Enter)"),
            ("Ta bort fran lista", self.remove_selected,
             "Ta bort markerade fran listan (Delete)"),
            ("Aterstall ordning",  self.reset_order,
             "Ga tillbaka till ursprungsordning (Ctrl+R)"),
        ]:
            btn = self._make_button(ctrl, text, cmd, "#374151", w=18)
            btn.pack(pady=2, fill=tk.X)
            self._add_tooltip(btn, tip)

        # -- Status/hjalp ------------------------------------------------------
        tk.Frame(ctrl, bg=self.COLOR_SEP, height=1).pack(
            fill=tk.X, pady=8
        )
        self.help_label = tk.Label(
            ctrl, text="",
            bg=self.COLOR_BG_DARK, fg="#888",
            font=("Segoe UI", 9), wraplength=140,
        )
        self.help_label.pack()

    def _build_footer(self):
        """Bygg footer med Avbryt/Bekrafta och loading-indikator."""
        bottom = tk.Frame(self.win, bg=self.COLOR_BG, padx=12, pady=8)
        bottom.pack(fill=tk.X)

        cancel_btn = self._make_button(
            bottom, "Avbryt", self.cancel,
            self.COLOR_DANGER, font_size=11
        )
        cancel_btn.config(padx=18, pady=7)
        cancel_btn.pack(side=tk.LEFT)

        confirm_btn = self._make_button(
            bottom, "Anvand denna ordning", self.confirm,
            self.COLOR_ACCENT, font_size=11, bold=True
        )
        confirm_btn.config(padx=18, pady=7)
        confirm_btn.pack(side=tk.RIGHT)

        # Loading-area
        loading_container = tk.Frame(bottom, bg=self.COLOR_BG)
        loading_container.pack(side=tk.RIGHT, padx=16)

        self.loading_label = tk.Label(
            loading_container, text="",
            bg=self.COLOR_BG, fg=self.COLOR_WARNING,
            font=("Segoe UI", 9),
        )
        self.loading_label.pack(side=tk.LEFT)

        self.loading_progress = ttk.Progressbar(
            loading_container, length=100, mode="determinate"
        )

    def _make_button(self, parent, text, command, color,
                     w=None, font_size=9, bold=False):
        """Skapa en knapp med hover-effekt."""
        weight = "bold" if bold else "normal"
        kwargs = dict(
            text=text,
            command=command,
            bg=color,
            fg=self.COLOR_TEXT,
            font=("Segoe UI", font_size, weight),
            cursor="hand2",
            relief="flat",
            activebackground=self._darken(color),
            activeforeground=self.COLOR_TEXT,
        )
        if w is not None:
            kwargs["width"] = w
        btn = tk.Button(parent, **kwargs)
        hover = self._darken(color)
        btn.bind("<Enter>", lambda e: btn.config(bg=hover))
        btn.bind("<Leave>", lambda e: btn.config(bg=color))
        return btn

    @staticmethod
    def _darken(hex_color, factor=0.80):
        """Morknar en hex-farg for hover-effekter."""
        try:
            h = hex_color.lstrip("#")
            r = int(int(h[0:2], 16) * factor)
            g = int(int(h[2:4], 16) * factor)
            b = int(int(h[4:6], 16) * factor)
            return "#%02x%02x%02x" % (r, g, b)
        except Exception:
            return hex_color

    def _bind_shortcuts(self):
        """Bind alla tangentbordsgenvagar."""
        shortcuts = {
            "<Control-z>":       lambda e: self.undo(),
            "<Control-Z>":       lambda e: self.undo(),
            "<Control-y>":       lambda e: self.redo(),
            "<Control-Y>":       lambda e: self.redo(),
            "<Control-Shift-z>": lambda e: self.redo(),
            "<Control-a>":       lambda e: self.select_all(),
            "<Control-A>":       lambda e: self.select_all(),
            "<Control-d>":       lambda e: self.deselect_all(),
            "<Control-i>":       lambda e: self.invert_selection(),
            "<Control-r>":       lambda e: self.reset_order(),
            "<Control-f>":       lambda e: self.focus_search(),
            "<Escape>": lambda e: (
                self.deselect_all() if self.selected else self.cancel()
            ),
            "<Delete>":    lambda e: self.remove_selected(),
            "<BackSpace>": lambda e: self.remove_selected(),
            "<Home>":      lambda e: self.to_top(),
            "<End>":       lambda e: self.to_bottom(),
            "<Alt-Up>":    lambda e: self.move_up(),
            "<Alt-Down>":  lambda e: self.move_down(),
            "<Up>":        lambda e: self.navigate(-self.cols),
            "<Down>":      lambda e: self.navigate(self.cols),
            "<Left>":      lambda e: self.navigate(-1),
            "<Right>":     lambda e: self.navigate(1),
            "<Return>":    lambda e: self.preview_selected(),
            "<space>":     lambda e: self.toggle_current_selection(),
        }
        for key, func in shortcuts.items():
            try:
                self.win.bind(key, func)
            except Exception:
                pass

    def _add_tooltip(self, widget, text):
        """Visa tooltip-bubbla vid hover (2.5s)."""
        def show(event):
            if not self.is_open:
                return
            tip = tk.Toplevel(widget)
            tip.wm_overrideredirect(True)
            tip.wm_geometry(
                "+%d+%d" % (event.x_root + 12, event.y_root + 12)
            )
            tk.Label(
                tip, text=text,
                bg="#222222", fg=self.COLOR_TEXT,
                font=("Segoe UI", 9), padx=6, pady=3,
                relief="solid", borderwidth=1,
            ).pack()
            widget._tooltip = tip
            widget.after(2500, lambda: hide(None))

        def hide(event):
            if hasattr(widget, "_tooltip") and widget._tooltip:
                try:
                    widget._tooltip.destroy()
                except Exception:
                    pass
                widget._tooltip = None

        widget.bind("<Enter>", show)
        widget.bind("<Leave>", hide)

    def _bind_mousewheel(self, event=None):
        """Bind mushjuls-scroll nar musen ar over canvaset."""
        if not self.is_open:
            return
        try:
            self.canvas.bind("<MouseWheel>",         self._on_mousewheel)
            self.canvas.bind("<Button-4>",
                             lambda e: self._scroll(-3))
            self.canvas.bind("<Button-5>",
                             lambda e: self._scroll(3))
            self.canvas.bind("<Control-MouseWheel>", self._on_ctrl_scroll)
        except Exception:
            pass

    def _unbind_mousewheel(self, event=None):
        """Unbind mushjuls-scroll nar musen lamnar canvaset."""
        try:
            self.canvas.unbind("<MouseWheel>")
            self.canvas.unbind("<Button-4>")
            self.canvas.unbind("<Button-5>")
            self.canvas.unbind("<Control-MouseWheel>")
        except Exception:
            pass

    def _on_mousewheel(self, event):
        """Hantera mushjul (Windows/Mac) - 3 enheter per klick."""
        if not self.is_open:
            return
        try:
            delta = -1 if event.delta > 0 else 1
            self.canvas.yview_scroll(delta * 3, "units")
        except Exception:
            pass

    def _scroll(self, direction):
        """Hantera mushjul (Linux) - 3 enheter."""
        if not self.is_open:
            return
        try:
            self.canvas.yview_scroll(direction, "units")
        except Exception:
            pass

    def _on_ctrl_scroll(self, event):
        """Ctrl+scroll -> zoom +-10px, range 60-160."""
        if not self.is_open:
            return
        delta   = 10 if event.delta > 0 else -10
        new_val = max(60, min(160, self.zoom_var.get() + delta))
        self.zoom_var.set(new_val)
        self.on_zoom_changed(None)

    def on_canvas_resize(self, event):
        """Hantera canvas-resize - rakna om kolumner."""
        if not self.is_open:
            return
        try:
            self.canvas.itemconfig(self.canvas_window, width=event.width)
            item_size = self.thumb_size + 26
            new_cols  = max(1, (event.width - 20) // item_size)
            if new_cols != self.cols:
                self.cols = new_cols
                self.refresh()
        except Exception:
            pass

    def on_canvas_click(self, event):
        """Klick pa tom yta - avmarkera allt."""
        widget = event.widget.winfo_containing(event.x_root, event.y_root)
        if widget == self.canvas:
            self.deselect_all()

    def on_zoom_changed(self, event):
        """Hantera zoom-slider med 250ms debounce."""
        if not self.is_open:
            return
        self.thumb_size = self.zoom_var.get()
        self.zoom_label.config(text="%dpx" % self.thumb_size)

        if hasattr(self, "_zoom_timer"):
            self.win.after_cancel(self._zoom_timer)
        self._zoom_timer = self.win.after(250, self._apply_zoom)

    def _apply_zoom(self):
        """Applicera ny zoomniva - rensa thumbnails och ladda om."""
        if not self.is_open:
            return
        self.thumbs.clear()
        self.load_thumbs_async()

    def on_search_changed(self, *args):
        """Filtrera bilder baserat pa soktexten."""
        if not self.is_open:
            return
        query = self.search_var.get().lower().strip()
        if not query:
            self.filtered_images = self.images.copy()
        else:
            self.filtered_images = [
                img for img in self.images
                if query in img.name.lower()
            ]
        self.selected.clear()
        self.refresh()

        shown = len(self.filtered_images)
        total = len(self.images)
        if query:
            self.count_label.config(
                text="%d/%d bilder" % (shown, total)
            )
        else:
            self.count_label.config(text="%d bilder" % total)

    def clear_search(self):
        """Rensa sokfaltet."""
        self.search_var.set("")

    def focus_search(self):
        """Fokusera sokfaltet (Ctrl+F)."""
        self.search_entry.focus_set()
        self.search_entry.select_range(0, tk.END)

    def on_click(self, event, index):
        """Hantera klick med full multi-select-logik."""
        if not self.is_open:
            return
        self.drag_data.update(
            start_x=event.x_root,
            start_y=event.y_root,
            start_index=index,
            active=False,
            pending_toggle=None,
        )

        ctrl  = bool(event.state & 0x4)
        shift = bool(event.state & 0x1)

        if ctrl:
            self.help_label.config(text="Ctrl: Lagg till/ta bort")
        elif shift:
            self.help_label.config(text="Shift: Markera intervall")
        else:
            self.help_label.config(text="")

        if shift and self.last_clicked is not None:
            lo = min(self.last_clicked, index)
            hi = max(self.last_clicked, index)
            if not ctrl:
                self.selected.clear()
            for i in range(lo, hi + 1):
                self.selected.add(i)
            self.refresh_visual()
        elif ctrl:
            if index in self.selected:
                self.drag_data["pending_toggle"] = index
            else:
                self.selected.add(index)
                self.last_clicked = index
                self.shift_anchor = index
                self.refresh_visual()
        else:
            if index in self.selected and len(self.selected) > 1:
                self.drag_data["pending_toggle"] = "single"
            else:
                self.selected     = {index}
                self.last_clicked = index
                self.shift_anchor = index
                self.refresh_visual()

    def on_drag(self, event, index):
        """Hantera drag - aktivera nar threshold overskridits."""
        if not self.is_open or not self.selected:
            return
        dx = abs(event.x_root - self.drag_data["start_x"])
        dy = abs(event.y_root - self.drag_data["start_y"])

        if dx > self.drag_data["threshold"] or \
                dy > self.drag_data["threshold"]:
            self.drag_data["active"]         = True
            self.drag_data["pending_toggle"] = None
            try:
                self.win.config(cursor="fleur")
            except Exception:
                pass
            self.show_drop_indicator(event)
            self._last_drag_event = event
            self._check_autoscroll(event)
            self._ensure_edge_poll()

    def _ensure_edge_poll(self) -> None:
        """Starta pekar-poll under drag (BUG-021)."""
        if getattr(self, "_edge_poll", None) is not None:
            return
        try:
            self._edge_poll = self.win.after(
                self.AUTOSCROLL_INTERVAL, self._edge_poll_tick,
            )
        except Exception:
            self._edge_poll = None

    def _edge_poll_tick(self) -> None:
        """Las live pekarposition mot canvas-kant."""
        self._edge_poll = None
        if not self.is_open or not self.drag_data.get("active"):
            return
        self._check_autoscroll(None)
        self._ensure_edge_poll()

    def _canvas_y_from_pointer(self, event=None):
        """Canvas-Y fran event eller live pekare."""
        try:
            root_y = self.canvas.winfo_rooty()
            if event is not None and hasattr(event, "y_root"):
                return event.y_root - root_y
            return self.win.winfo_pointery() - root_y
        except Exception:
            return None

    def _check_autoscroll(self, event):
        """Kontrollera om auto-scroll ska aktiveras (BUG-021)."""
        if not self.is_open or not self.drag_data["active"]:
            self._stop_autoscroll()
            return

        if self._autoscroll_timer is not None:
            try:
                self.win.after_cancel(self._autoscroll_timer)
            except Exception:
                pass
            self._autoscroll_timer = None

        try:
            canvas_y = self._canvas_y_from_pointer(event)
            if canvas_y is None:
                self._stop_autoscroll()
                return
            canvas_h = self.canvas.winfo_height()
            dist_top = canvas_y
            dist_bot = canvas_h - canvas_y

            if 0 <= dist_top < self.AUTOSCROLL_ZONE:
                proximity = 1.0 - (dist_top / float(self.AUTOSCROLL_ZONE))
                direction = -1
            elif 0 <= dist_bot < self.AUTOSCROLL_ZONE:
                proximity = 1.0 - (dist_bot / float(self.AUTOSCROLL_ZONE))
                direction = 1
            else:
                self._stop_autoscroll()
                return

            speed = int(
                self.AUTOSCROLL_MIN_SPEED
                + proximity
                * (self.AUTOSCROLL_MAX_SPEED - self.AUTOSCROLL_MIN_SPEED)
            )
            if speed < 1:
                speed = 1
            self._autoscroll_dir = direction
            self._run_autoscroll(direction, speed)
        except Exception:
            self._stop_autoscroll()

    def _run_autoscroll(self, direction, speed):
        """Utfor auto-scroll-steg."""
        if not self.is_open or not self.drag_data["active"]:
            self._stop_autoscroll()
            return

        if self._autoscroll_timer is not None:
            try:
                self.win.after_cancel(self._autoscroll_timer)
            except Exception:
                pass
            self._autoscroll_timer = None

        try:
            self.canvas.yview_scroll(direction * speed, "units")
            self._update_drop_from_pointer()
            self._autoscroll_timer = self.win.after(
                self.AUTOSCROLL_INTERVAL,
                lambda: self._continue_autoscroll(direction, speed),
            )
        except Exception:
            self._stop_autoscroll()

    def _update_drop_from_pointer(self) -> None:
        """Uppdatera drop-streck fran live pekare."""
        try:
            class _E(object):
                pass
            ev = _E()
            ev.x_root = self.win.winfo_pointerx()
            ev.y_root = self.win.winfo_pointery()
            self._last_drag_event = ev
            self.show_drop_indicator(ev)
        except Exception:
            if self._last_drag_event:
                self.show_drop_indicator(self._last_drag_event)

    def _continue_autoscroll(self, direction, speed):
        """Fortsatt auto-scroll-loopen med live pekare."""
        if not self.is_open or not self.drag_data["active"]:
            self._stop_autoscroll()
            return
        self._check_autoscroll(None)

    def _stop_autoscroll(self):
        """Stoppa pagaende auto-scroll (inte edge-poll)."""
        if self._autoscroll_timer is not None:
            try:
                self.win.after_cancel(self._autoscroll_timer)
            except Exception:
                pass
            self._autoscroll_timer = None
        self._autoscroll_dir = 0

    def _stop_edge_poll(self) -> None:
        """Stoppa pekar-poll."""
        if getattr(self, "_edge_poll", None) is not None:
            try:
                self.win.after_cancel(self._edge_poll)
            except Exception:
                pass
            self._edge_poll = None

    def show_drop_indicator(self, event):
        """Visa gron linje for drop-target."""
        if not self.is_open:
            return
        drop_idx = self.get_drop_index(event)
        if drop_idx is not None and drop_idx not in self.selected:
            item_size = self.thumb_size + 26
            row, col  = divmod(drop_idx, self.cols)
            try:
                self.drop_indicator.place(
                    x=col * (item_size + 6),
                    y=row * (item_size + 46),
                    width=item_size,
                    height=4,
                )
                n = len(self.selected)
                self.help_label.config(
                    text="Flytta %d bild%s -> #%d"
                    % (n, "er" if n > 1 else "", drop_idx + 1)
                )
            except Exception:
                pass
        else:
            self.hide_drop_indicator()

    def hide_drop_indicator(self):
        """Dolj drop-indikatorn."""
        try:
            self.drop_indicator.place_forget()
        except Exception:
            pass

    def get_drop_index(self, event):
        """Berakna drop-index fran canvas-koordinat."""
        try:
            cx = self.canvas.canvasx(
                event.x_root - self.canvas.winfo_rootx()
            )
            cy = self.canvas.canvasy(
                event.y_root - self.canvas.winfo_rooty()
            )
            item_size   = self.thumb_size + 26
            item_height = item_size + 46
            col = max(0, int(cx / (item_size + 6)))
            row = max(0, int(cy / item_height))
            idx = row * self.cols + col
            return max(0, min(idx, len(self.filtered_images)))
        except Exception:
            return None

    def on_drop(self, event, index):
        """Hantera mouse-release (drop)."""
        if not self.is_open:
            return
        self._stop_autoscroll()
        self._stop_edge_poll()
        self.hide_drop_indicator()
        self.help_label.config(text="")
        try:
            self.win.config(cursor="")
        except Exception:
            pass

        if self.drag_data["active"] and self.selected:
            drop_idx = self.get_drop_index(event)
            if drop_idx is not None and drop_idx not in self.selected:
                self.save_state()
                self.move_selected_to(drop_idx)
        elif not self.drag_data["active"]:
            pt = self.drag_data["pending_toggle"]
            if pt == index:
                self.selected.discard(index)
                self.refresh_visual()
            elif pt == "single":
                self.selected     = {index}
                self.last_clicked = index
                self.refresh_visual()

        self.drag_data["active"]         = False
        self.drag_data["pending_toggle"] = None
        self._last_drag_event            = None

    def on_right_click(self, event, index):
        """Visa hogerklick-kontextmeny."""
        if not self.is_open:
            return
        if index not in self.selected:
            self.selected     = {index}
            self.last_clicked = index
            self.refresh_visual()

        menu = tk.Menu(
            self.win, tearoff=0,
            bg="#2d2d2d", fg=self.COLOR_TEXT,
            activebackground=self.COLOR_SELECTED,
            activeforeground=self.COLOR_TEXT,
        )
        menu.add_command(
            label="Forhandsgranska",
            command=self.preview_selected
        )
        menu.add_separator()
        menu.add_command(label="Flytta upp",         command=self.move_up)
        menu.add_command(label="Flytta ner",         command=self.move_down)
        menu.add_command(label="Flytta till toppen", command=self.to_top)
        menu.add_command(label="Flytta till botten", command=self.to_bottom)
        menu.add_separator()
        menu.add_command(
            label="Ta bort fran lista",
            command=self.remove_selected
        )
        menu.tk_popup(event.x_root, event.y_root)

    def confirm(self):
        """Bekrafta ordningen och stang fonstret."""
        self.result = self.images.copy()
        self._cleanup()
        self.win.destroy()

    def cancel(self):
        """Avbryt utan att spara (result = None)."""
        self.result = None
        self._cleanup()
        self.win.destroy()

    def _cleanup(self):
        """Stada upp resurser vid stangning."""
        self.is_open = False
        self.loading = False
        self._stop_autoscroll()
        self._stop_edge_poll()
        self._unbind_mousewheel()
