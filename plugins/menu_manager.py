#!/usr/bin/env python3
# ============================================================
# Gallery Uploader - Menyhanterare
# ============================================================
# FIL:       plugins/menu_manager.py
# PLATS:     plugins/ (ftp_gallery_uploader/plugins/menu_manager.py)
# Klass:     MenuManager(BasePlugin)
# PRIORITY:  2
# VERSION:   2.6.1
# AUTHOR:    Rickard Längkvist
# COPYRIGHT: Copyright (c) <år> Rickard Längkvist (dynamiskt år,
#            se COPYRIGHT-konstanten nedan)
#
# ÄNDRINGAR v2.5.0 → v2.6.0 (öppna genererat galleri):
#   [G1]      Arkiv: Oppna genererat galleri... (Ctrl+Shift+G),
#             Lagg till bilder..., Lagg till videor...
#
# ÄNDRINGAR v2.4.0 → v2.5.0 (omladdning + textfält + snabbhet):
#   [Z8]      Idempotent menyrad vid plugin-reload. [Z9] bind add="+".
#   [Z10]     Genvagar hoppar over Entry. [Z11] senaste-mappar skip.
#
# ÄNDRINGAR v2.3.0 → v2.4.0 (text/fönster + minne + snabbhet):
#   [Z1]      register_theme_callback ärvs från base_plugin (delad
#             dispatcher). v2.3.0:s app.bind() stal temat från andra.
#   [Z2]      log/log_error/load_config/save_config ärvs (självläkande
#             config + traceback). ~90 rader dubblett bort.
#   [Z3]      Anpassad text: DPI via suggest_font_size (samma motor som
#             Loggvisaren/Inställningar). Dialoger, labels, kortkommandon
#             skalar 96 DPI -> 9 pt ... 192 DPI -> 12 pt.
#   [Z4]      Anpassat fönster: dialoger klammas till skärmen (fit_window),
#             centreras över huvudfönstret, Escape stänger. KOMPAKT läge
#             när skärmen är smal (<640 px) - kortare slider, mindre pad.
#   [Z5]      Minne: döda dialog-widgets rensas ur _panels/_labels vid
#             stängning och tema-byte (ingen obegränsad lista).
#   [Z6]      Snabbhet: Senaste-mappar ritas om via after_idle (en gång
#             per burst). Plugins-menyn byggs om bara när listan ändrats.
#   [Z7]      Enkelhet: _open_dialog/_close_dialog/_list_images. Ctrl+G
#             (generera) + Ctrl+R/F5 (ladda om) som kortkommandona sade.
#             Senaste mappar visar mappnamn först.
#
# ÄNDRINGAR v2.2.0 → v2.3.0 (DESIGN-SYSTEM-integration, spec v4.6.0):
#   [C1]      Farger från ThemeEngine via _THEME_KEYS + _load_theme_colors
#             / _restyle_all / on_theme_changed.
#   [C4]      Dialog-Toplevel bg=COLOR_BG. tk.Menyer stylas av ThemeEngine.
#
# BEVARAT:
#   Ingen print(), inga f-strings. Publik API oförändrad (select_folder,
#   set_folder, add_recent_folder, run_generate, add_menu_item, ...).
#   Emoji borttagna ur menyetiketter.
#
# ANSVARAR FOR:
#   - Menyraden: Arkiv / Redigera / Kor / Plugins / Hjalp
#   - Senaste mappar (config/recent_folders.json, max 10)
#   - Plugin-aktivering via checkboxar
#   - Tangentbordsgenvagar
#   - Generera / forhandsgranska
#   - Exportera/importera installningar
#
# CONTEXT SOM LASES:
#   '_tab_manager', '_gallery_view', '_settings', '_controls', '_logger'
#   'gallery', 'selected_folder', 'output_path'
# CONTEXT SOM SATTS:
#   '_menu_manager', 'selected_folder', 'sorted_images',
#   'gallery_order', 'manual_sort'
# ============================================================

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import subprocess
import sys
import json
from pathlib import Path
from datetime import datetime

from .base_plugin import BasePlugin

try:
    from .advanced_logger_guards import (
        clamp_font_size,
        suggest_font_size,
        fit_window,
        readable_width,
    )
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

    def fit_window(wanted_w, wanted_h, app=None, pad=80):
        return int(wanted_w), int(wanted_h), 80, 80

    def readable_width(app=None, chars=110, font_size=9):
        return int(chars * max(6, int(font_size) - 2))


