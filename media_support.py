# Copyright (c) 2026 Rickard Längkvist
"""Shared HEIF registration and atomic QuickTime-to-web conversion."""
from pathlib import Path
import os
import subprocess
import tempfile
import threading

_lock = threading.Lock()
_registered = False


def register_heif():
    global _registered
    with _lock:
        if _registered:
            return True
        try:
            from pillow_heif import register_heif_opener
            register_heif_opener()
        except (ImportError, OSError):
            return False
        _registered = True
        return True


def bundled_ffmpeg():
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except (ImportError, OSError, RuntimeError):
        return None


def quicktime_to_mp4(source, destination, ffmpeg=None):
    """Convert in a temporary file, preserve original and any existing output on failure."""
    source, destination = Path(source), Path(destination)
    ffmpeg = ffmpeg or bundled_ffmpeg()
    if not ffmpeg:
        raise RuntimeError('QuickTime kräver FFmpeg. Installera appberoendet imageio-ffmpeg eller välj FFmpeg i Video-fliken.')
    if source.resolve() == destination.resolve():
        raise ValueError('Originalvideon får inte skrivas över.')
    destination.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix='.quicktime-', suffix='.mp4', dir=destination.parent)
    os.close(fd)
    temporary = Path(name)
    try:
        command = [str(ffmpeg), '-hide_banner', '-loglevel', 'error', '-nostdin', '-y',
                   '-i', str(source), '-map', '0:v:0', '-map', '0:a:0?',
                   '-vf', 'scale=trunc(iw/2)*2:trunc(ih/2)*2',
                   '-c:v', 'libx264', '-crf', '22', '-preset', 'medium', '-pix_fmt', 'yuv420p',
                   '-c:a', 'aac', '-movflags', '+faststart', str(temporary)]
        result = subprocess.run(command, capture_output=True, text=True, errors='replace',
                                timeout=3600, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0) if os.name == 'nt' else 0)
        if result.returncode or temporary.stat().st_size == 0:
            raise RuntimeError('QuickTime-konvertering misslyckades: %s' % result.stderr[-4000:])
        temporary.replace(destination)
    finally:
        temporary.unlink(missing_ok=True)
    return destination
