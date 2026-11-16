# Copyright (c) 2026 Rickard Längkvist
"""Install stable GitHub Releases using Python only. Never use main or Git."""
import json
import os
from pathlib import Path
import queue
import threading
import urllib.request
import urllib.error

from app_paths import logs_dir, update_settings, save_update_settings

API = 'https://api.github.com/repos/Tokke2/FTP-uploader/releases/latest'


def open_release_url(request, timeout=20):
    """Log the failing stage/address; bounded retries for transient GitHub errors."""
    import time
    from event_log import emit
    for attempt in range(3):
        try:
            return urllib.request.urlopen(request, timeout=timeout)
        except urllib.error.HTTPError as exc:
            emit('update.http_error', 'ERROR', url=request.full_url, status=exc.code, attempt=attempt + 1)
            if exc.code in (404, 429, 500, 502, 503, 504) and attempt < 2:
                time.sleep(0.5 * (attempt + 1))
                continue
            raise


def update_error_message(exc):
    if isinstance(exc, urllib.error.HTTPError):
        hint = {404: 'Release, tagg eller commit hittades inte. Den kan ha flyttats eller vara otillgänglig.',
                403: 'GitHub nekade åtkomst eller API-gränsen har nåtts.',
                429: 'GitHubs anropsgräns har nåtts. Försök senare.'}.get(exc.code, 'GitHub svarade med ett HTTP-fel.')
        return 'Kunde inte uppdatera: HTTP %s. %s\nAdress: %s\nSe logs/update.log.' % (exc.code, hint, exc.url)
    return 'Kunde inte uppdatera: %s\nSe logs/update.log.' % exc


def latest_release():
    request = urllib.request.Request(API, headers={'Accept': 'application/vnd.github+json',
                                                  'User-Agent': 'FTP-uploader'})
    try:
        with open_release_url(request, timeout=15) as response:
            release = json.load(response)
    except urllib.error.HTTPError as exc:
        if exc.code != 404:
            raise
        # /latest can be temporarily absent. Only published stable releases,
        # never main or the highest Git tag without an associated release.
        request = urllib.request.Request(API.rsplit('/', 1)[0] + '?per_page=100',
                                         headers={'Accept': 'application/vnd.github+json', 'User-Agent': 'FTP-uploader'})
        with open_release_url(request, timeout=15) as response:
            releases = json.load(response)
        release = next((item for item in releases if not item.get('draft') and not item.get('prerelease')), None)
        if release is None:
            raise ValueError('Ingen publicerad stabil release hittades.')
    tag = release['tag_name']
    if release.get('draft') or release.get('prerelease') or not isinstance(tag, str):
        raise ValueError('Ingen stabil release.')
    # Never interpret an API response as a command option/ref expression.
    import re
    if not re.fullmatch(r'v?\d+\.\d+\.\d+(?:\.\d+)?', tag):
        raise ValueError('Releasetaggen måste vara vX.Y.Z eller X.Y.Z.')
    return tag


def release_commit(tag):
    """Resolve the published release tag, including annotated tags; never main."""
    import re
    if not re.fullmatch(r'v?\d+\.\d+\.\d+(?:\.\d+)?', tag):
        raise ValueError('Ogiltig releasetagg.')
    endpoint = 'https://api.github.com/repos/Tokke2/FTP-uploader/git/'
    url = endpoint + 'ref/tags/' + tag
    for _ in range(8):
        request = urllib.request.Request(url, headers={'User-Agent': 'FTP-uploader'})
        with open_release_url(request, timeout=15) as response:
            obj = json.load(response)['object']
        sha = obj.get('sha', '')
        if not re.fullmatch(r'[0-9a-f]{40}', sha):
            raise ValueError('Ogiltig release-commit.')
        if obj.get('type') == 'commit':
            return sha
        if obj.get('type') != 'tag':
            raise ValueError('Releasetaggen pekar inte på programkod.')
        url = endpoint + 'tags/' + sha
    raise ValueError('För många nästlade releasetaggar.')


