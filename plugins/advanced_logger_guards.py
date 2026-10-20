# ============================================================
# Hjalpfil: Loggvakter + filhantering + text/fonster-anpassning
# ============================================================
# FIL:       plugins/advanced_logger_guards.py
# PLATS:     plugins/ (ftp_gallery_uploader/plugins/advanced_logger_guards.py)
# Klass:     INGEN PLUGIN_NAME -> ignoreras av plugin-loadern (importeras)
# VERSION:   1.1.0
# AUTHOR:    Rickard Längkvist
# COPYRIGHT: Copyright (c) <år> Rickard Längkvist (dynamiskt år,
#            se COPYRIGHT-konstanten nedan)
#
# SYFTE (v1.0.0, utbruten ur advanced_logger.py v2.3.1 -> v2.4.0):
#   advanced_logger.py hade vuxit till 1767 rader (gräns 1800, spec §20 /
#   KRAV 17). Denna fil tar över de delar som INTE är UI:
#
#   [G-A] safe_write()          - fallback-skrivning, aldrig print()
#   [G-B] GuardedStream         - stdout/stderr-proxy som aldrig reser
#                                 (P14-8: WinError 6 under pythonw)
#   [G-C] install_stream_guard  - aktiverar proxyn på sys.stdout/stderr
#   [G-D] install_threading_hook- threading.excepthook (P14-6)
#   [G-E] install_tk_callback_hook - report_callback_exception (P14-7)
#   [G-F] tk_version()          - Tcl/Tk-patchlevel + TkVersion (P14-9)
#   [G-G] LogFiles              - logs/-mapp, rotation, huvudlogg,
#                                 felfil (errors_*.log), separatorer,
#                                 stängning. ALL fil-I/O för loggen ligger
#                                 här så att UI-koden aldrig rör filer.
#   [G-H] TEXT & FÖNSTER (T1-T6)- tk-scaling/DPI, föreslagen teckenstorlek,
#                                 geometritolkning, skärmrect, on-screen-
#                                 kontroll och anpassning av fönster till
#                                 skärmen. Används av "anpassat i text och
#                                 fönster" i advanced_logger v2.4.0.
#
# ANDRINGAR v1.0.0 -> v1.1.0:
#   [G-H2] _GEO_RE tillater negativa offset (1536x713+-1+1). Windows
#          maximerat rapporterar +-N+-N; gamla regexen sag ogiltig
#          geometri och diagnostiken larmade FEL i onodan.
#
# TEKNISK DETALJ:
#   * Inga f-strings - ALLT med %-formatering (B1).
#   * Ingen print() - safe_write() skriver till stderr eller
#     logs/stderr_fallback.log (B1).
#   * Alla publika funktioner är fel-säkra: de returnerar ett
#     sentinel-värde istället för att resa, eftersom de körs i
#     undantagsvägar (där ett nytt undantag skulle döda mainloop).
#   * Skrivs ALDRIG till av UI-trådens after()-jobb; LogFiles har egen
#     threading.RLock eftersom bakgrundstrådar (pipeline, watchdog,
#     tray) loggar samtidigt som UI-tråden.
# ============================================================

import os
import re
import sys
import threading
import traceback
from collections import deque
from datetime import datetime
from pathlib import Path

# -- Helpers (valfritt – för logs-sökväg, A10) -----------------
try:
    from helpers import get_logs_path as _helpers_logs_path
    _HAS_HELPERS = True
except ImportError:
    _HAS_HELPERS = False

VERSION   = "1.0.0"
AUTHOR    = "Rickard Längkvist"
COPYRIGHT = "Copyright (c) %d %s" % (datetime.now().year, AUTHOR)

#: Sentinel för "kunde inte avgöra" (skiljs från False/None i rapporter)
UNKNOWN = "?"


# ============================================================
# G-A. SAFE WRITE (aldrig print)
# ============================================================

def safe_write(message: str) -> None:
    """
    Skriv ett meddelande utan att krascha om stderr är stängd.

    Används som fallback när loggfilen eller logger inte är tillgänglig.
    Aldrig print() - skriver till stderr eller logs/stderr_fallback.log.

    Under pythonw.exe är sys.stderr ofta ett ogiltigt handtag; därför
    provas både sys.stderr och sys.__stderr__ innan fil-fallbacken.
    """
    for stream in (sys.stderr, sys.__stderr__):
        try:
            if stream and hasattr(stream, "write"):
                stream.write("%s\n" % message)
                stream.flush()
                return
        except (OSError, AttributeError, ValueError):
            continue
    try:
        Path("logs").mkdir(exist_ok=True)
        with open("logs/stderr_fallback.log", "a", encoding="utf-8") as f:
            f.write("%s\n" % message)
    except Exception:
        pass


# Bakåtkompatibilitet: advanced_logger importerade _safe_write tidigare
_safe_write = safe_write


# ============================================================
# G-B. GUARDED STREAM (P14-8)
# ============================================================

