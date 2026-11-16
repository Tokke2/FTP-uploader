from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from media_support import video_to_web_mp4


class VideoCacheTests(unittest.TestCase):
    def test_cache_requires_unchanged_source_and_output(self):
        with tempfile.TemporaryDirectory() as folder:
            source, output = Path(folder) / 'source.mov', Path(folder) / 'video.mp4'
            source.write_bytes(b'first')
            def encode(src, dst, ffmpeg):
                dst.parent.mkdir(parents=True, exist_ok=True)
                dst.write_bytes(b'encoded-' + src.read_bytes())
            with patch('shutil.which', return_value=None), patch('media_support.quicktime_to_mp4', side_effect=encode) as convert:
                video_to_web_mp4(source, output, 'nonexistent-ffmpeg')
                video_to_web_mp4(source, output, 'nonexistent-ffmpeg')
                self.assertEqual(convert.call_count, 1)
                source.write_bytes(b'second')
                video_to_web_mp4(source, output, 'nonexistent-ffmpeg')
                self.assertEqual(convert.call_count, 2)
                output.write_bytes(b'corrupt')
                video_to_web_mp4(source, output, 'nonexistent-ffmpeg')
                self.assertEqual(convert.call_count, 3)

    def test_installation_info_handles_old_and_new_state(self):
        from auto_update import installation_info
        with tempfile.TemporaryDirectory() as folder:
            self.assertIn('saknas', installation_info(folder))
            (Path(folder) / '.release-state.json').write_text('{"commit":"abcdef1234567890","installed_at":"2026-10-20"}')
            self.assertIn('abcdef123456', installation_info(folder))
            self.assertIn('2026-10-20', installation_info(folder))

    def test_update_handoff_saves_and_spawns_before_quitting(self):
        from auto_update import handoff_release
        from unittest.mock import Mock
        app = Mock()
        order = []
        app._save_all_settings.side_effect = lambda: order.append('save')
        app.quit_app.side_effect = lambda: order.append('quit')
        with patch('auto_update.live_update_blockers', return_value=[]), patch('release_scheduler.spawn', side_effect=lambda command: order.append('spawn')):
            handoff_release(app, '/app', ('v1.0.0', 'a' * 40))
        self.assertEqual(order, ['save', 'spawn', 'quit'])

    def test_compatible_streams_remux_instead_of_encoding(self):
        import json
        from types import SimpleNamespace
        from unittest.mock import Mock
        streams = {'streams': [{'codec_type': 'video', 'codec_name': 'h264', 'pix_fmt': 'yuv420p'},
                               {'codec_type': 'audio', 'codec_name': 'aac'}]}
        with tempfile.TemporaryDirectory() as folder:
            source, output = Path(folder) / 'source.mov', Path(folder) / 'web.mp4'
            source.write_bytes(b'original')
            def popen(command, **kwargs):
                Path(command[-1]).write_bytes(b'remuxed')
                return Mock()
            with patch('shutil.which', return_value='ffprobe'), \
                    patch('media_support.subprocess.run', return_value=SimpleNamespace(stdout=json.dumps(streams))), \
                    patch('media_support.subprocess.Popen', side_effect=popen) as process, \
                    patch('ffmpeg_progress.monitor'), patch('media_support.quicktime_to_mp4') as encode:
                video_to_web_mp4(source, output, 'ffmpeg')
                encode.assert_not_called()
                command = process.call_args.args[0]
                self.assertIn('copy', command)
                self.assertIn('+faststart', command)
                self.assertEqual(source.read_bytes(), b'original')
                self.assertEqual(output.read_bytes(), b'remuxed')

    def test_incompatible_codec_requires_encoding(self):
        import json
        from types import SimpleNamespace
        streams = {'streams': [{'codec_type': 'video', 'codec_name': 'hevc', 'pix_fmt': 'yuv420p10le'}]}
        with tempfile.TemporaryDirectory() as folder:
            source, output = Path(folder) / 'source.mp4', Path(folder) / 'web.mp4'
            source.write_bytes(b'hevc')
            with patch('shutil.which', return_value='ffprobe'), \
                    patch('media_support.subprocess.run', return_value=SimpleNamespace(stdout=json.dumps(streams))), \
                    patch('media_support.quicktime_to_mp4') as encode:
                video_to_web_mp4(source, output, 'ffmpeg')
                encode.assert_called_once_with(source, output, 'ffmpeg')

    def test_handoff_spawn_failure_keeps_app_open(self):
        from auto_update import handoff_release
        from unittest.mock import Mock
        app = Mock()
        with patch('auto_update.live_update_blockers', return_value=[]), \
                patch('release_scheduler.spawn', side_effect=OSError('cannot spawn')), self.assertRaises(OSError):
            handoff_release(app, '/app', ('v1.0.0', 'a' * 40))
        app.quit_app.assert_not_called()
