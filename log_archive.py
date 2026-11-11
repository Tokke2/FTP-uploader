# Copyright (c) 2026 Rickard Längkvist
"""Date-based archival. Never truncate logs while their writers are running."""
from datetime import date, datetime, timedelta
import hashlib
from pathlib import Path
import re
import socket

PREPARED = False
RETENTION_DAYS = 14


def split_days(path):
    """Prefer record dates; time-only/undated records inherit file day."""
    match = re.search(r'(?:gallery_|errors_)(\d{8})', path.name)
    try:
        current = datetime.strptime(match[1], '%Y%m%d').date() if match else datetime.fromtimestamp(path.stat().st_mtime).date()
    except ValueError:
        current = datetime.fromtimestamp(path.stat().st_mtime).date()
    previous_time = None
    groups = {}
    for line in path.read_bytes().splitlines(keepends=True):
        text = line.decode('utf-8', errors='replace')
        stamp = re.match(r'^(?:\[|# Start:\s*)?(\d{4}-\d{2}-\d{2})(?:[ T])', text)
        clock = re.match(r'^\[(\d{2}:\d{2}:\d{2})', text)
        if stamp:
            try:
                current = date.fromisoformat(stamp[1])
                previous_time = text[stamp.end():stamp.end() + 8] if re.match(r'\d{2}:\d{2}:\d{2}', text[stamp.end():]) else None
            except ValueError:
                pass
        elif clock:
            if previous_time:
                def seconds(value):
                    hour, minute, second = map(int, value.split(':'))
                    return hour * 3600 + minute * 60 + second
                # Ignore small out-of-order timestamps from concurrent writers.
                if seconds(previous_time) - seconds(clock[1]) > 60:
                    current += timedelta(days=1)
            previous_time = clock[1]
        groups.setdefault(current, bytearray()).extend(line)
    return groups


def archive_logs(directory, today=None, compact=False):
    """Snapshot prior dates. Compact only before app writers have opened files.

    Content-addressed names make repeated snapshots idempotent. Snapshots may
    overlap while an old session continues writing; originals stay safe.
    """
    directory = Path(directory)
    today = today or date.today()
    if not directory.is_dir():
        return
    for path in directory.glob('*.log*'):
        if (not path.is_file() or path.is_symlink() or path.name == 'unresolved_errors.log'
                or not re.search(r'\.log(?:\.\d+)?$', path.name)):
            continue
        try:
            groups = split_days(path)
            old = {day: bytes(data) for day, data in groups.items() if day < today}
            for day, data in old.items():
                if day < today - timedelta(days=RETENTION_DAYS):
                    continue  # Expired ordinary logs are removed on safe compaction.
                folder = directory / 'archive' / day.isoformat()
                folder.mkdir(parents=True, exist_ok=True)
                target = folder / (path.name + '.' + hashlib.sha256(data).hexdigest()[:16] + '.log')
                if not target.exists() or target.read_bytes() != data:
                    temporary = target.with_suffix('.tmp')
                    temporary.write_bytes(data)
                    temporary.replace(target)
            if compact and old:
                remaining = b''.join(bytes(data) for day, data in groups.items() if day >= today)
                if remaining:
                    temporary = path.with_name(path.name + '.archive-tmp')
                    temporary.write_bytes(remaining)
                    temporary.replace(path)
                else:
                    path.unlink()
        except OSError:
            continue  # An unreadable/locked source is never removed.

    prune_archives(directory, today)


def prune_archives(directory, today=None):
    """Delete ordinary archives strictly older than 14 calendar days; no symlinks."""
    today = today or date.today()
    cutoff = today - timedelta(days=RETENTION_DAYS)
    archive = Path(directory) / 'archive'
    if not archive.is_dir() or archive.is_symlink():
        return
    for folder in archive.iterdir():
        if folder.is_symlink() or not folder.is_dir():
            continue
        try:
            day = date.fromisoformat(folder.name)
        except ValueError:
            continue
        if day >= cutoff:
            continue
        # Never follow links or remove unrelated files placed in an archive.
        for file in folder.iterdir():
            if file.is_symlink() or not file.is_file() or not file.name.endswith('.log'):
                continue
            try:
                file.unlink()
            except OSError:
                pass
        try:
            folder.rmdir()
        except OSError:
            pass


def prepare_logs():
    """Import errors first, then archive old records before app files open."""
    global PREPARED
    if PREPARED:
        return
    guard = None
    from single_instance import owns_instance
    if not owns_instance():
        guard = socket.socket()
        try:
            guard.bind(('127.0.0.1', 47200))
            guard.listen(1)
        except OSError:
            guard.close()
            return  # Another instance may still have log files open.
    try:
        from app_paths import logs_dir
        from error_summary import ErrorSummary
        directory = logs_dir()
        collector = ErrorSummary()
        try:
            # Drain historical files (collector reads bounded chunks per pass).
            while True:
                before = {key: cursor.get('offset') for key, cursor in collector.state.items()}
                collector.collect()
                after = {key: cursor.get('offset') for key, cursor in collector.state.items()}
                if before == after:
                    break
        finally:
            collector.close()
        archive_logs(directory, compact=True)
        # Compaction rewrites files. Do not treat retained current-day errors as
        # new occurrences on the next collector pass.
        import json
        state_file = directory / '.all_errors-cursors.json'
        retained = {}
        for path in directory.glob('*.log'):
            if path.name in ('all_errors.log', 'unresolved_errors.log'):
                continue
            stat = path.stat()
            with path.open('rb') as source:
                sample = source.read(128)
            retained[str(path.resolve())] = {'offset': stat.st_size, 'inode': stat.st_ino,
                'sample_size': len(sample), 'sample': hashlib.sha256(sample).hexdigest(),
                'active': False, 'pending': ''}
        state_file.write_text(json.dumps(retained), encoding='utf-8')
        PREPARED = True
    finally:
        if guard is not None:
            guard.close()
