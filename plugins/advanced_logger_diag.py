# ============================================================
# Hjalpfil: AI-felsokning (diagnostik + "varfor syns inte fonstret")
# ============================================================
# FIL:       plugins/advanced_logger_diag.py
# PLATS:     plugins/ (ftp_gallery_uploader/plugins/advanced_logger_diag.py)
# Klass:     INGEN PLUGIN_NAME -> ignoreras av plugin-loadern (importeras)
# VERSION:   1.0.0
# AUTHOR:    Rickard Längkvist
# COPYRIGHT: Copyright (c) <år> Rickard Längkvist (dynamiskt år,
#            se COPYRIGHT-konstanten nedan)
#
# SYFTE (v1.0.0, ny i advanced_logger v2.4.0):
#   Tre uppgifter som tidigare krävde att en människa läste loggen:
#
#   [D1] FELMÖNSTER-REGLER: kända fel (WinError 6, Tcl/Tk 9.0 legacy
#        trace, namnkollision 'list' object is not callable, saknade
#        moduler, korrupt JSON, off-screen-geometri ...) matchas mot
#        loggen och svarar med ORSAK + ÅTGÄRD + ALLVAR. Varje regel är
#        hämtad från ett verkligt ärende i detta projekt (BUG-0xx).
#   [D2] FÖNSTERDIAGNOSTIK: svarar på "varför syns inte fönstret?"
#        genom att läsa Tk-tillstånd (state/mapped/geometry/alpha),
#        config (start_minimized, window_state.json), systray-status
#        (TRAY_AVAILABLE/_tray_running/_tray_visible), startup.log
#        (orsaksloggen från main.pyw) och single-instance-porten.
#   [D3] MILJÖ-RAPPORT: Python/Tk/DPI/skalning, skrivbara mappar,
#        beroenden, skärmgeometri, loggfilernas status.
#
#   Resultatet renderas som en textblock-rapport som BOTH loggas
#   (SYSTEM/VARNING/FEL med exakta tidsstämplar) och visas i ett
#   eget diagnostikfönster i UI:t.
#
# TEKNISK DETALJ:
#   * Inga f-strings, ingen print() (B1).
#   * Aldrig reser: varje kontroll ligger i try/except och rapporterar
#     "[?]" (UNKNOWN) istället för att döda appen - diagnostik körs ofta
#     NÄR något redan gått fel.
#   * Läser config/loggar skrivskyddat. Ändrar ALDRIG användarens filer
#     (förslag ges som text, t.ex. "radera config/window_state.json").
#   * Regelmatchning sker på loggtext (str) - aldrig på objekt, så att
#     även inklistrade loggar från användaren kan analyseras.
# ============================================================

import json
import re
import socket
import sys
from datetime import datetime
from pathlib import Path

from .advanced_logger_guards import (
    UNKNOWN,
    disk_free_mb,
    is_tk9,
    parse_geometry,
    screen_rect,
    screen_dpi,
    tk_scaling,
    tk_version,
    geometry_on_screen,
    fit_to_screen,
    safe_write,
)

VERSION   = "1.1.0"
AUTHOR    = "Rickard Längkvist"
COPYRIGHT = "Copyright (c) %d %s" % (datetime.now().year, AUTHOR)

#: Single-instance-port (helpers.SingleInstanceLock, spec §15)
SINGLE_INSTANCE_PORT = 47200

#: Allvar: 5 = appen oanvändbar, 1 = kosmetiskt
ALLVAR_TEXT = {5: "KRITISKT", 4: "ALLVARLIGT", 3: "MEDEL",
               2: "LINDRIGT", 1: "INFO"}


# ============================================================
# D1. FELMÖNSTER-REGLER (varje regel = ett verkligt ärende)
# ============================================================
# Fält:
#   id       - kortkod (loggas, sökbar)
#   pattern  - regex på loggtext (ignorera skiftläge)
#   allvar   - 1..5
#   titel    - vad användaren ser
#   orsak    - varför det händer
#   atgard   - konkret åtgärd (fil + radnivå om möjligt)
#   bug      - referens till spec.md §22 (valfritt)

