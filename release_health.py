# Copyright (c) 2026 Rickard Längkvist
"""Post-install startup acknowledgement and exact managed-file rollback."""
import json
import os
from pathlib import Path
import shutil
import tempfile
import time
import uuid


def write_receipt(base, backup, changed, commit):
    path = Path(base) / '.release-rollback.json'
    incoming = path.with_suffix('.tmp')
    incoming.write_text(json.dumps({'backup': str(backup), 'changed': [(str(p), existed) for p,existed in changed], 'commit': commit}),encoding='utf-8')
    incoming.replace(path)


def acknowledge(base):
    filename, nonce = os.environ.get('FTP_UPDATE_HEALTH_FILE'), os.environ.get('FTP_UPDATE_HEALTH_NONCE')
    if not filename or not nonce: return
    state = json.loads((Path(base)/'.release-state.json').read_text(encoding='utf-8'))
    if state.get('commit') != os.environ.get('FTP_UPDATE_HEALTH_COMMIT'):
        raise RuntimeError('Hälsokontrollens commit stämmer inte')
    path = Path(filename)
    incoming = path.with_suffix('.tmp')
    incoming.write_text(json.dumps({'nonce':nonce,'commit':state['commit']}),encoding='utf-8')
    incoming.replace(path)


def rollback(base, commit):
    from auto_update import managed_file
    base = Path(base).resolve()
    receipt = json.loads((base/'.release-rollback.json').read_text(encoding='utf-8'))
    if receipt.get('commit') != commit: raise ValueError('Fel rollback-commit')
    backup = Path(receipt['backup']).resolve()
    from backup_storage import category_dir
    expected = category_dir('releases',base)
    if backup.parent != expected or not backup.is_dir():
        raise ValueError('Ogiltig backupmapp')
    records = []
    for relative, existed in receipt['changed']:
        relative = Path(relative)
        if relative.is_absolute() or '..' in relative.parts or not (managed_file(relative) or str(relative)=='.release-state.json'):
            raise ValueError('Ogiltig återställningsfil')
        target, saved = base/relative, backup/relative
        if not target.resolve().is_relative_to(base) or not saved.resolve().is_relative_to(backup):
            raise ValueError('Återställningsfil utanför mappen')
        if existed and not saved.is_file(): raise ValueError('Backupfil saknas')
        records.append((target,saved,existed))
    for target,saved,existed in reversed(records):
        if existed:
            incoming = target.with_name(target.name+'.rollback-tmp')
            shutil.copy2(saved,incoming)
            incoming.replace(target)
        else: target.unlink(missing_ok=True)


def launch_checked(base, commit, spawn, executable, timeout=180):
    """Only terminate the exact child we started, before restoring its code."""
    with tempfile.TemporaryDirectory(prefix='ftp-update-health-') as directory:
        acknowledgement = Path(directory)/'ready.json'
        nonce = uuid.uuid4().hex
        env = dict(os.environ, FTP_UPLOADER_SILENT_RESTART='1', FTP_UPLOADER_AUTOUPDATE='0',
                   FTP_UPDATE_HEALTH_FILE=str(acknowledgement),FTP_UPDATE_HEALTH_NONCE=nonce,FTP_UPDATE_HEALTH_COMMIT=commit)
        child = spawn([executable,str(Path(base)/'start.pyw')],env=env)
        deadline = time.monotonic()+timeout
        while time.monotonic()<deadline:
            try:
                ready = json.loads(acknowledgement.read_text())
                if ready == {'nonce':nonce,'commit':commit} and child.poll() is None: return True
            except (ValueError,OSError): pass
            if child.poll() is not None: break
            time.sleep(0.25)
        if child.poll() is None:
            child.terminate()
            try: child.wait(timeout=10)
            except Exception:
                child.kill()
                child.wait(timeout=10)
        # Do not replace files if another app won the startup race.
        import socket
        with socket.socket() as guard:
            try:
                guard.bind(('127.0.0.1',47200))
                guard.listen(1)
            except OSError as exc:
                raise RuntimeError('Återställning stoppad: en appinstans körs. Backup behålls.') from exc
            rollback(base,commit)
        environment = dict(os.environ,FTP_UPLOADER_SILENT_RESTART='1',FTP_UPLOADER_AUTOUPDATE='0')
        for key in ('FTP_UPDATE_HEALTH_FILE','FTP_UPDATE_HEALTH_NONCE','FTP_UPDATE_HEALTH_COMMIT'): environment.pop(key,None)
        spawn([executable,str(Path(base)/'start.pyw')],env=environment)
        return False
