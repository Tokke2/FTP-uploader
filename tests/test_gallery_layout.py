from pathlib import Path
import unittest
from plugins.gallery_layout import filter_images, column_count
from plugins.html_generator_css import INDEX_CSS


class GalleryLayoutTests(unittest.TestCase):
    def setUp(self):
        self.images = [Path('Sommar.JPG'), Path('sommar.png'), Path('vinter.webp')]

    def test_combines_search_and_format(self):
        self.assertEqual(filter_images(self.images, 'sommar', 'PNG'), [Path('sommar.png')])

    def test_no_matches_stays_empty(self):
        self.assertEqual(filter_images(self.images, 'missing'), [])

    def test_clear_shows_everything(self):
        self.assertEqual(filter_images(self.images), self.images)

    def test_case_insensitive(self):
        self.assertEqual(filter_images(self.images, ' SOMMAR ', 'JPEG'), [Path('Sommar.JPG')])

    def test_columns_match_card_width(self):
        self.assertEqual(column_count(800, 120), 5)
        self.assertEqual(column_count(60, 120), 1)
        self.assertEqual(column_count(0, 120), 1)

    def test_accessible_web_styles_included(self):
        self.assertIn('.card:focus-visible', INDEX_CSS)
        self.assertIn('object-fit: contain', INDEX_CSS)
        self.assertIn('min-height: 44px', INDEX_CSS)
        self.assertIn('prefers-reduced-motion', INDEX_CSS)
