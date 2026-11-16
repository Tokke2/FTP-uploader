# Copyright (c) 2026 Rickard Längkvist
"""Reopen exported galleries without running the upload/processing pipeline."""
import json
from media_support import register_heif
register_heif()
from html.parser import HTMLParser
from pathlib import Path
import shutil
import tempfile
from datetime import datetime

MANIFEST = 'gallery-project.json'
FORMATS = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp', '.tif', '.heic', '.heif', '.tiff'}


def local_file(root, name):
    path = (root / name).resolve()
    if not path.is_relative_to(root.resolve()) or not path.is_file():
        raise ValueError('Ogiltig eller saknad exportfil: %s' % name)
    return path


class LegacyGallery(HTMLParser):
    def __init__(self):
        super().__init__()
        self.images = []
        self.title = ''
        self.in_title = False

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'title':
            self.in_title = True
        if tag == 'img':
            src = attrs.get('src', '')
            if src.startswith('image/') or src.startswith('full_'):
                if src not in self.images:
                    self.images.append(src)

    def handle_endtag(self, tag):
        if tag == 'title':
            self.in_title = False

    def handle_data(self, data):
        if self.in_title:
            self.title += data


def load_project(folder):
    folder = Path(folder).resolve()
    index = folder / 'index.html'
    if not index.is_file():
        raise ValueError('Mappen saknar index.html.')
    manifest = folder / MANIFEST
    if manifest.exists():
        data = json.loads(manifest.read_text(encoding='utf-8'))
        images = [local_file(folder, name) for name in data['images']]
    else:
        parser = LegacyGallery()
        parser.feed(index.read_text(encoding='utf-8'))
        images = [local_file(folder, name) for name in parser.images]
        if not images:
            raise ValueError('Inga exporterade bilder hittades. Stöder appens standard- och flat-export.')
        data = {'gallery': {'title': parser.title, 'description': '', 'theme': 'dark', 'columns': 6},
                'output_format': 'standard' if (folder / 'image').is_dir() else 'flat'}
    return data, images


def write_manifest(output, entries, gallery, output_format, context):
    output = Path(output)
    data = {'version': 2, 'gallery': {key: gallery.get(key) for key in
            ('title', 'description', 'theme', 'columns', 'jpeg_quality')}, 'output_format': output_format,
            'images': [str(Path(entry['full_dst']).relative_to(output).as_posix()) for entry in entries]}
    from .web_image_assets import export_options
    from .gallery_checks import cover_options
    number, url = cover_options(gallery)
    data['gallery'].update(cover_image=number, public_url=url)
    data['assets'] = (['cover.jpg'] if entries else []) + [v['src'] for entry in entries for v in entry.get('variants', [])]
    data['assets'] += [entry['download'] for entry in entries if entry.get('download')]
    data['gallery'].update(export_options(gallery))
    # Only exported original copies are portable. Never persist absolute local paths.
    data['originals'] = {Path(entry['full_dst']).relative_to(output).as_posix(): entry['original_download']
                         for entry in entries if entry.get('original_download')}
    for key in ('custom_css', 'custom_html_header', 'custom_html_footer'):
        data[key] = context.get(key, '')
    temporary = output / (MANIFEST + '.tmp')
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    temporary.replace(output / MANIFEST)


