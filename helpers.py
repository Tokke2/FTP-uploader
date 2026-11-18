#!/usr/bin/env python3
# ============================================================
# Gallery Uploader - Hjalpmodul
# ============================================================
# FIL:       helpers.py
# PLATS:     projektrot (ftp_gallery_uploader/)
# Syfte:     Alla hjalpklasser och funktioner som main.pyw
#            importerar. Haller main.pyw hanterbar.
# VERSION:   1.8.1
# AUTHOR:    Rickard Längkvist
# COPYRIGHT: Copyright (c) <år> Rickard Längkvist (dynamiskt år,
#            se COPYRIGHT-konstanten nedan)
#
# ÄNDRINGAR v1.5.0 → v1.6.0 (kanonisk ikonmapp icon/):
#   [I1]      get_icon_path() -> icon/ (skapas vid behov).
#   [I2]      resolve_icon_file(): sokordning icon/ sedan assets/.
#             Filer: icon.ico, icon.png, icon_16/32/64/256.png.
#   [I3]      load_app_icon(prefer_size): PIL-bild for systray.
#   [I4]      apply_tk_window_icon(window): fonster + aktivitetsfalt
#             (.ico pa Windows, PNG-storlekar via iconphoto overallt).
#             Fallback: generate_app_icon() om icon/ saknas.
#   SystrayManager._load_icon anvander load_app_icon (64 px).
#
# ÄNDRINGAR v1.4.0 → v1.5.0 (startdiagnostik, icke-brytande):
#   [L]       Ny startlogg i logs/startup.log: reset_startup_log(),
#             log_startup(), log_startup_exc(), log_startup_crash().
#             REN kronologisk logg (nollställs per process) som
#             dokumenterar hela startkedjan och fönster-visnings-
#             besluten. Logiken ligger HÄR sa att main.pyw inte sväller.
#
# ÄNDRINGAR v1.3.0 → v1.4.0 (snabbhet + minne + konsistens, icke-brytande):
#   [P]       ThemeEngine.apply(): early-return vid oförändrat tema – hela
#             ttk.Style-omstylingen hoppas över om samma tema redan
#             applicerats (stor vinst vid reload + upprepade apply()).
#   [P]       get_system_theme(): TTL-cache (5 s) så att upprepade anrop
#             inte kör subprocess/registry varje gång (t.ex. vid reload).
#   [P]       get_colors()/design-hjälpmetoder: bygger färg-dicts en gång
#             per tema och cachar dem (förstörs i apply()), i stället för
#             att kopiera/bygga om på varje hot-path-anrop.
#   [C2]      Ikon-generering konsoliderad: ny modul-funktion
#             generate_app_icon(size) – SystrayManager._generate_icon()
#             och main.py:s fönster-ikon delar SAMMA designkälla
#             (tidigare duplicerad/omvägt via temporära instanser).
#   [K]       Inga API-namn ändras; alla publika klasser/funktioner
#             behåller sina signaturer (bakatkompatibilitet).
#
# ÄNDRINGAR v1.8.0 → v1.8.1:
#   Temabyte restylar befintliga tk-widgets (Frame/Label/Text/Menu),
#   inte bara ttk.Entry. Palett-hex mappas nyckelvis dark<->light.
#
# ÄNDRINGAR v1.2.0 → v1.3.0: ThemeEngine 38 nycklar, DARK midnight /
#   LIGHT gallery, option_add for menyer, get_accent_gradient /
#   get_glass_colors / get_widget_colors.
#
# BEVARAT FRÅN v1.2.0:
#   Inga f-strings (B1), atomisk save_json med fsync (A9),
#   get_logs_path (A10), SystrayManager med Tema-meny (A7) +
#   fallback-ikon i appens design (C2), SingleInstanceLock
#   SO_REUSEADDR=0, WindowStateManager bounds, TabVisibilityManager,
#   get_system_theme (darkdetect/registry/GTK),
#   ThemeEngine StyleEngine-kontrakt (get_theme/set_mode/current).
#   ALLA gamla fargnycklar (bg, fg, button_bg, tab_bg, tree_*,
#   scroll_*, menu_*) finns KVAR for bakatkompatibilitet.
#
# INNEHALL:
#   safe_print()             - Kraschsaker utskrift
#   load_json()              - Ladda JSON-fil med fallback
#   save_json()              - Spara JSON atomiskt (A9: +fsync)
#   get_base_path()          - Projektrotens Path
#   get_assets_path()        - assets/-mappens Path
#   get_config_path()        - config/-mappens Path
#   get_logs_path()          - logs/-mappens Path (A10)
#   bind_mousewheel()        - Bind mushjul till widget
#   get_system_theme()       - Detektera OS-tema (dark/light)
#   SingleInstanceLock       - Socket-baserad instanslas
#   SystrayManager           - pystray-wrapper (A7: Tema-meny)
#   ThemeEngine              - DESIGN-SYSTEM (38 nycklar/tema)
#   TabVisibilityManager     - Spara/ladda tabb-synlighet
#   WindowStateManager       - Spara/ladda fonsterposition
#
# IMPORTER:
#   tkinter as tk, ttk
#   json, os, sys, socket, threading, platform
#   tempfile, re
#   pathlib.Path
# ============================================================

import app_paths
import tkinter as tk
from tkinter import ttk
import json
import os
import sys
import socket
import threading
import platform
import tempfile
import re
import time
from pathlib import Path
from datetime import datetime

from app_icon import (
    get_icon_path,
    resolve_icon_file,
    load_app_icon,
    apply_tk_window_icon,
)

# ==============================================================================
# MODULKONSTANTER (B3)
# ==============================================================================

VERSION   = "1.8.1"
AUTHOR    = "Rickard Längkvist"
COPYRIGHT = "Copyright (c) %d %s" % (datetime.now().year, AUTHOR)

_BASE = Path(__file__).resolve().parent

# ==============================================================================
# INTERN LOGGNING (ingen print/stderr direkt – B1)
# ==============================================================================

def safe_print(message: str) -> None:
    """
    Skriv ett meddelande utan att krascha om stderr ar stangd.

    Forsoker i ordning:
      1. sys.stderr
      2. sys.__stderr__
      3. logs/helpers_errors.log (sista utvag, under projektroten)
    """
    for stream in (sys.stderr, sys.__stderr__):
        try:
            if stream and hasattr(stream, "write"):
                stream.write("%s\n" % message)
                stream.flush()
                return
        except (OSError, AttributeError):
            continue
    try:
        log_dir = app_paths.logs_dir()
        log_dir.mkdir(exist_ok=True)
        with open(log_dir / "helpers_errors.log", "a", encoding="utf-8") as f:
            from log_clock import timestamp
            f.write("[%s] %s\n" % (timestamp(), message))
    except Exception:
        pass


# ==============================================================================
# SOKVAGAR
# ==============================================================================

def get_base_path() -> Path:
    """
    Returnera projektrotens Path (mappen med main.pyw).

    PORT-1: foljer appmappen, aven pa USB/ny disk. Aldrig D:\\ hardkodat.
    PyInstaller: katalogen dar .exe ligger (inte _MEIPASS-temp).
    """
    if getattr(sys, "frozen", False):
        try:
            return Path(sys.executable).resolve().parent
        except Exception:
            return Path(getattr(sys, "_MEIPASS", ".")).resolve()
    return Path(__file__).parent.resolve()