class GuardedStream(object):
    """
    Skriv-säker proxy för sys.stdout/sys.stderr (P14-8).

    Under pythonw.exe (ingen konsol, FreeConsole() anropad i main.pyw)
    är de ursprungliga handtagen ogiltiga. Varje skrivning där - även
    från tredje part (Tk:s report_callback_exception, warnings, PIL,
    watchdog) - ger då:

        OSError: [WinError 6] Referensen (handle) är felaktig

    Om det sker inne i en Tk-callback lämnar undantaget mainloop() och
    appen dör utan att något hamnar i loggen.

    Proxyn provar den ursprungliga strömmen först och faller tillbaka
    på en fil i logs/. Den reser ALDRIG (utom fileno(), se nedan).

    Parametrar:
        original:      den ursprungliga strömmen (kan vara None)
        fallback_path: Path till fil som får texten om skrivning misslyckas
        label:         "stdout"/"stderr" (loggas i fallback-filen)
    """

    def __init__(self, original, fallback_path, label):
        self._original      = original
        self._fallback_path = fallback_path
        self._label         = label
        self.fallback_writes = 0      # antal räddade skrivningar (v2.4.0)

    # -- skrivning ------------------------------------------------
    def write(self, text):
        """Skriv till originalet, annars till fallback-filen. Reser aldrig."""
        if not text:
            return 0
        try:
            if self._original is not None:
                self._original.write(text)
                try:
                    self._original.flush()
                except Exception:
                    pass
                return len(text)
        except Exception:
            pass
        try:
            with open(str(self._fallback_path), "a", encoding="utf-8") as f:
                f.write(
                    "[%s %s] %s"
                    % (
                        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        self._label,
                        text,
                    )
                )
            self.fallback_writes += 1
            return len(text)
        except Exception:
            return 0

    def writelines(self, lines):
        total = 0
        try:
            for line in lines:
                total += self.write(line)
        except Exception:
            pass
        return total

    def flush(self):
        try:
            if self._original is not None:
                self._original.flush()
        except Exception:
            pass

    # -- standardfråga --------------------------------------------
    def isatty(self):
        try:
            return bool(self._original is not None and self._original.isatty())
        except Exception:
            return False

    def writable(self):
        return True

    def closed(self):
        return False

    @property
    def encoding(self):
        try:
            return getattr(self._original, "encoding", None) or "utf-8"
        except Exception:
            return "utf-8"

    def fileno(self):
        """
        Delegera fileno() - får AVSVÄRDAS om handtaget är ogiltigt.

        Vissa bibliotek (subprocess med stderr=PIPE osv.) kräver ett
        riktigt filnummer; då ska de få det riktiga (eller ett fel),
        aldrig ett fejkat.
        """
        if self._original is None:
            raise OSError("Ingen underliggande stream (pythonw-läge)")
        return self._original.fileno()

    def detach(self):
        """Återställ originalet (används vid reload_plugins/avslut)."""
        return self._original

    def __getattr__(self, name):
        """Delegera allt annat (buffer, errors, name ...) till originalet."""
        return getattr(self._original, name)


# Bakåtkompatibilitet med advanced_logger v2.3.1
_GuardedStream = GuardedStream


# ============================================================
# G-C. STREAM GUARD
# ============================================================

def install_stream_guard(logs_dir):
    """
    Wrappa sys.stdout/sys.stderr i GuardedStream (P14-8).

    Parametrar:
        logs_dir: Path - mapp där stderr_fallback.log skapas

    Returnerar:
        (ok: bool, fallback_path: Path, guarded: list[str])
        ok=False om något gick fel (appen körs ändå, bara utan vakt).

    Idempotent: en redan wrappad ström wrappas inte igen (viktigt vid
    reload_plugins, annars blir det proxyn-i-proxyn i oändlighet).
    """
    guarded = []
    try:
        fallback = Path(logs_dir) / "stderr_fallback.log"
        for name in ("stdout", "stderr"):
            current = getattr(sys, name, None)
            if isinstance(current, GuardedStream):
                guarded.append(name)
                continue
            setattr(sys, name, GuardedStream(current, fallback, name))
            guarded.append(name)
        return True, fallback, guarded
    except Exception as exc:
        safe_write("[guards] install_stream_guard: %s" % exc)
        return False, None, guarded


def restore_streams():
    """
    Ta bort GuardedStream-proxyn (anropas i cleanup/vid reload).

    Utan detta kan en gammal proxy leva kvar med referens till en
    stängd fallback-fil efter reload_plugins.
    """
    restored = []
    for name in ("stdout", "stderr"):
        try:
            current = getattr(sys, name, None)
            if isinstance(current, GuardedStream):
                setattr(sys, name, current.detach())
                restored.append(name)
        except Exception:
            continue
    return restored


# ============================================================
# G-D. THREADING-HOOK (P14-6)
# ============================================================

