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
            self.assertEqual(app_paths.update_settings()['mode'], 'ask')
            app_paths.save_update_settings({'mode': 'off'})
            self.assertEqual(app_paths.update_settings()['mode'], 'off')