def managed_file(path):
    """Same file scope for comparison and installation."""
    path = Path(path)
    return ((len(path.parts) == 1 and
             (path.suffix in ('.py', '.pyw') or path.name in ('requirements.txt', 'Starta.vbs', 'Starta.sh', 'LICENSE', 'COPYRIGHT')))
            or (len(path.parts) > 1 and path.parts[0] == 'plugins' and path.suffix == '.py')
            or (len(path.parts) > 1 and path.parts[0] == 'icon' and path.suffix in ('.png', '.ico')))


def release_files(commit):
    """Read the file hashes of the exact release commit, never a branch."""
    import re
    from pathlib import PurePosixPath
    if not re.fullmatch(r'[0-9a-f]{40}', commit):
        raise ValueError('Ogiltig release-commit.')
    url = 'https://api.github.com/repos/Tokke2/FTP-uploader/git/trees/' + commit + '?recursive=1'
    request = urllib.request.Request(url, headers={'User-Agent': 'FTP-uploader'})
    with open_release_url(request, timeout=20) as response:
        tree = json.load(response)
    if tree.get('truncated') or not isinstance(tree.get('tree'), list):
        raise ValueError('Ofullständig fillista från GitHub.')
    files = {}
    for item in tree['tree']:
        name = item.get('path', '')
        path = PurePosixPath(name)
        if path.is_absolute() or '..' in path.parts or ':' in name or '\\' in name:
            raise ValueError('Ogiltig sökväg i releasefillistan.')
        if item.get('type') != 'blob' or not managed_file(name):
            continue
        if item.get('mode') == '120000':
            raise ValueError('Symboliska länkar stöds inte.')
        sha = item.get('sha', '')
        if not re.fullmatch(r'[0-9a-f]{40}', sha):
            raise ValueError('Ogiltig filhash i releasefillistan.')
        files[name] = sha
    if 'main.pyw' not in files:
        raise ValueError('Releasefillistan saknar main.pyw.')
    return files


def files_match_release(base, files):
    """Compare actual file content using Git blob hashes; no Git executable."""
    import hashlib
    base = Path(base).resolve()
    for name, expected in files.items():
        path = base / name
        if not path.resolve().is_relative_to(base) or path.is_symlink():
            return False
        try:
            content = path.read_bytes()
        except OSError:
            return False
        blob = b'blob ' + str(len(content)).encode('ascii') + b'\0' + content
        if hashlib.sha1(blob).hexdigest() != expected:
            return False
    return True


def check_release(base):
    """Read-only release check using Python's standard library; no Git needed."""
    import re
    source = (Path(base) / 'main.pyw').read_text(encoding='utf-8')
    match = re.search(r'^APP_VERSION\s*=\s*["\']([0-9.]+)["\']', source, re.MULTILINE)
    if not match:
        raise RuntimeError('Kunde inte läsa installerad version.')
    tag = latest_release()
    installed = tuple(int(part) for part in match[1].split('.'))
    available = tuple(int(part) for part in tag.lstrip('v').split('.'))
    if available < installed:
        return None
    commit = release_commit(tag)
    try:
        state = json.loads((Path(base) / '.release-state.json').read_text(encoding='utf-8'))
    except (OSError, ValueError):
        state = {}
    if available == installed and isinstance(state, dict) and state.get('commit') == commit and state.get('tag') == tag:
        if files_match_release(base, release_files(commit)):
            return None
    # Same version with a moved tag is still an update. Unknown installations
    # are installed once so subsequent checks have a reliable baseline.
    return tag, commit


def apply_release(base, release):
    # Hold the app's existing single-instance port throughout installation.
    # A running GUI (or a competing startup) must not load half-updated code.
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as guard:
        try:
            guard.bind(('127.0.0.1', 47200))
            guard.listen(1)
        except OSError:
            raise RuntimeError('Appen körs redan. Stäng den före releaseinstallationen.')
        return _install_release(base, release)


