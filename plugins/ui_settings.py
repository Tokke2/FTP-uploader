#!/usr/bin/env python3
# ============================================================
# Plugin: Installningspanel
# ============================================================
# FIL:       plugins/ui_settings.py
# PLATS:     plugins/ (ftp_gallery_uploader/plugins/ui_settings.py)
# Klass:     SettingsUI(BasePlugin)
# PRIORITY:  1
# VERSION:   2.7.1
# AUTHOR:    Rickard Längkvist
# ÄNDRINGAR v2.7.0 → v2.7.1:
#   Mixin-import GeneratedGalleryMixin (try/except). FS-11 rensning
#   av doda historikposter sker i ui_settings_gallery.py v1.2.0.
# COPYRIGHT: Copyright (c) <år> Rickard Längkvist (dynamiskt år,
#            se COPYRIGHT-konstanten nedan)
#
# ÄNDRINGAR v2.6.1 → v2.6.2:
#   [B5]      Import av advanced_logger_guards ar OPTIONAL. Saknas
#             filen kraschade HELA modulimporten -> pluginet
#             hoppades over -> Inställningar-fliken forsvann
#             ("12 plugins laddade"). Fallback: 9 pt lokalt.
#
# ÄNDRINGAR v2.5.0 → v2.6.0 (KOD/DESIGN + ANPASSAD TEXT & FÖNSTER):
#   [Z1]      register_theme_callback()-override:n BORTTAGEN: den gjorde
#             app.bind("<<ThemeChanged>>") som ERSATTE andra plugins
#             bindningar (enda sista pluginet fick temat). Nu används
#             base_plugin v1.4.1s delade dispatcher (BUG-024-familjen).
#   [Z2]      Duplicerade log/log_error/load_config/save_config/
#             widget_exists BORTTAGNA (~95 rader) - ärvs från base_plugin
#             v1.4.1 (atomiskt + .bak-rotation + korrupt-karantän +
#             schema-meta). Mindre kod, starkare beteende.
#   [Z3]      ANPASSAD TEXT (T1): teckenstorlek räknas från skärmens
#             DPI/tk-scaling via advanced_logger_guards (suggest_font_size/
#             clamp_font_size) - samma motor som Loggvisaren. Alla labels,
#             sektioner, knappar och inmatningsfält skalar; entry-bredder
#             och slider-längd följer storleken.
#   [Z4]      ANPASSAT FÖNSTER (T2): panelen känner av sin bredd och
#             växlar NORMALT/KOMPAKT läge (<640 px): mindre padding,
#             wraplength på långa rader (output-sökvägen), slider-längd
#             efter tillgänglig bredd. Layoutskiftet loggas.
#   [Z5]      DESIGN: färger via BasePlugin.get_theme_color (TTL-cachad),
#             alla knappar registreras i base_plugins tema-register (G11),
#             save_settings varnar om bildmappen saknas (sparar ändå).
#
# ÄNDRINGAR v2.4.0 → v2.5.0 (kvalitet/minne/snabbhet, icke-brytande):
#   [Q1]      Ny fabrik _mk_section(): LabelFrame-boilerplate samlad
#             (bg/fg/font/padx/pady/pack/registrering) -> identiskt
#             utseende i alla fyra titulerade sektioner + mindre kod.
#   [Q2]      _collect_settings() samlar hela data-dict en gang och
#             delas av save_settings() + cleanup() -> ingen duplicerad
#             config-logik som kan driva isar.
#   [Q3]      on_folder_changed(): den dyra katalog-skanningen
#             (bildrakning) debounce-as via after() sa att varje
#             tangenttryck ger max en skanning. Output/titel uppdateras
#             dock omedelbart (snabbhet).
#   [Q4]      _reg_panels()/_reg_labels() de-duplicerar registrering
#             -> inga dubbla tema-omstylingar (minne/snabbhet).
#
# ÄNDRINGAR v2.3.0 → v2.4.0 (DESIGN-SYSTEM-integration, spec v4.6.0):
#   [C1]      Fargerna hamtas nu fran ThemeEngine-designsystemet
#             (helpers v1.3.0, 58 nycklar/tema) via _THEME_KEYS:
#               COLOR_BG/COLOR_BG_MID  <- "bg"/"surface_alt"
#               COLOR_FG/COLOR_MUTED   <- "fg"/"muted"
#               COLOR_ACCENT           <- "accent"
#   [C1]      _load_theme_colors(): hamtar farger fran
#             app.theme_engine.get_color() med fallback till
#             klassattributen (fungerar aven utan tema-engine)
#   [C1]      _restyle_all(): applicerar aktuella farger pa alla
#             befintliga widgets (paneler, labels, canvas) vid
#             tema-byte - tidigare uppdaterades bara canvas
#   [C1]      on_theme_changed(): _load_theme_colors() +
#             _restyle_all() - full tema-uppdatering utan omstart
#   [C1]      register_theme_callback(): ny egen metod (nammnd i
#             v2.3.0-headern men saknades) - anropas i init()
#   [C1]      _get_bg(): anvander te.get_color("bg") istallet
#             for legacy te.current.get("bg")
#   [C1]      Nya hjälpare: _ensure_theme_lists, _reg_panels,
#             _reg_labels, _mk_label (skapar+registrerar labels),
#             _safe_cfg (tyst config)
#   [C4]      Alla ramar/labels registreras for tema-omstyling;
#             alla fargvarden via COLOR_*-attribut
#
# BEVARAT FRÅN v2.3.0 (log/config ärvs numera från base_plugin, Z2):
#   Ingen print() - all loggning via self.log()
#   open_output_folder: subprocess.Popen (blockerar ej)
#   execute: ValueError-fangst returnerar context oforandrad
#   cleanup: tyst felhantering
#   _build_scroll_container: tk.Frame wrapper (inte ttk.Frame)
#       -> ingen gra bakgrund
#   container: tk.Frame(bg=bg) for att matcha canvas
#   Alla sektioner: tk.LabelFrame(bg=...) istf ttk.LabelFrame
#   Titel-synkronisering (BUG-019) + PDF & Video-export (BUG-020)
#
# ANSVARAR FOR:
#   - Installningspanel i "settings"-tabben
#   - Bildmapp, output, titel, tema, kolumner
#   - Thumbnail-storlek, kvalitet, EXIF
#   - FTP-konfiguration (losenord sparas ALDRIG)
#   - Lasa/spara config/settings.json
#
# CONTEXT SOM LASES:
#   '_tab_manager'   - add_tab()
#   '_menu_manager'  - add_recent_folder(), run_generate()
#   '_controls'      - run_generate()
#
# CONTEXT SOM SATTS:
#   '_settings'      - self
#   'gallery'        - dict med alla galleri-installningar
#   'ftp_settings'   - dict (server, user, password, path)
#   'ftp_enabled'    - bool
#   'pdf_files'      - lista [{"original_name","name","filename","relative_path"}]
#   'video_files'    - lista [{"original_name","name","filename","relative_path"}]
#
# VARIABLER (tk.*Var):
#   folder_var, output_var, title_var, desc_var, theme_var
#   cols_var, thumb_size_var, fullsize_var, quality_var
#   preserve_exif_var, auto_rotate_var
#   ftp_enabled_var, ftp_server_var, ftp_user_var,
#   ftp_pass_var, ftp_path_var
#
# JSON: config/settings.json
#   OBS: ftp.password sparas ALDRIG
#
# IMPORTER:
#   tkinter as tk, ttk, filedialog, messagebox
#   pathlib.Path
#   subprocess, sys, shutil
#   datetime
#   .base_plugin: BasePlugin
#   .advanced_logger_guards: clamp_font_size, suggest_font_size (Z3)
# ============================================================

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path
import subprocess
import sys
import shutil
import re
from datetime import datetime

