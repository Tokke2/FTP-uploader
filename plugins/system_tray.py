#!/usr/bin/env python3
# ============================================================
# Gallery Uploader - System Tray Plugin
# ============================================================
# FIL:       plugins/system_tray.py
# PLATS:     plugins/ (ftp_gallery_uploader/plugins/system_tray.py)
# Klass:     SystemTrayPlugin(BasePlugin)
# PRIORITY:  3
# VERSION:   3.6.0
# AUTHOR:    Rickard Längkvist
# COPYRIGHT: Copyright (c) <år> Rickard Längkvist (dynamiskt år,
#            se COPYRIGHT-konstanten nedan)
#
# ÄNDRINGAR v3.5.2 → v3.6.0:
#   [P14-16]  EN ikon: main.pyw _start_systray anvander denna plugin
#             som _systray_mgr om tray redan kors (skapar inte
#             helpers.SystrayManager). _claim_systray_ownership kvar
#             som sakerhetsnat.
#
# ÄNDRINGAR v3.5.1 → v3.5.2 (två loggbevisade buggar):
#   [P14-14]  BUGGFIX: try/except/ELSE i init() steg 5-6. else-grenen körs
#             när after()-anropet LYCKAS (alltså alltid), inte när pystray
#             saknas. Följd i loggen 2026-09-21 09:14: falsk VARNING
#             "pystray/Pillow saknas" fast båda var installerade, OCH
#             app.after(200, app.show_window) tvingade fönstret synligt vid
#             varje start trots start_minimized=true (visas 200 ms,
#             minimeras sedan 400 ms → flimmer). Nu: varning + visning bara
#             när TRAY_AVAILABLE är False, och ägarskapsövertagandet
#             (P14-13) ligger i en egen try/except utan else.
#   [P14-15]  base_plugin v1.4.1 (R1) åtgärdar namnkollisionen som gav
#             "'list' object is not callable" i ui_settings/watch_folder/
#             video_processor. Denna plugin definierar själv _reg_panels()
#             och _reg_labels() och var lika drabbad.
#
# ÄNDRINGAR v3.4.0 → v3.5.0 (SYNLIGHETSVAKT — appen får aldrig vara onåbar):
#   [P14-10]  _schedule_visibility_check(): efter att tray-tråden startats
#             pollas tray_icon.visible var 500 ms i upp till 5 s (via
#             app.after, UI-tråden). pystray kan returnera UTAN undantag
#             men ändå aldrig visa ikonen (Shell_NotifyIcon misslyckas
#             tyst, Windows 11-overflow, trasig ikonbild). Kombinerat med
#             start_minimized=True blev appen då HELT OSYNLIG: inget
#             fönster och ingen ikon att klicka på. Nu: om ikonen aldrig
#             blir synlig loggas "SYSTRAY OSYNLIG" (FEL, med orsakstid i
#             errors-filen) OCH fönstret visas automatiskt som fallback.
#   [P14-11]  Ikonkällan loggas vid start: assets/icon.ico,
#             assets/icon.png eller genererad fallback (C2). Gör det
#             direkt synbart i loggen om ikonen är None/trasig.
#   [P14-12]  _tray_loop-kraschen nollställer _tray_visible så att
#             vakten inte tror att en död ikon lever.
#   [P14-13]  ENDAST EN ikon, garanterat: main.pyw:s steg 15 skapar en
#             EGEN helpers.SystrayManager eftersom dess dubblettskydd
#             (_systray_mgr är None) körs efter plugin-laddningen och
#             därför inte ser pluginens ikon. Två pystray-ikoner mot
#             samma skal kan ta bort/varandra -> osynlig ikon. Pluginen
#             tar därför över app._systray_mgr via after(60 ms):
#             stoppar helpers-managern och registrerar sig själv
#             (main.pyw anropar bara .start()/.stop() på attributet,
#             båda finns nu publikt här).
#
# ÄNDRINGAR v3.3.0 → v3.4.0 (kvalitet/design/minne, icke-brytande):
#   [Q1]      _reg_panels()/_reg_labels() de-duplicerar registrering
#             -> inga dubbla tema-omstylingar (minne/snabbhet).
#   [Q2]      _make_button(): hover/leave loser fargen dynamiskt ur
#             aktuell tema-farg (bg-attribut). Felrattat: efter
#             tema-byte återställde hover inte langre det nya temat.
#
# ÄNDRINGAR v3.2.0 → v3.3.0 (DESIGN-SYSTEM-integration, spec v4.6.0):
#   [C1]      Fargerna hamtas fran ThemeEngine-designsystemet
#             (helpers v1.3.0) via _THEME_KEYS:
#               COLOR_BG                            <- "bg"
#               COLOR_BG_BLUE/COLOR_BG_BLUE_DARK    <- "accent"/"accent_active"
#               COLOR_REFLECT/COLOR_LED_RED         <- "info"/"error"
#               COLOR_SUCCESS/COLOR_ERROR           <- "success"/"error"
#               COLOR_WARNING                       <- "warning"
#               COLOR_GRAY/COLOR_DARK               <- "button_bg"
#               COLOR_WHITE                         <- "selection_fg"
#   [C1]      _load_theme_colors() + _restyle_all() +
#             on_theme_changed() + register_theme_callback():
#             installningsdialogens farger uppdateras vid tema-byte
#             (dialogen registreras som panel; header med accent-
#             bakgrund hanteras separat da den INTE ska ha COLOR_BG)
#   [C1]      _make_button(): bg ar nu ATTRIBUTNAMN (strang) -
#             vardet hamtas via getattr() och knappen registreras
#             for omstyling vid tema-byte
#   [C1]      Nya hjälpare: _ensure_theme_lists, _reg_panels,
#             _reg_labels, _mk_label, _safe_cfg
#   [C4]      Dialogens Toplevel far bg=COLOR_BG (matchar ttk);
#             varnings-labels far tema-bakgrund via _mk_label
#   [C4]      OBS: COLOR_ICON_* (ikon-design) ar INTE tema-styrda
#             - fallback-ikonen ska ALLTID matcha app-ikonen (C2)
#
# BEVARAT FRÅN v3.2.0:
#   Ingen print() - all loggning via self.log()
#   log() och log_error() egna metoder (ej fran BasePlugin)
#   load_config/save_config egna metoder (A9/A10, ej fran BasePlugin)
#   _make_button -> attributnamn, _darken (hover-effekt)
#   _tray_loop() (konflikt med trad-metod atgardad)
#   Alla except-block loggar via self.log()
#   TRAY_AVAILABLE-kontroll i minimize_to_tray()
#   Wayland-fallback: XDG_SESSION_TYPE-kontroll
#   Robust _on_unmap: ignorerar om fonster inte ar iconic
#   Tydligare docstrings
#   Emoji borttagna ur Tkinter-widgets och tray-meny
#   Tema-undermeny i tray-menyn (A7) - oforandrad
#   Fallback-ikon i appens design (C2) - oforandrad
#
# ANSVARAR FOR:
#   - Systray-ikon (pystray + Pillow) - ENDA ikonen
#   - Genererad fallback-ikon i appens design om assets/ saknas
#   - Minimera till systray (X-knapp + Ctrl+M)
#   - Autostart (Windows registry)
#   - Installningsdialog
#   - Notifikationer
#   - Tema-byte via tray-menyn (A7)
#
# VIKTIG REGEL:
#   Detta plugin ar den ENDA systray-hanteraren.
#   main.py:s SystrayManager stoppas vid init() -> aldrig tva ikoner.
#
# CONTEXT SOM LASES:
#   '_controls'    - run_generate()
#   '_tab_manager' - select_tab()
#
# CONTEXT SOM SATTS:
#   '_system_tray' - self
#
# IMPORTER:
#   sys, os, json, threading, tempfile
#   tkinter as tk, ttk, messagebox
#   pathlib.Path
#   datetime
#   .base_plugin: BasePlugin
#   helpers: get_config_path, get_assets_path (valfritt)
#   pystray: Icon, Menu, MenuItem  (valfritt)
#   PIL: Image, ImageDraw          (valfritt)
#   winreg                         (Windows, valfritt)
# ============================================================

