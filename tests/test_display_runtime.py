from types import SimpleNamespace
from unittest.mock import Mock
import unittest
from display_runtime import enable_dpi_awareness


class DisplayRuntimeTests(unittest.TestCase):
    def test_modern_windows_uses_monitor_awareness(self):
        api=SimpleNamespace(user32=SimpleNamespace(SetProcessDpiAwarenessContext=Mock(return_value=1)))
        self.assertEqual(enable_dpi_awareness(api),'per-monitor-v2')
        api.user32.SetProcessDpiAwarenessContext.assert_called_once_with(-4)

    def test_old_windows_falls_back(self):
        api=SimpleNamespace(user32=SimpleNamespace(SetProcessDPIAware=Mock(return_value=1)))
        self.assertEqual(enable_dpi_awareness(api),'system')

    def test_already_configured_or_unsupported_is_safe(self):
        self.assertEqual(enable_dpi_awareness(SimpleNamespace()),'existing-or-unavailable')
