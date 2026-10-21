#!/usr/bin/env python3
# ============================================================
# FTP-Galleri – pip-tillbehor vid start
# ============================================================
# FIL:      ensure_deps.py
# PLATS:    projektrot (bredvid main.pyw)
# VERSION:  1.1.0
# AUTHOR:   Rickard Langkvist
# Syfte:    Om ett paket i requirements.txt saknas eller har
#           fel version installeras/uppdateras det automatiskt
#           INNAN plugins laddas. Visar en progressbar.
#           Kor bara vid behov – annars noll UI och noll pip.
#
# REGLER:   ingen print(), inga f-strangar (%-formatering).
#           Widget padx/pady = EN siffra (Tk 9).
# ============================================================

import sys
import subprocess
import threading
from datetime import datetime
from pathlib import Path

VERSION = "1.1.0"

_LOG_NAME = "deps.log"

# pip-namn -> importnamn (for snabb saknas-koll)
_IMPORT_NAME = {
    "Pillow": "PIL",
    "pystray": "pystray",
    "six": "six",
    "watchdog": "watchdog",
    "darkdetect": "darkdetect",
    "python-xlib": "Xlib",
    "pyobjc-framework-Quartz": "Quartz",
}


def _log(base, message):
    """Skriv en rad till logs/deps.log. Aldrig krascha."""
    try:
        path = Path(base) / "logs" / _LOG_NAME
        path.parent.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with path.open("a", encoding="utf-8") as fh:
            fh.write("%s  %s\n" % (stamp, message))
    except Exception:
        pass


def _marker_ok(marker):
    """Enkel sys_platform-markor. Okant = ta med paketet."""
    if not marker:
        return True
    text = marker.strip()
    plat = sys.platform
    want = None
    if '"' in text:
        parts = text.split('"')
        if len(parts) >= 2:
            want = parts[1]
    elif "'" in text:
        parts = text.split("'")
        if len(parts) >= 2:
            want = parts[1]
    if want is None:
        return True
    if "!=" in text:
        return plat != want
    if "==" in text:
        return plat == want
    return True


def _parse_requirements(req_path):
    """Lista (pip_namn, version_eller_None) fran requirements.txt."""
    specs = []
    try:
        raw = Path(req_path).read_text(encoding="utf-8")
    except Exception:
        return specs
    for line in raw.splitlines():
        text = line.strip()
        if not text or text.startswith("#"):
            continue
        marker = ""
        if ";" in text:
            text, marker = text.split(";", 1)
            text = text.strip()
            marker = marker.strip()
        if not _marker_ok(marker):
            continue
        name = text
        ver = None
        if "==" in text:
            name, ver = text.split("==", 1)
            name = name.strip()
            ver = ver.strip()
        if name:
            specs.append((name, ver))
    return specs


def _installed_version(dist_name):
    """Returnera installerad version eller None."""
    try:
        import importlib.metadata as meta
        return meta.version(dist_name)
    except Exception:
        pass
    try:
        import pkg_resources
        return pkg_resources.get_distribution(dist_name).version
    except Exception:
        return None


def _needed(specs):
    """Paket som saknas eller inte matchar pinnad version."""
    jobs = []
    for name, ver in specs:
        inst = _installed_version(name)
        if inst is None:
            jobs.append((name, ver, "saknas"))
            continue
        if ver and inst.strip() != ver.strip():
            jobs.append((name, ver, "uppdatera %s -> %s" % (inst, ver)))
    return jobs


def hide_console():
    """Dolj/koppla bort Windows-konsolen. Saker att kalla flera ganger."""
    if sys.platform != "win32":
        return
    try:
        import ctypes
        kernel32 = ctypes.windll.kernel32
        user32 = ctypes.windll.user32
        hwnd = kernel32.GetConsoleWindow()
        if hwnd:
            user32.ShowWindow(hwnd, 0)
        kernel32.FreeConsole()
        hwnd = kernel32.GetConsoleWindow()
        if hwnd:
            user32.ShowWindow(hwnd, 0)
    except Exception:
        pass


def _pip_python():
    """
    python.exe for pip (pythonw -m pip misslyckas tyst).

    CREATE_NO_WINDOW doljer konsolen pa python.exe.
    """
    try:
        exe = Path(sys.executable)
        if exe.name.lower() == "pythonw.exe":
            cand = exe.with_name("python.exe")
            if cand.is_file():
                return str(cand)
    except Exception:
        pass
    return sys.executable


def _pip_kwargs():
    """subprocess-kwargs: ingen konsol, fanga utdata."""
    kw = {
        "stdout": subprocess.PIPE,
        "stderr": subprocess.STDOUT,
        "stdin": subprocess.DEVNULL,
        "timeout": 300,
    }
    try:
        kw["text"] = True
        kw["encoding"] = "utf-8"
        kw["errors"] = "replace"
    except Exception:
        pass
    if sys.platform == "win32":
        kw["creationflags"] = getattr(
            subprocess, "CREATE_NO_WINDOW", 0x08000000
        )
        try:
            si = subprocess.STARTUPINFO()
            si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            si.wShowWindow = 0
            kw["startupinfo"] = si
        except Exception:
            pass
    return kw