def _install_release(base, release):
    """Install source from the exact release tag, with per-file backup/rollback.

    Only application code, dependencies and icons are replaced. User settings,
    exports and unrelated files are never installed from the archive.
    """
    import re
    import shutil
    import stat
    import tempfile
    import zipfile
    from datetime import datetime
    base = Path(base).resolve()
    tag = release[0]
    if not re.fullmatch(r'v?\d+\.\d+\.\d+(?:\.\d+)?', tag):
        raise ValueError('Ogiltig releasetagg.')
    commit = release[1]
    if not re.fullmatch(r'[0-9a-f]{40}', commit):
        raise ValueError('Ogiltig release-commit.')
    # A development checkout must never have its branch files overwritten.
    if (base / '.git').exists():
        raise RuntimeError('Utvecklingskopia med .git: installation hoppas över. '
                           'Använd en uppackad release för automatisk uppdatering.')
    lock = base / '.release-update.lock'
    descriptor = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    os.close(descriptor)
    backup = None
    changed = []
    try:
        with tempfile.TemporaryDirectory(prefix='ftp-release-') as temporary:
            work = Path(temporary)
            archive = work / 'release.zip'
            url = 'https://api.github.com/repos/Tokke2/FTP-uploader/zipball/' + commit
            request = urllib.request.Request(url, headers={'User-Agent': 'FTP-uploader'})
            with open_release_url(request, timeout=30) as response, archive.open('wb') as output:
                total = 0
                while True:
                    chunk = response.read(1024 * 1024)
                    if not chunk:
                        break
                    total += len(chunk)
                    if total > 64 * 1024 * 1024:
                        raise ValueError('Releasearkivet är för stort.')
                    output.write(chunk)
            staged = work / 'staged'
            staged.mkdir()
            files = []
            with zipfile.ZipFile(archive) as zipped:
                members = zipped.infolist()
                if len(members) > 10000 or sum(m.file_size for m in members) > 128 * 1024 * 1024:
                    raise ValueError('För stort uppackat releasearkiv.')
                roots = set()
                for member in members:
                    parts = member.filename.split('/')
                    if (member.filename.startswith('/') or '\\' in member.filename
                            or any(part in ('.', '..') or ':' in part for part in parts)):
                        raise ValueError('Osäker sökväg i releasearkivet.')
                    roots.add(parts[0])
                    if len(roots) != 1:
                        raise ValueError('Releasearkivet måste ha en rotmapp.')
                    if stat.S_ISLNK(member.external_attr >> 16):
                        raise ValueError('Symboliska länkar tillåts inte i releasearkiv.')
                    if member.is_dir() or len(parts) < 2:
                        continue
                    relative = Path(*parts[1:])
                    # Explicit installation scope; never import config or exports.
                    if not managed_file(relative):
                        continue
                    if relative in files:
                        raise ValueError('Duplicerad fil i releasearkivet.')
                    target = staged / relative
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(zipped.read(member))
                    files.append(relative)
            required = {'start.pyw', 'main.pyw', 'helpers.py', 'ensure_deps.py', 'requirements.txt'}
            if not required.issubset({str(path) for path in files}):
                raise ValueError('Releasen saknar nödvändiga appfiler.')
            source = (staged / 'main.pyw').read_text(encoding='utf-8')
            version = re.search(r'^APP_VERSION\s*=\s*["\']([0-9.]+)["\']', source, re.MULTILINE)
            if not version or version[1] != tag.lstrip('v'):
                raise ValueError('Releasetagg och APP_VERSION stämmer inte överens.')
            state_file = Path('.release-state.json')
            (staged / state_file).write_text(json.dumps({'tag': tag, 'commit': commit}), encoding='utf-8')
            files.append(state_file)
            # Validate all code before changing a single installed file.
            for relative in files:
                if relative.suffix in ('.py', '.pyw'):
                    compile((staged / relative).read_bytes(), str(relative), 'exec')
                target = base / relative
                if not target.resolve().is_relative_to(base):
                    raise ValueError('Installationssökväg pekar utanför appmappen.')
            backup = base.parent / (base.name + '.release-backup-' + datetime.now().strftime('%Y%m%d-%H%M%S-%f'))
            backup.mkdir()
            for relative in files:
                target = base / relative
                existed = target.exists()
                if existed:
                    saved = backup / relative
                    saved.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(target, saved)
                target.parent.mkdir(parents=True, exist_ok=True)
                # Mark before replacement so even a failed replacement is restored.
                changed.append((relative, existed))
                incoming = target.with_name(target.name + '.release-tmp')
                try:
                    shutil.copy2(staged / relative, incoming)
                    incoming.replace(target)
                finally:
                    incoming.unlink(missing_ok=True)
            return 'Installerad release %s. Säkerhetskopia: %s' % (tag, backup)
    except Exception:
        failures = []
        for relative, existed in reversed(changed):
            try:
                target = base / relative
                if existed:
                    shutil.copy2(backup / relative, target)
                else:
                    target.unlink(missing_ok=True)
            except OSError:
                failures.append(str(relative))
        if failures:
            raise RuntimeError('Återställning ofullständig. Säkerhetskopia: %s. Filer: %s' %
                               (backup, ', '.join(failures)))
        raise
    finally:
        lock.unlink(missing_ok=True)


