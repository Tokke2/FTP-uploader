import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import app_paths


class PathsTests(unittest.TestCase):
    def test_migration_and_settings(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, XDG_CONFIG_HOME=directory), patch('app_paths.sys.platform', 'linux'):
            path = app_paths.config_dir()
            self.assertEqual(path, Path(directory) / 'FTP-uploader/config')
            settings = path / 'settings.json'
            self.assertTrue(settings.exists())
            settings.write_text('{"test": true}')
            app_paths.config_dir()
            self.assertEqual(settings.read_text(), '{"test": true}')
            self.assertEqual(app_paths.update_settings()['mode'], 'auto')
            app_paths.save_update_settings({'mode': 'off'})
            self.assertEqual(app_paths.update_settings()['mode'], 'off')

    def test_logs_belong_to_app_not_user_data(self):
        with tempfile.TemporaryDirectory() as app, tempfile.TemporaryDirectory() as user:
            with patch('app_paths.app_dir', return_value=Path(app)), patch('app_paths.data_dir', return_value=Path(user)):
                path = app_paths.logs_dir()
                self.assertEqual(path, Path(app) / 'logs')
                self.assertTrue(path.is_dir())
                self.assertFalse((Path(user) / 'logs').exists())

    def test_packaged_app_uses_executable_directory(self):
        with patch('app_paths.sys.frozen', True, create=True), patch('app_paths.sys.executable', '/home/user/example/FTP-uploader.exe'):
            self.assertEqual(app_paths.app_dir(), Path('/home/user/example'))

    def test_source_app_uses_module_location(self):
        with patch('app_paths.sys.frozen', False, create=True):
            self.assertEqual(app_paths.app_dir(), Path(app_paths.__file__).resolve().parent)
