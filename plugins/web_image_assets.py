# Copyright (c) 2026 Rickard Längkvist
"""Responsive derivatives, optional downloads and an honest image-size report."""
import html
import json
from pathlib import Path
import re
import shutil

DOWNLOAD_MODES = ('off', '1280', '1920', 'original')
WIDTHS = (480, 960, 1600)


def export_options(gallery):
    mode = gallery.get('download_mode', 'off')
    if mode not in DOWNLOAD_MODES:
        mode = 'off'
    return {'responsive_images': bool(gallery.get('responsive_images', True)), 'download_mode': mode}


def _write(path, content):
    temporary = path.with_name(path.name + '.tmp')
    temporary.write_text(content, encoding='utf-8')
    temporary.replace(path)


def _save(image, path, size, quality):
    from PIL import Image
    copy = image.copy()
    try:
        copy.thumbnail(size, Image.Resampling.LANCZOS)
        if path.suffix == '.jpg' and copy.mode != 'RGB':
            converted = copy.convert('RGB')
            copy.close()
            copy = converted
        # Pillow can automatically re-emit PNG EXIF from image.info.
        # Resized downloads/variants must not inherit private source metadata.
        copy.info.clear()
        if path.suffix == '.jpg':
            copy.save(path, 'JPEG', quality=quality, optimize=True, progressive=True)
        else:
            copy.save(path, 'PNG', optimize=True)
        return copy.size
    finally:
        copy.close()