def live_update_blockers(app):
    from restart_safety import unsaved_reasons, active_job_reasons
    return unsaved_reasons(app) + active_job_reasons(app)


class RestartCountdown:
    """Cancellable three-second restart; all callbacks run on the UI thread."""
    def __init__(self, window, display, restart, seconds=3):
        self.window, self.display, self.restart = window, display, restart
        self.seconds, self.cancelled, self.timer = seconds, False, None

    def start(self):
        self.display(self.seconds)
        self.timer = self.window.after(1000, self.tick)

    def tick(self):
        if self.cancelled:
            return
        self.seconds -= 1
        if self.seconds <= 0:
            self.cancelled = True
            self.restart()
        else:
            self.start()

    def cancel(self):
        self.cancelled = True
        if self.timer is not None:
            self.window.after_cancel(self.timer)
            self.timer = None


def restart_installed(app, base):
    reasons = live_update_blockers(app)
    if reasons:
        raise RuntimeError('Omstart uppskjuten: ' + ', '.join(reasons))
    from release_scheduler import spawn, python_executable
    app._save_all_settings()
    # The helper waits for shutdown/instance-lock release; no second download.
    spawn([python_executable(), str(Path(base) / 'release_scheduler.py'),
           '--restart', str(base), '-', '-'])
    app.quit_app()


def offer_installed_restart(root, app, base, label):
    import tkinter as tk
    from tkinter import messagebox
    def later():
        countdown.cancel()
        root.destroy()
    def restart_now():
        countdown.cancel()
        try:
            restart_installed(app, base)
        except Exception as exc:
            messagebox.showwarning('Omstart uppskjuten', str(exc), parent=root)
        else:
            root.destroy()
    countdown = RestartCountdown(root, lambda remaining: label.config(
        text='Uppdateringen är installerad. Startar om om %d sekunder.\nVälj Senare för att fortsätta utan omstart.' % remaining), restart_now)
    tk.Button(root, text='Starta om nu', command=restart_now).pack(side='left', padx=15, pady=12)
    tk.Button(root, text='Senare', command=later).pack(side='right', padx=15, pady=12)
    root.protocol('WM_DELETE_WINDOW', later)
    root.bind('<Escape>', lambda event: later())
    countdown.start()