import sys
import os
import json
import tkinter as tk
from tkinter import ttk, messagebox
import threading
import tempfile
from pathlib import Path
from datetime import datetime

from .base_plugin import BasePlugin

# -- Helpers (valfritt – för config/assets-sökväg, A10/C2) -----
try:
    from helpers import get_config_path, get_assets_path
    _HAS_HELPERS = True
except ImportError:
    _HAS_HELPERS = False

# -- Systray (valfritt) ----------------------------------------
try:
    from pystray import Icon, Menu, MenuItem
    from PIL import Image as PILImage, ImageDraw
    TRAY_AVAILABLE = True
except ImportError:
    TRAY_AVAILABLE = False

# -- Wayland-kontroll (Linux) ----------------------------------
IS_WAYLAND = (
    sys.platform == "linux"
    and os.environ.get("XDG_SESSION_TYPE", "").lower() == "wayland"
)

# -- Autostart (Windows) ---------------------------------------
AUTOSTART_AVAILABLE = False
if sys.platform == "win32":
    try:
        import winreg
        AUTOSTART_AVAILABLE = True
    except ImportError:
        pass

AUTOSTART_KEY  = r"Software\Microsoft\Windows\CurrentVersion\Run"
AUTOSTART_NAME = "GalleryUploader"


class SystemTrayPlugin(BasePlugin):
    """
    ENDA systray-hanteraren for Gallery Uploader.

    main.py:s SystrayManager stoppas vid init() for att
    undvika dubbla ikoner.

    Wayland (Linux):
      Systray kan krascha pa Wayland. Om XDG_SESSION_TYPE=wayland
      visas fonstret direkt och X-knappen avslutar.

    v3.4.0:
    - _reg_panels()/_reg_labels() de-duplicerar (ingen dubbel omstyling)
    - _make_button(): hover foljer tema via bg-attribut (felrattat)

    v3.3.0:
    - Fargerna foljer ThemeEngine-designsystemet och uppdateras
      dynamiskt vid tema-byte (on_theme_changed + _restyle_all)
    - _make_button() tar emot bg som ATTRIBUTNAMN

    v3.2.0:
    - Tema-undermeny i tray-menyn (A7)
    - Fallback-ikon i appens design (C2)
    - Inga f-strings / hardkodade farger (B1)
    - Atomisk skrivning med fsync (A9), config/ via helpers (A10)
    """

    PLUGIN_NAME = "System Tray"
    PRIORITY    = 3
    VERSION     = "3.6.0"
    AUTHOR      = "Rickard Längkvist"
    COPYRIGHT   = "Copyright (c) %d %s" % (datetime.now().year, "Rickard Längkvist")

    ICON_SIZE = (64, 64)

    DEFAULTS = {
        "minimize_to_tray":   True,
        "close_to_tray":      True,
        "start_with_windows": False,
        "start_minimized":    False,
        "show_notifications": True,
    }

    # -- Fargkonstanter (B1/C1: tema-styrbara) -----------------
    COLOR_BG           = "#1e1e1e"
    COLOR_BG_BLUE      = "#2563eb"
    COLOR_BG_BLUE_DARK = "#1d4ed8"
    COLOR_REFLECT      = "#93c5fd"
    COLOR_LED_RED      = "#ef4444"
    COLOR_SUCCESS      = "#22c55e"
    COLOR_GRAY         = "#6b7280"
    COLOR_WARNING      = "#b45309"
    COLOR_ERROR        = "#b91c1c"
    COLOR_DARK         = "#4b5563"
    COLOR_WHITE        = "#ffffff"

    # -- Ikon-designfarger (C2: INTE tema-styrda) ---------------
    COLOR_ICON_TOP     = (45, 107, 224)     # #2D6BE0
    COLOR_ICON_BOT     = (122, 61, 245)     # #7A3DF5
    COLOR_ICON_SKY     = (205, 231, 255, 255)
    COLOR_ICON_SUN     = (255, 210, 63, 255)
    COLOR_ICON_MTN_L   = (120, 165, 235, 255)
    COLOR_ICON_MTN_D   = (61, 111, 216, 255)
    COLOR_ICON_HILL    = (76, 175, 110, 255)
    COLOR_ICON_GREEN   = (22, 201, 92, 255)
    COLOR_ICON_WHITE   = (255, 255, 255, 255)

    # -- Tema-nyckelmappning (C1) ------------------------------
    _THEME_KEYS = {
        "COLOR_BG":           "bg",
        "COLOR_BG_BLUE":      "accent",
        "COLOR_BG_BLUE_DARK": "accent_active",
        "COLOR_REFLECT":      "info",
        "COLOR_LED_RED":      "error",
        "COLOR_SUCCESS":      "success",
        "COLOR_GRAY":         "button_bg",
        "COLOR_WARNING":      "warning",
        "COLOR_ERROR":        "error",
        "COLOR_DARK":         "button_bg",
        "COLOR_WHITE":        "selection_fg",
    }

    # ==========================================================================
    # TEMA-FARGER (C1)
    # ==========================================================================

    def _ensure_theme_lists(self) -> None:
        """Initiera tema-omstylingslistor (defensivt)."""
        for name in ("_panels", "_buttons", "_labels"):
            if not hasattr(self, name):
                setattr(self, name, [])

    def _reg_panels(self, *widgets) -> None:
        """Registrera ramar/Toplevel for tema-omstyling (de-dup, Q1)."""
        for w in widgets:
            if w is not None and w not in self._panels:
                self._panels.append(w)

    def _reg_labels(self, *pairs) -> None:
        """Registrera (widget, fg-attribut)-par for omstyling (de-dup)."""
        for pair in pairs:
            if pair and pair not in self._labels:
                self._labels.append(pair)

    def _mk_label(self, parent, text="", fg_attr="COLOR_WHITE", **kwargs):
        """
        Skapa tk.Label med tema-registrering.

        Packas direkt om pack-kwargs skickas via 'pack'-nyckeln,
        t.ex. _mk_label(f, "Text", pack={"anchor": tk.W}).
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
        (installningsdialog: paneler, labels, knappar, header)
        vid tema-byte.
        """
        if not self.is_active:
            return
        try:
            # -- Paneler (dialog + ramar med bg=COLOR_BG) -------
            for w in self._panels:
                if self.widget_exists(w):
                    self._safe_cfg(w, bg=self.COLOR_BG)
            # -- Labels -----------------------------------------
            for lbl, fg_attr in self._labels:
                if self.widget_exists(lbl):
                    self._safe_cfg(
                        lbl, bg=self.COLOR_BG,
                        fg=getattr(self, fg_attr, "#888888"),
                    )
            # -- Knappar ----------------------------------------
            for btn, bg_attr in self._buttons:
                if self.widget_exists(btn):
                    c = getattr(self, bg_attr, "#4b5563")
                    self._safe_cfg(
                        btn, bg=c, fg=self.COLOR_WHITE,
                        activebackground=self._darken(c),
                        activeforeground=self.COLOR_WHITE,
                    )
            # -- Dialog-header (accent-bakgrund, ej COLOR_BG) ---
            if self.widget_exists(getattr(self, "_dlg_hdr", None)):
                self._safe_cfg(self._dlg_hdr, bg=self.COLOR_BG_BLUE)
            if self.widget_exists(getattr(self, "_dlg_hdr_lbl", None)):
                self._safe_cfg(
                    self._dlg_hdr_lbl,
                    bg=self.COLOR_BG_BLUE,
                    fg=self.COLOR_WHITE,
                )
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
    # INIT
    # ==========================================================================

    def init(self, app) -> None:
        """
        Initialisera systray-plugin.

        Steg:
          1. Stoppa main.py:s SystrayManager (dubblettskydd)
          2. Ladda installningar
          3. Satt X-knapp-handler
          4. Kontrollera Wayland (Linux)
          5. Starta systray om tillgangligt
          6. Starta minimerad om installt
        """
        super().init(app)
        self.app           = app
        self.tray_icon     = None
        self._tray_thread  = None
        self._tray_running = False
        self._tray_visible = False     # P14-10: bekräftad synlig ikon
        self._icon_source  = "?"       # P14-11: var ikonbilden kom ifrån

        # -- Tema-farger (C1) ----------------------------------
        self._ensure_theme_lists()
        self._load_theme_colors()

        self.settings = self._load_settings()
        app.context["_system_tray"] = self

        # -- 1. Stoppa main.py:s systray (dubblettskydd) -------
        if hasattr(app, "_systray_mgr") and app._systray_mgr:
            try:
                app._systray_mgr.stop()
            except Exception:
                pass
            app._systray_mgr = None
            self.log(
                "DEBUG",
                "Stoppade main.py:s SystrayManager (dubblettskydd)"
            )

        # -- 2. X-knapp-handler --------------------------------
        app.protocol("WM_DELETE_WINDOW", self._on_window_close)
        app.bind("<Unmap>", self._on_unmap)

        # -- 3. Ctrl+M (minimera) ------------------------------
        if TRAY_AVAILABLE and not IS_WAYLAND:
            app.bind_all("<Control-m>", lambda e: self.minimize_to_tray())
            app.bind_all("<Control-M>", lambda e: self.minimize_to_tray())

        # -- 4. Wayland-fallback -------------------------------
        if IS_WAYLAND:
            self.log(
                "VARNING",
                "Wayland detekterat - systray kan vara otillgangligt. "
                "Visar fonstret direkt."
            )
            app.after(200, app.show_window)
            self.log(
                "OK",
                "%s v%s (Wayland-lage)" % (self.PLUGIN_NAME, self.VERSION)
            )
            return

        # -- 5. Starta systray ---------------------------------
        if TRAY_AVAILABLE:
            self._start_tray()

        # -- 5b. Ta over agandeskapet (P14-13) -----------------
        # after() sa att main.pyw:s steg 15 hunnit skapa sin egen
        # SystrayManager innan vi stoppar den.
        # P14-14: INGEN else-gren har - else i try/except kOrs nar
        # after() LYCKAS och gav darfor falsk "pystray saknas"-varning
        # + tvingade fOnstret synligt trots start_minimized.
        try:
            self.app.after(60, self._claim_systray_ownership)
        except Exception:
            pass

        # -- 5c. Ingen tray alls: visa fOnstret sa att appen aldrig
        #         blir onabar (P14-14).
        if not TRAY_AVAILABLE:
            self.log(
                "VARNING",
                "pystray/Pillow saknas - pip install pystray Pillow"
            )
            app.after(200, app.show_window)

        # -- 6. Start minimerad --------------------------------
        if "--minimized" in sys.argv or \
                self.settings.get("start_minimized", False):
            if TRAY_AVAILABLE and self._tray_running:
                app.after(400, self.minimize_to_tray)
            else:
                app.after(200, app.show_window)

        # -- Tema-callback (C1) --------------------------------
        self.register_theme_callback()

        self.log("OK", "%s v%s" % (self.PLUGIN_NAME, self.VERSION))

    # ==========================================================================
    # IKON
    # ==========================================================================

    def _load_icon_image(self):
        """
        Ladda ikon i prioritetsordning:
          1. icon/ (icon_64.png, icon.png, icon.ico, ...)
          2. assets/ (bakåtkompatibilitet)
          3. Genererad fallback-ikon i appens design (C2)
        """
        if not TRAY_AVAILABLE:
            self._icon_source = "ingen (pystray/Pillow saknas)"
            return None

        try:
            from helpers import load_app_icon
            img, src = load_app_icon(prefer_size=64)
            self._icon_source = src
            if img is not None:
                return img
        except Exception as e:
            self.log("DEBUG", "load_app_icon misslyckades: %s" % e)

        self._icon_source = "genererad fallback-ikon (C2)"
        return self._generate_gallery_icon()

    def _generate_gallery_icon(self):
        """
        Generera fallback-ikon i SAMMA design som app-ikonen (C2).

        Design:
          - Rundad bakgrund, bla->lila gradient (uppifran och ner)
          - Vitt bildkort med landskap (himmel + sol + berg + kulle)
          - Gron uppladdnings-badge med vit pil upp
        """
        if not TRAY_AVAILABLE:
            return None

        W, H = self.ICON_SIZE
        img  = PILImage.new("RGBA", (W, H), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        top = self.COLOR_ICON_TOP
        bot = self.COLOR_ICON_BOT

        # -- Gradientbakgrund (rad for rad) + rundad mask ------
        for y in range(H):
            t = y / (H - 1) if H > 1 else 0
            r = int(top[0] + (bot[0] - top[0]) * t)
            g = int(top[1] + (bot[1] - top[1]) * t)
            b = int(top[2] + (bot[2] - top[2]) * t)
            draw.line([(0, y), (W, y)], fill=(r, g, b, 255))
        mask = PILImage.new("L", (W, H), 0)
        ImageDraw.Draw(mask).rounded_rectangle(
            [0, 0, W - 1, H - 1], radius=8, fill=255
        )
        img.putalpha(mask)

        # -- Vitt bildkort -------------------------------------
        card = [int(W * 0.25), int(H * 0.16), int(W * 0.75), int(H * 0.58)]
        draw.rounded_rectangle(card, radius=4, fill=self.COLOR_ICON_WHITE)

        # -- Landskap: himmel + sol + berg + kulle --------------
        sky_bottom = card[1] + int((card[3] - card[1]) * 0.45)
        draw.rectangle([card[0], card[1], card[2], sky_bottom],
                       fill=self.COLOR_ICON_SKY)

        # Sol
        sc = (int(card[0] + (card[2] - card[0]) * 0.66),
              int(card[1] + (card[3] - card[1]) * 0.24))
        sr = max(2, int(W * 0.045))
        draw.ellipse([sc[0] - sr, sc[1] - sr, sc[0] + sr, sc[1] + sr],
                     fill=self.COLOR_ICON_SUN)

        # Berg
        base_y = card[3]
        draw.polygon([
            (card[0] + 1, base_y),
            (int(card[0] + (card[2] - card[0]) * 0.30),
             int(card[1] + (card[3] - card[1]) * 0.30)),
            (int(card[0] + (card[2] - card[0]) * 0.62), base_y),
        ], fill=self.COLOR_ICON_MTN_L)
        draw.polygon([
            (int(card[0] + (card[2] - card[0]) * 0.35), base_y),
            (int(card[0] + (card[2] - card[0]) * 0.66),
             int(card[1] + (card[3] - card[1]) * 0.18)),
            (card[2], base_y),
        ], fill=self.COLOR_ICON_MTN_D)

        # Gron kulle
        draw.pieslice(
            [card[0] - 2, int(card[1] + (card[3] - card[1]) * 0.55),
             card[2] + 2, card[3] + int(H * 0.2)],
            180, 360, fill=self.COLOR_ICON_HILL
        )

        # -- Badge: gron cirkel + vit pil upp --------------------
        bc = (int(W * 0.74), int(H * 0.66))
        br = max(6, int(W * 0.155))
        # vit ring for separation
        draw.ellipse([bc[0] - br - 1, bc[1] - br - 1,
                      bc[0] + br + 1, bc[1] + br + 1],
                     fill=self.COLOR_ICON_WHITE)
        draw.ellipse([bc[0] - br, bc[1] - br,
                      bc[0] + br, bc[1] + br],
                     fill=self.COLOR_ICON_GREEN)
        # pil upp
        ah = max(4, int(W * 0.10))
        aw = max(4, int(W * 0.075))
        draw.polygon([
            (bc[0] - aw, bc[1]),
            (bc[0] + aw, bc[1]),
            (bc[0], bc[1] - ah),
        ], fill=self.COLOR_ICON_WHITE)
        draw.rectangle([
            bc[0] - max(2, int(W * 0.035)), bc[1],
            bc[0] + max(2, int(W * 0.035)), bc[1] + max(4, int(W * 0.07))
        ], fill=self.COLOR_ICON_WHITE)

        return img

    # ==========================================================================
    # TRAY - STARTA / STOPPA
    # ==========================================================================

    def _start_tray(self) -> None:
        """Skapa och starta systray-ikon i bakgrundstrad."""
        if not TRAY_AVAILABLE or self._tray_running:
            return
        try:
            icon_image = self._load_icon_image()
            menu       = self._build_tray_menu()

            self.tray_icon = Icon(
                name="gallery_uploader",
                icon=icon_image,
                title="Gallery Uploader",
                menu=menu,
            )

            self._tray_thread = threading.Thread(
                target=self._tray_loop,
                daemon=True,
                name="SystemTrayThread",
            )
            self._tray_thread.start()
            self._tray_running = True
            self.log(
                "INFO",
                "Systray-ikon startad (ikonkalla: %s)"
                % self._icon_source,
            )
            # P14-10: bekrafta att ikonen verkligen blev synlig
            self._schedule_visibility_check()
        except Exception as e:
            self.log_error("Kunde inte starta systray", e)
            self.app.after(0, self.app.show_window)

    def _schedule_visibility_check(self, attempt: int = 1) -> None:
        """
        Bekrafta att tray-ikonen verkligen blev synlig (P14-10).

        pystray kan returnera utan undantag men anda aldrig visa ikonen:
        Win32 Shell_NotifyIcon kan misslyckas tyst, Windows 11 lagger nya
        ikoner i overflowmenyn och en trasig ikonbild ger ingen ikon.
        Kombinerat med start_minimized=True blir appen da OSYNLIG -
        inget fonster och inget att klicka pa.

        Pollar tray_icon.visible var 500:e ms i upp till 5 sekunder via
        app.after() (UI-traden). Utfall:
          - synlig  -> loggas som OK
          - osynlig efter 5 s -> FEL-rad ("SYSTRAY OSYNLIG") + fönstret
            visas automatiskt sa att appen alltid ar nubar

        Parametrar:
            attempt: pollningsnummer (1-10)
        """
        if not self._tray_running or self.tray_icon is None:
            return
        try:
            if self.tray_icon.visible:
                self._tray_visible = True
                self.log("OK", "Systray-ikon synlig i systemfaltet")
                return
        except Exception:
            pass

        if attempt >= 10:   # 10 x 500 ms = 5 s
            self.log_error(
                "SYSTRAY OSYNLIG: tray-ikonen blev aldrig synlig inom 5 s "
                "(ikonkalla: %s). Visar fönstret i stallet sa att appen "
                "ar nubar." % self._icon_source
            )
            try:
                self.app.after(0, self.app.show_window)
            except Exception:
                pass
            return

        try:
            self.app.after(
                500,
                lambda a=attempt + 1: self._schedule_visibility_check(a),
            )
        except Exception:
            pass

    def _claim_systray_ownership(self) -> None:
        """
        Se till att appen har EXAKT EN tray-ikon (P14-13).

        Kors via after() eftersom main.pyw:s steg 15 (_start_systray)
        da redan kort: dess dubblettskydd kontrollerar bara sitt eget
        _systray_mgr-attribut (None vid plugin-laddning) och skapar
        darfor en andra helpers.SystrayManager med egen pystray-ikon.

        Har stoppas den dubbla managern och pluginen registrerar sig
        som app._systray_mgr - attributet som main.pyw anvander vid
        reload och avslut (endast .start()/.stop() anropas, bada finns
        publikt i denna klass).
        """
        try:
            mgr = getattr(self.app, "_systray_mgr", None)
            if mgr is not None and mgr is not self:
                try:
                    mgr.stop()
                except Exception:
                    pass
                self.log(
                    "DEBUG",
                    "Stoppade main.pyw:s dubbla SystrayManager "
                    "(ENDAST EN ikon)"
                )
            self.app._systray_mgr = self
        except Exception:
            pass

    def start(self) -> None:
        """
        Publik start (main.pyw-kontrakt). Idempotent.

        Om tray-traden redan kors gor denna metod ingenting - det är
        viktigt att ett reload/anrop inte skapar en andra ikon.
        """
        if self._tray_running:
            return
        if TRAY_AVAILABLE and not IS_WAYLAND:
            self._start_tray()

    def stop(self) -> None:
        """Publik stopp (main.pyw-kontrakt vid reload och avslut)."""
        self._stop_tray()

    def _tray_loop(self) -> None:
        """
        Kor systray-loop (bakgrundstrad).

        Heter _tray_loop (inte _tray_run) for att undvika
        namnkonflikt med trad-metodnamn.
        """
        try:
            if self.tray_icon:
                self.tray_icon.run()
        except Exception as e:
            self.log_error("Systray kraschade", e)
            self._tray_running = False
            self._tray_visible = False   # P14-12
            try:
                self.app.after(0, self.app.show_window)
            except Exception:
                pass

    def _stop_tray(self) -> None:
        """Stoppa systray-ikon."""
        self._tray_running = False
        self._tray_visible = False
        if self.tray_icon:
            try:
                self.tray_icon.stop()
            except Exception:
                pass
            self.tray_icon = None

    # ==========================================================================
    # TRAY - MENY (inkl. Tema-undermeny, A7)
    # ==========================================================================

    def _current_theme(self) -> str:
        """Returnera aktuellt tema-val (settings.theme)."""
        try:
            settings = getattr(self.app, "settings", {}) or {}
            return settings.get("theme", "system")
        except Exception:
            return "system"

    def _set_theme(self, theme: str) -> None:
        """Byt tema tradsakert via after() -> app.apply_theme()."""
        try:
            self.app.after(0, lambda: self.app.apply_theme(theme))
        except Exception:
            pass

    def _on_theme_light(self, icon=None, item=None) -> None:
        """Byt till ljust tema (A7)."""
        self._set_theme("light")

    def _on_theme_dark(self, icon=None, item=None) -> None:
        """Byt till morkt tema (A7)."""
        self._set_theme("dark")

    def _on_theme_system(self, icon=None, item=None) -> None:
        """Byt till system-tema (A7)."""
        self._set_theme("system")

    def _build_tray_menu(self):
        """Bygg systray-hogerklicksmeny (inkl. Tema-undermeny, A7)."""
        tema_menu = Menu(
            MenuItem(
                "Ljust",
                self._on_theme_light,
                checked=lambda item: self._current_theme() == "light",
                radio=True,
            ),
            MenuItem(
                "Mörkt",
                self._on_theme_dark,
                checked=lambda item: self._current_theme() == "dark",
                radio=True,
            ),
            MenuItem(
                "System",
                self._on_theme_system,
                checked=lambda item: self._current_theme() == "system",
                radio=True,
            ),
        )

        return Menu(
            MenuItem(
                "Visa Gallery Uploader",
                self._tray_show,
                default=True,     # Enkelklick -> visa
            ),
            Menu.SEPARATOR,
            MenuItem("Kor pipeline",        self._tray_run_pipeline),
            Menu.SEPARATOR,
            MenuItem("Tema",                tema_menu),
            MenuItem("Installningar",        self._tray_show_settings),
            MenuItem("Tray-installningar",   self._tray_show_tray_settings),
            Menu.SEPARATOR,
            MenuItem("Avsluta",              self._tray_quit),
        )

    def _tray_show(self, icon=None, item=None) -> None:
        """Visa fonstret (systemtray-klick)."""
        try:
            self.app.after(0, self.app.show_window)
        except Exception:
            pass

    def _tray_run_pipeline(self, icon=None, item=None) -> None:
        """Kor pipeline fran systray."""
        def _run():
            self.app.show_window()
            ctrl = self.app.context.get("_controls")
            if ctrl and hasattr(ctrl, "run_generate"):
                ctrl.run_generate()
            else:
                self.app._run_pipeline_safe()
        try:
            self.app.after(0, _run)
        except Exception:
            pass

    def _tray_show_settings(self, icon=None, item=None) -> None:
        """Navigera till installningar-tabben."""
        def _show():
            self.app.show_window()
            tm = self.app.context.get("_tab_manager")
            if tm and hasattr(tm, "select_tab"):
                try:
                    tm.select_tab("settings")
                except Exception:
                    pass
        try:
            self.app.after(0, _show)
        except Exception:
            pass

    def _tray_show_tray_settings(self, icon=None, item=None) -> None:
        """Oppna tray-installningsdialog."""
        try:
            self.app.after(0, self.show_settings_dialog)
        except Exception:
            pass

    def _tray_quit(self, icon=None, item=None) -> None:
        """Avsluta applikationen fran systray."""
        try:
            self.app.after(0, self.app.quit_app)
        except Exception:
            pass

    # ==========================================================================
    # MINIMERA / VISA
    # ==========================================================================

    def minimize_to_tray(self) -> None:
        """
        Minimera till systray.
        Fallback till iconify() om systray ej ar tillgangligt.
        """
        if not TRAY_AVAILABLE or not self.tray_icon or not self._tray_running:
            try:
                self.app.iconify()
            except Exception:
                pass
            return

        try:
            self.app.hide_to_tray()
        except AttributeError:
            try:
                self.app.withdraw()
            except Exception:
                pass

        if self.settings.get("show_notifications", True):
            self._notify(
                "Gallery Uploader",
                "Kors i bakgrunden. Klicka ikonen for att oppna."
            )

    def _notify(self, title: str, message: str) -> None:
        """Skicka systray-notifikation."""
        if self.tray_icon and TRAY_AVAILABLE:
            try:
                self.tray_icon.notify(message, title)
            except Exception:
                pass

    # ==========================================================================
    # EVENTS
    # ==========================================================================

    def _on_window_close(self) -> None:
        """
        X-knappen klickad.

        Beteende:
          - pystray tillganglig + close_to_tray=True -> minimera till tray
          - Annars -> bekraftelsedialog
        """
        if (
            TRAY_AVAILABLE
            and self.settings.get("close_to_tray", True)
            and self._tray_running
            and not IS_WAYLAND
        ):
            self.minimize_to_tray()
        else:
            if messagebox.askyesno(
                "Avsluta",
                "Vill du avsluta Gallery Uploader?"
            ):
                self.app.quit_app()
            else:
                try:
                    self.app.iconify()
                except Exception:
                    pass

    def _on_unmap(self, event) -> None:
        """
        Fonster doljs (minimeras till aktivitetsfaltet).
        Minimera till systray om installt.
        """
        if event.widget != self.app:
            return
        if not TRAY_AVAILABLE or not self._tray_running or IS_WAYLAND:
            return
        if not self.settings.get("minimize_to_tray", True):
            return
        self.app.after(200, self._check_and_minimize)

    def _check_and_minimize(self) -> None:
        """Minimera till tray om fonstret ar i iconic-state."""
        try:
            if self.app.state() == "iconic":
                self.minimize_to_tray()
        except Exception:
            pass

    # ==========================================================================
    # AUTOSTART (Windows)
    # ==========================================================================

    def is_autostart_enabled(self) -> bool:
        """Kontrollera om autostart ar aktiverat i Windows-registret."""
        if not AUTOSTART_AVAILABLE:
            return False
        try:
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER, AUTOSTART_KEY,
                0, winreg.KEY_READ
            )
            try:
                winreg.QueryValueEx(key, AUTOSTART_NAME)
                return True
            except FileNotFoundError:
                return False
            finally:
                winreg.CloseKey(key)
        except Exception as e:
            self.log("DEBUG", "is_autostart_enabled: %s" % e)
            return False

    def set_autostart(self, enable: bool) -> bool:
        """
        Aktivera/inaktivera autostart via Windows-registret.
        Returnerar True vid lyckat resultat.
        """
        if not AUTOSTART_AVAILABLE:
            messagebox.showwarning(
                "Ej tillganglig", "Autostart kraver Windows."
            )
            return False
        try:
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER, AUTOSTART_KEY,
                0, winreg.KEY_SET_VALUE
            )
            try:
                if enable:
                    cmd = self._build_autostart_command()
                    winreg.SetValueEx(
                        key, AUTOSTART_NAME, 0, winreg.REG_SZ, cmd
                    )
                    self.log("OK", "Autostart aktiverad: %s" % cmd)
                else:
                    try:
                        winreg.DeleteValue(key, AUTOSTART_NAME)
                    except FileNotFoundError:
                        pass
                    self.log("INFO", "Autostart inaktiverad")
                self.settings["start_with_windows"] = enable
                self._save_settings()
                return True
            finally:
                winreg.CloseKey(key)
        except PermissionError:
            messagebox.showerror(
                "Behorighetsfel",
                "Kor som administrator for att andra autostart."
            )
            return False
        except Exception as e:
            self.log_error("Autostart", e)
            return False

    def _build_autostart_command(self) -> str:
        """Bygg kommandostrang for autostart-post i registret."""
        if getattr(sys, "frozen", False):
            cmd = '"%s"' % sys.executable
        else:
            # Startskriptet är main.pyw (v2.6.0-omdöpning). Fallback till
            # main.py om en äldre kopia finns kvar.
            root = Path(__file__).parent.parent
            script = root / "main.pyw"
            if not script.exists():
                script = root / "main.py"
            cmd    = '"%s" "%s"' % (sys.executable, script.resolve())
        if self.settings.get("start_minimized", False):
            cmd += " --minimized"
        return cmd

    # ==========================================================================
    # INSTALLNINGSDIALOG
    # ==========================================================================

    def show_settings_dialog(self) -> None:
        """Visa installningsdialog for systray."""
        dlg = tk.Toplevel(self.app)
        dlg.title("System Tray - Installningar")
        dlg.geometry("480x440")
        dlg.configure(bg=self.COLOR_BG)
        dlg.transient(self.app)
        dlg.grab_set()
        dlg.resizable(False, False)
        self._reg_panels(dlg)

        # Centrera over huvudfonstret
        try:
            dlg.update_idletasks()
            ax, ay = self.app.winfo_x(), self.app.winfo_y()
            aw, ah = self.app.winfo_width(), self.app.winfo_height()
            dlg.geometry(
                "+%d+%d" % (ax + (aw - 480) // 2, ay + (ah - 440) // 2)
            )
        except Exception:
            pass

        # Header (accent-bakgrund - hanteras separat i _restyle_all)
        hdr = tk.Frame(dlg, bg=self.COLOR_BG_BLUE, height=50)
        hdr.pack(fill=tk.X)
        hdr.pack_propagate(False)
        self._dlg_hdr = hdr
        self._dlg_hdr_lbl = tk.Label(
            hdr, text="System Tray",
            bg=self.COLOR_BG_BLUE, fg=self.COLOR_WHITE,
            font=("Segoe UI", 13, "bold"),
        )
        self._dlg_hdr_lbl.pack(expand=True)

        body = ttk.Frame(dlg, padding=16)
        body.pack(fill=tk.BOTH, expand=True)

        # -- Systray-sektion -----------------------------------
        tray_lf = ttk.LabelFrame(body, text=" Systray ", padding=10)
        tray_lf.pack(fill=tk.X, pady=(0, 10))

        if TRAY_AVAILABLE and not IS_WAYLAND:
            minimize_var = tk.BooleanVar(
                value=self.settings.get("minimize_to_tray", True)
            )
            close_var = tk.BooleanVar(
                value=self.settings.get("close_to_tray", True)
            )
            notify_var = tk.BooleanVar(
                value=self.settings.get("show_notifications", True)
            )
            for var, txt in [
                (minimize_var, "Minimera till tray (Ctrl+M)"),
                (close_var,    "X-knappen minimerar (stanger inte)"),
                (notify_var,   "Visa notifikationer"),
            ]:
                ttk.Checkbutton(tray_lf, text=txt, variable=var).pack(
                    anchor=tk.W, pady=2
                )
        elif IS_WAYLAND:
            self._mk_label(
                tray_lf,
                "! Wayland - systray ej tillgangligt\n"
                "Fonstret visas direkt vid start.",
                "COLOR_WARNING",
                pack={"anchor": tk.W},
            )
        else:
            self._mk_label(
                tray_lf,
                "! pystray saknas\npip install pystray Pillow",
                "COLOR_ERROR",
                pack={"anchor": tk.W},
            )

        # -- Autostart-sektion ---------------------------------
        auto_lf = ttk.LabelFrame(
            body, text=" Autostart (Windows) ", padding=10
        )
        auto_lf.pack(fill=tk.X, pady=(0, 10))

        current_auto = self.is_autostart_enabled()

        if AUTOSTART_AVAILABLE:
            autostart_var = tk.BooleanVar(value=current_auto)
            start_min_var = tk.BooleanVar(
                value=self.settings.get("start_minimized", False)
            )
            ttk.Checkbutton(
                auto_lf, text="Starta med Windows",
                variable=autostart_var,
            ).pack(anchor=tk.W, pady=2)
            ttk.Checkbutton(
                auto_lf, text="Starta minimerad",
                variable=start_min_var,
            ).pack(anchor=tk.W, pady=2)
        else:
            self._mk_label(
                auto_lf,
                "Endast tillganglig pa Windows",
                "COLOR_GRAY",
                pack={"anchor": tk.W},
            )

        # -- Knappar -------------------------------------------
        btn_row = ttk.Frame(dlg, padding=(16, 0, 16, 16))
        btn_row.pack(fill=tk.X)

        def _save():
            if TRAY_AVAILABLE and not IS_WAYLAND:
                self.settings["minimize_to_tray"]   = minimize_var.get()
                self.settings["close_to_tray"]      = close_var.get()
                self.settings["show_notifications"] = notify_var.get()
            if AUTOSTART_AVAILABLE:
                new_auto = autostart_var.get()
                self.settings["start_minimized"] = start_min_var.get()
                if new_auto != current_auto:
                    self.set_autostart(new_auto)
            self._save_settings()
            dlg.destroy()

        self._make_button(btn_row, "Spara", _save,
                          bg="COLOR_SUCCESS", side=tk.LEFT)
        self._make_button(btn_row, "Avbryt", dlg.destroy,
                          bg="COLOR_GRAY", side=tk.LEFT)

        if TRAY_AVAILABLE and self._tray_running and not IS_WAYLAND:
            self._make_button(
                btn_row, "Minimera nu",
                lambda: (dlg.destroy(), self.minimize_to_tray()),
                bg="COLOR_BG_BLUE", side=tk.RIGHT,
            )

    def _make_button(
        self, parent, text, command, bg="COLOR_DARK", side=tk.LEFT
    ) -> tk.Button:
        """
        Skapa en knapp med hover-effekt.

        bg ar ATTRIBUTNAMN (strang) - vardet hamtas via getattr()
        sa att knappen foljer aktuella tema-farger och registreras
        for omstyling vid tema-byte (C1).
        """
        bg_value = getattr(self, bg, "#4b5563")
        darker   = self._darken(bg_value)

        def _resolved():
            # Q2: los aktuell tema-farg dynamiskt sa att hover/leave
            # alltid foljer nyaste temat (annars fastnar gamla bygg-farger).
            c = getattr(self, bg, "#4b5563")
            return c, self._darken(c)

        btn = tk.Button(
            parent, text=text, command=command,
            bg=bg_value, fg=self.COLOR_WHITE,
            font=("Segoe UI", 9, "bold"),
            relief="flat", cursor="hand2",
            activebackground=darker,
            activeforeground=self.COLOR_WHITE,
            padx=12, pady=5,
        )
        btn.pack(side=side, padx=4, pady=2)
        btn.bind("<Enter>", lambda e: btn.config(bg=_resolved()[1]))
        btn.bind("<Leave>", lambda e: btn.config(bg=_resolved()[0]))
        self._buttons.append((btn, bg))
        return btn

    @staticmethod
    def _darken(hex_color: str, factor: float = 0.80) -> str:
        """Morkna hex-farg for hover-effekt."""
        try:
            h = hex_color.lstrip("#")
            r = int(int(h[0:2], 16) * factor)
            g = int(int(h[2:4], 16) * factor)
            b = int(int(h[4:6], 16) * factor)
            return "#%02x%02x%02x" % (r, g, b)
        except Exception:
            return hex_color

    # ==========================================================================
    # JSON
    # ==========================================================================

    def _load_settings(self) -> dict:
        """Ladda installningar - med DEFAULTS som fallback."""
        data  = self.DEFAULTS.copy()
        saved = self.load_config("system_tray.json", default={})
        data.update(saved)
        return data

    def _save_settings(self) -> None:
        """Spara installningar atomiskt."""
        self.save_config("system_tray.json", self.settings)

    # ==========================================================================
    # PIPELINE
    # ==========================================================================

    def execute(self, context: dict, log=None) -> dict:
        """Pipeline-passthrough - returnerar context oforandrad."""
        return context

    def cleanup(self) -> None:
        """Stoppa systray vid avslutning."""
        self._stop_tray()
        super().cleanup()

    # ==========================================================================
    # INTERN LOGGNING OCH CONFIG
    # ==========================================================================

    def log(self, level: str, message: str) -> None:
        """
        Logga via advanced_logger om tillganglig.
        Fallback: tyst (ingen print/stderr).
        """
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
        Ladda JSON-fil fran config/-mappen (A10).

        Anvander helpers.get_config_path() om tillgangligt,
        annars projektrotens config/.
        """
        try:
            if _HAS_HELPERS:
                cfg = get_config_path() / filename
            else:
                cfg = Path(__file__).parent.parent / "config" / filename
            if cfg.exists():
                return json.loads(cfg.read_text(encoding="utf-8"))
        except Exception as e:
            self.log("DEBUG", "load_config(%s): %s" % (filename, e))
        return default if default is not None else {}

    def save_config(self, filename: str, data: dict) -> None:
        """
        Spara JSON-fil till config/-mappen (A9 + A10).

        Monster: mkstemp -> fdopen -> flush -> fsync -> os.replace.
        """
        tmp_path = None
        try:
            if _HAS_HELPERS:
                config_dir = get_config_path()
            else:
                config_dir = Path(__file__).parent.parent / "config"
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
