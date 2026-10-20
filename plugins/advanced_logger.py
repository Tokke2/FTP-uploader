#!/usr/bin/env python3
# ============================================================
# Plugin: Loggvisare
# ============================================================
# FIL:       plugins/advanced_logger.py
# PLATS:     plugins/ (ftp_gallery_uploader/plugins/advanced_logger.py)
# Klass:     AdvancedLogger(BasePlugin)
# PRIORITY:  -1  (kors allra FORST - fangar allt)
# VERSION:   2.5.1
# AUTHOR:    Rickard Längkvist
# COPYRIGHT: Copyright (c) <år> Rickard Längkvist (dynamiskt år,
#            se COPYRIGHT-konstanten nedan)
#
# ÄNDRINGAR v2.5.0 → v2.5.1 (LOGGSPAM + FALSKT GEOMETRI-LARM):
#   [Y8]      Temabyte-dedupe: <<ThemeChanged>> via bind_all loggade
#             varje widget vid start (~60x dark + hundratals light).
#             Nu loggas bara nar current_theme faktiskt andras
#             (advanced_logger_ui.py v1.1.0).
#   [Y9]      Falsk fönster-Destroy vid flikbyte hoppas over om
#             widgeten fortfarande lever. Map/Unmap/Visibility
#             throttlas 800 ms.
#   [Y10]     parse_geometry tar 1536x713+-1+1 (Windows maximerat).
#             Diagnostiken larmade FEL "ogiltig geometri" i onodan
#             (advanced_logger_guards.py v1.1.0).
#
# ÄNDRINGAR v2.4.0 → v2.5.0 (LEVANDE LOGG + TYDLIGARE CHATT-FELSÖKNING):
#   [Y1]      ContextObserver: app.context wrappas i en dict-subklass som
#             loggar VARJE nyckel som sätts/ändras/tas bort (DEBUG-nivå,
#             throttle per nyckel, värden loggas aldrig). Omsveps igen om
#             run_pipeline byter ut dicten. Dataflödet loggas nu också -
#             "loggning av precis allt som händer" gäller även context.
#             Kan stängas av: context_watch=false i logger_settings.json.
#   [Y2]      Händelsedigest: UI-/livscykelhändelser räknas och summeras
#             till EN rad per minut ("HÄNDELSER (60 s): 14 st - 9 klick,
#             3 val, ...") - allt loggas fortfarande, men överblickbart.
#   [Y3]      Fel-navigering: Ctrl+Down/Up hoppar mellan FEL-rader i
#             loggrutan, knappen "Nästa fel" + "Följ fel"-kryssruta som
#             auto-scrollar vid nya fel.
#   [Y4]      AI-chatt SYMTOMGUIDE: eget fönster där man bockar i vad som
#             hänt (fönstret syns inte / flik saknas / krasch / FTP / seg /
#             tomt galleri) och får riktade svar + kopierbar text.
#   [Y5]      Fönstervakt: var 5:e minut jämförs fönstrets läge; ändring
#             loggas, allvarlig avvikelse ger VARNING - "varför syns inte
#             fönstret" bevakas löpande, inte bara vid start.
#   [Y6]      Diskkontroll: fritt utrymme loggas vid start och i
#             diagnostikrapporten (låg disk = tyst tappade loggar).
#   [Y7]      Sessionsdiff i diagnostiken: fel jämförs mot förra
#             sessionens gallery-logg (nya/återkommande fel).
#
# ÄNDRINGAR v2.3.1 → v2.4.0 (STORT PASS - detaljer i spec.md v4.6.0):
#   [W1]  Uppdelning i advanced_logger_guards.py + advanced_logger_diag.py
#         (+ advanced_logger_ui.py v2.5.0) sa att huvudfilen haller taket.
#   [W2]  shutdown_logging() tillagd (main.pyw anropade den men den fanns ej).
#   [W3]  Central fangst av 13 handelseslag + ultra-lage (ALDRIG tangent-
#         innehall i inmatningsfalt - losenordsskydd).
#   [W4]  Anpassad text: DPI-teckenstorlek, A-/A+, Ctrl+mushjul, radbrytning.
#   [W5]  Anpassat fonster: kompakt toolbar, skarm-anpassat diagnostikfonster.
#   [W6]  AI-felsokning: 21 felmonster-regler (ORSAK/ATGARD/ALLVAR/BEVIS).
#   [W7]  Fönsterdiagnostik: 13 kontroller vid start + manuell (W7).
#   [W8]  Tydlig AI-chatt-rapport + diagnostikfonster, [W9] diagnostik_*.txt.
#   [W10] Publik API bevarad (log/info/.../create_ui/execute/cleanup...).
#
# ÄNDRINGAR v2.3.0 → v2.3.1 (KRASCHFIXAR — Python 3.14 / pythonw):
#   [P14-6]   threading.excepthook: alla bakgrundstrådsfel loggas.
#   [P14-7]   Tk-callback-vakt (report_callback_exception) -> ingen
#             stderr-print, ingen WinError 6, mainloop lever.
#   [P14-8]   GuardedStream på sys.stdout/sys.stderr (tredje part).
#   [P14-9]   Startbanner med Tk/Tcl-version + vakternas status.
#
# ÄNDRINGAR v2.2.0 → v2.3.0: [U1] errors_*.log, [U2] global UI-fångare,
#   [U3] fönsterlivscykel, [U4] log_ui/log_lifecycle/log_exception.
# ÄNDRINGAR v2.1.0 → v2.2.0: [B1] inga f-strings/hardkodade färger,
#   [B3] AUTHOR/COPYRIGHT/PLATS, [A10] logs/ via helpers, [C4] COLOR_*.
#
# ANSVARAR FOR:
#   - Fil-loggning logs/gallery_YYYYMMDD_HHMMSS.log (+ errors_*.log)
#   - Loggrotation (max 50 huvudloggar, 30 felfiler)
#   - Globala undantagsvakter (sys/threading/Tk/streams)
#   - Central fångst av ALLT som händer i UI + fönsterlivscykel
#   - Logg-flik med filter, sökning, statistik, anpassad text
#   - AI-felsökning: felmönster + fönsterdiagnostik + miljörapport
#   - Hook i app.run_pipeline och app.reload_plugins
#
# CONTEXT SOM SATTS:   '_logger'  - self
#
# IMPORTER:
#   tkinter as tk, ttk, filedialog, messagebox
#   datetime, time, traceback, sys, subprocess, json
#   pathlib.Path, collections.deque
#   .base_plugin: BasePlugin
#   .advanced_logger_guards: vakter, LogFiles, text/fönster-hjälp (W1)
#   .advanced_logger_diag:   regler, fönsterrapport, miljö, rendering (W1)
# ============================================================

import json
import subprocess
import sys
import time
import traceback
from collections import deque
from datetime import datetime
from pathlib import Path

import tkinter as tk
from tkinter import ttk, filedialog, messagebox

from .base_plugin import BasePlugin
from .advanced_logger_ui import (
    DiagWindowMixin,
    LogLiveMixin,
    SymptomWindowMixin,
    UiCaptureMixin,
)
from .advanced_logger_guards import (
    GuardedStream,
    LogFiles,
    UNKNOWN,
    disk_free_mb,
    clamp_font_size,
    fit_window,
    install_stream_guard,
    install_threading_hook,
    install_tk_callback_hook,
    readable_width,
    restore_streams,
    safe_write,
    screen_dpi,
    suggest_font_size,
    tk_scaling,
    tk_version,
)
from .advanced_logger_diag import (
    ALLVAR_TEXT,
    RULES,
    analyze_entries,
    analyze_files,
    chat_transcript,
    environment_report,
    render_report,
    suggest_geometry_fix,
    summary_line,
    window_report,
)

# Bakåtkompatibilitet (v2.3.1 hade dessa i denna fil)
_safe_write    = safe_write
_GuardedStream = GuardedStream


