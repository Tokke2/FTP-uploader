# Copyright (c) 2026 Rickard Längkvist
from pathlib import Path
import ast
import unittest
import xml.etree.ElementTree as ET
from types import SimpleNamespace
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]


class BrandingTests(unittest.TestCase):
    def test_print_svg_contains_only_vectors_and_outlined_type(self):
        for name in ('logo.svg', 'logo-dark.svg', 'logo-monochrome.svg', 'symbol.svg'):
            root = ET.parse(ROOT / 'branding' / name).getroot()
            self.assertIn('viewBox', root.attrib)
            tags = {element.tag.rsplit('}', 1)[-1] for element in root.iter()}
            self.assertNotIn('image', tags)
            self.assertNotIn('text', tags)
            self.assertNotIn('script', tags)
            self.assertIn('path', tags)

    def test_macos_icns_exists(self):
        self.assertEqual((ROOT / 'icon/icon.icns').read_bytes()[:4], b'icns')

    def test_macos_plugin_initializes_detached_on_calling_thread(self):
        # Run real method without importing Tk or platform tray dependencies.
        tree = ast.parse((ROOT / 'plugins/system_tray.py').read_text())
        cls = next(node for node in tree.body if isinstance(node, ast.ClassDef))
        method = next(node for node in cls.body if isinstance(node, ast.FunctionDef) and node.name == '_start_tray')
        method.returns = None
        for arg in method.args.args:
            arg.annotation = None
        fake_icon = Mock()
        context = {'TRAY_AVAILABLE': True, 'sys': SimpleNamespace(platform='darwin'),
                   'Icon': Mock(return_value=fake_icon), 'threading': Mock()}
        exec(compile(ast.fix_missing_locations(ast.Module(body=[method], type_ignores=[])), '<tray>', 'exec'), context)
        owner = SimpleNamespace(_tray_running=False, _load_icon_image=Mock(), _build_tray_menu=Mock(),
                                log=Mock(), log_error=Mock(), _icon_source='icon/icon.png', _tray_loop=Mock(),
                                _schedule_visibility_check=Mock(), app=Mock())
        context['_start_tray'](owner)
        fake_icon.run_detached.assert_called_once()
        context['threading'].Thread.assert_not_called()
        self.assertTrue(owner._tray_running)
