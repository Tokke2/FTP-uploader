# Copyright (c) 2026 Rickard Längkvist
"""Best-effort native DPI awareness, called before any Tk root is created."""
import sys


def enable_dpi_awareness(api=None):
    if sys.platform != 'win32' and api is None:
        return 'native'
    try:
        if api is None:
            import ctypes
            api = ctypes.windll
        try:
            if api.user32.SetProcessDpiAwarenessContext(-4):
                return 'per-monitor-v2'
        except (AttributeError, OSError):
            pass
        try:
            if api.shcore.SetProcessDpiAwareness(2) == 0:
                return 'per-monitor'
        except (AttributeError, OSError):
            pass
        try:
            if api.user32.SetProcessDPIAware():
                return 'system'
        except (AttributeError, OSError):
            pass
    except (AttributeError, OSError):
        pass
    return 'existing-or-unavailable'
