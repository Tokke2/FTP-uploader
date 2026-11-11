#!/usr/bin/env python3
# ============================================================
# FTP-Galleri – Huvudapplikation
# ============================================================
# FIL:      main.pyw
# PLATS:    projektrot (FTP-Galleri/)
# Version:  1.0.0
# AUTHOR:   Rickard Längkvist
# COPYRIGHT: Copyright (c) <år> Rickard Längkvist (dynamiskt år, se COPYRIGHT-konstanten)
# Syfte:    Minimalt skal – all funktionalitet i plugins/
# Beroenden: helpers.py, plugins/
#
# ÄNDRINGAR v2.8.3 → v2.8.4:
#   Temabyte restylar hela UI (inte bara textfalt). Dispatcher
#   kors direkt sa stulna <<ThemeChanged>>-bindningar inte vinner.
#
# ÄNDRINGAR v2.8.2 → v2.8.3:
#   Pip vid start med progressbar. Enda bat:
#   Installera_senaste_Python.bat.
#
# ÄNDRINGAR v2.8.1 → v2.8.2:
#   FreeConsole() KORS FORE tkinter-import (annars hinner konsolen
#   synas). Enda startfil: main.pyw (pythonw / .pyw = ingen konsol).
#
# ÄNDRINGAR v2.8.0 → v2.8.1:
#   [BUG-008b] _start_systray anvander system_tray-plugin som
#             _systray_mgr om den redan kors – ingen andra
#             helpers.SystrayManager. EN ikon.
#
# ÄNDRINGAR v2.7.0 → v2.8.0 (KOD/DESIGN + TEXT/FÖNSTER/MINNE/SNABBHET):
#   [M1]      Sista f-strängen borttagen (safe_write) – 0 f-strings,
#             0 print() i main.pyw.
#   [M2]      MAINLOOP-VAKT (stående order): _safe_mainloop() fångar
#             KeyboardInterrupt/TclError/övrigt, loggar i startup.log,
#             avslutar säkert och spärrar dubbel mainloop.
#   [M3]      FÖNSTERLÄGES-VAKTER (stående order): geometri sparas
#             BARA i normal-läge med giltig storlek (aldrig iconified/
#             withdrawn/zoomed, aldrig 0x0) – _on_configure hoppar
#             över onormala lägen.
#   [M4]      1800-taket: guard-/startup-logik flyttad till NYA
#             main_guards.py (safe_write, excepthook, autostart-
#             primitiv, cleanup_pycache) – spec §20 ATGÄRD klar.
#             Fixar latent bugg: excepthooken refererade
#             log_startup_crash före helpers-importen (tyst NameError).
#   [M5]      Design: redundanta except-tupler förenklade,
#             skrivfel rättade ("ANDRA INSTANS").
#   [M6]      Snabbhet: total init-tid loggas i startup.log;
#             importlib.invalidate_caches() vid reload.
#   [M7]      Minne: reload rensar importcache korrekt (frigör
#             modulreferenser) – ingen läckande widget-referens.
#   [M8]      ANPASSAT FÖNSTER: startgeometrin anpassas till skärmens
#             storlek (_adaptive_geometry, max sw-120 x sh-160).
#   [M9]      Robusthet: mappar skapas via BASE_DIR (inte cwd) –
#             fungerar oavsett varifrån appen startas.
#
# ÄNDRINGAR v2.6.0 → v2.7.0 (diagnostik – alla loggar i logs/, startlogg):
#   [L1]      Ny logs/startup.log: REN kronologisk startlogg som nollställs
#             vid varje start och loggar VARJE init-steg + exakt beslut om
#             fönstret visas/döljs. Klistra in denna = problemet syns direkt.
#   [L2]      Fönster-logik instrumenterad: single-instance (andra instansen
#             döljs → trigger), start_minimized/tray-branch, show_window(),
#             hide_to_tray(), _start_systray-fel, _poll_show_trigger.
#   [L3]      Undantag i startkedjan fångas och loggas per steg (inte bara
#             tyst pass). Kräftiga fel (sys.excepthook) speglas i startup.log.
#   [L4]      Alla logg-/kraschskrivningar hamnar i logs/-undermappen
#             (startup.log, crash_emergency.log, stderr_fallback.log,
#             gallery_*.log) – en enda loggkatalog under appen.
#
# ÄNDRINGAR v2.5.0 → v2.6.0 (snabbhet/robusthet + autostart-självläkning):
#   [R1]      Omdöpt main.py → main.pyw: enda startfil. Med .pyw och
#             FreeConsole() visas inget terminalfönster vid dubbelklick.
#             Alla funktionella sökvägar följer filens verkliga namn.
#   [R2]      Autostart-självläkning: _apply_autostart() jämför nu den
#             registrerade HKCU Run-nyckeln mot den ÖNSKADE kommandosträngen
#             (inte bara om den finns). Stämmer de inte överens skrivs
#             nyckeln om (t.ex. om python/sökväg flyttat). Vill man INTE ha
#             autostart men en gammal nyckel ligger kvar rensas den.
#   [R3]      Retry vid transienta fel: misslyckas synken görs upp till 3
#             forsoök med 1,5 s mellanrum (after) i stället för att ge upp.
#             Fel loggas via safe_write (konsol-fri).
#
# ÄNDRINGAR v2.5.0 (krav från spec v4.6.0):
#   [A11]     Autostart med Windows-starten (HKCU Run-nyckel):
#             pythonw.exe (inget terminalfönster) + start minimerad
#             till systemfältet. Meny: Arkiv → "Starta med Windows".
#             Settings-nycklar: autostart, start_minimized.
#   [C2]      Bättre ikon: fönsterikonen genererar nu en fallback-ikon
#             (samma design som systray) även när assets/icon.png saknas,
#             och autostart-länken får samma ikon via pythonw.exe.
#   [BUG-018b] Autostart-lancherare använder pythonw.exe så att ingen
#             konsol alls skapas vid logga in (komplement till
#             FreeConsole() för dubbelklick).
#
# ÄNDRINGAR v2.4.0 (krav från spec v4.5.0):
#   [BUG-018] FreeConsole() anropas FÖRST (kopplar bort konsolen helt),
#             ShowWindow-fallback – terminalfri även som .py
#   [A6]      Single-instance: andra instansen skapar trigger-fil
#             (instance_show.trigger) → huvudinstansen fokuserar
#             sitt fönster via poll (after 1000 ms) + visar varning
#   [A2]      Settings-validering: tema-migrering (auto/clam → system),
#             _meta.schema_version, .corrupt-backup vid korrupt JSON,
#             auto-repair av saknade fält
#   [C2]      Fönsterikon från assets/ (icon.ico på Windows,
#             icon.png på Linux/Mac) via get_assets_path()
#   [BUG-008b] reload_plugins stoppar systray FÖRE reload och startar
#             om efter – ENDAST EN tray-ikon
#   [A8]      shutdown_logging() anropas vid avslut (om logger stödjer)
#   [A4]      __pycache__-rensning vid avslut i PROD-läge
#             (skyddade mappar: config/logs/assets/out/data/In/json m.fl.)
#   [B1]      Inga f-strings i logganrop (%-formatering), inga print(),
#             inga hårdkodade sökvägar (BASE_DIR via __file__)
#   [B3]      VERSION + AUTHOR + COPYRIGHT (dynamiskt år) i header
#   [A10/Z]   Alla config-filer via get_config_path() (config/)
#
# BEVARAT FRÅN v2.3.0:
#   Grå ruta-fix (tk.Frame + _check_empty_notebook), BUG-002 None-fix,
#   BUG-004 skärmbounds, mushjul 3 enheter globalt, visa/dölj tabbar,
#   Ctrl+G/Ctrl+R/F5-genvägar, atomisk JSON via helpers.save_json.
# ============================================================

import sys
import os
from pathlib import Path as _DiagnosticPath
from startup_diagnostics import install as _install_diagnostics, phase as _startup_phase
_install_diagnostics(_DiagnosticPath(__file__).resolve().parent)

