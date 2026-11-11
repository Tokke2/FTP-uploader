# Copyright (c) 2026 Rickard Längkvist
"""Local, bounded observations and evidence-based suggestions, never self-modifying code."""
from collections import Counter
from datetime import datetime
import json
from pathlib import Path
import sqlite3
import statistics
import threading

LOCK = threading.RLock()
MAX_EXPORTS = 200
PREFERENCE_KEYS = ('jpeg_quality', 'fullsize_max', 'responsive_images', 'download_mode', 'theme', 'columns')


class LocalLearning:
    def __init__(self, path=None):
        if path is None:
            from app_paths import data_dir
            path = data_dir() / 'learning' / 'observations.sqlite3'
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with LOCK, self.connect() as connection:
            connection.execute('CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value INTEGER)')
            connection.execute('CREATE TABLE IF NOT EXISTS exports (id INTEGER PRIMARY KEY, at TEXT, folder TEXT, preferences TEXT, source_bytes INTEGER, web_bytes INTEGER, large_images INTEGER, image_count INTEGER)')

    def connect(self):
        # sqlite connection contexts do not close the connection themselves.
        from contextlib import contextmanager
        @contextmanager
        def opened():
            connection = sqlite3.connect(self.path, timeout=5)
            try:
                with connection:
                    yield connection
            finally:
                connection.close()
        return opened()

    def enabled(self):
        with LOCK, self.connect() as connection:
            row = connection.execute("SELECT value FROM settings WHERE key='enabled'").fetchone()
            return row is None or bool(row[0])

    def set_enabled(self, enabled):
        with LOCK, self.connect() as connection:
            connection.execute("INSERT OR REPLACE INTO settings VALUES ('enabled', ?)", (int(enabled),))

    def clear(self):
        with LOCK, self.connect() as connection:
            connection.execute('DELETE FROM exports')
        # Remove deleted paths from SQLite free pages too.
        with LOCK, self.connect() as connection:
            connection.execute('VACUUM')

    def observe_export(self, gallery, report):
        with LOCK, self.connect() as connection:
            enabled = connection.execute("SELECT value FROM settings WHERE key='enabled'").fetchone()
            if enabled is not None and not enabled[0]:
                return
            preferences = {key: gallery[key] for key in PREFERENCE_KEYS if key in gallery}
            totals = report.get('totals', {})
            images = report.get('images', [])
            connection.execute('INSERT INTO exports (at,folder,preferences,source_bytes,web_bytes,large_images,image_count) VALUES (?,?,?,?,?,?,?)',
                (datetime.now().astimezone().isoformat(timespec='seconds'), str(gallery.get('images_path', '')),
                 json.dumps(preferences, ensure_ascii=False), int(totals.get('source_bytes', 0)),
                 int(totals.get('web_bytes', 0)), sum(row.get('web_bytes', 0) > 1048576 for row in images), len(images)))
            connection.execute('DELETE FROM exports WHERE id NOT IN (SELECT id FROM exports ORDER BY id DESC LIMIT ?)', (MAX_EXPORTS,))

    def suggestions(self):
        with LOCK, self.connect() as connection:
            rows = connection.execute('SELECT folder,preferences,source_bytes,web_bytes,large_images,image_count FROM exports ORDER BY id DESC LIMIT 20').fetchall()
        if not rows:
            return ['Inga observationer ännu. Efter lyckade exporter samlas lokala resultat.']
        result = ['Underlag: %d senaste lyckade exporter (högst 200 sparas). Förslag ändrar aldrig dina val.' % len(rows)]
        folders = Counter(row[0] for row in rows if row[0])
        if folders:
            folder, count = folders.most_common(1)[0]
            if count >= 2:
                result.append('Vanlig bildmapp: %s (%d/%d exporter). Välj den manuellt om den passar nästa uppgift.' % (folder, count, len(rows)))
        prefs = Counter(row[1] for row in rows)
        preferred, count = prefs.most_common(1)[0]
        if count >= 3:
            result.append('Vanliga exportval (%d/%d): %s. Detta är en observerad vana, inte ett kvalitetsbetyg.' % (count, len(rows), preferred))
        if len(rows) < 3:
            result.append('För få exporter för bildförslag; minst tre behövs.')
        else:
            large = sum(row[4] for row in rows)
            images = sum(row[5] for row in rows)
            if large:
                result.append('%d av %d observerade webbilder var över 1 MiB. Prova mindre maxstorlek eller lägre JPEG-kvalitet på en kopia och jämför visuellt före publicering.' % (large, images))
            ratios = [(1 - row[3] / row[2]) * 100 for row in rows if row[2] > 0]
            if ratios:
                result.append('Medianbesparing källa → webbilder: %.1f%% per export. Källan kan vara en äldre webbild; visuellt innehåll och metadataförlust bedöms inte.' % statistics.median(ratios))
        return result


