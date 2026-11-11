# Copyright (c) 2026 Rickard Längkvist
from pathlib import Path
import struct
import unittest

ROOT = Path(__file__).resolve().parents[1]


class IconAssetTests(unittest.TestCase):
    def test_png_variants_have_expected_sizes_and_alpha(self):
        for size in (16, 32, 64, 256, 1024):
            path = ROOT / 'icon' / ('icon.png' if size == 1024 else 'icon_%d.png' % size)
            data = path.read_bytes()
            self.assertEqual(data[:8], b'\x89PNG\r\n\x1a\n')
            self.assertEqual(struct.unpack('>II', data[16:24]), (size, size))
            self.assertEqual(data[25], 6)  # RGBA; no baked-in checkerboard.

    def test_ico_includes_small_tray_and_large_taskbar_sizes(self):
        data = (ROOT / 'icon/icon.ico').read_bytes()
        reserved, kind, count = struct.unpack('<HHH', data[:6])
        self.assertEqual((reserved, kind), (0, 1))
        sizes = {data[6 + index * 16] or 256 for index in range(count)}
        self.assertTrue({16, 24, 32, 48, 64, 128, 256}.issubset(sizes))

    def test_same_identity_on_process_and_windows_shortcut(self):
        import windows_shortcut
        self.assertEqual(windows_shortcut.APP_ID, 'Tokke2.FTPUploader')
        source = (ROOT / 'windows_shortcut.py').read_text()
        self.assertIn('create_unicode_buffer(APP_ID)', source)
        self.assertIn('SetCurrentProcessExplicitAppUserModelID', source)
