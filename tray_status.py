# Copyright (c) 2026 Rickard Längkvist
"""Thread-safe pipeline status; no filenames, passwords or exception text in tooltips."""
import threading


class TrayStatus:
    def __init__(self):
        self._lock = threading.RLock()
        self._local = threading.local()
        self._jobs = {}
        self._next = 0
        self._result = 'Redo'
        self._last = None

    def begin(self):
        with self._lock:
            self._next += 1
            token = self._next
            self._local.token = token
            self._jobs[token] = {'stage': 'Arbetar', 'done': None, 'total': None,
                                 'error': False, 'cancelled': False}
            self._result = 'Redo'
            return token

    def stage(self, label):
        with self._lock:
            job = self._jobs.get(getattr(self._local, 'token', None))
            if job is not None:
                job.update(stage=' '.join(str(label).split())[:70], done=None, total=None)

    def progress(self, done, total):
        with self._lock:
            job = self._jobs.get(getattr(self._local, 'token', None))
            if job is not None and total > 0:
                job.update(done=max(0, min(int(done), int(total))), total=int(total))

    def issue(self):
        with self._lock:
            job = self._jobs.get(getattr(self._local, 'token', None))
            if job is not None:
                job['error'] = True

    def cancelled(self):
        with self._lock:
            job = self._jobs.get(getattr(self._local, 'token', None))
            if job is not None:
                job['cancelled'] = True

    def finish(self, token, failed=False):
        with self._lock:
            job = self._jobs.pop(token, None)
            if job is None:
                return
            if failed or job['error']:
                self._result = 'Fel – se felloggen'
            elif job['cancelled'] and not self._result.startswith('Fel'):
                self._result = 'Avbrutet'
            if getattr(self._local, 'token', None) == token:
                del self._local.token

    def text(self):
        with self._lock:
            if not self._jobs:
                return self._result
            job = self._jobs[max(self._jobs)]
            text = job['stage']
            if job['total'] is not None:
                text += ' %d/%d' % (job['done'], job['total'])
            if len(self._jobs) > 1:
                text += ' (%d jobb)' % len(self._jobs)
            if self._result.startswith('Fel') or any(j['error'] for j in self._jobs.values()):
                text += ' · Fel registrerat'
            return text

    def attach(self, app):
        """Refresh on Tk's thread; coalesce fast worker updates and handle tray restarts."""
        def tick():
            plugin = app.context.get('_system_tray')
            manager = getattr(app, '_systray_mgr', None)
            icons = [getattr(plugin, 'tray_icon', None), getattr(manager, '_icon', None)]
            if manager is not plugin:
                icons.append(getattr(manager, 'tray_icon', None))
            text = self.text()
            identities = []
            for icon in icons:
                if icon is None or any(icon is previous for previous in identities):
                    continue
                identities.append(icon)
                if self._last is not None and self._last[0] is icon and self._last[1] == text:
                    continue
                try:
                    icon.title = ('FTP-uploader – ' + text)[:127]
                    icon.update_menu()
                    self._last = (icon, text)
                except Exception:
                    pass  # Tray may be starting/stopping, or unavailable on this OS.
            try:
                app.after(250, tick)
            except Exception:
                pass
        app.after(250, tick)


def status_text(app):
    status = app.context.get('_tray_status')
    return status.text() if status is not None else 'Redo'
