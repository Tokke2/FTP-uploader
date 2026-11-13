import json
from pathlib import Path
import struct
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch
import windows_autostart as autostart


class WindowsAutostartTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)
        self.link = self.folder / 'Startup/FTP-uploader.lnk'
        self.python = self.folder / 'pythonw.exe'
        self.python.touch()
        self.base = Path(autostart.__file__).parent
        self.parts = patch.object(autostart, 'launch_parts', return_value=(self.python, [str(self.base / 'start.pyw')], self.base))
        self.parts.start()
        self.addCleanup(self.parts.stop)
        self.fake_registry = SimpleNamespace(HKEY_CURRENT_USER=1, KEY_SET_VALUE=2,
                                            OpenKey=Mock(side_effect=FileNotFoundError))

    def test_enable_creates_icon_shortcut_not_registry_command(self):
        def create(destination, *args):
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(b'fake-shortcut')
        with patch.object(autostart.sys, 'platform', 'win32'), patch.object(autostart, 'startup_link', return_value=self.link), patch.object(autostart, 'config_dir', return_value=self.folder), patch.dict('sys.modules', winreg=self.fake_registry), patch('windows_shortcut.create_shortcut', side_effect=create) as shortcut:
            self.assertTrue(autostart.set_enabled(True))
            args = shortcut.call_args.args
            self.assertEqual(args[1].name, 'pythonw.exe')
            self.assertEqual(Path(args[3]).name, 'icon.ico')
            self.assertEqual(autostart.registered(), autostart.command())
            self.assertTrue(autostart.set_enabled(False))
            self.assertFalse(self.link.exists())

    def test_icon_changed_triggers_shortcut_refresh(self):
        self.link.parent.mkdir(parents=True)
        self.link.touch()
        (self.folder / 'autostart-shortcut.json').write_text(json.dumps({'icon_hash': 'old'}))
        with patch.object(autostart.sys, 'platform', 'win32'), patch.object(autostart, 'startup_link', return_value=self.link), patch.object(autostart, 'config_dir', return_value=self.folder):
            self.assertEqual(autostart.registered(), 'föråldrad genväg')

    def test_non_windows_does_not_register(self):
        with patch.object(autostart.sys, 'platform', 'linux'):
            self.assertFalse(autostart.set_enabled(True))
            self.assertIsNone(autostart.registered())

    def test_png_sizes_and_multisize_windows_icon(self):
        folder = self.base / 'icon'
        for size in (16, 32, 64, 256):
            raw = (folder / ('icon_%d.png' % size)).read_bytes()
            self.assertEqual(struct.unpack('>II', raw[16:24]), (size, size))
        raw = (folder / 'icon.ico').read_bytes()
        reserved, kind, count = struct.unpack('<HHH', raw[:6])
        self.assertEqual((reserved, kind), (0, 1))
        self.assertGreaterEqual(count, 6)


    def test_autostart_launch_has_explicit_silent_flag(self):
        # Test real launch_parts, not setUp's stub.
        self.parts.stop()
        with patch.object(autostart.sys, 'frozen', False, create=True), patch('python_discovery.find_python', return_value=self.python):
            executable, args, base = autostart.launch_parts()
        self.assertIn('--autostart', args)
        self.assertEqual(executable, self.python)

    def test_windows_disabled_flag_is_detected_not_overwritten(self):
        from unittest.mock import MagicMock
        registry = MagicMock()
        registry.HKEY_CURRENT_USER = 1
        registry.QueryValueEx.return_value = (bytes([3]) + bytes(11), 3)
        with patch.object(autostart.sys, 'platform', 'win32'), patch.dict('sys.modules', winreg=registry):
            self.assertTrue(autostart.startup_disabled())
        registry.SetValueEx.assert_not_called()

    def test_missing_shortcut_is_not_reported_as_success(self):
        with patch.object(autostart.sys, 'platform', 'win32'), patch.object(autostart, 'startup_link', return_value=self.link), patch.object(autostart, 'config_dir', return_value=self.folder), patch.dict('sys.modules', winreg=self.fake_registry), patch('windows_shortcut.create_shortcut'):
            with self.assertRaises(OSError):
                autostart.set_enabled(True)

    def test_modified_link_forces_repair(self):
        self.link.parent.mkdir(parents=True)
        self.link.write_bytes(b'original')
        import hashlib
        with patch.object(autostart.sys, 'platform', 'win32'), patch.object(autostart, 'startup_link', return_value=self.link), patch.object(autostart, 'config_dir', return_value=self.folder), patch.dict('sys.modules', winreg=self.fake_registry):
            info = autostart.fingerprint()
            info['link_hash'] = hashlib.sha256(b'original').hexdigest()
            (self.folder / 'autostart-shortcut.json').write_text(json.dumps(info))
            self.assertEqual(autostart.registered(), autostart.command())
            self.link.write_bytes(b'tampered')
            self.assertEqual(autostart.registered(), 'föråldrad genväg')

    def test_duplicate_autostart_does_not_raise_existing_window(self):
        import single_instance
        guard = Mock()
        guard.acquire.return_value = False
        with patch.object(single_instance, '_primary', None), patch.object(single_instance, 'SingleInstance', return_value=guard), patch.object(autostart.sys, 'argv', ['start.pyw', '--autostart']):
            self.assertIsNone(single_instance.ensure_primary())
        guard.activate_existing.assert_not_called()
