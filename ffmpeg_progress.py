# Copyright (c) 2026 Rickard Längkvist
"""Drain both FFmpeg pipes concurrently; never block watchdog on readline."""
from collections import deque
import queue
import re
import quiet_process as subprocess
import threading
import time


def monitor(process, duration=0, progress=None, cancelled=None, heartbeat=None, timeout=3600):
    updates = queue.Queue(maxsize=32)
    errors = deque(maxlen=16)
    activity = {'time': time.monotonic()}

    def read_progress():
        try:
            for line in process.stdout:
                activity['time'] = time.monotonic()
                key, _, value = line.strip().partition('=')
                try:
                    updates.put_nowait((key, value))
                except queue.Full:
                    try:
                        updates.get_nowait()
                    except queue.Empty:
                        pass
                    try:
                        updates.put_nowait((key, value))
                    except queue.Full:
                        pass
        except (OSError, ValueError):
            pass

    def read_errors():
        try:
            while True:
                chunk = process.stderr.read(4096)
                if not chunk:
                    break
                errors.append(chunk)
                activity['time'] = time.monotonic()
        except (OSError, ValueError):
            pass

    readers = [threading.Thread(target=read_progress, daemon=True, name='FFmpeg-stdout'),
               threading.Thread(target=read_errors, daemon=True, name='FFmpeg-stderr')]
    for reader in readers:
        reader.start()
    started = last_heartbeat = time.monotonic()
    last_percent = -1
    try:
        while process.poll() is None or not updates.empty():
            now = time.monotonic()
            if cancelled and cancelled():
                raise RuntimeError('Avbrutet av användaren')
            if now - started > timeout:
                raise TimeoutError('FFmpeg överskred tidsgränsen på %d sekunder' % timeout)
            if heartbeat and now - last_heartbeat >= 1:
                heartbeat(int(now - started), int(now - activity['time']))
                last_heartbeat = now
            try:
                key, value = updates.get(timeout=0.2)
            except queue.Empty:
                continue
            if key in ('out_time_us', 'out_time_ms') and duration > 0:
                try:
                    percent = max(0, min(99, int(value) / 1000000 / duration * 100))
                except ValueError:
                    continue
                if progress and percent > last_percent:
                    progress(percent)
                    last_percent = percent
        code = process.wait(timeout=5)
        for reader in readers:
            reader.join(timeout=2)
        if cancelled and cancelled():
            raise RuntimeError('Avbrutet av användaren')
        if code:
            raise RuntimeError('FFmpeg exit %s: %s' % (code, ''.join(errors)[-8000:]))
        if progress:
            progress(100)
    finally:
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=3)
        for reader in readers:
            reader.join(timeout=2)
        for stream in (process.stdout, process.stderr):
            stream.close()


def duration_from_ffmpeg(executable, path, flags=0):
    """Fallback metadata read when ffprobe is missing; never invent duration."""
    result = subprocess.run([str(executable), '-hide_banner', '-nostdin', '-i', str(path)],
                            capture_output=True, text=True, errors='replace', timeout=15,
                            creationflags=flags)
    match = re.search(r'Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)', result.stderr)
    if match:
        return int(match[1]) * 3600 + int(match[2]) * 60 + float(match[3])
    return 0
