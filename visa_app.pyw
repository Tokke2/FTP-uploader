#!/usr/bin/env python3
# Copyright (c) 2026 Rickard Längkvist
"""Explicitly show the app, including legacy installations that use a trigger file.

Place beside main.pyw. Uses only Python's standard library; never installs packages.
"""
from datetime import datetime
from pathlib import Path
import socket
import subprocess
import sys

BASE = Path(__file__).resolve().parent


def log(message):
    directory = BASE / 'logs'
    directory.mkdir(exist_ok=True)
    with (directory / 'show-app.log').open('a', encoding='utf-8') as stream:
        stream.write('[%s] %s\n' % (datetime.now().isoformat(sep=' ', timespec='seconds'), message))


def show_existing():
    try:
        connection = socket.create_connection(('127.0.0.1', 47200), timeout=2)
    except ConnectionRefusedError:
        return False
    with connection:
        connection.settimeout(2)
        connection.sendall(b'FTP-UPLOADER/1 SHOW\n')
        try:
            response = b''
            while len(response) < 128 and not response.endswith(b'\n'):
                part = connection.recv(1)
                if not part:
                    break
                response += part
            if response.startswith(b'FTP-UPLOADER/1 OK '):
                pid = int(response.split()[-1])
                if sys.platform == 'win32':
                    import ctypes
                    ctypes.windll.user32.AllowSetForegroundWindow(pid)
                connection.sendall(b'ACK\n')
                log('Aktivering skickad till befintlig instans, pid %d.' % pid)
                return True
        except socket.timeout:
            pass
    # Old versions listen without reading sockets; their UI polls this file.
    (BASE / 'instance_show.trigger').write_text('show', encoding='utf-8')
    log('Äldre instans: visa-trigger skapad i %s.' % BASE)
    return True


def main():
    log('Visa begärt. Programmapp: %s. Python: %s.' % (BASE, sys.executable))
    if not show_existing():
        entry = BASE / 'start.pyw'
        if not entry.is_file():
            entry = BASE / 'main.pyw'
        if not entry.is_file():
            raise FileNotFoundError('Lägg visa_app.pyw i samma mapp som main.pyw.')
        (BASE / 'instance_show.trigger').write_text('show', encoding='utf-8')
        subprocess.Popen([sys.executable, str(entry), '--show'], cwd=BASE)
        log('Ingen instans svarade; startad med uttryckligt --show.')


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        try:
            log('FEL: %s: %s' % (type(exc).__name__, exc))
        except OSError:
            pass
        import tkinter as tk
        from tkinter import messagebox
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror('Visa FTP-Galleri', str(exc), parent=root)
        root.destroy()
