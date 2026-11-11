# Copyright (c) 2026 Rickard Längkvist
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import Mock, patch
import python_discovery as discovery


class DiscoveryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.python = self.root / 'python3'
        self.python.touch()

    def response(self, shared=True):
        return Mock(returncode=0, stdout=json.dumps({'shared': shared, 'tk': 8.6,
                     'version': [3, 13, 1], 'executable': str(self.python)}))

    def test_probe_requires_existing_shared_python_with_tk(self):
        with patch.object(discovery, '_run', return_value=self.response()):
            self.assertEqual(discovery.probe(self.python), self.python)
        with patch.object(discovery, '_run', return_value=self.response(False)):
            self.assertIsNone(discovery.probe(self.python))
        with patch.object(discovery, '_run', return_value=Mock(returncode=1, stdout='')):
            self.assertIsNone(discovery.probe(self.python))

    def test_prefer_first_working_installation_not_latest_other_python(self):
        other = self.root / 'python-other'
        with patch.object(discovery, 'candidates', return_value=iter([self.python, other])), \
             patch.object(discovery, 'probe', return_value=self.python) as probe:
            self.assertEqual(discovery.find_python(), self.python)
            probe.assert_called_once_with(self.python)

    def test_invalid_candidate_is_skipped_and_duplicates_are_not_retried(self):
        other = self.root / 'python-other'
        with patch.object(discovery, 'candidates', return_value=iter([self.python, self.python, other])), \
             patch.object(discovery, 'probe', side_effect=[None, other]) as probe:
            self.assertEqual(discovery.find_python(), other)
            self.assertEqual(probe.call_count, 2)

    def test_no_candidate_does_not_install_anything(self):
        with patch.object(discovery, 'candidates', return_value=iter([])), \
             patch.object(discovery.subprocess, 'Popen') as spawn:
            with self.assertRaises(OSError):
                discovery.find_python()
            spawn.assert_not_called()

    def test_windows_execution_alias_is_never_run(self):
        alias = self.root / 'WindowsApps/python.exe'
        alias.parent.mkdir()
        alias.touch()
        with patch.object(discovery.sys, 'platform', 'win32'), patch.object(discovery, '_run') as run:
            self.assertIsNone(discovery.probe(alias))
            run.assert_not_called()

    def test_windows_console_probe_selects_matching_pythonw(self):
        console = self.root / 'python.exe'
        quiet = self.root / 'pythonw.exe'
        console.touch()
        quiet.touch()
        response = self.response()
        response.stdout = json.dumps({'shared': True, 'tk': 9, 'version': [3, 14, 0], 'executable': str(console)})
        with patch.object(discovery.sys, 'platform', 'win32'), patch.object(discovery, '_run', return_value=response):
            self.assertEqual(discovery.probe(quiet), quiet)

    def test_relaunch_preserves_flags_and_clears_environment_overrides(self):
        entry = self.root / 'start.pyw'
        with patch.object(discovery, 'find_python', return_value=self.python), \
             patch.object(discovery.sys, 'executable', str(self.root / 'venv/python')), \
             patch.object(discovery.sys, 'argv', ['start.pyw', '--show']), \
             patch.dict(discovery.os.environ, {'PYTHONPATH': '/other', 'VIRTUAL_ENV': '/venv'}), \
             patch.object(discovery.subprocess, 'Popen') as spawn:
            spawn.return_value.wait.side_effect = subprocess.TimeoutExpired('python', 1)
            with self.assertRaises(SystemExit):
                discovery.select_for_start(entry)
            args = spawn.call_args
            self.assertEqual(args.args[0], [str(self.python), str(entry), '--show'])
            self.assertNotIn('VIRTUAL_ENV', args.kwargs['env'])
            self.assertNotIn('PYTHONPATH', args.kwargs['env'])

    def test_running_selected_python_does_not_restart(self):
        with patch.object(discovery, 'find_python', return_value=self.python), \
             patch.object(discovery.sys, 'executable', str(self.python)), \
             patch.object(discovery.subprocess, 'Popen') as spawn:
            discovery.select_for_start(self.root / 'main.pyw')
            spawn.assert_not_called()

    def test_probe_timeout_is_safe(self):
        with patch.object(discovery, '_run', side_effect=subprocess.TimeoutExpired('python', 5)):
            self.assertIsNone(discovery.probe(self.python))
