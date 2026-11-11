# Copyright (c) 2026 Rickard Längkvist
"""Inspect the actual interpreter and upgrade only an owned existing package.

Never use `install` as a fallback when an existing interpreter cannot be upgraded.
Bootstrapping an interpreter on a Python-free computer is outside this module.
"""
from dataclasses import dataclass
from pathlib import Path
import json
import os
import re
import shutil
import subprocess
import sys
import urllib.request

from app_paths import logs_dir

TAG_API = 'https://api.github.com/repos/python/cpython/git/matching-refs/tags/v3.'


@dataclass(frozen=True)
class RuntimePlan:
    installed: tuple
    latest: tuple
    executable: str
    command: tuple = ()
    reason: str = ''


def version_text(version):
    return '.'.join(map(str, version))


def run(command, timeout=30):
    flags = getattr(subprocess, 'CREATE_NO_WINDOW', 0) if os.name == 'nt' else 0
    return subprocess.run(list(command), stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                          stderr=subprocess.STDOUT, text=True, errors='replace', timeout=timeout,
                          creationflags=flags)


def latest_python():
    request = urllib.request.Request(TAG_API, headers={'User-Agent': 'FTP-uploader',
        'Accept': 'application/vnd.github+json'})
    with urllib.request.urlopen(request, timeout=20) as response:
        tags = json.load(response)
    versions = []
    if not isinstance(tags, list):
        raise ValueError('Kunde inte läsa officiella Python-taggar.')
    for item in tags:
        match = re.fullmatch(r'refs/tags/v(3\.\d+\.\d+)', item.get('ref', ''))
        if match:
            versions.append(tuple(map(int, match[1].split('.'))))
    if not versions:
        raise ValueError('Ingen stabil Python-version hittades.')
    return max(versions)


def windows_registered_here(executable):
    """Require the PEP 514 registration to point to this interpreter."""
    try:
        import winreg
    except ImportError:
        return False
    series = '%s.%s' % tuple(sys.version_info[:2])
    key = chr(92).join(('Software', 'Python', 'PythonCore', series, 'InstallPath'))
    for hive in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
        for view in (getattr(winreg, 'KEY_WOW64_64KEY', 0), getattr(winreg, 'KEY_WOW64_32KEY', 0)):
            try:
                with winreg.OpenKey(hive, key, 0, winreg.KEY_READ | view) as handle:
                    folder = Path(winreg.QueryValueEx(handle, '')[0]).resolve()
                    if Path(executable).parent.resolve() == folder:
                        return True
            except OSError:
                continue
    return False


def inspect_runtime(latest=None):
    """Current executable is the authority, not another Python on PATH."""
    latest = latest or latest_python()
    installed = tuple(sys.version_info[:3])
    executable = str(Path(sys.executable).resolve())

    def plan(reason, command=()):
        return RuntimePlan(installed, latest, executable, tuple(command), reason)

    if getattr(sys, 'frozen', False):
        return plan('Paketerad app: byt inte dess inbyggda Python. Uppdatera appreleasen.')
    if latest <= installed:
        return plan('Den Python som kör appen är redan aktuell eller nyare.')
    if latest[:2] != installed[:2]:
        return plan('Senaste stabila Python är en annan serie. Automatisk installation spärras '
                    'för att inte skapa en parallell Python. Byt befintlig installation manuellt '
                    'och uppdatera genvägarna; ingen extra installation görs av appen.')
    if sys.platform == 'win32':
        if not windows_registered_here(executable):
            return plan('Den aktiva Python-installationen kunde inte identifieras i Windows-registret. Ingen extra installation görs.')
        manager = shutil.which('winget')
        if not manager:
            return plan('WinGet saknas. Uppgradera den befintliga Python-installationen manuellt.')
        package = 'Python.Python.%s.%s' % installed[:2]
        result = run([manager, 'list', '--id', package, '--exact', '--source', 'winget',
                      '--accept-source-agreements', '--disable-interactivity'])
        if result.returncode or package not in result.stdout:
            return plan('Den befintliga Python-installationen kunde inte identifieras i WinGet. Ingen ny installation görs.')
        return plan('Uppgradera befintligt WinGet-paket. Ingen install-fallback används.',
                    [manager, 'upgrade', '--id', package, '--exact', '--source', 'winget',
                     '--accept-source-agreements', '--accept-package-agreements', '--disable-interactivity'])
    if sys.platform == 'darwin':
        manager = shutil.which('brew')
        if not manager:
            return plan('Denna macOS-installation kan inte uppgraderas med Homebrew. Använd dess ursprungliga installerare.')
        for formula in ('python', 'python@%s.%s' % installed[:2]):
            result = run([manager, '--prefix', formula])
            prefix = Path(result.stdout.strip()).resolve()
            if result.returncode == 0 and prefix.is_dir() and Path(executable).is_relative_to(prefix):
                return plan('Uppgradera endast den befintliga Homebrew-formeln.', [manager, 'upgrade', formula])
        return plan('Python ägs inte av en identifierad Homebrew-formel. Ingen ny installation görs.')
    if sys.platform.startswith('linux'):
        apt = shutil.which('apt-get')
        query = shutil.which('dpkg-query')
        cache = shutil.which('apt-cache')
        if not all((apt, query, cache)):
            return plan('Använd Linux-distributionens pakethanterare för att uppgradera dess befintliga Python. Ingen install-fallback används.')
        owner = run([query, '-S', executable])
        if owner.returncode or not re.search(r'python3(?:\.\d+)?(?:-minimal)?:', owner.stdout):
            return plan('Den Python som kör appen kunde inte kopplas till ett installerat distributionspaket.')
        package = 'python%s.%s' % installed[:2]
        policy = run([cache, 'policy', package])
        candidate = re.search(r'Candidate:\s*(?:\d+:)?(3\.\d+\.\d+)', policy.stdout)
        if policy.returncode or not candidate or tuple(map(int, candidate[1].split('.'))) < latest:
            return plan('Distributionens förråd erbjuder inte senaste stabila Python. Systemets Python ersätts inte med en separat installation.')
        command = [apt, 'install', '--only-upgrade', '-y', package]
        if os.geteuid() != 0:
            elevate = shutil.which('pkexec')
            if not elevate:
                return plan('Uppgradering kräver administratör. Kör systemets paketuppgradering manuellt.')
            command.insert(0, elevate)
        return plan('Uppgradera endast ett befintligt systempaket (--only-upgrade).', command)
    return plan('Operativsystemet stöds inte för automatisk uppgradering av Python.')


