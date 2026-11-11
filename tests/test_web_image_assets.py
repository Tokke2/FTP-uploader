# Copyright (c) 2026 Rickard Längkvist
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import types
import unittest
from unittest.mock import patch
from plugins.web_image_assets import export_options, prepare_assets, responsive_attributes
from plugins.export_editor import load_project, save_project, write_manifest, MANIFEST

try:
    from PIL import Image
except ImportError:
    Image = None


def generator_class():
    # Only the GUI base is replaced: exercise the real generator/templates/JS.
    base = types.ModuleType('plugins.base_plugin')
    base.BasePlugin = type('BasePlugin', (), {})
    with patch.dict(sys.modules, {'plugins.base_plugin': base}):
        spec = importlib.util.spec_from_file_location('plugins._headless_generator',
            Path(__file__).resolve().parents[1] / 'plugins/html_generator.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    return module.HtmlGenerator


class OptionTests(unittest.TestCase):
    def test_safe_defaults_and_invalid_download(self):
        self.assertEqual(export_options({}), {'responsive_images': True, 'download_mode': 'off'})
        self.assertEqual(export_options({'download_mode': '../../original'})['download_mode'], 'off')
        self.assertFalse(export_options({'responsive_images': False})['responsive_images'])


@unittest.skipIf(Image is None, 'Pillow required for real image tests')
class WebAssetTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.output = self.root / 'output'
        (self.output / 'image').mkdir(parents=True)
        (self.output / 'thumb').mkdir()
        self.original = self.root / 'private-original.bmp'
        with Image.new('RGB', (2400, 1800), '#306b98') as image:
            image.save(self.original)
            image.thumbnail((1920, 1440))
            image.save(self.output / 'image/1.jpg', quality=85)
            image.thumbnail((300, 300))
            image.save(self.output / 'thumb/1.jpg')
        self.entry = {'index': 1, 'original_path': str(self.original), 'original_name': '<photo>.bmp',
                      'full_dst': str(self.output / 'image/1.jpg'),
                      'thumb_dst': str(self.output / 'thumb/1.jpg')}

    def prepare(self, mode='off', responsive=True, fmt='standard', context=None):
        return prepare_assets([self.entry], self.output, fmt,
                              {'responsive_images': responsive, 'download_mode': mode}, context)

    def test_responsive_widths_dimensions_and_fallback(self):
        self.prepare()
        self.assertEqual([v['width'] for v in self.entry['variants']], [480, 960, 1600])
        for variant in self.entry['variants']:
            with Image.open(self.output / variant['src']) as image:
                self.assertEqual(image.size, (variant['width'], variant['width'] * 3 // 4))
                self.assertNotIn(274, image.getexif())
        attrs = responsive_attributes(self.entry, 'image/1.jpg')
        self.assertIn('image/1.jpg 1920w', attrs)
        self.assertIn('srcset=', attrs)
        self.assertEqual(self.entry['download'], '')
        self.assertFalse((self.output / 'downloads/1.jpg').exists())

    def test_no_upscale_and_no_crop(self):
        with Image.new('RGB', (320, 500)) as image:
            image.save(self.output / 'image/1.jpg')
        self.prepare('1920')
        self.assertEqual(self.entry['variants'], [])
        with Image.open(self.output / self.entry['download']) as image:
            self.assertEqual(image.size, (320, 500))
        self.assertIn('320 × 500', self.entry['download_label'])

    def test_download_resolutions(self):
        for mode, expected in [('1280', (1280, 960)), ('1920', (1920, 1440))]:
            with self.subTest(mode=mode):
                self.prepare(mode)
                with Image.open(self.output / self.entry['download']) as image:
                    self.assertEqual(image.size, expected)
                self.assertEqual(self.entry['original_download'], '')

    def test_original_is_byte_exact_not_the_web_image(self):
        self.prepare('original')
        target = self.output / self.entry['download']
        self.assertEqual(target.suffix, '.bmp')
        self.assertEqual(target.read_bytes(), self.original.read_bytes())
        self.assertEqual(self.entry['original_download'], self.entry['download'])

    def test_original_missing_never_substitutes_web_image(self):
        with self.assertRaisesRegex(ValueError, 'Originalbild saknas'):
            self.prepare('original', context={'original_sources': {str(self.original.resolve()): ''}})

    def test_report_counts_all_assets_and_savings_separately(self):
        report = self.prepare('1280')
        totals = report['totals']
        self.assertEqual(totals['saved_bytes'], self.original.stat().st_size - Path(self.entry['full_dst']).stat().st_size)
        image_files = [p for p in self.output.rglob('*') if p.is_file() and p.suffix in ('.jpg', '.png', '.bmp')]
        self.assertEqual(totals['total_export_bytes'], sum(p.stat().st_size for p in image_files))
        self.assertEqual(totals['total_export_bytes'], sum(totals[k] for k in
            ('web_bytes', 'thumbnail_bytes', 'responsive_bytes', 'download_bytes')))
        self.assertEqual(json.loads((self.output / 'optimization-report.json').read_text()), report)
        html = (self.output / 'optimization-report.html').read_text()
        self.assertIn('&lt;photo&gt;.bmp', html)
        self.assertNotIn('<photo>', html)
        self.assertIn('Sparat', html)
        self.assertNotIn(str(self.root), html)

    def test_exported_image_basis_is_explicit(self):
        report = self.prepare(context={'original_sources': {}})
        self.assertEqual(report['images'][0]['source_kind'], 'exported_image')
        self.assertEqual(report['totals']['saved_bytes'], 0)
        self.assertIn('Källa: exporterad webbild', (self.output / 'optimization-report.html').read_text())

    def test_disabling_removes_only_owned_derivatives_and_downloads(self):
        self.prepare('original')
        unrelated = self.output / 'responsive/keep-me.png'
        unrelated.write_bytes(b'user file')
        self.prepare('off', False)
        self.assertEqual(list((self.output / 'downloads').glob('*')), [])
        self.assertEqual(list((self.output / 'responsive').glob('*')), [unrelated])
        self.assertEqual(responsive_attributes(self.entry, 'image/1.jpg'), '')

    def test_flat_paths_and_stale_cleanup(self):
        self.prepare('original', fmt='flat')
        self.assertEqual(self.entry['download'], 'download_1.bmp')
        self.assertTrue(all('/' not in v['src'] for v in self.entry['variants']))
        self.prepare('off', False, 'flat')
        self.assertFalse(list(self.output.glob('responsive_*')))
        self.assertFalse(list(self.output.glob('download_*')))

    def test_transparency_is_kept(self):
        full = self.output / 'image/1.png'
        with Image.new('RGBA', (1000, 600), (20, 40, 60, 90)) as image:
            image.save(full)
        self.entry['full_dst'] = str(full)
        self.prepare('1280')
        for relative in [v['src'] for v in self.entry['variants']] + [self.entry['download']]:
            with Image.open(self.output / relative) as image:
                self.assertEqual(image.mode, 'RGBA')
                self.assertEqual(image.getextrema()[-1], (90, 90))

    def test_exif_orientation_and_metadata_stripping(self):
        full = self.output / 'image/1.jpg'
        exif = Image.Exif()
        exif[274] = 6
        exif[315] = 'Private author'
        with Image.new('RGB', (1200, 1800), '#abcdef') as image:
            image.save(full, exif=exif)
        self.prepare('1280')
        self.assertEqual((self.entry['image_width'], self.entry['image_height']), (1800, 1200))
        with Image.open(self.output / self.entry['download']) as image:
            self.assertEqual(image.size, (1280, 853))
            self.assertFalse(image.getexif())

    def test_animation_is_not_silently_flattened(self):
        full = self.output / 'image/1.gif'
        with Image.new('RGB', (600, 400), 'red') as first, Image.new('RGB', (600, 400), 'blue') as second:
            first.save(full, save_all=True, append_images=[second], duration=100, loop=0)
        self.entry['full_dst'] = str(full)
        report = self.prepare('1280')
        self.assertEqual(self.entry['variants'], [])
        self.assertEqual(self.entry['download'], '')
        self.assertTrue(report['images'][0]['warnings'])

    def test_large_web_image_warning(self):
        with Image.effect_noise((2000, 1500), 100).convert('RGB') as image:
            image.save(self.output / 'image/1.jpg', quality=100)
        report = self.prepare(responsive=False)
        self.assertGreater(report['images'][0]['web_bytes'], 1048576)
        self.assertTrue(any('1 MiB' in warning for warning in report['images'][0]['warnings']))


@unittest.skipIf(Image is None, 'Pillow required for real export tests')
class ExportIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.sources = self.root / 'sources'
        self.sources.mkdir()
        for name, color in [('one.jpg', '#ff0000'), ('two.jpg', '#0000ff')]:
            with Image.new('RGB', (2000, 1200), color) as image:
                image.save(self.sources / name)
        learner = patch('local_learning.LocalLearning')
        learner.start()
        self.addCleanup(learner.stop)
        self.generator = generator_class()()
        self.output = self.root / 'export'

    def generate(self, fmt='standard', mode='original'):
        return self.generator.execute({'gallery': {
            'images_path': str(self.sources), 'output_path': str(self.output),
            'title': 'Test gallery', 'responsive_images': True, 'download_mode': mode},
            'output_format': fmt})

    def test_real_export_links_report_and_ftp_list_both_formats(self):
        for fmt in ('standard', 'flat'):
            with self.subTest(fmt=fmt):
                self.output = self.root / fmt
                result = self.generate(fmt)
                html = (self.output / 'index.html').read_text()
                self.assertIn('srcset=', html)
                self.assertIn('sizes="100vw"', (self.output / 'slideshow.html').read_text())
                self.assertIn('"download":', html)
                for name in ('optimization-report.html', 'optimization-report.json', MANIFEST):
                    self.assertIn(name, result['files_to_upload'])
                for relative in result['files_to_upload']:
                    self.assertTrue((self.output / relative).is_file(), relative)
                data, images = load_project(self.output)
                self.assertEqual(data['gallery']['download_mode'], 'original')
                self.assertEqual(len(data['originals']), 2)
                self.assertEqual(len(images), 2)
                self.assertNotIn(str(self.root), (self.output / MANIFEST).read_text())

    def test_resave_reorder_keeps_the_correct_original_both_formats(self):
        for fmt in ('standard', 'flat'):
            with self.subTest(fmt=fmt):
                self.output = self.root / fmt
                self.generate(fmt)
                data, images = load_project(self.output)
                backup = save_project(self.output, data, list(reversed(images)), self.generator)
                self.assertTrue(backup.is_dir())
                updated, _ = load_project(self.output)
                first_original = next(iter(updated['originals'].values()))
                self.assertEqual((self.output / first_original).read_bytes(), (self.sources / 'two.jpg').read_bytes())
                # A second edit must still point to portable originals, not the backup.
                data, images = load_project(self.output)
                save_project(self.output, data, images, self.generator)
                updated, _ = load_project(self.output)
                self.assertEqual((self.output / next(iter(updated['originals'].values()))).read_bytes(),
                                 (self.sources / 'two.jpg').read_bytes())

    def test_old_export_cannot_mislabel_web_images_as_original(self):
        self.generate(mode='off')
        data, images = load_project(self.output)
        # Simulate a version-one manifest that never carried original information.
        data.pop('originals')
        data['gallery']['download_mode'] = 'original'
        before = (self.output / 'index.html').read_bytes()
        with self.assertRaisesRegex(ValueError, 'Originalbild saknas'):
            save_project(self.output, data, images, self.generator)
        self.assertEqual((self.output / 'index.html').read_bytes(), before)
        self.assertFalse(list(self.root.glob('.gallery-edit-*')))
        data['gallery']['download_mode'] = '1280'
        save_project(self.output, data, images, self.generator)
        report = json.loads((self.output / 'optimization-report.json').read_text())
        self.assertTrue(all(row['source_kind'] == 'exported_image' for row in report['images']))

    def test_edit_add_remove_and_disable_cleans_stale_files(self):
        self.generate()
        data, images = load_project(self.output)
        new = self.root / 'added.png'
        with Image.new('RGB', (300, 500), 'green') as image:
            image.save(new)
        save_project(self.output, data, [new, images[1]], self.generator)
        data, images = load_project(self.output)
        self.assertEqual((self.output / data['originals'][data['images'][0]]).read_bytes(), new.read_bytes())
        data['gallery'].update(responsive_images=False, download_mode='off')
        save_project(self.output, data, [images[0]], self.generator)
        self.assertFalse(list((self.output / 'responsive').glob('*')))
        self.assertFalse(list((self.output / 'downloads').glob('*')))
        data, images = load_project(self.output)
        self.assertEqual(len(images), 1)
        self.assertEqual(data['originals'], {})

    def test_script_safe_titles_roundtrip_and_download_policy(self):
        title = '</script><script>alert("x")</script> & å\\n'
        entry = {'index': 1, 'filename': '1.jpg', 'title': title, 'download': ''}
        rendered = self.generator._build_js_images([entry], 'standard')
        self.assertNotIn('</script>', rendered)
        self.assertEqual(json.loads(rendered)[0]['title'], title)
        self.generate(mode='off')
        html = (self.output / 'index.html').read_text()
        self.assertIn('id="lb-download" hidden style="display:none"', html)
        self.assertIn('"download": ""', html)
        self.assertIn('lbDown.removeAttribute("href")', html)
        self.assertIn('lbImg.srcset = item.srcset', html)

    @unittest.skipUnless(shutil.which('node'), 'Node required for JavaScript syntax check')
    def test_generated_javascript_syntax(self):
        from html.parser import HTMLParser
        class Scripts(HTMLParser):
            def __init__(self):
                super().__init__()
                self.active = False
                self.scripts = []
            def handle_starttag(self, tag, attrs):
                self.active = tag == 'script' or self.active
            def handle_endtag(self, tag):
                if tag == 'script':
                    self.active = False
            def handle_data(self, data):
                if self.active:
                    self.scripts.append(data)
        self.generate()
        for name in ('index.html', 'slideshow.html'):
            parser = Scripts()
            parser.feed((self.output / name).read_text())
            for index, script in enumerate(parser.scripts):
                path = self.root / ('%s-%d.js' % (name, index))
                path.write_text(script)
                result = subprocess.run(['node', '--check', str(path)], capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stderr)


class SettingsPersistenceTests(unittest.TestCase):
    """Run the actual settings methods without requiring a display/Tk install."""
    def make_settings(self):
        import ast
        source = Path(__file__).resolve().parents[1] / 'plugins/ui_settings.py'
        tree = ast.parse(source.read_text())
        cls = next(item for item in tree.body if isinstance(item, ast.ClassDef) and item.name == 'SettingsUI')
        names = {'_collect_settings', 'load_settings', 'reset_defaults', 'has_unsaved_changes'}
        methods = [item for item in cls.body if isinstance(item, ast.FunctionDef) and item.name in names]
        cls.bases, cls.keywords, cls.decorator_list, cls.body = [], [], [], methods
        tree.body = [cls]
        scope = {'__package__': 'plugins', 'Path': Path,
                 'messagebox': types.SimpleNamespace(askyesno=lambda *args: True)}
        exec(compile(tree, str(source), 'exec'), scope)
        settings = scope['SettingsUI']()
        class Variable:
            def __init__(self):
                self.value = ''
            def get(self):
                return self.value
            def set(self, value):
                self.value = value
        attributes = {node.attr for method in methods for node in ast.walk(method)
                      if isinstance(node, ast.Attribute) and node.attr.endswith('_var')}
        for name in attributes:
            setattr(settings, name, Variable())
        settings.toggle_ftp_fields = settings.update_quality_label = lambda: None
        settings.log = lambda *args: None
        settings.reset_defaults()
        return settings

    def test_save_load_and_dirty_tracking(self):
        from plugins.web_image_assets import DOWNLOAD_LABELS
        settings = self.make_settings()
        settings.responsive_images_var.set(False)
        settings.download_mode_var.set(DOWNLOAD_LABELS['1920'])
        data = settings._collect_settings()
        self.assertFalse(data['responsive_images'])
        self.assertEqual(data['download_mode'], '1920')
        settings.reset_defaults()
        settings.load_config = lambda *args, **kwargs: data
        settings.load_settings()
        self.assertFalse(settings.responsive_images_var.get())
        self.assertEqual(settings.download_mode_var.get(), DOWNLOAD_LABELS['1920'])
        self.assertFalse(settings.has_unsaved_changes())
        settings.responsive_images_var.set(True)
        self.assertTrue(settings.has_unsaved_changes())

    def test_legacy_settings_default_and_reset(self):
        from plugins.web_image_assets import DOWNLOAD_LABELS
        settings = self.make_settings()
        settings.load_config = lambda *args, **kwargs: {'title': 'Legacy settings'}
        settings.load_settings()
        self.assertTrue(settings.responsive_images_var.get())
        self.assertEqual(settings.download_mode_var.get(), DOWNLOAD_LABELS['off'])
        settings.download_mode_var.set(DOWNLOAD_LABELS['original'])
        settings.responsive_images_var.set(False)
        settings.reset_defaults()
        self.assertTrue(settings.responsive_images_var.get())
        self.assertEqual(settings.download_mode_var.get(), DOWNLOAD_LABELS['off'])


@unittest.skipUnless(shutil.which('node'), 'Node required for JavaScript behavior check')
class DownloadScriptTests(unittest.TestCase):
    def test_download_button_handles_off_on_video_and_fallback(self):
        from plugins.html_generator_js import INDEX_JS
        from plugins.html_generator_templates import _MINI_INDEX_JS
        rich = INDEX_JS[INDEX_JS.index('      if (lbDown) {', INDEX_JS.index('function showItem()')):]
        rich = rich[:rich.index('\n\n      stopVideo();')]
        fallback = _MINI_INDEX_JS[_MINI_INDEX_JS.index('      var download = $("lb-download")'):]
        fallback = fallback[:fallback.index('\n      if (videoMode())')]
        script = '''
const assert = require('assert');
function element() {
  return {hidden: false, style: {}, attrs: {},
    setAttribute(k,v) { this.attrs[k]=v; },
    removeAttribute(k) { delete this.attrs[k]; if(k==='href') delete this.href; }};
}
for (const code of CODES) {
  const button = element();
  const show = new Function('item','videoMode','lbDown','$', code);
  show({src:'image/1.jpg', download:'downloads/1.jpg', downloadLabel:'1280 px'}, () => false, button, () => button);
  assert.strictEqual(button.hidden, false);
  assert.strictEqual(button.attrs.href || button.href, 'downloads/1.jpg');
  show({src:'image/2.jpg', download:''}, () => false, button, () => button);
  assert.strictEqual(button.hidden, true);
  assert.strictEqual(button.attrs.href || button.href, undefined);
  show({src:'video/1.mp4', download:'downloads/1.jpg'}, () => true, button, () => button);
  assert.strictEqual(button.hidden, true);
}
'''.replace('CODES', json.dumps([rich, fallback]))
        result = subprocess.run(['node', '-e', script], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)


@unittest.skipIf(Image is None, 'Pillow required for gallery checks integration')
class CoverAndLinksIntegrationTests(ExportIntegrationTests):
    def test_cover_metadata_and_link_report_in_real_export(self):
        context = {'gallery': {'images_path': str(self.sources), 'output_path': str(self.output),
                   'cover_image': 2, 'public_url': 'https://example.se/gallery/'}, 'output_format': 'standard'}
        result = self.generator.execute(context)
        self.assertTrue(result['link_report']['ok'])
        for name in ('cover.jpg', 'link-report.html', 'link-report.json'):
            self.assertIn(name, result['files_to_upload'])
        self.assertIn('https://example.se/gallery/cover.jpg', (self.output / 'index.html').read_text())
        data, images = load_project(self.output)
        self.assertEqual(data['gallery']['cover_image'], 2)
        save_project(self.output, data, images, self.generator)
        self.assertEqual(load_project(self.output)[0]['gallery']['public_url'], 'https://example.se/gallery/')

    def test_broken_custom_link_stops_staged_save_without_replacing_export(self):
        self.generate()
        data, images = load_project(self.output)
        before = (self.output / 'index.html').read_bytes()
        data['custom_html_footer'] = '<a href="missing.pdf">Broken</a>'
        with self.assertRaisesRegex(ValueError, 'länkkontroll'):
            save_project(self.output, data, images, self.generator)
        self.assertEqual((self.output / 'index.html').read_bytes(), before)