def _run_pip(spec):
    """
    pip install --upgrade <spec>. Returnerar (ok, utdrag).

    Forsoker utan --user forst, sedan med --user.
    Anvander python.exe + CREATE_NO_WINDOW (ingen konsol).
    """
    exe = _pip_python()
    last = ""
    for extra in ([], ["--user"]):
        cmd = [
            exe, "-m", "pip", "install",
            "--disable-pip-version-check",
            "--upgrade",
        ]
        cmd.extend(extra)
        cmd.append(spec)
        try:
            proc = subprocess.run(cmd, **_pip_kwargs())
        except subprocess.TimeoutExpired:
            hide_console()
            return False, "timeout"
        except Exception as exc:
            last = str(exc)
            hide_console()
            continue
        hide_console()
        out = (proc.stdout or "").strip()
        last = out[-400:] if out else "kod %s" % proc.returncode
        if proc.returncode == 0:
            return True, last
    return False, last


def _ensure_pip(base):
    """Om pip saknas, bootstrap via ensurepip."""
    try:
        proc = subprocess.run(
            [_pip_python(), "-m", "pip", "--version"],
            **_pip_kwargs()
        )
        hide_console()
        if proc.returncode == 0:
            return True
    except Exception:
        hide_console()
        pass
    try:
        import ensurepip
        ensurepip.bootstrap(upgrade=True)
        _log(base, "ensurepip.bootstrap ok")
        return True
    except Exception as exc:
        _log(base, "ensurepip misslyckades: %s" % exc)
        return False


def _center(win, width, height):
    try:
        win.update_idletasks()
        sw = win.winfo_screenwidth()
        sh = win.winfo_screenheight()
        x = max(0, (sw - width) // 2)
        y = max(0, (sh - height) // 3)
        win.geometry("%dx%d+%d+%d" % (width, height, x, y))
    except Exception:
        pass


def _show_progress(base, jobs):
    """
    Tk-fonster med determinate progressbar.

    Returnerar (ok, misslyckade_namn).
    """
    import tkinter as tk
    from tkinter import ttk, messagebox

    total = len(jobs)
    state = {
        "i": 0,
        "status": "Forbereder...",
        "done": False,
        "failed": [],
        "ok": True,
    }

    root = tk.Tk()
    root.title("FTP-Galleri")
    root.resizable(False, False)
    try:
        ico = Path(base) / "icon" / "icon.ico"
        if ico.is_file():
            root.iconbitmap(str(ico))
    except Exception:
        pass
    try:
        root.attributes("-topmost", True)
    except Exception:
        pass
    try:
        root.protocol("WM_DELETE_WINDOW", lambda: None)
    except Exception:
        pass

    wrap = ttk.Frame(root)
    wrap.pack(fill="both", expand=True, padx=18, pady=14)

    title = ttk.Label(
        wrap,
        text="Installerar Python-tillbehor",
        font=("Segoe UI", 12, "bold"),
    )
    title.pack(anchor="w", pady=0)

    sub = ttk.Label(
        wrap,
        text="Kontrollerar och uppdaterar %s paket." % total,
    )
    sub.pack(anchor="w", pady=4)

    status = ttk.Label(wrap, text="Forbereder...")
    status.pack(anchor="w", pady=6)

    bar = ttk.Progressbar(
        wrap, mode="determinate", maximum=100, length=420
    )
    bar.pack(fill="x", pady=4)

    pct = ttk.Label(wrap, text="0 %")
    pct.pack(anchor="e", pady=2)

    _center(root, 460, 170)
    try:
        root.lift()
        root.focus_force()
    except Exception:
        pass

    def worker():
        for idx, (name, ver, why) in enumerate(jobs):
            spec = ("%s==%s" % (name, ver)) if ver else name
            state["i"] = idx
            state["status"] = "%s  (%s)" % (spec, why)
            ok, detail = _run_pip(spec)
            _log(base, "%s -> %s %s" % (spec, "OK" if ok else "FEL", detail))
            if not ok:
                state["failed"].append(name)
                state["ok"] = False
        state["i"] = total
        state["status"] = "Klart"
        state["done"] = True

    def tick():
        try:
            frac = 0
            if total:
                frac = int(100 * state["i"] / total)
            bar["value"] = frac
            status.config(text=state["status"])
            pct.config(text="%s %%" % frac)
        except Exception:
            pass
        if state["done"]:
            try:
                root.quit()
            except Exception:
                pass
            return
        try:
            root.after(80, tick)
        except Exception:
            pass

    threading.Thread(target=worker, daemon=True, name="DepInstall").start()
    tick()
    try:
        root.mainloop()
    except Exception:
        pass
    try:
        root.destroy()
    except Exception:
        pass

    if state["failed"]:
        try:
            messagebox.showerror(
                "Tillbehor",
                "Kunde inte installera:\n%s\n\n"
                "Kolla natet och starta appen igen."
                % "\n".join(state["failed"]),
            )
        except Exception:
            pass
    return state["ok"], state["failed"]


def ensure_requirements(base_dir=None):
    """Check/install/upgrade every declared package on every startup."""
    hide_console()
    base = Path(base_dir) if base_dir else Path(__file__).resolve().parent
    req = base / "requirements.txt"
    if not req.is_file():
        _log(base, "requirements.txt saknas – hoppar over")
        return True

    specs = _parse_requirements(req)
    # Ask pip's resolver for the newest stable compatible release on EVERY start.
    # Ignore historical pins: the user explicitly opts for rolling dependencies.
    jobs = [(name, None, "kontrollerar senaste stabila version") for name, ver in specs]
    if not _ensure_pip(base):
        from tkinter import messagebox
        messagebox.showerror("Python-tillägg", "pip saknas och kunde inte installeras.")
        return False
    ok, failed = _show_progress(base, jobs)
    import importlib
    importlib.invalidate_caches()
    return ok


if __name__ == "__main__":
    ensure_requirements()
