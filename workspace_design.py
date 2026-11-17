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
    return max(280, min(1120, width - 40)), max(240, min(820, height - 80))


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
    style = ttk.Style(root)
    style.configure('Studio.TFrame', background=TOKENS['bg'])
    style.configure('Studio.Card.TFrame', background=TOKENS['surface'])
    style.configure('Studio.TLabel', background=TOKENS['surface'], foreground=TOKENS['fg'], padding=4)
    style.configure('Studio.Title.TLabel', background=TOKENS['bg'], foreground=TOKENS['cyan'], font=('TkDefaultFont', 20, 'bold'))
    style.configure('Studio.TButton', padding=(12, 9), font=('TkDefaultFont', 10))
    style.map('Studio.TButton', foreground=[('disabled', '#666666')])
    style.configure('Studio.TPanedwindow', background=TOKENS['border'])