class MenuManager(BasePlugin):
    """
    Hanterar hela menyraden for Gallery Uploader.

    Koordinerar med:
      - main.py      (Arkiv/Visa/Kor/Hjalp skapas dar)
      - tab_manager  (tabb-navigering)
      - ui_controls  (generering i bakgrundstrad)
      - gallery_view (bildmapp + image_files)

    PRIORITY=2 -> laddas efter tab_manager (-10) och
    advanced_logger (1), men fore gallery_view (10).

    v2.4.0:
    - Text/fonster foljer DPI och skarmstorlek
    - log/config/tema-dispatcher arvs fran base_plugin
    - Dialoger centreras, klammas, Escape stanger

    v2.3.0:
    - Fargerna foljer ThemeEngine och uppdateras vid tema-byte
    """

    PLUGIN_NAME = "Menyhanterare"
    PRIORITY    = 2
    VERSION     = "2.6.1"
    AUTHOR      = "Rickard Längkvist"
    COPYRIGHT   = "Copyright (c) %d %s" % (
        datetime.now().year, "Rickard Längkvist"
    )

    RECENT_FILE = "recent_folders.json"
    MAX_RECENT  = 10
    COMPACT_PX  = 640

    PROTECTED_PLUGINS = {
        "advanced_logger",
        "menu_manager",
        "tab_manager",
    }

    IMAGE_EXTS = {
        ".jpg", ".jpeg", ".png", ".gif",
        ".webp", ".bmp", ".tiff", ".tif",
    }

    COLOR_BG           = "#1e1e1e"
    COLOR_FG           = "#ffffff"
    COLOR_SHORTCUT_BG  = "#1e1e1e"
    COLOR_SHORTCUT_FG  = "#d4d4d4"

    _THEME_KEYS = {
        "COLOR_BG":          "bg",
        "COLOR_FG":          "fg",
        "COLOR_SHORTCUT_BG": "bg_secondary",
        "COLOR_SHORTCUT_FG": "fg",
    }

    # ==========================================================================
    # TEMA + TEXT + FONSTER
    # ==========================================================================

    def _ensure_theme_lists(self) -> None:
        """Initiera tema-omstylingslistor (defensivt)."""
        if not hasattr(self, "_panels"):
            self._panels = []
        if not hasattr(self, "_labels"):
            self._labels = []

    def _prune_theme_lists(self) -> None:
        """Släng döda dialog-widgets (Z5 minne)."""
        self._ensure_theme_lists()
        self._panels = [w for w in self._panels if self.widget_exists(w)]
        self._labels = [
            (w, a) for (w, a) in self._labels if self.widget_exists(w)
        ]
        if not self.widget_exists(getattr(self, "_shortcuts_text", None)):
            self._shortcuts_text = None

    def _reg_panels(self, *widgets) -> None:
        """Registrera ramar/Toplevel for tema-omstyling."""
        self._ensure_theme_lists()
        for w in widgets:
            if w is not None and w not in self._panels:
                self._panels.append(w)

    def _reg_labels(self, *pairs) -> None:
        """Registrera (widget, fg-attribut)-par for tema-omstyling."""
        self._ensure_theme_lists()
        self._labels.extend(pairs)

    def _ui_font(self, style=None, mono=False):
        """DPI-anpassad UI-font (Z3)."""
        size = int(getattr(self, "_base_font_size", 9) or 9)
        family = "Consolas" if mono else "Segoe UI"
        if style:
            return (family, size, style)
        return (family, size)

    def _scaled(self, value) -> int:
        """Skala px med DPI-faktor."""
        try:
            return int(round(float(value) * float(self._font_scale)))
        except Exception:
            return int(value)

    def _apply_text_adaptation(self) -> None:
        """Rakna ut teckenstorlek fran skarmens DPI (Z3)."""
        try:
            self._base_font_size = clamp_font_size(
                suggest_font_size(self.app)
            )
        except Exception:
            self._base_font_size = 9
        try:
            self._font_scale = round(self._base_font_size / 9.0, 3)
        except Exception:
            self._font_scale = 1.0

    def _is_compact_screen(self) -> bool:
        """True om huvudfonstret/skarmen ar smal (Z4)."""
        try:
            if self.app and self.widget_exists(self.app):
                w = int(self.app.winfo_width() or 0)
                if w > 1:
                    return w < self.COMPACT_PX
        except Exception:
            pass
        return False

    def _fit_dlg(self, wanted_w, wanted_h):
        """
        Klampa dialogstorlek till skarmen och centrera over app (Z4).

        Returnerar (w, h, x, y).
        """
        w, h, x, y = int(wanted_w), int(wanted_h), 80, 80
        try:
            w, h, x, y = fit_window(wanted_w, wanted_h, self.app, pad=60)
        except Exception:
            pass
        try:
            if self.app and self.widget_exists(self.app):
                px = int(self.app.winfo_rootx())
                py = int(self.app.winfo_rooty())
                pw = int(self.app.winfo_width())
                ph = int(self.app.winfo_height())
                if pw > 50 and ph > 50:
                    x = max(0, px + (pw - w) // 2)
                    y = max(0, py + (ph - h) // 2)
        except Exception:
            pass
        return w, h, x, y

    def _open_dialog(self, title, wanted_w, wanted_h, resizable=False):
        """
        Skapa temat Toplevel: klampad, centrerad, Escape stanger (Z4/Z7).
        """
        dlg = tk.Toplevel(self.app)
        dlg.title(title)
        dlg.configure(bg=self.COLOR_BG)
        try:
            dlg.transient(self.app)
            dlg.grab_set()
        except Exception:
            pass
        dlg.resizable(bool(resizable), bool(resizable))
        w, h, x, y = self._fit_dlg(
            self._scaled(wanted_w), self._scaled(wanted_h)
        )
        try:
            dlg.geometry("%dx%d+%d+%d" % (w, h, x, y))
        except Exception:
            pass
        dlg.bind("<Escape>", lambda e: self._close_dialog(dlg))
        dlg.protocol("WM_DELETE_WINDOW", lambda: self._close_dialog(dlg))
        self._reg_panels(dlg)
        try:
            dlg.lift()
            dlg.focus_force()
        except Exception:
            pass
        return dlg

    def _close_dialog(self, dlg) -> None:
        """Stang dialog och rensa tema-listor (Z5)."""
        try:
            dlg.grab_release()
        except Exception:
            pass
        try:
            dlg.destroy()
        except Exception:
            pass
        self._prune_theme_lists()

    def _mk_label(self, parent, text="", fg_attr="COLOR_FG", **kwargs):
        """Skapa tk.Label med tema-registrering och DPI-font."""
        pack_kw = kwargs.pop("pack", None) or {}
        kwargs.setdefault("bg", self.COLOR_BG)
        kwargs.setdefault("font", self._ui_font())
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
        self.safe_widget_config(widget, **kwargs)

    def _load_theme_colors(self) -> None:
        """Hamta farger fran ThemeEngine (fallback = klassattribut)."""
        try:
            for attr, key in self._THEME_KEYS.items():
                current = getattr(self, attr, None)
                fallback = current if current else "#888888"
                setattr(self, attr, self.get_theme_color(key, fallback))
        except Exception as e:
            self.log("FEL", "Tema-farger kunde inte laddas: %s" % e)

    def _restyle_all(self) -> None:
        """Applicera aktuella farger pa oppna dialoger."""
        if not self.is_active:
            return
        try:
            self._prune_theme_lists()
            for w in self._panels:
                self._safe_cfg(w, bg=self.COLOR_BG)
            for lbl, fg_attr in self._labels:
                self._safe_cfg(
                    lbl, bg=self.COLOR_BG,
                    fg=getattr(self, fg_attr, "#888888"),
                )
            st = getattr(self, "_shortcuts_text", None)
            if self.widget_exists(st):
                self._safe_cfg(
                    st,
                    bg=self.COLOR_SHORTCUT_BG,
                    fg=self.COLOR_SHORTCUT_FG,
                )
        except Exception:
            pass

    def on_theme_changed(self, event=None) -> None:
        """Uppdatera farger vid tema-byte (utan omstart)."""
        if not self.is_active:
            return
        self._load_theme_colors()
        self._restyle_all()

    # ==========================================================================
    # INITIERING
    # ==========================================================================

    def init(self, app) -> None:
        """
        Initialisera menyrad.

        Steg:
          1. Ladda tema-farger + DPI-text
          2. Ladda senaste mappar
          3. Bygg / utoka menyer
          4. Registrera tangentbordsgenvagar
          5. Registrera i context + tema-dispatcher
        """
        super().init(app)
        self.app = app

        self._ensure_theme_lists()
        self._apply_text_adaptation()
        self._load_theme_colors()

        self.plugin_vars    = {}
        self.recent_folders = []
        self.menus          = {}
        self._recent_job    = None
        self._plugin_menu_names = None
        self._shortcuts_text = None

        self.recent_folders = self._load_recent_folders()

        # Z8: menubar överlever reload_plugins - bygg bara en gång
        if getattr(app, "_mm_built", False) and self._adopt_menus():
            self._refresh_recent_menu()
            self._refresh_plugins_menu(force=True)
        else:
            self._extend_arkiv_menu()
            self._build_redigera_menu()
            self._extend_kor_menu()
            self._build_plugins_menu()
            self._extend_help_menu()
            self._stash_menus()
            app._mm_built = True

        self._install_gallery_menu()
        self._setup_shortcuts()

        app.context["_menu_manager"] = self

        # Z1: delad dispatcher - stjal inte <<ThemeChanged>>
        self.register_theme_callback()

        self.log(
            "OK",
            "%s v%s initierad" % (self.PLUGIN_NAME, self.VERSION)
        )

    def _stash_menus(self) -> None:
        """Spara menyreferenser på app så reload inte duplicerar (Z8)."""
        app = self.app
        app._mm_menus = dict(self.menus)
        app._mm_recent_menu = getattr(self, "_recent_menu", None)
        app._mm_plugins_menu = getattr(self, "_plugins_menu", None)

    def _adopt_menus(self) -> bool:
        """Återanvänd menyer som överlevde reload. False = bygg nytt."""
        app = self.app
        menus = getattr(app, "_mm_menus", None) or {}
        recent = getattr(app, "_mm_recent_menu", None)
        plugins = getattr(app, "_mm_plugins_menu", None)
        file_m = menus.get("file")
        if not self.widget_exists(file_m):
            return False
        try:
            file_m.index("end")
        except Exception:
            return False
        if plugins is not None and not self.widget_exists(plugins):
            return False
        self.menus = menus
        self._recent_menu = recent
        self._plugins_menu = plugins
        return True

    def _menu_label_index(self, menu, label):
        """Index for en menyetikett, eller None."""
        try:
            end = menu.index("end")
            if end is None:
                return None
            for i in range(int(end) + 1):
                try:
                    if menu.entrycget(i, "label") == label:
                        return i
                except Exception:
                    continue
        except Exception:
            pass
        return None

    def _ensure_menu_command(
        self, menu, label, command, accelerator=None, after=None,
    ) -> None:
        """Lagg till eller uppdatera en kommandopost (idempotent)."""
        if menu is None:
            return
        idx = self._menu_label_index(menu, label)
        if idx is not None:
            try:
                kw = {"command": command}
                if accelerator:
                    kw["accelerator"] = accelerator
                menu.entryconfig(idx, **kw)
            except Exception:
                pass
            return
        kw = {"label": label, "command": command}
        if accelerator:
            kw["accelerator"] = accelerator
        try:
            if after:
                aidx = self._menu_label_index(menu, after)
                if aidx is not None:
                    menu.insert_command(aidx + 1, **kw)
                    return
            menu.add_command(**kw)
        except Exception:
            try:
                menu.add_command(**kw)
            except Exception:
                pass

    def _install_gallery_menu(self) -> None:
        """Arkiv-poster for historik / lagg till media."""
        arkiv = self.menus.get("file")
        self._ensure_menu_command(
            arkiv, "Importera fran historik...",
            self.open_generated_gallery, "Ctrl+Shift+G",
            after="Valj bildmapp...",
        )
        self._ensure_menu_command(
            arkiv, "Lagg till bilder...",
            self.add_images_to_gallery,
            after="Importera fran historik...",
        )
        self._ensure_menu_command(
            arkiv, "Lagg till videor...",
            self.add_videos_to_gallery,
            after="Lagg till bilder...",
        )
        self._ensure_menu_command(
            arkiv, "Valj bildmapp...",
            self.select_folder, "Ctrl+O",
        )
        self._ensure_menu_command(
            arkiv, "Oppna output-mapp",
            self.open_output_folder, "Ctrl+Shift+O",
        )
        self._ensure_menu_command(
            arkiv, "Oppna i webblasare",
            self.open_in_browser, "F12",
        )

    def _settings(self):
        try:
            return self.app.context.get("_settings")
        except Exception:
            return None

    def open_generated_gallery(self) -> None:
        """Importera ett genererat galleri fran historiken."""
        s = self._settings()
        if s and hasattr(s, "browse_generated_gallery"):
            s.browse_generated_gallery()
            return
        messagebox.showwarning(
            "Saknas", "Installningar-pluginet kan inte oppna historiken."
        )

    def add_images_to_gallery(self) -> None:
        """Lagg till bilder i aktivt galleri."""
        s = self._settings()
        if s and hasattr(s, "add_images_to_gallery"):
            s.add_images_to_gallery()
            return
        messagebox.showwarning("Saknas", "Installningar-pluginet saknas.")

    def add_videos_to_gallery(self) -> None:
        """Lagg till videor i aktivt galleri."""
        s = self._settings()
        if s and hasattr(s, "add_videos_to_gallery"):
            s.add_videos_to_gallery()
            return
        messagebox.showwarning("Saknas", "Installningar-pluginet saknas.")

    # ==========================================================================
    # BYGG MENYER
    # ==========================================================================

    def _extend_arkiv_menu(self) -> None:
        """
        Lagg till poster i main.py:s Arkiv-meny.

        main.py skapar: Ladda om plugins / --- / Avsluta
        Vi infogar FORE dessa (index 0+) med insert_command.
        """
        arkiv = getattr(self.app, "arkiv_menu", None)
        if arkiv is None:
            arkiv = tk.Menu(self.app.menubar, tearoff=0)
            try:
                self.app.menubar.insert_cascade(
                    0, label="Arkiv", menu=arkiv
                )
            except Exception:
                self.app.menubar.add_cascade(
                    label="Arkiv", menu=arkiv
                )

        self.menus["file"] = arkiv

        entries = [
            ("command", "Valj bildmapp...",
             self.select_folder, "Ctrl+O"),
        ]
        for i, (kind, label, cmd, acc) in enumerate(entries):
            try:
                arkiv.insert_command(
                    i, label=label, command=cmd, accelerator=acc
                )
            except Exception:
                arkiv.add_command(label=label, command=cmd)

        self._recent_menu = tk.Menu(arkiv, tearoff=0)
        try:
            arkiv.insert_cascade(
                1, label="Senaste mappar", menu=self._recent_menu
            )
        except Exception:
            arkiv.add_cascade(
                label="Senaste mappar", menu=self._recent_menu
            )
        self._refresh_recent_menu()

        inserts = [
            (2, "separator", None, None, None),
            (3, "command", "Oppna output-mapp",
             self.open_output_folder, "Ctrl+Shift+O"),
            (4, "command", "Oppna i webblasare",
             self.open_in_browser, "F12"),
            (5, "separator", None, None, None),
            (6, "command", "Exportera installningar...",
             self._export_settings, None),
            (7, "command", "Importera installningar...",
             self._import_settings, None),
            (8, "separator", None, None, None),
        ]
        for idx, kind, label, cmd, acc in inserts:
            try:
                if kind == "separator":
                    arkiv.insert_separator(idx)
                else:
                    kw = {"label": label, "command": cmd}
                    if acc:
                        kw["accelerator"] = acc
                    arkiv.insert_command(idx, **kw)
            except Exception:
                if kind == "separator":
                    arkiv.add_separator()
                elif label:
                    kw = {"label": label, "command": cmd}
                    if acc:
                        kw["accelerator"] = acc
                    arkiv.add_command(**kw)

    def _build_redigera_menu(self) -> None:
        """Skapa Redigera-menyn. Infoga EFTER Arkiv, FORE Visa."""
        menu = tk.Menu(self.app.menubar, tearoff=0)
        try:
            self.app.menubar.insert_cascade(
                2, label="Redigera", menu=menu
            )
        except Exception:
            self.app.menubar.add_cascade(label="Redigera", menu=menu)

        self.menus["edit"] = menu

        menu.add_command(
            label="Sortera bilder...",
            command=self._open_sorter,
            accelerator="Ctrl+S",
        )
        menu.add_separator()
        menu.add_command(
            label="Andra gallerititel...",
            command=self._edit_title,
        )
        menu.add_command(
            label="Bildkvalitet...",
            command=self._edit_quality,
        )
        menu.add_separator()
        menu.add_command(
            label="Rensa logg",
            command=self._clear_log,
            accelerator="Ctrl+L",
        )

    def _extend_kor_menu(self) -> None:
        """Lagg till Forhandsgranska i Kor-menyn."""
        kor = getattr(self.app, "run_menu", None)
        if kor is None:
            kor = tk.Menu(self.app.menubar, tearoff=0)
            self.app.menubar.add_cascade(label="Kor", menu=kor)

        self.menus["run"] = kor

        try:
            kor.insert_command(
                1,
                label="Forhandsgranska",
                command=self._run_preview,
                accelerator="F10",
            )
        except Exception:
            kor.add_command(
                label="Forhandsgranska",
                command=self._run_preview,
                accelerator="F10",
            )

    def _build_plugins_menu(self) -> None:
        """Skapa Plugins-menyn med checkboxar."""
        menu = tk.Menu(self.app.menubar, tearoff=0)
        try:
            kor_idx = self.app.menubar.index("Kor")
            self.app.menubar.insert_cascade(
                kor_idx + 1, label="Plugins", menu=menu
            )
        except Exception:
            self.app.menubar.add_cascade(label="Plugins", menu=menu)

        self.menus["plugins"] = menu
        self._plugins_menu    = menu
        self._refresh_plugins_menu(force=True)

    def _extend_help_menu(self) -> None:
        """Lagg till kortkommandon + plugin-mapp i Hjalp."""
        help_m = getattr(self.app, "help_menu", None)
        if help_m is None:
            help_m = tk.Menu(self.app.menubar, tearoff=0)
            self.app.menubar.add_cascade(label="Hjalp", menu=help_m)

        self.menus["help"] = help_m

        inserts = [
            (0, "command",   "Kortkommandon",      self._show_shortcuts),
            (1, "separator", None,                 None),
            (2, "command",   "Oppna plugin-mapp",  self._open_plugins_folder),
            (3, "separator", None,                 None),
        ]
        for idx, kind, label, cmd in inserts:
            try:
                if kind == "separator":
                    help_m.insert_separator(idx)
                else:
                    help_m.insert_command(idx, label=label, command=cmd)
            except Exception:
                if kind == "separator":
                    help_m.add_separator()
                elif label:
                    help_m.add_command(label=label, command=cmd)

    # ==========================================================================
    # TANGENTBORDSGENVAGAR
    # ==========================================================================

    def _typing_in_field(self) -> bool:
        """True om fokus är i ett textfält - då ska inte Ctrl+S mm stjäla (Z10)."""
        try:
            w = self.app.focus_get()
            if w is None:
                return False
            cls = str(w.winfo_class() or "")
            return cls in ("Entry", "TEntry", "Text", "TCombobox", "Spinbox")
        except Exception:
            return False

    def _unless_typing(self, fn):
        """Kör fn bara om användaren inte skriver i ett fält."""
        def _wrap(event=None):
            if self._typing_in_field():
                return
            return fn()
        return _wrap

    def _setup_shortcuts(self) -> None:
        """Registrera genvägar med add='+' (Z9). macOS: Command-*."""
        pairs = [
            (("<Control-o>", "<Command-o>"), self.select_folder),
            (("<Control-O>", "<Command-O>"), self.select_folder),
            (("<Control-Shift-O>", "<Command-Shift-O>"),
             self.open_output_folder),
            (("<Control-Shift-G>", "<Command-Shift-G>"),
             self.open_generated_gallery),
            (("<F12>",), self.open_in_browser),
            (("<Control-s>", "<Command-s>"), self._open_sorter),
            (("<Control-S>", "<Command-S>"), self._open_sorter),
            (("<Control-l>", "<Command-l>"), self._clear_log),
            (("<Control-L>", "<Command-L>"), self._clear_log),
            (("<F9>", "<Control-g>", "<Control-G>",
              "<Command-g>", "<Command-G>"), self.run_generate),
            (("<F10>",), self._run_preview),
            (("<Control-r>", "<Control-R>", "<Command-r>",
              "<Command-R>", "<F5>"), self._reload_plugins),
        ]
        prev = getattr(self.app, "_mm_bound_keys", ())
        for key in prev:
            try:
                self.app.unbind(key)
            except Exception:
                pass
        bound = []
        darwin = sys.platform == "darwin"
        for keys, fn in pairs:
            wrap = self._unless_typing(fn)
            for key in keys:
                if key.startswith("<Command") and not darwin:
                    continue
                try:
                    self.app.bind(key, wrap, add="+")
                    bound.append(key)
                except Exception:
                    pass
        self.app._mm_bound_keys = tuple(bound)

    # ==========================================================================
    # SENASTE MAPPAR
    # ==========================================================================

    def _load_recent_folders(self) -> list:
        """Ladda senaste mappar. Filtrerar bort mappar som inte finns."""
        try:
            data = self.load_config(self.RECENT_FILE, default={})
            if not isinstance(data, dict):
                data = {}
            folders = data.get("folders", data.get("recent", []))
            out = []
            seen = set()
            for f in folders:
                s = str(f)
                if s in seen:
                    continue
                try:
                    if Path(s).exists():
                        out.append(s)
                        seen.add(s)
                except Exception:
                    continue
                if len(out) >= self.MAX_RECENT:
                    break
            return out
        except Exception as e:
            self.log(
                "VARNING",
                "Kunde inte lasa %s: %s" % (self.RECENT_FILE, e)
            )
            return []

    def _save_recent_folders(self) -> None:
        """Spara senaste mappar atomiskt (arvd save_config, A9)."""
        try:
            self.save_config(
                self.RECENT_FILE,
                {"folders": self.recent_folders[: self.MAX_RECENT]},
            )
        except Exception as e:
            self.log(
                "VARNING",
                "Kunde inte spara %s: %s" % (self.RECENT_FILE, e)
            )

    def add_recent_folder(self, folder: str) -> None:
        """Lagg till mapp i senaste-listan (publik API)."""
        folder = str(folder)
        if folder in self.recent_folders:
            self.recent_folders.remove(folder)
        self.recent_folders.insert(0, folder)
        self.recent_folders = self.recent_folders[: self.MAX_RECENT]
        self._save_recent_folders()
        self._refresh_recent_menu()

    def _folder_label(self, folder: str) -> str:
        """Visa mappnamn forst, sedan kort foralder (Z7)."""
        try:
            p = Path(folder)
            name = p.name or str(p)
            parent = str(p.parent)
            if len(parent) > 42:
                parent = "..." + parent[-39:]
            return "%s  (%s)" % (name, parent)
        except Exception:
            if len(folder) <= 55:
                return folder
            return "...%s" % folder[-52:]

    def _refresh_recent_menu(self) -> None:
        """Rita om 'Senaste mappar' - coalescera via after_idle (Z6)."""
        app = getattr(self, "app", None)
        if app is not None and hasattr(app, "after"):
            job = getattr(self, "_recent_job", None)
            if job is not None:
                try:
                    app.after_cancel(job)
                except Exception:
                    pass
            try:
                self._recent_job = app.after(40, self._refresh_recent_menu_now)
                return
            except Exception:
                pass
        self._refresh_recent_menu_now()

    def _refresh_recent_menu_now(self) -> None:
        """Faktisk ommalning av senaste-mappar."""
        self._recent_job = None
        if not hasattr(self, "_recent_menu"):
            return
        try:
            self._recent_menu.delete(0, tk.END)
        except Exception:
            return

        if not self.recent_folders:
            self._recent_menu.add_command(
                label="(Inga senaste mappar)",
                state="disabled",
            )
            return

        for i, folder in enumerate(self.recent_folders, 1):
            self._recent_menu.add_command(
                label="%d. %s" % (i, self._folder_label(folder)),
                command=lambda f=folder: self.set_folder(f),
            )

        self._recent_menu.add_separator()
        self._recent_menu.add_command(
            label="Rensa lista",
            command=self._clear_recent,
        )

    def _clear_recent(self) -> None:
        """Rensa senaste mappar."""
        self.recent_folders = []
        self._save_recent_folders()
        self._refresh_recent_menu()

    # ==========================================================================
    # VALJ MAPP
    # ==========================================================================

    def _list_images(self, folder) -> list:
        """Bilder i mappen, dolda filer hoppas over."""
        try:
            p = Path(folder)
            if not p.exists():
                return []
            return sorted(
                f for f in p.glob("*")
                if f.is_file()
                and f.suffix.lower() in self.IMAGE_EXTS
                and not f.name.startswith(".")
            )
        except Exception:
            return []

    def select_folder(self) -> None:
        """Oppna OS-dialog for att valja bildmapp."""
        initial = (
            self.recent_folders[0]
            if self.recent_folders else str(Path.home())
        )
        folder = filedialog.askdirectory(
            title="Valj mapp med bilder",
            initialdir=initial,
        )
        if folder:
            self.set_folder(folder)

    def set_folder(self, folder: str) -> None:
        """
        Satt aktiv bildmapp.

        Uppdaterar context, ui_settings, gallery_view och senaste-listan.
        """
        folder_path = Path(folder)
        if not folder_path.exists():
            messagebox.showerror(
                "Fel", "Mappen finns inte:\n%s" % folder
            )
            return

        images = self._list_images(folder_path)
        if not images:
            if not messagebox.askyesno(
                "Inga bilder",
                "Mappen innehaller inga bilder.\nValj den anda?"
            ):
                return

        self.app.context["selected_folder"] = str(folder)

        settings = self.app.context.get("_settings")
        if settings and hasattr(settings, "folder_var"):
            settings.folder_var.set(str(folder))

        gallery = self.app.context.get("_gallery_view")
        if gallery:
            gallery.current_folder = folder_path
            if hasattr(gallery, "load_images"):
                try:
                    gallery.load_images()
                except Exception as e:
                    self.log(
                        "VARNING",
                        "gallery_view.load_images(): %s" % e
                    )

        self.add_recent_folder(str(folder))

        self.log(
            "INFO",
            "Bildmapp vald: %s (%d bilder)"
            % (folder_path.name, len(images)),
        )

    # ==========================================================================
    # OPPNA FILER / MAPPAR
    # ==========================================================================

    def open_output_folder(self) -> None:
        """Oppna output-mappen i OS-filhanteraren."""
        output = self._get_output_path()
        if output and output.exists():
            self._open_in_os(output)
            self.log("INFO", "Oppnar output-mapp: %s" % output)
        else:
            messagebox.showwarning(
                "Output-mapp saknas",
                "Ingen output-mapp finns annu.\n"
                "Generera ett galleri forst.",
            )

    def open_in_browser(self) -> None:
        """Oppna index.html i systemets webblasare."""
        output = self._get_output_path()
        if output:
            index = output / "index.html"
            if index.exists():
                self._safe_open_browser(index)
                self.log("INFO", "Oppnar webblasare: %s" % index.name)
                return
        messagebox.showwarning(
            "Ingen HTML",
            "Ingen index.html finns annu.\nGenerera ett galleri forst.",
        )

    def _safe_open_browser(self, path: Path) -> None:
        """Oppna fil i webblasare utan att blockera UI."""
        try:
            abs_path = path.resolve()
            if sys.platform == "win32":
                flags = (
                    subprocess.CREATE_NO_WINDOW
                    if hasattr(subprocess, "CREATE_NO_WINDOW") else 0
                )
                subprocess.Popen(
                    ["cmd", "/c", "start", "", str(abs_path)],
                    shell=False,
                    creationflags=flags,
                )
            elif sys.platform == "darwin":
                subprocess.Popen(["open", str(abs_path)])
            else:
                subprocess.Popen(["xdg-open", str(abs_path)])
        except Exception as e:
            self.log_error("Kunde inte oppna webblasare", e)
            messagebox.showerror(
                "Fel", "Kunde inte oppna webblasare:\n%s" % e
            )

    def _open_in_os(self, path: Path) -> None:
        """Oppna mapp/fil i OS-filhanterare."""
        try:
            if sys.platform == "win32":
                subprocess.Popen(["explorer", str(path)])
            elif sys.platform == "darwin":
                subprocess.Popen(["open", str(path)])
            else:
                subprocess.Popen(["xdg-open", str(path)])
        except Exception as e:
            self.log_error("Kunde inte oppna %s" % path.name, e)

    def _open_plugins_folder(self) -> None:
        """Oppna plugins/-mappen i OS-filhanteraren."""
        self._open_in_os(Path(__file__).parent)

    def _get_output_path(self):
        """
        Berakna output-sokvag.

        1. settings.get_output_path (override for genererat galleri)
        2. context['output_path']
        3. out/<mappnamn>/
        """
        settings = self.app.context.get("_settings")
        if settings and hasattr(settings, "get_output_path"):
            try:
                p = settings.get_output_path()
                if p and Path(p).exists():
                    return Path(p)
            except Exception:
                pass
        output = self.app.context.get("output_path")
        if output:
            p = Path(output)
            if p.exists():
                return p

        folder = ""
        settings = self.app.context.get("_settings")
        if settings and hasattr(settings, "folder_var"):
            folder = settings.folder_var.get()
        if not folder:
            folder = self.app.context.get("selected_folder", "")
        if folder:
            name = Path(folder).name
            for cand in (
                Path("out") / name,
                Path(__file__).parent.parent / "out" / name,
            ):
                try:
                    if cand.exists():
                        return cand
                except Exception:
                    continue
        return None

    # ==========================================================================
    # REDIGERA-OPERATIONER
    # ==========================================================================

    def _open_sorter(self) -> None:
        """Oppna bildsorteraren (image_sorter.SorterWindow)."""
        settings = self.app.context.get("_settings")
        folder = ""
        if settings and hasattr(settings, "folder_var"):
            folder = settings.folder_var.get()
        if not folder:
            folder = self.app.context.get("selected_folder", "")

        if not folder or not Path(folder).exists():
            messagebox.showwarning(
                "Sorterare", "Valj en bildmapp forst!"
            )
            return

        images = self._list_images(folder)
        if not images:
            messagebox.showinfo(
                "Inga bilder", "Inga bilder hittades i mappen."
            )
            return

        try:
            from .image_sorter import SorterWindow
            sorter = SorterWindow(images)
            if sorter.result:
                self.app.context["sorted_images"] = sorter.result
                self.app.context["manual_sort"]   = True
                self.log(
                    "INFO",
                    "Bilder sorterade manuellt: %d st"
                    % len(sorter.result),
                )
        except ImportError:
            messagebox.showerror("Fel", "image_sorter.py saknas.")
        except Exception as e:
            self.log_error("Sorterare misslyckades", e)

    def _edit_title(self) -> None:
        """Dialog for att andra gallerititel."""
        current = (
            self.app.context.get("gallery", {})
            .get("title", "Bildgalleri")
        )

        dlg = self._open_dialog("Andra gallerititel", 420, 140)
        self._mk_label(dlg, "Gallerititel:", pack={"pady": (18, 4)})

        entry = ttk.Entry(dlg, width=44, font=self._ui_font())
        entry.insert(0, current)
        entry.select_range(0, tk.END)
        entry.pack(pady=4, padx=16, fill=tk.X)
        entry.focus_set()

        def _save():
            new = entry.get().strip()
            if new:
                self.app.context.setdefault("gallery", {})["title"] = new
                settings = self.app.context.get("_settings")
                if settings and hasattr(settings, "title_var"):
                    settings.title_var.set(new)
                self.log("INFO", "Gallerititel: %s" % new)
            self._close_dialog(dlg)

        btn_row = ttk.Frame(dlg)
        btn_row.pack(pady=8)
        ttk.Button(btn_row, text="Spara", command=_save).pack(
            side=tk.LEFT, padx=6
        )
        ttk.Button(
            btn_row, text="Avbryt",
            command=lambda: self._close_dialog(dlg),
        ).pack(side=tk.LEFT)

        entry.bind("<Return>", lambda e: _save())
        entry.bind("<Escape>", lambda e: self._close_dialog(dlg))

    def _edit_quality(self) -> None:
        """Dialog for att andra JPEG-kvalitet."""
        current = (
            self.app.context.get("gallery", {}).get("jpeg_quality", 85)
        )
        try:
            current = int(current)
        except Exception:
            current = 85
        current = max(10, min(100, current))

        compact = self._is_compact_screen()
        dlg = self._open_dialog("JPEG-kvalitet", 360, 200 if compact else 210)

        self._mk_label(
            dlg, "JPEG-kvalitet (10-100):",
            pack={"pady": (16, 4)},
        )

        var = tk.IntVar(value=current)
        pct = self._mk_label(
            dlg, "%d%%" % current,
            font=self._ui_font("bold"),
        )
        pct.pack()

        hint = self._mk_label(
            dlg, "70 webb   ·   85 standard   ·   95 print",
            fg_attr="COLOR_SHORTCUT_FG",
            font=self._ui_font(),
        )
        hint.pack(pady=(0, 4))

        slider_len = 200 if compact else self._scaled(260)

        def _live(v):
            try:
                pct.config(text="%d%%" % int(float(v)))
            except Exception:
                pass

        ttk.Scale(
            dlg, from_=10, to=100, variable=var,
            orient=tk.HORIZONTAL, length=slider_len,
            command=_live,
        ).pack(pady=6, padx=16, fill=tk.X)

        def _save():
            q = int(var.get())
            self.app.context.setdefault("gallery", {})["jpeg_quality"] = q
            self.log("INFO", "JPEG-kvalitet: %d%%" % q)
            self._close_dialog(dlg)

        btn_row = ttk.Frame(dlg)
        btn_row.pack(pady=8)
        ttk.Button(btn_row, text="Spara", command=_save).pack(
            side=tk.LEFT, padx=6
        )
        ttk.Button(
            btn_row, text="Avbryt",
            command=lambda: self._close_dialog(dlg),
        ).pack(side=tk.LEFT)

    def _clear_log(self) -> None:
        """Rensa logg-UI (filen paverkas inte)."""
        logger = self.app.context.get("_logger")
        if logger:
            for method in ("clear_display", "_clear_log", "clear"):
                if hasattr(logger, method):
                    try:
                        getattr(logger, method)()
                        break
                    except Exception:
                        pass
        self.log("INFO", "Logg rensad")

    # ==========================================================================
    # GENERERA / FORHANDSGRANSKNING
    # ==========================================================================

    def run_generate(self) -> None:
        """
        Kor galleri-generering.

        1. ui_controls.run_generate() - bakgrundstrad + progress
        2. app.run_pipeline()         - synkron fallback
        """
        if not self._validate_folder():
            return

        controls = self.app.context.get("_controls")
        if controls and hasattr(controls, "run_generate"):
            controls.run_generate()
            return

        self.log("INFO", "Genererar galleri (direkt)...")
        self._prepare_context()
        try:
            self.app.run_pipeline()
            self._offer_open_browser()
        except Exception as e:
            self.log_error("Generering misslyckades", e)
            messagebox.showerror("Genereringsfel", str(e))

    def _run_preview(self) -> None:
        """Forhandsgranska senast genererade galleri."""
        output = self._get_output_path()
        if output:
            index = output / "index.html"
            if index.exists():
                self._safe_open_browser(index)
                return

        if messagebox.askyesno(
            "Forhandsgranska",
            "Inget galleri finns annu.\nGenerera nu?"
        ):
            self.run_generate()

    def _prepare_context(self) -> None:
        """Forbered context infor direkt pipeline-korning."""
        gallery = self.app.context.get("_gallery_view")
        if (
            gallery
            and hasattr(gallery, "image_files")
            and gallery.image_files
            and "sorted_images" not in self.app.context
        ):
            self.app.context["sorted_images"] = list(gallery.image_files)
            self.app.context["gallery_order"] = True

        self.app.context.setdefault("ftp_enabled", False)

    def _offer_open_browser(self) -> None:
        """Erbjud att oppna galleriet i webblasaren efter generering."""
        output = self._get_output_path()
        if output:
            index = output / "index.html"
            if index.exists() and messagebox.askyesno(
                "Generering klar",
                "Galleriet har genererats!\n\nOppna i webblasare?"
            ):
                self._safe_open_browser(index)

    def _validate_folder(self) -> bool:
        """True om en bildmapp ar vald och finns."""
        settings = self.app.context.get("_settings")
        folder = ""
        if settings and hasattr(settings, "folder_var"):
            folder = settings.folder_var.get()
        if not folder:
            folder = self.app.context.get("selected_folder", "")

        if not folder:
            messagebox.showwarning(
                "Ingen mapp vald",
                "Valj en bildmapp forst!\n\n"
                "Arkiv -> Valj bildmapp...",
            )
            return False

        if not Path(folder).exists():
            messagebox.showerror(
                "Mapp saknas", "Mappen finns inte:\n%s" % folder
            )
            return False

        return True

    # ==========================================================================
    # PLUGINS-MENY
    # ==========================================================================

    def _plugin_names(self) -> tuple:
        """Aktuella plugin-namn (utan menu_manager), stabil ordning."""
        try:
            return tuple(
                n for n, _p in self.app.get_plugins()
                if n != "menu_manager"
            )
        except Exception:
            return tuple()

    def _sync_plugin_vars(self) -> None:
        """Uppdatera checkboxar utan att bygga om menyn (Z6)."""
        for name, var in list(self.plugin_vars.items()):
            try:
                var.set(self.app.plugin_enabled.get(name, True))
            except Exception:
                pass

    def _refresh_plugins_menu(self, force=False) -> None:
        """Rita om Plugins-menyn. Hoppar over om listan ar oforandrad."""
        if not hasattr(self, "_plugins_menu"):
            return

        names = self._plugin_names()
        if (
            not force
            and names == getattr(self, "_plugin_menu_names", None)
            and self.plugin_vars
        ):
            self._sync_plugin_vars()
            return

        self._plugin_menu_names = names
        self._plugins_menu.delete(0, tk.END)
        self.plugin_vars.clear()

        plugins = []
        try:
            plugins = list(self.app.get_plugins())
        except Exception:
            plugins = []

        last_group = None
        for name, plugin in plugins:
            if name == "menu_manager":
                continue

            prio = getattr(plugin, "PRIORITY", 100)
            group = prio // 10
            if last_group is not None and group != last_group:
                self._plugins_menu.add_separator()
            last_group = group

            var = tk.BooleanVar(
                value=self.app.plugin_enabled.get(name, True)
            )
            self.plugin_vars[name] = var
            pname = getattr(plugin, "PLUGIN_NAME", name)
            state = (
                tk.DISABLED if name in self.PROTECTED_PLUGINS
                else tk.NORMAL
            )
            self._plugins_menu.add_checkbutton(
                label=pname,
                variable=var,
                command=lambda n=name: self._toggle_plugin(n),
                state=state,
            )

        self._plugins_menu.add_separator()
        self._plugins_menu.add_command(
            label="Aktivera alla",
            command=self._enable_all_plugins,
        )
        self._plugins_menu.add_command(
            label="Avaktivera alla",
            command=self._disable_all_plugins,
        )
        self._plugins_menu.add_separator()
        self._plugins_menu.add_command(
            label="Ladda om plugins",
            command=self._reload_plugins,
        )

    def _toggle_plugin(self, name: str) -> None:
        """Aktivera/inaktivera ett plugin via checkbox."""
        if name in self.PROTECTED_PLUGINS:
            return
        enabled = self.plugin_vars[name].get()
        self.app.plugin_enabled[name] = enabled
        plugin = self.app.plugins.get(name)
        pname = getattr(plugin, "PLUGIN_NAME", name) if plugin else name
        self.log(
            "INFO",
            "Plugin '%s': %s" % (
                pname, "aktiv" if enabled else "inaktiv"
            ),
        )

    def _enable_all_plugins(self) -> None:
        """Aktivera alla plugins."""
        for name in self.app.plugins:
            self.app.plugin_enabled[name] = True
        self._refresh_plugins_menu()
        self.log("INFO", "Alla plugins aktiverade")

    def _disable_all_plugins(self) -> None:
        """Avaktivera alla plugins utom skyddade."""
        for name in self.app.plugins:
            if name not in self.PROTECTED_PLUGINS:
                self.app.plugin_enabled[name] = False
        self._refresh_plugins_menu()
        self.log("INFO", "Alla valbara plugins avaktiverade")

    def _reload_plugins(self) -> None:
        """Ladda om plugins via main.py."""
        self.log("SYSTEM", "Laddar om plugins...")
        try:
            self.app.reload_plugins()
            self._refresh_plugins_menu(force=True)
            messagebox.showinfo("Klart", "Plugins har laddats om!")
        except Exception as e:
            self.log_error("Omladdning misslyckades", e)
            messagebox.showerror("Omladdningsfel", str(e))

    # ==========================================================================
    # EXPORTERA / IMPORTERA INSTALLNINGAR
    # ==========================================================================

    def _export_settings(self) -> None:
        """Exportera installningar till JSON-fil."""
        path = filedialog.asksaveasfilename(
            title="Exportera installningar",
            defaultextension=".json",
            filetypes=[("JSON-filer", "*.json")],
            initialfile=(
                "gallery_settings_%s.json"
                % datetime.now().strftime("%Y%m%d")
            ),
        )
        if not path:
            return
        try:
            data = {
                "gallery":        self.app.context.get("gallery", {}),
                "plugin_enabled": dict(self.app.plugin_enabled),
                "recent_folders": self.recent_folders,
            }
            Path(path).write_text(
                json.dumps(data, indent=2, default=str),
                encoding="utf-8",
            )
            self.log(
                "OK",
                "Installningar exporterade: %s" % Path(path).name
            )
            messagebox.showinfo(
                "Exporterat",
                "Installningar sparade:\n%s" % path,
            )
        except Exception as e:
            self.log_error("Export misslyckades", e)
            messagebox.showerror("Exportfel", str(e))

    def _import_settings(self) -> None:
        """Importera installningar fran JSON-fil."""
        path = filedialog.askopenfilename(
            title="Importera installningar",
            filetypes=[("JSON-filer", "*.json")],
        )
        if not path:
            return
        try:
            data = json.loads(
                Path(path).read_text(encoding="utf-8")
            )
            if "gallery" in data:
                self.app.context["gallery"] = data["gallery"]
            if "plugin_enabled" in data:
                self.app.plugin_enabled.update(data["plugin_enabled"])
                self._refresh_plugins_menu(force=True)
            if "recent_folders" in data:
                for f in reversed(data["recent_folders"]):
                    self.add_recent_folder(f)
            self.log(
                "OK",
                "Installningar importerade: %s" % Path(path).name
            )
            messagebox.showinfo(
                "Importerat", "Installningar importerade!"
            )
        except Exception as e:
            self.log_error("Import misslyckades", e)
            messagebox.showerror("Importfel", str(e))

    # ==========================================================================
    # HJALP-DIALOGER
    # ==========================================================================

    def _show_shortcuts(self) -> None:
        """Visa kortkommando-dialog (DPI-font, klampad till skarm)."""
        shortcuts = (
            "KORTKOMMANDON - Gallery Uploader\n"
            "==================================\n"
            "\n"
            "ARKIV\n"
            "  Ctrl+O          Valj bildmapp\n"
            "  Ctrl+Shift+G    Importera fran historik\n"
            "  Ctrl+Shift+O    Oppna output-mapp\n"
            "  F12             Oppna i webblasare\n"
            "\n"
            "REDIGERA\n"
            "  Ctrl+S          Sortera bilder\n"
            "  Ctrl+L          Rensa logg\n"
            "\n"
            "KOR\n"
            "  Ctrl+G / F9     Generera galleri\n"
            "  F10             Forhandsgranska\n"
            "  Ctrl+R / F5     Ladda om plugins\n"
            "\n"
            "GALLERI / SORTERARE\n"
            "  Ctrl+klick      Valj flera\n"
            "  Shift+klick     Valj serie\n"
            "  Drag            Flytta bilder\n"
            "  Delete          Ta bort valda\n"
            "  Ctrl+Z          Angra\n"
            "  Ctrl+Y          Gor om\n"
            "  Ctrl+A          Valj alla\n"
        )
        size = int(getattr(self, "_base_font_size", 9) or 9)
        try:
            want_w = max(380, min(560, readable_width(
                self.app, chars=42, font_size=size
            )))
        except Exception:
            want_w = 440
        dlg = self._open_dialog("Kortkommandon", want_w, 520)

        self._shortcuts_text = tk.Text(
            dlg, wrap=tk.WORD,
            font=self._ui_font(mono=True),
            padx=self._scaled(18), pady=self._scaled(14),
            bg=self.COLOR_SHORTCUT_BG, fg=self.COLOR_SHORTCUT_FG,
            relief=tk.FLAT, highlightthickness=0,
        )
        self._shortcuts_text.insert("1.0", shortcuts)
        self._shortcuts_text.config(state=tk.DISABLED)
        self._shortcuts_text.pack(fill=tk.BOTH, expand=True)

        ttk.Button(
            dlg, text="Stang",
            command=lambda: self._close_dialog(dlg),
        ).pack(pady=10)

    # ==========================================================================
    # PUBLIK API
    # ==========================================================================

    def add_menu_item(
        self,
        menu_name: str,
        label: str,
        command,
        position=None,
        accelerator: str = None,
        separator_before: bool = False,
    ) -> bool:
        """
        Lagg till menyalternativ fran annat plugin.

        menu_name: "file"|"edit"|"run"|"plugins"|"help"
        Returnerar True vid lyckat tillagg.
        """
        menu = self.menus.get(menu_name)
        if not menu:
            self.log("VARNING", "Meny '%s' finns inte" % menu_name)
            return False
        try:
            kwargs = {"label": label, "command": command}
            if accelerator:
                kwargs["accelerator"] = accelerator

            if position is None:
                if separator_before:
                    menu.add_separator()
                menu.add_command(**kwargs)
            elif position == "end":
                end = menu.index("end")
                if separator_before:
                    menu.insert_separator(end)
                    end += 1
                menu.insert_command(end, **kwargs)
            else:
                if separator_before:
                    menu.insert_separator(position)
                    position += 1
                menu.insert_command(position, **kwargs)
            return True
        except Exception as e:
            self.log(
                "DEBUG",
                "add_menu_item('%s','%s'): %s"
                % (menu_name, label, e)
            )
            return False

    def add_menu_separator(self, menu_name: str, position=None) -> bool:
        """Lagg till separator i meny."""
        menu = self.menus.get(menu_name)
        if not menu:
            return False
        try:
            if position is None:
                menu.add_separator()
            else:
                menu.insert_separator(position)
            return True
        except Exception as e:
            self.log("DEBUG", "add_menu_separator: %s" % e)
            return False

    # ==========================================================================
    # PLUGIN-KONTRAKT
    # ==========================================================================

    def execute(self, context: dict, log=None) -> dict:
        """Pipeline-passthrough - returnerar context oforandrad."""
        return context

    def cleanup(self) -> None:
        """Spara senaste mappar, avbryt after()-jobb, rensa dialoger."""
        job = getattr(self, "_recent_job", None)
        if job is not None and self.app is not None:
            try:
                self.app.after_cancel(job)
            except Exception:
                pass
        self._recent_job = None
        self._save_recent_folders()
        self._prune_theme_lists()
        super().cleanup()
