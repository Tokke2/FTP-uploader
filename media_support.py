# Copyright (c) 2026 Rickard Längkvist
"""Shared HEIF registration and atomic video-to-web conversion."""
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


def quicktime_to_mp4(source, destination, ffmpeg=None, cancelled=None):
    """Convert in a temporary file, preserve original and any existing output on failure."""
    source, destination = Path(source), Path(destination)
    ffmpeg = ffmpeg or bundled_ffmpeg()
    if not ffmpeg:
        raise RuntimeError('Videokonvertering kräver FFmpeg. Installera appberoendet imageio-ffmpeg eller välj FFmpeg i Video-fliken.')
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
        from resource_profiles import ffmpeg_args
        command[-1:-1] = ffmpeg_args()
        flags = getattr(subprocess, 'CREATE_NO_WINDOW', 0) if os.name == 'nt' else 0
        if cancelled is not None:
            from ffmpeg_progress import monitor
            if cancelled():
                raise RuntimeError('Videokonvertering avbruten')
            process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                       text=True, errors='replace', creationflags=flags)
            monitor(process, cancelled=cancelled, timeout=3600)
        else:
            result = subprocess.run(command, capture_output=True, text=True, errors='replace',
                                    timeout=3600, creationflags=flags)
            if result.returncode:
                raise RuntimeError('Videokonvertering misslyckades: %s' % result.stderr[-4000:])
        if temporary.stat().st_size == 0:
            raise RuntimeError('Videokonvertering gav en tom fil.')
        temporary.replace(destination)
    finally:
        temporary.unlink(missing_ok=True)
    return destination


def video_to_web_mp4(source, destination, ffmpeg=None, cancelled=None):
    """Reuse verified outputs; remux only conservatively compatible streams."""
    import hashlib
    import json
    import shutil
    source, destination = Path(source), Path(destination)
    if source.resolve() == destination.resolve():
        raise ValueError('Originalvideon får inte skrivas över.')
    def digest(path):
        result = hashlib.sha256()
        with path.open('rb') as stream:
            while True:
                if cancelled and cancelled():
                    raise RuntimeError('Videokonvertering avbruten')
                block = stream.read(1024 * 1024)
                if not block:
                    return result.hexdigest()
                result.update(block)
    cache = destination.with_suffix(destination.suffix + '.web.json')
    signature = {'profile': 'h264-aac-yuv420p-faststart-v1', 'source': digest(source)}
    try:
        saved = json.loads(cache.read_text())
        if all(saved.get(key) == value for key, value in signature.items()) and saved.get('output') == digest(destination):
            return destination
    except (OSError, ValueError, AttributeError):
        pass
    ffmpeg = ffmpeg or bundled_ffmpeg()
    probe = None
    if ffmpeg:
        sibling = Path(ffmpeg).with_name('ffprobe.exe' if os.name == 'nt' else 'ffprobe')
        probe = str(sibling) if sibling.is_file() else shutil.which('ffprobe')
    compatible = False
    if probe:
        try:
            data = json.loads(subprocess.run([probe, '-v', 'error', '-show_streams', '-of', 'json', str(source)],
                capture_output=True, text=True, timeout=15,
                creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0) if os.name == 'nt' else 0).stdout)
            streams = data.get('streams', [])
            videos = [v for v in streams if v.get('codec_type') == 'video']
            audio = [a for a in streams if a.get('codec_type') == 'audio']
            compatible = (len(videos) == 1 and videos[0].get('codec_name') == 'h264'
                and videos[0].get('pix_fmt') == 'yuv420p'
                and videos[0].get('color_transfer') not in ('smpte2084', 'arib-std-b67')
                and all(a.get('codec_name') == 'aac' for a in audio))
        except (OSError, ValueError, subprocess.TimeoutExpired, AttributeError):
            pass
    if compatible:
        destination.parent.mkdir(parents=True, exist_ok=True)
        fd, name = tempfile.mkstemp(prefix='.remux-', suffix='.mp4', dir=destination.parent)
        os.close(fd)
        temporary = Path(name)
        try:
            from ffmpeg_progress import monitor
            command = [ffmpeg, '-hide_banner', '-loglevel', 'error', '-nostdin', '-y', '-i', str(source),
                       '-map', '0:v:0', '-map', '0:a:0?', '-c', 'copy', '-movflags', '+faststart', str(temporary)]
            if cancelled and cancelled():
                raise RuntimeError('Videokonvertering avbruten')
            process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                text=True, errors='replace', creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0) if os.name == 'nt' else 0)
            monitor(process, cancelled=cancelled)
            if not temporary.stat().st_size:
                raise RuntimeError('Tom MP4 efter ompackning')
            temporary.replace(destination)
        finally:
            temporary.unlink(missing_ok=True)
    elif cancelled is None:
        quicktime_to_mp4(source, destination, ffmpeg)
    else:
        quicktime_to_mp4(source, destination, ffmpeg, cancelled=cancelled)
    if destination.is_file():
        signature['output'] = digest(destination)
        temporary_cache = cache.with_suffix(cache.suffix + '.tmp')
        try:
            temporary_cache.write_text(json.dumps(signature), encoding='utf-8')
            temporary_cache.replace(cache)
        finally:
            temporary_cache.unlink(missing_ok=True)
    return destination
