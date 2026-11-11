#!/usr/bin/env python3
# ============================================================
# Gallery Uploader – Guard-/startup-logik for main.pyw
# ============================================================
# FIL:      main_guards.py
# PLATS:    projektrot (ftp_gallery_uploader/)
# VERSION:  1.0.0
# AUTHOR:   Rickard Längkvist
# COPYRIGHT: Copyright (c) <år> Rickard Längkvist (dynamiskt år)
# Syfte:    Samla konsol-fria vakter och start-logik sa att
#           main.pyw halls under 1800 rader (spec §20 ATGARD).
#           Flyttad fran main.pyw v2.7.0 vid v2.8.0 (M4).
#
# INNEHALL:
#   safe_write(message)              saker skrivning (stderr -> fil)
#   EMERGENCY_LOG / emergency_excepthook / install_excepthook
#   set_startup_crash_callback(cb)   spegla krasch i startup.log
#   AUTOSTART_* / autostart_launcher_cmd / autostart_registered_value
#                                    / set_autostart  (Windows HKCU Run)
#   cleanup_pycache(base, mode, smart_cache)  (A4, PROD-rensning)
#
# REGLER:
#   - Ingen print() och inga f-strings (%-formatering).
#   - Importerar INTE tkinter/helpers vid modulniva (anvands
#     fore helpers-importen i main.pyw).
# ============================================================

import sys
import os
import io
import shutil
import traceback
import app_paths
from pathlib import Path
from datetime import datetime

VERSION = "1.0.0"

# Samma rot som main.pyw (bada ligger i projektroten)
BASE_DIR = Path(__file__).resolve().parent

# Kraschlogg (L4: allt under logs/)
EMERGENCY_LOG = app_paths.app_dir() / "logs" / "crash_emergency.log"
try:
    EMERGENCY_LOG.parent.mkdir(parents=True, exist_ok=True)
except Exception:
    pass

# Callback som speglar kraschar i logs/startup.log (satts av main
# efter helpers-importen; innan dess None = hoppa over).
_STARTUP_CRASH_CB = None


def set_startup_crash_callback(cb) -> None:
    """
    Registrera callback for kraschspegling i startup.log.

    main.pyw anropar denna efter helpers-importen. Fixar den
    latenta buggen i v2.7.0 dar emergency_excepthook refererade
    log_startup_crash innan den importerats (NameError atets tyst).
    """
    global _STARTUP_CRASH_CB
    _STARTUP_CRASH_CB = cb


# ==============================================================================
# SAKER SKRIVNING
# ==============================================================================

def safe_write(message: str) -> None:
    """
    Skriv ett meddelande utan att krascha om stderr ar stangd.

    Forsoker i ordning:
      1. sys.stderr
      2. sys.__stderr__
      3. logs/stderr_fallback.log (under BASE_DIR)
    """
    for stream in (sys.stderr, sys.__stderr__):
        try:
            if stream and hasattr(stream, "write"):
                stream.write("%s\n" % message)   # M1: ingen f-string
                stream.flush()
                return
        except (OSError, AttributeError, io.UnsupportedOperation):
            continue
    try:
        log_dir = app_paths.logs_dir()
        log_dir.mkdir(exist_ok=True)
        with open(log_dir / "stderr_fallback.log", "a", encoding="utf-8") as f:
            f.write(
                "[%s] %s\n" % (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), message)
            )
    except Exception:
        pass


# ==============================================================================
# GLOBAL EXCEPTHOOK (kraschlogg + valfri messagebox)
# ==============================================================================

