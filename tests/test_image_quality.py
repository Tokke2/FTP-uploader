import tempfile
from pathlib import Path
import unittest
from image_quality import assess_size, write_quality_report
from workspace_design import navigation_columns, density_padding


class QualityTests(unittest.TestCase):
    def test_resolution_and_orientation(self):
        self.assertTrue(assess_size(640,480)['small_image'])
        self.assertTrue(assess_size(1600,900)['upscale_risk'])
        self.assertFalse(assess_size(1080,1920)['upscale_risk'])
        self.assertEqual(assess_size(640,480)['scale_to_target'],3)

    def test_navigation_and_density(self):
        self.assertEqual(navigation_columns(300),2)
        self.assertEqual(navigation_columns(650),4)
        self.assertEqual(navigation_columns(1920),6)
        self.assertLess(density_padding('compact')[1],density_padding('comfortable')[1])

    def test_report_does_not_modify_images_and_escapes_names(self):
        try:
            from PIL import Image
        except ImportError:
            self.skipTest('Pillow required')
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);image=root/'test.png'
            Image.new('RGB',(320,240)).save(image)
            before=image.read_bytes()
            report=write_quality_report([{'filename':'<script>.png','full_dst':str(image)}],root)
            self.assertTrue(report['images'][0]['upscale_risk'])
            self.assertEqual(image.read_bytes(),before)
            self.assertIn('&lt;script&gt;', (root/'image-quality.html').read_text())
