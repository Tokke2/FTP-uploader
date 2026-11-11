from datetime import datetime
from pathlib import Path
import tempfile
import unittest
from weekly_schedule import WeeklySchedule, next_monday


class ScheduleTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / 'schedule.json'

    def test_first_start_schedules_future_monday_not_immediate_check(self):
        schedule = WeeklySchedule(self.path)
        now = datetime(2026, 11, 5, 10).timestamp()
        self.assertFalse(schedule.due('release', now))
        self.assertEqual(datetime.fromtimestamp(schedule.tasks['release']), datetime(2026, 11, 9, 8))

    def test_before_at_and_after_monday_eight(self):
        schedule = WeeklySchedule(self.path)
        schedule.due('release', datetime(2026, 11, 8, 12).timestamp())
        self.assertFalse(schedule.due('release', datetime(2026, 11, 9, 7, 59, 59).timestamp()))
        self.assertTrue(schedule.due('release', datetime(2026, 11, 9, 8).timestamp()))
        schedule.complete('release', datetime(2026, 11, 9, 8).timestamp())
        self.assertFalse(schedule.due('release', datetime(2026, 11, 9, 9).timestamp()))

    def test_restart_preserves_schedule(self):
        schedule = WeeklySchedule(self.path)
        schedule.due('python-and-packages', datetime(2026, 11, 5, 10).timestamp())
        restored = WeeklySchedule(self.path)
        self.assertFalse(restored.due('python-and-packages', datetime(2026, 11, 6, 10).timestamp()))

    def test_missed_monday_runs_once_then_next_monday(self):
        schedule = WeeklySchedule(self.path)
        schedule.due('release', datetime(2026, 11, 5, 10).timestamp())
        tuesday = datetime(2026, 11, 10, 11).timestamp()
        self.assertTrue(schedule.due('release', tuesday))
        schedule.complete('release', tuesday)
        self.assertEqual(datetime.fromtimestamp(schedule.tasks['release']), datetime(2026, 11, 16, 8))
        self.assertFalse(schedule.due('release', tuesday))

    def test_exact_boundary_next_occurrence(self):
        self.assertEqual(datetime.fromtimestamp(next_monday(datetime(2026, 11, 9, 8))), datetime(2026, 11, 16, 8))

    def test_weekly_helper_runs_python_and_dependencies_without_release(self):
        from unittest.mock import patch
        import release_scheduler
        with patch('socket.socket'), patch('release_scheduler.log'), patch('release_scheduler.spawn') as spawn, patch('runtime_startup.maintain_runtime', return_value=False) as python, patch('ensure_deps.ensure_requirements', return_value=True) as dependencies, patch('auto_update.apply_release') as release, patch.dict('os.environ', {}, clear=False):
            release_scheduler.restart('/app', '-', '-', maintenance=True)
            python.assert_called_once()
            dependencies.assert_called_once_with(Path('/app'))
            release.assert_not_called()
            spawn.assert_called_once()