def install_threading_hook(log_cb):
    """
    Fånga ohanterade undantag i ALLA bakgrundstrådar (P14-6).

    Python 3.8+ skickar dem till threading.excepthook. Utan egen hook
    skrivs de till stderr - som inte finns under pythonw - så felet
    antingen försvinner tyst eller blir en WinError 6.

    Parametrar:
        log_cb: callable(level: str, message: str) - t.ex. logger.log

    Returnerar: (ok: bool, reason: str)
    """
    if not callable(log_cb):
        return False, "log_cb är inte anropbar"

    def _thread_hook(args):
        try:
            exc_type  = getattr(args, "exc_type", None)
            exc_value = getattr(args, "exc_value", None)
            exc_tb    = getattr(args, "exc_traceback", None)
            if exc_type is None or issubclass(exc_type, SystemExit):
                return
            thread  = getattr(args, "thread", None)
            name    = getattr(thread, "name", UNKNOWN)
            tb_text = "".join(
                traceback.format_exception(exc_type, exc_value, exc_tb)
            )
            log_cb(
                "FEL",
                "OHANTERAT FEL I TRÅD '%s': %s: %s"
                % (name, exc_type.__name__, exc_value),
            )
            log_cb("DEBUG", "Traceback (tråd %s):\n%s" % (name, tb_text))
        except Exception:
            pass

    try:
        threading.excepthook = _thread_hook
        return True, "threading.excepthook installerad"
    except Exception as exc:
        return False, "%s: %s" % (type(exc).__name__, exc)


# ============================================================
# G-E. TK-CALLBACK-HOOK (P14-7)
# ============================================================

def install_tk_callback_hook(app, log_cb):
    """
    Fånga undantag i ALLA Tk-callbacks (P14-7).

    Gäller: knapp-kommandon, bind()-handlers, after()-jobb,
    trace_add-callbacks och <<Virtuella event>>.

    Utan vakt: Tk:s Misc.report_callback_exception() gör
        print("Exception in Tkinter callback", file=sys.stderr)
    vilket under pythonw.exe + FreeConsole() reser
        OSError: [WinError 6] Referensen (handle) är felaktig
    som sedan lämnar mainloop() -> appen dör.

    Med vakt: "TK-CALLBACK-FEL" + fullt traceback i huvudloggen och
    errors-filen, mainloop() fortsätter, inget skrivs till stderr och
    ingen dialog visas (dialog-storm vid upprepade fel undviks).

    Returnerar: (ok: bool, reason: str)
    """
    if app is None:
        return False, "ingen app (headless)"
    if not hasattr(app, "report_callback_exception"):
        return False, "app saknar report_callback_exception"
    if not callable(log_cb):
        return False, "log_cb är inte anropbar"

    def _tk_report(exc, val, tb):
        try:
            tb_text = "".join(traceback.format_exception(exc, val, tb))
            log_cb(
                "FEL",
                "TK-CALLBACK-FEL: %s: %s"
                % (getattr(exc, "__name__", exc), val),
            )
            log_cb("DEBUG", "Traceback (tk-callback):\n%s" % tb_text)
        except Exception:
            pass

    try:
        app.report_callback_exception = _tk_report
        return True, "Tk-callback-vakt aktiv"
    except Exception as exc:
        return False, "%s: %s" % (type(exc).__name__, exc)


# ============================================================
# G-F. TK/TCL-VERSION (P14-9)
# ============================================================

def tk_version(app=None) -> str:
    """
    Returnera Tk/Tcl-versionen, t.ex. "9.0.1 (TkVersion 9.0)".

    P14-9: Tcl/Tk 9.0 (som ingår i Python 3.14 på Windows) tog bort
    gamla kommandon som "trace variable". Att ha versionen i
    startbanner och i diagnostiken gör att en inklistrad logg direkt
    visar om ett fel beror på Tk-versionen.
    """
    patch = UNKNOWN
    try:
        if app is not None and hasattr(app, "tk"):
            patch = app.tk.call("info", "patchlevel")
    except Exception:
        patch = UNKNOWN
    try:
        import tkinter
        return "%s (TkVersion %s)" % (patch, tkinter.TkVersion)
    except Exception:
        return str(patch)


def is_tk9(app=None) -> bool:
    """True om Tcl/Tk 9.x körs (legacy-trace m.m. är borttaget)."""
    try:
        import tkinter
        return float(tkinter.TkVersion) >= 9.0
    except Exception:
        return False


# ============================================================
# G-G. LOGGFILER (rotation, huvudlogg, felfil)
# ============================================================

