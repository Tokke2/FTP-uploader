# Copyright (c) 2026 Rickard Längkvist
"""Bounded application telemetry. No keystrokes, environment dumps or external monitoring."""
import contextvars
from datetime import datetime
import json
import logging
import os
from pathlib import Path
import re
import sys
import threading
import time
import traceback
import uuid
import warnings

SESSION = uuid.uuid4().hex[:16]
JOB = contextvars.ContextVar('gallery_log_job', default=None)
_directory = None
_lock = threading.RLock()
_local = threading.local()
_installed = False
MAX_BYTES = 10 * 1024 * 1024


def redact(value, key='', depth=0):
    if re.search(r'password|passwd|secret|token|authorization|credential|api[_-]?key|ftp_pass', key, re.I):
        return '[MASKERAT]'
    if depth > 6:
        return '[MAXDJUP]'
    if isinstance(value, dict):
        return {str(k): redact(v, str(k), depth + 1) for k, v in list(value.items())[:50]}
    if isinstance(value, (list, tuple)):
        return [redact(v, depth=depth + 1) for v in value[:50]]
    if value is None or isinstance(value, (bool, int, float)):
        return value
    if not isinstance(value, (str, Path)):
        return '<%s>' % type(value).__name__
    text = str(value)
    text = re.sub(r'(https?://|ftps?://)[^\s/@]+:[^\s/@]+@', r'\1[MASKERAT]@', text, flags=re.I)
    text = re.sub(r'(?i)(\b(?:password|passwd|secret|token|authorization|api[_-]?key)\b[\s\"\x27]*[:=][\s]*)(?:\"[^\"]*\"|\x27[^\x27]*\x27|[^\s&,;]+)', r'\1[MASKERAT]', text)
    text = re.sub(r'(?i)\bBearer\s+[A-Za-z0-9._~+/=-]+', 'Bearer [MASKERAT]', text)
    return text[:32768]


def emit(event, level='INFO', **details):
    if _directory is None or getattr(_local, 'writing', False):
        return
    _local.writing = True
    try:
        now = datetime.now().astimezone()
        data = {'time': now.isoformat(timespec='milliseconds'), 'session': SESSION, 'pid': os.getpid(),
                'thread': threading.current_thread().name, 'job': JOB.get(), 'level': level,
                'event': event, 'details': redact(details)}
        line = '[%s] [%s] %s\n' % (now.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3], level,
                                           json.dumps(data, ensure_ascii=False))
        with _lock:
            _directory.mkdir(exist_ok=True)
            path = _directory / ('events_%s.log' % now.strftime('%Y%m%d'))
            if path.exists() and path.stat().st_size >= MAX_BYTES:
                # Preserve today's segments; 14-day date retention handles old ones.
                index = 1
                while path.with_name(path.name + '.%d' % index).exists():
                    index += 1
                path.rename(path.with_name(path.name + '.%d' % index))
            with path.open('a', encoding='utf-8') as stream:
                stream.write(line)
    except (OSError, ValueError, TypeError):
        pass  # Never recurse or interrupt an operation because telemetry failed.
    finally:
        _local.writing = False


def exception(event, exc_type, value, tb, **details):
    emit(event, 'ERROR', error_type=exc_type.__name__, message=str(value),
         traceback=''.join(traceback.format_exception(exc_type, value, tb)), **details)


class ForwardLogging(logging.Handler):
    def emit(self, record):
        try:
            details = {'logger': record.name, 'message': record.getMessage()}
            if record.exc_info:
                details['traceback'] = ''.join(traceback.format_exception(*record.exc_info))
            emit('python.logging', record.levelname, **details)
        except Exception:
            pass


class CapturedStream:
    def __init__(self, original, name):
        self.original, self.name = original, name
        self.local = threading.local()
    def _forward(self, text):
        if self.original is not None:
            self.original.write(redact(text))
    def write(self, text):
        text = str(text)
        pending = getattr(self.local, 'pending', '') + text
        lines = pending.split('\n')
        self.local.pending = lines.pop()
        for line in lines:
            if line.strip():
                emit(self.name, 'ERROR' if self.name == 'stderr' else 'INFO', message=line)
            self._forward(line + '\n')
        if len(self.local.pending) > 8192:
            emit(self.name, 'ERROR' if self.name == 'stderr' else 'INFO', message=self.local.pending)
            self._forward(self.local.pending)
            self.local.pending = ''
        return len(text)
    def flush(self):
        pending = getattr(self.local, 'pending', '')
        if pending:
            self.local.pending = ''
            emit(self.name, 'ERROR' if self.name == 'stderr' else 'INFO', message=pending)
            self._forward(pending)
        if self.original is not None:
            self.original.flush()
    def __getattr__(self, name):
        return getattr(self.original, name)


