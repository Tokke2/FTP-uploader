# Copyright (c) 2026 Rickard Längkvist
"""Convert native window minimization to tray hiding, only with a usable icon."""


class MinimizeToTray:
    def __init__(self, app):
        self.app = app
        self.pending = False

    def on_unmap(self, event):
        # Tk also reports Unmap for child widgets and withdraw().
        if event.widget is not self.app or self.pending:
            return
        self.pending = True
        self.app.after(150, self._check)

    def _check(self):
        self.pending = False
        try:
            if self.app.state() != 'iconic':
                return
            plugin = self.app.context.get('_system_tray')
            if plugin is not None:
                if not plugin.settings.get('minimize_to_tray', True):
                    return
                icon = plugin.tray_icon
                if plugin._tray_running and icon is not None and icon.visible:
                    plugin.minimize_to_tray()
                return
            # Also works with the built-in tray when the plugin is disabled.
            manager = self.app._systray_mgr
            icon = getattr(manager, '_icon', None)
            if icon is not None and icon.visible:
                self.app.hide_to_tray()
        except Exception:
            # Missing/unsupported tray: leave native minimization intact.
            return


def finish_minimized_startup(app, attempt=0):
    """Wait for a visible tray, otherwise leave a minimized taskbar window."""
    if getattr(app, '_startup_open_requested', False):
        return
    plugin = app.context.get('_system_tray')
    manager = getattr(app, '_systray_mgr', None)
    for owner in (plugin, manager):
        if owner is None:
            continue
        icon = getattr(owner, 'tray_icon', None) or getattr(owner, '_icon', None)
        try:
            if icon is not None and icon.visible:
                app.withdraw()
                return
        except Exception:
            pass
    if attempt >= 25:
        app.minimize_startup()
    else:
        app.after(200, lambda: finish_minimized_startup(app, attempt + 1))