def resolve_logs_dir(logs_dir=None, project_base=None):
    """
    Returnera logs/-mappens Path (A10).

    Prioritet: utpekat logs_dir -> helpers.get_logs_path() ->
    project_base/logs -> projektrot/logs -> ./logs.
    Mappen skapas och skrivbarhet provas; första träff vinner.
    Reser aldrig (returnerar Path(".") i värsta fall).
    """
    candidates = []
    if logs_dir is not None:
        candidates.append(Path(logs_dir))
    if _HAS_HELPERS:
        try:
            candidates.append(_helpers_logs_path())
        except Exception:
            pass
    if project_base is not None:
        candidates.append(Path(project_base) / "logs")
    candidates.append(Path(__file__).parent.parent / "logs")
    candidates.append(Path("logs"))

    for path in candidates:
        try:
            path = Path(path)
            path.mkdir(parents=True, exist_ok=True)
            probe = path / ".write_test"
            probe.write_text("ok", encoding="utf-8")
            probe.unlink()
            return path
        except Exception:
            continue
    return Path(".")


class LogFiles(object):
    """
    All fil-I/O för loggen (G-G).

    Ansvar:
      * logs/-mapp (resolve_logs_dir, skrivbarhetsprov)
      * huvudlogg  logs/gallery_YYYYMMDD_HHMMSS.log (rotation max 50)
      * felfil     logs/errors_YYYYMMDD.log        (rotation max 30)
      * startup.log läses BARA (skrivs av main.pyw/helpers - orsakslogg)
      * trådsäkerhet: egen RLock eftersom bakgrundstrådar och UI-tråden
        skriver samtidigt (ADOPT-4: separat I/O-lås)

    Inga print(), inga f-strings, alla fel sväljs med safe_write.
    """

    MAX_LOG_FILES   = 50
    MAX_ERROR_FILES = 30

    #: nivåer som speglas i felfilen (U1)
    ERROR_LEVELS = ("FEL", "VARNING")

    def __init__(self, logs_dir=None, start_time=None, main_max=None,
                 error_max=None):
        self.start_time = start_time or datetime.now()
        self.logs_dir   = resolve_logs_dir(logs_dir)
        self.max_main   = int(main_max or self.MAX_LOG_FILES)
        self.max_errors = int(error_max or self.MAX_ERROR_FILES)
        self._lock      = threading.RLock()

        self.main_path  = None
        self.error_path = None
        self._main      = None
        self._error     = None
        self.written    = 0          # skrivna rader i huvudloggen
        self.errors     = 0          # skrivna rader i felfilen
        self.opened     = []         # ["main", "errors"] för startbanner

    # -- öppna/stänga -------------------------------------------
    def open_all(self):
        """Rotera, öppna huvudlogg + felfil. Returnerar self."""
        self.rotate_main()
        self.rotate_errors()
        self._open_main()
        self._open_errors()
        return self

    def _open_main(self):
        ts = self.start_time.strftime("%Y%m%d_%H%M%S")
        self.main_path = self.logs_dir / ("gallery_%s.log" % ts)
        try:
            self._main = open(
                self.main_path, "a", encoding="utf-8",
                buffering=1,   # radvis buffring -> skrivs direkt
            )
            self.opened.append("main")
        except Exception as exc:
            safe_write("[LogFiles] Kunde inte öppna loggfil: %s" % exc)
            self._main = None

    def _open_errors(self):
        """
        Öppna (append) en felfil per dag: errors_YYYYMMDD.log (U1).

        Innehåller BARA fel/undantag med tid + full traceback. En
        separat, lättinspekterbar och klistra-in-vänlig fil.
        """
        try:
            name = "errors_%s.log" % datetime.now().strftime("%Y%m%d")
            self.error_path = self.logs_dir / name
            self._error = open(
                self.error_path, "a", encoding="utf-8", buffering=1
            )
            self._error.write(
                "\n=== [%s] Session start (gallery: %s) ===\n"
                % (
                    self.start_time.strftime("%Y-%m-%d %H:%M:%S"),
                    self.main_path.name if self.main_path else UNKNOWN,
                )
            )
            self.opened.append("errors")
        except Exception as exc:
            safe_write("[LogFiles] Kunde inte öppna felfil: %s" % exc)
            self._error = None

    def close(self):
        """Flusha och stäng båda filerna (cleanup). Reser aldrig."""
        with self._lock:
            if self._error is not None:
                try:
                    self.write_sep(
                        "=== Session slut (%s) ==="
                        % datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    )
                    self._error.flush()
                    self._error.close()
                except Exception:
                    pass
                self._error = None
            if self._main is not None:
                try:
                    self._main.flush()
                    self._main.close()
                except Exception:
                    pass
                self._main = None

    # -- rotation ------------------------------------------------
    def rotate_main(self):
        """Ta bort äldsta gallery_*.log om det finns >= max_main."""
        return self._rotate("gallery_*.log", self.max_main, "huvudlogg")

    def rotate_errors(self):
        """Ta bort äldsta errors_*.log om det finns >= max_errors."""
        return self._rotate("errors_*.log", self.max_errors, "felfil")

    def _rotate(self, pattern, keep, label):
        removed = 0
        try:
            files = sorted(
                self.logs_dir.glob(pattern),
                key=lambda p: p.stat().st_mtime,
            )
            while len(files) >= keep:
                oldest = files.pop(0)
                try:
                    oldest.unlink()
                    removed += 1
                except Exception as exc:
                    safe_write(
                        "[LogFiles] Kunde inte ta bort %s: %s" % (oldest, exc)
                    )
        except Exception as exc:
            safe_write("[LogFiles] Rotation %s: %s" % (label, exc))
        return removed

    # -- skrivning ------------------------------------------------
    def write(self, timestamp: str, level: str, message: str) -> bool:
        """Skriv en rad till huvudloggen. Tyst vid fel (True/False)."""
        if self._main is None:
            return False
        try:
            with self._lock:
                self._main.write(
                    "[%s] [%-10s] %s\n" % (timestamp, level, message)
                )
                self.written += 1
            return True
        except Exception:
            return False

    def write_error(self, timestamp: str, level: str, message: str) -> bool:
        """
        Skriv BARA fel/undantag/traceback till felfilen (U1).

        DEBUG-rader släpps igenom endast om de inleds med "Traceback",
        så att hela orsakskedjan hamnar i felfilen utan att den fylls
        med vanlig debug.
        """
        if self._error is None:
            return False
        lvl = (level or "").upper()
        if lvl not in self.ERROR_LEVELS and not (
            lvl == "DEBUG" and str(message).startswith("Traceback")
        ):
            return False
        try:
            with self._lock:
                self._error.write(
                    "[%s] [%-10s] %s\n" % (timestamp, lvl, message)
                )
                self.errors += 1
            return True
        except Exception:
            return False

    def write_sep(self, msg: str) -> None:
        """Skriv en separatormarkering till felfilen (t.ex. session slut)."""
        if self._error is None:
            return
        try:
            with self._lock:
                self._error.write(
                    "[%s] %s\n"
                    % (datetime.now().strftime("%H:%M:%S.%f")[:-3], msg)
                )
        except Exception:
            pass

    # -- läsning (diagnostik) -------------------------------------
    def read_startup(self, max_lines=400):
        """
        Läs logs/startup.log (ORSAKSLOGGEN - skrivs av main.pyw/helpers).

        Denna fil ägs INTE av loggvisaren; den läses bara för att
        diagnostiken ska kunna förklara varför fönstret visas/döljs.

        Returnerar: (header: dict, lines: list[str]) - tomma vid fel.
        """
        header, lines = {}, []
        try:
            path = self.logs_dir / "startup.log"
            if not path.exists():
                return header, lines
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                raw = f.read().splitlines()
            for row in raw:
                if row.startswith("# "):
                    if ":" in row:
                        key, _, val = row[2:].partition(":")
                        header[key.strip().lower()] = val.strip()
                elif row.strip():
                    lines.append(row)
            if len(lines) > max_lines:
                lines = lines[-max_lines:]
        except Exception as exc:
            safe_write("[LogFiles] read_startup: %s" % exc)
        return header, lines

    def stats(self) -> dict:
        """Status för startbanner/diagnostik."""
        return {
            "logs_dir":   str(self.logs_dir),
            "main":       self.main_path.name if self.main_path else UNKNOWN,
            "errors":     self.error_path.name if self.error_path else UNKNOWN,
            "main_open":  self._main is not None,
            "err_open":   self._error is not None,
            "written":    self.written,
            "errors":     self.errors,
        }


