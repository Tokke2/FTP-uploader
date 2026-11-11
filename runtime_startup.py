# Copyright (c) 2026 Rickard Längkvist
"""Scheduled maintenance of the existing Python; never create a virtualenv."""
import os
from pathlib import Path
import queue
import socket
import sys
import threading

from app_paths import logs_dir
from log_clock import timestamp
from python_runtime import inspect_runtime, execute_upgrade

SKIP_ONCE = 'FTP_UPLOADER_SKIP_RUNTIME_ONCE'


def log(message):
    try:
        with (logs_dir() / 'python-runtime.log').open('a', encoding='utf-8') as output:
            output.write('[%s] %s\n' % (timestamp(), message))
    except OSError:
        pass


def maintain_runtime():
    """Return True only if a verified upgrade needs a new interpreter process."""
    if os.environ.pop(SKIP_ONCE, None) == '1':
        log('Verifierad Python-uppgradering: fortsätter efter omstart utan en uppgraderingsloop.')
        return False
    with socket.socket() as guard:
        try:
            guard.bind(('127.0.0.1', 47200))
            guard.listen(1)
        except OSError:
            log('Python-kontroll uppskjuten: en appinstans körs redan.')
            return False
        try:
            plan = inspect_runtime()
            log('Startkontroll: installerad %s, senaste %s. %s' % (plan.installed, plan.latest, plan.reason))
            if plan.command:
                log(execute_upgrade(plan))
                return True
        except Exception as exc:
            log('FEL vid kontroll/uppgradering av Python: %s. Befintlig Python används.' % exc)
    return False


def check_on_start():
    """Keep normal startup responsive; automatic update restarts stay quiet."""
    if os.environ.get('FTP_UPLOADER_SILENT_RESTART') == '1' or os.environ.get(SKIP_ONCE) == '1':
        return maintain_runtime()
    import tkinter as tk
    root = tk.Tk()
    root.title('FTP-uploader – Python-kontroll')
    root.resizable(False, False)
    tk.Label(root, text='Kontrollerar befintlig Python och senaste stabila version …\n'
             'En tillgänglig uppgradering kan kräva administratörsgodkännande.',
             padx=24, pady=20).pack()
    try:
        from app_icon import apply_tk_window_icon
        apply_tk_window_icon(root)
    except Exception:
        pass
    root.protocol('WM_DELETE_WINDOW', lambda: None)
    results = queue.Queue()
    outcome = [False]

    def worker():
        try:
            results.put(maintain_runtime())
        except Exception as exc:
            log('FEL i Python-startkontrollen: %s' % exc)
            results.put(False)

    def poll():
        try:
            outcome[0] = results.get_nowait()
        except queue.Empty:
            root.after(100, poll)
            return
        root.destroy()

    threading.Thread(target=worker, daemon=True, name='PythonRuntimeStartup').start()
    root.after(100, poll)
    root.mainloop()
    return outcome[0]


def restart_with_updated_python(base):
    from release_scheduler import python_executable, spawn
    environment = dict(os.environ, **{SKIP_ONCE: '1'})
    spawn([python_executable(), str(Path(base) / 'start.pyw'), *sys.argv[1:]], env=environment)
    raise SystemExit(0)
