# Copyright (c) 2026 Rickard Längkvist
"""Thread-safe processing events; Tk is touched only by the UI poll."""
from collections import deque
import threading
import time
import uuid


class ProcessingProgress:
    def __init__(self, app):
        self.app = app
        self.events = deque(maxlen=512)
        self.lock = threading.Lock()
        self.jobs = {}
        self.window = None
        self.selected = None
        self.mode = None
        self.stopped = False
        app.bind('<Destroy>', self._destroyed, add='+')
        app.after(100, self.poll)

    def _destroyed(self, event):
        if event.widget is self.app:
            self.stopped = True

    def post(self, kind, token, **data):
        with self.lock:
            if kind == 'stage':
                for index in range(len(self.events) - 1, -1, -1):
                    if self.events[index][:2] == (kind, token):
                        self.events[index] = (kind, token, data)
                        return
            self.events.append((kind, token, data))

    def begin(self, title):
        token = uuid.uuid4().hex
        self.post('begin', token, title=title, stage='Förbereder filer…', percent=None, started=time.monotonic())
        return token

    def stage(self, token, text, percent=None):
        self.post('stage', token, stage=str(text), percent=percent)

    def finish(self, token, failed=False, cancelled=False):
        self.post('finish', token, failed=failed, cancelled=cancelled)

    def _open(self):
        import tkinter as tk
        from tkinter import ttk
        if self.window is not None and self.window.winfo_exists():
            self.window.deiconify()
            return
        self.window = tk.Toplevel(self.app)
        self.window.title('Filbearbetning – FTP Uploader')
        self.window.geometry('540x250')
        self.window.minsize(360, 230)
        self.window.configure(bg='#090f26')
        from app_icon import apply_tk_window_icon
        apply_tk_window_icon(self.window)
        self.title = tk.Label(self.window, bg='#090f26', fg='#26dce0', font=('TkDefaultFont', 15, 'bold'))
        self.title.pack(fill='x', padx=20, pady=(18, 8))
        self.detail = tk.Label(self.window, bg='#090f26', fg='white', wraplength=480)
        self.detail.pack(fill='x', padx=20, pady=5)
        self.bar = ttk.Progressbar(self.window, maximum=100, mode='indeterminate')
        self.bar.pack(fill='x', padx=24, pady=12)
        self.elapsed = tk.Label(self.window, bg='#090f26', fg='#c4cce1')
        self.elapsed.pack(fill='x', padx=20)
        tk.Button(self.window, text='Dölj', command=self.window.withdraw).pack(pady=10)
        self.window.protocol('WM_DELETE_WINDOW', self.window.withdraw)
        def resize(event):
            if event.widget is self.window:
                self.detail.configure(wraplength=max(200, event.width - 40))
        self.window.bind('<Configure>', resize, add='+')
        self.mode = None

    def poll(self):
        if self.stopped:
            return
        try:
            with self.lock:
                events = list(self.events)
                self.events.clear()
            for kind, token, data in events:
                if kind == 'begin':
                    # Keep bounded history and concurrent jobs without mixing percentages.
                    self.jobs = {key: job for key, job in self.jobs.items() if not job.get('done')}
                    self.jobs[token] = data
                    self.selected = token
                    self._open()
                elif token in self.jobs:
                    self.jobs[token].update(data)
                    if kind == 'finish':
                        self.jobs[token]['done'] = True
                        self.jobs[token]['finished'] = time.monotonic()
            if self.selected in self.jobs:
                self.render(self.jobs[self.selected])
                active = [key for key, job in self.jobs.items() if not job.get('done')]
                if self.jobs[self.selected].get('done') and active:
                    self.selected = active[-1]
        finally:
            if not self.stopped:
                self.app.after(100, self.poll)

    def render(self, job):
        if self.window is None or not self.window.winfo_exists():
            return
        done = job.get('done', False)
        percent = job.get('percent')
        mode = 'determinate' if done or percent is not None else 'indeterminate'
        if self.mode != mode:
            self.bar.stop()
            self.bar.configure(mode=mode)
            if mode == 'indeterminate':
                self.bar.start(14)
            self.mode = mode
        self.title.configure(text=job['title'])
        if done:
            message = 'Avbrutet' if job.get('cancelled') else 'Klart med fel – se loggen' if job.get('failed') else 'Bearbetningen är klar'
            self.bar.configure(value=0 if job.get('failed') or job.get('cancelled') else 100)
        else:
            message = job['stage']
            if percent is not None:
                percent = max(0, min(100, float(percent)))
                self.bar.configure(value=percent)
                message += ' · %d %%' % percent
        self.detail.configure(text=message)
        seconds = max(0, int(job.get('finished', time.monotonic()) - job['started']))
        self.elapsed.configure(text='Förfluten tid: %d:%02d%s' % (seconds // 60, seconds % 60,
                               '' if done else ' · Arbetar…'))


class InlineProgress:
    """UI-thread adapter for a visible per-file bar, even without duration."""
    def __init__(self, bar, variable, label):
        self.bar, self.variable, self.label = bar, variable, label
        self.running = False

    def update(self, value=None):
        if value is None:
            if not self.running:
                self.bar.configure(mode='indeterminate')
                self.variable.set(0)
                self.bar.start(12)
                self.running = True
            self.label.configure(text='Arbetar…')
            return
        self.stop()
        value = max(0, min(100, float(value)))
        self.variable.set(value)
        self.label.configure(text='%d %%' % value)

    def stop(self, text=None):
        self.bar.stop()
        self.bar.configure(mode='determinate')
        self.running = False
        if text is not None:
            self.variable.set(0)
            self.label.configure(text=text)