def to_app_rel(path) -> str:
    """Spara sokvag relativ projektroten (posix), annars namnet."""
    try:
        p = Path(path).resolve()
        base = get_base_path().resolve()
        rel = p.relative_to(base)
        return rel.as_posix()
    except Exception:
        try:
            return Path(path).as_posix()
        except Exception:
            return str(path or "")


def from_app_rel(s):
    """
    Las sokvag: relativ mot appen, eller gammal absolut som pekas
    om till out/<namn>/ om originaldisken saknas.
    """
    if not s:
        return None
    try:
        p = Path(s)
    except Exception:
        return None
    try:
        if p.is_absolute() and p.exists():
            return p
    except Exception:
        pass
    base = get_base_path()
    try:
        cand = (base / p) if not p.is_absolute() else p
        if cand.exists():
            return cand
    except Exception:
        pass
    name = p.name
    if name:
        for cand in (
            base / "out" / name,
            base / "out" / name / "image",
        ):
            try:
                if cand.is_dir():
                    return cand
            except Exception:
                continue
    try:
        return (base / p) if not p.is_absolute() else p
    except Exception:
        return p


def get_config_path() -> Path:
    """Returnera config/-mappens Path. Skapar mappen om den saknas."""
    p = app_paths.config_dir()
    p.mkdir(parents=True, exist_ok=True)
    return p


def get_assets_path() -> Path:
    """Returnera assets/-mappens Path."""
    return get_base_path() / "assets"


def get_logs_path() -> Path:
    """Returnera logs/-mappens Path. Skapar mappen om den saknas (A10)."""
    p = app_paths.logs_dir()
    p.mkdir(parents=True, exist_ok=True)
    return p


# ==============================================================================
# STARTUPLOGG (v2.7.0 – "klistra in och se problemet direkt")
# ==============================================================================
# En REN, kronologisk logg i logs/startup.log som nollställs vid varje ny
# process. Används av main.pyw för att dokumentera hela startkedjan och det
# exakta beslutet om fönstret visas/döljs. Logiken ligger HÄR (helpers) så
# att main.pyw hålls under 1800 rader.

_STARTUP_LOGFILE = None  # sätts av reset_startup_log()


def reset_startup_log() -> None:
    """Börja om logs/startup.log för DENNA körning."""
    global _STARTUP_LOGFILE
    try:
        logs = get_logs_path()
        _STARTUP_LOGFILE = logs / "startup.log"
        # Daily startup compaction has preserved today's earlier sessions.
        with open(_STARTUP_LOGFILE, "a", encoding="utf-8") as f:
            f.write(
                "\n# FTP-Galleri – startlogg (dagens körningar)\n"
                "# Start:      %s\n"
                "# Python:     %s\n"
                "# Plattform:  %s (pid %d)\n"
                "# argv:       %s\n"
                "# ============================================================\n"
                % (
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    getattr(sys, "version", "?").split()[0],
                    sys.platform,
                    os.getpid(),
                    " ".join(sys.argv),
                )
            )
    except Exception:
        pass


def _startup_target() -> Path:
    """Returnera den aktiva startup.log-sökvägen (skapar logs/)."""
    global _STARTUP_LOGFILE
    if _STARTUP_LOGFILE is None:
        _STARTUP_LOGFILE = get_logs_path() / "startup.log"
    return _STARTUP_LOGFILE


