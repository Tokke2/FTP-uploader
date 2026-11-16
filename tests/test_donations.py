from pathlib import Path
import unittest
from donations import SWISH_NUMBER, SWISH_PAYEE, SWISH_PAYLOAD, QR_FILE
from auto_update import managed_file

ROOT = Path(__file__).resolve().parents[1]


class DonationTests(unittest.TestCase):
    def test_exact_recipient_and_standard_payload(self):
        self.assertEqual(SWISH_NUMBER, '0721817177')
        self.assertEqual(SWISH_PAYEE, '46' + SWISH_NUMBER[1:])
        self.assertEqual(SWISH_PAYLOAD, 'C46721817177;;;6')
        self.assertNotIn('swish://', SWISH_PAYLOAD)

    def test_qr_is_in_release_update_scope(self):
        self.assertTrue(QR_FILE.is_file())
        self.assertEqual(QR_FILE.read_bytes()[:8], b'\x89PNG\r\n\x1a\n')
        self.assertTrue(managed_file('icon/swish-donation.png'))

    def test_only_swish_and_no_external_qr_or_payment_service(self):
        text = (ROOT / 'donations.py').read_text()
        for forbidden in ('paypal', 'ko-fi', 'qrserver', 'webbrowser', 'urllib', 'load_json', 'update_settings'):
            self.assertNotIn(forbidden, text.lower())
        self.assertNotIn('tk.Entry(', text)

    def test_license_grants_private_and_commercial_use(self):
        text = (ROOT / 'LICENSE').read_text()
        self.assertIn('privata och kommersiella', text)
        self.assertTrue(managed_file('LICENSE'))

    def test_qr_can_be_decoded_to_exact_payload(self):
        try:
            from PIL import Image
            import zxingcpp
        except ImportError:
            self.skipTest('QR decoder is an optional test tool, not an app dependency')
        result = zxingcpp.read_barcode(Image.open(QR_FILE))
        self.assertIsNotNone(result)
        self.assertEqual(result.text, SWISH_PAYLOAD)