RULES = (
    {
        "id": "NAME-SHADOW",
        "pattern": r"'(list|dict|set|str|int|float|NoneType|bool)' object "
                   r"is not callable",
        "allvar": 5,
        "titel": "Instansattribut skuggar en metod",
        "orsak": "Ett self.X = [] i __init__ har samma namn som en metod "
                 "def X() i klassen eller en mixin. Instansattribut vinner "
                 "ALLTID över klassmetoder i Python, så anropet self.X(...) "
                 "försöker anropa en lista.",
        "atgard": "Byt namn på instansattributet (base_plugin v1.4.1 döpte "
                 "om _reg_panels/_reg_labels till _theme_reg_*). Kör "
                 "Loggvisare -> Diagnostik; skuggningsvakten (R2) listar "
                 "alla kollisioner automatiskt.",
        "bug": "BUG-024",
    },
    {
        "id": "TK9-TRACE",
        "pattern": r'bad option "?variable"?: must be add, info, or remove',
        "allvar": 5,
        "titel": "Utfasad tkinter-trace under Tcl/Tk 9.0",
        "orsak": "Python 3.14 på Windows skeppas med Tcl/Tk 9.0 som tog bort "
                 "'trace variable'. Variable.trace()/trace_variable/ "
                 "trace_vdelete/trace_vinfo finns inte längre.",
        "atgard": "Ersätt med var.trace_add(\"write\", cb) och "
                 "var.trace_remove(\"write\", id) - fungerar på både 8.6 och "
                 "9.0. Fixat i ui_controls.py v2.4.1 och image_sorter.py "
                 "v4.2.1; sök efter trace_variable i övriga filer.",
    },
    {
        "id": "WINERROR6",
        "pattern": r"WinError 6|Referensen \(handle\) ar felaktig|"
                   r"\[Errno 9\] Bad file descriptor",
        "allvar": 5,
        "titel": "Ogiltigt stdout/stderr-handtag (pythonw)",
        "orsak": "Under pythonw.exe + FreeConsole() finns ingen konsol; en "
                 "skrivning till stderr (t.ex. Tk:s "
                 "report_callback_exception eller en tredje-parts print) "
                 "reser OSError WinError 6, som lämnar mainloop() och dödar "
                 "appen.",
        "atgard": "Se till att advanced_logger v2.3.1+ initieras FÖRST "
                 "(PRIORITY=-1) så att vakterna (P14-6/7/8) är aktiva: "
                 "startbanderollen ska visa 'Vakter: stdout/stderr=skyddade "
                 "trad-hook=aktiv tk-callback=aktiv'. Ingen print() i koden.",
        "bug": "P14-7/P14-8",
    },
    {
        "id": "PLUGIN-INIT",
        "pattern": r"Plugin '[^']+' (init-fel|laddningsfel)",
        "allvar": 5,
        "titel": "Plugin kraschade i init/laddning",
        "orsak": "Pluginets init() eller importen kastade ett undantag, så "
                 "dess flik/UI byggdes aldrig. Appen startar ändå - det är "
                 "därför felet lätt missas.",
        "atgard": "Läs tracebacken i logs/errors_*.log direkt under "
                 "init-felet (raden 'Traceback:' + fil:rad). Kör "
                 "Loggvisare -> Diagnostik för automatisk orsak/åtgärd. "
                 "Ett trasigt plugin ger ofta en saknad flik.",
    },
    {
        "id": "TRAY-MISSING",
        "pattern": r"pystray/Pillow saknas|pystray saknas",
        "allvar": 3,
        "titel": "Systray-ikon saknas (eller falsk varning)",
        "orsak": "Antingen saknas pystray/Pillow verkligen, ELLER så är det "
                 "den falska varningen från system_tray <= v3.5.1 "
                 "(try/except/else-gren som kördes när after() LYCKADES).",
        "atgard": "1) Kontrollera startbanderollen: '- pystray saknas' = "
                 "verkligen saknat -> python -m pip install -r "
                 "requirements.txt. 2) Står '+ pystray tillgängligt' men "
                 "varningen ändå kommer: uppgradera system_tray.py till "
                 "v3.5.2 (BUG-025).",
        "bug": "BUG-025",
    },
    {
        "id": "TRAY-INVISIBLE",
        "pattern": r"SYSTRAY OSYNLIG|SYSTRAY-FALLBACK",
        "allvar": 5,
        "titel": "Systray-ikonen blev aldrig synlig",
        "orsak": "pystray-tråden startade men ikonen registrerades aldrig "
                 "hos skalet (eller två ikoner tog bort varandra). Med "
                 "start_minimized=True blir appen då helt onåbar.",
        "atgard": "Starta appen en gång till (show_window körs vid "
                 "andrastart), sätt \"start_minimized\": false i "
                 "config/settings.json, eller ta bort en dubbel ikonpost. "
                 "Se P14-10/P14-13 i system_tray.py.",
        "bug": "P14-10",
    },
    {
        "id": "JSON-CORRUPT",
        "pattern": r"JSONDecodeError|Expecting value: line|Extra data: line|"
                   r"Unterminated string",
        "allvar": 4,
        "titel": "Korrupt JSON-fil (config eller sortering)",
        "orsak": "En config-fil skrevs av medan en krasch/strömavbrott "
                 "inträffade, eller redigerades för hand med fel encoding.",
        "atgard": "BasePlugin.load_config karantänlägger automatiskt trasiga "
                 "filer (.corrupt-backup) och återställer från .bak. Kör om "
                 "appen; vill du börja rent, radera den nämnda filen i "
                 "config/ så återskapas standardvärden.",
        "bug": "ADOPT-1",
    },
    {
        "id": "PERMISSION",
        "pattern": r"PermissionError|WinError 5|\[Errno 13\]",
        "allvar": 4,
        "titel": "Skrivskyddad mapp/fil",
        "orsak": "Programmet saknar skrivrättighet (t.ex. under "
                 "Program Files, eller filen är öppnad i Excel/Preview).",
        "atgard": "Flytta projektet till en mapp du äger (D:\\Program\\...), "
                 "kör inte som administratör i onödan, och stäng program som "
                 "låser filen. Kontrollera att logs/ och config/ är skrivbara "
                 "(Diagnostik visar det).",
    },
    {
        "id": "MODULE-MISSING",
        "pattern": r"ModuleNotFoundError: No module named '([A-Za-z0-9_\.]+)'|"
                   r"ImportError: cannot import name",
        "allvar": 4,
        "titel": "Python-modul saknas",
        "orsak": "Ett beroende är inte installerat i den Python-tolk som "
                 "kör appen (vanligt med flera installationer: py -3.14 vs "
                 "python).",
        "atgard": "python -m pip install -r requirements.txt med SAMMA tolk "
                 "som startar appen (py -3.14 -m pip ...). Verifiera med "
                 "python -c \"import PIL, pystray, watchdog, darkdetect\".",
    },
    {
        "id": "FFMPEG-MISSING",
        "pattern": r"FFmpeg.*(saknas|not found|hittades inte)|"
                   r"FileNotFoundError.*ffprobe|WinError 2",
        "allvar": 3,
        "titel": "FFmpeg/FFprobe hittas inte i PATH",
        "orsak": "video_processor letar upp ffmpeg/ffprobe i PATH; saknas de "
                 "fungerar bildbehandling men inte videokomprimering.",
        "atgard": "Installera med winget install Gyan.FFmpeg (eller "
                 "choco install ffmpeg) och starta om appen så att PATH "
                 "uppdateras.",
    },
    {
        "id": "TK-DESTROYED",
        "pattern": r"application has been destroyed|can't invoke \"?tk\"?|"
                   r"invalid command name|image \"pyimage\d+\" doesn't exist",
        "allvar": 4,
        "titel": "Tk-callback efter att widget/fönster förstörts",
        "orsak": "Efter after()/tråd-jobb körs när widgeten redan är "
                 "förstörd (t.ex. efter reload_plugins eller stängd "
                 "dialog). 'pyimage2' beror på flera Tk-rotar.",
        "atgard": "Använd BasePlugin.widget_exists() före varje config/insert "
                 "och safe_after() (som avbokas i cleanup) istället för "
                 "app.after() direkt.",
    },
    {
        "id": "KEY-BG",
        "pattern": r"KeyError: '(bg_primary|bg|fg|button_bg)'",
        "allvar": 4,
        "titel": "Temanyckel saknas i färgdict",
        "orsak": "En widget frågar efter en färgnyckel som temat inte "
                 "definierar (BUG-016 var 'bg_primary' i HTML-mallen).",
        "atgard": "Använd get_theme_color(nyckel, fallback) eller "
                 "COLOR_*-konstanter. I mallar: str.replace() med "
                 "{{PLATSHÅLLARE}} - aldrig .format().",
        "bug": "BUG-016",
    },
    {
        "id": "GEOMETRY-OFFSCREEN",
        "pattern": r"geometri.*ogiltig|utanfor skarmen|utanför skärmen|"
                   r"_check_screen_bounds",
        "allvar": 4,
        "titel": "Fönstergeometri utanför skärmen",
        "orsak": "Sparad geometri i config/window_state.json pekar på en "
                 "skärm som inte längre finns (dockad monitor, ändrad "
                 "upplösning/skalning).",
        "atgard": "Klicka 'Rätta fönsterposition' i Diagnostik, eller radera "
                 "config/window_state.json så används 900x700 centrerat.",
        "bug": "BUG-004",
    },
    {
        "id": "RECURSION",
        "pattern": r"RecursionError|maximum recursion depth",
        "allvar": 5,
        "titel": "Oändlig rekursion",
        "orsak": "Två funktioner anropar varandra (oftast en wrapper som "
                 "monkeypatchats två gånger, t.ex. vid reload_plugins).",
        "atgard": "Leta efter dubbla hooks: app.run_pipeline/after-bindningar "
                 "som lindas in igen. Guard-flaggor (t.ex. "
                 "_al_logger_hooked) ska sättas FÖRE lindningen.",
    },
    {
        "id": "MEMORY",
        "pattern": r"MemoryError|Unable to allocate",
        "allvar": 5,
        "titel": "Slut på minne",
        "orsak": "För många bilder/PIL-objekt i minnet samtidigt (tumnaglar "
                 "som inte frigörs, Text-widget utan radtak).",
        "atgard": "Loggvisaren begränsar redan till 3000 rader/5000 cache-"
                 "poster. För galleriet: sänk thumbnail-storlek, stäng "
                 "förhandsgranskningar, och processa i omgångar.",
    },
    {
        "id": "ENCODING",
        "pattern": r"UnicodeDecodeError|UnicodeEncodeError|"
                   r"invalid \\\\u|character maps to",
        "allvar": 3,
        "titel": "Encoding-fel (Tcl/Tk 9.0 har strikt I/O-profil)",
        "orsak": "Tcl/Tk 9.0 kastar fel vid ogiltig encoding istället för att "
                 "ersätta tecken; filer lästa utan encoding='utf-8' på "
                 "Windows (cp1252) ger samma symptom.",
        "atgard": "Öppna ALLA filer med encoding=\"utf-8\" (och "
                 "errors=\"replace\" för loggläsning). Skriv filnamn med "
                 "pathlib, inte strängkonkatenering.",
    },
    {
        "id": "SINGLE-INSTANCE",
        "pattern": r"Redan igang|single.?instance|port 47200|"
                   r"En annan instans",
        "allvar": 3,
        "titel": "En annan instans kör redan",
        "orsak": "Single-instance-låset (socket port %d) hålls av en annan "
                 "process, så den nya instansen avslutar sig - vilket ser ut "
                 "som att 'appen inte startar'." % SINGLE_INSTANCE_PORT,
        "atgard": "Klicka på den befintliga systray-ikonen. Finns ingen ikon: "
                 "avsluta processen python/pythonw i Aktivitetshanteraren "
                 "(eller taskkill /IM pythonw.exe /F) och starta om.",
    },
    {
        "id": "FTP",
        "pattern": r"ftplib\.|FTP.*(misslyckades|timeout|refused)|"
                   r"error_perm|error_temp",
        "allvar": 3,
        "titel": "FTP-uppladdning misslyckades",
        "orsak": "Fel server/port/användare, passiv vs aktiv läge, eller "
                 "brandvägg. Lösenord sparas aldrig - ett tomt lösenord ger "
                 "error_perm 530.",
        "atgard": "Kontrollera Inställningar -> FTP (server/användare/sökväg) "
                 "och att målmappen finns. Testa med passivt läge och "
                 "brandväggen öppen för utgående port 21 + PASV-ports.",
    },
    {
        "id": "WATCHDOG-MISSING",
        "pattern": r"watchdog saknas|No module named 'watchdog'",
        "allvar": 2,
        "titel": "watchdog saknas (mappbevakning avstängd)",
        "orsak": "Valfritt beroende; utan det fungerar allt utom realtids-"
                 "bevakning av mappar.",
        "atgard": "python -m pip install watchdog==6.0.0 (eller använd "
                 "knappen 'Installera watchdog' i Bevakad mapp-fliken).",
    },
    {
        "id": "TK-CALLBACK",
        "pattern": r"TK-CALLBACK-FEL",
        "allvar": 4,
        "titel": "Undantag i en Tk-callback",
        "orsak": "Ett fel i en knapp/bind/after-callback. Tack vare "
                 "callback-vakten (P14-7) dog INTE appen - felet fångades och "
                 "loggades istället för att skrivas till stderr.",
        "atgard": "Läs tracebacken (DEBUG-raden direkt efter) för fil:rad. "
                 "Lägg in widget_exists()/try-except i den aktuella "
                 "callbacken om felet återkommer.",
    },
    {
        "id": "THREAD-CRASH",
        "pattern": r"OHANTERAT FEL I TRAD",
        "allvar": 5,
        "titel": "Bakgrundstråd dog",
        "orsak": "En worker-tråd (pipeline, watchdog, tray, FTP) kastade ett "
                 "ohanterat undantag. Fångades av threading.excepthook "
                 "(P14-6) - tidigare försvann det tyst.",
        "atgard": "Tracebacken i nästa DEBUG-rad visar fil:rad. Tråden måste "
                 "ofta startas om manuellt (t.ex. Kör-pipeline igen).",
    },
)

