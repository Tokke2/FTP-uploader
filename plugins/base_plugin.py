#!/usr/bin/env python3
# ============================================================
# Gallery Uploader - Basklass for plugins
# ============================================================
# FIL:       plugins/base_plugin.py
# PLATS:     plugins/ (ftp_gallery_uploader/plugins/base_plugin.py)
# Syfte:     Basklass som alla plugins KAN arva fran.
#            Ger sakerhetsmetoder, loggning, config-hardning,
#            tema-stod och hjalpfunktioner.
#            IGNORERAS av plugin-loadern (hardkodat undantag).
# VERSION:   1.4.1
# AUTHOR:    Rickard Längkvist
# COPYRIGHT: Copyright (c) <år> Rickard Längkvist (dynamiskt år,
#            se COPYRIGHT-konstanten nedan)
#
# ÄNDRINGAR v1.4.0 → v1.4.1 (KRASCHFIX - namnkollision):
#   [R1]      self._reg_panels/_reg_labels/_reg_buttons i __init__ SKUGGADE
#             metoderna def _reg_panels()/_reg_labels() som finns i fem
#             plugins (ui_settings, menu_manager, system_tray, watch_folder,
#             video_processor_ui). Följd: "TypeError: 'list' object is not
#             callable" i plugin.init() -> Inställningar, Bevakad mapp och
#             Videobearbetning fick inget UI alls (logg 2026-09-21 09:14).
#             Listorna heter nu _theme_reg_panels/_theme_reg_labels/
#             _theme_reg_buttons (unika namn, ingen plugin använder dem).
#   [R2]      Ny självkontroll: _detect_shadowing() hittar instansattribut
#             som skuggar en metod i klassen. Körs EN gång per plugin när
#             app finns (init(), första log()-anrop eller
#             register_theme_callback()) och loggar fynden som VARNING via
#             avancerad logger - aldrig till stderr före init. Fångar även
#             attribut som sätts i subklassens __init__/create_ui.
#
# ÄNDRINGAR v1.3.0 → v1.4.0 (fullt förbättringspass, KRAV 82-ordning:
#   korrekthet -> dataförlust -> stabilitet -> snabbhet -> UI/UX):
#
#   KORREKTHET / DATAFÖRLUST:
#   [G1]      save_config: ADOPT-1 komplett. Efter fsync läses tmp-filen
#           TILLBAKA och json-valideras INNAN os.replace - en trasig
#           skrivning kan därmed aldrig ersätta en frisk config.
#           Före replace roteras även .bak/.bak.1/.bak.2 (max 3).
#   [G2]      load_config: självläkning (ADOPT-1/2). Ogiltig JSON
#           karantänas som <fil>.corrupt-backup-<tid> och innehållet
#           återställs automatiskt från senaste läsbara .bak (loggas
#           som OK). Tom fil -> default.
#   [G3]      _meta.schema_version skrivs i varje config vid save och
#           plockas bort vid load (subklasser ser aldrig _meta).
#           Ny hook migrate_config(data) för versionerad migrering.
#           Klassflaggor: CONFIG_SCHEMA_VERSION, CONFIG_ADD_META,
#           CONFIG_MAX_BAK.
#   [G4]      log_error(exc): tracebanken formateras nu ur det SKICKADE
#           undantaget (format_exception), inte format_exc() som utanför
#           ett except-block gav "NoneType: None" och därmed tappade
#           själva tracebanken.
#
#   STABILITET:
#   [G5]      safe_after: after-id:n spåras och callbacken wrappas så att
#           ett fel i den loggas (EN gång) i stället för att nå Tk:s
#           callback-väg. cancel_after()/cancel_all_afters() nya;
#           cleanup() avbryter alla pending after-jobb.
#   [G6]      after_debounced(key, ms, cb): sammanfallande anrop
#           sammanfogas (nyckel -> senaste id), minskar after-spam från
#           worker-trådar (FS-2-mönstret, centralt).
#   [G7]      widget_exists/safe_widget_config fångar Exception (inte
#           bara TclError) - trasiga/förstörda referenser propagerar
#           aldrig ut i en Tk-callback (samma lärdom som P14-2).
#   [G8]      _report_once(key, level, msg): rapporterar ett återkommande
#           fel EN gång per nyckel - inget loggspam, inget tyst fel.
#   [G9]      TEMA-DISPATCH (FS-4): <<ThemeChanged>> binds EN gång per
#           app via en delad dispatcher med handler-register. Tidigare
#           ersatte varje app.bind(...) föregående bindning, så bara
#           SISTA pluginet fick tema-byten. register_theme_callback()
#           de-dupliceras och avregistreras i cleanup().
#
#   SNABBHET / MINNE:
#   [G10]     get_theme_colors()/get_theme_color(): TTL-cache (5 s) så
#           upprepade anrop (restyle, widget-bygge) inte slår mot
#           ThemeEngine varje gång; cachen invalideras vid temabyte.
#
#   UI/UX / DESIGN:
#   [G11]     make_button(color_attr=...): hover/leave löser färgen
#           dynamiskt ur attributnamnet (som ui_controls _make_btn) så
#           en hover efter temabyte inte återställer gammal färg.
#           Knappar/paneler/labels kan registreras (register_button/
#           register_panel/register_label) och omstylas centralt via
#           restyle_registered() vid temabyte.
#   [G12]     __repr__ + uptime_seconds() för enklare felsökning i logg.
#
# BEVARAT FRÅN v1.3.0:
#   log_ui()/log_lifecycle() med fallback till log("INFO", ...)
#   log(): två anropsstilar, fallback via _safe_write (ej print)
#   save_config/load_config: atomiskt mkstemp->fdopen->flush->fsync->
#       os.replace + helpers.get_config_path() (A9/A10)
#   bind_mousewheel: 3 enheter per klick (Windows/Linux/macOS)
#   make_button: gamla parametrar oförändrade (bg/fg/width/side/...)
#   safe_after returnerar after-id; darken = _darken_color-alias
#   init_ui()/on_closing()/refresh()/init_menu()-aliasen
#   Ingen print() - all loggning via logger eller _safe_write
#
# IGNORERAS av load_plugins() via:
#   name == "base_plugin"
#
# IMPORTER:
#   tkinter as tk
#   sys, os, json, traceback, tempfile, threading, shutil, time
#   pathlib.Path, datetime
#   helpers: get_config_path (valfritt, A10)
# ============================================================


