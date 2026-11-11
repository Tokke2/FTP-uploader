# Copyright (c) 2026 Rickard Längkvist
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch
import event_log


class EventLogTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)
        change = patch.object(event_log, '_directory', self.folder)
        change.start()
        self.addCleanup(change.stop)

    def records(self):
        result = []
        for path in self.folder.glob('*.log*'):
            for line in path.read_text().splitlines():
                result.append(json.loads(line[line.index('{'):]))
        return result

    def test_session_job_thread_and_redacted_fields(self):
        token = event_log.JOB.set('job-123')
        try:
            event_log.emit('test', password='secret-value', nested={'api_key': 'api-secret'},
                           message='https://user:pass@example.se/?token=token-secret')
        finally:
            event_log.JOB.reset(token)
        raw = '\n'.join(path.read_text() for path in self.folder.glob('*'))
        for secret in ('secret-value', 'api-secret', 'token-secret', 'user:pass'):
            self.assertNotIn(secret, raw)
        data = self.records()[0]
        self.assertEqual(data['job'], 'job-123')
        self.assertEqual(data['session'], event_log.SESSION)
        self.assertIn('thread', data)

    def test_stream_split_writes_and_flush_are_captured_and_masked(self):
        original = io.StringIO()
        stream = event_log.CapturedStream(original, 'stderr')
        stream.write('password=')
        stream.write('never-save-this\n')
        stream.write('last partial')
        stream.flush()
        self.assertNotIn('never-save-this', original.getvalue())
        self.assertEqual(len(self.records()), 2)
        self.assertTrue(all(record['level'] == 'ERROR' for record in self.records()))

    def test_parallel_writes_are_complete_json_records(self):
        threads = [threading.Thread(target=lambda: [event_log.emit('parallel', number=n) for n in range(20)]) for _ in range(4)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        self.assertEqual(len(self.records()), 80)

    def test_rotation_preserves_todays_records(self):
        with patch.object(event_log, 'MAX_BYTES', 1):
            event_log.emit('one')
            event_log.emit('two')
        self.assertEqual(len(self.records()), 2)
        self.assertEqual(len(list(self.folder.glob('*.log*'))), 2)

    def test_python_logging_and_warnings_in_real_process(self):
        root = Path(__file__).resolve().parents[1]
        script = ('import logging,warnings;from event_log import install;install(%r);'
                  'logging.warning("library-warning");warnings.warn("runtime-warning",RuntimeWarning);'
                  'print("stdout-line")') % str(self.folder)
        result = subprocess.run([sys.executable, '-c', script], cwd=root, capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        raw = '\n'.join(path.read_text() for path in (self.folder / 'logs').glob('*.log*'))
        for expected in ('python.logging', 'python.warning', 'stdout-line', 'session.exit'):
            self.assertIn(expected, raw)

    def test_background_exception_in_real_process(self):
        root = Path(__file__).resolve().parents[1]
        script = ('import threading;from event_log import install;install(%r);'
                  't=threading.Thread(target=lambda:1/0);t.start();t.join()') % str(self.folder)
        result = subprocess.run([sys.executable, '-c', script], cwd=root, capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0)
        raw = '\n'.join(path.read_text() for path in (self.folder / 'logs').glob('*.log*'))
        self.assertIn('thread.exception', raw)
        self.assertIn('ZeroDivisionError', raw)

    def test_unraisable_destructor_exception_is_recorded(self):
        root = Path(__file__).resolve().parents[1]
        script = ('from event_log import install;install(%r)\n'
                  'class Broken:\n def __del__(self): raise ValueError("destructor-error")\n'
                  'x=Broken();del x\n') % str(self.folder)
        result = subprocess.run([sys.executable, '-c', script], cwd=root, capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0)
        raw = '\n'.join(path.read_text() for path in (self.folder / 'logs').glob('*.log*'))
        self.assertIn('python.unraisable', raw)
        self.assertIn('destructor-error', raw)

    def test_process_audit_never_stores_command_arguments_or_environment(self):
        root = Path(__file__).resolve().parents[1]
        script = ('import subprocess,sys,os;from event_log import install;install(%r);'
                  'env=os.environ.copy();env["MY_SECRET"]="environment-secret";'
                  'subprocess.run([sys.executable,"-c","pass","command-secret"],env=env)') % str(self.folder)
        result = subprocess.run([sys.executable, '-c', script], cwd=root, capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0)
        raw = '\n'.join(path.read_text() for path in (self.folder / 'logs').glob('*.log*'))
        self.assertIn('process.spawn', raw)
        self.assertNotIn('command-secret', raw)
        self.assertNotIn('environment-secret', raw)

    def test_tk_messagebox_is_logged_without_saving_password(self):
        import types
        fake = types.ModuleType('tkinter')
        fake.messagebox = types.SimpleNamespace(_show=lambda *args, **kwargs: 'ok')
        with patch.dict(sys.modules, {'tkinter': fake}):
            event_log.install_dialog_capture()
            self.assertEqual(fake.messagebox._show('Fel', 'password=super-secret', 'error'), 'ok')
        records = self.records()
        self.assertEqual(records[0]['event'], 'ui.messagebox')
        self.assertEqual(records[0]['level'], 'ERROR')
        self.assertNotIn('super-secret', str(records))

    def test_ui_pulse_and_destroy_are_logged_without_reading_inputs(self):
        from types import SimpleNamespace
        from unittest.mock import Mock
        app = SimpleNamespace(bind=Mock(), bind_all=Mock(), after=Mock(), state=Mock(return_value='withdrawn'))
        with patch.object(event_log.time, 'monotonic', return_value=100):
            event_log.attach_ui(app)
            pulse = app.after.call_args.args[1]
            pulse()
            destroy = app.bind.call_args_list[0].args[1]
            destroy(SimpleNamespace(widget=app))
        events = [record['event'] for record in self.records()]
        self.assertIn('ui.heartbeat', events)
        self.assertIn('ui.destroy', events)
        app.state.assert_called_once()
