# Copyright (c) 2026 Rickard Längkvist
import json
from pathlib import Path
import tempfile
import unittest
from plugins.gallery_checks import check_links, cover_options
try:
    from PIL import Image
except ImportError:
    Image = None


class LinkChecksTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def page(self, text):
        (self.root / 'index.html').write_text(text, encoding='utf-8')

    def test_images_downloads_video_pdf_and_srcset(self):
        for name in ('image.jpg', 'small.jpg', 'movie.mp4', 'poster.png', 'document.pdf', 'download.jpg'):
            (self.root / name).touch()
        self.page('<img src="image.jpg" srcset="small.jpg 480w, image.jpg 960w"><video src="movie.mp4" poster="poster.png"></video><a href="document.pdf">PDF</a><a href="download.jpg" download>Hämta</a>')
        result = check_links(self.root)
        self.assertTrue(result['ok'], result)
        self.assertEqual(result['checked'], 7)
        (self.root / 'small.jpg').unlink()
        self.assertFalse(check_links(self.root)['ok'])

    def test_external_links_are_never_fetched(self):
        self.page('<a href="https://example.se/no-network">Extern</a><img src="data:image/png;base64,abc"><a href="mailto:a@example.se">Mail</a>')
        result = check_links(self.root)
        self.assertTrue(result['ok'])
        self.assertEqual(result['external_not_checked'], 3)

    def test_html_fragments_and_encoded_filenames(self):
        (self.root / 'min bild.jpg').touch()
        self.page('<h1 id="titel">Titel</h1><a href="#titel">OK</a><a href="#saknas">Trasig</a><img src="min%20bild.jpg">')
        result = check_links(self.root)
        self.assertEqual(len(result['errors']), 1)
        self.assertEqual(result['errors'][0]['reason'], 'Ankare saknas')

    def test_escape_outside_export_is_rejected(self):
        self.page('<img src="../secret.jpg">')
        self.assertEqual(check_links(self.root)['errors'][0]['reason'], 'Utanför exportmappen')

    def test_manifest_checks_javascript_only_assets(self):
        self.page('<h1>Galleri</h1>')
        (self.root / 'gallery-project.json').write_text(json.dumps({'images': [], 'assets': ['downloads/1.jpg']}))
        self.assertFalse(check_links(self.root)['ok'])
        (self.root / 'downloads').mkdir()
        (self.root / 'downloads/1.jpg').touch()
        self.assertTrue(check_links(self.root)['ok'])

    def test_directory_index_link_and_javascript_route(self):
        self.page('<a href="./">Start</a><a href="#bild-1">Bild</a>')
        self.assertTrue(check_links(self.root)['ok'])

    def test_reports_are_escaped_and_machine_readable(self):
        self.page('<img src="&lt;missing&gt;.jpg">')
        result = check_links(self.root)
        self.assertEqual(json.loads((self.root / 'link-report.json').read_text()), result)
        report = (self.root / 'link-report.html').read_text()
        self.assertIn('&lt;missing&gt;', report)
        self.assertNotIn('<missing>', report)

    def test_cover_settings_validation(self):
        self.assertEqual(cover_options({}), (1, ''))
        for number in ('x', 0, -1):
            with self.subTest(number=number), self.assertRaises(ValueError):
                cover_options({'cover_image': number})
        for url in ('file:///private', 'javascript:alert(1)', 'https://user:password@host/', 'https://host/#fragment'):
            with self.subTest(url=url), self.assertRaises(ValueError):
                cover_options({'public_url': url})


@unittest.skipIf(Image is None, 'Pillow required for cover image tests')
class CoverTests(unittest.TestCase):
    def test_selected_cover_and_absolute_share_metadata(self):
        from plugins.gallery_checks import prepare_cover
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            for name, color in [('one.jpg', 'red'), ('two.jpg', 'blue')]:
                with Image.new('RGB', (200, 300), color) as image:
                    image.save(root / name)
            entries = [{'full_dst': root / 'one.jpg'}, {'full_dst': root / 'two.jpg'}]
            for url in ('https://example.se/gallery/', 'https://example.se/gallery/index.html'):
                tags = prepare_cover(entries, root, {'cover_image': 2, 'public_url': url}, '<Title>', '')
                self.assertIn('https://example.se/gallery/cover.jpg', tags)
                self.assertIn('&lt;Title&gt;', tags)
                with Image.open(root / 'cover.jpg') as image:
                    self.assertEqual(image.size, (1200, 630))
                    self.assertGreater(image.getpixel((600, 315))[2], 240)
                    self.assertLess(image.getpixel((600, 315))[0], 10)
                    self.assertFalse(image.getexif())
            self.assertEqual(prepare_cover(entries, root, {}, 'Title', ''), '')
            with self.assertRaises(ValueError):
                prepare_cover(entries, root, {'cover_image': 3}, 'Title', '')
