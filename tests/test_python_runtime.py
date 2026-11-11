import io
import json
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import patch
import python_runtime as runtime


class PythonRuntimeTests(unittest.TestCase):
    def result(self, text='', code=0):
        return SimpleNamespace(stdout=text, returncode=code)

    def test_latest_excludes_prereleases(self):
        tags = [{'ref': 'refs/tags/v3.13.9'}, {'ref': 'refs/tags/v3.14.0'},
                {'ref': 'refs/tags/v3.15.0a1'}, {'ref': 'refs/tags/v3.14.1rc1'}]
        with patch('python_runtime.urllib.request.urlopen', return_value=io.BytesIO(json.dumps(tags).encode())):
            self.assertEqual(runtime.latest_python(), (3, 14, 0))

    def test_up_to_date_never_invokes_manager(self):
        with patch.object(runtime.sys, 'version_info', (3, 13, 9)), patch.object(runtime, 'run') as run:
            self.assertFalse(runtime.inspect_runtime((3, 13, 9)).command)
            run.assert_not_called()

    def test_new_series_never_installs_parallel_python(self):
        with patch.object(runtime.sys, 'version_info', (3, 13, 9)), patch.object(runtime, 'run') as run:
            plan = runtime.inspect_runtime((3, 14, 0))
            self.assertFalse(plan.command)
            self.assertIn('parallell', plan.reason)
            run.assert_not_called()

    def test_windows_only_upgrades_existing_identified_package(self):
        with patch.object(runtime.sys, 'version_info', (3, 13, 1)), patch.object(runtime.sys, 'platform', 'win32'), patch.object(runtime, 'windows_registered_here', return_value=True), patch.object(runtime.shutil, 'which', return_value='/tools/winget'), patch.object(runtime, 'run', return_value=self.result('Python.Python.3.13')):
            command = runtime.inspect_runtime((3, 13, 2)).command
            self.assertIn('upgrade', command)
            self.assertNotIn('install', command)
            self.assertIn('Python.Python.3.13', command)

    def test_windows_unidentified_installation_has_no_install_fallback(self):
        with patch.object(runtime.sys, 'version_info', (3, 13, 1)), patch.object(runtime.sys, 'platform', 'win32'), patch.object(runtime, 'windows_registered_here', return_value=False), patch.object(runtime, 'run') as run:
            self.assertFalse(runtime.inspect_runtime((3, 13, 2)).command)
            run.assert_not_called()

    def test_linux_uses_only_upgrade_for_owned_package(self):
        with patch.object(runtime.sys, 'version_info', (3, 13, 1)), patch.object(runtime.sys, 'platform', 'linux'), patch.object(runtime.shutil, 'which', side_effect=lambda name: '/tools/' + name), patch.object(runtime.os, 'geteuid', return_value=0), patch.object(runtime, 'run', side_effect=[self.result('python3.13-minimal: /usr/bin/python3.13'), self.result('Candidate: 3.13.2-1')]):
            command = runtime.inspect_runtime((3, 13, 2)).command
            self.assertIn('--only-upgrade', command)
            self.assertIn('python3.13', command)

    def test_linux_repository_too_old_does_not_replace_system_python(self):
        with patch.object(runtime.sys, 'version_info', (3, 13, 1)), patch.object(runtime.sys, 'platform', 'linux'), patch.object(runtime.shutil, 'which', return_value='/tools/manager'), patch.object(runtime, 'run', side_effect=[self.result('python3.13-minimal: /usr/bin/python3.13'), self.result('Candidate: 3.13.1-1')]):
            self.assertFalse(runtime.inspect_runtime((3, 13, 2)).command)

    def test_macos_upgrades_only_owning_formula(self):
        with tempfile.TemporaryDirectory() as folder:
            executable = Path(folder) / 'bin/python3.13'
            with patch.object(runtime.sys, 'version_info', (3, 13, 1)), patch.object(runtime.sys, 'platform', 'darwin'), patch.object(runtime.sys, 'executable', str(executable)), patch.object(runtime.shutil, 'which', return_value='/tools/brew'), patch.object(runtime, 'run', return_value=self.result(folder)):
                self.assertEqual(runtime.inspect_runtime((3, 13, 2)).command, ('/tools/brew', 'upgrade', 'python'))

    def test_failed_upgrade_never_attempts_install(self):
        plan = runtime.RuntimePlan((3, 13, 1), (3, 13, 2), '/python', ('manager', 'upgrade'))
        with tempfile.TemporaryDirectory() as folder, patch.object(runtime, 'inspect_runtime', return_value=plan), patch.object(runtime, 'logs_dir', return_value=Path(folder)), patch.object(runtime, 'run', return_value=self.result('failed', 1)) as run:
            with self.assertRaises(RuntimeError):
                runtime.execute_upgrade(plan)
            run.assert_called_once_with(plan.command, timeout=900)

    def test_changed_plan_is_not_executed(self):
        plan = runtime.RuntimePlan((3, 13, 1), (3, 13, 2), '/python', ('manager', 'upgrade'))
        with patch.object(runtime, 'inspect_runtime', return_value=None), patch.object(runtime, 'run') as run:
            with self.assertRaisesRegex(RuntimeError, 'ändrats'):
                runtime.execute_upgrade(plan)
            run.assert_not_called()
