from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from ffmpeg_progress import monitor, duration_from_ffmpeg


class FFmpegMonitorTests(unittest.TestCase):
    def child(self, script):
        return subprocess.Popen([sys.executable, '-u', '-c', script], stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, text=True)

    def test_large_stderr_does_not_deadlock_and_progress_is_read(self):
        process = self.child('import sys;sys.stderr.write("x"*2000000);sys.stderr.flush();print("out_time_us=5000000");print("progress=end")')
        values = []
        monitor(process, duration=10, progress=values.append, timeout=5)
        self.assertIn(100, values)
        self.assertEqual(process.returncode, 0)

    def test_silent_process_can_timeout_without_waiting_for_newline(self):
        process = self.child('import time;time.sleep(30)')
        started = time.monotonic()
        with self.assertRaises(TimeoutError):
            monitor(process, timeout=0.3)
        self.assertLess(time.monotonic() - started, 5)
        self.assertIsNotNone(process.poll())

    def test_silent_process_can_be_cancelled(self):
        process = self.child('import time;time.sleep(30)')
        started = time.monotonic()
        with self.assertRaisesRegex(RuntimeError, 'Avbrutet'):
            monitor(process, cancelled=lambda: time.monotonic() - started > 0.2)
        self.assertIsNotNone(process.poll())

    def test_failure_contains_stderr_tail_and_not_success(self):
        process = self.child('import sys;sys.stderr.write("decoder exploded");sys.exit(7)')
        values = []
        with self.assertRaisesRegex(RuntimeError, 'decoder exploded'):
            monitor(process, progress=values.append)
        self.assertNotIn(100, values)

    def test_unknown_duration_does_not_make_up_percentage(self):
        process = self.child('print("out_time_ms=5000000")')
        values = []
        monitor(process, duration=0, progress=values.append)
        self.assertEqual(values, [100])

    def test_heartbeat_runs_while_process_is_silent(self):
        process = self.child('import time;time.sleep(1.4)')
        beats = []
        monitor(process, heartbeat=lambda elapsed, silent: beats.append((elapsed, silent)), timeout=4)
        self.assertTrue(beats)

    def test_real_ffmpeg_duration_without_ffprobe(self):
        from media_support import bundled_ffmpeg
        executable = bundled_ffmpeg()
        if not executable:
            self.skipTest('FFmpeg unavailable')
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / 'clip.mov'
            subprocess.run([executable, '-hide_banner', '-loglevel', 'error', '-f', 'lavfi', '-i',
                            'color=c=red:s=64x48:d=0.4', '-y', str(source)], check=True, capture_output=True, timeout=10)
            self.assertGreater(duration_from_ffmpeg(executable, source), 0)
