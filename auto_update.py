"""Install stable GitHub Releases using Python only. Never use main or Git."""
import json
import os
from pathlib import Path
import queue
import threading
import urllib.request

from app_paths import logs_dir, update_settings, save_update_settings

API = 'https://api.github.com/repos/Tokke2/FTP-uploader/releases/latest'


def latest_release():
    request = urllib.request.Request(API, headers={'Accept': 'application/vnd.github+json',
                                                  'User-Agent': 'FTP-uploader'})
    with urllib.request.urlopen(request, timeout=15) as response:
        release = json.load(response)
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
        with urllib.request.urlopen(request, timeout=15) as response:
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
            with urllib.request.urlopen(request, timeout=30) as response, archive.open('wb') as output:
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
                    allowed = (len(relative.parts) == 1 and
                               (relative.suffix in ('.py', '.pyw') or relative.name == 'requirements.txt'))
                    allowed = allowed or (relative.parts[0] == 'plugins' and relative.suffix == '.py')
                    allowed = allowed or (relative.parts[0] == 'icon' and relative.suffix in ('.png', '.ico'))
                    if not allowed:
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


def check_before_start(base, parent=None, manual=False):
    """All network/file work runs outside Tk; confirmations run on Tk thread."""
    import tkinter as tk
    from tkinter import messagebox
    settings = update_settings()
    mode = settings['mode']
    pending = settings.get('pending_release') if not manual else None
    if not pending and not manual and (mode == 'off' or os.environ.get('FTP_UPLOADER_AUTOUPDATE') == '0'):
        return
    root = tk.Tk() if parent is None else tk.Toplevel(parent)
    root.title('FTP-uploader – uppdateringar')
    label = tk.Label(root, text='Kontrollerar stabil GitHub Release …', padx=25, pady=20)
    label.pack()
    root.protocol('WM_DELETE_WINDOW', lambda: None)
    results = queue.Queue()

    def worker(action):
        try:
            results.put(('ok', action()))
        except Exception as exc:
            results.put(('error', 'Kunde inte uppdatera: %s' % exc))

    def launch(action):
        threading.Thread(target=worker, args=(action,), daemon=True).start()
        root.after(100, poll)

    def finish(message):
        try:
            (logs_dir() / 'update.log').write_text(message + '\n', encoding='utf-8')
        except OSError:
            pass
        if manual:
            messagebox.showinfo('Uppdateringar', message, parent=root)
        root.destroy()

    def poll():
        try:
            status, value = results.get_nowait()
        except queue.Empty:
            root.after(100, poll)
            return
        if status == 'error':
            finish(value)
        elif isinstance(value, tuple):
            approved = (not manual and (mode == 'auto' or pending == value[0]))
            if not approved:
                approved = messagebox.askyesno('Ny stabil release',
                    'Release %s finns. %s' % (value[0],
                    'Installera vid nästa appstart?' if manual else 'Installera nu före appstart?'), parent=root)
            if not approved:
                finish('Uppdateringen avböjdes.')
            elif manual:
                save_update_settings(dict(settings, pending_release=value[0]))
                finish('Release %s installeras vid nästa start via start.pyw.' % value[0])
            else:
                label.config(text='Installerar release %s …' % value[0])
                # Consume the queued request before attempting installation.
                settings.pop('pending_release', None)
                save_update_settings(settings)
                launch(lambda: apply_release(base, value))
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
