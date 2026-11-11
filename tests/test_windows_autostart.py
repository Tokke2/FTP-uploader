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
            destination.touch()
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
