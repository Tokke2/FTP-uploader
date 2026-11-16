from pathlib import Path
import ast
import subprocess
import tempfile
import unittest
from unittest.mock import patch
import media_support

ROOT = Path(__file__).resolve().parents[1]


class MediaSupportTests(unittest.TestCase):
    def test_heic_and_heif_roundtrip_decode(self):
        try:
            from PIL import Image
            import pillow_heif
        except ImportError:
            self.skipTest('HEIF codec unavailable')
        self.assertTrue(media_support.register_heif())
        with tempfile.TemporaryDirectory() as folder:
            for extension in ('.heic', '.heif'):
                path = Path(folder) / ('image' + extension)
                with Image.new('RGB', (64, 48), 'red') as image:
                    pillow_heif.from_pillow(image).save(path)
                with Image.open(path) as decoded:
                    decoded.load()
                    self.assertEqual(decoded.size, (64, 48))
                    self.assertGreater(decoded.convert('RGB').getpixel((20, 20))[0], 200)

    def test_quicktime_mov_and_qt_convert_to_web_mp4(self):
        ffmpeg = media_support.bundled_ffmpeg()
        if not ffmpeg:
            self.skipTest('FFmpeg unavailable')
        with tempfile.TemporaryDirectory() as folder:
            folder = Path(folder)
            for extension in ('.mov', '.qt'):
                source = folder / ('source' + extension)
                subprocess.run([ffmpeg, '-hide_banner', '-loglevel', 'error', '-y',
                                '-f', 'lavfi', '-i', 'color=c=red:s=64x48:d=0.2',
                                '-c:v', 'mpeg4', '-f', 'mov', str(source)], check=True, capture_output=True, timeout=20)
                original = source.read_bytes()
                output = folder / ('converted' + extension + '.mp4')
                media_support.quicktime_to_mp4(source, output, ffmpeg)
                self.assertGreater(output.stat().st_size, 0)
                self.assertEqual(source.read_bytes(), original)
                check = subprocess.run([ffmpeg, '-hide_banner', '-i', str(output), '-f', 'null', '-'],
                                       capture_output=True, text=True, timeout=20)
                self.assertEqual(check.returncode, 0, check.stderr)
                self.assertIn('h264', check.stderr)
                self.assertIn('yuv420p', check.stderr)

    def test_failed_conversion_preserves_original_and_existing_output(self):
        from types import SimpleNamespace
        with tempfile.TemporaryDirectory() as folder:
            source, output = Path(folder) / 'source.mov', Path(folder) / 'video.mp4'
            source.write_bytes(b'original')
            output.write_bytes(b'old output')
            with patch('media_support.subprocess.run', return_value=SimpleNamespace(returncode=1, stderr='invalid media')):
                with self.assertRaisesRegex(RuntimeError, 'invalid media'):
                    media_support.quicktime_to_mp4(source, output, 'ffmpeg')
            self.assertEqual(source.read_bytes(), b'original')
            self.assertEqual(output.read_bytes(), b'old output')
            self.assertFalse(list(Path(folder).glob('.quicktime-*')))

    def test_source_cannot_be_overwritten(self):
        with self.assertRaises(ValueError):
            media_support.quicktime_to_mp4('same.mp4', 'same.mp4', 'ffmpeg')

    def test_input_filters_recognize_new_formats(self):
        for filename in ('ui_settings.py', 'image_processor.py', 'gallery_view.py', 'html_generator.py', 'video_processor.py'):
            tree = ast.parse((ROOT / 'plugins' / filename).read_text())
            values = []
            for node in ast.walk(tree):
                if isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id == 'IMAGE_FORMATS' for target in node.targets):
                    values.append(ast.literal_eval(node.value))
            self.assertTrue(values, filename)
            self.assertIn('.heic', values[0], filename)
            self.assertIn('.heif', values[0], filename)
        for filename in ('ui_settings.py', 'video_processor.py', 'html_generator.py'):
            self.assertIn('".qt"', (ROOT / 'plugins' / filename).read_text())

    def test_export_routes_quicktime_through_converter(self):
        tree = ast.parse((ROOT / 'plugins/html_generator.py').read_text())
        method = next(node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef) and node.name == '_copy_and_rename_media')
        namespace = {'Path': Path}
        exec(compile(ast.fix_missing_locations(ast.Module(body=[method], type_ignores=[])), '<media-export>', 'exec'), namespace)
        from types import SimpleNamespace
        owner = SimpleNamespace(_find_ffmpeg=lambda: 'ffmpeg', _safe_copy=lambda *args: self.fail('QuickTime must be converted'))
        with tempfile.TemporaryDirectory() as folder, patch('media_support.quicktime_to_mp4') as convert:
            result = namespace['_copy_and_rename_media'](owner, [Path('clip.MOV')], Path(folder), 'standard', 'video', 'video')
            convert.assert_called_once()
            self.assertEqual(result[0]['relative_path'], 'video/video1.mp4')
            self.assertEqual(result[0]['original_name'], 'clip.MOV')

    def test_gallery_converts_every_video_including_mp4_not_just_quicktime(self):
        tree = ast.parse((ROOT / 'plugins/html_generator.py').read_text())
        method = next(node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef) and node.name == '_copy_and_rename_media')
        namespace = {'Path': Path}
        exec(compile(ast.fix_missing_locations(ast.Module(body=[method], type_ignores=[])), '<media-export>', 'exec'), namespace)
        from types import SimpleNamespace
        owner = SimpleNamespace(_find_ffmpeg=lambda: 'ffmpeg', _safe_copy=lambda *args: self.fail('Videos must be normalized'))
        sources = [Path('clip' + extension) for extension in ('.mov', '.qt', '.mp4', '.avi', '.mkv', '.webm')]
        with tempfile.TemporaryDirectory() as folder, patch('media_support.video_to_web_mp4') as convert:
            result = namespace['_copy_and_rename_media'](owner, sources, Path(folder), 'standard', 'video', 'video')
            self.assertEqual(convert.call_count, len(sources))
            self.assertTrue(all(item['relative_path'].endswith('.mp4') for item in result))

    def test_gallery_reexport_does_not_overwrite_any_source_video(self):
        tree = ast.parse((ROOT / 'plugins/html_generator.py').read_text())
        method = next(node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef) and node.name == '_copy_and_rename_media')
        namespace = {'Path': Path}
        exec(compile(ast.fix_missing_locations(ast.Module(body=[method], type_ignores=[])), '<media-export>', 'exec'), namespace)
        from types import SimpleNamespace
        owner = SimpleNamespace(_find_ffmpeg=lambda: 'ffmpeg')
        with tempfile.TemporaryDirectory() as folder, patch('media_support.video_to_web_mp4') as convert:
            folder = Path(folder)
            sources = [folder / 'video1.mp4', folder / 'video1_web.mp4']
            sources[0].write_bytes(b'first original')
            sources[1].write_bytes(b'second original')
            namespace['_copy_and_rename_media'](owner, sources, folder, 'flat', 'video', 'video')
            self.assertEqual(convert.call_args_list[0].args[1].name, 'video1_web_web.mp4')
            self.assertEqual(sources[0].read_bytes(), b'first original')
            self.assertEqual(sources[1].read_bytes(), b'second original')
