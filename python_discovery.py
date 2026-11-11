# Copyright (c) 2026 Rickard Längkvist
"""Find existing shared Python installations, offline, without creating environments."""
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

PROBE = ('import sys,json; import tkinter; '
         'print(json.dumps({"executable":sys.executable,"shared":sys.prefix==sys.base_prefix,'
         '"version":list(sys.version_info[:3]),"tk":tkinter.TkVersion}))')


def _run(command):
    return subprocess.run(command, capture_output=True, text=True, timeout=5,
                          creationflags=0x08000000 if sys.platform == 'win32' else 0)


def _registry_paths():
    try:
        import winreg
    except ImportError:
        return
    for hive in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
        for view in (getattr(winreg, 'KEY_WOW64_64KEY', 0), getattr(winreg, 'KEY_WOW64_32KEY', 0)):
            try:
                with winreg.OpenKey(hive, r'Software\Python', 0, winreg.KEY_READ | view) as root:
                    companies = [winreg.EnumKey(root, i) for i in range(winreg.QueryInfoKey(root)[0])]
            except OSError:
                continue
            for company in companies:
                try:
                    with winreg.OpenKey(hive, 'Software\\Python\\' + company, 0, winreg.KEY_READ | view) as key:
                        tags = [winreg.EnumKey(key, i) for i in range(winreg.QueryInfoKey(key)[0])]
                except OSError:
                    continue
                for tag in tags:
                    try:
                        with winreg.OpenKey(hive, 'Software\\Python\\%s\\%s\\InstallPath' % (company, tag), 0, winreg.KEY_READ | view) as key:
                            for name in ('ExecutablePath', ''):
                                try:
                                    value = winreg.QueryValueEx(key, name)[0]
                                    yield Path(value) / 'python.exe' if name == '' else Path(value)
                                except OSError:
                                    pass
                    except OSError:
                        continue


def candidates():
    """Prefer current shared interpreter; enumerate alternatives only if needed."""
    yield Path(sys.executable)
    base = getattr(sys, '_base_executable', None)
    if base:
        yield Path(base)
    for name in ('python3', 'python', 'pythonw'):
        found = shutil.which(name)
        if found:
            yield Path(found)
    if sys.platform == 'win32':
        yield from _registry_paths()
        launcher = shutil.which('py')
        if launcher:
            try:
                result = _run([launcher, '--list-paths'])
                for line in result.stdout.splitlines():
                    match = re.search(r'([A-Za-z]:\\.*?python(?:w)?\.exe)\s*$', line, re.I)
                    if match:
                        yield Path(match[1])
            except (OSError, subprocess.SubprocessError):
                pass
        local = Path(os.environ.get('LOCALAPPDATA', Path.home() / 'AppData/Local'))
        roots = [(local / 'Programs/Python', 'Python*/python.exe'),
                 (local / 'Python', 'pythoncore-*/python.exe'),
                 (Path(os.environ.get('ProgramFiles', 'C:/Program Files')), 'Python*/python.exe'),
                 (Path(os.environ.get('ProgramFiles(x86)', 'C:/Program Files (x86)')), 'Python*/python.exe'),
                 (Path(os.environ.get('SystemDrive', 'C:') + '/'), 'Python*/python.exe')]
    elif sys.platform == 'darwin':
        roots = [(Path('/Library/Frameworks/Python.framework/Versions'), '*/bin/python3'),
                 (Path('/opt/homebrew/bin'), 'python3*'), (Path('/usr/local/bin'), 'python3*'),
                 (Path('/usr/bin'), 'python3*')]
    else:
        roots = [(Path('/usr/bin'), 'python3*'), (Path('/usr/local/bin'), 'python3*'),
                 (Path('/opt'), 'python*/bin/python3'), (Path.home() / '.local/bin', 'python3*')]
    for root, pattern in roots:
        try:
            yield from sorted(root.glob(pattern), reverse=True)
        except OSError:
            continue


