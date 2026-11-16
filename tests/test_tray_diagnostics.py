import unittest
from plugins.advanced_logger_diag import _verdict


class TrayDiagnosticTests(unittest.TestCase):
    def test_visible_tray_is_intentionally_hidden(self):
        text, severity = _verdict('withdrawn', False, True, {'visible': True}, True, True)
        self.assertEqual(severity, 1)

    def test_running_tray_without_confirmation_is_not_certainly_unreachable(self):
        text, severity = _verdict('withdrawn', False, True, {'running': True, 'visible': False}, True, True)
        self.assertLess(severity, 4)
        self.assertNotIn('ONÅBAR', text)
