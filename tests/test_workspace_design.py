from pathlib import Path
import ast
import tempfile
import unittest
from workspace_design import bounded_int, window_size, pane_orientation, load_state, save_state, TOKENS
from layout_designer import options, css

ROOT = Path(__file__).resolve().parents[1]


class WorkspaceDesignTests(unittest.TestCase):
    def test_small_screen_and_panel_orientation(self):
        self.assertEqual(window_size(640, 480), (600, 400))
        self.assertEqual(window_size(1920, 1080), (1120, 820))
        self.assertEqual(pane_orientation(600), 'vertical')
        self.assertEqual(pane_orientation(1100), 'horizontal')

    def test_state_roundtrip_and_bad_state(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'workspace.json'
            self.assertEqual(load_state(path), {})
            save_state(path, {'advanced': True, 'ratio_horizontal': 0.6})
            self.assertEqual(load_state(path)['ratio_horizontal'], 0.6)
            path.write_text('invalid')
            self.assertEqual(load_state(path), {})
            path.write_text('[]')
            self.assertEqual(load_state(path), {})

    def test_layout_input_is_bounded_and_css_cannot_inject(self):
        self.assertEqual(bounded_int('nan', 16, 0, 48), 16)
        o = options({'gap': 9999, 'radius': -1, 'font_size': 'bad', 'aspect': '</style>', 'fit': 'evil'})
        self.assertEqual(o, {'gap': 48, 'radius': 0, 'font_size': 16, 'aspect': '4/3', 'fit': 'cover'})
        self.assertNotIn('</style>', css({'aspect': '</style>'}))
        self.assertIn('gap:20px', css({'gap': 20}))
        self.assertIn('object-fit:contain', css({'fit': 'contain'}))

    def test_design_foreground_has_accessible_contrast(self):
        def luminance(color):
            values = [int(color[i:i+2], 16)/255 for i in (1, 3, 5)]
            values = [v/12.92 if v <= 0.04045 else ((v+0.055)/1.055)**2.4 for v in values]
            return sum(v*w for v, w in zip(values, (0.2126, 0.7152, 0.0722)))
        for key in ('fg', 'muted', 'cyan', 'violet', 'pink'):
            ratio = (luminance(TOKENS[key]) + 0.05) / (luminance(TOKENS['surface']) + 0.05)
            self.assertGreater(ratio, 4.5, key)

    def test_layout_saved_in_settings_and_passed_to_generator(self):
        tree = ast.parse((ROOT / 'plugins/ui_settings.py').read_text())
        collect = next(node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef) and node.name == '_collect_settings')
        execute = next(node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef) and node.name == 'execute')
        self.assertIn("'layout'", ast.unparse(collect))
        self.assertIn("'layout'", ast.unparse(execute))
        self.assertIn('layout_css', (ROOT / 'plugins/html_generator.py').read_text())

    def test_workspace_is_ui_only_and_keeps_existing_tools(self):
        tree = ast.parse((ROOT / 'plugins/workspace.py').read_text())
        cls = next(n for n in tree.body if isinstance(n, ast.ClassDef))
        self.assertFalse(cls.bases)
        self.assertNotIn('execute', [n.name for n in cls.body if isinstance(n, ast.FunctionDef)])
        self.assertIn('toggle_advanced', [n.name for n in cls.body if isinstance(n, ast.FunctionDef)])

    def test_visual_settings_reach_real_export_and_portable_manifest(self):
        try:
            from PIL import Image
        except ImportError:
            self.skipTest('Pillow required')
        import json
        from test_web_image_assets import generator_class
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / 'originals'
            source.mkdir()
            with Image.new('RGB', (80, 60), 'blue') as image:
                image.save(source / 'sample.jpg')
            output = Path(folder) / 'gallery'
            generator = generator_class()()
            generator._get_output_format = lambda context: 'standard'
            context = {'gallery': {'images_path': str(source), 'output_path': str(output),
                                   'layout': {'gap': 24, 'radius': 8, 'font_size': 18, 'aspect': '1/1', 'fit': 'contain'}},
                       '_defer_learning': True}
            generator.execute(context)
            html = (output / 'index.html').read_text()
            self.assertIn('gap:24px', html)
            self.assertIn('aspect-ratio:1/1', html)
            self.assertIn('object-fit:contain', html)
            project = json.loads((output / 'gallery-project.json').read_text())
            self.assertEqual(project['gallery']['layout']['radius'], 8)
