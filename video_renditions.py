# Copyright (c) 2026 Rickard Längkvist
"""Cached, cancellable, no-upscale MP4 variants. Sequential by design."""
import hashlib
import json
import os
from pathlib import Path
import quiet_process as subprocess
import tempfile
from ffmpeg_progress import monitor
from resource_profiles import ffmpeg_args


def fingerprint(path, cancelled):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        while True:
            if cancelled and cancelled(): raise RuntimeError('Videovarianter avbrutna')
            chunk = stream.read(1024*1024)
            if not chunk: return digest.hexdigest()
            digest.update(chunk)


def create_renditions(videos, output, heights, ffmpeg, cancelled=None, progress=None):
    output = Path(output)
    for index, video in enumerate(videos, 1):
        source = output / video['relative_path']
        signature = fingerprint(source, cancelled) if heights else None
        video['qualities'] = {}
        for height in heights:
            if height not in (480,720,1080): raise ValueError('Ogiltig videohöjd')
            if progress: progress(None, 'Videokvalitet %dp – %d/%d' % (height,index,len(videos)))
            dest = source.with_name(source.stem + '.%dp.mp4' % height)
            cache = dest.with_suffix('.cache.json')
            expected = {'profile': 'h264-aac-no-upscale-v1', 'source': signature, 'height': height}
            try:
                saved = json.loads(cache.read_text())
                valid = all(saved.get(k) == v for k,v in expected.items()) and saved.get('output') == fingerprint(dest,cancelled)
            except (ValueError,OSError,AttributeError): valid = False
            if not valid:
                fd,name = tempfile.mkstemp(prefix='.rendition-',suffix='.mp4',dir=dest.parent)
                os.close(fd)
                temporary = Path(name)
                try:
                    if cancelled and cancelled(): raise RuntimeError('Videovarianter avbrutna')
                    command = [str(ffmpeg),'-nostdin','-hide_banner','-loglevel','error','-y','-i',str(source),
                               '-map','0:v:0','-map','0:a:0?','-vf',"scale=-2:'min(ih,%d)'" % height,
                               '-c:v','libx264','-crf','23','-pix_fmt','yuv420p','-c:a','aac','-movflags','+faststart',
                               *ffmpeg_args(),str(temporary)]
                    process = subprocess.Popen(command,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,errors='replace',
                        creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0) if os.name=='nt' else 0)
                    monitor(process,cancelled=cancelled)
                    if not temporary.stat().st_size: raise RuntimeError('Tom videovariant')
                    temporary.replace(dest)
                    expected['output'] = fingerprint(dest,cancelled)
                    cache.write_text(json.dumps(expected),encoding='utf-8')
                finally: temporary.unlink(missing_ok=True)
            video['qualities']['Max %dp' % height] = dest.relative_to(output).as_posix()