def save_project(folder, data, images, generator):
    folder = Path(folder).resolve()
    if not images:
        raise ValueError('Behåll minst en bild i galleriet.')
    for image in images:
        if not Path(image).is_file():
            raise ValueError('Bilden saknas: %s' % image)
    stage = Path(tempfile.mkdtemp(prefix='.gallery-edit-', dir=folder.parent))
    backup = folder.with_name(folder.name + '.backup-' + datetime.now().strftime('%Y%m%d-%H%M%S-%f'))
    try:
        shutil.copytree(folder, stage, dirs_exist_ok=True)
        # Never let size/mtime copy optimizations reuse the wrong numbered image
        # after reordering. Sources still live in the untouched original folder.
        if data.get('output_format', 'standard') == 'standard':
            candidates = list((stage / 'image').glob('*')) + list((stage / 'thumb').glob('*'))
        else:
            candidates = list(stage.glob('full_*')) + list(stage.glob('thumb_*'))
        for candidate in candidates:
            if candidate.is_file() and candidate.suffix.lower() in FORMATS:
                candidate.unlink()
        context = {key: data.get(key, '') for key in ('custom_css', 'custom_html_header', 'custom_html_footer')}
        context['gallery'] = dict(data.get('gallery', {}), images_path=str(folder), output_path=str(stage),
                                  output_format=data.get('output_format', 'standard'))
        context['output_format'] = data.get('output_format', 'standard')
        context['_defer_learning'] = True
        context['sorted_images'] = list(images)
        # An exported web image is NOT the camera original. Preserve genuine originals
        # across reordering through the old manifest, and accept newly added local files.
        exported = {str((folder / name).resolve()) for name in data.get('images', [])}
        if not exported:
            _, previous_images = load_project(folder)
            exported = {str(path.resolve()) for path in previous_images}
        original_map = {}
        for name, original in data.get('originals', {}).items():
            key = str((folder / name).resolve())
            try:
                original_map[key] = str(local_file(folder, original))
            except ValueError:
                pass  # Missing original must be reported, never silently substituted.
        context['original_sources'] = {
            str(Path(image).resolve()): original_map.get(str(Path(image).resolve()), '')
            if str(Path(image).resolve()) in exported else str(Path(image).resolve())
            for image in images}
        context['pdf_files'] = list(folder.rglob('*.pdf'))
        context['video_files'] = [p for p in folder.rglob('*') if p.suffix.lower() in generator.VIDEO_FORMATS]
        result = generator.execute(context)
        if not result.get('html_output') or not (stage / MANIFEST).is_file():
            raise RuntimeError('Exporten kunde inte genereras. Originalet är orört.')
        folder.rename(backup)
        try:
            stage.rename(folder)
        except Exception:
            backup.rename(folder)
            raise
        from local_learning import record_export
        if result.get('optimization_report'):
            record_export(context['gallery'], result['optimization_report'])
        return backup
    finally:
        if stage.exists():
            shutil.rmtree(stage)


