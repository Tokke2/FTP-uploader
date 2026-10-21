#!/usr/bin/env python3
# ============================================================
# Plugin: Flikhanterare
# ============================================================
# FIL:       plugins/tab_manager.py
# PLATS:     plugins/ (ftp_gallery_uploader/plugins/tab_manager.py)
# Syfte:     Anpassad flikrad med navigation, badges och kortkommandon
# PLUGIN_NAME: "Flikhanterare"
# PRIORITY:  -10  (kors allra FORST)
# VERSION:   2.5.1
# AUTHOR:    Rickard Längkvist
# COPYRIGHT: Copyright (c) <år> Rickard Längkvist (dynamiskt år,
#            se COPYRIGHT-konstanten nedan)
#
# ÄNDRINGAR v2.4.0 → v2.5.0 (snabbhet/robusthet/minne, icke-brytande):
#   [R1]      Delad _remove_tab_internal() + bulk close_other_tabs():
#             manga flikar stangs med EN save_state()/logg i stallet
#             for en disk-skrivning per flik -> snabbare, mindre I/O.
#   [R2]      Bug: stangd flik rensas nu ur tab_history och
#             forward_history - tidigare kunde Back/Forward hamna pa en
#             forstord flik och ge KeyError i _show_tab().
#   [R3]      flash_tab(): timer-id sparas och avbryts i cleanup();
#             blink avslutas om fliken forstors/inaktiveras. Inga
#             foraldrade after-callbacks efter stangning.
#   [R4]      _new_tool_button(): samlar stil for nav- och hamburger-
#             knapparna pa en plats (identiskt, tema-foljande utseende).
#
# ÄNDRINGAR v2.3.0 → v2.4.0 (kvalitet/design/minne, icke-brytande):
# ÄNDRINGAR v2.3.0 → v2.4.0 (kvalitet/design/minne, icke-brytande):
#   [Q1]      Ny fabrik _make_menu(): meny-styling (bg/fg/active)
#             samlad pa en plats och delas av hogerklick-menyn +
#             hamburger-menyn -> identiskt utseende, mindre kod.
#   [Q2]      Design-matchning: menu_btn, bada separatorlinjerna och
#             stang-knapparna registreras + omstylas vid tema-byte.
#             _apply_tab_styles() synkar nu aven stang-knappens
#             bakgrund med aktiv/inaktiv flik (tidigare fastnat som
#             inaktiv -> tydlig rektangel pa aktiv flik).
#   [Q3]      Tooltip-livscykel: after-id sparas + Toplevel destroyas
#             innan en ny visas -> inga foraldrade fönster kvar (minne).
#
# ÄNDRINGAR v2.2.0 → v2.3.0 (DESIGN-SYSTEM-integration, spec v4.6.0):
#   [C1]      Fargerna hamtas nu fran ThemeEngine-designsystemet
#             (helpers v1.3.0, 58 nycklar/tema) istallet for
#             hardkodade varden:
#               COLOR_BG           <- theme "bg"
#               COLOR_TAB_ACTIVE   <- theme "tab_active_bg"
#               COLOR_TAB_INACTIVE <- theme "tab_bg"
#               COLOR_TAB_HOVER    <- theme "surface_alt"
#               COLOR_FG_ACTIVE    <- theme "tab_active_fg"
#               COLOR_FG_INACTIVE  <- theme "tab_fg"
#               COLOR_FG_HOVER     <- theme "fg"
#               COLOR_NAV_BG       <- theme "surface"
#               COLOR_BADGE        <- theme "error"
#               COLOR_SEP          <- theme "border"
#               COLOR_TOOLTIP_BG   <- theme "tooltip_bg"
#               COLOR_MENU_BG      <- theme "menu_bg"
#               COLOR_CLOSE_BTN    <- theme "muted"
#               COLOR_FLASH        <- theme "warning"
#   [C1]      _load_theme_colors(): hamtar farger fran
#             app.theme_engine.get_color() med fallback till
#             klassattributen (fungerar aven utan tema-engine)
#   [C1]      on_theme_changed(): lyssnar pa <<ThemeChanged>> och
#             uppdaterar alla flikar, nav-knappar, canvas och
#             content vid tema-byte (utan omstart)
#   [C1]      _restyle_all_tabs(): applicerar aktuella farger pa
#             alla befintliga flik-knappar/containers + nav + meny
#   [C1]      register_theme_callback() anropas i init()
#   [C4]      Alla fargvarden via COLOR_*-attribut (uppdateras
#             dynamiskt fran temat)
#
# BEVARAT FRÅN v2.2.0:
#   Inga f-strings (B1), atomisk save_state med fsync (A9),
#   config/ via helpers (A10), alla flik-API-metoder,
#   hogerklick-meny, hamburger-meny, historik, badges,
#   tangentbordsgenvagar, tooltips, flash_tab.
#
# KLASSER I DENNA FIL:
#   TabManager(BasePlugin) - PRIORITY=-10
#
# IMPORTER:
#   tkinter as tk, ttk
#   pathlib.Path
#   json, os, tempfile
#   datetime
#   .base_plugin: BasePlugin
#   helpers: get_config_path (valfritt, A10)
#
# CONTEXT SOM SATTS:
#   '_tab_manager' - self
#
# CONTEXT SOM LASES:
#   '_logger'      - loggning
#   '_{tab_name}'  - plugin-instans for refresh()
#
# JSON: config/tab_state.json
#   { "last_tab": "settings", "tab_order": [...] }
#
# FLIK-API (for andra plugins):
#   add_tab(name, title, icon, closable) -> Frame
#   select_tab(name)
#   set_badge(name, text)
#   clear_badge(name)
#   set_tab_title(name, new_title)
#   flash_tab(name, times)
#   tab_exists(name) -> bool
#   get_tab(name) -> Frame
#   get_current_tab() -> str
#   get_tab_count() -> int
#
# TANGENTBORDSGENVAGAR:
#   Ctrl+Tab          - Nasta flik
#   Ctrl+Shift+Tab    - Foregaende flik
#   Alt+Left          - Bakat i historik
#   Alt+Right         - Framat i historik
#   Ctrl+1-9          - Valj flik per index
#   Alt+1-9           - Valj flik per index (alternativ)
# ============================================================

