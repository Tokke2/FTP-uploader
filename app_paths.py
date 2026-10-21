"""Per-user writable data, independent of the source checkout."""
import json
import os
from pathlib import Path
import shutil
import sys


def data_dir():
    if sys.platform == 'win32':
        root = Path(os.environ.get('APPDATA', str(Path.home() / 'AppData/Roaming')))
    elif sys.platform == 'darwin':
        root = Path.home() / 'Library/Application Support'
    else:
        root = Path(os.environ.get('XDG_CONFIG_HOME', str(Path.home() / '.config')))
    path = root / 'FTP-uploader'
    path.mkdir(parents=True, exist_ok=True)
    return path


def config_dir():
    path = data_dir() / 'config'
    path.mkdir(exist_ok=True)
    # One-time migration: copy, never remove or overwrite existing user settings.
    marker = path / '.migrated'
    if not marker.exists():
        legacy = Path(__file__).resolve().parent / 'config'
        if legacy.is_dir():
            for source in legacy.glob('*.json'):
                target = path / source.name
                if not target.exists():
                    shutil.copy2(source, target)
        marker.touch()
    return path


def logs_dir():
    path = data_dir() / 'logs'
    path.mkdir(exist_ok=True)
    return path


def update_settings():
    try:
        value = json.loads((config_dir() / 'updates.json').read_text(encoding='utf-8'))
        if value.get('mode') in ('auto', 'ask', 'off'):
            return value
    except (OSError, ValueError, AttributeError):
        pass
    return {'mode': 'ask'}


def save_update_settings(value):
    path = config_dir() / 'updates.json'
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(value, indent=2), encoding='utf-8')
    temporary.replace(path)