# ============================================================
# G-H. TEXT & FÖNSTER-ANPASSNING (T1-T6)
# ============================================================

#: Minsta/största teckenstorlek som UI:t får skala till
FONT_MIN, FONT_MAX = 7, 20

# Grupper: w, h, sign_x, x, sign_y, y. x/y far vara negativa
# (Tk: "900x700+-8+-8" = maximerat pa Windows).
_GEO_RE = re.compile(
    r"^(\d+)x(\d+)(?:([+-])(-?\d+)([+-])(-?\d+))?$"
)


def tk_scaling(app=None) -> float:
    """
    Tk:s scaling-faktor (pixlar per punkt) - 1.3333 = 96 DPI (T1).

    Returnerar 0.0 om scaling inte kan läsas (headless).
    """
    try:
        if app is None or not hasattr(app, "tk"):
            return 0.0
        return float(app.tk.call("tk", "scaling"))
    except Exception:
        return 0.0


def screen_dpi(app=None) -> int:
    """Skärmens DPI (scaling * 72), avrundat. 0 = okänt (T1)."""
    factor = tk_scaling(app)
    if factor <= 0:
        return 0
    return int(round(factor * 72))


def suggest_font_size(app=None, base=9) -> int:
    """
    Föreslagen teckenstorlek utifrån DPI (T1).

    96 DPI (standard)      -> base (9)
    120 DPI (125 % scaling)-> base + 1
    144 DPI (150 %)        -> base + 2
    192 DPI (200 %)        -> base + 4
    Klampad till FONT_MIN..FONT_MAX så att loggen aldrig blir oläsbar
    eller större än fönstret.
    """
    dpi = screen_dpi(app)
    if dpi <= 0:
        return int(base)
    size = int(round(base * dpi / 96.0))
    return max(FONT_MIN, min(FONT_MAX, size))