from .base_plugin import BasePlugin

# Mixin for historik/out/-gallerier. Saknas filen far pluginet
# inte krascha vid import (annars forsvinner Inställningar-fliken).
try:
    from .ui_settings_gallery import GeneratedGalleryMixin
except Exception:
    class GeneratedGalleryMixin(object):
        def browse_generated_gallery(self):
            try:
                messagebox.showerror(
                    "Saknas",
                    "plugins/ui_settings_gallery.py saknas.",
                )
            except Exception:
                pass

# B5: guards-importen FAR INTE falla pluginet. Saknas filen (vanligt nar
# bara ui_settings.py kopierats) forsvann hela Inställningar-fliken.
try:
    from .advanced_logger_guards import clamp_font_size, suggest_font_size
except Exception:
    def suggest_font_size(app=None, base=9):
        return int(base) if base else 9

    def clamp_font_size(size, fallback=9):
        try:
            n = int(size)
        except Exception:
            return fallback
        if n < 7:
            return 7
        if n > 18:
            return 18
        return n


class SettingsUI(GeneratedGalleryMixin, BasePlugin):
    """
    Installningspanel i egen flik.

    Sparar till config/settings.json (atomiskt).
    FTP-losenord sparas ALDRIG till disk.
    Registreras som app.context['_settings'].

    v2.6.0:
    - Z1 register_theme_callback via base_plugins delade dispatcher
    - Z2 log/config/widget_exists arvade fran base_plugin (ingen duplikat)
    - Z3 anpassad text: DPI-baserad teckenstorlek, skalade bredder
    - Z4 anpassat fonster: kompakt lage i smalt fonster (wraplength,
      padding, sliderlangd) - layoutskiftet loggas
    - Z5 tema-farger via get_theme_color, knappar i base_plugins
      tema-register, varning vid sparande av saknad mapp

    v2.5.0:
    - _mk_section()-fabrik: identiskt sektionsutseende, mindre kod
    - _collect_settings(): en data-kalla for save + cleanup (inga drev)
    - on_folder_changed(): debounce av dyr bildrakning (snabbhet)

    v2.4.0:
    - Fargerna foljer ThemeEngine-designsystemet och uppdateras
      dynamiskt vid tema-byte (on_theme_changed + _restyle_all)
    - register_theme_callback() som egen metod

    v2.3.0:
    - Inga f-strings (B1) - all %-formatering
    - Atomisk skrivning med fsync (A9)
    - config/ via helpers (A10)
    - EXAKT 3 teman: Morkt / Ljust / System (C1)
    """

    PLUGIN_NAME = "Inställningar"
    PRIORITY    = 1
    VERSION     = "2.7.1"
    AUTHOR      = "Rickard Längkvist"
    COPYRIGHT   = "Copyright (c) %d %s" % (datetime.now().year, "Rickard Längkvist")

    IMAGE_FORMATS = {
        ".jpg", ".jpeg", ".png", ".gif",
        ".webp", ".bmp", ".tiff", ".tif", ".heic", ".heif",
    }

    VIDEO_FORMATS = {
        ".mp4", ".avi", ".mov", ".qt", ".mkv", ".wmv", ".flv",
        ".webm", ".m4v", ".mpg", ".mpeg", ".3gp", ".ts",
    }

    # Standardfarger (uppdateras fran ThemeEngine, C1)
    COLOR_BG      = "#1e1e1e"
    COLOR_BG_MID  = "#252535"
    COLOR_FG      = "#ffffff"
    COLOR_MUTED   = "#888888"
    COLOR_ACCENT  = "#4a90d9"

    # -- Tema-nyckelmappning (C1) ------------------------------
    _THEME_KEYS = {
        "COLOR_BG":      "bg",
        "COLOR_BG_MID":  "surface_alt",
        "COLOR_FG":      "fg",
        "COLOR_MUTED":   "muted",
        "COLOR_ACCENT":  "accent",
    }

    # ==========================================================================
    # TEMA-FARGER (C1) + TEXT/FÖNSTER-ANPASSNING (Z3/Z4)
    # ==========================================================================

    def _ensure_theme_lists(self) -> None:
        """Initiera label-parslistan (fg-attribut kraver egen lista)."""
        if not hasattr(self, "_labels"):
            self._labels = []

    def _reg_panels(self, *widgets) -> None:
        """Registrera ramar/LabelFrames i base_plugins tema-register (Z5)."""
        for w in widgets:
            try:
                self.register_panel(w)
            except Exception:
                pass

    def _reg_labels(self, *pairs) -> None:
        """Registrera (widget, fg-attribut)-par for tema-omstyling (de-dup)."""
        for pair in pairs:
            if pair and pair not in self._labels:
                self._labels.append(pair)

    # -- Z3: anpassad text (DPI-baserad teckenstorlek) ----------

    def _apply_text_adaptation(self) -> None:
        """
        Räkna ut teckenstorlek och skalfaktor från skärmens DPI (Z3).

        Samma motor som Loggvisaren (advanced_logger_guards):
        96 DPI -> 9 pt, 120 -> 10 pt, 144 -> 11 pt, 192 -> 12 pt.
        Skalfaktorn driver entry-bredder och slider-längd.
        """
        try:
            self._base_font_size = clamp_font_size(suggest_font_size(self.app))
        except Exception:
            self._base_font_size = 9
        self._font_scale = round(self._base_font_size / 9.0, 3)

    def _font(self, style=None):
        """Aktuell UI-font: ("Segoe UI", <DPI-anpassad storlek>[, stil])."""
        if style:
            return ("Segoe UI", self._base_font_size, style)
        return ("Segoe UI", self._base_font_size)

    def _scaled(self, value):
        """Skala ett pixel-/enhetsvärde med teckenstorlekens faktor (Z3)."""
        try:
            return int(round(value * self._font_scale))
        except Exception:
            return value

    # -- Z4: anpassat fönster (kompakt läge i smalt fönster) ----

    COMPACT_WIDTH = 640

    def _set_output_label(self, lbl) -> None:
        """Spara referens till output-labeln (lång sökväg -> wraplength)."""
        self._output_label = lbl

    def _on_container_configure(self, event=None) -> None:
        """Växla NORMALT/KOMPAKT läge när panelens bredd ändras (Z4)."""
        try:
            width = int(getattr(event, "width", 0) or 0)
            if width <= 0:
                return
            compact = width < self.COMPACT_WIDTH
            if compact == getattr(self, "_compact", None):
                self._apply_layout(compact, width)   # finjustera slider
                return
            self._compact = compact
            self._apply_layout(compact, width)
            self.log("SYSTEM", "Installningar: %s lage (bredd %d px, Z4)"
                     % ("KOMPAKT" if compact else "NORMALT", width))
        except Exception:
            pass

    def _apply_layout(self, compact, width) -> None:
        """Applicera padding/wraplength/slider-längd för läget (Z4)."""
        try:
            if compact:
                pady_x, wrap = 6, max(200, width - 70)
            else:
                pady_x, wrap = 15, 0     # = ursprungligt sektions-padx
            for w in self._sections if hasattr(self, "_sections") else []:
                if self.widget_exists(w):
                    w.config(padx=pady_x)
            if self.widget_exists(getattr(self, "_output_label", None)):
                self._output_label.config(wraplength=wrap)
            q = getattr(self, "_quality_scale", None)
            if self.widget_exists(q):
                q.config(length=max(120, min(260, width // 3)))
        except Exception:
            pass

    def _mk_section(self, parent, text, pady=(5, 5),
                    fill=tk.X) -> tk.LabelFrame:
        """
        Skapa en standardiserad titulerad sektion (Q1).

        Samlar LabelFrame-boilerplate (bg/fg/font/padx/pady/pack/
        tema-registrering) sa att alla sektioner far identiskt
        utseende utan att upprepa koden.
        """
        f = tk.LabelFrame(
            parent, text=text,
            bg=self._bg, fg=self.COLOR_FG,
            font=self._font("bold"),      # Z3: DPI-anpassad
            padx=15, pady=10,
        )
        f.pack(fill=fill, padx=10, pady=pady)
        self._reg_panels(f)
        if hasattr(self, "_sections"):
            self._sections.append(f)
        return f

    def _mk_label(self, parent, text="", fg_attr="COLOR_FG", **kwargs):
        """
        Skapa tk.Label med tema-registrering.

        Packas direkt om pack-kwargs skickas via 'pack'-nyckeln,
        t.ex. _mk_label(f, "Text", pack={"side": tk.LEFT}).
        """
        pack_kw = kwargs.pop("pack", None) or {}
        kwargs.setdefault("bg", self._bg)
        kwargs.setdefault("font", self._font())   # Z3
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
        try:
            for attr, key in self._THEME_KEYS.items():
                current = getattr(self, attr, None) or "#888888"
                setattr(self, attr,
                        self.get_theme_color(key, current))   # Z5, TTL-cachad
        except Exception as e:
            self.log("FEL", "Tema-farger kunde inte laddas: %s" % e)

    def _restyle_all(self) -> None:
        """
        Applicera aktuella farger pa alla befintliga widgets
        (paneler, labels, canvas) vid tema-byte.
        """
        if not self.is_active:
            return
        try:
            self._bg = self.COLOR_BG
            # -- Paneler: base_plugin restylar _theme_reg_panels;
            #    LabelFrame-rubriker behöver fg, därför även egen loop.
            for w in getattr(self, "_theme_reg_panels", []):
                if self.widget_exists(w) and isinstance(w, tk.LabelFrame):
                    self._safe_cfg(w, bg=self._bg, fg=self.COLOR_FG)
            # -- Labels -----------------------------------------
            for lbl, fg_attr in self._labels:
                if self.widget_exists(lbl):
                    self._safe_cfg(
                        lbl, bg=self._bg,
                        fg=getattr(self, fg_attr, "#888888"),
                    )
            # -- Canvas + wrapper -------------------------------
            for w in (
                getattr(self, "_settings_canvas", None),
                getattr(self, "wrapper", None),
            ):
                self._safe_cfg(w, bg=self._bg)
        except Exception:
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

    # OBS (Z1): register_theme_callback() arvs fran base_plugin v1.4.1
    # (delad dispatcher). En egen override med app.bind() ersatte forr
    # alla tidigare bindningar sa att bara SISTA pluginet fick temat.

    # ==========================================================================
    # INIT
    # ==========================================================================

    def init(self, app) -> None:
        """
        Plugin-init.

        Steg:
          1. Skapa tabb via tab_manager
          2. Bygg scroll-container
          3. Bygg UI-sektioner
          4. Ladda sparade installningar
          5. Registrera i context
          6. Registrera tema-callback
        """
        super().init(app)
        self.app = app
        self._output_override = ""
        self._suppress_auto_title = False

        # -- Tema-farger + text/fonster-anpassning (C1/Z3) -----
        self._ensure_theme_lists()
        self._apply_text_adaptation()
        self._load_theme_colors()
        self._sections = []

        # Hamta bakgrundsfarg
        self._bg = self._get_bg()

        # Skapa tabb (B1: alltid synlig - tab_manager, sen notebook)
        parent = self._attach_settings_tab(app)
        if not parent:
            self.log("FEL", "Kunde inte skapa inställnings-tabb")
            return

        # Scroll-container
        self.canvas, self.container = self._build_scroll_container(parent)

        # UI-sektioner
        self.create_folder_section()
        self.create_gallery_section()
        self.create_image_section()
        self.create_ftp_section()
        self.create_buttons()

        # Ladda installningar
        self.load_settings()
        self._saved_settings_snapshot = self._collect_settings()

        # Registrera
        app.context["_settings"] = self

        # Tema-callback via base_plugins delade dispatcher (C1/Z1)
        super().register_theme_callback()

        # Fönsteranpassning: forsta layoutpasset (Z4)
        self._on_container_configure(None)

        # B2: välj fliken så den inte hamnar bakom senare flikar
        self._show_settings_tab()

        # B3: Arkiv-meny + Ctrl+,  (after_idle: efter menu_manager)
        try:
            self.app.after_idle(self._install_settings_menu)
        except Exception:
            self._install_settings_menu()

        self.log("OK", "+ %s v%s" % (self.PLUGIN_NAME, self.VERSION))

    def _attach_settings_tab(self, app):
        """
        Skapa inställningsfliken så den ALLTID syns (B1).

        1. tab_manager.add_tab("settings") om den finns
        2. app.add_tab() -> ttk.Notebook + Visa-menyn
        3. Sista utväg: Frame i main_frame (aldrig tyst fail)
        """
        title = "Inställningar"
        tab_manager = app.context.get("_tab_manager")
        parent = None
        if tab_manager and hasattr(tab_manager, "add_tab"):
            try:
                parent = tab_manager.add_tab("settings", title)
            except Exception as exc:
                self.log("FEL", "tab_manager.add_tab misslyckades: %s" % exc)
                parent = None
        if parent:
            return parent

        # Fallback: huvud-notebook + Visa-menyn
        try:
            parent = tk.Frame(app.notebook, bg=self._bg)
            if hasattr(app, "add_tab"):
                app.add_tab(title, parent)
                self.log("INFO", "Inställningar via notebook (tab_manager saknades)")
                return parent
        except Exception as exc:
            self.log("FEL", "app.add_tab misslyckades: %s" % exc)
            parent = None

        parent = tk.Frame(app.main_frame, bg=self._bg)
        parent.pack(fill=tk.BOTH, expand=True)
        self.log("VARNING", "Inställningar i huvudyta (ingen flikhanterare)")
        return parent

    def _show_settings_tab(self) -> None:
        """Visa inställningsfliken (B2). Kraschar aldrig."""
        try:
            tm = self.app.context.get("_tab_manager")
            if tm and hasattr(tm, "select_tab"):
                tm.select_tab("settings")
                return
        except Exception:
            pass
        try:
            frame = None
            tm = self.app.context.get("_tab_manager")
            if tm:
                frame = tm.tab_frames.get("settings")
            if frame is None:
                frame = self.app.tab_frames.get("Inställningar")
            if frame is not None and hasattr(self.app, "notebook"):
                self.app.notebook.select(frame)
        except Exception:
            pass

    def _install_settings_menu(self) -> None:
        """Arkiv → Inställningar + Ctrl+, (B3)."""
        try:
            menu = getattr(self.app, "arkiv_menu", None)
            if menu is None:
                return
            # Undvik dubblett vid reload (sök på label)
            try:
                end = menu.index("end")
            except tk.TclError:
                end = None
            if end is not None:
                for i in range(int(end) + 1):
                    try:
                        if menu.entrycget(i, "label") == "⚙ Inställningar":
                            return
                    except tk.TclError:
                        continue
            menu.insert_command(
                0,
                label="⚙ Inställningar",
                command=self._show_settings_tab,
                accelerator="Ctrl+,",
            )
            menu.insert_separator(1)
        except Exception:
            pass
        try:
            self.app.bind_all("<Control-comma>",
                              lambda e: self._show_settings_tab())
        except Exception:
            pass

    # ==========================================================================
    # SCROLL-CONTAINER
    # ==========================================================================

    def _build_scroll_container(self, parent):
        """
        Skapa canvas + scrollbar.

        REGLER:
          - INGEN bind_all (stor andra flikars scrollning)
          - Mushjul via canvas Enter/Leave (lokalt)
          - tk.Frame wrapper (inte ttk.Frame) -> ingen gra bakgrund
          - Canvas bg = self._bg (matchar fonster)

        Returnerar: (canvas, inner_frame)
        """
        bg = self._bg

        # Wrapper = tk.Frame (inte ttk.Frame)
        wrapper = tk.Frame(parent, bg=bg)
        wrapper.pack(fill=tk.BOTH, expand=True)
        self.wrapper = wrapper
        self._reg_panels(wrapper)

        canvas = tk.Canvas(
            wrapper,
            bg=bg,
            highlightthickness=0,
            borderwidth=0,
        )
        scrollbar = ttk.Scrollbar(
            wrapper, orient=tk.VERTICAL, command=canvas.yview
        )

        # Inner frame = tk.Frame (matchar canvas bakgrund)
        container = tk.Frame(canvas, bg=bg)
        self._reg_panels(container)
        container.bind(
            "<Configure>",
            lambda e: canvas.configure(
                scrollregion=canvas.bbox("all")
            ),
        )
        # Z4: kanna av bredden -> NORMALT/KOMPAKT lage
        container.bind("<Configure>", self._on_container_configure,
                       add="+")

        canvas_window = canvas.create_window(
            (0, 0), window=container, anchor=tk.NW
        )

        def _on_canvas_resize(event):
            canvas.itemconfig(canvas_window, width=event.width)

        canvas.bind("<Configure>", _on_canvas_resize)
        canvas.configure(yscrollcommand=scrollbar.set)

        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # -- Mushjul - LOKALT via Enter/Leave ------------------
        def _scroll(units):
            try:
                canvas.yview_scroll(units, "units")
            except tk.TclError:
                pass

        def _on_wheel(event):
            if sys.platform == "win32":
                _scroll(-3 if event.delta > 0 else 3)
            elif sys.platform == "darwin":
                _scroll(-1 if event.delta > 0 else 1)

        def _on_enter(event):
            canvas.bind("<MouseWheel>", _on_wheel)
            canvas.bind("<Button-4>", lambda e: _scroll(-3))
            canvas.bind("<Button-5>", lambda e: _scroll(3))

        def _on_leave(event):
            canvas.unbind("<MouseWheel>")
            canvas.unbind("<Button-4>")
            canvas.unbind("<Button-5>")

        canvas.bind("<Enter>", _on_enter)
        canvas.bind("<Leave>", _on_leave)

        self._settings_canvas = canvas
        return canvas, container

    # ==========================================================================
    # UI-SEKTIONER
    # ==========================================================================

    def create_folder_section(self) -> None:
        """Bildmapp och output-mapp."""
        bg    = self._bg
        frame = self._mk_section(self.container, "Mappar", pady=(10, 5))

        # Bildmapp
        self._mk_label(frame, "Bildmapp:").grid(
            row=0, column=0, sticky=tk.W, pady=8
        )

        folder_row = tk.Frame(frame, bg=bg)
        folder_row.grid(row=0, column=1, sticky=tk.EW, padx=10)
        self._reg_panels(folder_row)

        self.folder_var = tk.StringVar()
        self.folder_var.trace_add("write", self.on_folder_changed)
        ttk.Entry(
            folder_row, textvariable=self.folder_var,
            width=self._scaled(50), font=self._font(),   # Z3
        ).pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(
            folder_row, text="Bladdra...",
            command=self.browse_folder, width=12
        ).pack(side=tk.LEFT, padx=(5, 0))
        ttk.Button(
            folder_row, text="Historik...",
            command=self.browse_generated_gallery, width=12
        ).pack(side=tk.LEFT, padx=(5, 0))

        # Output-mapp
        self._mk_label(frame, "Output-mapp:").grid(
            row=1, column=0, sticky=tk.W, pady=8
        )

        output_row = tk.Frame(frame, bg=bg)
        output_row.grid(row=1, column=1, sticky=tk.EW, padx=10)
        self._reg_panels(output_row)

        self.output_var = tk.StringVar(value="(Valj bildmapp forst)")
        out_lbl = self._mk_label(
            output_row, "", "COLOR_MUTED",
            textvariable=self.output_var,
            font=self._font("italic"),                   # Z3
            pack={"side": tk.LEFT, "fill": tk.X, "expand": True},
        )
        self._set_output_label(out_lbl)                  # Z4 wraplength
        ttk.Button(
            output_row, text="Oppna",
            command=self.open_output_folder, width=12
        ).pack(side=tk.LEFT, padx=(5, 0))

        # Info
        self._mk_label(
            frame,
            "Output: out/[mappnamn]/  ·  Historik... importerar ett genererat galleri",
            "COLOR_MUTED",
            font=self._font(),
        ).grid(row=2, column=0, columnspan=2, sticky=tk.W, pady=(5, 0))

        frame.columnconfigure(1, weight=1)

    def create_gallery_section(self) -> None:
        """Titel, beskrivning, tema (3 st), kolumner."""
        bg    = self._bg
        frame = self._mk_section(self.container, "Galleri")

        # Titel
        self._mk_label(frame, "Titel:").grid(
            row=0, column=0, sticky=tk.W, pady=8
        )

        self.title_var = tk.StringVar(value="Mitt Bildgalleri")
        ttk.Entry(
            frame, textvariable=self.title_var,
            width=self._scaled(50), font=self._font(),   # Z3
        ).grid(row=0, column=1, columnspan=2, sticky=tk.EW, padx=10, pady=8)

        # Beskrivning
        self._mk_label(frame, "Beskrivning:").grid(
            row=1, column=0, sticky=tk.W, pady=8
        )

        self.desc_var = tk.StringVar(value="")
        ttk.Entry(
            frame, textvariable=self.desc_var,
            width=self._scaled(50), font=self._font(),   # Z3
        ).grid(row=1, column=1, columnspan=2, sticky=tk.EW, padx=10, pady=8)

        # Fargtema – EXAKT 3 alternativ (C1/14)
        self._mk_label(frame, "Fargtema:").grid(
            row=2, column=0, sticky=tk.W, pady=8
        )

        self.theme_var = tk.StringVar(value="system")
        theme_row = tk.Frame(frame, bg=bg)
        theme_row.grid(row=2, column=1, sticky=tk.W, padx=10, pady=8)
        self._reg_panels(theme_row)
        for label, value in [
            ("Morkt",   "dark"),
            ("Ljust",   "light"),
            ("System",  "system"),
        ]:
            ttk.Radiobutton(
                theme_row, text=label,
                value=value, variable=self.theme_var,
            ).pack(side=tk.LEFT, padx=(0, 15))

        # Kolumner
        self._mk_label(frame, "Kolumner:").grid(
            row=3, column=0, sticky=tk.W, pady=8
        )

        self.layout_options = {}
        self.cols_var = tk.IntVar(value=6)
        cols_row = tk.Frame(frame, bg=bg)
        cols_row.grid(row=3, column=1, sticky=tk.W, padx=10, pady=8)
        self._reg_panels(cols_row)
        ttk.Spinbox(
            cols_row, from_=2, to=12,
            textvariable=self.cols_var, width=5,
        ).pack(side=tk.LEFT)
        self._mk_label(
            cols_row, "kolumner", "COLOR_MUTED",
            pack={"side": tk.LEFT, "padx": 5},
        )

        from layout_designer import open_designer
        ttk.Button(frame, text='Visuell layout och liveförhandsvisning…',
                   command=lambda: open_designer(self.app, self)).grid(
                       row=4, column=0, columnspan=3, sticky='ew', padx=10, pady=8)
        frame.columnconfigure(1, weight=1)

    def create_image_section(self) -> None:
        """Thumbnail, kvalitet, EXIF."""
        bg    = self._bg
        frame = self._mk_section(self.container, "Bildinstallningar")

        # Miniatyr
        self._mk_label(frame, "Miniatyr:").grid(
            row=0, column=0, sticky=tk.W, pady=8
        )

        self.thumb_size_var = tk.StringVar(value="300x300")
        ttk.Combobox(
            frame, textvariable=self.thumb_size_var,
            values=["150x150", "200x200", "250x250",
                    "300x300", "400x400"],
            width=self._scaled(12), state="readonly", font=self._font(),
        ).grid(row=0, column=1, sticky=tk.W, padx=10, pady=8)

        # Max storlek
        self._mk_label(frame, "Max storlek:").grid(
            row=1, column=0, sticky=tk.W, pady=8
        )

        self.fullsize_var = tk.StringVar(value="1920x1080")
        ttk.Combobox(
            frame, textvariable=self.fullsize_var,
            values=["1280x720", "1600x900", "1920x1080",
                    "2560x1440", "Original"],
            width=self._scaled(12), state="readonly", font=self._font(),
        ).grid(row=1, column=1, sticky=tk.W, padx=10, pady=8)

        # JPEG-kvalitet
        self._mk_label(frame, "JPEG-kvalitet:").grid(
            row=2, column=0, sticky=tk.W, pady=8
        )

        q_row = tk.Frame(frame, bg=bg)
        q_row.grid(row=2, column=1, columnspan=2,
                   sticky=tk.EW, padx=10, pady=8)
        self._reg_panels(q_row)

        self.quality_var = tk.IntVar(value=85)
        self._quality_scale = ttk.Scale(
            q_row, from_=50, to=100,
            orient=tk.HORIZONTAL, variable=self.quality_var,
            length=self._scaled(200),                    # Z3, Z4 justerar
            command=self.update_quality_label,
        )
        self._quality_scale.pack(side=tk.LEFT)
        self.quality_label = self._mk_label(
            q_row, "85%", width=self._scaled(5),
            pack={"side": tk.LEFT, "padx": 10},
        )
        self._mk_label(
            q_row, "(50=liten fil, 100=bast)", "COLOR_MUTED",
            font=self._font(), pack={"side": tk.LEFT},
        )

        # EXIF
        self._mk_label(frame, "Metadata:").grid(
            row=3, column=0, sticky=tk.W, pady=8
        )

        self.preserve_exif_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            frame, text="Bevara EXIF-data",
            variable=self.preserve_exif_var,
        ).grid(row=3, column=1, sticky=tk.W, padx=10, pady=8)

        self.auto_rotate_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            frame, text="Auto-rotera (EXIF)",
            variable=self.auto_rotate_var,
        ).grid(row=4, column=1, sticky=tk.W, padx=10, pady=8)

        from .web_image_assets import create_controls
        web_options = ttk.Frame(frame)
        web_options.grid(row=5, column=0, columnspan=3, sticky=tk.EW, pady=8)
        self.responsive_images_var, self.download_mode_var = create_controls(web_options, {})
        from .gallery_checks import create_cover_controls
        self.cover_image_var, self.public_url_var = create_cover_controls(web_options, {})
        from .logo_watermark import create_controls as watermark_controls
        self.watermark_enabled_var, self.watermark_logo_var, self.watermark_opacity_var = watermark_controls(web_options)
        ttk.Button(web_options, text='Öppna länkkontroll',
                   command=self.open_link_report).pack(anchor='w', pady=4)
        ttk.Button(web_options, text='Öppna bildoptimeringsrapport',
                   command=self.open_optimization_report).pack(anchor='w', pady=4)

        frame.columnconfigure(1, weight=1)

    def open_link_report(self):
        from .gallery_checks import open_link_report
        open_link_report(self.app, self.app.context.get('link_report_path'))

    def open_optimization_report(self):
        from .web_image_assets import open_report
        open_report(self.app, self.app.context.get('optimization_report_path'))

    def create_ftp_section(self) -> None:
        """FTP-konfiguration. Losenord sparas ALDRIG."""
        bg    = self._bg
        frame = self._mk_section(self.container, "FTP (valfritt)")

        self.ftp_enabled_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            frame, text="Aktivera FTP-uppladdning",
            variable=self.ftp_enabled_var,
            command=self.toggle_ftp_fields,
        ).grid(row=0, column=0, columnspan=2, sticky=tk.W, pady=8)

        self.ftp_fields_frame = tk.Frame(frame, bg=bg)
        self.ftp_fields_frame.grid(
            row=1, column=0, columnspan=3, sticky=tk.EW
        )
        self._reg_panels(self.ftp_fields_frame)

        ftp_rows = [
            ("Server:",    "ftp_server_var", "",                     False),
            ("Anvandare:", "ftp_user_var",   "",                     False),
            ("Losenord:",  "ftp_pass_var",   "",                     True),
            ("Sokvag:",    "ftp_path_var",   "/public_html/gallery", False),
        ]
        for i, (label, attr, default, is_pw) in enumerate(ftp_rows):
            self._mk_label(
                self.ftp_fields_frame, label
            ).grid(row=i, column=0, sticky=tk.W, pady=5)

            var = tk.StringVar(value=default)
            setattr(self, attr, var)

            kw = {"textvariable": var, "width": self._scaled(40),
                  "font": self._font()}                  # Z3
            if is_pw:
                kw["show"] = "*"
            ttk.Entry(self.ftp_fields_frame, **kw).grid(
                row=i, column=1, sticky=tk.EW, padx=10, pady=5
            )

        self.ftp_fields_frame.columnconfigure(1, weight=1)

        self._mk_label(
            self.ftp_fields_frame,
            "Losenord sparas inte till disk",
            "COLOR_MUTED",
            font=self._font(),
        ).grid(
            row=len(ftp_rows), column=0, columnspan=2,
            sticky=tk.W, pady=(5, 0)
        )

        frame.columnconfigure(1, weight=1)
        self.toggle_ftp_fields()

    def create_buttons(self) -> None:
        """Knappraden langst ner."""
        bg    = self._bg
        frame = tk.Frame(self.container, bg=bg)
        frame.pack(fill=tk.X, padx=10, pady=20)
        self._reg_panels(frame)

        left = tk.Frame(frame, bg=bg)
        left.pack(side=tk.LEFT)
        self._reg_panels(left)
        for text, cmd in (("Spara", self.save_settings),
                          ("Aterstall", self.reset_defaults)):
            b = ttk.Button(left, text=text, command=cmd,
                           width=self._scaled(16))
            b.pack(side=tk.LEFT, padx=5)
            self.register_button(b)                      # Z5 tema-restyle

        right = tk.Frame(frame, bg=bg)
        right.pack(side=tk.RIGHT)
        self._reg_panels(right)
        b = ttk.Button(right, text="Sortera...", command=self.open_sorter,
                       width=self._scaled(14))
        b.pack(side=tk.LEFT, padx=5)
        self.register_button(b)
        b = ttk.Button(
            right, text="Generera", command=self.run_generate,
            width=self._scaled(14), style="Accent.TButton",
        )
        b.pack(side=tk.LEFT, padx=5)

    # ==========================================================================
    # EVENTS
    # ==========================================================================

    def on_folder_changed(self, *args) -> None:
        """
        Uppdatera output-label och auto-titel vid mappbyte.

        Output/titel uppdateras OMEDELBART (cheap); den dyra
        bildrakningen debounce-as sa att varje tangenttryck ger
        max en katalog-skanning (Q3, snabbhet).
        """
        folder = self.folder_var.get()
        if folder and Path(folder).exists():
            name   = Path(folder).name
            output = self.get_output_path()
            if output:
                self.output_var.set(str(output))
            else:
                self.output_var.set(
                    str(Path(__file__).parent.parent / "out" / name)
                )

            if not getattr(self, "_suppress_auto_title", False):
                self.title_var.set(name)

            # Debounce av dyr skanning (schema pa app-rotens eventloop)
            after = getattr(self, "_count_after", None)
            if after is not None:
                try:
                    self.app.after_cancel(after)
                except Exception:
                    pass
            self._count_after = self.app.after(
                180,
                lambda f=folder, n=name: self._log_folder_count(f, n),
            )
        else:
            self.output_var.set("(Valj bildmapp forst)")

    def _log_folder_count(self, folder: str, name: str) -> None:
        """Rakna bilder och logga (anropas debounce-ad)."""
        self._count_after = None
        try:
            n = sum(
                1 for f in Path(folder).iterdir()
                if f.is_file()
                and f.suffix.lower() in self.IMAGE_FORMATS
            )
            self.log("INFO", "Mapp: %s (%d bilder)" % (name, n))
        except Exception:
            pass

    def browse_folder(self) -> None:
        """Oppna OS-filvaljare."""
        initial = self.folder_var.get()
        if not initial or not Path(initial).exists():
            initial = str(Path.home())

        folder = filedialog.askdirectory(
            title="Valj mapp med bilder", initialdir=initial
        )
        if not folder:
            return

        self._output_override = ""
        self.folder_var.set(folder)

        mm = self.app.context.get("_menu_manager")
        if mm and hasattr(mm, "add_recent_folder"):
            mm.add_recent_folder(folder)

    def open_output_folder(self) -> None:
        """Oppna output i OS-filhanterare (Popen - blockerar ej)."""
        output = self.get_output_path()
        if output and output.exists():
            try:
                if sys.platform == "win32":
                    subprocess.Popen(["explorer", str(output)])
                elif sys.platform == "darwin":
                    subprocess.Popen(["open", str(output)])
                else:
                    subprocess.Popen(["xdg-open", str(output)])
            except Exception as e:
                messagebox.showerror("Fel", str(e))
        else:
            messagebox.showinfo(
                "Info",
                "Output-mappen finns inte annu.\n"
                "Den skapas vid generering."
            )

    def toggle_ftp_fields(self) -> None:
        """Visa/dolj FTP-falt."""
        if self.ftp_enabled_var.get():
            self.ftp_fields_frame.grid()
        else:
            self.ftp_fields_frame.grid_remove()

    def update_quality_label(self, value=None) -> None:
        """Uppdatera %-label vid slider-andring."""
        try:
            self.quality_label.config(
                text="%d%%" % self.quality_var.get()
            )
        except Exception:
            pass

    # ==========================================================================
    # SNABBKNAPPAR
    # ==========================================================================

    def open_sorter(self) -> None:
        """Oppna SorterWindow (image_sorter.py)."""
        folder = self.folder_var.get()
        if not folder or not Path(folder).exists():
            messagebox.showwarning("Varning", "Valj en bildmapp forst.")
            return

        images = sorted(
            f for f in Path(folder).iterdir()
            if f.is_file()
            and f.suffix.lower() in self.IMAGE_FORMATS
            and not f.name.startswith(".")
        )
        if not images:
            messagebox.showinfo("Info", "Inga bilder i mappen.")
            return

        try:
            from .image_sorter import SorterWindow
            sorter = SorterWindow(images)
            if sorter.result:
                self.app.context["sorted_images"] = sorter.result
                self.app.context["manual_sort"]   = True
                self.log(
                    "INFO",
                    "Sorterade %d bilder" % len(sorter.result)
                )
                messagebox.showinfo(
                    "Klart",
                    "%d bilder sorterade!" % len(sorter.result)
                )
        except ImportError as e:
            messagebox.showerror(
                "Fel", "Sortering ej tillganglig:\n%s" % e
            )
        except Exception as e:
            messagebox.showerror("Fel", str(e))

    def run_generate(self) -> None:
        """Snabbknapp for generering."""
        mm = self.app.context.get("_menu_manager")
        if mm and hasattr(mm, "run_generate"):
            mm.run_generate()
            return

        controls = self.app.context.get("_controls")
        if controls and hasattr(controls, "run_generate"):
            controls.run_generate()
            return

        try:
            self.validate_settings()
            self.app.run_pipeline()
            messagebox.showinfo("Klart", "Galleriet har genererats!")
        except ValueError as e:
            messagebox.showwarning("Ogiltiga installningar", str(e))
        except Exception as e:
            messagebox.showerror("Fel", str(e))

    # ==========================================================================
    # SPARA / LADDA / ATERSTALL
    # ==========================================================================

    def _collect_settings(self) -> dict:
        """
        Samla alla nuvarande installningar i ETT data-dict (Q2).

        Delas av save_settings() och cleanup() sa att de aldrig
        kan driva isar. FTP-losenord ingar ALDRIG.
        """
        from .web_image_assets import download_mode
        return {
            "watermark_enabled": self.watermark_enabled_var.get(),
            "watermark_logo": self.watermark_logo_var.get().strip(),
            "watermark_opacity": self.watermark_opacity_var.get(),
            "cover_image": self.cover_image_var.get(),
            "public_url": self.public_url_var.get().strip(),
            "responsive_images": self.responsive_images_var.get(),
            "download_mode": download_mode(self.download_mode_var.get()),
            "folder":         self.folder_var.get(),
            "title":          self.title_var.get(),
            "description":    self.desc_var.get(),
            "theme":          self.theme_var.get(),
            "columns":        self.cols_var.get(),
            "layout":         dict(getattr(self, 'layout_options', {})),
            "thumbnail_size": self.thumb_size_var.get(),
            "fullsize_max":   self.fullsize_var.get(),
            "quality":        self.quality_var.get(),
            "preserve_exif":  self.preserve_exif_var.get(),
            "auto_rotate":    self.auto_rotate_var.get(),
            "ftp": {
                "enabled": self.ftp_enabled_var.get(),
                "server":  self.ftp_server_var.get(),
                "user":    self.ftp_user_var.get(),
                # password sparas ALDRIG
                "path":    self.ftp_path_var.get(),
            },
        }

    def has_unsaved_changes(self):
        return (self._collect_settings() != getattr(self, '_saved_settings_snapshot', None)
                or bool(self.ftp_pass_var.get()))

    def save_settings(self) -> None:
        """Spara till config/settings.json. Losenord sparas ALDRIG."""
        folder = self.folder_var.get()
        if folder and not Path(folder).exists():          # Z5
            messagebox.showwarning(
                "Varning",
                "Bildmappen finns inte langre:\n%s\n\n"
                "Installningarna sparas anda." % folder,
            )
        data = self._collect_settings()
        if self.save_config("settings.json", data):
            self._saved_settings_snapshot = data
            self.log("OK", "Installningar sparade")
            messagebox.showinfo("Sparat", "Installningarna har sparats!")
        else:
            messagebox.showerror(
                "Fel", "Kunde inte spara installningar."
            )

    def load_settings(self) -> None:
        """
        Ladda config/settings.json.
        Tyst om filen saknas.
        Kontrollerar att bildmapp fortfarande finns.
        Legacy-tema (colorful/clam/auto) migreras till system (C1).
        """
        s = self.load_config("settings.json", default={})
        if not s:
            return

        folder = s.get("folder", "")
        if folder and Path(folder).exists():
            self.folder_var.set(folder)

        # C1: exakt 3 teman - migrera legacy-varden
        theme = s.get("theme", "system")
        if theme not in ("dark", "light", "system"):
            theme = "system"

        self.title_var.set(
            s.get("title",          "Mitt Bildgalleri")
        )
        self.desc_var.set(s.get("description",     ""))
        self.theme_var.set(theme)
        self.cols_var.set(s.get("columns",          6))
        from layout_designer import options as layout_options
        self.layout_options = layout_options(s.get('layout'))
        self.thumb_size_var.set(
            s.get("thumbnail_size", "300x300")
        )
        self.fullsize_var.set(s.get("fullsize_max", "1920x1080"))
        self.quality_var.set(s.get("quality",       85))
        self.preserve_exif_var.set(s.get("preserve_exif", False))
        self.auto_rotate_var.set(s.get("auto_rotate",     True))
        from .web_image_assets import export_options, DOWNLOAD_LABELS
        options = export_options(s)
        self.watermark_enabled_var.set(s.get('watermark_enabled') is True)
        self.watermark_logo_var.set(s.get('watermark_logo') or '')
        self.watermark_opacity_var.set(s.get('watermark_opacity', 70))
        self.cover_image_var.set(str(s.get('cover_image', 1)))
        self.public_url_var.set(s.get('public_url') or '')
        self.responsive_images_var.set(options['responsive_images'])
        self.download_mode_var.set(DOWNLOAD_LABELS[options['download_mode']])

        ftp = s.get("ftp", {})
        self.ftp_enabled_var.set(ftp.get("enabled", False))
        self.ftp_server_var.set(ftp.get("server",   ""))
        self.ftp_user_var.set(ftp.get("user",       ""))
        self.ftp_path_var.set(
            ftp.get("path",  "/public_html/gallery")
        )
        # ftp_pass_var laddas ALDRIG

        self.toggle_ftp_fields()
        self.update_quality_label()
        self._saved_settings_snapshot = self._collect_settings()
        self.log("INFO", "Installningar laddade")

    def reset_defaults(self) -> None:
        """Aterstall till fabriksvarden."""
        if not messagebox.askyesno(
            "Bekrafta", "Aterstalla alla installningar?"
        ):
            return

        self.title_var.set("Mitt Bildgalleri")
        self.desc_var.set("")
        self.theme_var.set("system")
        self.cols_var.set(4)
        from layout_designer import options as layout_options
        self.layout_options = layout_options()
        self.thumb_size_var.set("300x300")
        self.fullsize_var.set("1920x1080")
        self.quality_var.set(85)
        self.preserve_exif_var.set(False)
        self.auto_rotate_var.set(True)
        from .web_image_assets import DOWNLOAD_LABELS
        self.watermark_enabled_var.set(False)
        self.watermark_logo_var.set('')
        self.watermark_opacity_var.set(70)
        self.cover_image_var.set('1')
        self.public_url_var.set('')
        self.responsive_images_var.set(True)
        self.download_mode_var.set(DOWNLOAD_LABELS['off'])
        self.ftp_enabled_var.set(False)
        self.ftp_server_var.set("")
        self.ftp_user_var.set("")
        self.ftp_pass_var.set("")
        self.ftp_path_var.set("/public_html/gallery")
        self.toggle_ftp_fields()
        self.update_quality_label()
        self.log("INFO", "Standardvarden aterstallda")

    # ==========================================================================
    # HJALPMETODER
    # ==========================================================================

    def get_output_path(self):
        """Berakna output-sokvag: [program]/out/[mappnamn]/"""
        folder = self.folder_var.get()
        if folder and Path(folder).exists():
            return (
                Path(__file__).parent.parent / "out" / Path(folder).name
            )
        return None

    def validate_settings(self) -> bool:
        """
        Validera installningar.
        Kastar ValueError vid problem.
        Returnerar True om OK.
        """
        folder = self.folder_var.get()
        if not folder:
            raise ValueError("Ingen bildmapp vald.")

        p = Path(folder)
        if not p.exists():
            raise ValueError("Mappen finns inte:\n%s" % folder)

        imgs = [
            f for f in p.iterdir()
            if f.is_file() and f.suffix.lower() in self.IMAGE_FORMATS
        ]
        media = [f for f in p.iterdir() if f.is_file() and
                 f.suffix.lower() in (self.VIDEO_FORMATS | {'.pdf'})]
        if not imgs and not media:
            raise ValueError("Inga bilder, videor eller PDF-filer i mappen:\n%s" % folder)
        return True

    def _get_bg(self) -> str:
        """Hamta bakgrundsfarg fran temat (om tillgangligt)."""
        try:
            if hasattr(self, "app") and self.app:
                te = getattr(self.app, "theme_engine", None)
                if te and hasattr(te, "get_color"):
                    return te.get_color("bg", self.COLOR_BG)
        except Exception:
            pass
        return self.COLOR_BG

    # ==========================================================================
    # PIPELINE
    # ==========================================================================

    def execute(self, context: dict, log=None) -> dict:
        """
        Fyll context['gallery'] med installningar.
        Skannar och kopierar PDF- och videofiler till exportmappen
        (doper om dem till pdf1, pdf2 / video1, video2...).
        Returnerar context oforandrad om validate_settings() misslyckas.
        """
        try:
            self.validate_settings()
        except ValueError as e:
            if log:
                log("  [!] Installningar ogiltiga: %s" % e)
            raise ValueError('Kan inte generera galleri: %s' % e) from e

        try:
            tw, th     = self.thumb_size_var.get().split("x")
            thumb_size = (int(tw), int(th))
        except Exception:
            thumb_size = (300, 300)

        fs = self.fullsize_var.get()
        if fs == "Original":
            fullsize_max = None
        else:
            try:
                fw, fh       = fs.split("x")
                fullsize_max = (int(fw), int(fh))
            except Exception:
                fullsize_max = (1920, 1080)

        output = self.get_output_path()
        if output and context.get('_transactional_export'):
            from export_transaction import ExportTransaction
            transaction = ExportTransaction(output)
            context['_export_transaction'] = transaction
            output = transaction.stage

        # -- EXPORT AV PDF & VIDEOFILER --
        pdf_list = []
        video_list = []
        folder = self.folder_var.get()
        if folder and Path(folder).exists() and output:
            output_path = Path(output)
            output_path.mkdir(parents=True, exist_ok=True)

            # Sortera for att garantera konsekvent ordning pdf1, pdf2...
            all_files = sorted(
                Path(folder).iterdir(), key=lambda x: x.name.lower()
            )

            pdf_idx = 1
            video_idx = 1
            for f in all_files:
                if f.is_file() and not f.name.startswith("."):
                    ext = f.suffix.lower()
                    if ext == ".pdf":
                        new_name = "pdf%d%s" % (pdf_idx, ext)
                        dest = output_path / new_name
                        try:
                            # Kopiera endast om filen andrats eller inte finns
                            if (not dest.exists()
                                    or dest.stat().st_mtime < f.stat().st_mtime):
                                shutil.copy2(f, dest)
                            pdf_list.append({
                                "original_name": f.name,
                                "name": "pdf%d" % pdf_idx,  # Dops till pdf1, pdf2 osv
                                "filename": new_name,
                                "relative_path": new_name
                            })
                            pdf_idx += 1
                        except Exception as e:
                            self.log_error(
                                "Kunde inte kopiera PDF-fil %s" % f.name, e
                            )

                    elif ext in self.VIDEO_FORMATS:
                        new_name = "video%d%s" % (video_idx, ext)
                        # Skapa video-undermapp
                        video_dir = output_path / "video"
                        video_dir.mkdir(exist_ok=True)
                        dest = video_dir / new_name
                        try:
                            # Kopiera endast om filen andrats eller inte finns
                            if (not dest.exists()
                                    or dest.stat().st_mtime < f.stat().st_mtime):
                                shutil.copy2(f, dest)
                            video_list.append({
                                "original_name": f.name,
                                "name": "video%d" % video_idx,  # Dops till video1, video2
                                "filename": new_name,
                                "relative_path": "video/%s" % new_name
                            })
                            video_idx += 1
                        except Exception as e:
                            self.log_error(
                                "Kunde inte kopiera videofil %s" % f.name, e
                            )

            # G3: genererat galleri har videor i output/video, inte i image/
            if getattr(self, "_output_override", "") and not video_list:
                vdir = output_path / "video"
                extra = []
                try:
                    if vdir.is_dir():
                        extra = [
                            f for f in vdir.iterdir()
                            if f.is_file()
                            and f.suffix.lower() in self.VIDEO_FORMATS
                            and not f.name.startswith(".")
                        ]
                except Exception:
                    extra = []
                extra.sort(key=lambda p: [
                    int(t) if t.isdigit() else t.lower()
                    for t in re.split(r"(\d+)", p.name)
                ])
                for f in extra:
                    ext = f.suffix.lower()
                    new_name = "video%d%s" % (video_idx, ext)
                    dest = vdir / new_name
                    try:
                        if f.resolve() != dest.resolve():
                            if (not dest.exists()
                                    or dest.stat().st_mtime < f.stat().st_mtime):
                                shutil.copy2(f, dest)
                        video_list.append({
                            "original_name": f.name,
                            "name": "video%d" % video_idx,
                            "filename": new_name,
                            "relative_path": "video/%s" % new_name,
                        })
                        video_idx += 1
                    except Exception as e:
                        self.log_error(
                            "Kunde inte kopiera videofil %s" % f.name, e
                        )
            if getattr(self, "_output_override", "") and not pdf_list:
                pdir = output_path / "pdf"
                extra_pdf = []
                try:
                    scan = []
                    if pdir.is_dir():
                        scan.extend(pdir.iterdir())
                    scan.extend(output_path.iterdir())
                    extra_pdf = [
                        f for f in scan
                        if f.is_file()
                        and f.suffix.lower() == ".pdf"
                        and not f.name.startswith(".")
                    ]
                except Exception:
                    extra_pdf = []
                seen = set()
                for f in extra_pdf:
                    rp = str(f)
                    if rp in seen:
                        continue
                    seen.add(rp)
                    ext = f.suffix.lower() or ".pdf"
                    new_name = "pdf%d%s" % (pdf_idx, ext)
                    dest = output_path / new_name
                    try:
                        if f.resolve() != dest.resolve():
                            if (not dest.exists()
                                    or dest.stat().st_mtime < f.stat().st_mtime):
                                shutil.copy2(f, dest)
                        pdf_list.append({
                            "original_name": f.name,
                            "name": "pdf%d" % pdf_idx,
                            "filename": new_name,
                            "relative_path": new_name,
                        })
                        pdf_idx += 1
                    except Exception as e:
                        self.log_error(
                            "Kunde inte kopiera PDF-fil %s" % f.name, e
                        )

        context["pdf_files"] = pdf_list
        context["video_files"] = video_list

        # Registrera for FTP-uppladdning om FTP ar aktiverat
        if self.ftp_enabled_var.get() and "files_to_upload" in context:
            for item in pdf_list:
                if item["relative_path"] not in context["files_to_upload"]:
                    context["files_to_upload"].append(item["relative_path"])
            for item in video_list:
                if item["relative_path"] not in context["files_to_upload"]:
                    context["files_to_upload"].append(item["relative_path"])

        from .web_image_assets import download_mode
        context["gallery"] = {
            "watermark_enabled": self.watermark_enabled_var.get(),
            "watermark_logo": self.watermark_logo_var.get().strip(),
            "watermark_opacity": self.watermark_opacity_var.get(),
            "cover_image": self.cover_image_var.get(),
            "public_url": self.public_url_var.get().strip(),
            "responsive_images": self.responsive_images_var.get(),
            "download_mode": download_mode(self.download_mode_var.get()),
            "title":          self.title_var.get(),
            "description":    self.desc_var.get(),
            "theme":          self.theme_var.get(),
            "images_path":    self.folder_var.get(),
            "output_path":    str(output) if output else "",
            "thumbnail_size": thumb_size,
            "fullsize_max":   fullsize_max,
            "jpeg_quality":   self.quality_var.get(),
            "columns":        self.cols_var.get(),
            "layout":         dict(getattr(self, 'layout_options', {})),
            "preserve_exif":  self.preserve_exif_var.get(),
            "auto_rotate":    self.auto_rotate_var.get(),
        }

        if self.ftp_enabled_var.get():
            context["ftp_settings"] = {
                "server":   self.ftp_server_var.get(),
                "user":     self.ftp_user_var.get(),
                "password": self.ftp_pass_var.get(),
                "path":     self.ftp_path_var.get(),
            }
            context["ftp_enabled"] = True

        if log:
            log("  Mapp:      %s" % self.folder_var.get())
            log("  Output:    %s" % output)
            log("  Kvalitet:  %d%%" % self.quality_var.get())
            if pdf_list:
                log(
                    "  PDF:er:    Inkluderade och kopierade (%d st)"
                    % len(pdf_list)
                )
            if video_list:
                log(
                    "  Videofiler: Inkluderade och kopierade (%d st)"
                    % len(video_list)
                )

        return context

    def cleanup(self) -> None:
        """Spara installningar vid avslutning."""
        try:
            self.save_config("settings.json", self._collect_settings())
        except Exception:
            pass
        super().cleanup()

    # OBS (Z2): log/log_error/load_config/save_config/widget_exists arvs
    # fran base_plugin v1.4.1 - atomisk sjalvlakande config (.bak +
    # korrupt-karantan), traceback i log_error, skuggningsvakt i log().
    # Egen duplicationering borttagen; beteendet ar battre an forr.

