# Copyright (c) 2026 Rickard Längkvist
"""One icon-bearing Startup shortcut shared by both autostart controls."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

from app_paths import config_dir

KEY = r'Software\Microsoft\Windows\CurrentVersion\Run'
NAME = 'GalleryUploader'


def startup_link():
    return (Path(os.environ.get('APPDATA', str(Path.home() / 'AppData/Roaming'))) /
            'Microsoft/Windows/Start Menu/Programs/Startup/FTP-uploader.lnk')


def launch_parts():
    base = Path(__file__).resolve().parent
    executable = Path(sys.executable)
    if getattr(sys, 'frozen', False):
        return executable, ['--autostart'], executable.parent
    from python_discovery import find_python
    quiet = find_python()
    return quiet, [str(base / 'start.pyw'), '--autostart'], base


def command():
    if sys.platform != 'win32':
        return ''
    try:
        executable, arguments, base = launch_parts()
        return subprocess.list2cmdline([str(executable), *arguments])
    except OSError:
        return ''


def fingerprint():
    _, _, base = launch_parts()
    icon = base / 'icon/icon.ico'
    return {'command': command(), 'icon': str(icon),
            'icon_hash': hashlib.sha256(icon.read_bytes()).hexdigest()}


def legacy_value():
    import winreg
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, KEY) as key:
            return winreg.QueryValueEx(key, NAME)[0]
    except FileNotFoundError:
        return None


def registered():
    if sys.platform != 'win32':
        return None
    if startup_link().exists():
        try:
            metadata = json.loads((config_dir() / 'autostart-shortcut.json').read_text(encoding='utf-8'))
            expected = fingerprint()
            expected['link_hash'] = hashlib.sha256(startup_link().read_bytes()).hexdigest()
            if metadata == expected:
                # Force migration if the old registry entry still exists as well.
                return 'gammal Run-post finns' if legacy_value() else command()
        except (OSError, ValueError):
            pass
        return 'föråldrad genväg'
    return legacy_value()


def set_enabled(enabled):
    if sys.platform != 'win32':
        return False
    import winreg
    from windows_shortcut import create_shortcut
    from event_log import emit
    metadata = config_dir() / 'autostart-shortcut.json'
    if enabled:
        executable, arguments, base = launch_parts()
        info = fingerprint()
        create_shortcut(startup_link(), executable, subprocess.list2cmdline(arguments),
                        info['icon'], base)
        if not startup_link().is_file() or startup_link().stat().st_size == 0:
            raise OSError('Autostartgenvägen skapades inte korrekt.')
        info['link_hash'] = hashlib.sha256(startup_link().read_bytes()).hexdigest()
        emit('autostart.shortcut.created', path=startup_link(), command=info['command'])
        if startup_disabled():
            emit('autostart.disabled_by_windows', 'WARNING', message='Aktivera FTP-uploader under Inställningar > Appar > Autostart i Windows.')
        temporary = metadata.with_suffix('.tmp')
        temporary.write_text(json.dumps(info), encoding='utf-8')
        temporary.replace(metadata)
    else:
        startup_link().unlink(missing_ok=True)
        metadata.unlink(missing_ok=True)
    # Remove the old Run entry to prevent duplicate launches and Python branding.
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, KEY, 0, winreg.KEY_SET_VALUE) as key:
            winreg.DeleteValue(key, NAME)
    except FileNotFoundError:
        pass
    emit('autostart.registration', enabled=enabled, path=startup_link())
    return True


def startup_disabled():
    """Read Windows' user-controlled disable flag; never override it silently."""
    if sys.platform != 'win32':
        return False
    import winreg
    key_path = r'Software\Microsoft\Windows\CurrentVersion\Explorer\StartupApproved\StartupFolder'
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path) as key:
            value = winreg.QueryValueEx(key, startup_link().name)[0]
            return isinstance(value, bytes) and bool(value) and value[0] in (3, 7)
    except FileNotFoundError:
        return False


def install_app_shortcut():
    """A normal Start-menu entry lets users launch by our icon, not a .pyw file."""
    if sys.platform != 'win32':
        return None
    from windows_shortcut import create_shortcut
    executable, arguments, base = launch_parts()
    arguments = [arg for arg in arguments if arg != '--autostart']
    destination = startup_link().parent.parent / 'FTP-uploader.lnk'
    create_shortcut(destination, executable, subprocess.list2cmdline(arguments),
                    base / 'icon/icon.ico', base)
    return destination