def prepare_assets(entries, output, output_format, gallery, context=None, log=None):
    """Only generate from existing source pixels: never upscale or crop."""
    from PIL import Image, ImageOps
    output = Path(output)
    options = export_options(gallery)
    quality = max(40, min(100, int(gallery.get('jpeg_quality') or 85)))
    context = context if context is not None else {}
    originals = context.get('original_sources')
    managed = set()
    rows = []
    for entry in entries:
        full = Path(entry['full_dst'])
        original = Path(entry.get('original_path') or entry.get('full_src') or full)
        if originals is not None:
            value = originals.get(str(original.resolve()), '')
            original = Path(value) if value else None
        original_exists = original is not None and original.is_file()
        source_bytes = original.stat().st_size if original_exists else full.stat().st_size
        entry['variants'] = []
        entry['download'] = ''
        entry['download_label'] = ''
        entry['original_download'] = ''
        warnings = []
        with Image.open(full) as opened:
            animated = getattr(opened, 'n_frames', 1) > 1
            image = ImageOps.exif_transpose(opened)
            try:
                width, height = image.size
                entry['image_width'], entry['image_height'] = width, height
                alpha = image.mode in ('RGBA', 'LA') or 'transparency' in image.info
                extension = '.png' if alpha else '.jpg'
                if options['responsive_images'] and not animated:
                    for target_width in WIDTHS:
                        if target_width >= width:
                            continue
                        name = '%s-%d%s' % (entry['index'], target_width, extension)
                        relative = Path('responsive') / name if output_format == 'standard' else Path('responsive_' + name)
                        target = output / relative
                        target.parent.mkdir(parents=True, exist_ok=True)
                        actual, _ = _save(image, target, (target_width, max(1, round(height * target_width / width))), quality)
                        managed.add(relative.as_posix())
                        entry['variants'].append({'src': relative.as_posix(), 'width': actual, 'bytes': target.stat().st_size})
                elif animated:
                    warnings.append('Animerad bild: behåller animationen, inga statiska webbvarianter.')

                mode = options['download_mode']
                if mode != 'off':
                    if mode == 'original':
                        if not original_exists:
                            raise ValueError('Originalbild saknas för %s. Välj 1280/1920 px eller stäng av nedladdning.' % entry.get('original_name', full.name))
                        extension = original.suffix.lower()
                    name = str(entry['index']) + extension
                    relative = Path('downloads') / name if output_format == 'standard' else Path('download_' + name)
                    target = output / relative
                    target.parent.mkdir(parents=True, exist_ok=True)
                    if mode == 'original':
                        if original.resolve() != target.resolve():
                            shutil.copy2(original, target)
                        entry['original_download'] = relative.as_posix()
                        label = 'Ladda ned original'
                    elif animated:
                        warnings.append('Animerad bild: nedskalad nedladdning stöds inte; välj original för att behålla animationen.')
                        target = None
                    else:
                        size = _save(image, target, (int(mode), int(mode)), quality)
                        label = 'Ladda ned (%d × %d px)' % size
                    if target is not None:
                        managed.add(relative.as_posix())
                        entry['download'] = relative.as_posix()
                        entry['download_label'] = label
            finally:
                image.close()
        web_bytes = full.stat().st_size
        thumb_bytes = Path(entry['thumb_dst']).stat().st_size
        variant_bytes = sum(item['bytes'] for item in entry['variants'])
        download_bytes = (output / entry['download']).stat().st_size if entry['download'] else 0
        if web_bytes > 1024 * 1024:
            warnings.append('Webbild över 1 MiB.')
        if web_bytes >= source_bytes and source_bytes > 300 * 1024:
            warnings.append('Webbilden är inte mindre än jämförelsekällan.')
        rows.append({'image': entry.get('original_name', full.name), 'width': entry['image_width'],
                     'height': entry['image_height'], 'source_bytes': source_bytes,
                     'source_kind': 'original' if original_exists else 'exported_image',
                     'web_bytes': web_bytes, 'thumbnail_bytes': thumb_bytes,
                     'responsive_bytes': variant_bytes, 'download_bytes': download_bytes,
                     'total_export_bytes': web_bytes + thumb_bytes + variant_bytes + download_bytes,
                     'saved_bytes': source_bytes - web_bytes,
                     'saved_percent': round((1 - web_bytes / source_bytes) * 100, 1) if source_bytes else 0,
                     'warnings': warnings})

    # Remove only our numbered derivatives; never arbitrary user-owned files.
    candidates = []
    if output_format == 'standard':
        for folder in ('responsive', 'downloads'):
            candidates.extend((output / folder).glob('*'))
    else:
        candidates = list(output.glob('responsive_*')) + list(output.glob('download_*'))
    for path in candidates:
        relative = path.relative_to(output).as_posix()
        own = re.fullmatch(r'(?:responsive/|responsive_)\d+-\d+\.(?:jpg|png)', relative)
        own = own or re.fullmatch(r'(?:downloads/|download_)\d+\.[a-z0-9]+', relative)
        if own and path.is_file() and relative not in managed:
            path.unlink()
    totals = {key: sum(row[key] for row in rows) for key in (
        'source_bytes', 'web_bytes', 'thumbnail_bytes', 'responsive_bytes', 'download_bytes', 'total_export_bytes', 'saved_bytes')}
    totals['saved_percent'] = round(totals['saved_bytes'] / totals['source_bytes'] * 100, 1) if totals['source_bytes'] else 0
    report = {'version': 1, 'options': options, 'totals': totals, 'images': rows}
    _write(output / 'optimization-report.json', json.dumps(report, ensure_ascii=False, indent=2))
    _write(output / 'optimization-report.html', report_html(report))
    if log:
        log('  Bildrapport: källa %.2f MiB, webbilder %.2f MiB, alla exporterade bildfiler %.2f MiB.' % (
            totals['source_bytes'] / 1048576, totals['web_bytes'] / 1048576, totals['total_export_bytes'] / 1048576))
        count = sum(bool(row['warnings']) for row in rows)
        if count:
            log('  [!] %d bilder har noteringar; se optimization-report.html.' % count)
    return report