def check_before_start(base, parent=None, manual=False):
    """All network/file work runs outside Tk; confirmations run on Tk thread."""
    import tkinter as tk
    from tkinter import messagebox
    if parent is not None and getattr(parent, '_release_update_active', False):
        return
    settings = update_settings()
    mode = settings['mode']
    pending = settings.get('pending_release') if not manual else None
    if not pending and not manual and (mode == 'off' or os.environ.get('FTP_UPLOADER_AUTOUPDATE') == '0'):
        return
    root = tk.Tk() if parent is None else tk.Toplevel(parent)
    if parent is not None:
        parent._release_update_active = True
        def release_flag(event):
            if event.widget is root:
                parent._release_update_active = False
        root.bind('<Destroy>', release_flag, add='+')
    installing = False
    root.title('FTP-uploader – uppdateringar')
    from app_icon import apply_tk_window_icon
    apply_tk_window_icon(root)
    label = tk.Label(root, text='Kontrollerar stabil GitHub Release …', padx=25, pady=20)
    label.pack()
    root.protocol('WM_DELETE_WINDOW', lambda: None)
    results = queue.Queue()

    def worker(action):
        try:
            results.put(('ok', action()))
        except Exception as exc:
            import traceback
            from event_log import exception as log_exception
            log_exception('update.failed', type(exc), exc, exc.__traceback__)
            try:
                with (logs_dir() / 'update.log').open('a', encoding='utf-8') as stream:
                    stream.write(traceback.format_exc() + '\n')
            except OSError:
                pass
            results.put(('error', update_error_message(exc)))

    def launch(action):
        threading.Thread(target=worker, args=(action,), daemon=True).start()
        root.after(100, poll)

    def finish(message):
        if parent is not None:
            from restart_safety import active_job_reasons
            stop_event = getattr(parent, '_update_stop_event', None)
            if stop_event is not None and not active_job_reasons(parent):
                stop_event.clear()
        try:
            with (logs_dir() / 'update.log').open('a', encoding='utf-8') as stream:
                from datetime import datetime
                stream.write('[%s] %s\n' % (datetime.now().isoformat(), message))
        except OSError:
            pass
        if manual:
            messagebox.showinfo('Uppdateringar', message, parent=root)
        root.destroy()

    def poll():
        nonlocal installing
        try:
            status, value = results.get_nowait()
        except queue.Empty:
            root.after(100, poll)
            return
        if status == 'error':
            finish(value)
        elif isinstance(value, tuple):
            approved = manual or mode == 'auto' or pending == value[0]
            if not approved:
                approved = messagebox.askyesno('Ny stabil release',
                    'Release %s finns. Ladda ned och installera nu?' % value[0], parent=root)
            if not approved:
                finish('Uppdateringen avböjdes.')
                return
            if parent is not None:
                from restart_safety import request_job_stop, active_job_reasons, unsaved_reasons
                # Hold the UI against new jobs while current workers unwind.
                root.grab_set()
                request_job_stop(parent)
                jobs = active_job_reasons(parent)
                if jobs:
                    label.config(text='Stoppar pågående jobb före uppdatering …\n' + ', '.join(jobs))
                    root.after(200, lambda: (results.put(('ok', value)), poll()))
                    return
                reasons = unsaved_reasons(parent)
                if reasons:
                    root.grab_release()
                    finish('Jobben har stoppats. Spara ändringar före uppdatering: ' + ', '.join(reasons))
                    return
            installing = True
            label.config(text='Laddar ned och installerar release %s …' % value[0])
            settings.pop('pending_release', None)
            save_update_settings(settings)
            launch(lambda: apply_release(base, value))
        else:
            if installing and parent is not None:
                try:
                    with (logs_dir() / 'update.log').open('a', encoding='utf-8') as stream:
                        stream.write(str(value) + '\n')
                except OSError:
                    pass
                root.grab_release()
                stop_event = getattr(parent, '_update_stop_event', None)
                if stop_event is not None:
                    stop_event.clear()
                offer_installed_restart(root, parent, base, label)
            else:
                finish(value or 'Denna release är redan installerad.')

    launch(lambda: (pending, release_commit(pending)) if pending else check_release(base))
    if parent is None:
        root.mainloop()


def show_update_settings(parent, base):
    import tkinter as tk
    from tkinter import ttk
    window = tk.Toplevel(parent)
    window.title('Uppdateringar')
    mode = tk.StringVar(value=update_settings()['mode'])
    ttk.Label(window, text='Stabila utgåvor från GitHub Releases').pack(padx=20, pady=10)
    for text, value in [('Uppdatera automatiskt', 'auto'), ('Fråga först', 'ask'), ('Avstängt', 'off')]:
        ttk.Radiobutton(window, text=text, variable=mode, value=value).pack(anchor='w', padx=20)
    ttk.Button(window, text='Spara', command=lambda: (
        save_update_settings({'mode': mode.get()}), window.destroy())).pack(pady=10)
    ttk.Button(window, text='Sök efter uppdateringar', command=lambda:
               check_before_start(base, parent=window, manual=True)).pack(padx=20, pady=10)


def request_from_tray(app):
    """Tray callbacks run outside Tk: dispatch manual release check to Tk."""
    def show():
        check_before_start(Path(__file__).resolve().parent, parent=app, manual=True)
    app.after(0, show)