#: Kompilerade regler (en gång vid import)
_COMPILED = []
for _rule in RULES:
    try:
        _COMPILED.append((re.compile(_rule["pattern"], re.IGNORECASE), _rule))
    except re.error as _exc:                       # pragma: no cover
        safe_write("[diag] ogiltig regex %s: %s" % (_rule["id"], _exc))


def known_rule_ids():
    """Lista med alla regel-id:n (för test/rapport)."""
    return [r["id"] for r in RULES]


# ============================================================
# D1b. ANALYS AV LOGGTEXT
# ============================================================

def analyze_text(text, max_bevis=3):
    """
    Matcha en loggtext mot alla regler.

    Parametrar:
        text:      str (hel logg, en sektion eller inklistrad text)
        max_bevis: antal bevisrader som behålls per regel

    Returnerar: lista med finding-dicts (sorterad på allvar, fallande).
    """
    findings = []
    if not text:
        return findings
    lines = str(text).splitlines()
    for pattern, rule in _COMPILED:
        bevis, tider = [], []
        for line in lines:
            if pattern.search(line):
                if len(bevis) < max_bevis:
                    bevis.append(line.strip()[:220])
                tider.append(_line_time(line))
        if not bevis:
            continue
        tider = [t for t in tider if t]
        findings.append({
            "id":     rule["id"],
            "allvar": rule["allvar"],
            "titel":  rule["titel"],
            "orsak":  rule["orsak"],
            "atgard": rule["atgard"],
            "bug":    rule.get("bug", ""),
            "antal":  len(tider) or len(bevis),
            "forst":  tider[0] if tider else UNKNOWN,
            "sist":   tider[-1] if tider else UNKNOWN,
            "bevis":  bevis,
        })
    findings.sort(key=lambda f: (-f["allvar"], f["id"]))
    return findings


