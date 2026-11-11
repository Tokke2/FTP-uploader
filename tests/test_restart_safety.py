import queue
import time
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch
from restart_safety import unsaved_reasons
from release_scheduler import ReleaseScheduler


class RestartSafetyTests(unittest.TestCase):
    def app(self, plugin=None, children=None):
        return SimpleNamespace(plugins={'gallery': plugin} if plugin else {},
            winfo_children=lambda: children or [], _save_all_settings=Mock(), quit_app=Mock(), after=Mock())

    def test_sort_and_rotations_block_restart(self):
        self.assertTrue(unsaved_reasons(self.app(SimpleNamespace(sort_changed=True))))
        self.assertTrue(unsaved_reasons(self.app(SimpleNamespace(image_rotations={'image.jpg': 90}))))

    def test_editor_title_or_text_changes_block_restart(self):
        self.assertTrue(unsaved_reasons(self.app(SimpleNamespace(has_unsaved_changes=lambda: True))))
        self.assertFalse(unsaved_reasons(self.app(SimpleNamespace(has_unsaved_changes=lambda: False))))

    def test_unknown_state_blocks_restart(self):
        plugin = SimpleNamespace(has_unsaved_changes=Mock(side_effect=OSError()))
        self.assertIn('kan inte verifiera', unsaved_reasons(self.app(plugin))[0])

    def test_nested_dialog_provider_blocks_restart(self):
        child = SimpleNamespace(_has_unsaved_changes=lambda: True, winfo_children=lambda: [])
        self.assertTrue(unsaved_reasons(self.app(children=[child])))

    def test_scheduler_keeps_pending_update_without_quitting(self):
        scheduler = ReleaseScheduler.__new__(ReleaseScheduler)
        scheduler.app = self.app(SimpleNamespace(sort_changed=True))
        scheduler.results = queue.Queue()
        scheduler.busy = False
        scheduler.pending = ('v1.0.0', 'a' * 40)
        scheduler.schedule = Mock()
        scheduler.schedule.due.return_value = False
        scheduler.maintenance_pending = False
        with patch('release_scheduler.update_settings', return_value={'mode': 'auto'}), patch('release_scheduler.spawn') as spawn, patch('release_scheduler.log'):
            scheduler.tick()
            spawn.assert_not_called()
        scheduler.app.quit_app.assert_not_called()
        scheduler.app._save_all_settings.assert_not_called()
        self.assertIsNotNone(scheduler.pending)