def open_editor(parent):
    import tkinter as tk
    from tkinter import filedialog, messagebox, ttk
    from .html_generator import HtmlGenerator
    folder = filedialog.askdirectory(title='Öppna exporterad gallerimapp', parent=parent)
    if not folder:
        return
    try:
        data, images = load_project(folder)
    except Exception as exc:
        messagebox.showerror('Öppna galleri', str(exc), parent=parent)
        return
    if not (Path(folder) / MANIFEST).exists():
        if not messagebox.askyesno('Äldre export',
                'Bilder och ordning kan läsas in. Äldre exporter saknar projektdata; '
                'tema, beskrivning och egen HTML/CSS kan behöva återskapas. '
                'Den gamla exporten säkerhetskopieras vid sparning. Fortsätt?', parent=parent):
            return
    window = tk.Toplevel(parent)
    window.title('Redigera export – ' + str(folder))
    window.geometry('1040x720')
    window.minsize(760, 540)
    title = tk.StringVar(value=data.get('gallery', {}).get('title') or '')
    description = tk.StringVar(value=data.get('gallery', {}).get('description') or '')
    from .web_image_assets import create_controls, download_mode, open_report
    options_frame = ttk.Frame(window)
    # Pack below title/description entries after those widgets are created.
    responsive, download = create_controls(options_frame, data.get('gallery', {}))
    from .gallery_checks import create_cover_controls, open_link_report
    cover, public_url = create_cover_controls(options_frame, data.get('gallery', {}))
    ttk.Button(options_frame, text='Öppna länkkontroll', command=lambda: open_link_report(
        window, Path(folder) / 'link-report.html')).pack(anchor='w')
    def snapshot():
        return (tuple(images), title.get(), description.get(), responsive.get(), download.get(), cover.get(), public_url.get())
    initial = snapshot()
    window._has_unsaved_changes = lambda: snapshot() != initial

    def cancel():
        if not window._has_unsaved_changes() or messagebox.askyesno(
                'Osparade ändringar', 'Kasta ändringarna och stäng redigeraren?', parent=window):
            window.destroy()

    window.protocol('WM_DELETE_WINDOW', cancel)
    for text, variable in [('Titel', title), ('Beskrivning', description)]:
        ttk.Label(window, text=text).pack(anchor='w', padx=12)
        ttk.Entry(window, textvariable=variable).pack(fill='x', padx=12, pady=4)
    options_frame.pack(fill='x', padx=12)
    from PIL import Image, ImageTk, ImageOps
    body = ttk.Panedwindow(window, orient='horizontal')
    body.pack(fill='both', expand=True, padx=12, pady=8)
    browser = ttk.Frame(body)
    inspector = ttk.Frame(body, padding=12)
    body.add(browser, weight=3)
    body.add(inspector, weight=2)
    style_name = 'ExportEditor%d.Treeview' % id(window)
    ttk.Style(window).configure(style_name, rowheight=66)
    listing = ttk.Treeview(browser, selectmode='extended', columns=('number',),
                          style=style_name, show='tree headings')
    listing.heading('#0', text='Bilder – välj för förhandsvisning')
    listing.heading('number', text='Nr')
    listing.column('#0', width=300, minwidth=140)
    listing.column('number', width=45, stretch=False)
    scrollbar = ttk.Scrollbar(browser, orient='vertical', command=listing.yview)
    listing.configure(yscrollcommand=scrollbar.set)
    scrollbar.pack(side='right', fill='y')
    listing.pack(fill='both', expand=True)
    preview = ttk.Label(inspector, text='Välj en bild för förhandsvisning', anchor='center')
    preview.pack(fill='both', expand=True)
    details = ttk.Label(inspector, text='', wraplength=290, justify='left')
    details.pack(fill='x', pady=12)
    ttk.Label(inspector, text='Ctrl/⌘ eller Shift: markera flera.\nUpp/Ned-knapparna ändrar bildordningen.',
              wraplength=290).pack(anchor='w')
    status = tk.StringVar()
    ttk.Label(window, textvariable=status).pack(anchor='w', padx=12)
    thumbnails = {}

    def selected():
        return sorted(int(item) for item in listing.selection())

    def show_preview(event=None):
        selection = selected()
        if not selection:
            preview.configure(image='', text='Välj en bild för förhandsvisning')
            preview.image = None
            details.configure(text='')
            return
        path = images[selection[0]]
        try:
            with Image.open(path) as source:
                width, height = source.size
                image = ImageOps.exif_transpose(source)
                image.thumbnail((340, 360))
                photo = ImageTk.PhotoImage(image, master=window)
            preview.configure(image=photo, text='')
            preview.image = photo
            details.configure(text='%s\n%d × %d px · %.1f MB\n%d markerade' % (
                path.name, width, height, path.stat().st_size / 1048576, len(selection)))
        except Exception:
            preview.configure(image='', text='Bilden kan inte visas')
            preview.image = None
            details.configure(text=path.name)

    listing.bind('<<TreeviewSelect>>', show_preview)

    def refresh():
        listing.delete(*listing.get_children())
        for number, image in enumerate(images, 1):
            if image not in thumbnails:
                try:
                    with Image.open(image) as source:
                        thumb = ImageOps.exif_transpose(source)
                        thumb.thumbnail((56, 56))
                        thumbnails[image] = ImageTk.PhotoImage(thumb, master=window)
                except Exception:
                    thumbnails[image] = None
            options = {'image': thumbnails[image]} if thumbnails[image] is not None else {}
            listing.insert('', 'end', iid=str(number - 1), text=image.name,
                           values=(number,), **options)
        status.set('%d bilder · Borttagning ändrar bara exporten, inte originalbilderna.' % len(images))
        show_preview()

    def add():
        paths = filedialog.askopenfilenames(parent=window, title='Lägg till bilder',
                    filetypes=[('Bilder', '*.jpg *.jpeg *.png *.gif *.webp *.bmp *.tif *.tiff *.heic *.heif')])
        for path in paths:
            image = Path(path).resolve()
            if image.suffix.lower() in FORMATS and image not in images:
                images.append(image)
        refresh()

    def remove():
        for index in reversed(selected()):
            del images[index]
        refresh()

    def move(delta):
        selection = selected()
        if len(selection) != 1:
            return
        index = selection[0]
        target = index + delta
        if 0 <= target < len(images):
            images[index], images[target] = images[target], images[index]
            refresh()
            listing.selection_set(str(target))
            listing.see(str(target))

    def save():
        if not messagebox.askyesno('Spara export', 'Skriv om exporten? Den gamla mappen sparas som säkerhetskopia.', parent=window):
            return
        data.setdefault('gallery', {}).update(title=title.get(), description=description.get(),
                                             responsive_images=responsive.get(), download_mode=download_mode(download.get()),
                                             cover_image=cover.get(), public_url=public_url.get().strip())
        try:
            backup = save_project(folder, data, images, HtmlGenerator())
            messagebox.showinfo('Sparat', 'Exporten uppdaterad.\nSäkerhetskopia: %s' % backup, parent=window)
            window.destroy()
        except Exception as exc:
            messagebox.showerror('Kunde inte spara', str(exc), parent=window)

    buttons = ttk.Frame(window)
    buttons.pack(fill='x', padx=12, pady=12)
    for text, command in [('Lägg till bilder', add), ('Ta bort valda', remove), ('Upp', lambda: move(-1)),
                          ('Ned', lambda: move(1)), ('Bildrapport', lambda: open_report(window, Path(folder) / 'optimization-report.html')),
                          ('Spara export', save), ('Avbryt', cancel)]:
        ttk.Button(buttons, text=text, command=command).pack(side='left', padx=3)
    refresh()