import app_paths
from media_support import register_heif
register_heif()
import tkinter as tk
import sys
import os
import json
import traceback
import tempfile
import threading
import shutil
import time
from pathlib import Path
from datetime import datetime

# -- Helpers (valfritt – för config-sökväg, A10) ---------------
try:
    from helpers import get_config_path as _helpers_config_path
    _HAS_HELPERS = True
except ImportError:
    _HAS_HELPERS = False


def _safe_write(message: str) -> None:
    """
    Skriv ett meddelande utan att krascha om stderr ar stangd.

    Intern hjalpfunktion - anvands av BasePlugin.log()
    som sista fallback nar logger saknas.
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
        with open(app_paths.logs_dir() / "base_plugin_errors.log", "a",
                  encoding="utf-8") as f:
            from log_clock import timestamp
            f.write("[%s] %s\n" % (timestamp(), message))
    except Exception:
        pass


# ==============================================================================
# TEMA-DISPATCH (G9) - EN bindning, alla plugins
# ==============================================================================
# tkinter-bindning pa samma sekvens ERSATTER foregaende bindning. Nar varje
# plugin band "<<ThemeChanged>>" pa appen fick darfor bara det SISTA
# pluginet temat bytt. Har: en delad dispatcher binds en gang per app och
# anropar alla registrerade handlers i ordning.

_THEME_HANDLERS = []
_THEME_DISPATCH_APP = {"app": None}
_THEME_BUSY = {"on": False}


def _theme_dispatcher(event=None):
    """Anropa alla registrerade tema-handlers. Kraschar aldrig."""
    if _THEME_BUSY["on"]:
        return
    _THEME_BUSY["on"] = True
    try:
        _theme_dispatcher_run(event)
    finally:
        _THEME_BUSY["on"] = False


def _theme_dispatcher_run(event=None):
    for handler in list(_THEME_HANDLERS):
        try:
            handler(event)
        except Exception:
            pass


def dispatch_theme_changed(app=None):
    """
    Kor alla plugin-restyles. Anropas fran App.apply_theme sa att
    en stulen app.bind(<<ThemeChanged>>) inte kan hoppa over plugins.
    """
    if app is not None:
        try:
            app.bind("<<ThemeChanged>>", _theme_dispatcher, add="+")
            _THEME_DISPATCH_APP["app"] = app
        except Exception:
            pass
    _theme_dispatcher()


class BasePlugin:
    """
    Basklass for alla Gallery Uploader-plugins.

    PLUGIN-KONTRAKT:
      Obligatoriskt:
        PLUGIN_NAME: str   - Visas i logg och meny
      Valfritt:
        PRIORITY:   int    - Korordning (default=100, lagre=tidigare)
        VERSION:    str    - Versionssrang
        TAB_NAME:   str    - Om pluginet skapar en tabb

      Valfria metoder (override efter behov):
        init(app)             - Initiering, bygg UI
        execute(context, log) - Pipeline-steg
        cleanup()             - Stadning vid avslutning
        migrate_config(data)  - Migrera laddad config (G3)
        on_theme_changed(ev)  - Reagera pa temabyte

    Startsekvens:
      1. main.py instansierar plugin via cls()
      2. main.py anropar plugin.init(app) i PRIORITY-ordning
      3. Pipeline anropar plugin.execute(context, log_func)
      4. Vid avslutning: plugin.cleanup()
    """

    # -- Klassattribut - override i subklass -------------------
    PLUGIN_NAME = "Base Plugin"
    PRIORITY    = 100
    VERSION     = "1.4.2"
    AUTHOR      = "Rickard Längkvist"
    COPYRIGHT   = "Copyright (c) %d %s" % (datetime.now().year, "Rickard Längkvist")
    TAB_NAME    = None

    # -- Config-hardning (G1-G3) -------------------------------
    CONFIG_SCHEMA_VERSION = 1     # skrivs i _meta.schema_version
    CONFIG_ADD_META       = True  # False = skriv ingen _meta alls
    CONFIG_MAX_BAK        = 3     # .bak, .bak.1, .bak.2

    # -- Temacache (G10) ---------------------------------------
    THEME_CACHE_TTL = 5.0         # sekunder

    # -- Fargkonstanter (B1: inga hardkodade hex i widgets) ----
    COLOR_BUTTON_BG = "#374151"
    COLOR_BUTTON_FG = "#ffffff"

    # ==========================================================================
    # INITIERING
    # ==========================================================================

    def __init__(self):
        """
        Grundinitiering - anropas av plugin-loadern.
        Satt inte upp UI har (app finns inte an).
        """
        self.app                   = None
        self.is_active             = False
        self._mousewheel_unbinders = []

        # Config (G1-G3)
        self._config_lock = threading.RLock()
        self._config_meta = {}

        # After-jobb (G5/G6)
        self._after_ids    = set()
        self._debounce_ids = {}

        # Engangsrapporter (G8)
        self._seen_reports = set()

        # Tema (G9-G11)
        # OBS R1: heter INTE _reg_panels/_reg_labels - de namnen används
        # som METODER i fem plugins och skulle skuggas av instansattribut.
        self._theme_cache       = None
        self._theme_bound       = False
        self._theme_reg_panels  = []
        self._theme_reg_labels  = []
        self._theme_reg_buttons = []

        # Livscykel (G12)
        self._activate_time = None

        # Namnkollisionskontroll (R2): forsta soken efter BasePlugins egna
        # attribut (R1-klassen av fel) goras har - rapporteras senare, nar
        # app/logger finns. En andra sokning i log() fångar även attribut
        # som subklassen satter i sin __init__/create_ui.
        self._shadow_warnings = self._detect_shadowing()
        self._shadow_checked  = False

    def init(self, app) -> None:
        """
        Initiera plugin med app-referens.

        Anropas av main.py i PRIORITY-ordning EFTER att
        alla plugins har instansierats.

        Override i subklass for att:
          - Bygga UI
          - Ladda installningar
          - Registrera self i app.context
        Kom ihag: anropa super().init(app) forst.

        Parametrar:
            app: Huvudapplikationen (tk.Tk)
        """
        self.app       = app
        self.is_active = True
        if self._activate_time is None:
            self._activate_time = datetime.now()

    def init_ui(self, app) -> None:
        """Alias for init() - bakatkompatibilitet."""
        self.init(app)

    def init_menu(self, app) -> None:
        """
        Lagg till menyalternativ.
        Override i subklass om menyer behovs.
        """
        pass

    # ==========================================================================
    # PIPELINE
    # ==========================================================================

    def execute(self, context: dict, log=None) -> dict:
        """
        Kor plugin-logik i pipeline.

        VIKTIGT:
          - Returnera ALLTID context (BUG-002: aldrig None)
          - Satt context-nycklar for nasta plugin

        Parametrar:
            context: Delad data-dict
            log:     Valfri callback(str)

        Returnerar:
            context (uppdaterad eller oforandrad)
        """
        return context

    # ==========================================================================
    # LIVSCYKEL
    # ==========================================================================

    def cleanup(self) -> None:
        """
        Stada upp nar appen stangs. Idempotent.

        Override i subklass for att:
          - Stanga oppna filer
          - Stoppa bakgrundstradar
          - Spara installningar
        Anropa super().cleanup() sist.

        Anropas av main.py i quit_app().
        """
        self.is_active = False
        self.cancel_all_afters()
        self.unbind_all_mousewheels()
        try:
            if self._theme_event in _THEME_HANDLERS:
                _THEME_HANDLERS.remove(self._theme_event)
        except Exception:
            pass

    def on_closing(self) -> None:
        """Alias for cleanup() - bakatkompatibilitet."""
        self.cleanup()

    def refresh(self) -> None:
        """
        Uppdatera UI efter tema-byte eller data-andring.
        Override i subklass om pluginet reagerar pa <<ThemeChanged>>.
        """
        pass

    def uptime_seconds(self) -> float:
        """Sekunder sedan init(app) - 0.0 om pluginet aldrig initierats."""
        if self._activate_time is None:
            return 0.0
        return (datetime.now() - self._activate_time).total_seconds()

    def __repr__(self) -> str:
        """Felsokningsvanlig representation for logg/debug."""
        return "<%s v%s active=%s>" % (
            self.PLUGIN_NAME, self.VERSION, self.is_active
        )

    # ==========================================================================
    # LOGGNING
    # ==========================================================================

    def log(self, level_or_message: str, message: str = "") -> None:
        """
        Logga ett meddelande via advanced_logger.

        Stoder tva anropsstilar:
            self.log("INFO", "Klart!")   - med niva
            self.log("Klart!")           - bara meddelande (-> INFO)

        Nivaer: DEBUG, INFO, VARNING, FEL, OK, SYSTEM, PLUGIN

        Fallback (ingen logger):
          _safe_write() - skriver till stderr/loggfil (ALDRIG print())
        """
        if self.app and not self._shadow_checked:
            self._check_shadowing()

        known_levels = {
            "DEBUG", "INFO", "VARNING", "FEL", "OK",
            "SYSTEM", "PLUGIN", "PIPELINE", "CONTEXT",
            "WARNING", "ERROR", "CRITICAL", "SUCCESS",
        }

        if message:
            level = level_or_message.upper()
            msg   = message
        elif level_or_message.upper() in known_levels:
            level = level_or_message.upper()
            msg   = ""
        else:
            level = "INFO"
            msg   = level_or_message

        if not msg:
            return

        prefixed = "[%s] %s" % (self.PLUGIN_NAME, msg)

        # Forsok via advanced_logger
        if self.app and hasattr(self.app, "context"):
            logger = self.app.context.get("_logger")
            if logger and hasattr(logger, "log"):
                try:
                    logger.log(level, prefixed)
                    return
                except Exception:
                    pass

        # Fallback: _safe_write (aldrig print())
        _safe_write("[%s] %s" % (level, prefixed))

    def log_action(self, message: str) -> None:
        """Logga en atgard pa INFO-niva. Bakatkompatibel."""
        self.log("INFO", message)

    def log_error(self, message: str, exc: Exception = None) -> None:
        """
        Logga ett fel, valfritt med traceback.

        G4: tracebanken byggs ur det SKICKADE undantaget sa att den
        blir korrekt aven nar log_error anropas utanfor ett except-block.

        Parametrar:
            message: Felbeskrivning
            exc:     Undantag (valfritt)
        """
        self.log("FEL", message)
        if exc is not None:
            tb = "".join(
                traceback.format_exception(
                    type(exc), exc, getattr(exc, "__traceback__", None)
                )
            )
            if tb.strip():
                self.log("DEBUG", "Traceback:\n%s" % tb)

    def log_debug(self, message: str)   -> None: self.log("DEBUG",   message)
    def log_warning(self, message: str) -> None: self.log("VARNING", message)
    def log_success(self, message: str) -> None: self.log("OK",      message)

    # -- Namnkollisionskontroll (R2) ---------------------------

    def _detect_shadowing(self) -> list:
        """
        Hitta instansattribut som skuggar en metod (R2).

        Bakgrund (R1): BasePlugin.__init__ satte self._reg_panels = []
        medan fem plugins har def _reg_panels(). Instansattribut vinner
        alltid over klassmetoder -> "TypeError: 'list' object is not
        callable" nar pluginet anropade self._reg_panels(widget).

        Returnerar lista med "namn (skuggar Klass.namn)" - tom = OK.
        Kostar en dict-iteration och kors EN gang per plugininstans.
        """
        bad = []
        try:
            cls = type(self)
            for name in list(self.__dict__):
                if name.startswith("_shadow") or name.startswith("__"):
                    continue
                if callable(getattr(cls, name, None)):
                    bad.append("%s (skuggar %s.%s)"
                               % (name, cls.__name__, name))
        except Exception:
            return []
        return bad

    def _check_shadowing(self) -> None:
        """
        Kor skuggningskontrollen EN gang nar app/logger finns (R2).

        Anropas fran init(), log() och register_theme_callback() - det
        gor att aven attribut som satts i subklassens __init__ eller
        create_ui() hinns med (BasePlugin.__init__ kor for tidigt).
        """
        if self._shadow_checked:
            return
        self._shadow_checked = True
        for item in self._detect_shadowing():
            if item not in self._shadow_warnings:
                self._shadow_warnings.append(item)
        self._flush_shadow_warnings()

    def _flush_shadow_warnings(self) -> None:
        """Logga upptackta namnkollisioner EN gang (R2)."""
        pending = self._shadow_warnings
        self._shadow_warnings = []
        for item in pending:
            self.log("VARNING", "Namnkollision: self.%s" % item)

    def _report_once(self, key: str, level: str, message: str) -> None:
        """
        Rapportera ett aterkommande fel EN gang per nyckel (G8).

        Anvands for fel som annars skulle loggas tusentals ganger
        (t.ex. en widget som saknas i varje write_log-anrop).

        Parametrar:
            key:     Unik nyckel for felet (t.ex. "write_log")
            level:   Loggniva
            message: Meddelande
        """
        if key in self._seen_reports:
            return
        self._seen_reports.add(key)
        self.log(level, message)

    def log_ui(self, action: str, detail: str = "") -> None:
        """
        Logga en UI-händelse via advanced_logger.log_ui().

        Anropsstil:
            self.log_ui("KLICK", "Start")
            self.log_ui("FLIK",  "Galleri")

        Fallback: self.log("INFO", ...) om loggern saknar log_ui().
        """
        logger = self.get_logger()
        if logger and hasattr(logger, "log_ui"):
            try:
                logger.log_ui(action, detail)
                return
            except Exception:
                pass
        msg = "UI: %s" % action
        if detail:
            msg += " -> %s" % detail
        self.log("INFO", msg)

    def log_lifecycle(self, event: str, detail: str = "") -> None:
        """
        Logga en fönster-/livscykelhändelse via advanced_logger.

        Anropsstil:
            self.log_lifecycle("visa", "deiconify")
            self.log_lifecycle("dolj", "start_minimized")

        Fallback: self.log("INFO", ...) om loggern saknar metoden.
        """
        logger = self.get_logger()
        if logger and hasattr(logger, "log_lifecycle"):
            try:
                logger.log_lifecycle(event, detail)
                return
            except Exception:
                pass
        msg = "LIVSCYKEL: %s" % event
        if detail:
            msg += " | %s" % detail
        self.log("INFO", msg)

    # ==========================================================================
    # SAKRA UI-METODER
    # ==========================================================================

    def safe_after(self, delay: int, callback):
        """
        Saker version av app.after() (G5).

        Callbacken wrappas: ett undantag i den loggas EN gang via
        _report_once i stallet for att na Tk:s callback-vag (som under
        pythonw kan betyda WinError 6 och dod mainloop).

        Parametrar:
            delay:    Fordrojning i millisekunder
            callback: Funktion att anropa

        Returnerar:
            after-id (kan avbrytas med cancel_after) eller None
        """
        if not self.is_active or not self.app:
            return None
        try:
            if not self.app.winfo_exists():
                return None

            aid_box = {}

            def _wrapped(*args):
                aid = aid_box.get("id")
                if aid is not None:
                    self._after_ids.discard(aid)
                try:
                    return callback(*args)
                except Exception as exc:
                    self._report_once(
                        "after:%s" % getattr(callback, "__name__", "?"),
                        "FEL",
                        "Fel i after-callback: %s" % exc,
                    )
                    return None

            aid = self.app.after(delay, _wrapped)
            aid_box["id"] = aid
            self._after_ids.add(aid)
            return aid
        except Exception:
            return None

    def cancel_after(self, after_id) -> None:
        """Avbryt ett after-jobb och glom dess id (G5)."""
        if after_id is None:
            return
        self._after_ids.discard(after_id)
        for key, val in list(self._debounce_ids.items()):
            if val == after_id:
                self._debounce_ids.pop(key, None)
        if not self.app:
            return
        try:
            self.app.after_cancel(after_id)
        except Exception:
            pass

    def cancel_all_afters(self) -> None:
        """Avbryt alla pending after-jobb. Anropas av cleanup() (G5)."""
        ids = list(self._after_ids)
        self._after_ids.clear()
        self._debounce_ids.clear()
        if not self.app:
            return
        for aid in ids:
            try:
                self.app.after_cancel(aid)
            except Exception:
                pass

    def after_debounced(self, key: str, delay: int, callback):
        """
        Debouncad after: senaste anropet per nyckel vinner (G6).

        Anvand for att sammanfoga snabbt upprepade UI-uppdateringar
        fran worker-tradar (t.ex. progress/logg) sa att UI-traden
        inte bombarderas med after-jobb.

        Parametrar:
            key:      Nyckel som identifierar anropsserien
            delay:    Fordrojning i ms
            callback: Funktion att anropa

        Returnerar:
            after-id eller None
        """
        prev = self._debounce_ids.pop(key, None)
        if prev is not None:
            self.cancel_after(prev)
        aid = self.safe_after(delay, callback)
        if aid is not None:
            self._debounce_ids[key] = aid
        return aid

    def safe_update(self) -> None:
        """Saker update_idletasks(). Kraschar inte om appen stangs."""
        if not self.is_active or not self.app:
            return
        try:
            if self.app.winfo_exists():
                self.app.update_idletasks()
        except Exception:
            pass

    def widget_exists(self, widget) -> bool:
        """
        Kontrollera om en widget existerar och ar giltig (G7).

        Fangar Exception (inte bara TclError): en trasig eller redan
        forstord referens ska aldrig propagera ut i en Tk-callback.

        Returnerar:
            True om widget finns
        """
        if widget is None:
            return False
        try:
            return bool(widget.winfo_exists())
        except Exception:
            return False

    def safe_widget_config(self, widget, **kwargs) -> bool:
        """
        Konfigurera widget om den existerar (G7).

        Returnerar:
            True om konfigurationen lyckades
        """
        if not self.widget_exists(widget):
            return False
        try:
            widget.config(**kwargs)
            return True
        except Exception:
            return False

    # ==========================================================================
    # MUSHJUL
    # ==========================================================================

    def bind_mousewheel(self, widget, units: int = 3) -> None:
        """
        Bind mushjuls-scroll till en widget (via Enter/Leave).

        3 enheter per klick (Windows/Linux).
        Avbindningen sker automatiskt vid Leave och cleanup().

        Parametrar:
            widget: Canvas, Text, Listbox eller scrollbar-widget
            units:  Antal enheter per hjulklick (standard: 3)
        """
        if not self.widget_exists(widget):
            return

        def _scroll(event):
            if not self.is_active:
                return
            if not self.widget_exists(widget):
                return
            try:
                if sys.platform == "darwin":
                    widget.yview_scroll(-1 * event.delta, "units")
                elif sys.platform == "win32":
                    direction = -1 if event.delta > 0 else 1
                    widget.yview_scroll(direction * units, "units")
                else:
                    if event.num == 4:
                        widget.yview_scroll(-units, "units")
                    else:
                        widget.yview_scroll(units, "units")
            except Exception:
                pass

        def _bind(event=None):
            if not self.is_active or not self.widget_exists(widget):
                return
            widget.bind("<MouseWheel>", _scroll)
            widget.bind("<Button-4>",   _scroll)
            widget.bind("<Button-5>",   _scroll)

        def _unbind(event=None):
            try:
                if self.widget_exists(widget):
                    widget.unbind("<MouseWheel>")
                    widget.unbind("<Button-4>")
                    widget.unbind("<Button-5>")
            except Exception:
                pass

        widget.bind("<Enter>", _bind)
        widget.bind("<Leave>", _unbind)
        self._mousewheel_unbinders.append(_unbind)

    def unbind_all_mousewheels(self) -> None:
        """
        Avbind alla mushjuls-bindningar.
        Anropas automatiskt av cleanup().
        """
        for unbind in self._mousewheel_unbinders:
            try:
                unbind()
            except Exception:
                pass
        self._mousewheel_unbinders.clear()

    # ==========================================================================
    # CONTEXT-HANTERING
    # ==========================================================================

    def get_context_value(self, key: str, default=None):
        """Hamta ett varde fran app.context."""
        if self.app and hasattr(self.app, "context"):
            return self.app.context.get(key, default)
        return default

    def set_context_value(self, key: str, value) -> None:
        """Satt ett varde i app.context."""
        if self.app and hasattr(self.app, "context"):
            self.app.context[key] = value

    def get_logger(self):
        """Hamta advanced_logger-instansen."""
        return self.get_context_value("_logger")

    def get_tab_manager(self):
        """Hamta tab_manager-instansen."""
        return self.get_context_value("_tab_manager")

    def get_settings(self):
        """Hamta ui_settings-instansen."""
        return self.get_context_value("_settings")

    # ==========================================================================
    # JSON-HANTERING (A9 + A10 + G1-G3)
    # ==========================================================================

    def migrate_config(self, data):
        """
        Migrera laddad config till aktuell schema-version (G3).

        Override i subklass: kontrollera data.get("_schema") eller
        egen versionsnyckel och normalisera/saknade falt. Returnera
        alltid den migrerade datan.

        Parametrar:
            data: Laddad dict/list

        Returnerar:
            Migrerad data
        """
        return data

    def load_config(self, filename: str, default: dict = None):
        """
        Ladda JSON fran config/-mappen med sjalvlakning (G2).

        Flode:
          1. Las filen. Ogiltig JSON -> karantanas som
             <fil>.corrupt-backup-<tid> och backup provas.
          2. Saknas filen/oläsbar -> senaste läsbara .bak aterstalls
             (loggas som OK) och anvands.
          3. _meta plockas bort (G3) och migrate_config() kors.
          4. Annars: default.copy()

        Parametrar:
            filename: Filnamn (t.ex. "video_settings.json")
            default:  Standardvarde om filen saknas

        Returnerar:
            Laddad (migrerad) data eller default
        """
        if default is None:
            default = {}

        config_path = self.get_config_path() / filename

        with self._config_lock:
            data = self._read_json(config_path, filename)

            if data is None:
                data = self._restore_from_backup(config_path, filename)

            if data is None:
                return default.copy()

            if isinstance(data, dict) and "_meta" in data:
                self._config_meta[filename] = data.pop("_meta", None)

            try:
                migrated = self.migrate_config(data)
                if migrated is not None:
                    data = migrated
            except Exception as e:
                self.log(
                    "VARNING",
                    "migrate_config(%s) misslyckades: %s" % (filename, e),
                )
            return data

    def _read_json(self, path: Path, filename: str):
        """
        Las och parsa JSON. Returnerar None vid fel (G2).

        Vid JSONDecodeError karantanas filen sa att nasta save
        börjar fran friskt state och sa att anvandaren kan inspektera
        den trasiga filen.
        """
        try:
            if not path.exists():
                return None
            text = path.read_text(encoding="utf-8")
            if not text.strip():
                return None
            return json.loads(text)
        except json.JSONDecodeError as e:
            self.log("VARNING", "Ogiltig JSON i %s: %s" % (filename, e))
            self._quarantine(path, filename)
            return None
        except PermissionError as e:
            self.log("VARNING", "Behorighetsfel %s: %s" % (filename, e))
            return None
        except Exception as e:
            self.log("VARNING", "Kunde inte lasa %s: %s" % (filename, e))
            return None

    def _quarantine(self, path: Path, filename: str) -> None:
        """Flytta undan en trasig config sa att den kan inspekteras."""
        try:
            stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            target = path.with_name(
                "%s.corrupt-backup-%s" % (path.name, stamp)
            )
            os.replace(path, target)
            self.log(
                "VARNING",
                "Trasig config karantänad: %s" % target.name,
            )
        except Exception:
            pass

    def _backup_name(self, path: Path, index: int) -> Path:
        """Namn pa backup-fil: <fil>.bak, <fil>.bak.1, ..."""
        return Path(str(path) + (".bak" if index == 0 else ".bak.%d" % index))

    def _restore_from_backup(self, path: Path, filename: str):
        """
        Aterstall fran senaste läsbara .bak (G2-sjalvlakning).

        Backupen kopieras tillbaka till originalfilen sa att state
        blir konsekvent aven for verktyg som läser filen direkt.
        .bak ar NYAST och .bak.N aldst - darfor provas index 0 forst.

        Returnerar:
            Laddad data eller None
        """
        for index in range(0, max(1, self.CONFIG_MAX_BAK)):
            cand = self._backup_name(path, index)
            if not cand.exists():
                continue
            try:
                data = json.loads(cand.read_text(encoding="utf-8"))
            except Exception:
                continue
            try:
                shutil.copy2(cand, path)
            except Exception:
                pass
            self.log(
                "OK",
                "Självläkning: %s återställd från %s"
                % (filename, cand.name),
            )
            return data
        return None

    def save_config(self, filename: str, data: dict) -> bool:
        """
        Spara data till JSON atomiskt med verifiering (A9 + G1).

        Monster: mkstemp -> fdopen -> flush -> fsync ->
                 läs tillbaka + json-validera ->
                 rotera .bak -> os.replace.

        En trasig skrivning kan därmed ALDRIG ersätta en frisk config,
        och foregaende versioner finns i .bak/.bak.1/.bak.2.
        _meta.schema_version läggs till om CONFIG_ADD_META (G3).

        Parametrar:
            filename: Filnamn
            data:     Data att spara

        Returnerar:
            True vid lyckat sparande
        """
        config_dir  = self.get_config_path()
        config_path = config_dir / filename
        tmp_path    = None

        try:
            with self._config_lock:
                config_dir.mkdir(parents=True, exist_ok=True)

                payload = data
                if isinstance(data, dict) and self.CONFIG_ADD_META:
                    payload = dict(data)
                    payload["_meta"] = {
                        "schema_version": self.CONFIG_SCHEMA_VERSION,
                        "saved": datetime.now().strftime(
                            "%Y-%m-%dT%H:%M:%S"
                        ),
                        "writer": "%s v%s" % (
                            self.PLUGIN_NAME, self.VERSION
                        ),
                    }

                fd, tmp_str = tempfile.mkstemp(
                    dir=config_dir,
                    prefix=".%s_" % Path(filename).stem,
                    suffix=".tmp",
                )
                tmp_path = Path(tmp_str)

                with os.fdopen(fd, "w", encoding="utf-8") as f:
                    json.dump(payload, f, ensure_ascii=False, indent=2)
                    f.flush()
                    os.fsync(f.fileno())   # A9

                # G1: verifiera att tmp-filen verkligen är läsbar JSON
                with open(tmp_path, "r", encoding="utf-8") as f:
                    json.load(f)

                self._rotate_backups(config_path)
                os.replace(tmp_path, config_path)
                tmp_path = None
                return True

        except Exception as e:
            if tmp_path is not None and tmp_path.exists():
                try:
                    tmp_path.unlink()
                except OSError:
                    pass
            self.log("FEL", "Kunde inte spara %s: %s" % (filename, e))
            return False

    def _rotate_backups(self, path: Path) -> None:
        """
        Rotera .bak-filer före replace (G1).

        Aldsta backupen (.bak.N-1) tas bort, ovriga shiftas ett steg
        (.bak.i -> .bak.i+1) och nuvarande fil kopieras till .bak.
        Max CONFIG_MAX_BAK stycken.
        """
        try:
            if self.CONFIG_MAX_BAK <= 0 or not path.exists():
                return
            last = self.CONFIG_MAX_BAK - 1
            oldest = self._backup_name(path, last)
            if oldest.exists():
                oldest.unlink()
            for i in range(last, 0, -1):
                src = self._backup_name(path, i - 1)
                if src.exists():
                    os.replace(src, self._backup_name(path, i))
            shutil.copy2(path, self._backup_name(path, 0))
        except Exception:
            pass

    # ==========================================================================
    # SOKVAGAR (A10)
    # ==========================================================================

    def ensure_path(self, path) -> Path:
        """Sakerstall att en katalog existerar."""
        p = Path(path)
        p.mkdir(parents=True, exist_ok=True)
        return p

    def get_base_path(self) -> Path:
        """Returnera projektrotens absoluta sokvag."""
        return Path(__file__).parent.parent.resolve()

    def get_config_path(self) -> Path:
        """
        Returnera config/-mappens Path (A10).

        Anvander helpers.get_config_path() om tillgangligt,
        annars projektrotens config/.
        """
        if _HAS_HELPERS:
            try:
                return _helpers_config_path()
            except Exception:
                pass
        p = app_paths.config_dir()
        p.mkdir(parents=True, exist_ok=True)
        return p

    def get_logs_path(self) -> Path:
        """Returnera logs/-mappens Path."""
        p = app_paths.logs_dir()
        p.mkdir(parents=True, exist_ok=True)
        return p

    # ==========================================================================
    # TEMA (G9-G11)
    # ==========================================================================

    def get_theme_colors(self) -> dict:
        """
        Hamta aktuella temafarger fran ThemeEngine (TTL-cachade, G10).

        Returnerar:
            Dict med fargnycklar eller tom dict
        """
        now = time.monotonic()
        if self._theme_cache is not None:
            colors, stamp = self._theme_cache
            if (now - stamp) < self.THEME_CACHE_TTL:
                return colors

        colors = {}
        if self.app and hasattr(self.app, "theme_engine"):
            try:
                colors = self.app.theme_engine.get_colors() or {}
            except Exception:
                colors = {}
        self._theme_cache = (colors, now)
        return colors

    def get_theme_color(
        self, key: str, fallback: str = "#888888"
    ) -> str:
        """
        Hamta en specifik temafarg.

        Parametrar:
            key:      Fargnyckel (t.ex. "bg", "accent")
            fallback: Varde om nyckeln saknas

        Returnerar:
            Hex-fargstrang
        """
        return self.get_theme_colors().get(key, fallback)

    def invalidate_theme_cache(self) -> None:
        """Tvinga nästa get_theme_colors() att läsa om från engine."""
        self._theme_cache = None

    def on_theme_changed(self, event=None) -> None:
        """
        Anropas nar temat byts (<<ThemeChanged>>-event).
        Override i subklass for att uppdatera plugin-specifika farger.
        """
        pass

    def _theme_event(self, event=None) -> None:
        """
        Intern tema-handler: cache + centralt restyle + subklass (G9).
        """
        self.invalidate_theme_cache()
        try:
            loader = getattr(self, "_load_theme_colors", None)
            if callable(loader):
                loader()
        except Exception:
            pass
        self.restyle_registered()
        try:
            self.on_theme_changed(event)
        except Exception as exc:
            self._report_once(
                "on_theme_changed",
                "FEL",
                "on_theme_changed fel: %s" % exc,
            )

    def register_theme_callback(self) -> None:
        """
        Registrera pluginet for <<ThemeChanged>>-event (G9).

        Bindningen sker EN gang per app via den delade dispatchern
        (_theme_dispatcher) - tidigare ersatte varje app.bind()
        foregaende bindning sa att bara sista pluginet fick temat.

        Anropa fran init():
            self.register_theme_callback()
        """
        if not self.app:
            return
        self._check_shadowing()
        if self._theme_event not in _THEME_HANDLERS:
            _THEME_HANDLERS.append(self._theme_event)
        try:
            self.app.bind("<<ThemeChanged>>", _theme_dispatcher, add="+")
            _THEME_DISPATCH_APP["app"] = self.app
            self._theme_bound = True
        except Exception:
            pass

    # -- Centralt restyle-register (FS-4 / G11) ----------------

    def register_panel(self, widget) -> None:
        """Registrera en panel (LabelFrame/Frame) for tema-restyle."""
        if widget is not None and widget not in self._theme_reg_panels:
            self._theme_reg_panels.append(widget)

    def register_label(self, widget) -> None:
        """Registrera en label for tema-restyle (bg + fg)."""
        if widget is not None and widget not in self._theme_reg_labels:
            self._theme_reg_labels.append(widget)

    def register_button(self, widget, color_attr=None, fg=None) -> None:
        """
        Registrera en knapp for tema-restyle (G11).

        Parametrar:
            widget:     tk.Button
            color_attr: Attributnamn pa klassen/instansen som haller
                        bakgrundsfargen (loser dynamiskt vid restyle)
            fg:         Textfarg (None = COLOR_BUTTON_FG)
        """
        if widget is None:
            return
        for item in self._theme_reg_buttons:
            if item[0] is widget:
                return
        self._theme_reg_buttons.append(
            (widget, color_attr, self.COLOR_BUTTON_BG, fg)
        )

    def restyle_registered(self) -> None:
        """
        Applicera aktuella temafarger pa registrerade widgets (G11).

        Anropas automatiskt vid <<ThemeChanged>> via _theme_event.
        """
        colors = self.get_theme_colors()
        bg = colors.get("bg", self.COLOR_BUTTON_BG)
        fg = colors.get("fg", self.COLOR_BUTTON_FG)

        for w in list(self._theme_reg_panels):
            if not self.widget_exists(w):
                self._theme_reg_panels.remove(w)
                continue
            self.safe_widget_config(w, bg=bg)

        for w in list(self._theme_reg_labels):
            if not self.widget_exists(w):
                self._theme_reg_labels.remove(w)
                continue
            self.safe_widget_config(w, bg=bg, fg=fg)

        for widget, color_attr, const_bg, const_fg in list(
            self._theme_reg_buttons
        ):
            if not self.widget_exists(widget):
                self._theme_reg_buttons.remove(
                    (widget, color_attr, const_bg, const_fg)
                )
                continue
            c = const_bg
            if color_attr:
                c = getattr(self, color_attr, const_bg)
            self.safe_widget_config(
                widget,
                bg=c,
                fg=const_fg or fg,
                activebackground=self._darken_color(c),
                activeforeground=const_fg or fg,
            )

    # ==========================================================================
    # KNAPPAR (G11)
    # ==========================================================================

    def make_button(
        self,
        parent,
        text: str,
        command,
        bg: str    = None,
        fg: str    = None,
        width: int = None,
        side: str  = None,
        padx       = 4,
        pady       = 3,
        font       = ("Segoe UI", 10, "bold"),
        color_attr: str = None,
    ) -> tk.Button:
        """
        Gemensam knapp-fabrik med hover-effekt.

        Hover-farg beraknas automatiskt (25% morkare).
        Default-farger fran COLOR_BUTTON_BG/COLOR_BUTTON_FG (B1/C4).

        G11: color_attr=... gor att hover/leave loser bakgrundsfargen
        dynamiskt ur attributet (t.ex. "COLOR_GREEN") sa att en hover
        efter temabyte inte återställer en gammal färg. Knappen
        registreras även för centralt restyle.

        Parametrar:
            parent:  Foraldra-widget
            text:    Knapptext
            command: Callback-funktion
            bg:      Bakgrundsfarg (hex)
            fg:      Textfarg (hex)
            width:   Bredd i tecken (None = auto)
            side:    pack()-sida (None = pack anropas ej)
            padx:    Inre horisontell padding
            pady:    Inre vertikal padding
            font:    Typsnitt
            color_attr: Attributnamn for dynamisk bakgrundsfarg

        Returnerar:
            tk.Button
        """
        if color_attr:
            bg = getattr(self, color_attr, bg or self.COLOR_BUTTON_BG)
        if bg is None:
            bg = self.COLOR_BUTTON_BG
        if fg is None:
            fg = self.COLOR_BUTTON_FG

        hover_bg = self._darken_color(bg)

        def _resolved():
            if color_attr:
                c = getattr(self, color_attr, self.COLOR_BUTTON_BG)
                return c, self._darken_color(c)
            return bg, hover_bg

        kwargs = dict(
            text=text,
            command=command,
            bg=bg,
            fg=fg,
            activebackground=hover_bg,
            activeforeground=fg,
            relief=tk.FLAT,
            cursor="hand2",
            font=font,
            padx=padx,
            pady=pady,
        )
        if width is not None:
            kwargs["width"] = width

        btn = tk.Button(parent, **kwargs)
        btn.bind(
            "<Enter>",
            lambda e: self.safe_widget_config(btn, bg=_resolved()[1]),
        )
        btn.bind(
            "<Leave>",
            lambda e: self.safe_widget_config(btn, bg=_resolved()[0]),
        )
        self.register_button(btn, color_attr, bg if not color_attr else None, fg)

        if side is not None:
            btn.pack(side=side, padx=2)

        return btn

    @staticmethod
    def _darken_color(hex_color: str, factor: float = 0.75) -> str:
        """
        Morkna en hex-farg med factor.

        Parametrar:
            hex_color: Hex-strang (#rrggbb)
            factor:    Morkningsfaktor (0.0-1.0)

        Returnerar:
            Morknad hex-strang
        """
        try:
            h = hex_color.lstrip("#")
            r = max(0, int(int(h[0:2], 16) * factor))
            g = max(0, int(int(h[2:4], 16) * factor))
            b = max(0, int(int(h[4:6], 16) * factor))
            return "#%02x%02x%02x" % (r, g, b)
        except Exception:
            return hex_color

    # Publik alias (bakatkompatibilitet)
    darken = _darken_color