def analyze_entries(entries, max_bevis=3):
    """
    Analysera loggposter (list[dict] med time/level/message).

    Samma som analyze_text men behåller tid + nivå per post, och räknar
    antal träffar exakt.
    """
    findings = []
    if not entries:
        return findings
    for pattern, rule in _COMPILED:
        bevis, tider, niva = [], [], set()
        for entry in entries:
            msg = str(entry.get("message", ""))
            if not pattern.search(msg):
                continue
            niva.add(entry.get("level", UNKNOWN))
            tider.append(entry.get("time", UNKNOWN))
            if len(bevis) < max_bevis:
                bevis.append(msg.strip()[:220])
        if not bevis:
            continue
        findings.append({
            "id":     rule["id"],
            "allvar": rule["allvar"],
            "titel":  rule["titel"],
            "orsak":  rule["orsak"],
            "atgard": rule["atgard"],
            "bug":    rule.get("bug", ""),
            "antal":  len(tider),
            "forst":  tider[0] if tider else UNKNOWN,
            "sist":   tider[-1] if tider else UNKNOWN,
            "niva":   "/".join(sorted(niva)) or UNKNOWN,
            "bevis":  bevis,
        })
    findings.sort(key=lambda f: (-f["allvar"], f["id"]))
    return findings


def analyze_files(logs_dir, tails=400):
    """
    Analysera de filer som INTE finns i huvudloggen.

    Läses (skrivskyddat): stderr_fallback.log, crash_emergency.log,
    errors_*.log (senaste). Returnerar findings + en lista med de
    senaste raderna från fallback-filen (bevis).
    """
    out = {"findings": [], "fallback_tail": [], "crash_tail": []}
    try:
        logs = Path(logs_dir)
    except Exception:
        return out

    for name, key in (("stderr_fallback.log", "fallback_tail"),
                      ("crash_emergency.log", "crash_tail")):
        try:
            path = logs / name
            if not path.exists():
                continue
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                rows = f.read().splitlines()
            out[key] = rows[-tails:]
        except Exception as exc:
            safe_write("[diag] analyze_files %s: %s" % (name, exc))

    text = "\n".join(out["fallback_tail"] + out["crash_tail"])
    if text:
        out["findings"] = analyze_text(text)
    return out


# ============================================================
# SESSIONSDIFF (Y5) - nya fel jamfort med forra sessionen
# ============================================================

def _norm_err(msg):
    """Normalisera ett felmeddelande for diff (tar bort siffror/adresser)."""
    try:
        s = re.sub(r"0x[0-9a-fA-F]+", "0xN", str(msg))
        s = re.sub(r"\b\d+\b", "N", s)
        return s.strip()[:120]
    except Exception:
        return str(msg)[:120]


def session_diff(logs_dir, current_name=None, max_scan=40):
    """
    Jamfor nuvarande sessions fel mot den NAST senaste gallery-loggen (Y5).

    Returnerar dict:
        prev_file   namnet pa foregaende logg (eller tom strang)
        nya         lista av felmeddelanden som BARA finns i denna session
        losta       fel som fanns forr men inte nu
        aterkommande fel som finns i bada
    Tom dict vid fel / om det inte finns nagon tidigare session.
    """
    out = {}
    try:
        logs = Path(logs_dir)
        files = sorted(logs.glob("gallery_*.log"), key=lambda p: p.name)
        if current_name:
            files = [p for p in files if p.name != current_name]
        if not files:
            return {}
        prev = files[-1]
        prev_errs = set()
        with open(prev, "r", encoding="utf-8", errors="replace") as f:
            for line in f.read().splitlines()[-2000:]:
                if "[FEL" in line or "[VARNING" in line:
                    body = line.split("]", 2)[-1].strip()
                    if body:
                        prev_errs.add(_norm_err(body))
        out = {"prev_file": prev.name, "nya": [], "losta": [],
               "aterkommande": []}
        out["_prev_set"] = prev_errs
    except Exception as exc:
        safe_write("[diag] session_diff: %s" % exc)
    return out


def diff_current(entries, prev_set):
    """
    Klassificera nuvarande sessions fel mot prev_set fran session_diff().

    Returnerar (nya, aterkommande) som listor av strangar.
    """
    nya, ater = [], []
    try:
        seen = set()
        for e in entries:
            if e.get("level") not in ("FEL", "VARNING"):
                continue
            key = _norm_err(e.get("message", ""))
            if key in seen:
                continue
            seen.add(key)
            if key in prev_set:
                ater.append(key)
            else:
                nya.append(key)
    except Exception:
        pass
    return nya[:12], ater[:12]


def _line_time(line):
    """Plocka ut [HH:MM:SS.mmm] ur en loggrad (tom sträng om ingen)."""
    m = re.match(r"\s*\[?(\d{2}:\d{2}:\d{2}(?:\.\d{1,3})?)\]?", str(line))
    return m.group(1) if m else ""


