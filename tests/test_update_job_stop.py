from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import Mock

from restart_safety import request_job_stop, active_job_reasons


class UpdateJobStopTests(unittest.TestCase):
    def test_stop_sets_cancel_without_faking_idle_or_discarding_edits(self):
        worker = SimpleNamespace(processing=True, cancel_requested=False, paused=True, sort_changed=True)
        app = SimpleNamespace(context={}, plugins={'video': worker}, _pipeline_busy=1)
        request_job_stop(app)
        self.assertTrue(worker.cancel_requested)
        self.assertFalse(worker.paused)
        self.assertTrue(worker.processing)
        self.assertTrue(worker.sort_changed)
        self.assertTrue(app.context['cancel_check']())
        self.assertTrue(active_job_reasons(app))

    def test_repeated_stop_preserves_original_check_without_recursion(self):
        previous = Mock(return_value=True)
        app = SimpleNamespace(context={'cancel_check': previous}, plugins={})
        for _ in range(10):
            request_job_stop(app)
        app._update_stop_event.clear()
        self.assertTrue(app.context['cancel_check']())
        previous.assert_called_once()

    def test_cancelled_gallery_conversion_preserves_existing_output(self):
        from media_support import video_to_web_mp4
        with tempfile.TemporaryDirectory() as folder:
            source, output = Path(folder) / 'original.mov', Path(folder) / 'export.mp4'
            source.write_bytes(b'original')
            output.write_bytes(b'old valid output')
            with self.assertRaisesRegex(RuntimeError, 'avbruten'):
                video_to_web_mp4(source, output, 'unused-ffmpeg', cancelled=lambda: True)
            self.assertEqual(source.read_bytes(), b'original')
            self.assertEqual(output.read_bytes(), b'old valid output')
            self.assertEqual(len(list(Path(folder).iterdir())), 2)

    def test_in_app_install_reuses_existing_instance_guard_after_stop(self):
        from auto_update import apply_release
        from unittest.mock import patch
        app = SimpleNamespace(context={}, plugins={}, _release_update_active=True)
        request_job_stop(app)
        with patch('auto_update._install_release', return_value='OK') as install, patch('socket.socket') as socket:
            self.assertEqual(apply_release('/app', ('v1.0.0', 'a' * 40), running_app=app), 'OK')
            install.assert_called_once()
            socket.assert_not_called()

    def test_in_app_install_cannot_skip_active_jobs_or_stop_guard(self):
        from auto_update import apply_release
        from unittest.mock import patch
        app = SimpleNamespace(context={}, plugins={}, _release_update_active=True, _pipeline_busy=1)
        with patch('auto_update._install_release') as install:
            with self.assertRaises(RuntimeError):
                apply_release('/app', ('v1.0.0', 'a' * 40), running_app=app)
            request_job_stop(app)
            with self.assertRaisesRegex(RuntimeError, 'jobb avslutas'):
                apply_release('/app', ('v1.0.0', 'a' * 40), running_app=app)
            install.assert_not_called()

    def test_external_installer_still_rejects_running_app(self):
        from auto_update import apply_release
        from unittest.mock import patch
        with patch('socket.socket') as socket, patch('auto_update._install_release') as install:
            socket.return_value.__enter__.return_value.bind.side_effect = OSError('in use')
            with self.assertRaisesRegex(RuntimeError, 'Appen körs redan'):
                apply_release('/app', ('v1.0.0', 'a' * 40))
            install.assert_not_called()