# STEG 1: dolj konsol FORE tkinter (annars hinner fonstret synas).
if sys.platform == "win32":
    try:
        import ctypes
        ctypes.windll.kernel32.FreeConsole()
        hwnd = ctypes.windll.kernel32.GetConsoleWindow()
        if hwnd:
            ctypes.windll.user32.ShowWindow(hwnd, 0)
    except Exception:
        pass

# Claim the process identity before Tk, package installation or startup logs.
if __name__ == "__main__":
    from python_discovery import select_for_start
    from pathlib import Path as _StartupPath
    select_for_start(_StartupPath(__file__))

from single_instance import ensure_primary
if __name__ == "__main__" and ensure_primary() is None:
    sys.exit(0)

try:
    from log_archive import prepare_logs
    prepare_logs()
except Exception:
    pass

_startup_phase('Importerar Tk')
import tkinter as tk
_startup_phase('Tk importerat')
from tkinter import ttk, messagebox
import importlib
import pkgutil
import json
import shutil
import traceback
import re
from pathlib import Path
from threading import Thread
from datetime import datetime

# ===========================================================================
# BAS-SOKVAG (aldrig hardkodad absolut sokvag)
# ===========================================================================

BASE_DIR = Path(__file__).resolve().parent

# STEG 1b: AppUserModelID (inte pythonw-ikon) + pip-tillbehor
try:
    from app_icon import set_windows_app_id
    set_windows_app_id()
except Exception:
    pass
try:
    from ensure_deps import ensure_bootstrap, hide_console
    hide_console()
    _startup_phase('Kontrollerar saknade beroenden')
    if not ensure_bootstrap(BASE_DIR):
        raise RuntimeError('Saknade beroenden kunde inte installeras; se logs/deps.log.')
    _startup_phase('Beroenden klara')
    hide_console()
except Exception as exc:
    from startup_diagnostics import report as _report_startup
    _report_startup(type(exc), exc, exc.__traceback__)
    sys.exit(1)

# ==============================================================================
# STEG 2: Säker skriv-funktion (M4: flyttad till main_guards.py)
# ==============================================================================

from main_guards import (
    safe_write,
    install_excepthook,
    set_startup_crash_callback,
    EMERGENCY_LOG,
    autostart_launcher_cmd,
    autostart_registered_value,
    set_autostart,
    cleanup_pycache,
)

# ==============================================================================
# STEG 2b: STARTUPLOGG (v2.7.0 – "klistra in och se problemet direkt")
# ==============================================================================
# Logiken ligger i helpers.py (reset_startup_log/log_startup/log_startup_exc/
# log_startup_crash) så att main.pyw hålls under 1800 rader. De importeras
# nedan i STEG 4 och skriver en REN kronologisk logg till logs/startup.log.

# ==============================================================================
# STEG 3: Global excepthook (M4: logik i main_guards.py)
# ==============================================================================
# Kraschar skrivs till logs/crash_emergency.log och speglas i
# logs/startup.log. Callbacken for startup-spegling registreras i
# STEG 4 (efter helpers-importen) - fixar v2.7.0s latenta bugg dar
# log_startup_crash anropades innan den importerats.

install_excepthook()

# ==============================================================================
# STEG 4: Importera helpers.py
# ==============================================================================

try:
    from helpers import (
        load_json,
        save_json,
        get_base_path,
        get_assets_path,
        get_icon_path,
        apply_tk_window_icon,
        get_config_path,
        bind_mousewheel,
        get_system_theme,
        reset_startup_log,
        log_startup,
        log_startup_exc,
        log_startup_crash,
        SystrayManager,
        ThemeEngine,
        TabVisibilityManager,
        WindowStateManager,
    )
except ImportError as e:
    safe_write("KRITISKT: helpers.py saknas: %s" % e)
    try:
        import tkinter.messagebox as mb
        _root = tk.Tk()
        _root.withdraw()
        mb.showerror(
            "Startfel – helpers.py saknas",
            "helpers.py kunde inte laddas:\n%s\n\nMapp: %s"
            % (e, BASE_DIR),
        )
        _root.destroy()
    except Exception:
        pass
    sys.exit(1)

# v2.8.0 M4: spegla krascher i startup.log (efter helpers-import)
set_startup_crash_callback(log_startup_crash)

# ==============================================================================
# STEG 5: Systray-kontroll
# ==============================================================================

try:
    import pystray
    from PIL import Image
    HAS_SYSTRAY = True
except ImportError:
    HAS_SYSTRAY = False

# ==============================================================================
# KONSTANTER
# ==============================================================================

APP_NAME            = "FTP-Galleri"
APP_VERSION         = "1.0.0"
AUTHOR              = "Rickard Längkvist"
COPYRIGHT           = "Copyright (c) %d %s" % (datetime.now().year, AUTHOR)
DEFAULT_GEOMETRY    = "900x700"
MIN_WIDTH           = 600
MIN_HEIGHT          = 400
LOCK_PORT           = 47200

# M6: matt init-tiden fran modulstart
try:
    import time as _time_mod
    _T0 = _time_mod.time()
except Exception:
    _T0 = 0.0

# Config-filer (relativa config/ – via get_config_path(), A10/Z)
SETTINGS_FILE       = "settings.json"
PLUGIN_STATES_FILE  = "plugin_states.json"
TAB_VISIBILITY_FILE = "tab_visibility.json"
WINDOW_STATE_FILE   = "window_state.json"

# Trigger-fil för single-instance-fokus (A6)
SHOW_TRIGGER_FILE   = "instance_show.trigger"

# Autostart med Windows-starten (A11; primitiv i main_guards.py)
AUTOSTART_MENU_TXT  = "🌅 Starta med Windows (logga in)"

# ==============================================================================
# HUVUDKLASS
# ==============================================================================

