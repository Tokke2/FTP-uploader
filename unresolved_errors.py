# Copyright (c) 2026 Rickard Längkvist
"""Persistent active-error register. Resolution is explicit, never guessed."""
import json
from error_register_store import ErrorRegister


def show_unresolved(parent):
    import tkinter as tk
    from tkinter import ttk, messagebox, simpledialog
    from app_paths import logs_dir
    register = ErrorRegister(logs_dir())
    window = tk.Toplevel(parent)
    window.title('Aktiva fel – markera åtgärdade fel')
    window.geometry('900x560')
    listing = ttk.Treeview(window, columns=('code', 'source', 'count'), show='headings')
    for key, label in [('code', 'Felkod / ID'), ('source', 'Källogg'), ('count', 'Antal')]:
        listing.heading(key, text=label)
    listing.pack(fill='both', expand=True, padx=12, pady=12)
    detail = tk.Text(window, height=10, wrap='word')
    detail.pack(fill='both', expand=True, padx=12)
    entries = {}
    include_history = tk.BooleanVar(value=False)

    def refresh():
        entries.clear()
        listing.delete(*listing.get_children())
        for entry in register.records(include_resolved=include_history.get()):
            entries[entry['id']] = entry
            listing.insert('', 'end', iid=entry['id'], values=(entry['code'] + (' [åtgärdat]' if entry['status'] == 'resolved' else ''), ', '.join(entry['sources']), entry['count']))
        detail.delete('1.0', 'end')

    def select(event=None):
        selection = listing.selection()
        detail.delete('1.0', 'end')
        if selection:
            entry = entries[selection[0]]
            detail.insert('end', entry['details'] + '\n\nÅTGÄRDSHISTORIK\n' + json.dumps(entry.get('history', []), ensure_ascii=False, indent=2))

    def resolve():
        selection = listing.selection()
        if selection and messagebox.askyesno('Markera åtgärdade',
                'Markera valda fel som åtgärdade? Om de återkommer öppnas de igen.', parent=window):
            comment = simpledialog.askstring('Åtgärdskommentar', 'Vad åtgärdades?', parent=window)
            if comment is None:
                return
            with register.batch():
                for identifier in selection:
                    register.resolve(identifier, comment=comment)
            refresh()

    listing.bind('<<TreeviewSelect>>', select)
    buttons = ttk.Frame(window)
    buttons.pack(fill='x', padx=12, pady=12)
    ttk.Button(buttons, text='Markera som åtgärdade', command=resolve).pack(side='left')
    ttk.Button(buttons, text='Uppdatera lista', command=refresh).pack(side='left', padx=8)
    ttk.Checkbutton(buttons, text='Visa åtgärdade / historik', variable=include_history, command=refresh).pack(side='left')
    refresh()