def emergency_excepthook(exc_type, exc_value, exc_tb):
    """
    Global undantagsfangare - skriver till fil, aldrig print.

    Visas som messagebox om tkinter ar tillgangligt.
    Kraschen speglas aven i startup.log om callback registrerats.
    """
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_tb)
        return

    msg = "".join(
        traceback.format_exception(exc_type, exc_value, exc_tb)
    )

    try:
        with open(EMERGENCY_LOG, "a", encoding="utf-8") as f:
            f.write(
                "\n[%s] KRASCH:\n%s\n%s\n"
                % (datetime.now(), msg, "=" * 60)
            )
    except Exception:
        pass

    # Spegla kraschen i startup.log - en fil visar allt (L3).
    if _STARTUP_CRASH_CB:
        try:
            _STARTUP_CRASH_CB(msg)
        except Exception:
            pass

    safe_write("[KRASCH] %s: %s" % (exc_type.__name__, exc_value))

    try:
        import tkinter.messagebox as mb
        mb.showerror(
            "Gallery Uploader – Kritiskt fel",
            "%s: %s\n\nDetaljer sparade i:\n%s"
            % (exc_type.__name__, exc_value, EMERGENCY_LOG.resolve()),
        )
    except Exception:
        pass


def install_excepthook() -> None:
    """Aktivera den globala undantagsfangaren."""
    sys.excepthook = emergency_excepthook


# ==============================================================================
# AUTOSTART (A11 – Windows HKCU Run)
# ==============================================================================

AUTOSTART_APP_NAME = "GalleryUploader"
AUTOSTART_REG_KEY  = r"Software\Microsoft\Windows\CurrentVersion\Run"


def autostart_launcher_cmd() -> str:
    from windows_autostart import command
    return command()


def autostart_registered_value():
    from windows_autostart import registered
    return registered()


def set_autostart(enabled: bool) -> bool:
    try:
        from windows_autostart import set_enabled
        return set_enabled(enabled)
    except Exception as exc:
        safe_write("[AUTOSTART] Kunde inte uppdatera Windows-genvägen: %s" % exc)
        return False


# ==============================================================================
# CACHE-RENSNING (A4 – PROD)
# ==============================================================================

def cleanup_pycache(base_dir=None, mode: str = "dev",
                    smart_cache: bool = True) -> tuple:
    """
    Rensa __pycache__ + losa .pyc/.pyo i PROD-lage (A4).

    Kors bara om: smart_cache=false (tvingad) ELLER mode=prod.
    Skyddade mappar rors ALDRIG (config, logs, assets, out,
    data, In, json, .git, venv, .idea, .vscode, node_modules).
    Symlankar foljs aldrig; varje rmtree i egen try/except.

    Returnerar (removed_dirs, removed_files).
    """
    removed_dirs  = 0
    removed_files = 0
    try:
        smart = bool(smart_cache)
        if smart and mode != "prod":
            return (0, 0)   # DEV behaller cache (snabb iteration)

        protected = {
            "config", "logs", "assets", "out", "data", "In",
            "json", "sap", "dispatch", "xlsx",
            ".git", ".venv", "venv", "env",
            ".idea", ".vscode", "node_modules",
        }
        base = Path(base_dir) if base_dir else BASE_DIR

        for root, dirs, files in os.walk(
            base, topdown=True, followlinks=False
        ):
            rel = Path(root).relative_to(base)
            if set(rel.parts) & protected:
                dirs[:] = []
                continue

            # Rensa __pycache__-kataloger
            kept = []
            for d in dirs:
                p = Path(root) / d
                if (
                    d == "__pycache__" and p.is_dir()
                    and not p.is_symlink()
                ):
                    try:
                        shutil.rmtree(p)
                        removed_dirs += 1
                        safe_write("[CACHE] Borttagen: %s" % p)
                    except Exception as exc:
                        safe_write(
                            "[CACHE] Kunde inte ta bort %s: %s"
                            % (p, exc)
                        )
                else:
                    kept.append(d)
            dirs[:] = kept

            # Losa .pyc/.pyo utanfor __pycache__
            for f in files:
                if f.endswith((".pyc", ".pyo")):
                    try:
                        (Path(root) / f).unlink()
                        removed_files += 1
                    except Exception:
                        pass
    except Exception as exc:
        safe_write("[CACHE] Rensning misslyckades: %s" % exc)
    return (removed_dirs, removed_files)
