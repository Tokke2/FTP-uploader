# Copyright (c) 2026 Rickard Längkvist
"""Choose a real, nonblank video frame with bounded candidate extraction."""
from pathlib import Path
import os
import quiet_process as subprocess
import tempfile


def frame_score(image):
    from PIL import ImageStat, ImageFilter
    gray = image.convert('L')
    gray.thumbnail((160, 100))
    stats = ImageStat.Stat(gray)
    histogram = gray.histogram()
    total = max(1, sum(histogram))
    clipped = (sum(histogram[:16]) + sum(histogram[240:])) / total
    edges = ImageStat.Stat(gray.filter(ImageFilter.FIND_EDGES)).mean[0]
    # Prefer detail/contrast and penalize near-black/white intro frames.
    return stats.stddev[0] + edges * 0.6 - clipped * 45


def choose_video_thumbnail(source, destination, ffmpeg, cancelled=None):
    from PIL import Image
    from ffmpeg_progress import duration_from_ffmpeg, monitor
    if not ffmpeg:
        return False
    flags = getattr(subprocess, 'CREATE_NO_WINDOW', 0) if os.name == 'nt' else 0
    if cancelled and cancelled():
        raise RuntimeError('Videominiatyr avbruten')
    try:
        duration = duration_from_ffmpeg(ffmpeg, source, flags)
    except (OSError, subprocess.TimeoutExpired, ValueError):
        duration = 0
    candidates = [0, 1] if not duration else [duration * p for p in (0.08, 0.25, 0.5, 0.75)]
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    best = None
    best_score = float('-inf')
    with tempfile.TemporaryDirectory(prefix='.video-frames-', dir=destination.parent) as folder:
        for index, seconds in enumerate(candidates):
            if cancelled and cancelled():
                raise RuntimeError('Videominiatyr avbruten')
            candidate = Path(folder) / ('%d.jpg' % index)
            try:
                process = subprocess.Popen([ffmpeg, '-nostdin', '-hide_banner', '-loglevel', 'error', '-y',
                    '-ss', str(round(seconds, 3)), '-i', str(source), '-frames:v', '1',
                    '-vf', 'scale=640:-2', '-q:v', '4', str(candidate)],
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, errors='replace', creationflags=flags)
                monitor(process, cancelled=cancelled, timeout=20)
                if candidate.is_file():
                    with Image.open(candidate) as image:
                        score = frame_score(image)
                    if score > best_score:
                        best, best_score = candidate, score
            except (OSError, ValueError, RuntimeError, TimeoutError):
                if cancelled and cancelled():
                    raise RuntimeError('Videominiatyr avbruten')
                continue
        if best is not None:
            best.replace(destination)
            return True
    return False
