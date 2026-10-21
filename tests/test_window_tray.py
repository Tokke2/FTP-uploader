from types import SimpleNamespace
import unittest
from unittest.mock import Mock
from window_tray import MinimizeToTray


class WindowTrayTests(unittest.TestCase):
    def setUp(self):
        self.plugin = SimpleNamespace(settings={}, _tray_running=True,
                                      tray_icon=SimpleNamespace(visible=True),
                                      minimize_to_tray=Mock())
        self.app = SimpleNamespace(context={'_system_tray': self.plugin},
                                   state=Mock(return_value='iconic'), after=Mock(),
                                   hide_to_tray=Mock(), _systray_mgr=None)
        self.handler = MinimizeToTray(self.app)

    def test_minimize_hides_to_tray(self):
        self.handler.on_unmap(SimpleNamespace(widget=self.app))
        self.app.after.call_args.args[1]()
        self.plugin.minimize_to_tray.assert_called_once()

    def test_child_events_ignored(self):
        self.handler.on_unmap(SimpleNamespace(widget=object()))
        self.app.after.assert_not_called()

    def test_withdraw_or_restored_ignored(self):
        for state in ('withdrawn', 'normal', 'zoomed'):
            self.app.state.return_value = state
            self.handler._check()
        self.plugin.minimize_to_tray.assert_not_called()

    def test_invisible_tray_keeps_native_minimize(self):
        self.plugin.tray_icon.visible = False
        self.handler._check()
        self.plugin.minimize_to_tray.assert_not_called()
        self.app.hide_to_tray.assert_not_called()

    def test_setting_disabled(self):
        self.plugin.settings['minimize_to_tray'] = False
        self.handler._check()
        self.plugin.minimize_to_tray.assert_not_called()

    def test_builtin_fallback(self):
        self.app.context.clear()
        self.app._systray_mgr = SimpleNamespace(_icon=SimpleNamespace(visible=True))
        self.handler._check()
        self.app.hide_to_tray.assert_called_once()

    def test_repeated_events_only_schedule_once(self):
        event = SimpleNamespace(widget=self.app)
        self.handler.on_unmap(event)
        self.handler.on_unmap(event)
        self.app.after.assert_called_once()

    def test_no_tray_keeps_window_accessible(self):
        self.app.context.clear()
        self.handler._check()
        self.app.hide_to_tray.assert_not_called()
