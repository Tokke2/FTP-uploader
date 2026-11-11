# Copyright (c) 2026 Rickard Längkvist
"""Standard-library-only diagnostics installed before Tk, dependencies and discovery."""
import atexit
from datetime import datetime
import faulthandler
import os
from pathlib import Path
import sys
import traceback

_base = None
_phase = 'inte startad'
_streams = []


def phase(name, detail=''):
    global _phase
    _phase = name
    from event_log import emit, redact
    detail = redact(detail)
    emit('startup.phase', name=name, detail=detail)
    if _base is None:
        return
    try:
        directory = _base / 'logs'
        directory.mkdir(exist_ok=True)
        with (directory / 'startup-early.log').open('a', encoding='utf-8') as stream:
            stream.write('[%s] pid=%d %s | %s\n' % (
                datetime.now().isoformat(sep=' ', timespec='milliseconds'), os.getpid(), name, detail))
    except OSError:
        pass


def report(exc_type, value, tb, popup=True):
    previous = _phase
    from event_log import exception, redact
    exception('startup.exception', exc_type, value, tb, phase=previous)
    phase('STARTFEL', '%s: %s; föregående steg=%s' % (exc_type.__name__, value, previous))
    path = (_base or Path(__file__).resolve().parent) / 'logs/startup-crash.log'
    try:
        path.parent.mkdir(exist_ok=True)
        with path.open('a', encoding='utf-8') as stream:
            stream.write('\n[%s] pid=%d Python=%s mapp=%s steg=%s\n%s' % (
                datetime.now().isoformat(sep=' ', timespec='seconds'), os.getpid(), sys.executable,
                _base, previous, redact(''.join(traceback.format_exception(exc_type, value, tb)))))
    except OSError:
        pass
    if popup and sys.platform == 'win32':
        try:
            import ctypes
            ctypes.windll.user32.MessageBoxW(None,
                '%s: %s\n\nSteg: %s\nLogg: %s' % (exc_type.__name__, value, previous, path),
                'FTP-uploader – startfel', 0x10)
        except Exception:
            pass


def install(base):
    global _base
    if _base is not None:
        return
    _base = Path(base).resolve()
    phase('Process startad', 'Python=%s version=%s mapp=%s' % (sys.executable, sys.version.split()[0], _base))
    sys.excepthook = report
    try:
        directory = _base / 'logs'
        directory.mkdir(exist_ok=True)
        suffix = datetime.now().strftime('%Y%m%d') + '_%d.log' % os.getpid()
        # Pythonw has no console streams. Preserve real terminals for developers.
        if sys.stderr is None:
            stderr = (directory / ('early_stderr_' + suffix)).open('a', encoding='utf-8', buffering=1)
            _streams.append(stderr)
            sys.stderr = stderr
        if sys.stdout is None:
            sys.stdout = sys.stderr
        fault = (directory / ('native_fault_' + suffix)).open('a', encoding='utf-8', buffering=1)
        _streams.append(fault)
        faulthandler.enable(file=fault, all_threads=True)
    except (OSError, RuntimeError):
        pass
    from event_log import install as install_events
    install_events(_base)
    def exiting():
        phase('Process avslutas', 'Sista steg framgår ovan. Avslut kan vara normal vidarestart eller stängning.')
    atexit.register(exiting)
