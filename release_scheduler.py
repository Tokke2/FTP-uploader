# Copyright (c) 2026 Rickard Längkvist
"""Quiet, weekly release checks and coordinated Python-only restarts."""
import json
import os
from pathlib import Path
import queue
import subprocess
import sys
import threading
import time

from app_paths import config_dir, logs_dir, update_settings

from weekly_schedule import WeeklySchedule


def log(message):
    try:
        with (logs_dir() / 'update.log').open('a', encoding='utf-8') as output:
            output.write('%s %s\n' % (time.strftime('%Y-%m-%d %H:%M:%S'), message))
    except OSError:
        pass


def python_executable():
    executable = Path(sys.executable)
    if os.name == 'nt':
        quiet = executable.with_name('pythonw.exe')
        if quiet.exists():
            return str(quiet)
    return str(executable)


def spawn(command, env=None):
    return subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL, env=env,
                            creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0) if os.name == 'nt' else 0,
                            start_new_session=os.name != 'nt')


class ReleaseScheduler:
    def __init__(self, app, base):
        self.app, self.base = app, Path(base)
        self.results = queue.Queue()
        self.busy = False
        self.pending = None
        self.schedule = WeeklySchedule(config_dir() / 'weekly-checks.json')
        self.maintenance_pending = False
        self.schedule.due('release')
        self.schedule.due('python-and-packages')
        app.after(1000, self.tick)

    def tick(self):
        settings = update_settings()
        enabled = settings['mode'] != 'off' and os.environ.get('FTP_UPLOADER_AUTOUPDATE') != '0'
        try:
            result = self.results.get_nowait()
            self.busy = False
            if result:
                self.pending = result
        except queue.Empty:
            pass
        if enabled and not self.busy and self.schedule.due('release'):
            self.schedule.complete('release')
            self.busy = True
            threading.Thread(target=self.check, daemon=True, name='ReleaseCheck').start()
        if enabled and self.schedule.due('python-and-packages'):
            self.maintenance_pending = True
        needs_restart = (self.pending and settings['mode'] == 'auto') or self.maintenance_pending
        if enabled and needs_restart and not self.busy:
            # Any open dialog/editor or active background job postpones restart.
            dialogs = [w for w in self.app.winfo_children() if w.winfo_toplevel() is w]
            from restart_safety import active_job_reasons
            workers = active_job_reasons(self.app)
            plugin_busy = False  # Job flags/processes are included above.
            from restart_safety import unsaved_reasons
            unsaved = unsaved_reasons(self.app)
            if unsaved and unsaved != getattr(self, '_last_unsaved', None):
                log('Omstart väntar på osparade ändringar: ' + ', '.join(unsaved))
            self._last_unsaved = unsaved
            if not unsaved and not dialogs and not workers and not plugin_busy and not getattr(self.app, '_pipeline_busy', 0):
                try:
                    self.app._save_all_settings()
                    release = self.pending if self.pending and settings['mode'] == 'auto' else ('-', '-')
                    maintenance = self.maintenance_pending
                    spawn([python_executable(), str(self.base / 'release_scheduler.py'),
                           '--maintenance' if maintenance else '--restart', str(self.base), *release])
                    if maintenance:
                        self.schedule.complete('python-and-packages')
                except Exception as exc:
                    log('Omstart kunde inte förberedas: %s' % exc)
                    self.pending = None
                else:
                    self.app.quit_app()
                    return
        self.app.after(30000, self.tick)

    def check(self):
        from auto_update import check_release
        try:
            release = check_release(self.base)
            if release and (self.base / '.git').exists():
                log('Release finns men utvecklingskopian lämnas orörd.')
                release = None
            log('Ny release: %s' % (release,) if release else 'Releasekontroll klar; ingen installation.')
            self.results.put(release)
        except Exception as exc:
            log('Releasekontroll misslyckades: %s' % exc)
            self.results.put(None)


def restart(base, tag, commit, maintenance=False):
    """Wait for shutdown, update, and launch even if update fails/rolls back."""
    import socket
    base = Path(base)
    stopped = False
    for _ in range(120):
        with socket.socket() as guard:
            try:
                guard.bind(('127.0.0.1', 47200))
                stopped = True
                break
            except OSError:
                time.sleep(1)
    if not stopped:
        log('Omstart avbruten: appen stängdes inte inom två minuter.')
        return
    try:
        if tag != '-':
            from auto_update import apply_release
            log(apply_release(base, (tag, commit)))
    except Exception as exc:
        log('Uppdatering misslyckades: %s' % exc)
    if maintenance:
        os.environ['FTP_UPLOADER_SILENT_RESTART'] = '1'
        try:
            from runtime_startup import maintain_runtime
            maintain_runtime()
        except Exception as exc:
            log('FEL i veckokontroll av Python: %s' % exc)
        try:
            from ensure_deps import ensure_requirements
            if not ensure_requirements(base):
                log('FEL: veckouppdateringen av Python-tillägg kunde inte slutföras.')
        except Exception as exc:
            log('FEL i veckokontroll av Python-tillägg: %s' % exc)
    environment = dict(os.environ, FTP_UPLOADER_SILENT_RESTART='1')
    spawn([python_executable(), str(base / 'start.pyw')], env=environment)


if __name__ == '__main__' and len(sys.argv) == 5 and sys.argv[1] in ('--restart', '--maintenance'):
    restart(*sys.argv[2:], maintenance=sys.argv[1] == '--maintenance')