def probe(path):
    path = Path(path)
    if sys.platform == 'win32':
        # Store execution aliases may open installation UI. Never run these stubs.
        if path.parent.name.lower() == 'windowsapps':
            return None
        if path.name.lower() == 'pythonw.exe':
            path = path.with_name('python.exe')
    if not path.is_file():
        return None
    try:
        result = _run([str(path), '-I', '-c', PROBE])
        info = json.loads(result.stdout.strip()) if result.returncode == 0 else {}
        if info.get('shared') is True and tuple(info.get('version', ())) >= (3, 10) and info.get('tk'):
            executable = Path(info['executable'])
            if sys.platform == 'win32':
                quiet = executable.with_name('pythonw.exe')
                if not quiet.is_file():
                    return None
                executable = quiet
            return executable
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError):
        pass
    return None


def find_python():
    seen = set()
    for candidate in candidates():
        identity = os.path.normcase(str(candidate.resolve()))
        if identity in seen:
            continue
        seen.add(identity)
        found = probe(candidate)
        if found:
            return found
    raise OSError('Ingen befintlig system-Python med Tk-stöd hittades. '
                  'Installera/aktivera Python med Tcl/Tk; ingen egen miljö skapas.')


def select_for_start(entry):
    """Relaunch at most once, before claiming the instance lock or installing packages."""
    if getattr(sys, 'frozen', False):
        return
    if os.environ.pop('FTP_UPLOADER_RUNTIME_SELECTED', None) == '1':
        return
    try:
        selected = find_python()
    except OSError as exc:
        _log_selection(entry, 'FEL: %s' % exc)
        raise
    _log_selection(entry, 'Vald befintlig Python: %s; startad med: %s' % (selected, sys.executable))
    current = Path(sys.executable).resolve()
    if selected.resolve() == current:
        return
    # On Windows, a console Python and its Pythonw sibling are the same installation.
    if sys.platform == 'win32' and selected.parent.resolve() == current.parent and sys.prefix == sys.base_prefix:
        if current.name.lower() == 'pythonw.exe':
            return
    env = os.environ.copy()
    for name in ('PYTHONHOME', 'PYTHONPATH', 'VIRTUAL_ENV', '__PYVENV_LAUNCHER__'):
        env.pop(name, None)
    env['FTP_UPLOADER_RUNTIME_SELECTED'] = '1'
    # Capture Pythonw failures even if main.pyw fails before its first statement.
    from datetime import datetime
    directory = Path(entry).resolve().parent / 'logs'
    directory.mkdir(exist_ok=True)
    output = directory / ('python-child_%s_%d.log' % (datetime.now().strftime('%Y%m%d'), os.getpid()))
    with output.open('a', encoding='utf-8') as stream:
        child = subprocess.Popen([str(selected), str(Path(entry).resolve()), *sys.argv[1:]], env=env,
                                 cwd=Path(entry).resolve().parent, stdout=stream, stderr=subprocess.STDOUT)
    _log_selection(entry, 'Vidarestartad som pid=%s. Felutmatning: %s' % (child.pid, output))
    from startup_diagnostics import phase
    phase('Vidarestart till vald Python', 'Barnprocess pid=%s; logg=%s' % (child.pid, output))
    try:
        code = child.wait(timeout=1)
    except subprocess.TimeoutExpired:
        code = None  # Healthy long-running child; its early hook handles later errors.
    if code not in (None, 0):
        raise RuntimeError('Vald Python avslutades direkt med kod %s. Se %s' % (code, output))
    raise SystemExit(0)


def _log_selection(entry, message):
    try:
        from datetime import datetime
        directory = Path(entry).resolve().parent / 'logs'
        directory.mkdir(exist_ok=True)
        with (directory / 'python-discovery.log').open('a', encoding='utf-8') as stream:
            stream.write('[%s] %s\n' % (datetime.now().isoformat(sep=' ', timespec='seconds'), message))
    except OSError:
        pass
