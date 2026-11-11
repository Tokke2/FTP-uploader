# Copyright (c) 2026 Rickard Längkvist
"""Transactional error register: SQLite storage and one log export per batch."""
from contextlib import contextmanager
from datetime import datetime
import getpass
import hashlib
import json
from pathlib import Path
import re
import sqlite3
import threading

LOCK = threading.RLock()


def normalize(message):
    text = re.sub(r'^\[?\d{2}(?:\d{2}-\d{2}-\d{2}[ T])?[\d:.+TZ-]*\]?\s*', '', message)
    text = re.sub(r'^\[\s*(?:FEL|ERROR|CRITICAL|FATAL|VARNING|DEBUG|INFO)\s*\]\s*', '', text, flags=re.I)
    text = re.sub(r'^(?:FEL|ERROR|CRITICAL|FATAL|VARNING)\s*:\s*', '', text, flags=re.I)
    return ' '.join(text.split())


def app_version():
    try:
        from app_paths import app_dir
        text = (app_dir() / 'main.pyw').read_text(encoding='utf-8')
        return re.search(r'^APP_VERSION\s*=\s*["\']([^"\']+)', text, re.M)[1]
    except (OSError, TypeError):
        return 'unknown'


class ErrorRegister:
    def __init__(self, directory):
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        self.state_file = self.directory / 'error-register.sqlite3'
        self.log_file = self.directory / 'unresolved_errors.log'
        self._batch_connection = None
        self._dirty = False
        self._export_pending = False
        connection = self._connect()
        try:
            with LOCK:
                self._initialize(connection)
        finally:
            connection.close()

    def _initialize(self, connection):
        connection.execute('CREATE TABLE IF NOT EXISTS issues (id TEXT PRIMARY KEY, fingerprint TEXT UNIQUE, data TEXT NOT NULL)')
        self._migrate(connection)
        connection.commit()
        self._export(connection)

    def _connect(self):
        # Explicit closing is done by callers; Connection's own context only commits.
        return sqlite3.connect(self.state_file, timeout=10)

    def _migrate(self, connection):
        if connection.execute('SELECT 1 FROM issues LIMIT 1').fetchone():
            return
        legacy = self.directory / '.error-register.json'
        try:
            records = json.loads(legacy.read_text(encoding='utf-8'))
        except (OSError, ValueError):
            return
        if not isinstance(records, dict):
            return
        for entry in records.values():
            if not isinstance(entry, dict) or not entry.get('id'):
                continue
            message = entry.get('details', '').split('\n')[0]
            fingerprint = hashlib.sha256(normalize(message).encode()).hexdigest()
            entry.setdefault('sources', [entry.get('source', '')])
            entry.setdefault('history', [])
            if entry.get('resolved_at') and not entry['history']:
                entry['history'].append({'action': 'resolved', 'at': entry['resolved_at'],
                    'actor': 'unknown (legacy)', 'version': 'unknown',
                    'comment': 'Migrerat från äldre register; användare/version saknas.'})
            existing = connection.execute('SELECT id, data FROM issues WHERE fingerprint=?', (fingerprint,)).fetchone()
            if existing:
                identifier, raw = existing
                merged = json.loads(raw)
                merged['sources'] = list(dict.fromkeys(merged['sources'] + entry['sources']))
                merged['count'] += entry.get('count', 0)
                merged['history'].extend(entry['history'])
                if entry.get('status') == 'open':
                    merged['status'] = 'open'
                connection.execute('UPDATE issues SET data=? WHERE id=?', (json.dumps(merged, ensure_ascii=False), identifier))
            else:
                connection.execute('INSERT INTO issues VALUES (?, ?, ?)',
                                   (entry['id'], fingerprint, json.dumps(entry, ensure_ascii=False)))
        # Keep legacy JSON untouched as a migration backup.

    @contextmanager
    def batch(self):
        with LOCK:
            if self._batch_connection is not None:
                yield
                return
            connection = self._connect()
            self._batch_connection = connection
            self._dirty = False
            try:
                with connection:
                    yield
                if self._dirty or self._export_pending or not self.log_file.exists():
                    self._export_pending = True
                    self._export(connection)
                    self._export_pending = False
            finally:
                self._batch_connection = None
                connection.close()

    @contextmanager
    def _transaction(self):
        with LOCK:
            if self._batch_connection is not None:
                yield self._batch_connection
            else:
                with self.batch():
                    yield self._batch_connection

    def _put(self, connection, identifier, fingerprint, entry):
        self._dirty = True
        connection.execute('INSERT INTO issues VALUES (?, ?, ?) ON CONFLICT(id) DO UPDATE SET fingerprint=excluded.fingerprint, data=excluded.data',
                           (identifier, fingerprint, json.dumps(entry, ensure_ascii=False)))

    def _export(self, connection):
        text = ['AKTIVA FEL – ligger kvar tills de markeras som åtgärdade.\n']
        for (raw,) in connection.execute('SELECT data FROM issues ORDER BY id'):
            entry = json.loads(raw)
            if entry['status'] != 'open':
                continue
            text.append('\n%s | %s\nKällor: %s\nFörst: %s | Senast: %s | Antal loggträffar: %s\n%s\n' % (
                entry['id'], entry['code'], ', '.join(entry['sources']), entry['first_seen'],
                entry['last_seen'], entry['count'], entry['details']))
        temporary = self.log_file.with_suffix('.tmp')
        temporary.write_text(''.join(text), encoding='utf-8')
        temporary.replace(self.log_file)

    def observe(self, source, message):
        normalized = normalize(message)
        identity = str(source) + '\n' + normalized if normalized.startswith('Traceback (') else normalized
        fingerprint = hashlib.sha256(identity.encode()).hexdigest()
        identifier = 'ERR-' + fingerprint[:12].upper()
        code = re.search(r'\b(?:WinError\s+\d+|Errno\s+\d+|\w*(?:Error|Exception)|E\d{3,})\b', message)
        now = datetime.now().astimezone().isoformat(timespec='seconds')
        with self._transaction() as connection:
            row = connection.execute('SELECT id, data FROM issues WHERE fingerprint=?', (fingerprint,)).fetchone()
            if row:
                identifier, raw = row
                entry = json.loads(raw)
                if entry['status'] == 'resolved':
                    entry.setdefault('history', []).append({'action': 'reopened', 'at': now, 'version': app_version()})
            else:
                entry = {'id': identifier, 'first_seen': now, 'count': 0, 'sources': [], 'history': []}
            if str(source) not in entry['sources']:
                entry['sources'].append(str(source))
            entry.update(code=code[0] if code else entry.get('code', identifier), source=entry['sources'][0],
                         last_seen=now, status='open', details=message, count=entry['count'] + 1)
            self._put(connection, identifier, fingerprint, entry)
        return identifier

    def is_open(self, identifier):
        with LOCK:
            connection = self._batch_connection or self._connect()
            try:
                row = connection.execute('SELECT data FROM issues WHERE id=?', (identifier,)).fetchone()
                return bool(row and json.loads(row[0])['status'] == 'open')
            finally:
                if connection is not self._batch_connection:
                    connection.close()

    def detail(self, identifier, text):
        with self._transaction() as connection:
            row = connection.execute('SELECT fingerprint, data FROM issues WHERE id=?', (identifier,)).fetchone()
            if row:
                fingerprint, raw = row
                entry = json.loads(raw)
                if entry['status'] == 'open' and len(entry['details']) < 65536:
                    entry['details'] += '\n' + text
                    match = re.search(r'\b(?:WinError\s+\d+|Errno\s+\d+|\w*(?:Error|Exception)|E\d{3,})\b', text)
                    if match:
                        entry['code'] = match[0]
                    if normalize(entry['details'].split('\n')[0]).startswith('Traceback (') and re.match(r'^\w*(?:Error|Exception):', text):
                        canonical = hashlib.sha256(normalize(text).encode()).hexdigest()
                        new_id = 'ERR-' + canonical[:12].upper()
                        mirrored = connection.execute('SELECT id, data FROM issues WHERE fingerprint=?', (canonical,)).fetchone()
                        if mirrored and mirrored[0] != identifier:
                            new_id, raw = mirrored
                            previous = json.loads(raw)
                            entry['sources'] = list(dict.fromkeys(previous['sources'] + entry['sources']))
                            entry['count'] += previous['count']
                            entry['first_seen'] = min(previous['first_seen'], entry['first_seen'])
                            entry['history'] = previous.get('history', []) + entry.get('history', [])
                            if previous['status'] == 'resolved':
                                entry['history'].append({'action': 'reopened', 'at': entry['last_seen'], 'version': app_version()})
                        connection.execute('DELETE FROM issues WHERE id=?', (identifier,))
                        identifier, fingerprint = new_id, canonical
                        entry['id'] = identifier
                    self._put(connection, identifier, fingerprint, entry)
        return identifier

    def resolve(self, identifier, comment='', actor=None, version=None):
        with self._transaction() as connection:
            row = connection.execute('SELECT fingerprint, data FROM issues WHERE id=?', (identifier,)).fetchone()
            if not row:
                raise KeyError(identifier)
            fingerprint, raw = row
            entry = json.loads(raw)
            now = datetime.now().astimezone().isoformat(timespec='seconds')
            entry.update(status='resolved', resolved_at=now)
            entry.setdefault('history', []).append({'action': 'resolved', 'at': now,
                'actor': actor or getpass.getuser(), 'version': version or app_version(), 'comment': comment})
            self._put(connection, identifier, fingerprint, entry)

    def records(self, include_resolved=False):
        with LOCK:
            connection = self._batch_connection or self._connect()
            try:
                records = [json.loads(row[0]) for row in connection.execute('SELECT data FROM issues ORDER BY id')]
                return records if include_resolved else [e for e in records if e['status'] == 'open']
            finally:
                if connection is not self._batch_connection:
                    connection.close()

    def active(self):
        return self.records()
