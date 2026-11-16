from pathlib import Path
import unittest
from donations import SWISH_NUMBER, SWISH_PAYEE, SWISH_PAYLOAD, QR_FILE
from auto_update import managed_file
from unittest.mock import patch
from donations import PAYMENT_LINKS, open_payment

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

    def test_no_intermediary_page_or_external_qr_service(self):
        text = (ROOT / 'donations.py').read_text()
        for forbidden in ('recept/stod', 'qrserver', 'urllib', 'load_json', 'update_settings'):
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


    def test_payment_buttons_open_exact_profiles_directly(self):
        for service, url in (('paypal', 'https://paypal.me/Rickard3dPrint'),
                             ('kofi', 'https://ko-fi.com/tokke2')):
            with patch('donations.webbrowser.open', return_value=True) as browser:
                self.assertTrue(open_payment(service))
                browser.assert_called_once_with(url)
        with self.assertRaises(TypeError):
            PAYMENT_LINKS['paypal'] = 'https://example.invalid'

    def test_unknown_payment_target_cannot_be_opened(self):
        with patch('donations.webbrowser.open') as browser:
            with self.assertRaises(KeyError):
                open_payment('https://example.invalid')
            browser.assert_not_called()