# ============================================================
# D2. FÖNSTERDIAGNOSTIK ("varför syns inte fönstret?")
# ============================================================

def _config_dir():
    """config/-mapp (via helpers om möjligt)."""
    try:
        from helpers import get_config_path
        return Path(get_config_path())
    except Exception:
        return Path(__file__).parent.parent / "config"


def _read_json(path, default=None):
    """Läs JSON skrivskyddat; returnerar default vid minsta fel."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else default
    except Exception:
        return default if default is not None else {}


def _tk_call(app, method, *args, **kw):
    """Anrop på Tk-objekt med felångst (returnerar UNKNOWN vid fel)."""
    try:
        fn = getattr(app, method, None)
        if fn is None:
            return UNKNOWN
        return fn(*args, **kw)
    except Exception:
        return UNKNOWN


def check_single_instance(port=SINGLE_INSTANCE_PORT):
    """
    Är single-instance-porten upptagen av en ANNAN process?

    Returnerar (ledig: bool, info: str). Om låset hålls startar en ny
    instans inte alls - ett vanligt 'appen syns inte'-skäl.
    """
    s = None
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 0)
        s.settimeout(0.4)
        s.bind(("127.0.0.1", int(port)))
        return True, "port %d ledig (ingen annan instans)" % port
    except OSError as exc:
        return False, "port %d upptagen: %s" % (port, exc)
    except Exception as exc:
        return True, "kunde inte testas: %s" % exc
    finally:
        try:
            if s is not None:
                s.close()
        except Exception:
            pass


def window_report(app=None, context=None, logs_dir=None, startup_lines=None,
                  entries=None):
    """
    Svar på frågan "varför syns inte fönstret?" (D2).

    Returnerar dict:
        checks  - list[(status, text)] status i OK/INFO/VARNING/FEL/?
        verdict - en mening som förklarar läget
        fixes   - list[str] konkreta åtgärder i prioritetsordning
        data    - rådata (state, geometry, dpi ...) för rapport/logg

    Kontroller i ordning (Tk -> config -> tray -> startup.log -> logg):
      1 app finns/lever            6 alpha/transparent
      2 state (withdrawn/iconic)   7 overrideredirect
      3 mapped/viewable            8 start_minimized (settings.json)
      4 geometry + on-screen       9 systray-status (plugin + main)
      5 storlek (1x1?)            10 window_state.json (förgiftad?)
                                  11 startup.log-steg 15 (avsikten)
                                  12 single-instance-port
                                  13 init-fel/krascher i loggen
    """
    checks, fixes, data = [], [], {}
    context = context or {}
    entries = entries or []
    cfg_dir = _config_dir()

    # -- 1. app-referens -----------------------------------------
    if app is None:
        checks.append(("FEL", "Ingen app-referens (headless eller init felade)"))
        return {
            "checks": checks, "fixes": ["Starta om appen och läs logs/"],
            "verdict": "Kan inte avgöra fönstrets läge utan app-objekt.",
            "data": data,
        }

    exists = _tk_call(app, "winfo_exists")
    data["exists"] = exists
    if not exists:
        checks.append(("FEL", "app.winfo_exists() = %s (Tk-rot förstörd)"
                       % exists))
        fixes.append("Starta om appen; kontrollera att ingen anropar "
                     "destroy() i förtid (quit_app/on_close).")

    # -- 2. state ------------------------------------------------
    state = str(_tk_call(app, "state") or UNKNOWN)
    data["state"] = state
    state_text = {
        "withdrawn": "DOLT (withdraw) - syns varken i fält eller på skärm",
        "iconic":    "MINIMERAT till aktivitetsfältet",
        "normal":    "state=normal (fönstret ska vara uppritat)",
        "zoomed":    "maximerat",
    }.get(state, "state=%s" % state)
    checks.append((
        "INFO" if state in ("withdrawn", "iconic") else "OK",
        "Fönstrets state: %s" % state_text,
    ))

    # -- 3. mapped/viewable --------------------------------------
    mapped = _tk_call(app, "winfo_ismapped")
    viewable = _tk_call(app, "winfo_viewable")
    data["mapped"], data["viewable"] = mapped, viewable
    if state == "normal" and not mapped:
        checks.append(("FEL", "state=normal men winfo_ismapped()=%s - "
                              "fönstret är aldrig ritat" % mapped))
        fixes.append("Kontrollera att deiconify() körs (show_window) och att "
                     "mainloop() nås utan undantag.")
    else:
        checks.append(("OK", "winfo_ismapped=%s winfo_viewable=%s"
                       % (mapped, viewable)))

    # -- 4/5. geometri + on-screen -------------------------------
    geo = str(_tk_call(app, "geometry") or "")
    data["geometry"] = geo
    parsed = parse_geometry(geo)
    if parsed:
        data["size"] = "%dx%d" % (parsed["w"], parsed["h"])
        if parsed["w"] < 40 or parsed["h"] < 40:
            checks.append(("FEL", "Fönstret är %dx%d px - för litet för att "
                                  "synas/klickas" % (parsed["w"], parsed["h"])))
            fixes.append("Använd 'Rätta fönsterposition' nedan, eller radera "
                         "config/window_state.json.")
    on_screen, why = geometry_on_screen(geo, app)
    data["on_screen"], data["on_screen_why"] = on_screen, why
    checks.append((
        "OK" if on_screen else "FEL",
        "Geometri %s -> %s" % (geo or UNKNOWN, why),
    ))
    if not on_screen:
        fixes.append("Rätta positionen (knapp nedan) eller radera "
                     "config/window_state.json.")

    # -- 6. alpha ------------------------------------------------
    alpha = _tk_call(app, "wm_attributes", "-alpha")
    data["alpha"] = alpha
    try:
        if alpha is not None and alpha != UNKNOWN and float(alpha) <= 0.05:
            checks.append(("FEL", "Fönstret är transparent (alpha=%s)" % alpha))
            fixes.append("Sätt app.wm_attributes('-alpha', 1.0) - kontrollera "
                         "om ett tema/plugin sänkt alpha.")
    except Exception:
        pass

    # -- 7. overrideredirect -------------------------------------
    ovr = _tk_call(app, "overrideredirect")
    data["overrideredirect"] = ovr
    if ovr in (True, 1):
        checks.append(("VARNING", "overrideredirect=True - ingen titellist, "
                                  "kan hamna utanför skärmen utan sätt att "
                                  "flytta"))

    # -- 8. start_minimized --------------------------------------
    settings = _read_json(cfg_dir / "settings.json")
    start_min = settings.get("start_minimized", None)
    data["start_minimized"] = start_min
    checks.append((
        "INFO",
        "config/settings.json: start_minimized=%s autostart=%s theme=%s"
        % (start_min, settings.get("autostart"), settings.get("theme")),
    ))

    # -- 9. systray ----------------------------------------------
    tray = context.get("_system_tray")
    tray_info = {}
    if tray is not None:
        mod = sys.modules.get("plugins.system_tray")
        tray_info = {
            "plugin":        True,
            "available":     bool(getattr(mod, "TRAY_AVAILABLE", False))
                             if mod is not None else UNKNOWN,
            "running":       bool(getattr(tray, "_tray_running", False)),
            "visible":       bool(getattr(tray, "_tray_visible", False)),
            "icon_source":   str(getattr(tray, "_icon_source", UNKNOWN)),
        }
    else:
        tray_info = {"plugin": False}
    mgr = getattr(app, "_systray_mgr", None)
    tray_info["main_mgr"] = bool(mgr)
    data["tray"] = tray_info
    if tray_info.get("plugin"):
        checks.append((
            "OK" if tray_info["visible"] else "VARNING",
            "Systray-plugin: TRAY_AVAILABLE=%s kör=%s bekräftat_synlig=%s "
            "ikon=%s"
            % (tray_info["available"], tray_info["running"],
               tray_info["visible"], tray_info["icon_source"]),
        ))
    else:
        checks.append(("VARNING", "system_tray finns inte i context "
                                 "(pluginet laddades inte?)"))
    if not tray_info.get("plugin") and not tray_info.get("main_mgr"):
        checks.append(("FEL", "Ingen systray alls (varken plugin eller "
                              "main.pyw:s SystrayManager) - ett dolt fönster "
                              "kan inte nås"))
        fixes.append("python -m pip install pystray==0.19.5 Pillow==12.3.0, "
                     "eller sätt \"start_minimized\": false i "
                     "config/settings.json.")

    # -- 10. window_state.json -----------------------------------
    ws_path = cfg_dir / "window_state.json"
    ws = _read_json(ws_path, None)
    if ws is None:
        data["window_state"] = "saknas/trasig"
        checks.append(("VARNING" if ws_path.exists() else "INFO",
                       "config/window_state.json %s"
                       % ("är trasig (JSON-fel)" if ws_path.exists()
                          else "finns inte (standard 900x700 används)")))
        if ws_path.exists():
            fixes.append("Radera config/window_state.json (trasig/förgiftad).")
    else:
        ws_geo = str(ws.get("geometry", ""))
        ws_ok, ws_why = geometry_on_screen(ws_geo, app)
        data["window_state"] = ws_geo
        checks.append((
            "OK" if ws_ok else "FEL",
            "Sparad geometri '%s' -> %s" % (ws_geo, ws_why),
        ))
        if not ws_ok:
            fixes.append("Radera config/window_state.json eller använd "
                         "'Rätta fönsterposition'.")

    # -- 11. startup.log (orsaksloggen) --------------------------
    s_lines = startup_lines if startup_lines is not None else []
    decision = [ln for ln in s_lines if "Visa fönster" in ln or "15." in ln]
    data["startup_decision"] = decision[-2:] if decision else []
    if decision:
        checks.append(("INFO", "startup.log steg 15: %s"
                       % " || ".join(x.strip()[:150] for x in decision[-2:])))
    show_calls = [ln for ln in s_lines if "show_window" in ln]
    data["startup_show_window"] = show_calls[-2:] if show_calls else []
    if show_calls:
        checks.append(("INFO", "startup.log show_window: %s"
                       % " || ".join(x.strip()[:150]
                                     for x in show_calls[-2:])))
    crash = [ln for ln in s_lines if "KRASCH" in ln or "FEL:" in ln]
    if crash:
        checks.append(("FEL", "startup.log innehåller %d fel-/kraschrader, "
                              "senaste: %s"
                       % (len(crash), crash[-1].strip()[:180])))
        fixes.append("Läs logs/startup.log rad för rad - den visar exakt var "
                     "startkedjan avbröts.")

    # -- 12. single instance -------------------------------------
    # OBS: appen sjalv haller laget (helpers.SingleInstanceLock), sa ett
    # rent porttest alltid skulle svara "upptagen". Därför frågar vi först
    # låset om DET är vårt - annars testas porten (W7).
    lock = getattr(app, "_instance_lock", None)
    held = None
    if lock is not None:
        try:
            held = bool(lock.is_held())
        except Exception:
            held = None
    if held:
        ledig, portinfo = True, "vårt eget single-instance-lås hålls (förväntat)"
    else:
        ledig, portinfo = check_single_instance()
    data["port"] = portinfo
    checks.append(("OK" if ledig else "VARNING", "Single-instance: %s"
                   % portinfo))
    if not ledig:
        fixes.append("En annan instans kör: klicka på dess systray-ikon, eller "
                     "avsluta pythonw.exe i Aktivitetshanteraren.")

    # -- 13. plugin-krascher i loggen ----------------------------
    initfel = [e for e in entries
               if "init-fel" in str(e.get("message", ""))
               or "laddningsfel" in str(e.get("message", ""))]
    data["plugin_init_errors"] = len(initfel)
    if initfel:
        checks.append(("FEL", "%d plugin kraschade i init/laddning - deras "
                              "flikar saknas: %s"
                       % (len(initfel),
                          ", ".join(str(e.get("message", ""))[:60]
                                    for e in initfel[:4]))))
        fixes.append("Läs tracebacken i logs/errors_*.log; sektion 3 i denna "
                     "rapport matchar mönstret mot kända fel.")

    # -- SLUTSATS -------------------------------------------------
    verdict, severity = _verdict(state, mapped, on_screen, tray_info,
                                 start_min, ledig)
    data["severity"] = severity
    return {"checks": checks, "fixes": fixes, "verdict": verdict, "data": data}


def _verdict(state, mapped, on_screen, tray, start_min, port_free):
    """Kokar ner alla kontroller till EN mening + allvar (1-5)."""
    if state == "withdrawn":
        if tray.get("visible"):
            return (
                "Fönstret är DOLT med flit (start_minimized=%s) och "
                "systray-ikonen är bekräftat synlig - klicka på ikonen för "
                "att visa appen." % start_min,
                1,
            )
        if tray.get("running") and not tray.get("visible"):
            return (
                "Fönstret är DOLT och systray-ikonen är INTE bekräftat "
                "synlig -> appen är just nu ONÅBAR (P14-10).",
                5,
            )
        if not tray.get("plugin"):
            return (
                "Fönstret är DOLT och systray-pluginet saknas -> appen är "
                "ONÅBAR. Sätt start_minimized=false eller installera pystray.",
                5,
            )
        return (
            "Fönstret är DOLT (start_minimized=%s) men ikonen är inte "
            "bekräftad synlig - risk att appen är onåbar." % start_min,
            4,
        )
    if state == "iconic":
        return "Fönstret är minimerat till aktivitetsfältet (state=iconic).", 1
    if not on_screen:
        return (
            "Fönstret är öppet men ligger UTANFÖR skärmen eller är för litet "
            "- det ser ut som att appen inte startade.",
            4,
        )
    if state == "normal" and not mapped:
        return ("state=normal men fönstret är aldrig ritat (ismapped=0) - "
                "mainloop eller deiconify har inte körts."), 5
    if not port_free:
        return ("Den här instansen startade troligen inte: en annan process "
                "håller single-instance-låset."), 3
    return "Fönstret är synligt och normalt (state=normal, inom skärmen).", 1


# ============================================================
# D3. MILJÖ-RAPPORT
# ============================================================

def environment_report(app=None, logs_dir=None, files_stats=None):
    """
    Samla miljön i en rapport (D3).

    Returnerar list[(status, text)] - allt från Python/Tk-version till
    skrivbara mappar och skärmgeometri. Reser aldrig.
    """
    out = []
    out.append(("OK", "Python %s (%s) | %s"
                % (sys.version.split()[0],
                   "64-bit" if sys.maxsize > 2 ** 32 else "32-bit",
                   sys.platform)))
    out.append(("OK", "Tk/Tcl %s%s"
                % (tk_version(app),
                   "  <-- 9.0: legacy trace_variable är borttaget"
                   if is_tk9(app) else "")))
    scaling, dpi = tk_scaling(app), screen_dpi(app)
    out.append(("OK" if dpi else "INFO",
                "Skalning: tk scaling=%s -> %s DPI (100%% = 96 DPI)"
                % (("%.4f" % scaling) if scaling else UNKNOWN,
                   dpi or UNKNOWN)))
    rect = screen_rect(app)
    out.append(("OK" if rect["ok"] else "INFO",
                "Skärm: %dx%d px, virtuellt skrivbord %dx%d"
                % (rect["sw"], rect["sh"], rect["vw"], rect["vh"])))
    out.append(("OK", "argv: %s" % " ".join(sys.argv[:4])))

    # skrivbarhet
    for label, path in (("logs", logs_dir), ("config", _config_dir())):
        if not path:
            continue
        try:
            p = Path(path)
            p.mkdir(parents=True, exist_ok=True)
            probe = p / ".diag_write_test"
            probe.write_text("ok", encoding="utf-8")
            probe.unlink()
            out.append(("OK", "%s/ skrivbar: %s" % (label, p)))
        except Exception as exc:
            out.append(("FEL", "%s/ EJ skrivbar (%s): %s"
                        % (label, path, exc)))

    # diskutrymme (Y6): full loggdisk = tyst tappade loggar
    free = disk_free_mb(logs_dir or ".")
    if free < 0:
        out.append(("INFO", "Diskutrymme: kunde inte avläsas"))
    elif free < 100:
        out.append(("FEL", "Diskutrymme: ENDAST %d MB ledigt - loggning "
                            "kan tyst misslyckas" % free))
    elif free < 500:
        out.append(("VARNING", "Diskutrymme: %d MB ledigt (lågt)" % free))
    else:
        out.append(("OK", "Diskutrymme: %d MB ledigt" % free))

    # beroenden
    for mod, pkg in (("PIL", "Pillow"), ("pystray", "pystray"),
                     ("watchdog", "watchdog"), ("darkdetect", "darkdetect")):
        try:
            m = __import__(mod)
            ver = getattr(m, "__version__", getattr(m, "VERSION", UNKNOWN))
            out.append(("OK", "+ %s %s" % (pkg, ver)))
        except ImportError:
            lvl = "VARNING" if pkg in ("Pillow", "pystray") else "INFO"
            out.append((lvl, "- %s saknas -> pip install %s" % (pkg, pkg)))
        except Exception as exc:
            out.append(("FEL", "! %s importerbar men trasig: %s" % (pkg, exc)))

    if files_stats:
        out.append(("OK" if files_stats.get("main_open") else "FEL",
                    "Loggfiler: %s (öppen=%s) | felfil: %s (öppen=%s) | "
                    "skrivna rader=%s varav fel=%s"
                    % (files_stats.get("main", UNKNOWN),
                       files_stats.get("main_open"),
                       files_stats.get("errors", UNKNOWN),
                       files_stats.get("err_open"),
                       files_stats.get("written"),
                       files_stats.get("errors"))))
    return out


# ============================================================
# RAPPORT-RENDERING
# ============================================================

STATUS_MARK = {"OK": "[OK]   ", "INFO": "[INFO] ",
               "VARNING": "[VARN] ", "FEL": "[FEL]  ", "?": "[?]    "}


def render_report(window=None, environment=None, findings=None,
                  extra=None, width=78):
    """
    Bygg textblocket som både loggas och visas i diagnostikfönstret.

    Parametrar:
        window:      dict från window_report() (kan vara None)
        environment: list[(status, text)] från environment_report()
        findings:    list från analyze_entries()/analyze_text()
        extra:       dict med t.ex. {"fallback_tail": [...]}
        width:       radbredd för avdelare

    Returnerar: (report_text, worst_allvar)
    """
    sep = "=" * width
    thin = "-" * width
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    worst = 1
    rows = [sep,
            " AI-FELSÖKNING  %s" % now,
            " advanced_logger - automatisk orsak/åtgärd (D1-D3)",
            sep]

    # 1. fönstret
    rows.append("")
    rows.append("1. VARFÖR SYNS / SYNS INTE FÖNSTRET?")
    rows.append(thin)
    if window:
        for status, text in window.get("checks", []):
            rows.append("  %s%s" % (STATUS_MARK.get(status, "[?]    "), text))
        rows.append("")
        rows.append("  SLUTSATS: %s" % window.get("verdict", UNKNOWN))
        worst = max(worst, int(window.get("data", {}).get("severity", 1)))
        fixes = window.get("fixes", [])
        if fixes:
            rows.append("  ÅTGÄRD (i ordning):")
            for i, fix in enumerate(fixes, 1):
                rows.append("    %d) %s" % (i, fix))
    else:
        rows.append("  [?]    Ingen app-referens - rapporten körs headless")

    # 2. miljö
    rows.append("")
    rows.append("2. MILJÖ OCH BERENDEN")
    rows.append(thin)
    for status, text in (environment or []):
        rows.append("  %s%s" % (STATUS_MARK.get(status, "[?]    "), text))

    # 3. felmönster
    rows.append("")
    rows.append("3. KÄNDA FELMÖNSTER I LOGGEN (%d regler)" % len(RULES))
    rows.append(thin)
    if findings:
        for f in findings:
            worst = max(worst, int(f["allvar"]))
            rows.append("  [%s] %s  (%d träffar, först %s, sist %s)"
                        % (ALLVAR_TEXT.get(f["allvar"], "?"), f["id"],
                           f["antal"], f["forst"], f["sist"]))
            rows.append("         %s" % f["titel"])
            rows.append("         Orsak : %s" % f["orsak"])
            rows.append("         Åtgärd: %s" % f["atgard"])
            if f.get("bug"):
                rows.append("         Ref   : %s (spec.md §22)" % f["bug"])
            for b in f.get("bevis", [])[:2]:
                rows.append("         Bevis : %s" % b)
            rows.append("")
    else:
        rows.append("  [OK]   Inget känt felmönster matchade loggen.")

    # 4. extra bevis (fallback/crash-filer)
    if extra:
        for key, title in (("fallback_tail", "logs/stderr_fallback.log"),
                           ("crash_tail", "logs/crash_emergency.log")):
            tail = extra.get(key) or []
            if not tail:
                continue
            rows.append("")
            rows.append("4. SISTA RADERNA I %s (%d)" % (title, len(tail)))
            rows.append(thin)
            for line in tail[-12:]:
                rows.append("  %s" % line.strip()[:width - 4])

    # 5. nästa steg
    rows.append("")
    rows.append("NÄSTA STEG")
    rows.append(thin)
    for i, step in enumerate(next_steps(window, findings), 1):
        rows.append("  %d) %s" % (i, step))
    rows.append(sep)
    return "\n".join(rows), worst


def chat_transcript(window=None, findings=None, max_fynd=4):
    """
    Tydlig AI-chatt-sammanfattning (W8).

    Formaterar rapporten som frågor/svar så att den går att klistra in i
    valfri AI-chatt (eller läsas snabbt av en människa). Tre frågor:
      1. Varför syns inte fönstret?
      2. Vad har gått fel i loggen?
      3. Vad gör jag nu?
    """
    lines = [
        "AI-CHATT (sammanfattning - kan klistras in i valfri AI-chatt)",
        "-" * 62,
    ]
    verdict = (window or {}).get("verdict", "Ingen fönsterrapport (headless).")
    lines.append("  Du: Varfor syns inte fonstret?")
    lines.append("  AI: %s" % verdict)
    flagged = [c for c in (window or {}).get("checks", [])
               if c[0] in ("FEL", "VARNING")]
    for status, text in flagged[:4]:
        lines.append("      - [%s] %s" % (status, text))
    lines.append("")
    lines.append("  Du: Vad har gatt fel i loggen?")
    if findings:
        lines.append("  AI: %d kanda felmonster matchade:" % len(findings))
        for f in findings[:max_fynd]:
            lines.append(
                "      - %s (%s, %d traffar, forst %s): %s"
                % (f["id"], ALLVAR_TEXT.get(f["allvar"], "?"), f["antal"],
                   f["forst"], f["titel"])
            )
        if len(findings) > max_fynd:
            lines.append("      - ... och %d till (se full rapport)"
                         % (len(findings) - max_fynd))
    else:
        lines.append("  AI: Inget kant felmonster matchade loggen.")
    lines.append("")
    lines.append("  Du: Vad gor jag nu?")
    for i, step in enumerate(next_steps(window, findings)[:4], 1):
        lines.append("  AI: %d) %s" % (i, step))
    lines.append("-" * 62)
    return "\n".join(lines)


def next_steps(window=None, findings=None):
    """Kort, prioriterad att-göra-lista (max 6 steg)."""
    steps = []
    if window:
        for fix in window.get("fixes", []):
            if fix not in steps:
                steps.append(fix)
    for f in (findings or []):
        if f["allvar"] >= 4 and f["atgard"] not in steps:
            steps.append(f["atgard"])
    if not steps:
        steps.append("Inget att åtgärda - logga om något ändå känns fel.")
    steps.append("Bifoga logs/errors_*.log + denna rapport vid supportärende.")
    return steps[:6]


def suggest_geometry_fix(app=None, window_state_path=None):
    """
    Föreslå en rättad geometri (används av knappen i UI).

    Returnerar (nuvarande, föreslagen, behövs: bool). Ändrar INGET på
    disk - användaren bekräftar i UI först.
    """
    current = str(_tk_call(app, "geometry") or "")
    suggested = fit_to_screen(current, app)
    on_screen, _why = geometry_on_screen(current, app)
    return current, suggested, (not on_screen) or (suggested != current)


def summary_line(window=None, findings=None):
    """En rad för loggen: 'DIAGNOSTIK: 2 fel, 1 varning, slutsats ...'."""
    fel = warn = 0
    if window:
        for status, _t in window.get("checks", []):
            if status == "FEL":
                fel += 1
            elif status == "VARNING":
                warn += 1
    kritiska = [f for f in (findings or []) if f["allvar"] >= 4]
    return (
        "DIAGNOSTIK: %d felflaggor, %d varningar, %d kritiska mönster - %s"
        % (fel, warn, len(kritiska),
           (window or {}).get("verdict", "ingen fönsterrapport")[:120])
    )
