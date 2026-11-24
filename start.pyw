#!/usr/bin/env python3
# Copyright (c) 2026 Rickard Längkvist
"""GUI entry point for Windows, macOS and Linux."""
import os
from display_runtime import enable_dpi_awareness
enable_dpi_awareness()
from pathlib import Path
import runpy
import sys

BASE = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE))
from startup_diagnostics import install, phase
install(BASE)

if __name__ == "__main__":
    try:
        from python_discovery import select_for_start
        select_for_start(BASE / 'start.pyw')
        from single_instance import ensure_primary
        if ensure_primary() is None:
            sys.exit(0)
        from log_archive import prepare_logs
        prepare_logs()
        from app_icon import set_windows_app_id
        set_windows_app_id()
        from auto_update import check_before_start
        from app_paths import update_settings
        phase('Kontrollerar väntande releaseinstallation')
        if update_settings().get('pending_release') and not os.environ.get('FTP_UPLOADER_SILENT_RESTART'):
            check_before_start(BASE)
        # main.pyw is read only after the update has completed.
        phase('Laddar main.pyw')
        runpy.run_path(str(BASE / "main.pyw"), run_name="__main__")
    except Exception:
        from startup_diagnostics import report
        report(*sys.exc_info())
        import traceback
        try:
            from app_paths import logs_dir
            logs = logs_dir()
            logs.mkdir(exist_ok=True)
            from log_clock import timestamp
            (logs / "launcher.log").write_text("[%s] KRASCH\n%s" % (timestamp(), traceback.format_exc()), encoding="utf-8")
        except OSError:
            pass
        try:
            from error_summary import ErrorSummary
            ErrorSummary().close()
        except Exception:
            pass
        try:
            import tkinter as tk
            from tkinter import messagebox
            root = tk.Tk()
            root.withdraw()
            from app_icon import apply_tk_window_icon
            apply_tk_window_icon(root)
            messagebox.showerror("FTP-uploader", "Kunde inte starta. Se logs/launcher.log.")
            root.destroy()
        except Exception:
            pass
        sys.exit(1)
