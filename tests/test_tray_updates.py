from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch
import auto_update


class TrayUpdatesTests(unittest.TestCase):
    def test_dispatches_manual_check_on_tk_thread(self):
        app = SimpleNamespace(after=Mock())
        with patch('auto_update.check_before_start') as check:
            auto_update.request_from_tray(app)
            check.assert_not_called()
            delay, callback = app.after.call_args.args
            self.assertEqual(delay, 0)
            callback()
            check.assert_called_once_with(Path(auto_update.__file__).resolve().parent,
                                          parent=app, manual=True)
