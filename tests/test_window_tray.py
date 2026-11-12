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

    def test_legacy_disabled_setting_does_not_override_always_tray(self):
        self.plugin.settings['minimize_to_tray'] = False
        self.handler._check()
        self.plugin.minimize_to_tray.assert_called_once()

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


class MinimizedStartupTests(unittest.TestCase):
    def app(self):
        return SimpleNamespace(_startup_open_requested=False, context={}, _systray_mgr=None,
                               withdraw=Mock(), minimize_startup=Mock(), after=Mock())

    def test_visible_tray_hides_startup_window(self):
        from window_tray import finish_minimized_startup
        app = self.app()
        app.context['_system_tray'] = SimpleNamespace(tray_icon=SimpleNamespace(visible=True))
        finish_minimized_startup(app)
        app.withdraw.assert_called_once()
        app.minimize_startup.assert_not_called()

    def test_missing_tray_minimizes_to_taskbar_after_bounded_wait(self):
        from window_tray import finish_minimized_startup
        app = self.app()
        finish_minimized_startup(app, 25)
        app.minimize_startup.assert_called_once()
        app.withdraw.assert_not_called()
        app.after.assert_not_called()

    def test_second_launch_activation_is_never_hidden_again(self):
        from window_tray import finish_minimized_startup
        app = self.app()
        app._startup_open_requested = True
        finish_minimized_startup(app)
        app.withdraw.assert_not_called()
        app.minimize_startup.assert_not_called()
        app.after.assert_not_called()

    def test_tray_starting_waits_without_opening_window(self):
        from window_tray import finish_minimized_startup
        app = self.app()
        finish_minimized_startup(app)
        app.after.assert_called_once()
        app.minimize_startup.assert_not_called()
        app.withdraw.assert_not_called()


class CloseToTrayTests(unittest.TestCase):
    def app(self, visible=False):
        return SimpleNamespace(context={}, _systray_mgr=SimpleNamespace(_icon=SimpleNamespace(visible=visible)),
                               hide_to_tray=Mock(), iconify=Mock(), deiconify=Mock(), quit_app=Mock())

    def test_close_with_visible_tray_hides_without_exit(self):
        from window_tray import close_to_tray
        app = self.app(True)
        close_to_tray(app)
        app.hide_to_tray.assert_called_once()
        app.quit_app.assert_not_called()
        app.iconify.assert_not_called()

    def test_close_without_tray_minimizes_without_exit(self):
        from window_tray import close_to_tray
        app = self.app(False)
        close_to_tray(app)
        app.iconify.assert_called_once()
        app.hide_to_tray.assert_not_called()
        app.quit_app.assert_not_called()

    def test_unsupported_iconify_keeps_window_visible(self):
        from window_tray import close_to_tray
        app = self.app()
        app.iconify.side_effect = RuntimeError('unsupported')
        close_to_tray(app)
        self.assertEqual(app.deiconify.call_count, 2)
        app.quit_app.assert_not_called()