def log_startup(step: str, detail: str = "") -> None:
    """
    Skriv en tidsstämplad rad till logs/startup.log (aldrig print).

    step   – fasnamn (t.ex. "13. Tema").
    detail – frivillig kontext (inställning, beslut, sökväg).
    Fel kan aldrig krascha starten (helt passiv).
    """
    try:
        line = "[%s] %s" % (
            datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3], step,
        )
        if detail:
            line += " | " + detail
        with open(_startup_target(), "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass


def log_startup_exc(step: str, exc) -> None:
    """Logga ett undantag i startkedjan (typ + meddelande)."""
    try:
        log_startup(step, "FEL: %s: %s" % (type(exc).__name__, exc))
    except Exception:
        pass


def log_startup_crash(traceback_text: str) -> None:
    """Spegla en global krasch (flerradig traceback) i startup.log."""
    try:
        with open(_startup_target(), "a", encoding="utf-8") as f:
            f.write(
                "\n[%s] KRASCH:\n%s%s\n"
                % (
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    traceback_text,
                    "=" * 60,
                )
            )
    except Exception:
        pass



# ==============================================================================
# JSON-HANTERING
# ==============================================================================

def load_json(path: Path, default=None):
    """
    Ladda en JSON-fil.

    Parametrar:
        path:    Path till filen
        default: Varde att returnera om filen saknas eller ar korrupt
                 (standard: {})

    Returnerar:
        Parsad data, eller default vid fel.
        Loggar fel via safe_print (ingen raise).
    """
    if default is None:
        default = {}
    try:
        if path.exists():
            text = path.read_text(encoding="utf-8")
            if text.strip():
                return json.loads(text)
    except json.JSONDecodeError as e:
        safe_print("[helpers] load_json: ogiltig JSON (%s): %s" % (path.name, e))
    except PermissionError as e:
        safe_print("[helpers] load_json: behorighetsfel (%s): %s" % (path.name, e))
    except OSError as e:
        safe_print("[helpers] load_json: I/O-fel (%s): %s" % (path.name, e))
    except Exception as e:
        safe_print("[helpers] load_json: ovantat fel (%s): %s" % (path.name, e))
    return default


def save_json(path: Path, data) -> bool:
    """
    Spara data till JSON-fil atomiskt (A9: fsync-starkt monster).

    Atomisk skrivning skyddar mot korruption vid krasch.
    Monster: tempfile.mkstemp -> os.fdopen -> flush -> fsync ->
             os.replace.
    Skapar foraldrakataloger automatiskt.
    Stadar upp .tmp-fil vid fel.

    Parametrar:
        path: Path till malfilen
        data: Python-objekt (dict, list, etc.)

    Returnerar:
        True vid lyckat sparande, False vid fel.
    """
    tmp_path = None
    try:
        path.parent.mkdir(parents=True, exist_ok=True)

        fd, tmp_str = tempfile.mkstemp(
            dir=path.parent,
            prefix=".%s_" % path.stem,
            suffix=".tmp",
        )
        tmp_path = Path(tmp_str)

        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.flush()
            os.fsync(f.fileno())   # A9: säkerställ att data nått disken

        os.replace(tmp_path, path)
        return True

    except Exception as e:
        safe_print("[helpers] save_json: fel (%s): %s" % (path.name, e))
        if tmp_path and tmp_path.exists():
            try:
                tmp_path.unlink()
            except OSError:
                pass
        return False


# ==============================================================================
# MUSHJUL
# ==============================================================================

def bind_mousewheel(
    widget: tk.Widget,
    callback=None,
    units: int = 3,
) -> None:
    """
    Bind mushjuls-scroll till en specifik widget.

    Fungerar pa Windows, Mac och Linux.
    Hanterar <MouseWheel>, <Button-4>, <Button-5>.

    Parametrar:
        widget:   Widgeten att binda
        callback: Valfri callback(event). Om None anvands
                  widget.yview_scroll automatiskt.
        units:    Antal enheter per hjulklick (standard: 3)
    """
    def _scroll(event):
        if callback:
            callback(event)
            return
        try:
            if sys.platform == "darwin":
                widget.yview_scroll(-1 * event.delta, "units")
            elif sys.platform == "win32":
                widget.yview_scroll(
                    -1 * (event.delta // 120) * units, "units"
                )
            else:
                if event.num == 4:
                    widget.yview_scroll(-units, "units")
                else:
                    widget.yview_scroll(units, "units")
        except tk.TclError:
            pass

    widget.bind("<MouseWheel>", _scroll)
    widget.bind("<Button-4>",   _scroll)
    widget.bind("<Button-5>",   _scroll)


# ==============================================================================
# TEMA-DETEKTION
# ==============================================================================

_system_theme_cache = {"value": None, "ts": 0.0}
_SYSTEM_THEME_TTL   = 5.0   # sekunder – OS-temat ändras sällan i en session


def get_system_theme() -> str:
    """
    Detektera om OS kor i morkt eller ljust lage.

    TTL-cache (5 s): upprepade anrop (t.ex. vid plugin-reload) hoppar
    over subprocess/registry-anrop och returnerar senaste resultatet.

    Forsoker i ordning:
      1. darkdetect (pip install darkdetect)
      2. Windows registry
      3. macOS defaults
      4. Linux GTK (gsettings)
      5. Fallback: "dark"

    Returnerar:
        "dark" eller "light"
    """
    now = time.monotonic()
    if (
        _system_theme_cache["value"] is not None
        and (now - _system_theme_cache["ts"]) < _SYSTEM_THEME_TTL
    ):
        return _system_theme_cache["value"]

    result = _detect_system_theme()

    _system_theme_cache["value"] = result
    _system_theme_cache["ts"]    = now
    return result


def _detect_system_theme() -> str:
    """Intern detektering – anropas bara vid cachemiss (get_system_theme)."""
    # 1. darkdetect
    try:
        import darkdetect
        result = darkdetect.theme()
        if result:
            return result.lower()
    except Exception:
        pass

    # 2. Windows registry
    if sys.platform == "win32":
        try:
            import winreg
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize"
            )
            value, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
            winreg.CloseKey(key)
            return "light" if value == 1 else "dark"
        except Exception:
            pass

    # 3. macOS
    if sys.platform == "darwin":
        try:
            import quiet_process as subprocess
            result = subprocess.run(
                ["defaults", "read", "-g", "AppleInterfaceStyle"],
                capture_output=True, text=True, timeout=2
            )
            return "dark" if "Dark" in result.stdout else "light"
        except Exception:
            pass

    # 4. Linux GTK (gsettings)
    if sys.platform == "linux":
        try:
            import quiet_process as subprocess
            result = subprocess.run(
                ["gsettings", "get",
                 "org.gnome.desktop.interface", "color-scheme"],
                capture_output=True, text=True, timeout=2
            )
            if "dark" in result.stdout.lower():
                return "dark"
            if result.returncode == 0:
                return "light"
        except Exception:
            pass

    return "dark"


# ==============================================================================
# SINGLE-INSTANCE LOCK
# ==============================================================================

class SingleInstanceLock:
    """
    Forhindrar att flera instanser av appen kors samtidigt.

    Metod: binder en socket till localhost:port.
    Misslyckas om porten redan ar bunden (annan instans kors).

    OBS: SO_REUSEADDR = 0 (False) ar korrekt for las-syfte.
    Med SO_REUSEADDR = 1 kan nya instanser ta laset fran gamla.

    Anvandning:
        lock = SingleInstanceLock(port=47200)
        if not lock.acquire():
            sys.exit(0)
        # ... korning ...
        lock.release()
    """

    def __init__(self, port: int = 47200):
        self._port   = port
        self._socket = None
        self._held   = False

    def acquire(self) -> bool:
        """
        Forsok att ta laset.

        Returnerar:
            True  - lyckades (denna instans ar ensam)
            False - misslyckades (annan instans kors)
        """
        try:
            self._socket = socket.socket(
                socket.AF_INET, socket.SOCK_STREAM
            )
            # SO_REUSEADDR = 0 = korrekt lock-beteende
            self._socket.setsockopt(
                socket.SOL_SOCKET, socket.SO_REUSEADDR, 0
            )
            self._socket.bind(("127.0.0.1", self._port))
            self._socket.listen(1)
            self._held = True
            return True
        except OSError:
            if self._socket:
                try:
                    self._socket.close()
                except Exception:
                    pass
                self._socket = None
            return False

    def release(self) -> None:
        """Frigor laset vid appavslutning."""
        self._held = False
        if self._socket:
            try:
                self._socket.close()
            except Exception:
                pass
            self._socket = None

    def is_held(self) -> bool:
        """Returnerar True om detta objekt haller laset."""
        return self._held


# ==============================================================================
# TEMA-ENGINE – DESIGN-SYSTEM (38 nycklar per tema)
# ==============================================================================

class ThemeEngine:
    """
    Ljust/morkt design-system (38 nycklar). DARK midnight / LIGHT gallery.
    apply() satter ttk.Style, tk.Tk, menyer och befintliga tk-widgets.
    """

    # -- Tooltip-farger (plugins anvander dessa) ---------------
    COLOR_TOOLTIP_BG = "#1e293b"
    COLOR_TOOLTIP_FG = "#e2e8f0"

    # -- Morkt tema "midnight" (FTP-Galleri: kobolt + smaragd) --
    DARK = {
        # Bas
        "bg":                "#070B14",
        "fg":                "#F3F5FB",
        "surface":           "#101827",
        "surface_alt":       "#162033",
        "bg_secondary":      "#05080F",
        "panel_bg":          "#0C1424",
        "card_bg":           "#121A2C",
        "card_hover":        "#1A2740",
        "input_bg":          "#080D18",
        # Text
        "text":              "#F3F5FB",
        "text_secondary":    "#B8C0D4",
        "muted":             "#8791A8",
        "disabled_fg":       "#5B6578",
        "disabled_bg":       "#121A28",
        "inverse_text":      "#070B14",
        # Knappar (ljusare an bg -> syns tydligt i morkt tema)
        "button_bg":         "#3D4A5C",
        "button_fg":         "#F8FAFC",
        "button_hover":      "#4E5C70",
        "button_active":     "#334050",
        # Tabbar (aktiv = kobolt-mjuk)
        "tab_bg":            "#121A28",
        "tab_fg":            "#9AA6BC",
        "tab_active_bg":     "#153056",
        "tab_active_fg":     "#ffffff",
        # Accent = app-ikon kobolt, success = smaragd-badge
        "accent":            "#4A9EFF",
        "accent_hover":      "#6BB0FF",
        "accent_active":     "#3B82F6",
        "accent_soft":       "#153056",
        "link":              "#7CB8FF",
        # Kanter
        "border":            "#1E2C44",
        "border_soft":       "#162033",
        # Status
        "success":           "#22C55E",
        "warning":           "#F59E0B",
        "error":             "#EF4444",
        "info":              "#38BDF8",
        # Markering / tooltip / glass
        "selection_bg":      "#4A9EFF",
        "selection_fg":      "#ffffff",
        "tooltip_bg":        "#101827",
        "tooltip_fg":        "#F3F5FB",
        "surface_glass":     "#101827",
        # Legacy-nycklar (bakatkompatibilitet)
        "frame_bg":          "#0C1424",
        "label_bg":          "#070B14",
        "label_fg":          "#C5CDDC",
        "entry_bg":          "#080D18",
        "entry_fg":          "#F3F5FB",
        "select_bg":         "#4A9EFF",
        "select_fg":         "#ffffff",
        "tree_bg":           "#070B14",
        "tree_fg":           "#F3F5FB",
        "tree_sel_bg":       "#153056",
        "tree_sel_fg":       "#ffffff",
        "tree_heading_bg":   "#121A28",
        "tree_heading_fg":   "#C5CDDC",
        "scroll_bg":         "#1E2C44",
        "scroll_trough":     "#070B14",
        "menu_bg":           "#101827",
        "menu_fg":           "#F3F5FB",
        "menu_active_bg":    "#4A9EFF",
        "menu_active_fg":    "#ffffff",
    }

    # -- Ljust tema "gallery" (varm pappersvagg, kobolt-accent) -
    LIGHT = {
        # Bas
        "bg":                "#F4F0E8",
        "fg":                "#17150F",
        "surface":           "#FFFdf8",
        "surface_alt":       "#EDE7DC",
        "bg_secondary":      "#E8E2D6",
        "panel_bg":          "#FFFdf8",
        "card_bg":           "#FFFFFF",
        "card_hover":        "#F7F3EC",
        "input_bg":          "#FFFFFF",
        # Text
        "text":              "#17150F",
        "text_secondary":    "#4A453A",
        "muted":             "#6F685C",
        "disabled_fg":       "#B0A898",
        "disabled_bg":       "#E8E2D6",
        "inverse_text":      "#ffffff",
        # Knappar (MORKGRA + SVART text - anvandarens krav)
        "button_bg":         "#6b7280",
        "button_fg":         "#111827",
        "button_hover":      "#7d8694",
        "button_active":     "#5b6472",
        # Tabbar (MORKGRA inaktiva + svart text, aktiv = accent_soft)
        "tab_bg":            "#6b7280",
        "tab_fg":            "#111827",
        "tab_active_bg":     "#D6E4FA",
        "tab_active_fg":     "#0f172a",
        # Accent-gradient
        "accent":            "#1D4ED8",
        "accent_hover":      "#1E40AF",
        "accent_active":     "#1E3A8A",
        "accent_soft":       "#D6E4FA",
        "link":              "#1D4ED8",
        # Kanter
        "border":            "#D4CBBA",
        "border_soft":       "#E8E2D6",
        # Status
        "success":           "#15803D",
        "warning":           "#B45309",
        "error":             "#B91C1C",
        "info":              "#0369A1",
        # Markering / tooltip / glass
        "selection_bg":      "#1D4ED8",
        "selection_fg":      "#ffffff",
        "tooltip_bg":        "#1A1915",
        "tooltip_fg":        "#F4F0E8",
        "surface_glass":     "#FFFdf8",
        # Legacy-nycklar (bakatkompatibilitet)
        "frame_bg":          "#EDE7DC",
        "label_bg":          "#F4F0E8",
        "label_fg":          "#3F3A32",
        "entry_bg":          "#FFFFFF",
        "entry_fg":          "#17150F",
        "select_bg":         "#1D4ED8",
        "select_fg":         "#ffffff",
        "tree_bg":           "#FFFFFF",
        "tree_fg":           "#17150F",
        "tree_sel_bg":       "#D6E4FA",
        "tree_sel_fg":       "#17150F",
        "tree_heading_bg":   "#EDE7DC",
        "tree_heading_fg":   "#3F3A32",
        "scroll_bg":         "#C9C0B0",
        "scroll_trough":     "#EDE7DC",
        "menu_bg":           "#FFFdf8",
        "menu_fg":           "#17150F",
        "menu_active_bg":    "#1D4ED8",
        "menu_active_fg":    "#ffffff",
    }

    def __init__(self, app: tk.Tk):
        self._app      = app
        self._style    = ttk.Style(app)
        self._theme    = "dark"
        self._colors   = self.DARK.copy()
        self.COLOR_TOOLTIP_BG = self._colors["tooltip_bg"]
        self.COLOR_TOOLTIP_FG = self._colors["tooltip_fg"]
        self._applied  = False          # sätts True efter första apply()
        self._gradient_cache = {}       # per-tema design-cache (v1.4.0)

        try:
            self._style.theme_use("clam")
        except tk.TclError:
            pass

    def apply(self, theme_name: str) -> None:
        """
        Applicera tema pa hela applikationen.

        Parametrar:
            theme_name: "dark" eller "light"

        GRA RUTA-FIX:
            TNotebook.background = c["bg"]       <- fonstrets farg
            TNotebook.borderwidth = 0            <- ingen kant
            TNotebook.tabmargins = [0, 0, 0, 0]  <- inga marginaler
        """
        if self._applied and self._theme == theme_name:
            return   # v1.4.0: redan applicerat – hoppa över redundant omstyling

        self._colors = (
            self.DARK.copy() if theme_name == "dark"
            else self.LIGHT.copy()
        )
        self._theme = theme_name
        self.COLOR_TOOLTIP_BG = self._colors["tooltip_bg"]
        self.COLOR_TOOLTIP_FG = self._colors["tooltip_fg"]
        self._gradient_cache = {}     # nytt tema → töm design-cachen
        c = self._colors
        s = self._style
        self._applied = True

        # -- Fonsterbakgrund -----------------------------------
        self._app.configure(bg=c["bg"])

        # -- Generell bas --------------------------------------
        s.configure(".",
            background=c["bg"],
            foreground=c["fg"],
            font=("Segoe UI", 10),
        )

        # -- tk.Menyer (Arkiv/Visa/Kor/Plugins/Hjalp) ----------
        try:
            self._app.option_add("*Menu.background",   c["menu_bg"])
            self._app.option_add("*Menu.foreground",   c["menu_fg"])
            self._app.option_add("*Menu.activeBackground", c["menu_active_bg"])
            self._app.option_add("*Menu.activeForeground", c["menu_active_fg"])
            self._app.option_add("*Menu.selectColor",  c["menu_active_bg"])
            self._app.option_add("*Menu.borderWidth",  0)
            self._app.option_add("*Menu.font",
                                 ("Segoe UI", 10))
        except Exception:
            pass

        # -- Frame ---------------------------------------------
        s.configure("TFrame", background=c["bg"])

        # -- LabelFrame ----------------------------------------
        s.configure("TLabelframe",
            background=c["bg"],
            foreground=c["fg"],
            bordercolor=c["border"],
        )
        s.configure("TLabelframe.Label",
            background=c["bg"],
            foreground=c["fg"],
            font=("Segoe UI", 10, "bold"),
        )

        # -- Label ---------------------------------------------
        s.configure("TLabel",
            background=c["bg"],
            foreground=c["fg"],
            font=("Segoe UI", 10),
        )

        # -- Button --------------------------------------------
        s.configure("TButton",
            background=c["button_bg"],
            foreground=c["button_fg"],
            font=("Segoe UI", 10, "bold"),
            relief="flat",
            padding=(12, 6),
            borderwidth=0,
        )
        s.map("TButton",
            background=[
                ("active",   c["button_hover"]),
                ("pressed",  c["button_active"]),
                ("focus",    c["button_hover"]),
                ("disabled", c["disabled_bg"]),
            ],
            foreground=[
                ("disabled", c["disabled_fg"]),
            ],
        )
        s.configure("Accent.TButton",
            background=c["accent"],
            foreground="#ffffff",
            font=("Segoe UI", 10, "bold"),
            relief="flat",
            padding=(14, 7),
            borderwidth=0,
        )
        s.map("Accent.TButton",
            background=[
                ("active",   c["accent_hover"]),
                ("pressed",  c["accent_active"]),
                ("disabled", c["disabled_bg"]),
            ],
            foreground=[
                ("disabled", c["disabled_fg"]),
            ],
        )
        s.configure("Success.TButton",
            background=c["success"],
            foreground="#ffffff",
            font=("Segoe UI", 10, "bold"),
            relief="flat",
            padding=(14, 7),
            borderwidth=0,
        )
        s.map("Success.TButton",
            background=[
                ("active",   c["success"]),
                ("pressed",  c["success"]),
            ],
        )

        # -- Entry ---------------------------------------------
        s.configure("TEntry",
            fieldbackground=c["entry_bg"],
            foreground=c["entry_fg"],
            insertcolor=c["fg"],
            bordercolor=c["border"],
            lightcolor=c["border_soft"],
            darkcolor=c["border_soft"],
            selectbackground=c["selection_bg"],
            selectforeground=c["selection_fg"],
        )
        s.map("TEntry",
            bordercolor=[
                ("focus", c["accent"]),
            ],
        )

        # -- Combobox ------------------------------------------
        s.configure("TCombobox",
            fieldbackground=c["entry_bg"],
            foreground=c["entry_fg"],
            background=c["button_bg"],
            bordercolor=c["border"],
            arrowcolor=c["text_secondary"],
            selectbackground=c["selection_bg"],
            selectforeground=c["selection_fg"],
        )
        s.map("TCombobox",
            fieldbackground=[("readonly", c["entry_bg"])],
            foreground=[("readonly",      c["entry_fg"])],
            bordercolor=[
                ("focus", c["accent"]),
            ],
        )

        # -- Spinbox -------------------------------------------
        s.configure("TSpinbox",
            fieldbackground=c["entry_bg"],
            foreground=c["entry_fg"],
            background=c["button_bg"],
            bordercolor=c["border"],
            arrowcolor=c["text_secondary"],
        )
        s.map("TSpinbox",
            bordercolor=[
                ("focus", c["accent"]),
            ],
        )

        # -- Menubutton ----------------------------------------
        s.configure("TMenubutton",
            background=c["button_bg"],
            foreground=c["button_fg"],
            font=("Segoe UI", 10, "bold"),
            relief="flat",
        )
        s.map("TMenubutton",
            background=[
                ("active", c["button_hover"]),
            ],
        )

        # -- Notebook ------------------------------------------
        # KRITISK GRA RUTA-FIX:
        #   background  = c["bg"]         <- FONSTRETS FARG, inte tab_bg
        #   borderwidth = 0               <- tar bort synlig kant
        #   relief      = "flat"          <- ingen 3D-effekt
        #   tabmargins  = [0, 0, 0, 0]    <- inga marginaler runt flikraden
        s.configure("TNotebook",
            background=c["bg"],
            borderwidth=0,
            relief="flat",
            tabmargins=[0, 0, 0, 0],
        )
        s.configure("TNotebook.Tab",
            background=c["tab_bg"],
            foreground=c["tab_fg"],
            font=("Segoe UI", 10, "bold"),
            padding=[18, 8],
            borderwidth=0,
        )
        s.map("TNotebook.Tab",
            background=[
                ("selected", c["tab_active_bg"]),
                ("active",   c["surface_alt"]),
            ],
            foreground=[
                ("selected", c["tab_active_fg"]),
                ("active",   c["fg"]),
            ],
            expand=[
                ("selected", [0, 0, 0, 0])
            ],
        )

        # -- Scrollbar -----------------------------------------
        s.configure("TScrollbar",
            background=c["scroll_bg"],
            troughcolor=c["scroll_trough"],
            bordercolor=c["border_soft"],
            arrowcolor=c["text_secondary"],
        )
        s.map("TScrollbar",
            background=[
                ("active", c["accent_hover"]),
            ],
        )

        # -- Progressbar ---------------------------------------
        s.configure("TProgressbar",
            background=c["accent"],
            troughcolor=c["input_bg"],
            bordercolor=c["border_soft"],
        )

        # -- Checkbutton ---------------------------------------
        s.configure("TCheckbutton",
            background=c["bg"],
            foreground=c["fg"],
            font=("Segoe UI", 10),
        )
        s.map("TCheckbutton",
            background=[("active", c["bg"])],
            foreground=[
                ("active", c["fg"]),
                ("disabled", c["disabled_fg"]),
            ],
            indicatorcolor=[
                ("selected", c["accent"]),
                ("active",   c["accent_soft"]),
            ],
        )

        # -- Radiobutton ---------------------------------------
        s.configure("TRadiobutton",
            background=c["bg"],
            foreground=c["fg"],
            font=("Segoe UI", 10),
        )
        s.map("TRadiobutton",
            background=[("active", c["bg"])],
            foreground=[
                ("active", c["fg"]),
                ("disabled", c["disabled_fg"]),
            ],
            indicatorcolor=[
                ("selected", c["accent"]),
            ],
        )

        # -- Scale ---------------------------------------------
        s.configure("TScale",
            background=c["bg"],
            troughcolor=c["input_bg"],
            sliderrelief="flat",
        )
        s.map("TScale",
            background=[("active", c["bg"])],
            slidercolor=[
                ("active", c["accent_hover"]),
            ],
        )

        # -- Treeview ------------------------------------------
        s.configure("Treeview",
            background=c["tree_bg"],
            foreground=c["tree_fg"],
            fieldbackground=c["tree_bg"],
            font=("Segoe UI", 10),
            rowheight=28,
            bordercolor=c["border_soft"],
        )
        s.configure("Treeview.Heading",
            background=c["tree_heading_bg"],
            foreground=c["tree_heading_fg"],
            font=("Segoe UI", 10, "bold"),
            relief="flat",
        )
        s.map("Treeview",
            background=[("selected", c["tree_sel_bg"])],
            foreground=[("selected", c["tree_sel_fg"])],
        )
        s.map("Treeview.Heading",
            background=[
                ("active", c["surface_alt"]),
            ],
        )

        # -- Separator -----------------------------------------
        s.configure("TSeparator", background=c["border_soft"])

        # -- PanedWindow ---------------------------------------
        s.configure("TPanedwindow", background=c["bg"])
        try:
            s.configure("Sash",
                background=c["border"],
                sashthickness=4,
            )
        except Exception:
            pass

        # -- Befintliga tk-widgets (inte bara ttk.Entry) -------
        self.recolor_existing()

    def recolor_existing(self) -> None:
        """Byt farg pa redan skapade tk-widgets via palett-mappning."""
        keys = (
            "bg", "fg", "frame_bg", "label_bg", "label_fg",
            "button_bg", "button_fg", "button_hover", "button_active",
            "entry_bg", "entry_fg", "surface", "surface_alt",
            "panel_bg", "card_bg", "text", "text_secondary", "muted",
            "menu_bg", "menu_fg", "tab_bg", "tab_fg",
            "input_bg", "border", "border_soft",
        )
        cmap = {}
        new = self._colors
        for pal in (self.DARK, self.LIGHT):
            for k in keys:
                v = pal.get(k)
                nv = new.get(k)
                if v and nv:
                    hx = str(v).lower()
                    if hx not in cmap:
                        cmap[hx] = nv
        self._recolor_tree(self._app, cmap)
        try:
            mbar = self._app.nametowidget(self._app["menu"])
            self._recolor_tree(mbar, cmap)
        except Exception:
            pass

    def _recolor_tree(self, w, cmap: dict) -> None:
        """Rekursivt byt bg/fg mm om nuvarande farg finns i paletten."""
        try:
            cls = str(w.winfo_class())
        except Exception:
            return
        is_ttk = cls == "Treeview" or (
            cls.startswith("T") and len(cls) > 1 and cls[1].isupper()
        )
        if not is_ttk:
            for opt in (
                "bg", "fg", "insertbackground",
                "selectbackground", "selectforeground",
                "activebackground", "activeforeground",
                "highlightbackground", "troughcolor",
            ):
                try:
                    cur = str(w.cget(opt)).lower()
                except Exception:
                    continue
                nxt = cmap.get(cur)
                if nxt:
                    try:
                        w[opt] = nxt
                    except Exception:
                        pass
        try:
            kids = w.winfo_children()
        except Exception:
            return
        for ch in kids:
            self._recolor_tree(ch, cmap)

    # -- Publikt API (StyleEngine-kontrakt, C1) ----------------

    def get_theme(self) -> str:
        """Returnera aktuellt tema-namn ("dark" eller "light")."""
        return self._theme

    def set_mode(self, mode: str) -> None:
        """Alias for apply() – sätt tema utan omstart."""
        self.apply(mode)

    def get_colors(self) -> dict:
        """Returnera aktuellt tema's fargdict (kopia)."""
        return dict(self._colors)

    def get_color(self, key: str, fallback: str = "#888888") -> str:
        """Hamta en specifik farg fran aktuellt tema."""
        return self._colors.get(key, fallback)

    def color(self, key: str, fallback: str = "#888888") -> str:
        """Alias for get_color() – kort form."""
        return self._colors.get(key, fallback)

    # -- Design-hjalpmetoder -----------------------------------

    def get_accent_gradient(self) -> dict:
        """
        Returnera accent-familjen (matchar app-ikonen bla->lila).

        Nycklar: accent, accent_hover, accent_active, accent_soft, link
        """
        cached = self._gradient_cache.get("accent")
        if cached is None:
            cached = {
                "accent":        self._colors.get("accent",        "#4a9eff"),
                "accent_hover":  self._colors.get("accent_hover",  "#63adff"),
                "accent_active": self._colors.get("accent_active", "#3b82f6"),
                "accent_soft":   self._colors.get("accent_soft",   "#1e3a5f"),
                "link":          self._colors.get("link",          "#7cb8ff"),
            }
            self._gradient_cache["accent"] = cached
        return dict(cached)

    def get_glass_colors(self) -> dict:
        """
        Returnera glassmorphism-farger (U5).

        Nycklar: surface_glass, border_soft, card_bg, card_hover
        """
        cached = self._gradient_cache.get("glass")
        if cached is None:
            cached = {
                "surface_glass": self._colors.get("surface_glass", "#1e293b"),
                "border_soft":   self._colors.get("border_soft",   "#1f2d45"),
                "card_bg":       self._colors.get("card_bg",       "#1b2942"),
                "card_hover":    self._colors.get("card_hover",    "#223352"),
            }
            self._gradient_cache["glass"] = cached
        return dict(cached)

    def get_widget_colors(self, widget_type: str) -> dict:
        """
        Returnera fargdict for en specifik widgettyp.

        widget_type: "button" | "tab" | "entry" | "treeview" |
                     "menu" | "tooltip" | "status" | "selection"

        Hjalper plugins att hamta allt pa en gang.
        """
        c = self._colors
        cached = self._gradient_cache.get("widgets")
        if cached is None:
            cached = self._build_widget_mapping(c)
            self._gradient_cache["widgets"] = cached
        return dict(cached.get(widget_type, {}))

    def _build_widget_mapping(self, c: dict) -> dict:
        """Bygg widget-fargmappningen en gang per tema (v1.4.0)."""
        mapping = {
            "button": {
                "bg":       c.get("button_bg",       "#5b6472"),
                "fg":       c.get("button_fg",       "#f1f5f9"),
                "hover":    c.get("button_hover",    "#6b7484"),
                "active":   c.get("button_active",   "#4d5563"),
                "disabled": c.get("disabled_bg",     "#1a2436"),
            },
            "tab": {
                "bg":         c.get("tab_bg",        "#1a2436"),
                "fg":         c.get("tab_fg",        "#94a3b8"),
                "active_bg":  c.get("tab_active_bg", "#1e3a5f"),
                "active_fg":  c.get("tab_active_fg", "#ffffff"),
                "hover":      c.get("surface_alt",   "#263449"),
            },
            "entry": {
                "bg":       c.get("entry_bg",     "#0d1526"),
                "fg":       c.get("entry_fg",     "#e2e8f0"),
                "border":   c.get("border",       "#2a3a55"),
                "focus":    c.get("accent",       "#4a9eff"),
                "select_bg": c.get("selection_bg", "#4a9eff"),
                "select_fg": c.get("selection_fg", "#ffffff"),
            },
            "treeview": {
                "bg":        c.get("tree_bg",        "#0f172a"),
                "fg":        c.get("tree_fg",        "#e2e8f0"),
                "sel_bg":    c.get("tree_sel_bg",    "#1e3a5f"),
                "sel_fg":    c.get("tree_sel_fg",    "#ffffff"),
                "heading_bg": c.get("tree_heading_bg", "#1a2436"),
                "heading_fg": c.get("tree_heading_fg", "#cbd5e1"),
            },
            "menu": {
                "bg":         c.get("menu_bg",        "#1e293b"),
                "fg":         c.get("menu_fg",        "#e2e8f0"),
                "active_bg":  c.get("menu_active_bg", "#4a9eff"),
                "active_fg":  c.get("menu_active_fg", "#ffffff"),
            },
            "tooltip": {
                "bg": self.COLOR_TOOLTIP_BG,
                "fg": self.COLOR_TOOLTIP_FG,
            },
            "status": {
                "success": c.get("success", "#22c55e"),
                "warning": c.get("warning", "#f59e0b"),
                "error":   c.get("error",   "#ef4444"),
                "info":    c.get("info",    "#38bdf8"),
                "muted":   c.get("muted",   "#64748b"),
            },
            "selection": {
                "bg": c.get("selection_bg", "#4a9eff"),
                "fg": c.get("selection_fg", "#ffffff"),
            },
        }
        return mapping

    @property
    def current_theme(self) -> str:
        """Returnera aktuellt tema-namn ("dark" eller "light")."""
        return self._theme

    # Alias for bakatkompatibilitet
    @property
    def current(self) -> dict:
        """Returnera hela fargdicten (bakatkompatibilitet)."""
        return self._colors


# ==============================================================================
# TABB-SYNLIGHETSHANTERARE
# ==============================================================================

class TabVisibilityManager:
    """
    Sparar och laddar tabb-synlighet till/fran JSON-fil.

    Fil-format:
        {
          "settings": true,
          "gallery":  true,
          "logger":   false
        }

    Anvandning:
        mgr = TabVisibilityManager(Path("config/tab_visibility.json"))
        visible = mgr.is_visible("gallery")
        mgr.set_visible("gallery", False)
        mgr.save()
    """

    def __init__(self, path: Path):
        self._path  = path
        self._state = {}
        self._load()

    def _load(self) -> None:
        """Ladda fran JSON. Tyst om filen saknas."""
        self._state = load_json(self._path, default={})

    def is_visible(self, tab_name: str, default: bool = True) -> bool:
        """
        Returnera synlighet for tabb.

        Parametrar:
            tab_name: fliknamn
            default:  True = synlig om inget sparat varde finns
        """
        return bool(self._state.get(tab_name, default))

    def set_visible(self, tab_name: str, visible: bool) -> None:
        """Satt synlighet och spara direkt."""
        self._state[tab_name] = visible
        self.save()

    def save(self) -> None:
        """Spara till JSON atomiskt (A9-monstret via save_json)."""
        save_json(self._path, self._state)

    def get_all(self) -> dict:
        """Returnera hela state-dict (kopia)."""
        return self._state.copy()


# ==============================================================================
# FONSTERPOSITIONS-HANTERARE
# ==============================================================================

class WindowStateManager:
    """
    Sparar och laddar fonsterposition och storlek.

    Fil-format:
        {
          "geometry": "900x700+100+50"
        }

    Skarm-bounds-kontroll:
      Om sparad position ar utanfor skarmen centreras
      fonstret automatiskt (BUG-004 fix, hanteras i main.py).

    Anvandning:
        mgr = WindowStateManager(Path("config/window_state.json"))
        geo = mgr.get_geometry()
        mgr.save_state("900x700+200+100")
    """

    DEFAULT_GEOMETRY = "900x700"

    def __init__(self, path: Path):
        self._path = path
        self._data = load_json(path, default={})

    def get_geometry(self) -> str:
        """
        Returnera sparad geometri.

        Kontrollerar att storleken ar rimlig (>= 400x300).
        Returnerar DEFAULT_GEOMETRY om inget giltigt varde finns.
        Position (offset) lamnas at _check_screen_bounds() i main.py.
        """
        geo = self._data.get("geometry", "")
        if geo and self._is_valid(geo):
            return geo
        return self.DEFAULT_GEOMETRY

    def save_state(self, geometry: str) -> None:
        """Spara fonstergeometri atomiskt (A9 via save_json)."""
        self._data["geometry"] = geometry
        save_json(self._path, self._data)

    @staticmethod
    def _is_valid(geo: str) -> bool:
        """
        Kontrollera att geometri-strangen har ratt format och
        rimliga dimensioner (minst 400x300).
        """
        m = re.match(r"(\d+)x(\d+)(\+(-?\d+)\+(-?\d+))?$", geo)
        if not m:
            return False
        w, h = int(m.group(1)), int(m.group(2))
        return w >= 400 and h >= 300


# ==============================================================================
# IKON-GENERERING (C2 – ENDA designkällan för fallback-ikon)
# ==============================================================================

def generate_app_icon(size=(64, 64)):
    """
    Generera fallback-app-ikonen i appens design (C2).

    Design:
      - Rundad bakgrund, bla->lila gradient (uppifran och ner)
      - Vitt bildkort med landskap (himmel + berg + kulle)
      - Gron uppladdnings-badge med vit pil upp

    Anvands av BADE systray (SystrayManager._generate_icon) och
    fonster-ikonen i main.py – en enda kalla for samma utseende.

    Parametrar:
        size: (bredd, hojd) i pixlar

    Returnerar:
        PIL.Image (RGBA)
    """
    from PIL import Image, ImageDraw

    W, H = size
    img  = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    top   = (45, 107, 224)     # #2D6BE0
    bot   = (122, 61, 245)     # #7A3DF5
    white = (255, 255, 255, 255)
    green = (22, 201, 92, 255)   # #16C95C

    # -- Gradientbakgrund (rad for rad) + rundad mask ---------
    for y in range(H):
        t = y / (H - 1) if H > 1 else 0
        r = int(top[0] + (bot[0] - top[0]) * t)
        g = int(top[1] + (bot[1] - top[1]) * t)
        b = int(top[2] + (bot[2] - top[2]) * t)
        draw.line([(0, y), (W, y)], fill=(r, g, b, 255))
    mask = Image.new("L", (W, H), 0)
    ImageDraw.Draw(mask).rounded_rectangle(
        [0, 0, W - 1, H - 1], radius=8, fill=255
    )
    img.putalpha(mask)

    # -- Vitt bildkort ----------------------------------------
    card = [int(W * 0.25), int(H * 0.16), int(W * 0.75), int(H * 0.58)]
    draw.rounded_rectangle(card, radius=4, fill=white)

    # -- Landskap: himmel + sol + berg + kulle -----------------
    sky_bottom = card[1] + int((card[3] - card[1]) * 0.45)
    draw.rectangle([card[0], card[1], card[2], sky_bottom],
                   fill=(205, 231, 255, 255))

    # Sol
    sc = (int(card[0] + (card[2] - card[0]) * 0.66),
          int(card[1] + (card[3] - card[1]) * 0.24))
    sr = max(2, int(W * 0.045))
    draw.ellipse([sc[0] - sr, sc[1] - sr, sc[0] + sr, sc[1] + sr],
                 fill=(255, 210, 63, 255))

    # Berg
    base_y = card[3]
    draw.polygon([
        (card[0] + 1, base_y),
        (int(card[0] + (card[2] - card[0]) * 0.30),
         int(card[1] + (card[3] - card[1]) * 0.30)),
        (int(card[0] + (card[2] - card[0]) * 0.62), base_y),
    ], fill=(120, 165, 235, 255))
    draw.polygon([
        (int(card[0] + (card[2] - card[0]) * 0.35), base_y),
        (int(card[0] + (card[2] - card[0]) * 0.66),
         int(card[1] + (card[3] - card[1]) * 0.18)),
        (card[2], base_y),
    ], fill=(61, 111, 216, 255))

    # Gron kulle
    draw.pieslice(
        [card[0] - 2, int(card[1] + (card[3] - card[1]) * 0.55),
         card[2] + 2, card[3] + int(H * 0.2)],
        180, 360, fill=(76, 175, 110, 255)
    )

    # -- Badge: gron cirkel + vit pil upp ----------------------
    bc = (int(W * 0.74), int(H * 0.66))
    br = max(6, int(W * 0.155))
    # vit ring for separation
    draw.ellipse([bc[0] - br - 1, bc[1] - br - 1,
                  bc[0] + br + 1, bc[1] + br + 1], fill=white)
    draw.ellipse([bc[0] - br, bc[1] - br,
                  bc[0] + br, bc[1] + br], fill=green)
    # pil upp
    ah = max(4, int(W * 0.10))
    aw = max(4, int(W * 0.075))
    draw.polygon([
        (bc[0] - aw, bc[1]),
        (bc[0] + aw, bc[1]),
        (bc[0], bc[1] - ah),
    ], fill=white)
    draw.rectangle([bc[0] - max(2, int(W * 0.035)), bc[1],
                    bc[0] + max(2, int(W * 0.035)), bc[1] + max(4, int(W * 0.07))],
                   fill=white)

    return img


# ==============================================================================
# SYSTRAY-MANAGER
# ==============================================================================

class SystrayManager:
    """
    Hanterar systray-ikonen med pystray.

    Kraver: pystray + Pillow (pip install pystray Pillow)
    Ikon:   icon/ (icon.ico, icon_64.png, icon.png, ...)
            Fallback: assets/ sedan genererad ikon i appens design
            (bla->lila gradient, vitt bildkort, gron badge).
    Wayland-fallback: visar fonstret direkt.

    Meny (A7 – Tema-undermeny):
      Visa FTP-Galleri  -> app.show_window()  [enkelklick]
      Tema >
        Ljust   (radio, markerad om settings.theme == "light")
        Morkt   (radio, markerad om settings.theme == "dark")
        System  (radio, markerad om settings.theme == "system")
      ---------------------
      Avsluta                -> app.quit_app()

    Kor i bakgrundstrad (daemon=True).

    Anvandning:
        mgr = SystrayManager(app)
        mgr.start()
        mgr.stop()
    """

    ICON_COLOR = "#4a9eff"
    ICON_SIZE  = (64, 64)

    def __init__(self, app: tk.Tk):
        self._app    = app
        self._icon   = None
        self._thread = None
        self._active = False

    def start(self) -> None:
        """Starta systray i bakgrundstrad."""
        # Wayland-kontroll (BUG-003)
        if (
            sys.platform == "linux"
            and os.environ.get("XDG_SESSION_TYPE", "").lower() == "wayland"
        ):
            safe_print(
                "[SystrayManager] Wayland detekterat - systray hoppad"
            )
            try:
                self._app.after(200, self._app.minimize_startup)
            except Exception:
                pass
            return

        self._active = True
        if sys.platform == 'darwin':
            self._run()
            return
        self._thread = threading.Thread(
            target=self._run,
            daemon=True,
            name="SystrayThread",
        )
        self._thread.start()

    def stop(self) -> None:
        """Stoppa systray-ikonen."""
        self._active = False
        if self._icon:
            try:
                self._icon.stop()
            except Exception:
                pass

    def _run(self) -> None:
        """Kors i bakgrundstraden."""
        try:
            import pystray

            icon_image = self._load_icon()

            tema_menu = pystray.Menu(
                pystray.MenuItem(
                    "Ljust",
                    self._on_theme_light,
                    checked=lambda item: self._current_theme() == "light",
                    radio=True,
                ),
                pystray.MenuItem(
                    "Mörkt",
                    self._on_theme_dark,
                    checked=lambda item: self._current_theme() == "dark",
                    radio=True,
                ),
                pystray.MenuItem(
                    "System",
                    self._on_theme_system,
                    checked=lambda item: self._current_theme() == "system",
                    radio=True,
                ),
            )

            from tray_status import status_text
            menu = pystray.Menu(
                pystray.MenuItem(lambda item: 'Status: ' + status_text(self._app), None, enabled=False),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem(
                    "Visa FTP-Galleri",
                    self._on_show,
                    default=True,
                ),
                pystray.MenuItem("Tema", tema_menu),
                pystray.MenuItem("Sök efter uppdateringar", self._on_updates),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem("Avsluta", self._on_quit),
            )

            self._icon = pystray.Icon(
                name="ftp_galleri",
                icon=icon_image,
                title="FTP-Galleri",
                menu=menu,
            )

            if sys.platform == 'darwin':
                self._icon.run_detached()
            else:
                self._icon.run()

        except Exception as e:
            safe_print("[SystrayManager] Fel: %s" % e)
            try:
                self._app.after(0, self._app.minimize_startup)
            except Exception:
                pass

    # -- Tema (A7) --------------------------------------------

    def _current_theme(self) -> str:
        """Returnera aktuellt tema-val (settings.theme)."""
        try:
            settings = getattr(self._app, "settings", {}) or {}
            return settings.get("theme", "system")
        except Exception:
            return "system"

    def _set_theme(self, theme: str) -> None:
        """Byt tema tradsakert via after() -> app.apply_theme()."""
        try:
            self._app.after(0, lambda: self._app.apply_theme(theme))
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

    # -- Visa/Avsluta -----------------------------------------

    def _on_updates(self, icon=None, item=None) -> None:
        from auto_update import request_from_tray
        request_from_tray(self._app)

    def _on_show(self, icon=None, item=None) -> None:
        """Visa fonstret (tradsakert via after)."""
        try:
            self._app.after(0, self._app.show_window)
        except Exception:
            pass

    def _on_quit(self, icon=None, item=None) -> None:
        """Avsluta appen (tradsakert via after)."""
        try:
            self._app.after(0, self._app.quit_app)
        except Exception:
            pass

    # -- Ikon (C2) --------------------------------------------

    def _load_icon(self):
        """
        Ladda ikon fran icon/ (sedan assets/) eller generera fallback.

        Prefererar 64 px PNG for skarpa systray-ikoner.
        """
        img, src = load_app_icon(prefer_size=64)
        self._icon_source = src
        if img is not None:
            return img
        return self._generate_icon()

    def _generate_icon(self):
        """
        Generera fallback-ikon i SAMMA design som app-ikonen (C2).

        Delegerar till den delade modul-funktionen generate_app_icon()
        sa att systray och fonster-ikonen alltid delar utseendet.
        """
        return generate_app_icon(self.ICON_SIZE)

    def notify(self, title: str, message: str) -> None:
        """Visa balloon-notifikation (stods ej pa alla plattformar)."""
        if self._icon and self._active:
            try:
                self._icon.notify(message, title)
            except Exception:
                pass


# ==============================================================================
# EXPORTS
# ==============================================================================

__all__ = [
    "VERSION",
    "AUTHOR",
    "COPYRIGHT",
    "load_json",
    "save_json",
    "get_base_path",
    "get_assets_path",
    "get_icon_path",
    "resolve_icon_file",
    "load_app_icon",
    "apply_tk_window_icon",
    "get_config_path",
    "get_logs_path",
    "to_app_rel",
    "from_app_rel",
    "bind_mousewheel",
    "get_system_theme",
    "generate_app_icon",
    "SingleInstanceLock",
    "SystrayManager",
    "ThemeEngine",
    "TabVisibilityManager",
    "WindowStateManager",
]