def execute_upgrade(plan):
    """Explicitly approved action; never install a second interpreter on failure."""
    if not plan.command:
        raise RuntimeError(plan.reason)
    # Recheck ownership/version so a stale UI plan cannot target a new interpreter.
    current = inspect_runtime(latest=plan.latest)
    if current != plan:
        raise RuntimeError('Python-installationen har ändrats. Kör kontrollen igen.')
    result = run(plan.command, timeout=900)
    text = result.stdout[-12000:]
    with (logs_dir() / 'python-runtime.log').open('a', encoding='utf-8') as output:
        from log_clock import timestamp
        output.write('[%s] %s\n%s\n' % (timestamp(), 'OK' if result.returncode == 0 else 'FEL', text))
    if result.returncode:
        raise RuntimeError('Pakethanteraren kunde inte uppgradera Python. Ingen install-fallback kördes. Se logs/python-runtime.log.')
    executable = Path(plan.executable)
    if executable.name.lower() == 'pythonw.exe':
        executable = executable.with_name('python.exe')
    verification = run([str(executable), '--version'])
    match = re.search(r'Python (3\.\d+\.\d+)', verification.stdout)
    if verification.returncode or not match or tuple(map(int, match[1].split('.'))) < plan.latest:
        raise RuntimeError('Pakethanteraren avslutades men senaste Python kunde inte verifieras. Ingen install-fallback görs.')
    return 'Python är uppgraderad. Starta om appen för att använda den nya versionen.'


def show_python_status(parent):
    import queue
    import threading
    import tkinter as tk
    from tkinter import ttk, messagebox
    from restart_safety import unsaved_reasons
    window = tk.Toplevel(parent)
    window.title('Python – kontrollera befintlig installation')
    status = tk.StringVar(value='Kontrollerar installerad Python och senaste stabila version …')
    ttk.Label(window, textvariable=status, wraplength=560, justify='left').pack(padx=20, pady=20)
    results = queue.Queue()
    state = {'plan': None, 'busy': False}

    def launch(action):
        state['busy'] = True
        upgrade.configure(state='disabled')
        check.configure(state='disabled')
        def worker():
            try:
                results.put((True, action()))
            except Exception as exc:
                results.put((False, str(exc)))
        threading.Thread(target=worker, daemon=True, name='PythonRuntimeCheck').start()
        window.after(100, poll)

    def poll():
        try:
            ok, value = results.get_nowait()
        except queue.Empty:
            window.after(100, poll)
            return
        state['busy'] = False
        check.configure(state='normal')
        if ok and isinstance(value, RuntimePlan):
            state['plan'] = value
            status.set('Installerad: %s\nSenaste stabila: %s\nKörfil: %s\n\n%s' % (
                version_text(value.installed), version_text(value.latest), value.executable, value.reason))
            upgrade.configure(state='normal' if value.command else 'disabled')
        else:
            status.set(str(value))

    def update():
        if unsaved_reasons(parent) or getattr(parent, '_pipeline_busy', 0) or any(
                getattr(plugin, 'is_generating', False) for plugin in parent.plugins.values()):
            messagebox.showwarning('Python', 'Spara osparat arbete och avsluta pågående jobb först.', parent=window)
            return
        if messagebox.askyesno('Uppgradera befintlig Python',
                'Detta ändrar Python-installationen och kan påverka andra program. '
                'Administratörsgodkännande eller omstart kan krävas. Fortsätt?', parent=window):
            launch(lambda: execute_upgrade(state['plan']))

    buttons = ttk.Frame(window)
    buttons.pack(padx=20, pady=12)
    check = ttk.Button(buttons, text='Kontrollera igen', command=lambda: launch(inspect_runtime))
    check.pack(side='left', padx=4)
    upgrade = ttk.Button(buttons, text='Uppgradera befintlig Python', command=update, state='disabled')
    upgrade.pack(side='left', padx=4)
    window.protocol('WM_DELETE_WINDOW', lambda: None if state['busy'] else window.destroy())
    launch(inspect_runtime)