def error_suggestions(records):
    result = []
    for record in records:
        if record.get('status') != 'open' or record.get('count', 0) < 2:
            continue
        result.append('%s: %d registrerade loggträffar (inte nödvändigtvis separata fel). Se Aktiva fel för detaljer.' % (record.get('code', record.get('id')), record['count']))
        history = [event for event in record.get('history', []) if event.get('action') == 'resolved' and event.get('comment')]
        if history:
            result.append('Tidigare manuellt rapporterad åtgärd för samma fel: %s. Felet har återkommit; åtgärden är inte en verifierad lösning.' % history[-1]['comment'])
        if len(result) >= 20:
            break
    return result or ['Inga återkommande öppna fel med tillräckligt underlag.']


def show_learning(parent):
    import tkinter as tk
    from tkinter import ttk, messagebox
    from app_paths import logs_dir
    from error_register_store import ErrorRegister
    try:
        learning = LocalLearning()
    except Exception as exc:
        messagebox.showerror('Lokalt lärande', str(exc), parent=parent)
        return
    window = tk.Toplevel(parent)
    window.title('Lokalt lärande – observationer och förslag')
    window.geometry('850x640')
    enabled = tk.BooleanVar(master=window, value=learning.enabled())
    ttk.Label(window, text='Lokal statistik, inte en självomskrivande AI. Inga bilder eller lösenord lagras här. '
              'Mappar och utvalda exportinställningar sparas lokalt. Felhistorik läses från det befintliga felregistret.',
              wraplength=790).pack(fill='x', padx=16, pady=12)
    def change_enabled():
        try:
            learning.set_enabled(enabled.get())
        except Exception as exc:
            messagebox.showerror('Lokalt lärande', str(exc), parent=window)
    ttk.Checkbutton(window, text='Samla nya exportobservationer löpande', variable=enabled,
                    command=change_enabled).pack(anchor='w', padx=16)
    text = tk.Text(window, wrap='word')
    text.pack(fill='both', expand=True, padx=16, pady=12)
    def refresh():
        try:
            suggestions = learning.suggestions()
            errors = error_suggestions(ErrorRegister(logs_dir()).records(include_resolved=True))
            content = '\n\n'.join(suggestions) + '\n\nFEL OCH STABILITET\n\n' + '\n\n'.join(errors)
            text.configure(state='normal')
            text.delete('1.0', 'end')
            text.insert('1.0', content)
            text.configure(state='disabled')
        except Exception as exc:
            messagebox.showerror('Lokalt lärande', str(exc), parent=window)
    def clear():
        if messagebox.askyesno('Radera observationer', 'Radera inlärningshistoriken för exporter? '
                              'Det ordinarie felregistret och dina inställningar lämnas orörda.', parent=window):
            try:
                learning.clear()
                refresh()
            except Exception as exc:
                messagebox.showerror('Lokalt lärande', str(exc), parent=window)
    buttons = ttk.Frame(window)
    buttons.pack(fill='x', padx=16, pady=12)
    ttk.Button(buttons, text='Uppdatera förslag', command=refresh).pack(side='left')
    ttk.Button(buttons, text='Radera inlärningshistorik', command=clear).pack(side='left', padx=8)
    refresh()
    def tick():
        if window.winfo_exists():
            refresh()
            window.after(5000, tick)
    window.after(5000, tick)


def record_export(gallery, report, log=None):
    """Learning must never make a valid export fail."""
    try:
        LocalLearning().observe_export(gallery, report)
    except Exception as exc:
        if log:
            log('  [!] Lokalt lärande kunde inte spara observationen: %s' % exc)