def install(base):
    global _directory, _installed
    if _installed:
        return
    _directory = Path(base).resolve() / 'logs'
    _installed = True
    logging.getLogger().addHandler(ForwardLogging())
    previous_warning = warnings.showwarning
    def warning(message, category, filename, lineno, file=None, line=None):
        emit('python.warning', 'WARNING', message=str(message), category=category.__name__, file=filename, line=lineno)
        previous_warning(message, category, filename, lineno, file, line)
    warnings.showwarning = warning
    previous_thread = threading.excepthook
    def thread_error(args):
        if args.exc_type is not SystemExit:
            exception('thread.exception', args.exc_type, args.exc_value, args.exc_traceback,
                      failed_thread=getattr(args.thread, 'name', '?'))
        previous_thread(args)
    threading.excepthook = thread_error
    previous_unraisable = sys.unraisablehook
    def unraisable(args):
        if args.exc_type is not None:
            exception('python.unraisable', args.exc_type, args.exc_value, args.exc_traceback,
                      context=args.err_msg, object_type=type(args.object).__name__)
        else:
            emit('python.unraisable', 'ERROR', context=args.err_msg, object_type=type(args.object).__name__)
        previous_unraisable(args)
    sys.unraisablehook = unraisable
    sys.stdout = CapturedStream(sys.stdout, 'stdout')
    sys.stderr = CapturedStream(sys.stderr, 'stderr')
    emit('session.start', python=sys.executable, version=sys.version.split()[0], base=base)
    def audit(event, args):
        # Do NOT capture command arguments, environments, file contents or FTP
        # protocol commands (PASS can contain plaintext credentials).
        if event == 'subprocess.Popen':
            emit('process.spawn', executable=args[0] if args else None)
        elif event == 'socket.connect':
            emit('network.connect.attempt', address=args[1] if len(args) > 1 else None)
    sys.addaudithook(audit)
    import atexit
    def finish():
        for stream in (sys.stdout, sys.stderr):
            try:
                stream.flush()
            except Exception:
                pass
        emit('session.exit')
    atexit.register(finish)


def attach_ui(app):
    """Report stalled UI without calling Tk from the watchdog thread."""
    beat = {'last': time.monotonic(), 'stalled': False, 'report': 0}
    stop = threading.Event()
    def pulse():
        beat['last'] = time.monotonic()
        if beat['stalled']:
            beat['stalled'] = False
            emit('ui.responsive', message='Gränssnittet svarar igen.')
        if time.monotonic() - beat['report'] >= 60:
            beat['report'] = time.monotonic()
            emit('ui.heartbeat', state=app.state(), active_jobs=getattr(app, '_pipeline_busy', 0),
                 threads=threading.active_count())
        app.after(1000, pulse)
    def watch():
        while not stop.wait(5):
            delay = time.monotonic() - beat['last']
            if delay > 15 and not beat['stalled']:
                beat['stalled'] = True
                frame = sys._current_frames().get(threading.main_thread().ident)
                stack = ''.join(traceback.format_stack(frame)) if frame is not None else ''
                del frame
                emit('ui.unresponsive', 'WARNING', seconds=round(delay), main_thread_stack=stack,
                     message='UI-puls försenad. Kan vara ett långt jobb eller en modal/systemdialog; inte bevis för krasch.')
    def destroy(event):
        if event.widget is app:
            stop.set()
            emit('ui.destroy')
    app.bind('<Destroy>', destroy, add='+')
    def window_event(event):
        if event.widget is app:
            emit('window.event', type=str(event.type))
    for sequence in ('<Map>', '<Unmap>', '<FocusIn>', '<FocusOut>'):
        app.bind(sequence, window_event, add='+')
    def clicked(event):
        try:
            emit('ui.click', widget_class=event.widget.winfo_class())
        except Exception:
            pass
    app.bind_all('<ButtonRelease-1>', clicked, add='+')
    app.after(1000, pulse)
    threading.Thread(target=watch, name='UI-health-log', daemon=True).start()


def install_dialog_capture():
    from tkinter import messagebox
    original = messagebox._show
    if getattr(original, '_gallery_logged', False):
        return
    def show(*args, **kwargs):
        title = args[0] if args else kwargs.get('title')
        message = args[1] if len(args) > 1 else kwargs.get('message')
        icon = args[2] if len(args) > 2 else kwargs.get('_icon')
        level = 'ERROR' if icon == 'error' else 'WARNING' if icon == 'warning' else 'INFO'
        emit('ui.messagebox', level, title=title, message=message)
        try:
            result = original(*args, **kwargs)
            emit('ui.messagebox.closed', result=result)
            return result
        except Exception as exc:
            exception('ui.messagebox.failed', type(exc), exc, exc.__traceback__)
            raise
    show._gallery_logged = True
    messagebox._show = show
