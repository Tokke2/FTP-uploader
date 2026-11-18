# Copyright (c) 2026 Rickard Längkvist
"""All new backups live inside the installed app; never fall back elsewhere."""
from pathlib import Path
import hashlib
import re
import uuid
from app_paths import app_dir


def backup_root(base=None):
    base = Path(base if base is not None else app_dir()).resolve()
    root = base / 'backups'
    root.mkdir(parents=True, exist_ok=True)
    if root.is_symlink() or not root.resolve().is_relative_to(base):
        raise ValueError('Backupmappen måste ligga inuti appmappen, utan extern länk.')
    return root.resolve()


def category_dir(category, base=None):
    if category not in ('releases', 'galleries', 'editor', 'config'):
        raise ValueError('Okänd backupkategori')
    root = backup_root(base)
    folder = root/category
    folder.mkdir(exist_ok=True)
    if folder.is_symlink() or not folder.resolve().is_relative_to(root):
        raise ValueError('Backupkategori pekar utanför appmappen')
    return folder.resolve()


def new_backup(category, name, base=None):
    safe = re.sub(r'[^\w.-]+','-',str(name))[:60].strip('.') or 'backup'
    return category_dir(category,base)/(safe+'-'+uuid.uuid4().hex)


def config_backup(path, suffix='.bak'):
    path = Path(path)
    key = hashlib.sha256(str(path.resolve()).encode()).hexdigest()[:20]
    return category_dir('config')/(path.name+'.'+key+suffix)


def move_directory_to_backup(source, destination):
    """Cross-volume-safe: finish the backup copy before removing old output."""
    import shutil
    source, destination = Path(source), Path(destination)
    if source.stat().st_dev == destination.parent.stat().st_dev:
        source.rename(destination)
        return
    shutil.copytree(source,destination)
    try:
        shutil.rmtree(source)
    except BaseException:
        # A permission failure may have removed only part of the old export.
        shutil.copytree(destination,source,dirs_exist_ok=True)
        raise


def restore_directory(backup, destination):
    import shutil
    backup, destination = Path(backup), Path(destination)
    if backup.stat().st_dev == destination.parent.stat().st_dev and not destination.exists():
        backup.rename(destination)
    else:
        shutil.copytree(backup,destination,dirs_exist_ok=True)
