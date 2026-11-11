# Copyright (c) 2026 Rickard Längkvist
"""Portable cover metadata and offline validation of exported gallery links."""
import html
from html.parser import HTMLParser
import json
from pathlib import Path
from urllib.parse import urlsplit, urljoin, unquote


def cover_options(gallery):
    try:
        number = int(gallery.get('cover_image', 1))
        if number < 1:
            raise ValueError('Omslagsbildens nummer måste vara positivt.')
    except (ValueError, TypeError):
        raise ValueError('Omslagsbildens nummer måste vara ett positivt heltal.')
    url = str(gallery.get('public_url') or '').strip()
    if url:
        parsed = urlsplit(url)
        if parsed.scheme not in ('https', 'http') or not parsed.netloc or parsed.username or parsed.password or parsed.query or parsed.fragment:
            raise ValueError('Ange en publik HTTP/HTTPS-URL utan inloggning, frågedel eller fragment.')
    return number, url


def prepare_cover(entries, output, gallery, title, description):
    from PIL import Image, ImageOps
    number, url = cover_options(gallery)
    if number > len(entries):
        raise ValueError('Omslagsbild %d finns inte; galleriet har %d bilder.' % (number, len(entries)))
    with Image.open(entries[number - 1]['full_dst']) as source:
        image = ImageOps.exif_transpose(source).convert('RGBA')
        try:
            image.thumbnail((1200, 630), Image.Resampling.LANCZOS)
            with Image.new('RGB', (1200, 630), '#101827') as canvas:
                canvas.paste(image, ((1200 - image.width) // 2, (630 - image.height) // 2), image)
                canvas.save(Path(output) / 'cover.jpg', 'JPEG', quality=88, optimize=True)
        finally:
            image.close()
    if not url:
        return ''
    base = url if url.lower().endswith('.html') else url.rstrip('/') + '/'
    image_url = urljoin(base, 'cover.jpg')
    tags = {'og:url': base, 'og:image': image_url, 'og:image:width': '1200',
            'og:image:height': '630', 'og:image:alt': title}
    result = ['<meta property="%s" content="%s">' % (key, html.escape(value, quote=True)) for key, value in tags.items()]
    result += ['<meta name="twitter:image" content="%s">' % html.escape(image_url, quote=True),
               '<meta name="twitter:image:alt" content="%s">' % html.escape(title, quote=True)]
    return '\n'.join(result)


class References(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []
        self.ids = set()
    def handle_starttag(self, tag, attributes):
        attrs = dict(attributes)
        if attrs.get('id'):
            self.ids.add(attrs['id'])
        if tag == 'a' and attrs.get('name'):
            self.ids.add(attrs['name'])
        for key in ('src', 'href', 'poster'):
            if attrs.get(key):
                self.links.append(attrs[key])
        if attrs.get('srcset') and not attrs['srcset'].startswith('data:'):
            self.links.extend(item.strip().split()[0] for item in attrs['srcset'].split(',') if item.strip())


def check_links(output):
    """No network access; verify local references, fragments and manifest assets."""
    root = Path(output).resolve()
    parsed = {}
    for file in root.rglob('*.html'):
        parser = References()
        parser.feed(file.read_text(encoding='utf-8'))
        parsed[file.resolve()] = parser
    errors, external = [], set()
    checked = 0
    def check(source, reference):
        nonlocal checked
        try:
            parts = urlsplit(reference)
        except ValueError:
            errors.append({'source': source.relative_to(root).as_posix(), 'target': reference, 'reason': 'Ogiltig adress'})
            return
        if parts.scheme or parts.netloc:
            external.add(reference)
            return
        checked += 1
        path = unquote(parts.path)
        target = (source.parent / path).resolve() if path else source
        if target.is_dir():
            target = target / 'index.html'
        if not target.is_relative_to(root):
            errors.append({'source': source.relative_to(root).as_posix(), 'target': reference, 'reason': 'Utanför exportmappen'})
        elif not target.is_file():
            errors.append({'source': source.relative_to(root).as_posix(), 'target': reference, 'reason': 'Fil saknas'})
        elif parts.fragment and target in parsed:
            fragment = unquote(parts.fragment)
            # These routes are handled by the exported lightbox JavaScript.
            import re
            if fragment not in parsed[target].ids and not re.fullmatch(r'(?:bild|img|video)-[1-9]\d*', fragment):
                errors.append({'source': source.relative_to(root).as_posix(), 'target': reference, 'reason': 'Ankare saknas'})
    for source, parser in parsed.items():
        for reference in parser.links:
            check(source, reference)
    manifest = root / 'gallery-project.json'
    if manifest.is_file():
        data = json.loads(manifest.read_text(encoding='utf-8'))
        for reference in data.get('images', []) + list(data.get('originals', {}).values()) + data.get('assets', []):
            check(manifest, reference)
    report = {'version': 1, 'ok': not errors, 'checked': checked,
              'external_not_checked': len(external), 'errors': errors}
    (root / 'link-report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    rows = ''.join('<li>%s → %s: %s</li>' % tuple(html.escape(str(row[key])) for key in ('source', 'target', 'reason')) for row in errors)
    (root / 'link-report.html').write_text('<!doctype html><html lang="sv"><meta charset="utf-8"><title>Länkkontroll</title>'
        '<body><h1>Länkkontroll: %s</h1><p>%d lokala referenser kontrollerade. %d externa adresser kontrollerades inte.</p>'
        '<p>Kontrollen verifierar filer och HTML-ankare, inte JavaScript, CSS-url:er, nätverksåtkomst eller hur delningstjänster visar omslaget.</p><ul>%s</ul></body></html>'
        % ('OK' if report['ok'] else 'Fel hittades', checked, len(external), rows), encoding='utf-8')
    return report


def create_cover_controls(parent, gallery):
    import tkinter as tk
    from tkinter import ttk
    frame = ttk.Frame(parent)
    frame.pack(fill='x', pady=6)
    number = tk.StringVar(master=parent, value=str(gallery.get('cover_image', 1)))
    url = tk.StringVar(master=parent, value=gallery.get('public_url') or '')
    ttk.Label(frame, text='Omslagsbildens nummer i nuvarande bildordning:').pack(anchor='w')
    ttk.Spinbox(frame, from_=1, to=999999, textvariable=number, width=10).pack(anchor='w')
    ttk.Label(frame, text='Publicerad galleri-URL (för länkdelning, valfri):').pack(anchor='w')
    ttk.Entry(frame, textvariable=url).pack(fill='x')
    ttk.Label(frame, text='Exempel: https://example.se/galleri/ · Omslaget beskärs inte. '
              'Utan URL skapas cover.jpg, men inga bildtaggar för länkdelning.', wraplength=650).pack(anchor='w')
    return number, url


def open_link_report(parent, path=None):
    import webbrowser
    from tkinter import filedialog
    path = Path(path) if path else None
    if path is None or not path.is_file():
        chosen = filedialog.askopenfilename(parent=parent, title='Öppna länkkontroll',
                 initialfile='link-report.html', filetypes=[('Länkkontroll', 'link-report.html')])
        if not chosen:
            return
        path = Path(chosen)
    webbrowser.open(path.resolve().as_uri())
