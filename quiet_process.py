# Copyright (c) 2026 Rickard Längkvist
"""Subprocess facade: Windows console children never allocate a console window.

Do not monkey-patch Python's subprocess module or hide the user's terminal.
GUI programs intentionally opened by the user keep their normal windows.
"""
import subprocess as _subprocess
import sys


def hidden_options(options):
    options = dict(options)
    if sys.platform == 'win32':
        no_window = getattr(_subprocess, 'CREATE_NO_WINDOW', 0x08000000)
        new_console = getattr(_subprocess, 'CREATE_NEW_CONSOLE', 0x00000010)
        options['creationflags'] = (options.get('creationflags', 0) & ~new_console) | no_window
    return options


def Popen(*args, **kwargs):
    return _subprocess.Popen(*args, **hidden_options(kwargs))


def run(*args, **kwargs):
    return _subprocess.run(*args, **hidden_options(kwargs))


def check_output(*args, **kwargs):
    return _subprocess.check_output(*args, **hidden_options(kwargs))


def check_call(*args, **kwargs):
    return _subprocess.check_call(*args, **hidden_options(kwargs))


def call(*args, **kwargs):
    return _subprocess.call(*args, **hidden_options(kwargs))


def __getattr__(name):
    return getattr(_subprocess, name)
