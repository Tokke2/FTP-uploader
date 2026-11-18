# Copyright (c) 2026 Rickard Längkvist
"""Explicit opt-ins for localized pages, panoramas and MP4 renditions."""
import re
from resource_profiles import PROFILES


def validate(value):
    value = value if isinstance(value, dict) else {}
    languages = value.get('languages', {})
    if not isinstance(languages, dict) or len(languages) > 12:
        raise ValueError('Språk ska vara ett objekt med högst 12 språkkoder.')
    clean = {}
    for code, item in languages.items():
        if not re.fullmatch(r'[a-z]{2,3}(?:-[A-Z]{2})?', code) or not isinstance(item, dict):
            raise ValueError('Ogiltig språkkod eller översättning: %s' % code)
        labels = item.get('labels', {})
        if not isinstance(labels, dict) or len(labels) > 200 or not all(isinstance(k, str) and isinstance(v, str) and len(k)+len(v) < 4000 for k,v in labels.items()):
            raise ValueError('labels måste vara en begränsad text-till-text-ordlista.')
        clean[code] = {'title': str(item.get('title', ''))[:1000], 'description': str(item.get('description', ''))[:10000],
                       'labels': labels, 'dir': 'rtl' if item.get('dir') == 'rtl' else 'ltr'}
    qualities = value.get('qualities', [])
    if not isinstance(qualities, list) or any(q not in (480, 720, 1080) for q in qualities):
        raise ValueError('Videokvalitet måste vara en lista med 480, 720 och/eller 1080.')
    return {'languages': clean, 'panorama_auto': value.get('panorama_auto') is True,
            'qualities': sorted(set(qualities)),
            'resource_profile': value.get('resource_profile') if value.get('resource_profile') in PROFILES else 'balanced'}


def open_options(app, settings):
    import json
    import tkinter as tk
    from tkinter import ttk, messagebox
    from workspace_design import window_size
    window = tk.Toplevel(app)
    window.title('Språk, panorama, videokvaliteter och resurser')
    w,h = window_size(app.winfo_screenwidth(), app.winfo_screenheight())
    window.geometry('%dx%d' % (min(w, 800), min(h, 680)))
    current = validate(getattr(settings, 'delivery_options', {}))
    profile = tk.StringVar(window, value=current['resource_profile'])
    pano = tk.BooleanVar(window, value=current['panorama_auto'])
    qualities = {height: tk.BooleanVar(window, value=height in current['qualities']) for height in (480,720,1080)}
    top = ttk.Frame(window, padding=12)
    top.pack(fill='x')
    ttk.Label(top, text='Resurser: quiet = tyst, balanced = balanserat, fast = snabbare').pack(anchor='w')
    ttk.Combobox(top, textvariable=profile, values=tuple(PROFILES), state='readonly').pack(anchor='w', pady=5)
    ttk.Checkbutton(top, text='Skapa 360°-visare för bilder med format cirka 2:1 (opt-in)', variable=pano).pack(anchor='w')
    for height, var in qualities.items():
        ttk.Checkbutton(top, text='Extra MP4: %dp (ingen uppskalning)' % height, variable=var).pack(anchor='w')
    ttk.Label(top, text='Översättningar som JSON. Tomt {} = endast ordinarie svenska sidor.\nExempel: {"en":{"title":"Gallery","description":"Welcome","labels":{"Bildspel":"Slideshow"}},"ar":{"dir":"rtl","title":"معرض"}}', wraplength=700).pack(fill='x', pady=8)
    editor_frame = ttk.Frame(window)
    editor_frame.pack(fill='both', expand=True, padx=12)
    editor = tk.Text(editor_frame, wrap='word', height=12, undo=True)
    scroll = ttk.Scrollbar(editor_frame, command=editor.yview)
    scroll.pack(side='right', fill='y')
    editor.configure(yscrollcommand=scroll.set)
    editor.pack(fill='both', expand=True)
    editor.insert('1.0', json.dumps(current['languages'], ensure_ascii=False, indent=2))
    def snapshot():
        return (profile.get(), pano.get(), tuple(v.get() for v in qualities.values()), editor.get('1.0', 'end-1c'))
    original = snapshot()
    window._has_unsaved_changes = lambda: snapshot() != original
    def apply():
        try:
            data = validate({'languages': json.loads(editor.get('1.0','end-1c')), 'panorama_auto': pano.get(),
                             'qualities': [h for h,v in qualities.items() if v.get()], 'resource_profile': profile.get()})
            from resource_profiles import save_profile
            save_profile(profile.get())
            settings.delivery_options = data
            window.destroy()
        except (ValueError, OSError) as exc:
            messagebox.showerror('Ogiltiga inställningar', str(exc), parent=window)
    def close():
        if not window._has_unsaved_changes() or messagebox.askyesno('Osparat', 'Kasta ändringarna?', parent=window):
            window.destroy()
    footer = ttk.Frame(window, padding=12)
    footer.pack(fill='x')
    ttk.Button(footer, text='Använd', command=apply).pack(side='left')
    ttk.Button(footer, text='Avbryt', command=close).pack(side='right')
    window.protocol('WM_DELETE_WINDOW', close)
    return window
