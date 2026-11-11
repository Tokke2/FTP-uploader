from types import SimpleNamespace
import unittest
from unittest.mock import patch
import runtime_startup as startup


class RuntimeStartupTests(unittest.TestCase):
    def setUp(self):
        self.patches = [patch('runtime_startup.log'), patch('runtime_startup.socket.socket'),
                        patch.dict(startup.os.environ, {startup.SKIP_ONCE: '0'})]
        for item in self.patches:
            item.start()
            self.addCleanup(item.stop)
        self.plan = SimpleNamespace(installed=(3, 13, 1), latest=(3, 13, 2), reason='existing', command=('manager', 'upgrade'))

    def test_every_user_start_checks_existing_python(self):
        self.plan.command = ()
        with patch('runtime_startup.inspect_runtime', return_value=self.plan) as inspect, patch('runtime_startup.execute_upgrade') as upgrade:
            self.assertFalse(startup.maintain_runtime())
            self.assertFalse(startup.maintain_runtime())
            self.assertEqual(inspect.call_count, 2)
            upgrade.assert_not_called()

    def test_available_upgrade_runs_before_restart(self):
        with patch('runtime_startup.inspect_runtime', return_value=self.plan), patch('runtime_startup.execute_upgrade', return_value='upgraded') as upgrade:
            self.assertTrue(startup.maintain_runtime())
            upgrade.assert_called_once_with(self.plan)

    def test_failed_check_continues_with_installed_python(self):
        with patch('runtime_startup.inspect_runtime', side_effect=OSError('offline')):
            self.assertFalse(startup.maintain_runtime())

    def test_verified_restart_skips_exactly_once(self):
        with patch.dict(startup.os.environ, {startup.SKIP_ONCE: '1'}), patch('runtime_startup.inspect_runtime', return_value=self.plan) as inspect:
            self.assertFalse(startup.maintain_runtime())
            inspect.assert_not_called()
            self.assertNotIn(startup.SKIP_ONCE, startup.os.environ)

    def test_restart_uses_installed_python_not_virtual_environment(self):
        with patch('release_scheduler.python_executable', return_value='/installed/python'), patch('release_scheduler.spawn') as spawn:
            with self.assertRaises(SystemExit):
                startup.restart_with_updated_python('/app')
            command = spawn.call_args.args[0]
            self.assertEqual(command[:2], ['/installed/python', '/app/start.pyw'])
            self.assertEqual(spawn.call_args.kwargs['env'][startup.SKIP_ONCE], '1')
