# Copyright (c) 2026 Rickard Längkvist
"""Validated gallery styling and an illustrative, live desktop preview."""
from workspace_design import bounded_int

DEFAULTS = {'gap': 16, 'radius': 14, 'font_size': 16, 'aspect': '4/3', 'fit': 'cover'}


def options(value=None):
    value = value if isinstance(value, dict) else {}
    return {'gap': bounded_int(value.get('gap', 16), 16, 0, 48),
            'radius': bounded_int(value.get('radius', 14), 14, 0, 40),
            'font_size': bounded_int(value.get('font_size', 16), 16, 12, 24),
            'aspect': value.get('aspect') if value.get('aspect') in ('4/3', '1/1', '16/9', '3/4') else '4/3',
            'fit': value.get('fit') if value.get('fit') in ('cover', 'contain') else 'cover'}


def css(value):
    o = options(value)
    return ('.gallery{gap:%dpx}.card,.vcard{border-radius:%dpx}'
            'body{font-size:%dpx}.card img{aspect-ratio:%s;object-fit:%s}' %
            (o['gap'], o['radius'], o['font_size'], o['aspect'], o['fit']))


def open_designer(app, settings):
    import tkinter as tk
    from tkinter import ttk, messagebox
    from workspace_design import TOKENS, apply_styles, window_size
    apply_styles(app)
    window = tk.Toplevel(app)
    window.title('Visuell gallerilayout')
    width, height = window_size(app.winfo_screenwidth(), app.winfo_screenheight())
    window.geometry('%dx%d' % (min(900, width), min(700, height)))
    window.minsize(min(380, width), min(400, height))
    initial = options(getattr(settings, 'layout_options', None))
    variables = {key: tk.StringVar(window, value=str(value)) for key, value in initial.items()}
    columns = tk.StringVar(window, value=str(settings.cols_var.get()))
    device = tk.StringVar(window, value='Dator')
    controls = ttk.Frame(window, padding=10)
    controls.pack(fill='x')
    fields = [('Mellanrum', 'gap'), ('Hörnradie', 'radius'), ('Textstorlek', 'font_size')]
    for row, (label, key) in enumerate(fields):
        ttk.Label(controls, text=label).grid(row=row, column=0, sticky='w', padx=4, pady=3)
        limit = {'gap': 48, 'radius': 40, 'font_size': 24}[key]
        ttk.Spinbox(controls, from_=12 if key == 'font_size' else 0, to=limit,
                    textvariable=variables[key], width=8).grid(row=row, column=1, sticky='w')
    for row, (label, key, choices) in enumerate([
            ('Bildformat', 'aspect', ('4/3', '1/1', '16/9', '3/4')),
            ('Bildanpassning', 'fit', ('cover', 'contain'))], 3):
        ttk.Label(controls, text=label).grid(row=row, column=0, sticky='w', padx=4, pady=3)
        ttk.Combobox(controls, textvariable=variables[key], values=choices, state='readonly', width=10).grid(row=row, column=1, sticky='w')
    ttk.Label(controls, text='Kolumner (dator)').grid(row=5, column=0, sticky='w', padx=4)
    ttk.Spinbox(controls, from_=2, to=12, textvariable=columns, width=8).grid(row=5, column=1, sticky='w')
    ttk.Combobox(controls, textvariable=device, values=('Dator', 'Surfplatta', 'Mobil'), state='readonly', width=14).grid(row=6, column=0, pady=6)
    ttk.Label(window, text='Schematisk liveförhandsvisning – öppna exporterad HTML för exakt webbläsarvisning.', wraplength=600).pack(fill='x', padx=14)
    preview_frame = ttk.Frame(window)
    preview_frame.pack(fill='both', expand=True, padx=12, pady=8)
    preview = tk.Canvas(preview_frame, bg=TOKENS['bg'], highlightthickness=0, height=240)
    scroll = ttk.Scrollbar(preview_frame, command=preview.yview)
    scroll.pack(side='right', fill='y')
    preview.configure(yscrollcommand=scroll.set)
    preview.pack(side='left', fill='both', expand=True)
    def snapshot():
        return tuple(variable.get() for variable in variables.values()) + (columns.get(),)
    original = snapshot()
    window._has_unsaved_changes = lambda: snapshot() != original
    def draw(*_):
        preview.delete('all')
        o = options({key: var.get() for key, var in variables.items()})
        available = max(120, preview.winfo_width() - 24)
        width = min(available, {'Dator': 1000, 'Surfplatta': 700, 'Mobil': 340}[device.get()])
        count = bounded_int(columns.get(), 6, 2, 12)
        count = min(count, 2 if width <= 600 else 4 if width <= 900 else 12)
        if width <= 380:
            count = 1
        gap = o['gap'] * 0.5
        cell = max(10, (width - (count - 1) * gap) / count)
        a, b = map(int, o['aspect'].split('/'))
        height = cell * b / a
        for i in range(count * 2):
            x, y = 12 + i % count * (cell + gap), 12 + i // count * (height + gap + 26)
            r = min(o['radius'], cell / 3, height / 3)
            preview.create_polygon(x+r,y,x+cell-r,y,x+cell,y+r,x+cell,y+height-r,
                                   x+cell-r,y+height,x+r,y+height,x,y+height-r,x,y+r,
                                   smooth=True, fill=TOKENS['surface'], outline=TOKENS['cyan'])
            if o['fit'] == 'contain':
                preview.create_rectangle(x+cell*0.15, y+height*0.15, x+cell*0.85, y+height*0.85, outline=TOKENS['violet'])
            preview.create_text(x+cell/2, y+height/2, text='Bild %d' % (i+1), fill=TOKENS['fg'], font=('TkDefaultFont', o['font_size']))
        preview.configure(scrollregion=(0, 0, available+24, 36 + 2*(height+gap+26)))
    for variable in [*variables.values(), columns, device]:
        variable.trace_add('write', draw)
    preview.bind('<Configure>', draw)
    def apply():
        settings.layout_options = options({key: var.get() for key, var in variables.items()})
        settings.cols_var.set(bounded_int(columns.get(), 6, 2, 12))
        # Keep the owner's ordinary save/dirty flow; do not save unrelated edits.
        window.destroy()
    def close():
        if not window._has_unsaved_changes() or messagebox.askyesno('Osparad layout', 'Kasta layoutändringarna?', parent=window):
            window.destroy()
    buttons = ttk.Frame(window, padding=10)
    buttons.pack(fill='x')
    ttk.Button(buttons, text='Använd i projektet', command=apply, style='Studio.TButton').pack(side='left')
    ttk.Button(buttons, text='Avbryt', command=close, style='Studio.TButton').pack(side='right')
    window.protocol('WM_DELETE_WINDOW', close)
    return window