class App(tk.Tk):
    """
    Huvudapplikation – minimalt skal.

    All funktionalitet är i plugins/.
    main.py orkestrerar laddning, UI-grund och livscykel.

    Startsekvens:
      1.  withdraw()             – dölj OMEDELBART
      2.  SingleInstanceLock     – förhindra dubbel instans (A6: fokusera)
      3.  Skapa mappar           – config/ logs/ assets/ plugins/
      4.  Initiera state
      5.  Ladda inställningar    – validering + auto-repair (A2)
      6.  Konfigurera fönster
      7.  Initiera hjälpklasser  – ThemeEngine, WindowStateManager, etc.
      8.  Återställ position
      9.  Bygg bas-UI            – main_frame + notebook + menyrad
      9b. Fönsterikon            – icon/ (C2/I4)
      10. Globala bindningar     – mushjul, shortcuts, events, trigger-poll
      11. Ladda plugins          – PRIORITY-sorterat, init()
      12. Skärmbounds-kontroll   – BUG-004 fix
      13. Applicera tema         – dark/light/system (auto→system)
      14. Starta systray         – pystray eller show_window()
      15. Logga start

    GRÅ RUTA-FIX (BUG-017):
      main_frame: tk.Frame(bg=...) – INTE ttk.Frame.
      notebook.pack: pady=0, padx=0 (döljs helt via _check_empty_notebook).
      ThemeEngine: TNotebook.background = c["bg"], borderwidth=0,
                   tabmargins=[0,0,0,0].
    """

    def __init__(self):
        super().__init__(className="FTP-uploader")
        self._startup_open_requested = False

        # ── 0. Startlogg (v2.7.0) ─────────────────────────────
        reset_startup_log()
        log_startup("0. App-konstruktor", "startar")
        log_startup("Programkopia", "version=%s mapp=%s Python=%s" % (APP_VERSION, BASE_DIR, sys.executable))

        # ── 1. Dölj OMEDELBART ────────────────────────────────
        self.withdraw()
        log_startup("1. Fönster dolt (withdraw)", "rejält dolt tills vi väljer att visa")

        # The launcher already owns this same guard. Direct main.pyw starts
        # acquire it before importing Tk; constructor use remains protected too.
        self._instance_lock = ensure_primary()
        self._show_trigger = get_base_path() / SHOW_TRIGGER_FILE
        if self._instance_lock is None:
            self.destroy()
            sys.exit(0)
        log_startup("2. Single-instance", "erhölls (enda instans, IPC aktiverat)")

        # ── 3. Mappar (M9: via BASE_DIR, aldrig cwd) ────────────
        for folder in ("config", "logs", "assets", "icon", "plugins"):
            try:
                (BASE_DIR / folder).mkdir(parents=True, exist_ok=True)
            except Exception as exc:
                safe_write("[VARNING] Kunde inte skapa %s/: %s" % (folder, exc))
                log_startup("3. Mappar", "KUNDE INTE skapa %s/: %s" % (folder, exc))
        log_startup("3. Mappar", "config/ logs/ assets/ icon/ plugins/")

        _init_file = BASE_DIR / "plugins" / "__init__.py"
        if not _init_file.exists():
            try:
                _init_file.write_text(
                    "# FTP-Galleri plugins\n",
                    encoding="utf-8",
                )
            except Exception:
                pass

        # ── 4. State ──────────────────────────────────────────
        self.context             = {}
        from tray_status import TrayStatus
        self.context['_tray_status'] = TrayStatus()
        self.context['_tray_status'].attach(self)
        self.plugins             = {}
        self.plugin_enabled      = {}
        self.tab_frames          = {}
        self._tab_menu_vars      = {}
        self._configure_after_id = None
        self._icon_photo         = None   # håll referens till ikon (C2)

        # ── 5. Inställningar (A2: validering + auto-repair) ───
        self.settings = {}
        self._load_all_settings()
        log_startup("5. Inställningar", "lästa (%d nycklar) start_minimized=%s autostart=%s theme=%s" % (len(self.settings), self.settings.get("start_minimized"), self.settings.get("autostart"), self.settings.get("theme")))

        # ── 6. Fönster (M8: geometri anpassad till skärmen) ────
        self.title(APP_NAME)
        self._apply_window_icon()
        self.geometry(self._adaptive_geometry())
        self.minsize(MIN_WIDTH, MIN_HEIGHT)

        # ── 7. Hjälpklasser ───────────────────────────────────
        self.theme_engine      = ThemeEngine(self)
        self._window_state_mgr = WindowStateManager(
            get_config_path() / WINDOW_STATE_FILE
        )
        self._tab_vis_mgr = TabVisibilityManager(
            get_config_path() / TAB_VISIBILITY_FILE
        )

        # ── 8. Återställ position ─────────────────────────────
        self.geometry(self._window_state_mgr.get_geometry())
        log_startup("8. Position", "geometry=%s" % self.geometry())

        # ── 9. Bygg bas-UI ────────────────────────────────────
        self._build_base_ui()
        log_startup("9. Bas-UI byggd", "main_frame + notebook + menyer")

        # ── 10. Bindningar ────────────────────────────────────
        self._setup_mousewheel()
        self._setup_keyboard_shortcuts()
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        self.bind("<Configure>", self._on_configure)
        from window_tray import MinimizeToTray
        self._minimize_to_tray = MinimizeToTray(self)
        self.bind("<Unmap>", self._minimize_to_tray.on_unmap, add="+")

        # ── 10b. Trigger-poll (A6) ────────────────────────────
        self.after(200, self._poll_show_trigger)

        # ── 11. Plugins ───────────────────────────────────────
        _load_exc = []
        try:
            self._load_plugins()
        except Exception as exc:
            _load_exc.append(exc)
            log_startup_exc("11. Ladda plugins", exc)
        self._check_empty_notebook()
        log_startup("11. Plugins", "%d laddade; fel: %s" % (len(self.plugins), _load_exc or "inga"))

        # ── 12. Skärmbounds ───────────────────────────────────
        try:
            self._check_screen_bounds()
        except Exception as exc:
            log_startup_exc("12. Skärmbounds", exc)
        log_startup("12. Skärmbounds", "klar")

        # ── 13. Tema (auto/clam → system, A2) ─────────────────
        saved_theme = self.settings.get("theme", "system")
        try:
            self.apply_theme(saved_theme)
        except Exception as exc:
            log_startup_exc("13. Tema", exc)
        log_startup("13. Tema", "applicerar theme=%s" % saved_theme)

        # ── 14. Autostart-synk (A11) ──────────────────────────
        try:
            self._apply_autostart()
        except Exception as exc:
            log_startup_exc("14. Autostart-synk", exc)

        # Always start minimized, irrespective of legacy saved settings.
        self.settings['start_minimized'] = True
        self._systray_mgr = None
        if HAS_SYSTRAY:
            self._start_systray()
        from window_tray import finish_minimized_startup
        self.after(100, lambda: finish_minimized_startup(self))
        if '--show' in sys.argv:
            self.after(0, self.show_window)  # Explicit recovery action, not normal startup.


        # ── 15b. Systray-resultat ─────────────────────────────
        log_startup("15b. Systray", "instans skapad" if self._systray_mgr is not None else "EJ skapad (ingen, eller föll till show_window)")

        # ── 16. Logga start (M6: med total init-tid) ────────────
        try:
            import time as _t
            log_startup(
                "16. Start klar",
                "total init-tid: %.2f s" % (_t.time() - _T0),
            )
        except Exception:
            pass
        logger = self.context.get("_logger")
        if logger:
            logger.log("OK",   "✓ %s v%s startad" % (APP_NAME, APP_VERSION))
            logger.log("INFO", "  Plugins: %s laddade" % len(self.plugins))
            logger.log(
                "INFO",
                "  Systray: %s" % ("Ja" if HAS_SYSTRAY else "Nej"),
            )
            logger.log("INFO", "  Tema:    %s" % saved_theme)

    # ==========================================================================
    # UI – GRUNDSTRUKTUR
    # ==========================================================================

    def _build_base_ui(self) -> None:
        """
        Bygg grundläggande UI.

        GRÅ RUTA-FIX (v2.3.0+):
          main_frame = tk.Frame(bg=self._get_bg()) – INTE ttk.Frame.
          ttk.Frame tar ttk-temat bakgrundsfärg (grå) och skapar en
          synlig remsa mellan menyrad och flikar. tk.Frame med explicit
          bg-färg matchar fönstret.

          notebook.pack: pady=0, padx=0.
          ThemeEngine sätter:
            TNotebook.background  = c["bg"]
            TNotebook.borderwidth = 0
            TNotebook.tabmargins  = [0,0,0,0]
        """
        bg = self._get_bg()

        # ── Huvud-container ───────────────────────────────────
        # tk.Frame – INTE ttk.Frame (grå ruta-fix)
        self.main_frame = tk.Frame(self, bg=bg)
        self.main_frame.pack(fill=tk.BOTH, expand=True)

        # ── Notebook ──────────────────────────────────────────
        self.notebook = ttk.Notebook(self.main_frame)
        # Packas INTE har: tab_manager ager flikytan. En tom notebook
        # med expand=True stal halva (eller hela) ytan sa att
        # inställningsfliken "saknas". Notebook packas bara om nagot
        # anropar add_tab() (_check_empty_notebook).
        self.notebook.bind("<Button-3>", self._on_tab_right_click)

        # ── Menyrad ───────────────────────────────────────────
        self.menubar = tk.Menu(self)
        self.config(menu=self.menubar)

        # ── Arkiv ─────────────────────────────────────────────
        self.arkiv_menu = tk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label="Arkiv", menu=self.arkiv_menu)
        self.arkiv_menu.add_command(
            label="🔄 Ladda om plugins",
            command=self.reload_plugins,
            accelerator="Ctrl+R",
        )
        # ── Autostart (A11): bockbar "Starta med Windows" ─────
        self._autostart_var = tk.BooleanVar(
            value=bool(self.settings.get("autostart", False))
        )
        self.arkiv_menu.add_checkbutton(
            label=AUTOSTART_MENU_TXT,
            variable=self._autostart_var,
            command=self._toggle_autostart,
        )
        self.arkiv_menu.add_separator()
        self.arkiv_menu.add_command(
            label="❌ Avsluta",
            command=self.quit_app,
            accelerator="Alt+F4",
        )

        # ── Visa ──────────────────────────────────────────────
        self.visa_menu = tk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label="Visa", menu=self.visa_menu)

        self._tema_menu = tk.Menu(self.visa_menu, tearoff=0)
        self.visa_menu.add_cascade(label="🎨 Tema", menu=self._tema_menu)
        for label, theme in [
            ("☀  Ljust",  "light"),
            ("🌙  Mörkt", "dark"),
            ("⚙  System", "system"),
        ]:
            self._tema_menu.add_command(
                label=label,
                command=lambda t=theme: self.apply_theme(t),
            )

        self.visa_menu.add_separator()
        self.visa_menu.add_command(
            label="Visa alla tabbar",
            command=self._show_all_tabs,
        )
        self.visa_menu.add_separator()
        # Tabb-checkboxar läggs till dynamiskt av add_tab()

        # ── Kör ───────────────────────────────────────────────
        self.run_menu = tk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label="Kör", menu=self.run_menu)
        self.run_menu.add_command(
            label="▶  Kör pipeline",
            command=self._run_pipeline_safe,
            accelerator="Ctrl+G",
        )
        self.run_menu.add_command(
            label="🔄 Ladda om plugins",
            command=self.reload_plugins,
            accelerator="Ctrl+R",
        )

        # ── Hjälp ─────────────────────────────────────────────
        from auto_update import show_update_settings
        self.menubar.add_command(label="Uppdateringar", command=lambda:
                                 show_update_settings(self, BASE_DIR))
        self.help_menu = tk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label="Hjälp", menu=self.help_menu)
        from local_learning import show_learning
        self.help_menu.add_command(label="Lärande och förslag", command=lambda: show_learning(self))
        self.help_menu.add_command(
            label="Om %s" % APP_NAME,
            command=self._show_about,
        )
        self.help_menu.add_command(
            label="📂 Öppna loggmapp",
            command=self._open_log_folder,
        )
        self.help_menu.add_command(
            label="Öppna samlad fellogg",
            command=self._open_error_summary,
        )
        from unresolved_errors import show_unresolved
        self.help_menu.add_command(label="Aktiva fel / markera åtgärdade",
                                   command=lambda: show_unresolved(self))
        from python_runtime import show_python_status
        self.help_menu.add_command(label="Kontrollera / uppgradera Python",
                                   command=lambda: show_python_status(self))

    def _adaptive_geometry(self) -> str:
        """
        Anpassa startgeometrin till skärmens storlek (M8).

        Utgångspunkt DEFAULT_GEOMETRY (900x700), men aldrig större
        än skärmen minus marginaler och aldrig mindre än MIN-måtten.
        """
        try:
            self.update_idletasks()
            sw = self.winfo_screenwidth()
            sh = self.winfo_screenheight()
            w  = max(MIN_WIDTH,  min(900, sw - 120))
            h  = max(MIN_HEIGHT, min(700, sh - 160))
            return "%dx%d" % (w, h)
        except Exception:
            return DEFAULT_GEOMETRY

    def _get_bg(self) -> str:
        """
        Hämta bakgrundsfärg från ThemeEngine.

        Fallback: mörk bakgrund om ThemeEngine ej initierad.
        """
        try:
            if hasattr(self, "theme_engine"):
                return self.theme_engine.get_color("bg", "#1e1e1e")
        except Exception:
            pass
        return "#1e1e1e"

    # ==========================================================================
    # FÖNSTERIKON (C2 – ikonen används överallt)
    # ==========================================================================

    def _apply_window_icon(self) -> None:
        """
        Sätt fönster- och aktivitetsfalts-ikon från icon/ (I4).

        Windows: icon/icon.ico (iconbitmap = aktivitetsfält/Alt-Tab).
        Alla OS: icon_16/32/64/256.png + icon.png via iconphoto.
        Fallback: generate_app_icon(). Källa loggas i startup.log.
        """
        try:
            src = apply_tk_window_icon(self)
            log_startup("9b. Fönsterikon", src or "applicerad")
            if sys.platform == "win32":
                from windows_autostart import install_app_shortcut
                install_app_shortcut()
        except Exception as exc:
            safe_write("[IKON] Kunde inte sätta fönsterikon: %s" % exc)

    # ==========================================================================
    # PLUGIN-HANTERING
    # ==========================================================================

    def _load_plugins(self) -> None:
        """
        Ladda alla plugins från plugins/-katalogen.

        Steg:
          1. iter_modules – hitta moduler
          2. Hoppa över '_*' och 'base_plugin'
          3. Importera, hitta klass med PLUGIN_NAME (BUG-001: break)
          4. Sortera på PRIORITY
          5. Initiera i ordning

        Felhantering: loggar och fortsätter vid enskilda plugin-fel.
        """
        plugins_path = Path(__file__).parent / "plugins"
        plugins_path.mkdir(exist_ok=True)

        plugin_states = load_json(
            get_config_path() / PLUGIN_STATES_FILE,
            default={},
        )

        found = []
        for finder, name, ispkg in pkgutil.iter_modules(
            [str(plugins_path)]
        ):
            if name.startswith("_") or name == "base_plugin":
                continue
            try:
                module = importlib.import_module("plugins.%s" % name)
                for attr_name in dir(module):
                    cls = getattr(module, attr_name)
                    if (
                        isinstance(cls, type)
                        and hasattr(cls, "PLUGIN_NAME")
                        and cls.__name__ != "BasePlugin"
                        and attr_name != "BasePlugin"
                    ):
                        instance = cls()
                        self.plugins[name]        = instance
                        self.plugin_enabled[name] = plugin_states.get(
                            name, True
                        )
                        found.append((name, instance))
                        break   # BUG-001: bara första klass per modul
            except Exception as exc:
                self._log_error(
                    "Plugin '%s' laddningsfel: %s" % (name, exc),
                    traceback.format_exc(),
                )

        # Sortera på PRIORITY (lägst = körs först)
        found.sort(key=lambda x: getattr(x[1], "PRIORITY", 100))

        for name, plugin in found:
            try:
                if hasattr(plugin, "init"):
                    plugin.init(self)
                    logger = self.context.get("_logger")
                    if logger and name != "advanced_logger":
                        prio = getattr(plugin, "PRIORITY", 100)
                        logger.log(
                            "PLUGIN",
                            "✓ %s (prio=%s)" % (plugin.PLUGIN_NAME, prio),
                        )
            except Exception as exc:
                self._log_error(
                    "Plugin '%s' init-fel: %s" % (name, exc),
                    traceback.format_exc(),
                )

    def _log_error(self, message: str, tb: str = "") -> None:
        """
        Logga fel.

        Försöker i ordning:
          1. _logger i context
          2. safe_write (stderr/fallback)
          3. _EMERGENCY_LOG
        """
        logger = self.context.get("_logger")
        if logger:
            try:
                logger.log("FEL", message)
                if tb:
                    logger.log("DEBUG", "Traceback:\n%s" % tb)
                return
            except Exception:
                pass

        safe_write("[FEL] %s" % message)
        if tb:
            safe_write(tb)

        try:
            with open(EMERGENCY_LOG, "a", encoding="utf-8") as f:
                f.write("[%s] %s\n" % (datetime.now(), message))
                if tb:
                    f.write(tb + "\n")
        except Exception:
            pass

    def get_plugins(self, only_enabled: bool = False) -> list:
        """
        Hämta plugins sorterade efter PRIORITY (lägst först).

        Parametrar:
            only_enabled: om True returneras bara aktiva plugins

        Returnerar:
            [(modulnamn, instans), ...]
        """
        items = [
            (n, p)
            for n, p in self.plugins.items()
            if not only_enabled or self.plugin_enabled.get(n, True)
        ]
        return sorted(
            items, key=lambda x: getattr(x[1], "PRIORITY", 100)
        )

    def run_pipeline(self, log_func=None) -> None:
        """
        Kör alla aktiverade plugins i PRIORITY-ordning.

        BUG-002 fix: None-returvärde ignoreras
        (context ersätts bara om result is not None).
        """
        self._pipeline_busy = getattr(self, '_pipeline_busy', 0) + 1
        status = self.context.get('_tray_status')
        token = status.begin() if status is not None else None
        failed = False
        try:
            for name, plugin in self.get_plugins(only_enabled=True):
                if not hasattr(plugin, "execute"):
                    continue
                if status is not None:
                    status.stage(plugin.PLUGIN_NAME)
                if log_func:
                    log_func("→ %s" % plugin.PLUGIN_NAME)
                try:
                    result = plugin.execute(self.context, log_func)
                    if result is not None:   # BUG-002
                        self.context = result
                except Exception as exc:
                    msg = "[FEL] %s: %s" % (name, exc)
                    if log_func:
                        log_func(msg)
                    self._log_error(msg, traceback.format_exc())
                    raise
        except BaseException:
            failed = True
            raise
        finally:
            if status is not None:
                status.finish(token, failed)
            self._pipeline_busy -= 1

    def _run_pipeline_safe(self) -> None:
        """Kör pipeline i bakgrundstråd – blockerar inte UI (A12)."""
        def _worker():
            try:
                logger = self.context.get("_logger")
                log_fn = (
                    logger.log_action if logger
                    and hasattr(logger, "log_action") else None
                )
                self.run_pipeline(log_func=log_fn)
            except Exception as exc:
                self._log_error(
                    "Pipeline-fel: %s" % exc, traceback.format_exc()
                )

        Thread(
            target=_worker, daemon=True, name="PipelineThread"
        ).start()

    def reload_plugins(self) -> None:
        """
        Ladda om hela plugin-systemet utan omstart.

        Steg:
          0. Stoppa systray FÖRE reload (BUG-008b – ENDAST EN ikon)
          1. Cleanup på alla plugins
          2. Spara viktig context-data
          3. Förstör alla UI-widgets
          4. Rensa state och importcache
          5. Återbygg UI och ladda om plugins
          6. Återställ sparad context-data
          7. Applicera tema
          8. Starta om systray (om det fanns)
        """
        logger = self.context.get("_logger")
        if logger:
            logger.log("SYSTEM", "🔄 Laddar om plugins...")

        # ── 0. Stoppa systray FÖRE reload (BUG-008b) ──────────
        had_systray = False
        if HAS_SYSTRAY and self._systray_mgr:
            try:
                self._systray_mgr.stop()
                had_systray = True
            except Exception as exc:
                safe_write("[SYSTRAY] Stop-fel vid reload: %s" % exc)
            self._systray_mgr = None

        # ── 1. Cleanup ────────────────────────────────────────
        for name, plugin in self.get_plugins():
            for method in ("cleanup", "on_closing"):
                if hasattr(plugin, method):
                    try:
                        getattr(plugin, method)()
                    except Exception:
                        pass
                    break

        # ── 2. Spara viktig context-data ──────────────────────
        old_context = {
            k: v for k, v in self.context.items()
            if k in (
                "gallery", "ftp_settings", "ftp_enabled",
                "selected_folder", "sorted_images", "_tray_status",
            )
        }

        # ── 3. Rensa UI ───────────────────────────────────────
        for widget in self.main_frame.winfo_children():
            try:
                widget.destroy()
            except Exception:
                pass

        # ── 4. Rensa state ────────────────────────────────────
        self.plugins.clear()
        self.plugin_enabled.clear()
        self.tab_frames.clear()
        self._tab_menu_vars.clear()
        self.context = {}

        # Rensa importcache (M6/M7: aven bytecode-cachen)
        for k in list(sys.modules.keys()):
            if k.startswith("plugins."):
                del sys.modules[k]
        try:
            importlib.invalidate_caches()
        except Exception:
            pass

        # ── 5. Återbygg ───────────────────────────────────────
        self._build_base_ui()
        self._load_plugins()
        self._check_empty_notebook()

        for key, val in old_context.items():
            if key not in self.context:
                self.context[key] = val

        self.apply_theme(self.settings.get("theme", "system"))

        # ── 8. Starta om systray (BUG-008b) ───────────────────
        if had_systray and HAS_SYSTRAY:
            self._start_systray()

        logger = self.context.get("_logger")
        if logger:
            logger.log(
                "OK",
                "✓ Omladdning klar – %s plugins" % len(self.plugins),
            )

    # ==========================================================================
    # FÖNSTERHANTERING
    # ==========================================================================

    def show_window(self) -> None:
        """Visa fönstret (från systray-klick eller fallback)."""
        self._startup_open_requested = True
        log_startup("show_window", "anropad → deiconify+lift+focus_force")
        try:
            self._check_screen_bounds()
        except Exception as exc:
            log_startup_exc("show_window/_check_screen_bounds", exc)
        self.deiconify()
        self.lift()
        self.focus_force()
        from app_icon import focus_app_window
        focus_app_window(self)
        log_startup("show_window", "klar – is_visible=%s" % (self.state() == "normal"))

    def minimize_startup(self):
        """Reachable native taskbar fallback; never undo an explicit activation."""
        if not self._startup_open_requested:
            self.deiconify()
            self.iconify()

    def hide_to_tray(self) -> None:
        """Minimera till systray. Sparar position."""
        log_startup("hide_to_tray", "döljer fönster till systemfältet")
        self._save_window_state()
        self.withdraw()

    def on_close(self) -> None:
        """
        X-knappen klickad.

        Med systray: minimera (ALDRIG avsluta).
        Utan systray: avsluta.
        """
        # Kontrollera system_tray-plugin (äger X-knappen)
        system_tray = self.context.get("_system_tray")
        if system_tray and hasattr(system_tray, "_on_window_close"):
            system_tray._on_window_close()
            return

        # Fallback
        if HAS_SYSTRAY and self._systray_mgr:
            self.hide_to_tray()
        else:
            self.quit_app()

    def quit_app(self) -> None:
        """
        Avsluta applikationen helt.

        Steg:
          1. Logga avslutning
          2. Cleanup alla plugins
          3. Spara alla inställningar
          4. shutdown_logging() (A8)
          5. Cache-rensning i PROD (A4)
          6. Ta bort trigger-fil (A6)
          7. Stoppa systray
          8. Frigör instance-lock
          9. destroy() + sys.exit(0)
        """
        logger = self.context.get("_logger")
        if logger:
            try:
                logger.log("SYSTEM", "👋 Avslutar...")
            except Exception:
                pass

        # ── 2. Cleanup plugins ────────────────────────────────
        for name, plugin in self.get_plugins():
            for method in ("cleanup", "on_closing"):
                if hasattr(plugin, method):
                    try:
                        getattr(plugin, method)()
                    except Exception:
                        pass
                    break

        # ── 3. Spara ──────────────────────────────────────────
        try:
            self._save_all_settings()
        except Exception as exc:
            safe_write("[SPARA FEL] %s" % exc)

        # ── 4. shutdown_logging (A8) ──────────────────────────
        try:
            if logger and hasattr(logger, "shutdown_logging"):
                logger.shutdown_logging()
        except Exception:
            pass

        # ── 5. Cache-rensning i PROD (A4) ─────────────────────
        try:
            self._cleanup_pycache()
        except Exception as exc:
            safe_write("[CACHE] Rensning misslyckades: %s" % exc)

        # ── 6. Ta bort trigger-fil (A6) ───────────────────────
        try:
            if self._show_trigger.exists():
                self._show_trigger.unlink()
        except Exception:
            pass

        # ── 7. Stoppa systray ─────────────────────────────────
        try:
            if self._systray_mgr:
                self._systray_mgr.stop()
        except Exception:
            pass

        # ── 8. Frigör instance-lock ───────────────────────────
        try:
            self._instance_lock.release()
        except Exception:
            pass

        self.destroy()
        sys.exit(0)

    def _safe_mainloop(self) -> None:
        """
        Mainloop med vakt (M2 - staende order).

        - Sparrar dubbel mainloop (t.ex. vid felaktigt ateranrop).
        - KeyboardInterrupt -> snyggt avslut via quit_app().
        - TclError (fonstret redan forstort) -> loggas, ingen krasch.
        - Ovriga fel -> loggas i startup.log + kraschlogg, sakert
          avslut sa att inställningar/plugins stadas upp.
        """
        if getattr(self, "_mainloop_running", False):
            safe_write("[MAINLOOP] redan igang - hoppar over")
            return
        self._mainloop_running = True
        log_startup("mainloop", "startar")
        try:
            self.mainloop()
            log_startup("mainloop", "avslutad normalt")
        except KeyboardInterrupt:
            log_startup("mainloop", "KeyboardInterrupt -> quit_app")
            try:
                self.quit_app()
            except Exception:
                pass
        except tk.TclError as exc:
            from startup_diagnostics import report
            report(type(exc), exc, exc.__traceback__)
            log_startup("mainloop", "TclError: %s" % exc)
            safe_write("[MAINLOOP] TclError: %s" % exc)
        except Exception as exc:
            from startup_diagnostics import report
            report(type(exc), exc, exc.__traceback__)
            log_startup_exc("mainloop", exc)
            self._log_error(
                "Mainloop-krasch: %s" % exc, traceback.format_exc()
            )
            try:
                self.quit_app()
            except Exception:
                pass
        finally:
            self._mainloop_running = False

    def _on_configure(self, event) -> None:
        """Spara position med 500ms debounce vid resize/flytt.

        M3: endast i normal-läge (inte minimerad/dold/maximerad).
        """
        if event.widget is not self:
            return
        try:
            if self.state() != "normal":
                return
        except Exception:
            pass
        if self._configure_after_id:
            self.after_cancel(self._configure_after_id)
        self._configure_after_id = self.after(
            500, self._save_window_state
        )

    def _save_window_state(self) -> None:
        """
        Spara aktuell fönstergeometri (M3: med läges-vakter).

        Sparar BARA när:
          - widgeten existerar
          - fönstret är i normal-läge (aldrig iconified/withdrawn/
            zoomed - där är geometrin meningslös/vilseledande)
          - geometrin är giltig och minst 50x50 px
        """
        try:
            if not self.winfo_exists():
                return
            if self.state() != "normal":
                return
            geom = self.geometry()
            m = re.match(
                r"(\d+)x(\d+)\+(-?\d+)\+(-?\d+)", geom
            )
            if not m:
                return
            if int(m.group(1)) < 50 or int(m.group(2)) < 50:
                return
            self._window_state_mgr.save_state(geom)
        except Exception:
            pass

    def _check_screen_bounds(self) -> None:
        """
        BUG-004: Centrera om fönstret är utanför skärmen.

        Minst 50px måste vara synligt på skärmen.
        Anropas vid show_window() och efter plugin-laddning.
        """
        try:
            self.update_idletasks()
            m = re.match(
                r"(\d+)x(\d+)\+(-?\d+)\+(-?\d+)", self.geometry()
            )
            if not m:
                return
            w  = int(m.group(1))
            h  = int(m.group(2))
            x  = int(m.group(3))
            y  = int(m.group(4))
            sw = self.winfo_screenwidth()
            sh = self.winfo_screenheight()
            mg = 50
            if (
                x > sw - mg or y > sh - mg
                or x < -w + mg or y < -h + mg
            ):
                self.geometry(
                    "%dx%d+%d+%d"
                    % (w, h, (sw - w) // 2, (sh - h) // 2)
                )
        except Exception:
            pass

    def _check_empty_notebook(self) -> None:
        """
        Dölj notebooken om den inte har några flikar
        (grå ruta-fix för BUG-017).
        """
        try:
            if hasattr(self, "notebook") and self.notebook.winfo_exists():
                if len(self.notebook.tabs()) == 0:
                    self.notebook.pack_forget()
                else:
                    self.notebook.pack(
                        fill=tk.BOTH, expand=True, padx=0, pady=0
                    )
        except Exception:
            pass

    # ==========================================================================
    # SINGLE-INSTANCE-FOKUS (A6)
    # ==========================================================================

    def _poll_show_trigger(self) -> None:
        """
        Läs IPC och kompatibilitetstrigger var 200 ms.

        Om en andra instans startats skapar den filen
        instance_show.trigger – då visas och fokuseras fönstret.
        """
        try:
            if self._instance_lock.consume_show_request() or self._show_trigger.exists():
                log_startup("_poll_show_trigger", "trigger hittad → show_window")
                try:
                    self._show_trigger.unlink()
                except Exception:
                    pass
                self.show_window()
        except Exception as exc:
            log_startup_exc("_poll_show_trigger", exc)
        try:
            self.after(200, self._poll_show_trigger)
        except Exception:
            pass

    # ==========================================================================
    # TABB-HANTERING
    # ==========================================================================

    def add_tab(self, name: str, frame: tk.Widget) -> None:
        """
        Lägg till en tabb i notebook.

        Anropas av plugins i deras init().
        Lägger till checkbox i Visa-menyn.
        Laddar sparad synlighet från tab_visibility.json.

        Parametrar:
            name:   unikt nyckelnamn
            frame: Frame-widgeten som är tabbens innehåll
        """
        self.tab_frames[name] = frame
        self.notebook.add(frame, text="  %s  " % name)
        self._check_empty_notebook()

        var = tk.BooleanVar(value=True)
        self._tab_menu_vars[name] = var
        self.visa_menu.add_checkbutton(
            label="    %s" % name,
            variable=var,
            command=lambda n=name: self.toggle_tab(n),
        )

        is_visible = self._tab_vis_mgr.is_visible(name, default=True)
        var.set(is_visible)
        if not is_visible:
            self._hide_tab(name)

    def toggle_tab(self, name: str) -> None:
        """Visa/dölj tabb via Visa-menyn eller högerklick."""
        var = self._tab_menu_vars.get(name)
        if var is None:
            return
        new_state = var.get()
        (self._show_tab if new_state else self._hide_tab)(name)
        self._tab_vis_mgr.set_visible(name, new_state)

    def _show_tab(self, name: str) -> None:
        """Visa en dold tabb (lägg till i notebook)."""
        frame = self.tab_frames.get(name)
        if not frame:
            return
        try:
            self.notebook.index(frame)
        except tk.TclError:
            self.notebook.add(frame, text="  %s  " % name)
        self._check_empty_notebook()

    def _hide_tab(self, name: str) -> None:
        """Dölj en tabb (ta bort från notebook utan att förstöra)."""
        frame = self.tab_frames.get(name)
        if not frame:
            return
        try:
            self.notebook.hide(frame)
        except tk.TclError:
            pass
        self._check_empty_notebook()

    def _show_all_tabs(self) -> None:
        """Visa alla dolda tabbar (notebook ELLER tab_manager)."""
        tm = self.context.get("_tab_manager")
        for name, var in self._tab_menu_vars.items():
            if not var.get():
                var.set(True)
                if tm and name in getattr(tm, "tabs", {}):
                    try:
                        tm.show_tab_button(name)
                    except Exception:
                        pass
                else:
                    self._show_tab(name)
                    self._tab_vis_mgr.set_visible(name, True)
        self._check_empty_notebook()

    def _on_tab_right_click(self, event) -> None:
        """
        Högerklick på tabb → kontextmeny.

        Hittar tabb-namn via frame-jämförelse.
        """
        try:
            idx = self.notebook.index("@%d,%d" % (event.x, event.y))
        except tk.TclError:
            return

        try:
            tabs = self.notebook.tabs()
            if idx >= len(tabs):
                return
            tab_id = tabs[idx]
        except (tk.TclError, IndexError):
            return

        # Hitta namn via tab_frames-dict
        tab_name = None
        for name, frame in self.tab_frames.items():
            try:
                # Jämför tab-ID (sträng) med frame-widget-ID
                if str(frame) == tab_id or self.notebook.index(
                    frame
                ) == idx:
                    tab_name = name
                    break
            except Exception:
                continue

        if not tab_name:
            return

        menu = tk.Menu(self, tearoff=0)
        menu.add_command(
            label="🙈 Dölj '%s'" % tab_name,
            command=lambda: self._toggle_tab_from_context(tab_name),
        )
        menu.add_separator()
        menu.add_command(
            label="Visa alla tabbar",
            command=self._show_all_tabs,
        )
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

    def _toggle_tab_from_context(self, name: str) -> None:
        """Dölj tabb via högerklick-kontextmeny."""
        var = self._tab_menu_vars.get(name)
        if var:
            var.set(False)
            self._hide_tab(name)
            self._tab_vis_mgr.set_visible(name, False)

    # ==========================================================================
    # TEMA
    # ==========================================================================

    def apply_theme(self, theme_name: str) -> None:
        """Applicera dark/light/system. Sparar och restylar hela UI."""
        if theme_name not in ("light", "dark", "system"):
            theme_name = "system"

        resolved = (
            get_system_theme() if theme_name == "system"
            else theme_name
        )
        self.theme_engine.apply(resolved)
        self.settings["theme"] = theme_name
        save_json(get_config_path() / SETTINGS_FILE, self.settings)

        try:
            bg = self.theme_engine.get_color("bg", "#1e1e1e")
            if hasattr(self, "main_frame"):
                self.main_frame.configure(bg=bg)
        except Exception:
            pass

        try:
            from plugins.base_plugin import dispatch_theme_changed
            dispatch_theme_changed(self)
        except Exception:
            pass
        try:
            self.event_generate("<<ThemeChanged>>")
        except Exception:
            pass

    # ==========================================================================
    # MUSHJUL
    # ==========================================================================

    def _setup_mousewheel(self) -> None:
        """
        Global mushjuls-scroll.

        Söker uppåt i widget-hierarkin efter närmaste
        scrollbar-ansluten widget (Text, Canvas, Listbox, Treeview).
        3 enheter per klick på alla plattformar.
        """
        def _find_scrollable(widget):
            """Hitta närmaste scrollbara widget uppåt i hierarkin."""
            w = widget
            while w:
                if isinstance(
                    w,
                    (tk.Text, tk.Canvas, tk.Listbox, ttk.Treeview)
                ):
                    return w
                try:
                    w = w.master
                except AttributeError:
                    break
            return None

        def _on_wheel(event):
            if sys.platform == "darwin":
                direction = -1 if event.delta > 0 else 1
                units     = max(1, abs(event.delta)) * 3
            elif sys.platform == "win32":
                direction = -1 if event.delta > 0 else 1
                units     = 3
            else:
                direction = -1 if event.num == 4 else 1
                units     = 3

            target = _find_scrollable(event.widget)
            if target:
                try:
                    target.yview_scroll(direction * units, "units")
                except (tk.TclError, AttributeError):
                    pass

        self.bind_all("<MouseWheel>", _on_wheel)
        self.bind_all("<Button-4>",   _on_wheel)
        self.bind_all("<Button-5>",   _on_wheel)

    # ==========================================================================
    # TANGENTBORDSGENVÄGAR
    # ==========================================================================

    def _setup_keyboard_shortcuts(self) -> None:
        """
        Globala tangentbordsgenvägar.

        Ctrl+G → Kör pipeline
        Ctrl+R / F5 → Ladda om plugins
        """
        pairs = [
            ("<Control-g>", self._run_pipeline_safe),
            ("<Control-G>", self._run_pipeline_safe),
            ("<Control-r>", self.reload_plugins),
            ("<Control-R>", self.reload_plugins),
            ("<F5>",        self.reload_plugins),
        ]
        for key, cmd in pairs:
            self.bind_all(key, lambda e, c=cmd: c())

    # ==========================================================================
    # SYSTRAY
    # ==========================================================================

    def _start_systray(self) -> None:
        """
        Starta systray. ENDAST EN ikon (BUG-008b).

        Om system_tray-pluginet redan kors anvands DET som
        _systray_mgr (ingen helpers.SystrayManager darifran).
        Fallback: helpers.SystrayManager, annars show_window().
        """
        try:
            if self._systray_mgr is not None:
                return
            plugin = None
            try:
                plugin = self.context.get("_system_tray")
            except Exception:
                plugin = None
            if (
                plugin is not None
                and hasattr(plugin, "stop")
                and getattr(plugin, "_tray_running", False)
            ):
                log_startup(
                    "15. _start_systray",
                    "anvander system_tray-plugin (EN ikon)",
                )
                self._systray_mgr = plugin
                return
            log_startup("15. _start_systray", "skapar SystrayManager")
            self._systray_mgr = SystrayManager(self)
            self._systray_mgr.start()
            log_startup("15. _start_systray", "startad")
        except Exception as exc:
            log_startup_exc("15. _start_systray", exc)
            self._log_error("Systray-fel: %s" % exc)
            log_startup(
                "15. _start_systray",
                "FEL → fallback show_window om 100 ms",
            )
            self.after(100, self.minimize_startup)

    # ==========================================================================
    # AUTOSTART (A11 – starta med Windows, minimerad till systemfältet)
    # ==========================================================================

    # M4: autostart-primitiven (kommando, registervärde, skrivning)
    # ligger i main_guards.py. Wrappers nedan behåller anropsytan.

    @staticmethod
    def _autostart_launcher_cmd() -> str:
        """Kommando för HKCU Run (main_guards.autostart_launcher_cmd)."""
        return autostart_launcher_cmd()

    def _autostart_registered_value(self):
        """RAW värde i HKCU Run (main_guards.autostart_registered_value)."""
        return autostart_registered_value()

    def _set_autostart(self, enabled: bool) -> bool:
        """
        Lägg till/ta bort autostart i HKCU Run (via main_guards).

        Windows: registret skrivs/raderas. Andra plattformar: endast
        settings-flaggan uppdateras (stöds ej). True vid framgång.
        """
        if sys.platform == "win32":
            success = set_autostart(bool(enabled))
            if success:
                tray = self.context.get('_system_tray')
                if tray is not None:
                    tray.settings['start_with_windows'] = bool(enabled)
                    tray._save_settings()
            return success
        self.settings["autostart"] = bool(enabled)
        return True

    def _toggle_autostart(self) -> None:
        """Meny-handlare för "Starta med Windows" (synkar reg + settings)."""
        enabled = bool(self._autostart_var.get())
        ok = self._set_autostart(enabled)
        if ok and sys.platform == "win32":
            self.settings["autostart"] = enabled
            try:
                self._save_all_settings()
            except Exception:
                pass
            try:
                logger = self.context.get("_logger")
                if logger:
                    logger.log(
                        "OK" if enabled else "INFO",
                        "Autostart %saktiverad"
                        % ("" if enabled else "av"),
                    )
            except Exception:
                pass
        else:
            # Återställ checkboxen om åtgärden misslyckades
            self._autostart_var.set(self.settings.get("autostart", False))
            messagebox.showwarning(
                APP_NAME,
                "Autostart kunde inte %s.\n"
                "Stöds på Windows (genväg i Autostart-mappen)."
                % ("aktiveras" if enabled else "avaktiveras"),
            )

    _AUTOSTART_HEAL_ATTEMPTS = 3

    def _apply_autostart(self, _attempt: int = 1) -> None:
        """
        Självläkande autostart-synk (A11 + v2.6.0 R2/R3).

        Körs vid start och ser till att HKCU Run-nyckeln stämmer mot
        inställningen:

          * autostart=True  men nyckel saknas/föråldrad  -> skrivs om.
          * autostart=False men en gammal nyckel ligger kvar -> rensas.

        Registret jämförs mot den ÖNSKADE kommandosträngen (via
        _autostart_registered_value()), så även en gammal sökväg till
        en flyttad python/skript upptäcks. Vid transienta fel görs upp
        till 3 försök med 1,5 s mellanrum (after) i stället för att
        ge upp direkt. Allt loggas konsol-fritt via safe_write().
        """
        if sys.platform != "win32":
            return
        try:
            want     = bool(self.settings.get("autostart", False))
            desired  = self._autostart_launcher_cmd() if want else ""
            current  = self._autostart_registered_value()
            needs_fix = False

            if want:
                needs_fix = (current != desired)
            else:
                # Vill inte ha autostart men en gammal nyckel finns kvar
                needs_fix = (current is not None)

            if not needs_fix:
                return

            ok = self._set_autostart(want)
            if ok:
                # Verifiera (skrivningen lyckades men nyckeln ska nu matcha)
                if not want or self._autostart_registered_value() == desired:
                    return
                ok = False
            if not ok:
                raise RuntimeError("registrering misslyckades")
        except Exception as exc:
            if _attempt < self._AUTOSTART_HEAL_ATTEMPTS:
                safe_write(
                    "[AUTOSTART] Synk-fel (%d/%d) vid start, "
                    "forsoker igen: %s"
                    % (_attempt, self._AUTOSTART_HEAL_ATTEMPTS, exc)
                )
                try:
                    self.after(
                        1500,
                        lambda: self._apply_autostart(_attempt + 1),
                    )
                except Exception:
                    pass
            else:
                safe_write(
                    "[AUTOSTART] Synk misslyckades efter %d forso: %s"
                    % (self._AUTOSTART_HEAL_ATTEMPTS, exc)
                )

    # ==========================================================================
    # JSON-INSTÄLLNINGAR (A2 + A10)
    # ==========================================================================

    def _default_settings(self) -> dict:
        """Fabriksinställningar (används vid korrupt/saknad settings.json)."""
        return {
            "theme":           "system",
            "mode":            "dev",
            "smart_cache":     True,
            "autostart":       False,
            "start_minimized": True,
            "_meta":           {"schema_version": 2},
            "folder":          "",
            "title":           "",
            "description":     "",
            "columns":         4,
            "thumbnail_size":  "300x300",
            "fullsize_max":    "1920x1080",
            "quality":         85,
            "preserve_exif":   False,
            "auto_rotate":     True,
            "ftp": {
                "enabled": False,
                "server":  "",
                "user":    "",
                "path":    "/public_html/gallery",
            },
        }

    def _load_all_settings(self) -> None:
        """
        Ladda config/settings.json med validering (A2).

        - Korrupt JSON → .corrupt-backup + fabriksinställningar.
        - Saknade fält → auto-repair till default.
        - Legacy-tema (auto/clam) → migreras till "system".
        - _meta.schema_version sätts till 1.
        """
        path = get_config_path() / SETTINGS_FILE
        raw = load_json(path, default=None)

        if raw is None or not isinstance(raw, dict):
            if path.exists():
                # Korrupt fil: säkra en backup innan vi skriver om
                try:
                    backup = get_config_path() / (
                        "settings.json.corrupt-%s"
                        % datetime.now().strftime("%Y%m%d_%H%M%S")
                    )
                    shutil.copy2(path, backup)
                    safe_write(
                        "[SETTINGS] Korrupt settings.json → backup: %s"
                        % backup.name
                    )
                except Exception as exc:
                    safe_write("[SETTINGS] Backup misslyckades: %s" % exc)
            self.settings = self._default_settings()
        else:
            self.settings = raw

        self._repair_settings()

    def _repair_settings(self) -> None:
        """Auto-repair: saknade fält, tema-migrering, schema_version."""
        changed = False

        theme = self.settings.get("theme", "system")
        if theme not in ("light", "dark", "system"):
            self.settings["theme"] = "system"   # migrera auto/clam
            changed = True

        if "mode" not in self.settings:
            self.settings["mode"] = "dev"
            changed = True

        if "smart_cache" not in self.settings:
            self.settings["smart_cache"] = True
            changed = True

        if "autostart" not in self.settings:
            self.settings["autostart"] = False
            changed = True

        if self.settings.get("start_minimized") is not True:
            self.settings["start_minimized"] = True
            changed = True

        meta = self.settings.get("_meta")
        if not isinstance(meta, dict) or meta.get("schema_version") < 2:
            self.settings["_meta"] = {"schema_version": 2}
            changed = True

        if "ftp" not in self.settings or not isinstance(
            self.settings.get("ftp"), dict
        ):
            self.settings["ftp"] = {
                "enabled": False,
                "server":  "",
                "user":    "",
                "path":    "/public_html/gallery",
            }
            changed = True

        if changed:
            save_json(get_config_path() / SETTINGS_FILE, self.settings)

    def _save_all_settings(self) -> None:
        """
        Spara alla JSON-filer atomiskt (A9).

        Sparar:
          - config/settings.json
          - config/plugin_states.json
          - config/tab_visibility.json (via TabVisibilityManager)
          - config/window_state.json   (via WindowStateManager)
        """
        cfg = get_config_path()
        save_json(cfg / SETTINGS_FILE,      self.settings)
        save_json(cfg / PLUGIN_STATES_FILE, dict(self.plugin_enabled))
        self._tab_vis_mgr.save()
        self._save_window_state()

    # Publika aliases för plugin-access
    def save_all_settings(self) -> None:
        """Publik alias för _save_all_settings()."""
        self._save_all_settings()

    def load_all_settings(self) -> None:
        """Publik alias för _load_all_settings()."""
        self._load_all_settings()

    # ==========================================================================
    # SMART CACHE (A4)
    # ==========================================================================

    def _cleanup_pycache(self) -> None:
        """
        Rensa __pycache__ + lösa .pyc/.pyo vid avslut i PROD-läge.

        M4: logiken flyttad till main_guards.cleanup_pycache()
        (skyddade mappar, symlink-säker, PROD-gate).
        """
        try:
            dirs, files = cleanup_pycache(
                get_base_path(),
                self.settings.get("mode", "dev"),
                self.settings.get("smart_cache", True),
            )
            if dirs or files:
                safe_write(
                    "[CACHE] Rensning klar: %s mappar, %s filer"
                    % (dirs, files)
                )
        except Exception as exc:
            safe_write("[CACHE] Rensning misslyckades: %s" % exc)

    # ==========================================================================
    # HJÄLPMETODER
    # ==========================================================================

    def _show_about(self) -> None:
        """Visa Om-dialog."""
        enabled = sum(1 for e in self.plugin_enabled.values() if e)
        messagebox.showinfo(
            "Om %s" % APP_NAME,
            "%s  v%s\n%s\n%s\n"
            "Plugins:  %s/%s aktiva\n"
            "Python:   %s\n"
            "Systray:  %s\n\n"
            "Loggfil:  logs/"
            % (
                APP_NAME,
                APP_VERSION,
                COPYRIGHT,
                "─" * 36,
                enabled,
                len(self.plugins),
                sys.version.split()[0],
                "Ja" if HAS_SYSTRAY else "Nej (pip install pystray)",
            ),
        )

    def _open_error_summary(self) -> None:
        from error_summary import summary_path
        import webbrowser
        collector = getattr(self, '_error_summary', None)
        if collector is not None:
            collector.collect()
        path = summary_path()
        path.touch(exist_ok=True)
        if sys.platform == "win32":
            os.startfile(path)
        else:
            webbrowser.open(path.as_uri())

    def _open_log_folder(self) -> None:
        """Öppna logs/-mappen i OS-filhanterare."""
        from app_paths import logs_dir
        log_dir = logs_dir()
        log_dir.mkdir(exist_ok=True)
        try:
            if sys.platform == "win32":
                os.startfile(log_dir)
            elif sys.platform == "darwin":
                import subprocess
                subprocess.Popen(["open", str(log_dir)])
            else:
                import subprocess
                subprocess.Popen(["xdg-open", str(log_dir)])
        except Exception as exc:
            messagebox.showerror(
                "Fel", "Kunde inte öppna loggmapp:\n%s" % exc
            )

# ==============================================================================
# STARTPUNKT
# ==============================================================================

if __name__ == "__main__":
    _startup_phase('Skapar huvudfönster')
    app = App()
    _startup_phase('Huvudfönster skapat', 'Minimerad start är normal; öppna via tray eller visa_app.pyw.')
    from error_summary import ErrorSummary
    app._error_summary = ErrorSummary().start()
    from release_scheduler import ReleaseScheduler
    app._release_scheduler = ReleaseScheduler(app, BASE_DIR)
    _startup_phase('Startar mainloop')
    app._safe_mainloop()   # M2: vaktad mainloop
    _startup_phase('Mainloop avslutad')
