# Copyright (c) 2026 Rickard Längkvist
from types import SimpleNamespace
import threading
import unittest
from unittest.mock import Mock
from tray_status import TrayStatus, status_text


class TrayStatusTests(unittest.TestCase):
    def test_ready_progress_stage_and_success(self):
        status = TrayStatus()
        self.assertEqual(status.text(), 'Redo')
        token = status.begin()
        status.stage('Bearbetar')
        status.progress(12, 80)
        self.assertEqual(status.text(), 'Bearbetar 12/80')
        status.stage('HTML-generator')
        self.assertEqual(status.text(), 'HTML-generator')
        status.finish(token)
        self.assertEqual(status.text(), 'Redo')

    def test_failed_job_stays_visible_until_next_job(self):
        status = TrayStatus()
        token = status.begin()
        status.finish(token, failed=True)
        self.assertEqual(status.text(), 'Fel – se felloggen')
        token = status.begin()
        status.finish(token)
        self.assertEqual(status.text(), 'Redo')

    def test_partial_errors_and_cancellation_are_not_reported_as_success(self):
        for action, expected in [('issue', 'Fel – se felloggen'), ('cancelled', 'Avbrutet')]:
            status = TrayStatus()
            token = status.begin()
            getattr(status, action)()
            status.finish(token)
            self.assertEqual(status.text(), expected)

    def test_background_progress_is_thread_safe(self):
        status = TrayStatus()
        ready, release = threading.Event(), threading.Event()
        def work():
            token = status.begin()
            status.stage('Laddar upp')
            status.progress(4, 20)
            ready.set()
            release.wait(2)
            status.finish(token)
        worker = threading.Thread(target=work)
        worker.start()
        try:
            self.assertTrue(ready.wait(2))
            self.assertEqual(status.text(), 'Laddar upp 4/20')
        finally:
            release.set()
            worker.join(2)
        self.assertEqual(status.text(), 'Redo')

    def test_concurrent_jobs_do_not_pretend_to_be_idle(self):
        status = TrayStatus()
        first = status.begin()
        second = status.begin()
        self.assertIn('2 jobb', status.text())
        status.finish(first, True)
        self.assertNotEqual(status.text(), 'Redo')
        status.finish(second)
        self.assertEqual(status.text(), 'Fel – se felloggen')

    def test_tooltip_updates_fallback_and_coalesces_repeated_values(self):
        status = TrayStatus()
        icon = SimpleNamespace(title='', update_menu=Mock())
        app = SimpleNamespace(context={'_tray_status': status},
                              _systray_mgr=SimpleNamespace(_icon=icon), after=Mock())
        status.attach(app)
        app.after.call_args.args[1]()
        self.assertEqual(icon.title, 'FTP-uploader – Redo')
        app.after.call_args.args[1]()
        icon.update_menu.assert_called_once()
        status.begin()
        status.stage('Bearbetar')
        status.progress(3, 8)
        app.after.call_args.args[1]()
        self.assertEqual(icon.title, 'FTP-uploader – Bearbetar 3/8')
        self.assertEqual(status_text(app), 'Bearbetar 3/8')

    def test_missing_tray_is_safe_and_recreated_icon_gets_current_status(self):
        status = TrayStatus()
        app = SimpleNamespace(context={}, _systray_mgr=None, after=Mock())
        status.attach(app)
        app.after.call_args.args[1]()
        icon = SimpleNamespace(title='', update_menu=Mock())
        app.context['_system_tray'] = SimpleNamespace(tray_icon=icon)
        app.after.call_args.args[1]()
        self.assertEqual(icon.title, 'FTP-uploader – Redo')
        self.assertEqual(status_text(SimpleNamespace(context={})), 'Redo')

    def test_plugin_and_manager_same_icon_only_updated_once(self):
        status = TrayStatus()
        icon = SimpleNamespace(title='', update_menu=Mock())
        plugin = SimpleNamespace(tray_icon=icon)
        app = SimpleNamespace(context={'_system_tray': plugin}, _systray_mgr=plugin, after=Mock())
        status.attach(app)
        app.after.call_args.args[1]()
        icon.update_menu.assert_called_once()


class UploadStatusTests(unittest.TestCase):
    def setUp(self):
        import importlib.util
        import sys
        import types
        from pathlib import Path
        from unittest.mock import patch
        base = types.ModuleType('plugins.base_plugin')
        base.BasePlugin = type('BasePlugin', (), {})
        with patch.dict(sys.modules, {'plugins.base_plugin': base}):
            spec = importlib.util.spec_from_file_location('plugins._headless_ftp',
                    Path(__file__).resolve().parents[1] / 'ftp_uploader.py')
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
        self.uploader = module.FTPUploader()
        self.status = TrayStatus()
        self.token = self.status.begin()

    def upload(self, cancel=None):
        from pathlib import Path
        import tempfile
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)
            (path / 'photo.jpg').write_bytes(b'test')
            return self.uploader._upload_all(Mock(), ['photo.jpg'], path, '', None, None, cancel, self.status)

    def test_completed_upload_count_and_ready(self):
        self.uploader._upload_file = Mock(return_value=(True, None))
        uploaded, failed = self.upload()
        self.assertEqual(self.status.text(), 'Laddar upp 1/1')
        self.assertEqual(len(uploaded), 1)
        self.assertEqual(failed, [])
        self.status.finish(self.token)
        self.assertEqual(self.status.text(), 'Redo')

    def test_failed_file_does_not_end_as_ready(self):
        self.uploader._upload_file = Mock(return_value=(False, 'private details'))
        self.upload()
        self.status.finish(self.token)
        self.assertEqual(self.status.text(), 'Fel – se felloggen')
        self.assertNotIn('private details', self.status.text())

    def test_cancelled_upload_is_distinct_from_success(self):
        self.upload(cancel=lambda: True)
        self.status.finish(self.token)
        self.assertEqual(self.status.text(), 'Avbrutet')