def clamp_font_size(size, fallback=9) -> int:
    """Klampa ett användarval till FONT_MIN..FONT_MAX (T1)."""
    try:
        return max(FONT_MIN, min(FONT_MAX, int(size)))
    except Exception:
        return int(fallback)


def parse_geometry(geo) -> dict:
    """
    Tolka "900x700+100+50" -> {"w":900,"h":700,"x":100,"y":50} (T2).

    Saknas offset blir x/y None. Ogiltig sträng ger {} (anroparen
    avgör fallback). Negativa offset tillåts (multi-monitor).
    """
    if not geo:
        return {}
    m = _GEO_RE.match(str(geo).strip())
    if not m:
        return {}
    out = {"w": int(m.group(1)), "h": int(m.group(2)), "x": None, "y": None}
    if m.group(4) is not None:
        sign_x = -1 if m.group(3) == "-" else 1
        sign_y = -1 if m.group(5) == "-" else 1
        out["x"] = sign_x * int(m.group(4))
        out["y"] = sign_y * int(m.group(6))
    return out


def format_geometry(w, h, x, y) -> str:
    """Bygg en Tk-geometristräng med korrekt tecken på offset (T2)."""
    return "%dx%d%s%d%s%d" % (
        int(w), int(h),
        "+" if (x or 0) >= 0 else "-", abs(int(x or 0)),
        "+" if (y or 0) >= 0 else "-", abs(int(y or 0)),
    )


def screen_rect(app=None) -> dict:
    """
    Skärmens storlek + virtuellt skrivbord (T3).

    Nycklar: sw, sh (winfo_screenwidth/height), vw, vh
    (winfo_vrootwidth/height), ok (bool). På Windows är vroot oftast
    lika med screen; på X11 kan vroot vara mindre än screen.
    """
    out = {"sw": 0, "sh": 0, "vw": 0, "vh": 0, "ok": False}
    try:
        if app is None:
            return out
        out["sw"] = int(app.winfo_screenwidth())
        out["sh"] = int(app.winfo_screenheight())
        try:
            out["vw"] = int(app.winfo_vrootwidth())
            out["vh"] = int(app.winfo_vrootheight())
        except Exception:
            out["vw"], out["vh"] = out["sw"], out["sh"]
        out["ok"] = out["sw"] > 0 and out["sh"] > 0
    except Exception:
        return out
    if not out["vw"]:
        out["vw"] = out["sw"]
    if not out["vh"]:
        out["vh"] = out["sh"]
    return out


def geometry_on_screen(geo, app=None, margin=40) -> tuple:
    """
    Kontrollera att ett fönster faktiskt syns på skärmen (T3/BUG-004).

    Returnerar (synlig: bool, orsak: str). Synlig=False med en konkret
    orsak är exakt det som behövs för att svara på "varför syns inte
    fönstret": utanför skärmen, 1x1 px, eller ogiltig geometri.

    Regler:
      * ogiltig geometristräng            -> (False, "ogiltig geometri ...")
      * bredd/höjd < 40 px                -> (False, "för litet ...")
      * titelraden (y+30) helt utanför    -> (False, "utanför skärmen ...")
      * minst margin px synligt i X-led   -> annars (False, ...)
    """
    rect = screen_rect(app)
    parsed = parse_geometry(geo)
    if not parsed:
        return False, "ogiltig geometri '%s' (förväntat WxH+X+Y)" % geo
    w, h = parsed["w"], parsed["h"]
    x, y = parsed["x"], parsed["y"]
    if x is None or y is None:
        return True, "geometri utan offset (placeras av fönsterhanteraren)"
    if w < 40 or h < 40:
        return False, "för litet fönster (%dx%d px)" % (w, h)
    if not rect["ok"]:
        return True, "skärmstorlek okänd - kan inte avgöra (headless)"
    sw, sh = max(rect["sw"], rect["vw"]), max(rect["sh"], rect["vh"])
    if y + 30 < 0 or y > sh - 10:
        return False, "utanför skärmen i Y-led (y=%d, skärmhöjd %d)" % (y, sh)
    if x + w - margin < 0 or x > sw - margin:
        return False, "utanför skärmen i X-led (x=%d, skärmbredd %d)" % (x, sw)
    return True, "inom skärmen (%dx%d+%d+%d på %dx%d)" % (w, h, x, y, sw, sh)


