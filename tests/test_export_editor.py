import json
from pathlib import Path
import tempfile
import unittest
from plugins.export_editor import load_project, save_project, write_manifest, MANIFEST


class FakeGenerator:
    VIDEO_FORMATS = {'.mp4'}

    def execute(self, context):
        output = Path(context['gallery']['output_path'])
        image_dir = output / 'image'
        image_dir.mkdir(exist_ok=True)
        # Simulate generator replacement from original sources, including renumbering.
        contents = [Path(p).read_bytes() for p in context['sorted_images']]
        for old in image_dir.glob('*'):
            old.unlink()
        entries = []
        for i, content in enumerate(contents, 1):
            target = image_dir / ('%d.jpg' % i)
            target.write_bytes(content)
            entries.append({'full_dst': str(target)})
        (output / 'index.html').write_text('updated')
        write_manifest(output, entries, context['gallery'], 'standard', context)
        context['html_output'] = output / 'index.html'
        return context


class ExportEditorTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name) / 'export'
        (self.folder / 'image').mkdir(parents=True)
        (self.folder / 'image/1.jpg').write_bytes(b'first')
        (self.folder / 'image/2.jpg').write_bytes(b'second')
        (self.folder / 'index.html').write_text('<title>Galleri &amp; bilder</title><img src="image/2.jpg"><img src="image/1.jpg">')

    def test_legacy_preserves_display_order(self):
        data, images = load_project(self.folder)
        self.assertEqual([p.name for p in images], ['2.jpg', '1.jpg'])
        self.assertEqual(data['gallery']['title'], 'Galleri & bilder')

    def test_flat_legacy(self):
        (self.folder / 'full_1.jpg').write_bytes(b'flat')
        (self.folder / 'index.html').write_text('<img src="full_1.jpg"><img src="thumb_1.jpg">')
        data, images = load_project(self.folder)
        self.assertEqual([p.name for p in images], ['full_1.jpg'])

    def test_manifest_rejects_path_traversal(self):
        (self.folder / MANIFEST).write_text(json.dumps({'images': ['../../outside.jpg']}))
        with self.assertRaises(ValueError):
            load_project(self.folder)

    def test_remove_add_save_and_backup(self):
        data, images = load_project(self.folder)
        added = Path(self.temp.name) / 'new.jpg'
        added.write_bytes(b'new')
        backup = save_project(self.folder, data, [images[0], added], FakeGenerator())
        self.assertEqual((self.folder / 'image/1.jpg').read_bytes(), b'second')
        self.assertEqual((self.folder / 'image/2.jpg').read_bytes(), b'new')
        self.assertEqual((backup / 'image/1.jpg').read_bytes(), b'first')
        self.assertEqual(added.read_bytes(), b'new')
        _, loaded = load_project(self.folder)
        self.assertEqual(len(loaded), 2)

    def test_error_leaves_original_untouched(self):
        class Broken(FakeGenerator):
            def execute(self, context):
                raise OSError('disk failure')
        original = (self.folder / 'index.html').read_bytes()
        data, images = load_project(self.folder)
        with self.assertRaises(OSError):
            save_project(self.folder, data, images, Broken())
        self.assertEqual((self.folder / 'index.html').read_bytes(), original)
        self.assertEqual(list(self.folder.parent.glob('.gallery-edit-*')), [])

    def test_empty_gallery_rejected(self):
        with self.assertRaises(ValueError):
            save_project(self.folder, {}, [], FakeGenerator())
