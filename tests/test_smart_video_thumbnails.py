from pathlib import Path
import subprocess
import tempfile
import unittest
from video_thumbnails import frame_score, choose_video_thumbnail

try:
    from PIL import Image, ImageDraw
except ImportError:
    Image = None


@unittest.skipIf(Image is None, 'Pillow required')
class SmartThumbnailTests(unittest.TestCase):
    def test_detail_beats_black_and_blank_intro(self):
        with Image.new('RGB', (160, 100), 'black') as black, Image.new('RGB', (160, 100), 'gray') as blank:
            with Image.new('RGB', (160, 100), 'white') as detailed:
                draw = ImageDraw.Draw(detailed)
                for x in range(0, 160, 10):
                    draw.rectangle((x, 10, x+5, 90), fill='blue')
                self.assertGreater(frame_score(detailed), frame_score(black))
                self.assertGreater(frame_score(detailed), frame_score(blank))

    def test_cancellation_preserves_existing_thumbnail(self):
        with tempfile.TemporaryDirectory() as folder:
            dst = Path(folder) / 'thumb.jpg'
            dst.write_bytes(b'existing')
            with self.assertRaisesRegex(RuntimeError, 'avbruten'):
                choose_video_thumbnail('unused.mp4', dst, 'ffmpeg', lambda: True)
            self.assertEqual(dst.read_bytes(), b'existing')

    def test_real_video_avoids_black_intro(self):
        from media_support import bundled_ffmpeg
        ffmpeg = bundled_ffmpeg()
        if not ffmpeg:
            self.skipTest('FFmpeg required')
        with tempfile.TemporaryDirectory() as folder:
            source, thumb = Path(folder) / 'clip.mp4', Path(folder) / 'thumb.jpg'
            subprocess.run([ffmpeg, '-nostdin', '-hide_banner', '-loglevel', 'error',
                '-f', 'lavfi', '-i', 'color=black:s=160x100:r=10:d=1',
                '-f', 'lavfi', '-i', 'testsrc2=s=160x100:r=10:d=3',
                '-filter_complex', '[0:v][1:v]concat=n=2:v=1:a=0[out]', '-map', '[out]',
                '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-y', str(source)],
                check=True, capture_output=True, timeout=20)
            self.assertTrue(choose_video_thumbnail(source, thumb, ffmpeg))
            with Image.open(thumb) as image:
                self.assertGreater(frame_score(image), 0)
            self.assertFalse(list(Path(folder).glob('.video-frames-*')))
