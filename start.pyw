#!/usr/bin/env python3
"""GUI entry point for Windows, macOS and Linux."""
import os
from pathlib import Path
import runpy
import sys

BASE = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE))

if __name__ == "__main__":
    try:
        from auto_update import check_before_start
        check_before_start(BASE)
        # main.pyw is read only after the update has completed.
        runpy.run_path(str(BASE / "main.pyw"), run_name="__main__")
    except Exception:
        import traceback
        try:
            logs = BASE / "logs"
            logs.mkdir(exist_ok=True)
            (logs / "launcher.log").write_text(traceback.format_exc(), encoding="utf-8")
        except OSError:
            pass
        try:
            import tkinter as tk
            from tkinter import messagebox
            root = tk.Tk()
            root.withdraw()
            messagebox.showerror("FTP-uploader", "Kunde inte starta. Se logs/launcher.log.")
            root.destroy()
        except Exception:
            pass
        sys.exit(1)
