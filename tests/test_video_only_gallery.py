import ast
from pathlib import Path
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

ROOT = Path(__file__).resolve().parents[1]


def extract(filename, function, namespace):
    tree = ast.parse((ROOT / filename).read_text())
    method = next(node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef) and node.name == function)
    exec(compile(ast.fix_missing_locations(ast.Module(body=[method], type_ignores=[])), '<test-method>', 'exec'), namespace)
    return namespace[function]


class VideoOnlyGalleryTests(unittest.TestCase):
    def test_settings_accept_folder_containing_only_original_mov(self):
        method = extract('plugins/ui_settings.py', 'validate_settings', {'Path': Path})
        with tempfile.TemporaryDirectory() as folder:
            (Path(folder) / 'original.MOV').write_bytes(b'video')
            owner = SimpleNamespace(folder_var=SimpleNamespace(get=lambda: folder),
                                    IMAGE_FORMATS={'.jpg'}, VIDEO_FORMATS={'.mov', '.qt', '.mp4'})
            self.assertTrue(method(owner))

    def test_empty_folder_reports_error(self):
        method = extract('plugins/ui_settings.py', 'validate_settings', {'Path': Path})
        with tempfile.TemporaryDirectory() as folder:
            owner = SimpleNamespace(folder_var=SimpleNamespace(get=lambda: folder), IMAGE_FORMATS={'.jpg'}, VIDEO_FORMATS={'.mov'})
            with self.assertRaises(ValueError):
                method(owner)

    def test_old_html_file_does_not_trigger_false_success(self):
        method = extract('plugins/ui_controls.py', '_generate_thread', {'Path': Path})
        with tempfile.TemporaryDirectory() as folder:
            html = Path(folder) / 'index.html'
            html.write_text('old export')
            app = SimpleNamespace(context={'html_output': html, '_gallery_generated': True},
                                  run_pipeline=Mock(), after=lambda delay, callback: callback())
            owner = SimpleNamespace(app=app, cancel_requested=False, write_log=Mock(), update_progress=Mock(),
                                    _on_generation_complete=Mock(), _on_generation_error=Mock())
            method(owner)
            owner._on_generation_complete.assert_not_called()
            owner._on_generation_error.assert_called_once()
            self.assertIn('Inget nytt galleri', str(owner._on_generation_error.call_args.args[0]))

    def test_real_video_only_export_converts_original_without_manual_step(self):
        from media_support import bundled_ffmpeg
        ffmpeg = bundled_ffmpeg()
        if not ffmpeg:
            self.skipTest('FFmpeg required')
        try:
            from PIL import Image
        except ImportError:
            self.skipTest('Pillow required')
        from test_web_image_assets import generator_class
        generator = generator_class()()
        generator._get_output_format = lambda context: 'standard'
        generator._ffmpeg_exe = ffmpeg
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / 'originals'
            source.mkdir()
            video = source / 'iphone.MOV'
            subprocess.run([ffmpeg, '-hide_banner', '-loglevel', 'error', '-f', 'lavfi', '-i',
                            'color=c=red:s=64x48:d=0.4', '-c:v', 'mpeg4', '-y', str(video)],
                           check=True, capture_output=True, timeout=15)
            original = video.read_bytes()
            output = Path(folder) / 'gallery'
            context = {'gallery': {'images_path': str(source), 'output_path': str(output), 'title': 'Videos'},
                       '_defer_learning': True}
            result = generator.execute(context)
            self.assertTrue(result['_gallery_generated'])
            self.assertTrue((output / 'index.html').is_file())
            self.assertTrue((output / 'video/video1.mp4').is_file())
            self.assertIn('video/video1.mp4', (output / 'index.html').read_text())
            self.assertTrue(result['link_report']['ok'])
            self.assertEqual(video.read_bytes(), original)

    def test_pipeline_prepares_settings_even_if_excluded_from_optional_steps(self):
        import contextvars
        import traceback
        calls = []
        def prepare(context, log):
            calls.append('settings')
            context['gallery'] = {'images_path': 'original-videos'}
            return context
        def generate(context, log):
            calls.append('html')
            self.assertEqual(context['gallery']['images_path'], 'original-videos')
            return context
        settings = SimpleNamespace(execute=prepare, PLUGIN_NAME='Inställningar')
        html = SimpleNamespace(execute=generate, PLUGIN_NAME='HTML')
        owner = SimpleNamespace(context={'_settings': settings}, get_plugins=lambda **kwargs: [('html', html)], _log_error=Mock())
        run = extract('main.pyw', 'run_pipeline', {'_event': Mock(), '_event_exception': Mock(),
                     '_log_job': contextvars.ContextVar('test-gallery-job'), 'traceback': traceback})
        run(owner)
        self.assertEqual(calls, ['settings', 'html'])
