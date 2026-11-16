# Copyright (c) 2026 Rickard Längkvist
"""Incrementally collect errors from existing logs without changing their writers."""
import atexit
import hashlib
import json
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
import re
import threading
from datetime import datetime

from app_paths import logs_dir

ERROR = re.compile(
    r'\b(?:FEL|ERROR|CRITICAL|FATAL|KRASCH)\b|Traceback \(most recent call last\)'
    r'|\b\w*(?:Error|Exception):|misslyck|kunde inte|failed|failure|timeout|\[!\]', re.I)
RECORD = re.compile(r'^\[?\d{2}(?:\d{2}-\d{2}-\d{2}[ T])?[:\d.-]*\s|^\[\d{2}:')


def is_error_line(line):
    """Classify events, not incidental words in successful status summaries."""
    if re.search(r'\bfel:\s*(?:inga|0)\s*$', line, re.I):
        return False
    if re.search(r'\bSkrivna rader:\s*\d+\s*\(varav fel \d+\)', line, re.I):
        return False
    return bool(ERROR.search(line))


def summary_path():
    return logs_dir() / 'all_errors.log'


class ErrorSummary:
    def __init__(self, roots=None, destination=None, max_bytes=5 * 1024 * 1024, backups=3):
        self.destination = Path(destination) if destination else summary_path()
        self.destination.parent.mkdir(parents=True, exist_ok=True)
        self.roots = list(dict.fromkeys(Path(p).resolve() for p in (roots or (
            logs_dir(),))))
        from unresolved_errors import ErrorRegister
        self.register = ErrorRegister(self.destination.parent)
        self.archive_day = datetime.now().date()
        self.state_path = self.destination.with_name('.all_errors-cursors.json')
        try:
            self.state = json.loads(self.state_path.read_text(encoding='utf-8'))
            if not isinstance(self.state, dict):
                self.state = {}
        except (OSError, ValueError):
            self.state = {}
        self.handler = RotatingFileHandler(self.destination, maxBytes=max_bytes,
                                           backupCount=backups, encoding='utf-8')
        self.handler.setFormatter(logging.Formatter('%(message)s'))
        self.lock = threading.RLock()
        self.stopping = threading.Event()
        self.thread = None
        self.closed = False

    def _write(self, path, line):
        text = '%s | %s | %s' % (datetime.now().astimezone().isoformat(timespec='seconds'), path, line)
        # Call handle so logging's lock protects rotation and append as one operation.
        self.handler.handle(logging.LogRecord('error-summary', logging.ERROR, '', 0, text, (), None))

    def _read(self, path):
        key = str(path.resolve())
        previous = self.state.get(key, {})
        if not isinstance(previous, dict):
            previous = {}
        stat = path.stat()
        with path.open('rb') as source:
            sample_size = previous.get('sample_size', min(stat.st_size, 128))
            sample = source.read(sample_size)
            signature = hashlib.sha256(sample).hexdigest()
            reset = (stat.st_size < previous.get('offset', 0)
                     or stat.st_ino != previous.get('inode', stat.st_ino)
                     or previous.get('sample', signature) != signature)
            cursor = {} if reset else previous
            offset = cursor.get('offset', 0)
            source.seek(offset)
            # Bounded work per poll; large historical logs drain over several polls.
            data = source.read(1024 * 1024)
            if not data:
                return
            dedicated = path.name.lower().startswith(('errors_', 'crash_', 'launcher', 'stderr'))
            active = cursor.get('active', False)
            issue = cursor.get('issue')
            pending = bytes.fromhex(cursor.get('pending', '')) + data
            lines = pending.split(b'\n')
            remainder = lines.pop()
            for raw in lines:
                line = raw.decode('utf-8', errors='replace').rstrip('\r')
                new_record = bool(RECORD.match(line))
                if new_record:
                    active = False
                    issue = None
                if is_error_line(line) or dedicated:
                    active = True
                if active and line:
                    self._write(path, line)
                    if is_error_line(line) and (issue is None or not self.register.is_open(issue) or new_record or re.match(r'^(?:FEL|ERROR|CRITICAL|FATAL)\b', line)):
                        issue = self.register.observe(path, line)
                    elif issue:
                        issue = self.register.detail(issue, line) or issue
            # Preserve incomplete lines and tracebacks across reads and restarts.
            # A pathological unterminated line must not grow memory indefinitely.
            if len(remainder) > 256 * 1024:
                line = remainder.decode('utf-8', errors='replace')
                if active or is_error_line(line) or dedicated:
                    self._write(path, line)
                remainder = b''
            source.seek(0)
            sample_size = min(stat.st_size, 128)
            sample = source.read(sample_size)
            self.state[key] = {'offset': offset + len(data), 'inode': stat.st_ino,
                               'sample_size': sample_size, 'sample': hashlib.sha256(sample).hexdigest(),
                               'active': active, 'issue': issue, 'pending': remainder.hex()}

    def collect(self):
        """Commit error data before checkpointing source offsets."""
        import copy
        with self.lock:
            previous = copy.deepcopy(self.state)
            try:
                with self.register.batch():
                    seen = set()
                    for root in self.roots:
                        if not root.is_dir():
                            continue
                        for path in root.rglob('*.log'):
                            if 'archive' in path.relative_to(root).parts or path.name == 'unresolved_errors.log':
                                continue
                            if path.is_symlink() or path.name.startswith('all_errors') or path.resolve() == self.destination.resolve():
                                continue
                            key = str(path.resolve())
                            seen.add(key)
                            try:
                                self._read(path)
                            except (OSError, ValueError, TypeError):
                                continue
                    self.state = {key: value for key, value in self.state.items() if key in seen}
            except Exception:
                self.state = previous
                raise
            try:
                temporary = self.state_path.with_suffix('.tmp')
                temporary.write_text(json.dumps(self.state), encoding='utf-8')
                temporary.replace(self.state_path)
            except OSError:
                pass

    def start(self):
        if self.thread is not None:
            return self

        def worker():
            while not self.stopping.is_set():
                try:
                    self.collect()
                    today = datetime.now().date()
                    if today != self.archive_day:
                        from log_archive import archive_logs
                        archive_logs(self.destination.parent, today=today)
                        self.archive_day = today
                except Exception:
                    pass  # Collector failure must not recurse through app logging.
                self.stopping.wait(2)

        self.thread = threading.Thread(target=worker, daemon=True, name='ErrorSummary')
        self.thread.start()
        atexit.register(self.close)
        return self

    def close(self):
        if self.closed:
            return
        self.stopping.set()
        if self.thread and self.thread is not threading.current_thread():
            self.thread.join(timeout=5)
        with self.lock:
            self.collect()
            # Flush an unterminated final error/traceback line on clean shutdown.
            with self.register.batch():
                for key, cursor in self.state.items():
                    pending = bytes.fromhex(cursor.get('pending', ''))
                    if pending:
                        text = pending.decode('utf-8', errors='replace')
                        if cursor.get('active') or ERROR.search(text) or Path(key).name.startswith(('crash_', 'launcher', 'stderr', 'errors_')):
                            self._write(Path(key), text)
                            if cursor.get('issue'):
                                self.register.detail(cursor['issue'], text)
                            elif ERROR.search(text):
                                self.register.observe(Path(key), text)
                            cursor['pending'] = ''
            try:
                temporary = self.state_path.with_suffix('.tmp')
                temporary.write_text(json.dumps(self.state), encoding='utf-8')
                temporary.replace(self.state_path)
            except OSError:
                pass
            self.handler.flush()
            self.handler.close()
            self.closed = True