def fit_to_screen(geo, app=None, min_w=400, min_h=300, margin=40) -> str:
    """
    Flytta/klampa en geometri så att fönstret garanterat syns (T4).

    Används av "Rätta fönsterposition" i diagnostiken: behåller sparad
    storlek men flyttar in fönstret på skärmen om det ligger utanför,
    och tvingar minst min_w x min_h (spec §16: min 400x300).
    """
    parsed = parse_geometry(geo)
    rect = screen_rect(app)
    if not parsed:
        return "%dx%d" % (min_w, min_h)
    w = max(min_w, parsed["w"])
    h = max(min_h, parsed["h"])
    x = parsed["x"]
    y = parsed["y"]
    if rect["ok"]:
        sw = max(rect["sw"], rect["vw"])
        sh = max(rect["sh"], rect["vh"])
        w = min(w, sw)
        h = min(h, sh)
        if x is None:
            x = max(0, (sw - w) // 2)
        if y is None:
            y = max(0, (sh - h) // 2)
        x = max(-w + margin, min(x, sw - margin))
        y = max(0, min(y, sh - margin))
    else:
        x = 100 if x is None else x
        y = 100 if y is None else y
    return format_geometry(w, h, x, y)


def readable_width(app=None, chars=110, font_size=9) -> int:
    """
    Pixlar som behövs för `chars` tecken i en monospace-font (T5).

    Används för att dimensionera diagnostikfönstret så att rader inte
    behöver brytas eller skrollas i sidled i onödan.
    """
    try:
        factor = tk_scaling(app) or (96.0 / 72.0)
        char_px = max(5.0, font_size * factor * 0.60)
        return int(chars * char_px)
    except Exception:
        return chars * 7


def fit_window(wanted_w, wanted_h, app=None, pad=80) -> tuple:
    """
    Klampa ett önskat fönster till skärmen (T6).

    Returnerar (w, h, x, y) centrerat. Används av diagnostikfönstret
    så att det aldrig blir större än skärmen (4K -> 1024x768 -> lika).
    """
    rect = screen_rect(app)
    if rect["ok"]:
        sw = max(rect["sw"], rect["vw"])
        sh = max(rect["sh"], rect["vh"])
    else:
        sw, sh = 1280, 800
    w = max(320, min(int(wanted_w), sw - pad))
    h = max(240, min(int(wanted_h), sh - pad))
    return w, h, max(0, (sw - w) // 2), max(0, (sh - h) // 2)


# ============================================================
# SJÄLVTEST (körs med: python -m plugins.advanced_logger_guards)
# ============================================================

def _self_test():
    """
    Enkel headless-självtest.

    Returnerar (antal_tester, lista_med_fel) - tom lista = allt OK.
    Ingen print() (B1): anroparen skriver ut resultatet.
    """
    import tempfile
    fel = []
    antal = [0]

    def krav(namn, villkor):
        antal[0] += 1
        if not villkor:
            fel.append(namn)

    tmp = Path(tempfile.mkdtemp(prefix="loggtest_"))
    lf = LogFiles(logs_dir=tmp)
    lf.open_all()
    krav("huvudlogg oppnad", lf.stats()["main_open"])
    krav("felfil oppnad", lf.stats()["err_open"])
    lf.write("12:00:00.000", "INFO", "hej")
    lf.write("12:00:00.001", "FEL", "trasigt")
    lf.write_error("12:00:00.001", "FEL", "trasigt")
    lf.write_error("12:00:00.002", "INFO", "ska INTE till felfilen")
    lf.close()
    st = lf.stats()
    krav("2 rader skrivna i huvudloggen", st["written"] == 2)
    krav("1 rad skrivet i felfilen", st["errors"] == 1)
    krav("loggmapp skapad", (tmp / st["main"]).exists())

    krav("parse_geometry", parse_geometry("900x700+100+50")
         == {"w": 900, "h": 700, "x": 100, "y": 50})
    krav("parse_geometry negativ x", parse_geometry("800x600-20+30")["x"] == -20)
    krav("parse_geometry ogiltig", parse_geometry("x") == {})
    krav("format_geometry rundgång",
         parse_geometry(format_geometry(800, 600, -20, 30))["x"] == -20)
    # Fejkad skarm (1920x1080) - headless finns ingen riktig
    class FakeApp(object):
        def winfo_screenwidth(self):
            return 1920

        def winfo_screenheight(self):
            return 1080

        def winfo_vrootwidth(self):
            return 1920

        def winfo_vrootheight(self):
            return 1040

    fake = FakeApp()
    krav("screen_rect med fejkapp", screen_rect(fake)["sw"] == 1920)
    synlig, orsak = geometry_on_screen("900x700+99999+99999", fake)
    krav("utanfor skarmen upptacks", not synlig)
    krav("orsak namner X- eller Y-led",
         ("X-led" in orsak) or ("Y-led" in orsak))
    synlig2, orsak2 = geometry_on_screen("900x700+100+50", fake)
    krav("inom skarmen godkanns", synlig2 and "inom skärmen" in orsak2)
    synlig3, orsak3 = geometry_on_screen("10x10+100+50", fake)
    krav("for litet fonster upptacks",
         not synlig3 and "för litet" in orsak3)
    rattad = fit_to_screen("900x700+99999+99999", fake)
    krav("fit_to_screen ger giltig geometri", parse_geometry(rattad) != {})
    krav("fit_to_screen flyttar in pa skarmen",
         geometry_on_screen(rattad, fake)[0])
    krav("fit_to_screen headless ger minst 400x300",
         parse_geometry(fit_to_screen("trasig", None))["w"] >= 400)
    krav("clamp_font_size ovre grans", clamp_font_size(999) == FONT_MAX)
    krav("clamp_font_size undre grans", clamp_font_size(-3) == FONT_MIN)
    krav("suggest_font_size headless", suggest_font_size(None) == 9)
    krav("screen_rect headless", screen_rect(None)["ok"] is False)
    krav("tk_scaling headless", tk_scaling(None) == 0.0)
    krav("fit_window headless inom grans",
         fit_window(99999, 99999, None)[0] <= 99999)
    krav("read_startup saknas ger tomt", lf.read_startup() == ({}, []))
    krav("ContextObserver loggar setitem", _test_context_observer())
    krav("disk_free_mb returnerar int", isinstance(disk_free_mb("."), int))
    return antal[0], fel


def disk_free_mb(path):
    """
    Fritt utrymme (MB) pa filsystemet som innehaller `path` (Y6).

    Loggdisken full = tyst tappade loggar. Returnerar -1 vid fel.
    Anvander shutil.disk_usage; reser aldrig.
    """
    try:
        import shutil
        usage = shutil.disk_usage(str(path))
        return int(usage.free // (1024 * 1024))
    except Exception:
        return -1


class ContextObserver(dict):
    """
    dict-subklass som loggar varje skrivning till app.context (Y1).

    "Loggning av precis allt som hander" inkluderar dataflodet: varje
    nyckel som satts/tas bort i context loggas (DEBUG, throttle per
    nyckel sa en pipeline-loop inte drunkar loggen).

    Sakerhet:
      * isinstance(ctx, dict) forblir True (subklass).
      * __setitem__/__delitem__ reser ALDRIG - super() anropas alltid,
        loggningen ligger i try/except fore.
      * Varden loggas INTE (kan vara stora listor/kansliga), bara
        nyckel + typ + langd.
    """

    def __init__(self, source=None, logger=None, throttle_ms=1500):
        dict.__init__(self)
        if source:
            try:
                dict.update(self, source)
            except Exception:
                pass
        self._obs_logger = logger
        self._obs_throttle_ms = 1500 if throttle_ms is None else int(throttle_ms)
        self._obs_last = {}

    def _obs_log(self, action, key):
        try:
            logger = self._obs_logger
            if logger is None:
                return
            import time as _time
            now = _time.monotonic() * 1000.0
            stamp = self._obs_last.get(key, 0.0)
            if self._obs_throttle_ms > 0 and (now - stamp) < self._obs_throttle_ms:
                return
            self._obs_last[key] = now
            try:
                val = dict.__getitem__(self, key)
                info = type(val).__name__
                if isinstance(val, (list, tuple, dict, str)):
                    info += "(%d)" % len(val)
            except Exception:
                info = "?"
            logger.log("CONTEXT", "context %s: %s = %s" % (action, key, info))
        except Exception:
            pass

    def __setitem__(self, key, value):
        try:
            existed = key in self
        except Exception:
            existed = False
        dict.__setitem__(self, key, value)
        self._obs_log("uppdaterad" if existed else "ny", key)

    def __delitem__(self, key):
        dict.__delitem__(self, key)
        try:
            self._obs_log("borttagen", key)
        except Exception:
            pass

    def update(self, *args, **kwargs):
        dict.update(self, *args, **kwargs)
        try:
            src = args[0] if args else kwargs
            keys = list(src.keys())[:8] if hasattr(src, "keys") else []
            if keys and self._obs_logger is not None:
                self._obs_logger.log(
                    "CONTEXT", "context update: %d nycklar (%s%s)"
                    % (len(src), ", ".join(str(k) for k in keys),
                       ", ..." if len(src) > 8 else ""))
        except Exception:
            pass


def _test_context_observer():
    """Liten intern kontroll av ContextObserver (for _self_test)."""
    class _Log(object):
        def __init__(self):
            self.rows = []

        def log(self, level, msg):
            self.rows.append((level, msg))

    logger = _Log()
    ctx = ContextObserver({"a": 1}, logger, throttle_ms=0)
    ctx["b"] = [1, 2, 3]
    ctx["b"] = [1, 2]
    del ctx["a"]
    joined = " ".join(m for _l, m in logger.rows)
    return ("ny" in joined and "list(3)" in joined
            and "borttagen" in joined and "uppdaterad" in joined)


if __name__ == "__main__":
    totalt, missar = _self_test()
    safe_write(
        "[guards-sjalvtest] %d/%d OK%s"
        % (
            totalt - len(missar), totalt,
            "" if not missar else " - FEL: " + ", ".join(missar),
        )
    )
    raise SystemExit(1 if missar else 0)