import app_paths
import tkinter as tk
from tkinter import ttk
from pathlib import Path
import json
import os
import tempfile
from datetime import datetime

from .base_plugin import BasePlugin

# -- Helpers (valfritt – för config-sökväg, A10) ---------------
try:
    from helpers import get_config_path
    _HAS_HELPERS = True
except ImportError:
    _HAS_HELPERS = False


class TabManager(BasePlugin):
    """
    Anpassad flikhanterare med navigation, badges och kortkommandon.

    Ersatter ttk.Notebook med en helt anpassad flikrad.
    Kors med PRIORITY=-10 for att vara klar innan alla andra plugins.

    v2.5.0:
    - bulk-close (en save/log) + rensar stangda flikar ur historiken
    - avbrytbar flash_tab (timer-id, cleanup)
    - _new_tool_button() samlar nav/hamburger-stil

    v2.4.0:
    - _make_menu()-fabrik (delas av hogerklick- och hamburger-menyn)
    - menu_btn/separatorer/stang-knappar omstylas nu vid tema-byte
    - _apply_tab_styles() synkar stang-knappens bakgrund med fliktillstand
    - Tooltip-livscykel rattad (inget fonster/efter-kvar)

    v2.3.0: Fargerna foljer ThemeEngine-designsystemet (58 nycklar/
    tema) och uppdateras dynamiskt vid tema-byte via
    on_theme_changed() + _restyle_all_tabs().
    """

    PLUGIN_NAME = "Flikhanterare"
    PRIORITY    = -10
    VERSION     = "2.5.1"
    AUTHOR      = "Rickard Längkvist"
    COPYRIGHT   = "Copyright (c) %d %s" % (datetime.now().year, "Rickard Längkvist")

    # -- Standardikoner per fliknamn ---------------------------
    # Emoji borttagna for stabil rendering i Tkinter pa Windows.
    # Plugins kan fortfarande skicka egen icon-strang till add_tab().
    DEFAULT_ICONS = {
        "settings": "\u2699",
        "controls": "",
        "gallery":  "",
        "video":    "",
        "ftp":      "",
        "log":      "",
        "help":     "",
        "info":     "",
        "watch":    "",
        "sorter":   "",
        "css":      "",
    }

    # -- Farger (fallback-defaults; uppdateras fran temat) -----
    COLOR_BG           = "#070B14"
    COLOR_TAB_ACTIVE   = "#153056"
    COLOR_TAB_INACTIVE = "#121A28"
    COLOR_TAB_HOVER    = "#1A2740"
    COLOR_FG_ACTIVE    = "#ffffff"
    COLOR_FG_INACTIVE  = "#9AA6BC"
    COLOR_FG_HOVER     = "#F3F5FB"
    COLOR_NAV_BG       = "#101827"
    COLOR_BADGE        = "#ef4444"
    COLOR_SEP          = "#1E2C44"   # Separator-linje

    # -- Fargkonstanter (B1: inga hardkodade hex i widgets) ----
    COLOR_TOOLTIP_BG   = "#1e293b"
    COLOR_MENU_BG      = "#1e293b"
    COLOR_CLOSE_BTN    = "#64748b"
    COLOR_FLASH        = "#f59e0b"

    # -- Tema-nyckelmappning (C1) ------------------------------
    _THEME_KEYS = {
        "COLOR_BG":           "bg",
        "COLOR_TAB_ACTIVE":   "tab_active_bg",
        "COLOR_TAB_INACTIVE": "tab_bg",
        "COLOR_TAB_HOVER":    "surface_alt",
        "COLOR_FG_ACTIVE":    "tab_active_fg",
        "COLOR_FG_INACTIVE":  "tab_fg",
        "COLOR_FG_HOVER":     "fg",
        "COLOR_NAV_BG":       "surface",
        "COLOR_BADGE":        "error",
        "COLOR_SEP":          "accent",
        "COLOR_TOOLTIP_BG":   "tooltip_bg",
        "COLOR_MENU_BG":      "menu_bg",
        "COLOR_CLOSE_BTN":    "muted",
        "COLOR_FLASH":        "warning",
    }

    def _config_file(self) -> Path:
        """Returnera sokvag till tab_state.json (A10)."""
        if _HAS_HELPERS:
            return get_config_path() / "tab_state.json"
        return app_paths.config_dir() / "tab_state.json"

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
            self.log_action("Tema-farger kunde inte laddas: %s" % e)

    def _restyle_all_tabs(self) -> None:
        """Applicera aktuella farger pa alla flikar och ramar."""
        if not self.widget_exists(self.main_container):
            return
        try:
            # Bakgrunder
            for w in (
                self.main_container,
                self.tab_bar_container,
                self.nav_frame,
                self.tools_frame,
                self.tab_bar,
                self.content,
            ):
                if self.widget_exists(w):
                    try:
                        w.configure(bg=self.COLOR_BG)
                    except Exception:
                        pass
            if self.widget_exists(self.tab_canvas):
                self.tab_canvas.configure(bg=self.COLOR_BG)

            # Navigationsknappar
            for btn in (self.back_btn, self.forward_btn):
                if self.widget_exists(btn):
                    try:
                        btn.configure(bg=self.COLOR_NAV_BG)
                    except Exception:
                        pass

            # Meny-knapp (hamburger, Q2)
            if self.widget_exists(getattr(self, "menu_btn", None)):
                try:
                    self.menu_btn.configure(
                        bg=self.COLOR_NAV_BG,
                        fg=self.COLOR_FG_ACTIVE,
                        activebackground=self.COLOR_TAB_HOVER,
                        activeforeground=self.COLOR_FG_ACTIVE,
                    )
                except Exception:
                    pass

            # Separatorlinjer (Q2)
            for sep in (
                getattr(self, "sep_vertical", None),
                getattr(self, "sep_horizontal", None),
            ):
                if self.widget_exists(sep):
                    try:
                        sep.configure(bg=self.COLOR_SEP)
                    except Exception:
                        pass

            # Badges (Q2)
            for badge in self.tab_badges.values():
                if self.widget_exists(badge):
                    try:
                        badge.configure(
                            bg=self.COLOR_BADGE, fg=self.COLOR_FG_ACTIVE
                        )
                    except Exception:
                        pass

            # Flikknappar + containers (stilar enligt aktiv/inaktiv)
            if self.current_tab:
                self._apply_tab_styles(self.current_tab)
            else:
                self._apply_tab_styles(None)

            self._update_nav_buttons()
        except Exception:
            pass

    # ==========================================================================
    # PLUGIN-LIVSCYKEL
    # ==========================================================================

    def init(self, app):
        """
        Plugin-initiering.

        Steg:
          1. Initiera intern state
          2. Ladda sparad flikstatus
          3. Ladda tema-farger (C1)
          4. Bygg UI (flikrad + contentyta)
          5. Bind tangentbordsgenvagar
          6. Registrera i context
          7. Registrera tema-callback
        """
        self.app       = app
        self.is_active = True

        # -- Intern state --------------------------------------
        self.tabs            = {}   # name -> {button, container, title, closable}
        self.tab_frames      = {}   # name -> Frame
        self.tab_buttons     = {}   # name -> Button
        self.tab_badges      = {}   # name -> Label
        self.tab_icons       = {}   # name -> str (ikon)
        self.tab_order       = []   # visningsordning
        self.current_tab     = None
        self.tab_history     = []   # bakat (max 50)
        self.forward_history = []   # framat
        self._flash_after    = None  # v2.5.0: blink-timer (avbryts i cleanup)

        # -- Sparat state --------------------------------------
        self.saved_state = self.load_state()

        # -- Tema-farger (C1) ----------------------------------
        self._load_theme_colors()

        # -- Bygg UI -------------------------------------------
        self._build_layout(app)

        # -- Tangentbordsgenvagar ------------------------------
        self.setup_shortcuts()

        # -- Registrera ----------------------------------------
        app.context["_tab_manager"] = self

        # -- Tema-callback (C1) --------------------------------
        self.register_theme_callback()

    def execute(self, context, log=None):
        """Pipeline-passthrough - returnerar context oforandrad."""
        return context

    # ==========================================================================
    # UI-LAYOUT
    # ==========================================================================

    def _build_layout(self, app):
        """
        Bygg flikhanterarens layout.

        VIKTIGT v2.1.0:
          Alla ramar ar tk.Frame(bg=COLOR_BG), INTE ttk.Frame.
          ttk.Frame tar ttk-bakgrundsfargen (gra) fran temat,
          vilket orsakar gra remsor.

        Struktur:
          main_container  [tk.Frame, bg=COLOR_BG]
            tab_bar_container [tk.Frame, bg=COLOR_BG]
              nav_frame       [tk.Frame, bg=COLOR_BG]  (back/forward)
              separator       [tk.Frame, bg=COLOR_SEP, w=1]
              tab_canvas      [tk.Canvas, bg=COLOR_BG]
                tab_bar       [tk.Frame, bg=COLOR_BG]
              tools_frame     [tk.Frame, bg=COLOR_BG]  (menu)
            sep_line          [tk.Frame, bg=COLOR_SEP, h=1]
            content           [tk.Frame, bg=COLOR_BG]
        """
        # -- Yttre container -----------------------------------
        self.main_container = tk.Frame(app.main_frame, bg=self.COLOR_BG)
        self.main_container.pack(fill=tk.BOTH, expand=True)

        # -- Flikrad -------------------------------------------
        self.tab_bar_container = tk.Frame(
            self.main_container, bg=self.COLOR_BG
        )
        self.tab_bar_container.pack(fill=tk.X)

        # Navigation (back / forward)
        self.nav_frame = tk.Frame(
            self.tab_bar_container, bg=self.COLOR_BG
        )
        self.nav_frame.pack(side=tk.LEFT, padx=(5, 0))

        self.back_btn = self._make_nav_btn(
            self.nav_frame, "\u25c0", self.go_back,
            "Foregaende flik  (Alt+Left)"
        )
        self.back_btn.pack(side=tk.LEFT, padx=2)
        self.back_btn.config(
            state="disabled", fg=self.COLOR_FG_INACTIVE
        )

        self.forward_btn = self._make_nav_btn(
            self.nav_frame, "\u25b6", self.go_forward,
            "Nasta flik  (Alt+Right)"
        )
        self.forward_btn.pack(side=tk.LEFT, padx=2)
        self.forward_btn.config(
            state="disabled", fg=self.COLOR_FG_INACTIVE
        )

        # Vertikal separator (tk.Frame, inte ttk.Separator)
        self.sep_vertical = tk.Frame(
            self.tab_bar_container,
            bg=self.COLOR_SEP,
            width=1,
        )
        self.sep_vertical.pack(side=tk.LEFT, fill=tk.Y, padx=8, pady=4)

        # Canvas for horisontell scroll av flikar
        # DPI-saker hojd: 40 px klipper knapparna vid 125-150 % skalning
        # sa flikarna "saknas". Mata fontens linespace + padding.
        try:
            _lh = int(self.app.tk.call(
                "font", "metrics", ("Segoe UI", 10), "-linespace"
            ))
            _canvas_h = max(40, _lh + 18)
        except Exception:
            _canvas_h = 40
        self.tab_canvas = tk.Canvas(
            self.tab_bar_container,
            height=_canvas_h,
            bg=self.COLOR_BG,
            highlightthickness=0,
        )
        self.tab_canvas.pack(side=tk.LEFT, fill=tk.X, expand=True)

        self.tab_bar = tk.Frame(self.tab_canvas, bg=self.COLOR_BG)
        self.tab_canvas.create_window(
            (0, 0), window=self.tab_bar, anchor="nw"
        )

        self.tab_bar.bind("<Configure>", self._on_tab_bar_configure)
        self.tab_canvas.bind("<MouseWheel>", self._on_tab_scroll)
        self.tab_canvas.bind(
            "<Button-4>",
            lambda e: self.tab_canvas.xview_scroll(-3, "units")
        )
        self.tab_canvas.bind(
            "<Button-5>",
            lambda e: self.tab_canvas.xview_scroll(3, "units")
        )

        # Flikmeny-knapp (hamburger)
        self.tools_frame = tk.Frame(
            self.tab_bar_container, bg=self.COLOR_BG
        )
        self.tools_frame.pack(side=tk.RIGHT, padx=(0, 5))

        menu_btn = self._new_tool_button(
            self.tools_frame, "\u2630", self.show_tab_menu, 12, 10, 4
        )
        self.menu_btn = menu_btn
        menu_btn.pack(side=tk.RIGHT, padx=2)
        self._add_tooltip(menu_btn, "Alla flikar")

        # Horisontell separator under flikraden (1px linje)
        self.sep_horizontal = tk.Frame(
            self.main_container,
            bg=self.COLOR_SEP,
            height=2,
        )
        self.sep_horizontal.pack(fill=tk.X)

        # -- Contentyta ----------------------------------------
        self.content = tk.Frame(self.main_container, bg=self.COLOR_BG)
        self.content.pack(fill=tk.BOTH, expand=True)

    def _new_tool_button(self, parent, text, command, font_size, padx, pady):
        """
        Standardiserad verktygs-knapp for nav/hamburger (v2.5.0).

        Samlar stil-parametrarna (COLOR_NAV_BG, flat, hand2, hover)
        pa en plats sa nav-knappar och hamburger-knappen alltid
        matchar och foljer temat. Returnerar en (ej packad) Button.
        """
        return tk.Button(
            parent,
            text=text,
            command=command,
            relief=tk.FLAT,
            bg=self.COLOR_NAV_BG,
            fg=self.COLOR_FG_ACTIVE,
            activebackground=self.COLOR_TAB_HOVER,
            activeforeground=self.COLOR_FG_ACTIVE,
            font=("Segoe UI", font_size),
            padx=padx,
            pady=pady,
            cursor="hand2",
        )

    def _make_nav_btn(self, parent, text, command, tooltip_text):
        """
        Skapa navigationsknappar (back / forward).

        Konsekvent stil: COLOR_NAV_BG, flat, hand2-cursor.
        """
        btn = self._new_tool_button(parent, text, command, 10, 8, 4)
        self._add_tooltip(btn, tooltip_text)
        return btn

    # ==========================================================================
    # STATE: SPARA / LADDA
    # ==========================================================================

    def load_state(self) -> dict:
        """
        Ladda config/tab_state.json.
        Returnerar dict med last_tab och tab_order.
        Tyst fallback om filen saknas eller ar korrupt.
        """
        try:
            cfg = self._config_file()
            if cfg.exists():
                with open(cfg, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception:
            pass
        return {"last_tab": None, "tab_order": []}

    def save_state(self) -> None:
        """
        Spara flikstatus atomiskt till config/tab_state.json (A9).

        Monster: mkstemp -> fdopen -> flush -> fsync -> os.replace.
        Skriver aldrig direkt till malfilen (skyddar mot korruption).
        """
        tmp_path = None
        try:
            cfg = self._config_file()
            cfg.parent.mkdir(parents=True, exist_ok=True)

            data = {
                "last_tab":  self.current_tab,
                "tab_order": self.tab_order,
            }

            fd, tmp_str = tempfile.mkstemp(
                dir=cfg.parent,
                prefix=".%s_" % cfg.stem,
                suffix=".tmp",
            )
            tmp_path = Path(tmp_str)

            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
                f.flush()
                os.fsync(f.fileno())   # A9

            os.replace(tmp_path, cfg)
        except Exception:
            if tmp_path and tmp_path.exists():
                try:
                    tmp_path.unlink()
                except OSError:
                    pass

    # ==========================================================================
    # TANGENTBORDSGENVAGAR
    # ==========================================================================

    def setup_shortcuts(self) -> None:
        """
        Bind globala tangentbordsgenvagar.

        Ctrl+Tab / Ctrl+Shift+Tab  - Nasta/foregaende flik
        Alt+Left / Alt+Right       - Bakat/framat i historik
        Ctrl+1-9 / Alt+1-9         - Valj flik per index
        """
        self.app.bind("<Control-Tab>", self.next_tab)
        self.app.bind("<Control-Shift-Tab>", self.prev_tab)
        self.app.bind("<Alt-Left>", lambda e: self.go_back())
        self.app.bind("<Alt-Right>", lambda e: self.go_forward())

        for i in range(1, 10):
            self.app.bind(
                "<Control-Key-%d>" % i,
                lambda e, idx=i - 1: self.select_by_index(idx)
            )
            self.app.bind(
                "<Alt-Key-%d>" % i,
                lambda e, idx=i - 1: self.select_by_index(idx)
            )

    # ==========================================================================
    # LAGG TILL FLIK
    # ==========================================================================

    def add_tab(self, name, title, icon=None, closable=False):
        """
        Lagg till en ny flik.

        Anropas av andra plugins i deras init()-metod.

        Parametrar:
            name:     unikt nyckelnamn (t.ex. "settings")
            title:    visningsnamn (t.ex. "Installningar")
            icon:     ikon-strang (None -> hamtas fran DEFAULT_ICONS)
            closable: visa stang-knapp om True

        Returnerar:
            tk.Frame dar pluginet bygger sin UI.
            Returnerar befintlig Frame om fliken redan finns.
        """
        if not self.is_active:
            return None
        if name in self.tabs:
            return self.tab_frames[name]

        # -- Ikon ----------------------------------------------
        self.tab_icons[name] = icon or self.DEFAULT_ICONS.get(name, "")

        # -- Flik-container ------------------------------------
        tab_container = tk.Frame(self.tab_bar, bg=self.COLOR_TAB_INACTIVE)
        tab_container.pack(side=tk.LEFT, padx=1)

        display = (
            "%s %s" % (self.tab_icons[name], title)
            if self.tab_icons[name] else title
        )

        # -- Fliknapp ------------------------------------------
        btn = tk.Button(
            tab_container,
            text=display,
            command=lambda n=name: self.select_tab(n),
            relief=tk.FLAT,
            bg=self.COLOR_TAB_INACTIVE,
            fg=self.COLOR_FG_INACTIVE,
            activebackground=self.COLOR_TAB_ACTIVE,
            activeforeground=self.COLOR_FG_ACTIVE,
            font=("Segoe UI", 10),
            padx=15,
            pady=8,
            cursor="hand2",
            bd=0,
        )
        btn.pack(side=tk.LEFT)
        btn.bind(
            "<Enter>",
            lambda e, b=btn, n=name: self._on_tab_hover(b, n, True)
        )
        btn.bind(
            "<Leave>",
            lambda e, b=btn, n=name: self._on_tab_hover(b, n, False)
        )
        btn.bind(
            "<Button-3>",
            lambda e, n=name: self._show_tab_context_menu(e, n)
        )
        btn.bind(
            "<Double-Button-1>",
            lambda e, n=name: self._on_tab_double_click(n)
        )

        # -- Stang-knapp (valfritt) ----------------------------
        close_btn = None
        if closable:
            close_btn = tk.Button(
                tab_container,
                text="\u00d7",
                command=lambda n=name: self.close_tab(n),
                relief=tk.FLAT,
                bg=self.COLOR_TAB_INACTIVE,
                fg=self.COLOR_CLOSE_BTN,
                activebackground=self.COLOR_BADGE,
                activeforeground=self.COLOR_FG_ACTIVE,
                font=("Segoe UI", 10),
                padx=4,
                pady=0,
                cursor="hand2",
                bd=0,
            )
            close_btn.pack(side=tk.LEFT)
            close_btn.bind(
                "<Enter>",
                lambda e, b=close_btn: b.config(fg=self.COLOR_BADGE)
            )
            close_btn.bind(
                "<Leave>",
                lambda e, b=close_btn: b.config(fg=self.COLOR_CLOSE_BTN)
            )

        # -- Badge (dold) --------------------------------------
        badge = tk.Label(
            tab_container,
            text="",
            bg=self.COLOR_BADGE,
            fg=self.COLOR_FG_ACTIVE,
            font=("Segoe UI", 8, "bold"),
            padx=4,
            pady=0,
        )
        self.tab_badges[name] = badge

        # -- Content frame -------------------------------------
        frame = tk.Frame(self.content, bg=self.COLOR_BG)

        # -- Registrera ----------------------------------------
        self.tabs[name] = {
            "button":    btn,
            "container": tab_container,
            "title":     title,
            "closable":  closable,
            "close_btn": close_btn,
        }
        self.tab_frames[name]  = frame
        self.tab_buttons[name] = btn
        self.tab_order.append(name)

        # -- Tooltip med kortkommando --------------------------
        idx      = len(self.tab_order)
        shortcut = "Ctrl+%d" % idx if idx <= 9 else ""
        tip      = "%s\n%s" % (title, shortcut) if shortcut else title
        self._add_tooltip(btn, tip)

        # -- Auto-valj -----------------------------------------
        if (
            len(self.tabs) == 1
            or self.saved_state.get("last_tab") == name
        ):
            self.select_tab(name)

        self.log_action("Flik tillagd: %s (%s)" % (name, title))
        self._register_visa_menu(name, title)
        return frame

    # ==========================================================================
    # HOVER OCH SCROLL
    # ==========================================================================

    def _get_default_icon(self, name: str) -> str:
        """Hamta standardikon baserat pa fliknamn."""
        return self.DEFAULT_ICONS.get(name, "")

    def _on_tab_hover(self, btn, name, entering: bool) -> None:
        """Hover-effekt pa inaktiv flik."""
        if not self.is_active or name == self.current_tab:
            return
        btn.config(
            bg=self.COLOR_TAB_HOVER if entering else self.COLOR_TAB_INACTIVE,
            fg=self.COLOR_FG_HOVER  if entering else self.COLOR_FG_INACTIVE,
        )

    def _on_tab_bar_configure(self, event) -> None:
        """Uppdatera canvas scrollregion nar flikar laggs till/tas bort."""
        self.tab_canvas.configure(
            scrollregion=self.tab_canvas.bbox("all")
        )

    def _on_tab_scroll(self, event) -> None:
        """Horisontell scroll av flikraden med mushjul."""
        delta = (
            -1 * (event.delta // 120)
            if hasattr(event, "delta") and event.delta else 0
        )
        self.tab_canvas.xview_scroll(delta, "units")

    # ==========================================================================
    # HOGERKLICK-MENY
    # ==========================================================================

    def _make_menu(self) -> tk.Menu:
        """
        Skapa en standardiserad dropdown-meny (Q1).

        Samlar meny-styling sa att hogerklick-menyn och
        hamburger-menyn far identiskt utseende och foljer
        aktuella tema-farger.
        """
        return tk.Menu(
            self.app, tearoff=0,
            bg=self.COLOR_MENU_BG, fg=self.COLOR_FG_ACTIVE,
            activebackground=self.COLOR_TAB_ACTIVE,
            activeforeground=self.COLOR_FG_ACTIVE,
        )

    def _show_tab_context_menu(self, event, name) -> None:
        """
        Hogerklick-meny per flik.
        Alternativ: Fast | Duplicera | Flytta | Stang | Stang andra
        """
        menu = self._make_menu()
        menu.add_command(
            label="Fast flik",
            command=lambda: self.pin_tab(name)
        )
        menu.add_command(
            label="Duplicera flik",
            command=lambda: self.duplicate_tab(name)
        )
        menu.add_separator()
        menu.add_command(
            label="\u25c0 Flytta vanster",
            command=lambda: self.move_tab(name, -1)
        )
        menu.add_command(
            label="\u25b6 Flytta hoger",
            command=lambda: self.move_tab(name, 1)
        )
        menu.add_separator()
        menu.add_command(
            label="Dolj denna flik",
            command=lambda: self._hide_tab_from_menu(name)
        )
        if self.tabs[name].get("closable"):
            menu.add_command(
                label="\u2715 Stang",
                command=lambda: self.close_tab(name)
            )
        menu.add_command(
            label="\u2715 Stang andra",
            command=lambda: self.close_other_tabs(name)
        )
        menu.tk_popup(event.x_root, event.y_root)

    def _hide_tab_from_menu(self, name: str) -> None:
        """Dolj flik via hogerklick - synkar med main.py:s toggle_tab."""
        try:
            var = self.app._tab_menu_vars.get(name)
            if var:
                var.set(False)
            self.app._hide_tab(name)
            self.app._tab_vis_mgr.set_visible(name, False)
        except Exception:
            pass

    def _on_tab_double_click(self, name: str) -> None:
        """Dubbelklick pa flik (placeholder)."""
        self.log_action("Dubbelklick: %s" % name)

    # ==========================================================================
    # TOOLTIP
    # ==========================================================================

    def _add_tooltip(self, widget, text: str) -> None:
        """
        Visa tooltip-bubba vid hover.
        Auto-doljs efter 2.5 sekunder (Q3).

        Q3: after-id sparas + Toplevel destroyas innan en ny visas,
        och after-callbacken avbryts vid hide -> inga foraldrade
        Toplevel-fonster eller after-callbacks kan lämnas kvar.
        """
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
                         padx=8, pady=4,
                relief="solid", borderwidth=1,
            ).pack()
            widget._tooltip = tip
            widget._tooltip_after = widget.after(2500, _destroy)

        def hide(event):
            _destroy()

        widget.bind("<Enter>", show)
        widget.bind("<Leave>", hide)

    # ==========================================================================
    # VALJ FLIK
    # ==========================================================================

    def select_tab(self, name: str) -> None:
        """
        Valj och visa en flik.

        Steg:
          1. Lagg till current_tab i tab_history (max 50)
          2. Tom forward_history (ny riktning)
          3. Visa via _show_tab()
          4. Spara state
        """
        if not self.is_active or name not in self.tabs:
            return

        if self.current_tab and self.current_tab != name:
            self.tab_history.append(self.current_tab)
            self.tab_history = self.tab_history[-50:]
            self.forward_history.clear()

        self._show_tab(name)
        self.save_state()
        self.log_action("Visar: %s" % self.tabs[name]["title"])

    def _show_tab(self, name: str) -> None:
        """
        Intern: visa flik utan att skriva till historik.
        Gom alla frames, applicera stilar, visa vald.
        """
        for frame in self.tab_frames.values():
            frame.pack_forget()
        self._apply_tab_styles(name)
        self.tab_frames[name].pack(fill=tk.BOTH, expand=True)
        self.current_tab = name
        self.clear_badge(name)
        self._update_nav_buttons()

    def _apply_tab_styles(self, active_name) -> None:
        """
        Applicera aktiv/inaktiv stil pa alla fliknapparna.

        Aktiv:   COLOR_TAB_ACTIVE, vit text, bold
        Inaktiv: COLOR_TAB_INACTIVE, gra text, normal
        """
        for tab_name, tab_info in self.tabs.items():
            btn       = tab_info["button"]
            container = tab_info["container"]
            close_btn = tab_info.get("close_btn")
            if tab_name == active_name:
                btn.config(
                    bg=self.COLOR_TAB_ACTIVE,
                    fg=self.COLOR_FG_ACTIVE,
                    font=("Segoe UI", 10, "bold"),
                )
                container.config(bg=self.COLOR_TAB_ACTIVE)
                # Q2: stang-knappen foljer aktiv flik-bakgrund
                if close_btn is not None and self.widget_exists(close_btn):
                    close_btn.config(bg=self.COLOR_TAB_ACTIVE)
            else:
                btn.config(
                    bg=self.COLOR_TAB_INACTIVE,
                    fg=self.COLOR_FG_INACTIVE,
                    font=("Segoe UI", 10),
                )
                container.config(bg=self.COLOR_TAB_INACTIVE)
                if close_btn is not None and self.widget_exists(close_btn):
                    close_btn.config(bg=self.COLOR_TAB_INACTIVE)

    def _update_nav_buttons(self) -> None:
        """Aktivera/inaktivera back/forward baserat pa historik."""
        has_back    = bool(self.tab_history)
        has_forward = bool(self.forward_history)
        self.back_btn.config(
            state="normal" if has_back else "disabled",
            fg=self.COLOR_FG_ACTIVE if has_back else self.COLOR_FG_INACTIVE,
        )
        self.forward_btn.config(
            state="normal" if has_forward else "disabled",
            fg=self.COLOR_FG_ACTIVE if has_forward else self.COLOR_FG_INACTIVE,
        )

    # ==========================================================================
    # HISTORIK-NAVIGATION
    # ==========================================================================

    def go_back(self) -> None:
        """Ga till foregaende flik i historiken (Alt+Left)."""
        if not self.tab_history:
            return
        prev = self.tab_history.pop()
        self.forward_history.append(self.current_tab)
        self._show_tab(prev)
        self._update_nav_buttons()

    def go_forward(self) -> None:
        """Ga framat i historiken (Alt+Right)."""
        if not self.forward_history:
            return
        nxt = self.forward_history.pop()
        self.tab_history.append(self.current_tab)
        self._show_tab(nxt)
        self._update_nav_buttons()

    def _select_tab_no_history(self, name: str) -> None:
        """Valj flik utan att paverka historik."""
        if name not in self.tabs:
            return
        self._show_tab(name)

    # ==========================================================================
    # STANG / ORDNA FLIKAR
    # ==========================================================================

    def _remove_tab_internal(self, name: str) -> None:
        """Forinta en flik utan att spara state eller logga (v2.5.0).

        Delas av close_tab() och close_other_tabs() sa att manga
        flikar kan stangas med EN spara-/logg-operation i stallet for
        en skrivning per flik. Rensar aven bort fliken ur bada
        historiklistorna, sa att Back/Forward aldrig hamnar pa en
        forstord flik (kunde tidigare ge KeyError i _show_tab).
        """
        if name not in self.tabs:
            return
        try:
            self.tabs[name]["container"].destroy()
        except Exception:
            pass
        try:
            self.tab_frames[name].destroy()
        except Exception:
            pass

        del self.tabs[name]
        del self.tab_frames[name]
        del self.tab_buttons[name]
        if name in self.tab_order:
            self.tab_order.remove(name)
        self.tab_badges.pop(name, None)
        self.tab_icons.pop(name, None)
        # Rensa historiken fran den stangda fliken
        if name in self.tab_history:
            self.tab_history = [h for h in self.tab_history if h != name]
        if name in self.forward_history:
            self.forward_history = [
                h for h in self.forward_history if h != name
            ]

    def close_tab(self, name: str) -> None:
        """
        Stang en closable flik.
        Tar bort widget, frame och alla interna strukturer.
        Valjer narmaste flik om den stangda var aktiv.
        """
        if name not in self.tabs or not self.tabs[name].get("closable"):
            return
        self._remove_tab_internal(name)

        if self.current_tab == name:
            self.current_tab = None
            if self.tab_order:
                self.select_tab(self.tab_order[0])

        self.save_state()
        self.log_action("Stangde flik: %s" % name)

    def close_other_tabs(self, keep_name: str) -> None:
        """Stang alla closable flikar utom keep_name (v2.5.0 bulk)."""
        others = [
            n for n in list(self.tab_order)
            if n != keep_name
            and self.tabs.get(n, {}).get("closable")
        ]
        for name in others:
            self._remove_tab_internal(name)

        if self.current_tab in others:
            self.current_tab = None
            if self.tab_order:
                self.select_tab(self.tab_order[0])

        if others:
            self.save_state()
            self.log_action("Stangde %d flik(ar)" % len(others))

    def pin_tab(self, name: str) -> None:
        """Fast flik: flytta till position 0 i ordningen."""
        if name not in self.tab_order:
            return
        self.tab_order.remove(name)
        self.tab_order.insert(0, name)
        self._reorder_tabs()
        self.save_state()
        self.log_action("Faste flik: %s" % name)

    def move_tab(self, name: str, direction: int) -> None:
        """
        Flytta flik ett steg vanster (-1) eller hoger (+1).
        Ignoreras om fliken ar i ytterposition.
        """
        if name not in self.tab_order:
            return
        idx     = self.tab_order.index(name)
        new_idx = idx + direction
        if 0 <= new_idx < len(self.tab_order):
            self.tab_order.remove(name)
            self.tab_order.insert(new_idx, name)
            self._reorder_tabs()
            self.save_state()

    def _reorder_tabs(self) -> None:
        """Ompacka fliknapparna enligt aktuell tab_order."""
        for name in self.tab_order:
            if name in self.tabs:
                c = self.tabs[name]["container"]
                c.pack_forget()
                c.pack(side=tk.LEFT, padx=1)

    def duplicate_tab(self, name: str) -> None:
        """Duplicera flik - placeholder."""
        self.log_action("Duplicera: %s (ej implementerat)" % name)

    # ==========================================================================
    # BADGES
    # ==========================================================================

    def set_badge(self, name: str, text: str) -> None:
        """
        Satt notifikations-badge pa flik.
        Tom text: dolj. Icke-tom: visa rod badge.
        """
        if name not in self.tab_badges:
            return
        badge = self.tab_badges[name]
        if text:
            badge.config(text=str(text))
            badge.pack(side=tk.LEFT, padx=(0, 5))
        else:
            badge.pack_forget()

    def clear_badge(self, name: str) -> None:
        """Ta bort badge fran flik."""
        self.set_badge(name, "")

    # ==========================================================================
    # HAMBURGER-MENY
    # ==========================================================================

    def _register_visa_menu(self, name, title) -> None:
        """Lagg fliken i Visa-menyn sa den inte 'saknas' dar."""
        try:
            if not hasattr(self.app, "visa_menu"):
                return
            vars_ = getattr(self.app, "_tab_menu_vars", None)
            if vars_ is None:
                return
            if name in vars_:
                return
            var = tk.BooleanVar(value=True)
            vars_[name] = var
            frames = getattr(self.app, "tab_frames", None)
            if isinstance(frames, dict):
                frames[name] = self.tab_frames.get(name)
            self.app.visa_menu.add_checkbutton(
                label="    %s" % title,
                variable=var,
                command=lambda n=name: self._toggle_from_visa(n),
            )
        except Exception:
            pass

    def _toggle_from_visa(self, name) -> None:
        """Visa-menyns checkbox: visa/dolj tab_manager-flik."""
        try:
            var = self.app._tab_menu_vars.get(name)
            if var is None:
                return
            if var.get():
                self.show_tab_button(name)
                self.select_tab(name)
            else:
                self.hide_tab_button(name)
        except Exception:
            pass

    def hide_tab_button(self, name) -> None:
        """Gom flikknappen (pack_forget) utan att forstora innehallet."""
        info = self.tabs.get(name)
        if not info:
            return
        try:
            info["container"].pack_forget()
        except Exception:
            pass
        if self.current_tab == name:
            nxt = None
            for n in self.tab_order:
                if n == name:
                    continue
                try:
                    if self.tabs[n]["container"].winfo_ismapped():
                        nxt = n
                        break
                except Exception:
                    continue
            if nxt:
                self.select_tab(nxt)
            else:
                try:
                    for frame in self.tab_frames.values():
                        frame.pack_forget()
                except Exception:
                    pass
                self.current_tab = None

    def show_tab_button(self, name) -> None:
        """Visa en dold flikknapp igen."""
        info = self.tabs.get(name)
        if not info:
            return
        try:
            if not info["container"].winfo_ismapped():
                info["container"].pack(side=tk.LEFT, padx=1)
        except Exception:
            try:
                info["container"].pack(side=tk.LEFT, padx=1)
            except Exception:
                pass

    def show_tab_menu(self) -> None:
        """
        Visa dropdown med alla flikar.
        Visar punkt framfor aktiv flik och Ctrl+N-genvag.
        """
        menu = self._make_menu()
        menu.add_command(
            label="\u2550\u2550\u2550  Alla flikar  \u2550\u2550\u2550",
            state="disabled"
        )
        menu.add_separator()

        for i, name in enumerate(self.tab_order):
            info  = self.tabs[name]
            icon  = self.tab_icons.get(name, "")
            label = "%s %s" % (icon, info["title"]) if icon else info["title"]
            if name == self.current_tab:
                label = "\u25cf %s" % label
            shortcut = "Ctrl+%d" % (i + 1) if i < 9 else ""
            menu.add_command(
                label=label,
                accelerator=shortcut,
                command=lambda n=name: self.select_tab(n),
            )

        menu.add_separator()
        menu.add_command(
            label="\u27f3 Uppdatera alla",
            command=self.refresh_all_tabs,
        )

        try:
            x = self.tools_frame.winfo_rootx()
            y = (
                self.tools_frame.winfo_rooty()
                + self.tools_frame.winfo_height()
            )
            menu.tk_popup(x, y)
        except Exception:
            pass

    def refresh_all_tabs(self) -> None:
        """Anropa refresh() pa alla plugin-instanser som stoder det."""
        self.log_action("Uppdaterar alla flikar...")
        for name in self.tab_order:
            plugin = self.app.context.get("_%s" % name)
            if plugin and hasattr(plugin, "refresh"):
                try:
                    plugin.refresh()
                except Exception as e:
                    self.log_action(
                        "Refresh misslyckades for %s: %s" % (name, e)
                    )

    # ==========================================================================
    # TEMA-BYTE (C1)
    # ==========================================================================

    def on_theme_changed(self, event=None) -> None:
        """
        Uppdatera alla flikfarger vid tema-byte.

        Laddar nya farger fran ThemeEngine och applicerar dem
        pa alla befintliga widgets utan omstart.
        """
        if not self.is_active:
            return
        self._load_theme_colors()
        self._restyle_all_tabs()


    # ==========================================================================
    # PUBLIK API
    # ==========================================================================

    def get_tab(self, name: str):
        """Hamta flikens Frame. None om saknas."""
        return self.tab_frames.get(name)

    def next_tab(self, event=None):
        """Nasta flik (Ctrl+Tab). Loopar runt."""
        if not self.tab_order or not self.current_tab:
            return "break"
        idx = self.tab_order.index(self.current_tab)
        self.select_tab(
            self.tab_order[(idx + 1) % len(self.tab_order)]
        )
        return "break"

    def prev_tab(self, event=None):
        """Foregaende flik (Ctrl+Shift+Tab). Loopar runt."""
        if not self.tab_order or not self.current_tab:
            return "break"
        idx = self.tab_order.index(self.current_tab)
        self.select_tab(
            self.tab_order[(idx - 1) % len(self.tab_order)]
        )
        return "break"

    def select_by_index(self, index: int) -> None:
        """Valj flik via numeriskt index (Ctrl+1 = index 0)."""
        if index < len(self.tab_order):
            self.select_tab(self.tab_order[index])

    def get_current_tab(self) -> str:
        """Returnerar aktuellt fliknamn (str eller None)."""
        return self.current_tab

    def get_tab_count(self) -> int:
        """Returnerar antal flikar."""
        return len(self.tabs)

    def tab_exists(self, name: str) -> bool:
        """Returnerar True om fliken finns."""
        return name in self.tabs

    def set_tab_title(self, name: str, new_title: str) -> None:
        """
        Andra visningstitel pa en flik.
        Uppdaterar knapptexten med ikon + ny titel.
        """
        if name not in self.tabs:
            return
        self.tabs[name]["title"] = new_title
        icon    = self.tab_icons.get(name, "")
        display = "%s %s" % (icon, new_title) if icon else new_title
        self.tabs[name]["button"].config(text=display)

    def flash_tab(self, name: str, times: int = 3) -> None:
        """
        Blinka en flik for att dra uppmarksamhet.
        Ignoreras om fliken ar aktiv.
        Blinkar times ganger (300ms intervall).
        """
        if name not in self.tabs or name == self.current_tab:
            return

        btn         = self.tabs[name]["button"]
        original_bg = btn.cget("bg")

        def _flash(count):
            # v2.5.0: avbryt om inaktiv/forstord samt spara timer-id
            # sa att en pagaende blink kan avbrytas i cleanup().
            if count <= 0 or not self.is_active \
               or not self.widget_exists(btn):
                self._flash_after = None
                if self.widget_exists(btn):
                    try:
                        btn.config(bg=original_bg)
                    except Exception:
                        pass
                return
            current = btn.cget("bg")
            new_bg  = (
                self.COLOR_FLASH
                if current == original_bg else original_bg
            )
            try:
                btn.config(bg=new_bg)
            except Exception:
                self._flash_after = None
                return
            self._flash_after = self.app.after(
                300, lambda: _flash(count - 1)
            )

        _flash(times * 2)

    # ==========================================================================
    # OVRIGT
    # ==========================================================================

    def log_action(self, message: str) -> None:
        """
        Logga via _logger i context (DEBUG-niva).
        Tyst fallback om _logger saknas - ingen print().
        """
        try:
            logger = self.app.context.get("_logger")
            if logger and hasattr(logger, "log"):
                logger.log("DEBUG", "[Flik] %s" % message)
        except Exception:
            pass

    def on_closing(self) -> None:
        """
        Spara state vid stangning.

        NOTERA: Registreras INTE med app.protocol("WM_DELETE_WINDOW")
        eftersom system_tray-plugin ager den handelsen.
        Anropas istallet fran app.quit_app() -> cleanup().
        """
        self.is_active = False
        self.save_state()

    def cleanup(self) -> None:
        """Stada upp och spara state (anropas fran app.quit_app())."""
        self.is_active = False
        # v2.5.0: avbryt en eventuell pagaende flikblink
        if self._flash_after is not None:
            try:
                self.app.after_cancel(self._flash_after)
            except Exception:
                pass
            self._flash_after = None
        self.save_state()