class AdvancedLogger(BasePlugin, UiCaptureMixin, DiagWindowMixin,
                     LogLiveMixin, SymptomWindowMixin):
    """
    Avancerad loggning med fil-output, UI-flik, smart cache och
    automatisk AI-felsökning.

    Funktioner (v2.4.0):
    - Loggar ALLT till disk (även utan UI) + separat felfil
    - Loggrotation (max 50 huvudloggar, 30 felfiler)
    - Fyra globala undantagsvakter (sys/threading/Tk/streams)
    - Central fångst av 13 händelseslag (+ ultra-läge)
    - Logg-flik med nivåfilter, sökmarkering, statistik, anpassad text
    - AI-felsökning: 21 felmönster + fönsterdiagnostik + miljörapport,
      presenterad som tydlig chatt-rapport (W6-W9)
    - Hook i run_pipeline och reload_plugins
    - Inga print(), inga f-strings
    """

    PLUGIN_NAME  = "Loggvisare"
    PRIORITY     = -1
    VERSION      = "2.5.1"
    AUTHOR       = "Rickard Längkvist"
    COPYRIGHT    = "Copyright (c) %d %s" % (datetime.now().year,
                                            "Rickard Längkvist")

    MAX_LOG_FILES     = 50
    MAX_CACHE_SIZE    = 5000    # Max antal poster i display-cache
    MAX_DISPLAY_LINES = 3000    # Max antal rader i Text-widget
    MAX_ERROR_FILES   = 30      # Max antal errors_*.log som behalls

    #: Tröskel för dubbellogg (samma widget/handling inom X ms)
    UI_DEDUPE_MS      = 400
    #: Throttle för högfrekventa händelser (ms)
    THROTTLE_CONFIGURE = 900
    THROTTLE_SCROLL    = 1200
    THROTTLE_MOTION    = 700
    THROTTLE_HOVER     = 900
    #: Fördröjning innan "varför syns inte fönstret" körs (ms)
    VISIBILITY_DELAY   = 2500
    #: Uppdatering av uptime/statistik (ms)
    STATS_INTERVAL     = 20000
    #: Händelsedigest-intervall (Y2) och fönstervakts-intervall (Y5)
    DIGEST_MS          = 60000
    WATCHDOG_MS        = 300000

    CONFIG_FILE = "logger_settings.json"

    #: Standardinställningar - sparas i config/logger_settings.json
    DEFAULT_SETTINGS = {
        "capture":       True,     # central UI-fångst (W3)
        "ultra":         False,    # tangenter/musrörelse/hover (W3)
        "font_size":     "auto",   # "auto" eller 7..20 (W4)
        "wrap":          False,    # radbrytning i loggrutan (W4)
        "level":         "ALLA",   # nivåfilter
        "auto_scroll":   True,
        "only_errors":   False,    # visa bara FEL/VARNING (W8)
        "diag_on_start": True,     # fönsterdiagnostik vid start (W7)
        "context_watch": True,     # logga context-skrivningar (Y1)
        "follow_errors": False,    # auto-scrolla vid nya FEL (Y3)
        "digest":        True,     # händelsedigest per minut (Y2)
        "watchdog":      True,     # löpande fönstervakt (Y5)
    }

    # -- Farger ------------------------------------------------
    TAG_COLORS = {
        "TIME":     "#6e7681",
        "INFO":     "#58a6ff",
        "DEBUG":    "#8b949e",
        "VARNING":  "#ffa657",
        "FEL":      "#f85149",
        "OK":       "#3fb950",
        "SYSTEM":   "#d2a8ff",
        "PLUGIN":   "#79c0ff",
        "CONTEXT":  "#7ee787",
        "PIPELINE": "#ffa657",
        "DIAG":     "#e3b341",
    }

    COLOR_BG     = "#0d1117"
    COLOR_BG_MID = "#161b22"
    COLOR_FG     = "#c9d1d9"
    COLOR_MUTED  = "#6e7681"

    # -- Fargkonstanter (B1: inga hardkodade hex i widgets) ----
    COLOR_BTN_DEFAULT = "#374151"
    COLOR_BTN_BLUE    = "#1e40af"
    COLOR_BTN_GRAY    = "#4b5563"
    COLOR_BTN_DIAG    = "#7c2d12"
    COLOR_SELECT      = "#3b82f6"
    COLOR_MATCH       = "#a16207"
    COLOR_INFO_BAR    = "#111111"
    COLOR_INFO_TEXT   = "#8b949e"

    #: Widget-klasser som räknas som interaktiva (W3)
    INTERACTIVE = ("Button", "Menubutton", "Checkbutton", "Radiobutton",
                   "TCombobox", "Combobox", "Menu", "LabelFrame", "TCheckbutton",
                   "TRadiobutton", "TButton", "TMenubutton", "Listbox")
    #: Klasser där tangentloggning aldrig visar innehåll (säkerhet, W3)
    TEXT_ENTRY = ("Entry", "TEntry", "TCombobox", "Combobox", "Text",
                  "TSpinbox", "Spinbox")

    # ==========================================================================
    # INITIERING
    # ==========================================================================

    def init(self, app) -> None:
        """
        Initialisera logger.

        Steg:
          1. Initiera state + inställningar (W3/W4)
          2. Öppna loggfiler via LogFiles (G-G)
          3. Registrera i context
          4. Installera undantagsvakter (P14-6/7/8)
          5. Logga uppstartinfo (+ DPI/skalning, W4)
          6. Koppla in i pipeline/reload + livscykel
          7. Central UI-fångst (W3)
          8. Schemalägg "varför syns inte fönstret" (W7)
        """
        self.app           = app
        self.is_active     = True
        self.start_time    = datetime.now()
        self.log_entries   = []
        self._entry_cache  = deque(maxlen=self.MAX_CACHE_SIZE)
        self.ui_created    = False

        # Undantagsvakter (P14-6/7/8)
        self._streams_guarded = False
        self._tk_hooked       = False
        self._thread_hooked   = False
        self._guard_notes     = {}

        # Fångst-state (U2/W3)
        self._ui_installed     = False
        self._lifecycle_hooked = False
        self._last_ui_key      = ""
        self._last_ui_ms       = 0.0
        self._throttles        = {}
        self._ultra_bound      = False
        self._key_counts       = {}

        # Levande logg (Y1-Y5)
        self._event_counts    = {}
        self._last_watch_key  = None
        self._goto_count      = 0
        self._sym_win         = None
        self._sym_vars        = {}
        self._last_sym_answer = ""
        self._context_wrapped = False

        # UI-referenser (sätts i create_ui)
        self.log_text        = None
        self.stats_label     = None
        self.info_left       = None
        self.info_right      = None
        self.level_var       = None
        self.search_var      = None
        self.auto_scroll_var = None
        self.wrap_var        = None
        self.ultra_var       = None
        self.errors_var      = None
        self._toolbar        = None
        self._toolbar_compact = None
        self._font_widgets   = []
        self._hbar           = None
        self._diag_win       = None
        self._diag_text      = None
        self._last_report    = ""
        self._last_worst     = 1

        # -- Inställningar (W3/W4) ------------------------------
        self._settings = self._load_settings()

        # -- Loggfiler (G-G: all I/O i guards) ------------------
        self._files = LogFiles(
            start_time=self.start_time,
            main_max=self.MAX_LOG_FILES,
            error_max=self.MAX_ERROR_FILES,
        )
        self._files.open_all()
        self.logs_dir        = self._files.logs_dir
        self.log_file_path   = self._files.main_path
        self.error_file_path = self._files.error_path

        # -- Registrera -----------------------------------------
        try:
            app.context["_logger"] = self
        except Exception:
            pass

        # -- Vakter + startupinfo + hooks -----------------------
        self._install_excepthook()
        self._log_startup_info()
        self._hook_application(app)
        self._install_ui_capture(app)
        if self._settings.get("diag_on_start", True):
            self.safe_after(
                self.VISIBILITY_DELAY, self._startup_visibility_check
            )

        # -- Levande logg (Y2/Y5) ------------------------------
        self._follow_errors = bool(self._settings.get("follow_errors", False))
        if self._settings.get("digest", True):
            self.safe_after(self.DIGEST_MS, self._digest_tick)
        if self._settings.get("watchdog", True):
            self.safe_after(self.WATCHDOG_MS, self._visibility_watchdog)

        # -- Context-observator (Y1) ---------------------------
        if self._settings.get("context_watch", True):
            self._install_context_observer(app)

    # -- inställningar -------------------------------------------

    def _load_settings(self) -> dict:
        """Läs config/logger_settings.json med DEFAULT_SETTINGS-fallback."""
        data = dict(self.DEFAULT_SETTINGS)
        try:
            saved = self.load_config(self.CONFIG_FILE, default={})
            if isinstance(saved, dict):
                for key in self.DEFAULT_SETTINGS:
                    if key in saved:
                        data[key] = saved[key]
        except Exception as exc:
            safe_write("[AdvancedLogger] _load_settings: %s" % exc)
        return data

    def _save_settings(self) -> None:
        """Spara inställningar atomiskt (A9 via BasePlugin.save_config)."""
        try:
            self.save_config(
                self.CONFIG_FILE,
                {k: self._settings.get(k, v)
                 for k, v in self.DEFAULT_SETTINGS.items()},
            )
        except Exception as exc:
            safe_write("[AdvancedLogger] _save_settings: %s" % exc)

    def _setting(self, key, default=None):
        """Hämta en inställning (aldrig reser)."""
        try:
            return self._settings.get(key, default)
        except Exception:
            return default

    # FILHANTERING (tunna kompatibilitets-wrapper över LogFiles, W1/W10)
    # ==========================================================================

    def _resolve_logs_dir(self) -> Path:
        """Returnera logs/-mappens Path (A10)."""
        return self._files.logs_dir if self._files else Path("logs")

    def _rotate_logs(self) -> int:
        """Rotera huvudloggar (max MAX_LOG_FILES). Returnerar antal borttagna."""
        return self._files.rotate_main() if self._files else 0

    def _write_to_file(self, timestamp: str, level: str, message: str) -> None:
        """Skriv en rad till loggfilen. Tyst vid fel."""
        if self._files:
            self._files.write(timestamp, level, message)

    def _write_error(self, timestamp: str, level: str, message: str) -> None:
        """Skriv BARA fel/undantag/traceback till felfilen (U1)."""
        if self._files:
            self._files.write_error(timestamp, level, message)

    def _write_error_sep(self, msg: str) -> None:
        """Separator i felfilen (t.ex. session slut)."""
        if self._files:
            self._files.write_sep(msg)

    # ==========================================================================
    # GLOBALA UNDANTAGSVAKTER (P14-6/7/8, nu i guards)
    # ==========================================================================

    def _install_excepthook(self) -> None:
        """
        Installerar ALLA globala undantagsfangare (P0).

        1. sys.excepthook               - huvudtraden
        2. threading.excepthook         - alla bakgrundstradar (P14-6)
        3. Tk report_callback_exception - alla UI-callbacks (P14-7)
        4. GuardedStream stdout/stderr  - tredje part (P14-8)

        Ingen av dem skriver nagonsin till stderr med print() (B1).
        """
        ok, _fallback, guarded = install_stream_guard(self.logs_dir)
        self._streams_guarded = ok
        self._guard_notes["streams"] = ",".join(guarded) if ok else "misslyckad"

        ok, reason = install_threading_hook(self.log)
        self._thread_hooked = ok
        self._guard_notes["thread"] = reason

        ok, reason = install_tk_callback_hook(self.app, self.log)
        self._tk_hooked = ok
        self._guard_notes["tk"] = reason

        _self = self

        def _hook(exc_type, exc_value, exc_tb):
            if issubclass(exc_type, KeyboardInterrupt):
                sys.__excepthook__(exc_type, exc_value, exc_tb)
                return
            tb_text = "".join(
                traceback.format_exception(exc_type, exc_value, exc_tb)
            )
            _self.log(
                "FEL",
                "OUPPTACKT UNDANTAG: %s: %s"
                % (exc_type.__name__, exc_value),
            )
            _self.log("DEBUG", "Traceback:\n%s" % tb_text)
            try:
                if _self.app and _self.app.winfo_exists():
                    _self.app.after(0, lambda: messagebox.showerror(
                        "Kritiskt fel",
                        "Ett ovantat fel intraffade:\n\n%s: %s\n\n"
                        "Detaljer sparade i:\n%s"
                        % (exc_type.__name__, exc_value, _self.log_file_path),
                    ))
            except Exception:
                pass

        sys.excepthook = _hook

    def _get_tk_version(self) -> str:
        """Tk/Tcl-version, t.ex. "9.0.1 (TkVersion 9.0)" (P14-9)."""
        return tk_version(self.app)

    # ==========================================================================
    # PUBLIK LOGG-API
    # ==========================================================================

    def log(self, level: str, message: str) -> None:
        """
        Huvud-loggmetod. Tradsaker.

        - Skriver till fil ALLTID (aven utan UI)
        - Lagger i log_entries (hela sessionen) + _entry_cache (max 5000)
        - Speglar FEL/VARNING/traceback i errors_*.log (U1)
        - Uppdaterar UI via app.after(0, ...) om UI finns
        """
        if not self.is_active:
            return

        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        lvl = (level or "INFO").upper()
        entry = {"time": timestamp, "level": lvl, "message": message}

        self.log_entries.append(entry)
        self._entry_cache.append(entry)

        if self._files:
            self._files.write(timestamp, lvl, message)
            self._files.write_error(timestamp, lvl, message)

        if self.ui_created and self.widget_exists(self.log_text):
            try:
                self.app.after(0, lambda e=entry: self._append_to_display(e))
            except Exception:
                pass

    # -- Bekvamlighetsaliaser ----------------------------------
    def info(self, msg: str)       -> None: self.log("INFO",    msg)
    def warning(self, msg: str)    -> None: self.log("VARNING", msg)
    def error(self, msg: str)      -> None: self.log("FEL",     msg)
    def debug(self, msg: str)      -> None: self.log("DEBUG",   msg)
    def success(self, msg: str)    -> None: self.log("OK",      msg)
    def log_action(self, msg: str) -> None: self.log("INFO",    msg)

    def log_ui(self, action: str, detail: str = "") -> None:
        """
        Logga en UI-handelse (klick, flikbyte, menyval, combobox mm.).

        Skrivs pa SYSTEM-niva med tid. Dedupe sker i _dedupe_ui() sa att
        en dubbeltrigger (bade Button-1 och Return) blir EN rad.
        """
        if not self.is_active or not self._setting("capture", True):
            return
        try:
            self._bump_event(action)          # händelsedigest (Y2)
            msg = "UI: %s -> %s" % (action, detail) if detail \
                else "UI: %s" % action
            self.log("SYSTEM", msg)
        except Exception:
            pass

    def log_lifecycle(self, event: str, detail: str = "") -> None:
        """
        Logga en fönster-/livscykelhändelse (visa, dölj, minimera...).

        Komplement till startup.log (som behålls separat som orsakslogg).
        """
        if not self.is_active:
            return
        try:
            self._bump_event("LIVSCYKEL")     # händelsedigest (Y2)
            msg = "LIVSCYKEL: %s | %s" % (event, detail) if detail \
                else "LIVSCYKEL: %s" % event
            self.log("SYSTEM", msg)
        except Exception:
            pass

    def log_exception(self, message: str, exc: Exception) -> None:
        """Logga undantag med full traceback och exakt orsakstid (U1/U4)."""
        caused = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        self.log("FEL", "%s: %s (orsakad %s)" % (message, exc, caused))
        self.log("DEBUG", "Traceback (orsakad %s):\n%s"
                 % (caused, traceback.format_exc()))

    def log_diag(self, text: str, level: str = "DIAG") -> None:
        """Logga en diagnostikrapport/flerradig text (W6)."""
        if not self.is_active:
            return
        try:
            self.log(level if level in self.TAG_COLORS else "SYSTEM", text)
        except Exception:
            pass

    # ==========================================================================
    # UPPSTARTLOGGNING
    # ==========================================================================

    def _log_startup_info(self) -> None:
        """Logga systeminformation + vakternas status vid start (P14-9/W4)."""
        sep = "=" * 60
        stats = self._files.stats() if self._files else {}
        self.log("SYSTEM", sep)
        self.log("SYSTEM", "FTP-GALLERI STARTAD")
        self.log("SYSTEM", "Tid:      %s"
                 % self.start_time.strftime("%Y-%m-%d %H:%M:%S"))
        self.log("SYSTEM", "Python:   %s (%s)"
                 % (sys.version.split()[0],
                    "64-bit" if sys.maxsize > 2 ** 32 else "32-bit"))
        self.log("SYSTEM", "Platform: %s" % sys.platform)
        self.log("SYSTEM", "Tk/Tcl:   %s" % self._get_tk_version())
        self.log("SYSTEM", "Text/fonster: scaling=%s dpi=%s foreslagen "
                           "teckenstorlek=%s"
                 % (("%.4f" % tk_scaling(self.app)) or UNKNOWN,
                    screen_dpi(self.app) or UNKNOWN,
                    self._effective_font_size()))
        self.log("SYSTEM", "Loggfil:  %s" % stats.get("main", UNKNOWN))
        self.log("SYSTEM", "Felfil:   %s" % stats.get("errors", UNKNOWN))
        free = disk_free_mb(self.logs_dir)
        self.log("SYSTEM" if free < 0 or free >= 500 else "VARNING",
                 "Disk:     %s MB ledigt pa loggdisken (Y6)"
                 % (free if free >= 0 else "?"))
        self.log(
            "SYSTEM",
            "Vakter:   stdout/stderr=%s  trad-hook=%s  tk-callback=%s"
            % (
                "skyddade" if self._streams_guarded else "OSKYDDADE",
                "aktiv"     if self._thread_hooked   else "INAKTIV",
                "aktiv"     if self._tk_hooked       else "INAKTIV",
            ),
        )
        for key, note in sorted(self._guard_notes.items()):
            if note and "aktiv" not in str(note) and key != "streams":
                self.log("DEBUG", "Vakt %s: %s" % (key, note))

        for mod, pkg in (("PIL", "Pillow"), ("pystray", "pystray"),
                         ("watchdog", "watchdog"), ("darkdetect", "darkdetect")):
            try:
                __import__(mod)
                self.log("OK", "+ %s tillgangligt" % pkg)
            except ImportError:
                lvl = "VARNING" if pkg in ("Pillow", "pystray") else "INFO"
                self.log(lvl, "- %s saknas  ->  pip install %s" % (pkg, pkg))
        self.log("SYSTEM", "Fangst:   capture=%s ultra=%s (13 händelseslag%s)"
                 % (self._setting("capture"), self._setting("ultra"),
                    " + tangenter/mus" if self._setting("ultra") else ""))
        self.log("SYSTEM", "Felsokning: %d felmonster-regler aktiva (D1)"
                 % len(RULES))
        self.log("SYSTEM", sep)

    # ==========================================================================
    # PIPELINE-HOOKS + LIVSCYKEL
    # ==========================================================================

    def _hook_application(self, app) -> None:
        """
        Koppla in loggning i app.run_pipeline och app.reload_plugins.

        Anvander closure for att undvika cirkular referens.
        Aldrig print() - all loggning via self.log().
        """
        _original_run = getattr(app, "run_pipeline", None)
        if callable(_original_run):
            def _logged_run(log_func=None):
                self.log("PIPELINE", "=" * 50)
                self.log("PIPELINE", "Pipeline startar")
                try:
                    active = [
                        (n, p) for n, p in app.get_plugins(only_enabled=True)
                        if hasattr(p, "execute")
                    ]
                except Exception:
                    active = []
                self.log("PIPELINE", "Kor %d plugins:" % len(active))
                for _name, plugin in active:
                    self.log("PIPELINE", "  - %s (prio %d)"
                             % (plugin.PLUGIN_NAME,
                                getattr(plugin, "PRIORITY", 100)))

                def _wrap_log(msg):
                    self.log("PIPELINE", msg)
                    if log_func:
                        log_func(msg)

                t0 = datetime.now()
                try:
                    result = _original_run(_wrap_log)
                    self.log("OK", "Pipeline klar pa %.2fs"
                             % (datetime.now() - t0).total_seconds())
                    self._rewrap_context(app)
                    return result
                except Exception as exc:
                    self.log("FEL", "Pipeline misslyckades: %s" % exc)
                    self.log("DEBUG", traceback.format_exc())
                    self._rewrap_context(app)
                    raise

            app.run_pipeline = _logged_run

        _original_reload = getattr(app, "reload_plugins", None)
        if callable(_original_reload):
            def _logged_reload():
                self.log("SYSTEM", "Laddar om plugins...")
                try:
                    _original_reload()
                    self.log("OK", "+ Omladdning klar - %d plugins"
                             % len(getattr(app, "plugins", {})))
                except Exception as exc:
                    self.log("FEL", "Reload misslyckades: %s" % exc)
                    self.log("DEBUG", traceback.format_exc())
                    raise

            app.reload_plugins = _logged_reload

        # -- Fönsterlivscykel (U3) -----------------------------
        # Monkeypatch show_window/hide_to_tray så att VARFÖR fönstret
        # visas/döljs också speglas i huvudloggen. startup.log behålls
        # separat som orsakslogg. Guard mot dubbel-hook vid plugin-reload.
        try:
            already = getattr(app, "_al_logger_hooked", False)
        except Exception:
            already = False
        if not already and not self._lifecycle_hooked:
            try:
                app._al_logger_hooked = True
            except Exception:
                pass
            self._lifecycle_hooked = True
            for _mname in ("show_window", "hide_to_tray"):
                _orig = getattr(app, _mname, None)
                if not callable(_orig):
                    continue

                def _mk(_name, _orig_m):
                    def _wrapped(*a, **kw):
                        try:
                            state = app.state() if hasattr(app, "state") else "?"
                            self.log_lifecycle(_name, "state=%s" % state)
                        except Exception:
                            pass
                        return _orig_m(*a, **kw)
                    return _wrapped

                try:
                    setattr(app, _mname, _mk(_mname, _orig))
                except Exception:
                    pass

    # ==========================================================================
    # W7. VARFÖR SYNS / SYNS INTE FÖNSTRET?
    # ==========================================================================

    def _startup_visibility_check(self) -> None:
        """
        Automatisk fönsterkontroll ~2,5 s efter start (W7).

        Loggar en slutsats (varför fönstret är dolt/synligt) + åtgärder om
        något är fel. Öppnar INGET fönster automatiskt - det vore ironiskt
        om felsökningen själv stal fokus.
        """
        if not self.is_active:
            return
        try:
            report = self._build_report(source="startkontroll")
            window = report.get("window") or {}
            severity = int(report.get("worst", 1))
            verdict = window.get("verdict", UNKNOWN)
            level = "FEL" if severity >= 4 else (
                "VARNING" if severity == 3 else "SYSTEM")
            self.log(level, "FÖNSTERDIAGNOSTIK: %s" % verdict)
            for status, text in window.get("checks", []):
                if status in ("FEL", "VARNING"):
                    self.log(status if status == "FEL" else "VARNING",
                             "  [%s] %s" % (status, text))
            for i, fix in enumerate(window.get("fixes", [])[:4], 1):
                self.log("INFO", "  ÅTGÄRD %d) %s" % (i, fix))
            findings = report.get("findings") or []
            if findings:
                self.log("DIAG", "Felmönster i loggen: %s"
                         % ", ".join("%s(%d)" % (f["id"], f["antal"])
                                     for f in findings[:8]))
            if severity >= 4:
                self.log("DIAG", "Öppna Loggvisare -> Felsök för full "
                                 "rapport (sparas även i logs/)")
        except Exception:
            pass

    def _build_report(self, source="manuell") -> dict:
        """
        Samla in allt och rendera rapporten (W6-W8).

        Returnerar dict: window, environment, findings, extra, text, worst.
        Reser aldrig - diagnostik körs ofta när något redan gått fel.
        """
        out = {"window": {}, "environment": [], "findings": [],
               "extra": {}, "text": "", "worst": 1, "source": source}
        try:
            entries = list(self.log_entries)[-2000:]
            _header, startup_lines = (
                self._files.read_startup() if self._files else ({}, [])
            )
            context = {}
            try:
                context = dict(self.app.context) if self.app else {}
            except Exception:
                context = {}
            out["window"] = window_report(
                self.app, context, self.logs_dir, startup_lines, entries
            )
            out["environment"] = environment_report(
                self.app, self.logs_dir,
                self._files.stats() if self._files else None,
            )
            out["findings"] = analyze_entries(entries)
            out["extra"] = analyze_files(self.logs_dir)
            chat = chat_transcript(out["window"], out["findings"])
            text, worst = render_report(
                out["window"], out["environment"], out["findings"],
                out["extra"],
            )
            # Sessionsdiff (Y7): nya fel jamfort med forra sessionen
            diff_block = self._session_diff_block(entries)
            if diff_block:
                text = "%s\n\n%s" % (text, diff_block)
            out["text"] = "%s\n\n%s" % (chat, text) if chat else text
            out["worst"] = worst
        except Exception as exc:
            out["text"] = "DIAGNOSTIK MISSLYCKADES: %s\n%s" % (
                exc, traceback.format_exc())
            out["worst"] = 4
        return out

    def run_diagnostics(self, show: bool = True, source: str = "manuell"):
        """
        Kör AI-felsökningen (W6-W9). Publik - kan anropas från andra
        plugins eller main.pyw: app.context["_logger"].run_diagnostics().

        Parametrar:
            show:   True = öppna diagnostikfönstret
            source: "manuell" | "startkontroll" | "kortkommando"
        Returnerar: rapport-texten.
        """
        report = self._build_report(source)
        text, worst = report.get("text", ""), report.get("worst", 1)
        self._last_report, self._last_worst = text, worst

        level = "FEL" if worst >= 4 else ("VARNING" if worst >= 3 else "DIAG")
        try:
            self.log(level, summary_line(report.get("window"),
                                         report.get("findings")))
        except Exception:
            pass
        path = self._save_diag_file(text)
        if path:
            self.log("INFO", "Diagnostikrapport sparad: %s (%d rader, %s)"
                     % (Path(path).name, text.count("\n") + 1, source))
        if show:
            self._open_diag_window(report)
        return text

    def _save_diag_file(self, text: str):
        """Skriv rapporten till logs/diagnostik_*.txt (W9). Returnerar Path."""
        try:
            name = "diagnostik_%s.txt" % datetime.now().strftime(
                "%Y%m%d_%H%M%S")
            path = Path(self.logs_dir) / name
            path.write_text(text, encoding="utf-8")
            return path
        except Exception as exc:
            self.log("VARNING", "Kunde inte spara diagnostikfil: %s" % exc)
            return None

    def _fix_geometry(self) -> None:
        """
        Rätta fönsterpositionen så att fönstret garanterat syns (W7/T4).

        Ändrar inget på disk utan fråga - användaren bekräftar sparande
        till config/window_state.json.
        """
        try:
            current, suggested, needed = suggest_geometry_fix(self.app)
            if not needed:
                self.log("OK", "Fönstergeometrin är redan giltig (%s)"
                         % current)
                messagebox.showinfo(
                    "Fönsterposition",
                    "Geometrin är redan giltig:\n%s" % current,
                )
                return
            old_geo = current
            self.app.geometry(suggested)
            try:
                self.app.deiconify()
                self.app.lift()
            except Exception:
                pass
            self.log_lifecycle("rätta-geometri", "%s -> %s"
                               % (old_geo, suggested))
            save = messagebox.askyesno(
                "Fönsterposition rättad",
                "Ny geometri: %s\n\nSpara i config/window_state.json?"
                % suggested,
            )
            if save:
                self._save_window_state_file(suggested)
        except Exception as exc:
            self.log("FEL", "Kunde inte rätta geometri: %s" % exc)

    def _save_window_state_file(self, geo: str) -> None:
        """Spara geometri till config/window_state.json (atomiskt, A9)."""
        try:
            from helpers import save_json, get_config_path
            path = Path(get_config_path()) / "window_state.json"
            if save_json(path, {"geometry": geo}):
                self.log("OK", "Sparade geometri %s i %s" % (geo, path.name))
            else:
                self.log("VARNING", "save_json returnerade False för %s" % path)
        except Exception:
            try:
                path = Path(self.get_config_path()) / "window_state.json"
                tmp = path.with_suffix(".json.tmp")
                tmp.write_text(json.dumps({"geometry": geo}, indent=2),
                               encoding="utf-8")
                tmp.replace(path)
                self.log("OK", "Sparade geometri %s (fallback)" % geo)
            except Exception as exc:
                self.log("FEL", "Kunde inte spara window_state.json: %s" % exc)

    # ==========================================================================
    # UI - SKAPA FLIK
    # ==========================================================================

    def create_ui(self) -> None:
        """
        Skapar logg-fliken.

        Anropas fran execute() forsta gangen pipeline kors (eller direkt
        av tab_manager). Visar alla buffrade poster direkt.
        """
        if self.ui_created:
            return
        tab_manager = None
        try:
            tab_manager = self.app.context.get("_tab_manager")
        except Exception:
            tab_manager = None
        if not tab_manager:
            self.log("VARNING", "tab_manager saknas - logg-UI byggs inte")
            return
        try:
            log_frame = tab_manager.add_tab("log", "Logg")
            if not log_frame:
                self.log("FEL", "tab_manager.add_tab() returnerade None")
                return

            self._build_toolbar(log_frame)
            self._build_log_area(log_frame)
            self._build_info_bar(log_frame)
            self.ui_created = True
            self._apply_fonts()
            self.log("INFO", "Logg-UI skapat. Cache: %d poster"
                     % len(self._entry_cache))
            self._rebuild_display()
            self._update_info_bar()
            self.safe_after(self.STATS_INTERVAL, self._stats_tick)
        except Exception as exc:
            self.log("FEL", "Kunde inte bygga logg-UI: %s" % exc)
            self.log("DEBUG", traceback.format_exc())

    # -- Toolbar (W5/W8) ----------------------------------------

    def _build_toolbar(self, parent: tk.Widget) -> None:
        """
        Verktygsfalt med knappar, filter och text/ultra-val.

        tk.Frame(bg=COLOR_BG_MID) - INTE ttk.Frame -> ingen gra bakgrund.
        Flödar om till kompakt läge när fönstret är smalt (W5).
        """
        bg   = self.COLOR_BG_MID
        ctrl = tk.LabelFrame(
            parent, text="Kontroller",
            bg=bg, fg=self.COLOR_FG, font=("Segoe UI", 9),
            padx=8, pady=6,
        )
        ctrl.pack(fill=tk.X, pady=5, padx=10)
        self._toolbar = ctrl
        ctrl.bind("<Configure>", self._on_toolbar_configure)

        # -- Rad 1: knappar ------------------------------------
        row1 = tk.Frame(ctrl, bg=bg)
        row1.pack(fill=tk.X, pady=(0, 4))
        for text, cmd, color in (
            ("Rensa",          self.clear_display,    self.COLOR_BTN_DEFAULT),
            ("Kopiera",        self.copy_log,         self.COLOR_BTN_DEFAULT),
            ("Spara som...",   self.save_log_as,      self.COLOR_BTN_DEFAULT),
            ("Oppna loggmapp", self.open_logs_folder, self.COLOR_BTN_BLUE),
            ("Uppdatera",      self._rebuild_display, self.COLOR_BTN_DEFAULT),
            ("Nästa fel",      self._goto_next_error, self.COLOR_BTN_DEFAULT),
            ("Symtom",         self._open_symptom_window, self.COLOR_BTN_GRAY),
            ("Felsök (AI)",    self._diag_from_ui,    self.COLOR_BTN_DIAG),
        ):
            btn = self._make_btn(row1, text, cmd, color)
            if text.startswith("Felsök"):
                self._diag_btn = btn

        self.stats_label = tk.Label(
            row1, text="", bg=bg, fg=self.COLOR_MUTED,
            font=("Segoe UI", 9, "bold"),
        )
        self.stats_label.pack(side=tk.RIGHT, padx=10)

        # -- Rad 2: filter + textval ---------------------------
        row2 = tk.Frame(ctrl, bg=bg)
        row2.pack(fill=tk.X)
        self._toolbar_row2 = row2

        self._lbl_level = tk.Label(row2, text="Nivå:", bg=bg,
                                   fg=self.COLOR_FG, font=("Segoe UI", 9))
        self._lbl_level.pack(side=tk.LEFT, padx=(0, 4))

        self.level_var = tk.StringVar(value=str(self._setting("level", "ALLA")))
        level_cb = ttk.Combobox(
            row2, textvariable=self.level_var,
            values=["ALLA"] + list(self.TAG_COLORS.keys()),
            width=11, state="readonly",
        )
        level_cb.pack(side=tk.LEFT, padx=(0, 10))
        level_cb.bind("<<ComboboxSelected>>", self._on_filter_change)

        self._lbl_search = tk.Label(row2, text="Sök:", bg=bg,
                                    fg=self.COLOR_FG, font=("Segoe UI", 9))
        self._lbl_search.pack(side=tk.LEFT, padx=(0, 4))

        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *_: self._on_filter_change())
        self._search_entry = ttk.Entry(row2, textvariable=self.search_var,
                                       width=24)
        self._search_entry.pack(side=tk.LEFT, padx=(0, 2))
        self._make_btn(row2, "X", lambda: self.search_var.set(""),
                       self.COLOR_BTN_GRAY, padx=(0, 10))

        # Höger sida: växlar (W3/W4/W8)
        self.auto_scroll_var = tk.BooleanVar(
            value=bool(self._setting("auto_scroll", True)))
        ttk.Checkbutton(row2, text="Auto-scroll",
                        variable=self.auto_scroll_var,
                        command=self._save_toggle_settings
                        ).pack(side=tk.RIGHT, padx=(6, 0))

        self.wrap_var = tk.BooleanVar(value=bool(self._setting("wrap", False)))
        ttk.Checkbutton(row2, text="Radbryt", variable=self.wrap_var,
                        command=self._toggle_wrap).pack(side=tk.RIGHT,
                                                        padx=(6, 0))

        self.ultra_var = tk.BooleanVar(value=bool(self._setting("ultra", False)))
        ttk.Checkbutton(row2, text="Ultra", variable=self.ultra_var,
                        command=self._toggle_ultra).pack(side=tk.RIGHT,
                                                         padx=(6, 0))

        self.errors_var = tk.BooleanVar(
            value=bool(self._setting("only_errors", False)))
        ttk.Checkbutton(row2, text="Endast fel", variable=self.errors_var,
                        command=self._toggle_only_errors
                        ).pack(side=tk.RIGHT, padx=(6, 0))

        self.follow_var = tk.BooleanVar(
            value=bool(self._setting("follow_errors", False)))
        ttk.Checkbutton(row2, text="Följ fel", variable=self.follow_var,
                        command=self._toggle_follow_errors
                        ).pack(side=tk.RIGHT, padx=(6, 0))

        self._make_btn(row2, "A-", lambda: self._bump_font(-1),
                       self.COLOR_BTN_GRAY, padx=(6, 2))
        self._make_btn(row2, "A+", lambda: self._bump_font(1),
                       self.COLOR_BTN_GRAY, padx=(0, 6))

    def _on_toolbar_configure(self, event=None) -> None:
        """
        Flöda om verktygsfältet i smalt fönster (W5).

        Under 700 px göms etiketterna "Nivå:"/"Sök:" och sökfältet görs
        smalare - knapparna och växlarna finns kvar (de är det viktiga).
        """
        try:
            width = int(getattr(event, "width", 0) or 0)
            if width <= 0:
                return
            compact = width < 700
            if compact == self._toolbar_compact:
                return
            self._toolbar_compact = compact
            if compact:
                self._lbl_level.pack_forget()
                self._lbl_search.pack_forget()
                self._search_entry.config(width=12)
            else:
                self._lbl_level.pack(side=tk.LEFT, padx=(0, 4),
                                     before=self._search_entry)
                self._lbl_search.pack(side=tk.LEFT, padx=(0, 4),
                                      before=self._search_entry)
                self._search_entry.config(width=24)
        except Exception:
            pass

    # -- Logg-area (W4) -----------------------------------------

    def _build_log_area(self, parent: tk.Widget) -> None:
        """Text-widget med scrollbars. tk.Frame - ingen gra bakgrund."""
        bg = self.COLOR_BG
        container = tk.Frame(parent, bg=bg)
        container.pack(fill=tk.BOTH, expand=True, padx=10, pady=4)

        vbar = ttk.Scrollbar(container, orient=tk.VERTICAL)
        vbar.pack(side=tk.RIGHT, fill=tk.Y)

        self._hbar = ttk.Scrollbar(container, orient=tk.HORIZONTAL)
        self._hbar.pack(side=tk.BOTTOM, fill=tk.X)

        self.log_text = tk.Text(
            container, bg=bg, fg=self.COLOR_FG,
            font=("Consolas", 9),
            wrap=tk.WORD if self._setting("wrap", False) else tk.NONE,
            state=tk.DISABLED, relief=tk.FLAT,
            yscrollcommand=vbar.set, xscrollcommand=self._hbar.set,
            selectbackground=self.COLOR_SELECT, cursor="arrow",
            padx=4, pady=3, spacing1=0, spacing3=1,
        )
        self.log_text.pack(fill=tk.BOTH, expand=True)
        vbar.config(command=self.log_text.yview)
        self._hbar.config(command=self.log_text.xview)
        if self._setting("wrap", False):
            self._hbar.pack_forget()

        self._font_widgets.append(self.log_text)

        # Fargtaggar (nivå + tid + sökträff)
        for tag, color in self.TAG_COLORS.items():
            bold = tag in ("FEL", "VARNING", "SYSTEM", "PIPELINE", "DIAG")
            self.log_text.tag_configure(
                tag, foreground=color,
                font=("Consolas", 9, "bold" if bold else "normal"),
            )
        self.log_text.tag_configure("TIME", foreground=self.COLOR_MUTED)
        self.log_text.tag_configure(
            "MATCH", background=self.COLOR_MATCH, foreground="#ffffff")
        # Fel-navigering (Y3): markera raden man hoppat till
        self.log_text.tag_configure(
            "NAV", background="#374151", foreground="#ffffff")

        # Mushjul: 3 enheter per klick; Ctrl+mushjul = textstorlek (W4)
        self.log_text.bind("<Enter>", lambda e: self._bind_wheel())
        self.log_text.bind("<Leave>", lambda e: self._unbind_wheel())
        self.log_text.bind("<Button-4>", lambda e: self._scroll(-3))
        self.log_text.bind("<Button-5>", lambda e: self._scroll(3))
        self.log_text.bind("<Control-MouseWheel>", self._on_ctrl_wheel)
        self.log_text.bind("<Control-Button-4>", lambda e: self._bump_font(1))
        self.log_text.bind("<Control-Button-5>", lambda e: self._bump_font(-1))
        # Kortkommandon i loggrutan
        self.log_text.bind("<Control-f>", lambda e: self._focus_search())
        self.log_text.bind("<Control-d>", lambda e: self._diag_from_ui())
        self.log_text.bind("<Control-plus>", lambda e: self._bump_font(1))
        self.log_text.bind("<Control-minus>", lambda e: self._bump_font(-1))
        self.log_text.bind("<Control-e>", lambda e: self._toggle_only_errors())
        # Fel-navigering (Y3): Ctrl+Down/Up hoppar mellan FEL-rader
        self.log_text.bind("<Control-Down>",
                           lambda e: (self._goto_error(1), "break")[1])
        self.log_text.bind("<Control-Up>",
                           lambda e: (self._goto_error(-1), "break")[1])

    # -- Info-rad (W5) -------------------------------------------

    def _build_info_bar(self, parent: tk.Widget) -> None:
        """Informationsrad langst ned: session, filer, geometri/DPI (W5)."""
        bg  = self.COLOR_INFO_BAR
        bar = tk.Frame(parent, bg=bg)
        bar.pack(fill=tk.X, side=tk.BOTTOM)

        self.info_left = tk.Label(
            bar, text="Session: %s"
            % self.start_time.strftime("%Y-%m-%d %H:%M:%S"),
            bg=bg, fg=self.COLOR_INFO_TEXT, font=("Segoe UI", 8),
        )
        self.info_left.pack(side=tk.LEFT, padx=8, pady=2)

        self.info_right = tk.Label(
            bar, text="", bg=bg, fg=self.COLOR_INFO_TEXT,
            font=("Segoe UI", 8),
        )
        self.info_right.pack(side=tk.RIGHT, padx=8, pady=2)
        self._font_widgets.extend([self.info_left, self.info_right])

    def _update_info_bar(self) -> None:
        """Uppdatera info-raden med filer + fönster/DPI-läge (W5)."""
        if not self.widget_exists(self.info_right):
            return
        try:
            geo = state = "?"
            if self.app is not None:
                geo = str(self.app.geometry() or "?")
                state = str(self.app.state() or "?")
            self.info_right.config(
                text="Fil: %s | Felfil: %s | Fönster: %s %s | DPI: %s | "
                     "Typsnitt: %s"
                % (
                    self.log_file_path.name if self.log_file_path else "-",
                    self.error_file_path.name if self.error_file_path else "-",
                    geo, state, screen_dpi(self.app) or UNKNOWN,
                    self._effective_font_size(),
                )
            )
        except Exception:
            pass

    # ==========================================================================
    # W4. ANPASSAD TEXT (DPI, storlek, radbrytning)
    # ==========================================================================

    def _effective_font_size(self) -> int:
        """Aktuell teckenstorlek: inställning eller DPI-förslag (T1)."""
        size = self._setting("font_size", "auto")
        if isinstance(size, int) and size > 0:
            return clamp_font_size(size)
        try:
            return clamp_font_size(suggest_font_size(self.app))
        except Exception:
            return 9

    def _apply_fonts(self) -> None:
        """
        Sätt typsnitt på loggruta, taggar och infofält (W4/T1).

        Anropas vid skapande och efter varje storleksändring (A-/A+,
        Ctrl+mushjul). Consolas/Segoe UI finns på Windows; Tk faller
        tillbaka på en likvärdig monospace/sans om de saknas.
        """
        size = self._effective_font_size()
        mono = ("Consolas", size)
        ui_font = ("Segoe UI", size)
        try:
            if self.widget_exists(self.log_text):
                self.log_text.config(font=mono)
                for tag in self.TAG_COLORS:
                    bold = tag in ("FEL", "VARNING", "SYSTEM", "PIPELINE",
                                   "DIAG")
                    self.log_text.tag_configure(
                        tag, font=(mono[0], size, "bold" if bold else "normal"))
            for w in self._font_widgets:
                if w is self.log_text or not self.widget_exists(w):
                    continue
                try:
                    w.config(font=ui_font)
                except Exception:
                    continue
        except Exception:
            pass
        self._update_info_bar()

    def _bump_font(self, delta: int) -> None:
        """Ändra teckenstorlek stegvis och spara valet (W4)."""
        try:
            new = clamp_font_size(self._effective_font_size() + int(delta))
            if new == self._setting("font_size"):
                return
            self._settings["font_size"] = new
            self._save_settings()
            self._apply_fonts()
            self.log("DEBUG", "Teckenstorlek: %d pt (DPI %s)"
                     % (new, screen_dpi(self.app) or UNKNOWN))
        except Exception:
            pass

    def _on_ctrl_wheel(self, event) -> None:
        """Ctrl + mushjul = textstorlek (W4)."""
        try:
            delta = getattr(event, "delta", 0) or 0
            if delta:
                self._bump_font(1 if delta > 0 else -1)
        except Exception:
            pass

    def _toggle_wrap(self) -> None:
        """Radbrytning av/på + göm/visa horisontell scrollbar (W4)."""
        try:
            on = bool(self.wrap_var.get()) if self.wrap_var else False
            self._settings["wrap"] = on
            self._save_settings()
            if self.widget_exists(self.log_text):
                self.log_text.config(wrap=tk.WORD if on else tk.NONE)
            if self._hbar is not None:
                if on:
                    self._hbar.pack_forget()
                else:
                    self._hbar.pack(side=tk.BOTTOM, fill=tk.X)
            self.log("DEBUG", "Radbrytning: %s" % ("på" if on else "av"))
        except Exception:
            pass

    def _toggle_ultra(self) -> None:
        """Ultra-läge: tangenter/musrörelse/hover (W3)."""
        try:
            on = bool(self.ultra_var.get()) if self.ultra_var else False
            self._settings["ultra"] = on
            self._save_settings()
            self._bind_ultra(on)
            self.log("VARNING" if on else "INFO",
                     "Ultra-fångst %s (%s)"
                     % ("AKTIVERAD - tangenter/mus loggas, aldrig "
                        "innehåll i inmatningsfält" if on else "avstängd",
                        "config/logger_settings.json"))
        except Exception:
            pass

    def _toggle_only_errors(self) -> None:
        """Snabbfilter: bara FEL/VARNING (W8)."""
        try:
            on = bool(self.errors_var.get()) if self.errors_var else False
            self._settings["only_errors"] = on
            self._save_settings()
            self._on_filter_change()
        except Exception:
            pass

    def _save_toggle_settings(self) -> None:
        """Spara auto-scroll-valet (W4)."""
        try:
            self._settings["auto_scroll"] = bool(self.auto_scroll_var.get())
            self._save_settings()
        except Exception:
            pass

    def _focus_search(self) -> None:
        """Ctrl+F: fokusera sökfältet (W8)."""
        try:
            self._search_entry.focus_set()
            self._search_entry.select_range(0, tk.END)
        except Exception:
            pass

    def _goto_next_error(self) -> None:
        """Knapp 'Nästa fel': hoppa framåt till nästa FEL-rad (Y3)."""
        self._goto_error(1)

    # ==========================================================================
    # UI - VISNING (SMART CACHE)
    # ==========================================================================

    def _passes_filter(self, entry: dict) -> bool:
        """Kontrollera niva-filter, sokterm och "Endast fel" (W8)."""
        level_f = self.level_var.get() if self.level_var else "ALLA"
        search = (self.search_var.get().lower() if self.search_var else "")
        lvl = entry.get("level", "")
        if self._setting("only_errors", False) and lvl not in ("FEL", "VARNING"):
            return False
        if level_f != "ALLA" and lvl != level_f:
            return False
        if search and search not in entry.get("message", "").lower():
            return False
        return True

    def _insert_entry(self, entry: dict) -> None:
        """Skriv en post i Text-widgeten (tid + nivå + meddelande)."""
        self.log_text.insert(tk.END, "[%s] " % entry.get("time", ""), "TIME")
        self.log_text.insert(tk.END, "[%-10s] " % entry.get("level", ""),
                             entry.get("level", "INFO"))
        self.log_text.insert(tk.END, "%s\n" % entry.get("message", ""))

    def _append_to_display(self, entry: dict) -> None:
        """
        Lagg till en post i Text-widget (main thread).

        Begransar till MAX_DISPLAY_LINES rader for att halla minnet nere.
        """
        if not self.ui_created or not self.widget_exists(self.log_text):
            return
        if not self._passes_filter(entry):
            return
        try:
            self.log_text.config(state=tk.NORMAL)
            self._insert_entry(entry)
            lines = int(self.log_text.index("end-1c").split(".")[0])
            if lines > self.MAX_DISPLAY_LINES:
                self.log_text.delete(
                    "1.0", "%d.0" % (lines - self.MAX_DISPLAY_LINES + 500))
            self.log_text.config(state=tk.DISABLED)
            self._highlight_matches(one_line=True)
            if self.auto_scroll_var and self.auto_scroll_var.get():
                self.log_text.see(tk.END)
            elif self._follow_errors and entry.get("level") == "FEL":
                self.log_text.see(tk.END)   # Y3: Följ fel
            self._update_stats()
        except tk.TclError:
            pass

    def _rebuild_display(self, *_) -> None:
        """
        Rita om hela loggen fran smart cache.

        Vid filter=ALLA och ingen sokning: visa cachen (snabbt).
        Vid filter: iterera entries for korrekthet.
        """
        if not self.ui_created or not self.widget_exists(self.log_text):
            return
        try:
            self.log_text.config(state=tk.NORMAL)
            self.log_text.delete("1.0", tk.END)

            level_f = self.level_var.get() if self.level_var else "ALLA"
            search = self.search_var.get().lower() if self.search_var else ""
            no_filter = (level_f == "ALLA" and not search
                         and not self._setting("only_errors", False))
            source = (
                list(self._entry_cache)
                if no_filter and len(self.log_entries) > self.MAX_CACHE_SIZE
                else self.log_entries
            )

            shown = 0
            for entry in source:
                if not self._passes_filter(entry):
                    continue
                self._insert_entry(entry)
                shown += 1
                if shown >= self.MAX_DISPLAY_LINES:
                    self.log_text.insert(
                        tk.END,
                        "[... %d poster dolda - rensa eller ändra filter ...]\n"
                        % (len(source) - shown), "TIME")
                    break

            self.log_text.config(state=tk.DISABLED)
            self._highlight_matches()
            if self.auto_scroll_var and self.auto_scroll_var.get():
                self.log_text.see(tk.END)
            self._update_stats()
        except tk.TclError:
            pass

    def _highlight_matches(self, one_line: bool = False) -> None:
        """Markera sökträffar gult (W8). one_line=True bara sista raden."""
        try:
            if not self.widget_exists(self.log_text):
                return
            term = self.search_var.get() if self.search_var else ""
            self.log_text.config(state=tk.NORMAL)
            if one_line:
                self.log_text.tag_remove("MATCH", "end-2l", tk.END)
            else:
                self.log_text.tag_remove("MATCH", "1.0", tk.END)
            if term and len(term) >= 2:
                start = "1.0"
                stop = tk.END
                for _i in range(2000):
                    pos = self.log_text.search(term, start, stopindex=stop,
                                               nocase=True)
                    if not pos:
                        break
                    end = "%s+%dc" % (pos, len(term))
                    self.log_text.tag_add("MATCH", pos, end)
                    start = end
            self.log_text.config(state=tk.DISABLED)
        except tk.TclError:
            pass

    def _on_filter_change(self, *_args) -> None:
        """Filter/sök ändrat: spara nivå + rita om (debounced, W8)."""
        try:
            if self.level_var:
                self._settings["level"] = self.level_var.get()
            self.after_debounced("filter", 220, self._rebuild_display)
        except Exception:
            self._rebuild_display()

    def _update_stats(self) -> None:
        """Statistik: poster, fel, varningar, synliga, uptime (W8)."""
        if not self.widget_exists(self.stats_label):
            return
        try:
            total = len(self.log_entries)
            errors = sum(1 for e in self.log_entries if e["level"] == "FEL")
            warnings = sum(1 for e in self.log_entries
                           if e["level"] == "VARNING")
            visible = 0
            try:
                visible = int(self.log_text.index("end-1c").split(".")[0]) - 1
            except Exception:
                visible = 0
            text = "%d poster (%d visade)" % (max(0, total), max(0, visible))
            if errors:
                text += " | %d fel" % errors
            if warnings:
                text += " | %d varn" % warnings
            text += " | %s" % self._uptime_text()
            if errors:
                color = self.TAG_COLORS["FEL"]
            elif warnings:
                color = self.TAG_COLORS["VARNING"]
            else:
                color = self.TAG_COLORS["OK"]
            self.stats_label.config(text=text, fg=color)
        except tk.TclError:
            pass

    def _uptime_text(self) -> str:
        """Uptime som HH:MM:SS (W8)."""
        try:
            seconds = int((datetime.now() - self.start_time).total_seconds())
            return "uppe %02d:%02d:%02d" % (
                seconds // 3600, (seconds % 3600) // 60, seconds % 60)
        except Exception:
            return "uppe ?"

    def _stats_tick(self) -> None:
        """Uppdatera uptime/statistik med jämna mellanrum (W8)."""
        if not self.is_active or not self.ui_created:
            return
        self._update_stats()
        self._update_info_bar()
        self.safe_after(self.STATS_INTERVAL, self._stats_tick)

    # ==========================================================================
    # UI - HANDELSEHANTERARE
    # ==========================================================================

    def clear_display(self) -> None:
        """Rensa UI-visningen (filen paverkas INTE)."""
        if not self.widget_exists(self.log_text):
            return
        if not messagebox.askyesno(
            "Rensa logg",
            "Rensa loggen?\n\nOBS: Loggfilen pa disk paverkas inte.",
        ):
            return
        self.clear_display_silent()
        self.log("INFO", "Logg rensad av anvandaren")

    def clear_display_silent(self) -> None:
        """Rensa UI och entries utan dialog (intern)."""
        self.log_entries.clear()
        self._entry_cache.clear()
        if not self.widget_exists(self.log_text):
            return
        try:
            self.log_text.config(state=tk.NORMAL)
            self.log_text.delete("1.0", tk.END)
            self.log_text.config(state=tk.DISABLED)
        except tk.TclError:
            pass
        self._update_stats()

    def copy_log(self) -> None:
        """Kopiera synlig logg till urklipp."""
        if not self.widget_exists(self.log_text):
            return
        try:
            content = self.log_text.get("1.0", tk.END)
            self.app.clipboard_clear()
            self.app.clipboard_append(content)
            self.log("OK", "Logg kopierad till urklipp (%d tecken)"
                     % len(content))
            messagebox.showinfo("Kopierad",
                                "Loggen har kopierats till urklipp!")
        except tk.TclError:
            pass

    def save_log_as(self) -> None:
        """Spara logg till valfri fil."""
        filename = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Textfil", "*.txt"), ("Loggfil", "*.log"),
                       ("Alla filer", "*.*")],
            initialfile="gallery_log_%s.txt"
                        % datetime.now().strftime("%Y%m%d_%H%M%S"),
            initialdir=self.logs_dir,
        )
        if not filename:
            return
        try:
            lines = [
                "[%s] [%-10s] %s" % (e["time"], e["level"], e["message"])
                for e in self.log_entries
            ]
            Path(filename).write_text("\n".join(lines), encoding="utf-8")
            self.log("OK", "Logg sparad: %s (%d rader)"
                     % (Path(filename).name, len(lines)))
            messagebox.showinfo("Sparad", "Loggen sparad:\n%s" % filename)
        except Exception as exc:
            self.log("FEL", "Kunde inte spara logg: %s" % exc)
            messagebox.showerror("Fel", "Kunde inte spara:\n%s" % exc)

    def open_logs_folder(self) -> None:
        """Oppna logs/-mappen i OS-filhanterare (blockerar ej UI)."""
        try:
            Path(self.logs_dir).mkdir(parents=True, exist_ok=True)
            if sys.platform == "win32":
                subprocess.Popen(["explorer", str(self.logs_dir)])
            elif sys.platform == "darwin":
                subprocess.Popen(["open", str(self.logs_dir)])
            else:
                subprocess.Popen(["xdg-open", str(self.logs_dir)])
            self.log("INFO", "Oppnar: %s" % self.logs_dir)
        except Exception as exc:
            self.log("FEL", "Kunde inte oppna mapp: %s" % exc)
            messagebox.showerror("Fel", "Kunde inte oppna:\n%s" % exc)

    # ==========================================================================
    # MUSHJUL
    # ==========================================================================

    def _bind_wheel(self) -> None:
        if self.widget_exists(self.log_text):
            self.log_text.bind("<MouseWheel>", self._on_wheel)

    def _unbind_wheel(self) -> None:
        if self.widget_exists(self.log_text):
            try:
                self.log_text.unbind("<MouseWheel>")
            except Exception:
                pass

    def _on_wheel(self, event) -> None:
        """Hantera mushjul (Windows/Mac) - 3 enheter per klick."""
        direction = -1 if (getattr(event, "delta", 0) or 0) > 0 else 1
        self._scroll(direction * 3)

    def _scroll(self, units: int) -> None:
        """Skrolla loggen."""
        if self.widget_exists(self.log_text):
            try:
                self.log_text.yview_scroll(units, "units")
            except tk.TclError:
                pass

    # ==========================================================================
    # KNAPP-FABRIK
    # ==========================================================================

    def _make_btn(self, parent, text: str, command, bg: str = None,
                  side: str = tk.LEFT, padx=(2, 2)) -> tk.Button:
        """Intern knapp-fabrik med hover-effekt (BOLD, hand2)."""
        if bg is None:
            bg = self.COLOR_BTN_DEFAULT
        hover = self._darken(bg)
        btn = tk.Button(
            parent, text=text, command=command,
            bg=bg, fg=self.COLOR_FG,
            activebackground=hover, activeforeground=self.COLOR_FG,
            relief=tk.FLAT, cursor="hand2",
            font=("Segoe UI", 9, "bold"), padx=8, pady=3,
        )
        btn.pack(side=side, padx=padx)
        btn.bind("<Enter>", lambda e: btn.config(bg=hover))
        btn.bind("<Leave>", lambda e: btn.config(bg=bg))
        self._font_widgets.append(btn)
        return btn

    @staticmethod
    def _darken(hex_color: str, factor: float = 0.75) -> str:
        """Morkna hex-farg for hover-effekt."""
        try:
            h = hex_color.lstrip("#")
            r = max(0, int(int(h[0:2], 16) * factor))
            g = max(0, int(int(h[2:4], 16) * factor))
            b = max(0, int(int(h[4:6], 16) * factor))
            return "#%02x%02x%02x" % (r, g, b)
        except Exception:
            return hex_color

    @staticmethod
    def widget_exists(widget) -> bool:
        """Returnera True om widgeten finns och inte forstorts."""
        if widget is None:
            return False
        try:
            return bool(widget.winfo_exists())
        except Exception:
            return False

    # ==========================================================================
    # PLUGIN-KONTRAKT
    # ==========================================================================

    def execute(self, context: dict, log=None) -> dict:
        """
        Pipeline-steg.

        - Skapar UI om det inte finns annu
        - Ser till att fångsten är installerad (W3)
        - Loggar context-nycklar pa DEBUG-niva
        """
        if not self.is_active:
            return context
        if not self.ui_created:
            self.create_ui()
        if not self._ui_installed:
            self._install_ui_capture(self.app)

        self.log("CONTEXT", "Context: %d nycklar" % len(context or {}))
        interesting = [
            "gallery_images", "sorted_images", "gallery_order",
            "processed_images", "processed_videos", "processed_pdfs",
            "output_path", "files_to_upload", "ftp_enabled",
        ]
        for key in interesting:
            if key not in (context or {}):
                continue
            val = context[key]
            if isinstance(val, list):
                self.log("DEBUG", "  %s: lista (%d element)" % (key, len(val)))
            elif isinstance(val, dict):
                self.log("DEBUG", "  %s: dict (%d nycklar)" % (key, len(val)))
            else:
                self.log("DEBUG", "  %s: %s" % (key, str(val)[:60]))
        return context

    # ==========================================================================
    # LIVSCYKEL
    # ==========================================================================

    def shutdown_logging(self) -> None:
        """
        Stäng loggningen säkert (W2 - anropas av main.pyw steg 4, A8).

        Finns i main.pyw som hasattr-guardat anrop men SAKNADES i v2.3.1,
        så de sista raderna kunde försvinna. Nu: skriv avslut, flusha,
        stäng filer, återställ stdout/stderr och avboka after-jobb.
        """
        try:
            if self.is_active:
                self.log("SYSTEM", "shutdown_logging: stänger loggfiler")
            self.cleanup()
        except Exception:
            pass
        try:
            restored = restore_streams()
            if restored:
                safe_write("[AdvancedLogger] återställde %s"
                           % ",".join(restored))
        except Exception:
            pass

    def cleanup(self) -> None:
        """Stada upp vid appavslutning (W1: fil-I/O via LogFiles)."""
        if not self.is_active and self._files is None:
            return
        elapsed = (datetime.now() - self.start_time).total_seconds()
        sep = "=" * 60
        was_active = self.is_active
        self.is_active = False
        try:
            self.cancel_all_afters()
        except Exception:
            pass
        try:
            self._close_diag()
        except Exception:
            pass
        if self._files:
            stamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
            for msg in (
                sep,
                "SESSION AVSLUTAS",
                "Total tid:     %.1fs" % elapsed,
                "Loggposter:    %d" % len(self.log_entries),
                "Skrivna rader: %d (varav fel %d)"
                % (self._files.written, self._files.errors),
                "Loggfil:       %s" % (self.log_file_path.name
                                       if self.log_file_path else UNKNOWN),
                "Vakter:        streams=%s thread=%s tk=%s"
                % (self._streams_guarded, self._thread_hooked,
                   self._tk_hooked),
                sep,
            ):
                self._files.write(stamp, "SYSTEM", msg)
            self._files.close()
        if was_active:
            safe_write("[AdvancedLogger] session avslutad (%.1fs, %d poster)"
                       % (elapsed, len(self.log_entries)))

    def on_closing(self) -> None:
        """Alias - bakatkompatibilitet."""
        self.cleanup()
