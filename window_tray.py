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
