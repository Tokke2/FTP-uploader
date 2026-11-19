# Copyright (c) 2026 Rickard Längkvist
"""Shared desktop tokens and bounded, screen-aware layout helpers."""
import json
import os
from pathlib import Path

TOKENS = {'bg': '#101827', 'surface': '#192538', 'fg': '#f1f5f9', 'muted': '#b8c6d9',
          'cyan': '#67e8f9', 'violet': '#c4b5fd', 'pink': '#f9a8d4', 'border': '#3c506b'}


def bounded_int(value, default, low, high):
    try:
        return max(low, min(high, int(float(value))))
    except (ValueError, TypeError, OverflowError):
        return default


def window_size(width, height):
    return max(280, min(1760, width - 40)), max(240, min(1100, height - 80))


def pane_orientation(width):
    return 'vertical' if width < 820 else 'horizontal'


def load_state(path):
    try:
        value = json.loads(Path(path).read_text(encoding='utf-8'))
        return value if isinstance(value, dict) else {}
    except (OSError, ValueError):
        return {}


def save_state(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix('.tmp')
    try:
        with temporary.open('w', encoding='utf-8') as stream:
            json.dump(value, stream)
            stream.flush()
            os.fsync(stream.fileno())
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def apply_styles(root):
    from tkinter import ttk
    colors = palette(root)
    family = setup_fonts(root)
    style = ttk.Style(root)
    style.configure('Studio.TFrame', background=colors['bg'])
    style.configure('Studio.Card.TFrame', background=colors['surface'])
    style.configure('Studio.TLabel', background=colors['surface'], foreground=colors['fg'], padding=4)
    style.configure('Studio.Title.TLabel', background=colors['bg'], foreground=colors['cyan'], font=(family, 23, 'bold'))
    style.configure('Studio.TButton', padding=(12, 9), font=(family, 11))
    style.map('Studio.TButton', foreground=[('disabled', '#666666')])
    style.configure('Studio.TPanedwindow', background=colors['border'])


def preferred_font(available):
    """Use installed UI fonts; never download fonts or change DPI scaling."""
    lookup = {name.casefold(): name for name in available}
    for name in ('Segoe UI Variable', 'Segoe UI', 'SF Pro Text', 'Inter', 'Noto Sans', 'DejaVu Sans'):
        if name.casefold() in lookup:
            return lookup[name.casefold()]
    return 'TkDefaultFont'


def setup_fonts(root):
    from tkinter import font
    family = preferred_font(font.families(root))
    for name in ('TkDefaultFont', 'TkTextFont', 'TkMenuFont', 'TkHeadingFont', 'TkCaptionFont'):
        font.nametofont(name, root=root).configure(family=family, size=11)
    return family


def palette(root):
    engine = getattr(root, 'theme_engine', None)
    if engine is None:
        return dict(TOKENS)
    colors = dict(TOKENS)
    for key, source in {'bg':'bg', 'surface':'surface', 'fg':'fg', 'muted':'text_secondary',
                        'cyan':'accent', 'border':'border'}.items():
        colors[key] = engine.get_color(source, colors[key])
    return colors


def navigation_icon(root, kind, color):
    """Small raster line icons independent of emoji/font availability."""
    import tkinter as tk
    image = tk.PhotoImage(master=root, width=20, height=20)
    shapes = {
        'workspace': [(3,4,17,6),(3,9,8,17),(10,9,17,11),(10,14,17,17)],
        'settings': [(2,6,18,8),(4,3,10,6),(2,8,4,17),(4,15,18,17),(16,8,18,17)],
        'gallery': [(2,3,18,5),(2,5,4,17),(16,5,18,17),(4,15,16,17),(6,9,9,12),(10,7,14,11)],
        'designer': [(3,3,17,5),(3,9,17,11),(3,15,17,17),(6,2,9,7),(12,8,15,13),(5,14,8,19)],
        'controls': [(9,2,11,15),(6,5,14,7),(4,13,6,18),(14,13,16,18),(4,17,16,19)]}
    for rect in shapes[kind]:
        image.put(color, to=rect)
    return image