def report_html(report):
    totals = report['totals']
    rows = []
    for row in report['images']:
        rows.append('<tr><td>%s</td><td>%d × %d</td><td>%.1f</td><td>%.1f</td><td>%.1f</td><td>%.1f%%</td><td>%.1f</td><td>%s</td></tr>' % (
            html.escape(row['image']), row['width'], row['height'], row['source_bytes'] / 1024,
            row['web_bytes'] / 1024, row['saved_bytes'] / 1024, row['saved_percent'], row['total_export_bytes'] / 1024,
            html.escape(('Källa: exporterad webbild. ' if row['source_kind'] == 'exported_image' else '') + ' '.join(row['warnings']))))
    return '''<!doctype html><html lang="sv"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Bildoptimeringsrapport</title><style>body{font:16px system-ui;margin:2rem;color:#172033;background:#f6f8fc}main{max-width:1200px;margin:auto}table{border-collapse:collapse;background:white;width:100%%}th,td{text-align:left;padding:12px;border-bottom:1px solid #dae0e8}.table{overflow:auto}a{color:#174dcc}</style>
<main><h1>Bildoptimeringsrapport</h1><p>Källfiler: %.2f MiB · Webbilder: %.2f MiB · Alla exporterade bildfiler: %.2f MiB</p><p>Sparat (källa − webbild): %.2f MiB (%.1f%%)</p><p>Miniatyrer: %.2f MiB · Responsiva varianter: %.2f MiB · Nedladdningar: %.2f MiB</p>
<p>Besparingen jämför källfilen med fullstor webbild. Miniatyrer, webbvarianter och nedladdningar tar ytterligare utrymme och ingår i totalen. Vid redigering kan källan vara en tidigare exporterad bild. Negativ besparing betyder större fil. Rapporten mäter inte visuell kvalitet.</p>
<div class="table"><table><thead><tr><th>Bild</th><th>Webbmått</th><th>Källa KiB</th><th>Webb KiB</th><th>Sparat KiB</th><th>Besparing</th><th>Totalt KiB</th><th>Notering</th></tr></thead><tbody>%s</tbody></table></div><p><a href="index.html">Till galleriet</a></p></main></html>''' % (
        totals['source_bytes'] / 1048576, totals['web_bytes'] / 1048576, totals['total_export_bytes'] / 1048576,
        totals['saved_bytes'] / 1048576, totals['saved_percent'],
        totals['thumbnail_bytes'] / 1048576, totals['responsive_bytes'] / 1048576,
        totals['download_bytes'] / 1048576, ''.join(rows))


def responsive_srcset(entry, full_url):
    variants = entry.get('variants', [])
    if not variants:
        return ''
    choices = [(item['src'], item['width']) for item in variants]
    choices.append((full_url, entry['image_width']))
    return ', '.join('%s %dw' % pair for pair in choices)


def responsive_attributes(entry, full_url, sizes='auto, (max-width: 600px) 100vw, (max-width: 1100px) 50vw, 33vw'):
    srcset = responsive_srcset(entry, full_url)
    if not srcset:
        return ''
    return ' srcset="%s" sizes="%s"' % (html.escape(srcset, quote=True), html.escape(sizes, quote=True))


DOWNLOAD_LABELS = {'off': 'Avstängd', '1280': '1280 px (längsta sidan)',
                   '1920': '1920 px (längsta sidan)', 'original': 'Originalfil'}


def download_mode(label):
    return next((key for key, value in DOWNLOAD_LABELS.items() if value == label), 'off')


def create_controls(parent, gallery):
    """Shared app/editor controls; importing this module needs neither Tk nor Pillow."""
    import tkinter as tk
    from tkinter import ttk
    options = export_options(gallery)
    frame = ttk.Frame(parent)
    frame.pack(fill='x', pady=6)
    responsive = tk.BooleanVar(master=parent, value=options['responsive_images'])
    download = tk.StringVar(master=parent, value=DOWNLOAD_LABELS[options['download_mode']])
    ttk.Checkbutton(frame, text='Responsiva webbilder (480, 960 och 1600 px breda)',
                    variable=responsive).pack(anchor='w')
    row = ttk.Frame(frame)
    row.pack(fill='x', pady=4)
    ttk.Label(row, text='Besökares nedladdning:').pack(side='left', padx=(0, 8))
    ttk.Combobox(row, state='readonly', textvariable=download,
                 values=list(DOWNLOAD_LABELS.values()), width=27).pack(side='left')
    ttk.Label(frame, text='Ingen uppskalning. 1280/1920 px utgår från webbilden och kan bli mindre. '
              'Originalfil kopieras oförändrad och kan innehålla EXIF/GPS. '
              'Avstängd döljer knappen, men skyddar inte bilder från att sparas.',
              wraplength=650, justify='left').pack(anchor='w', pady=3)
    return responsive, download


def open_report(parent, path=None):
    import webbrowser
    from tkinter import filedialog
    path = Path(path) if path else None
    if not path or not path.is_file():
        selected = filedialog.askopenfilename(parent=parent, title='Öppna bildoptimeringsrapport',
                   initialfile='optimization-report.html', filetypes=[('Bildrapport', 'optimization-report.html')])
        if not selected:
            return
        path = Path(selected)
    webbrowser.open(path.resolve().as_uri())
