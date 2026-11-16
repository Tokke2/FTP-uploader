from pathlib import Path
import unittest
from donations import DESTINATIONS, payment_url, parse_amount
from auto_update import managed_file

ROOT = Path(__file__).resolve().parents[1]


class DonationTests(unittest.TestCase):
    def test_recipients_are_read_only_and_exact(self):
        self.assertEqual(DESTINATIONS['paypal'], 'https://paypal.me/Rickard3dPrint')
        self.assertEqual(DESTINATIONS['kofi'], 'https://ko-fi.com/tokke2')
        with self.assertRaises(TypeError):
            DESTINATIONS['paypal'] = 'https://example.invalid'

    def test_amount_is_optional_and_decimal_safe(self):
        self.assertIsNone(parse_amount(''))
        self.assertEqual(parse_amount('25,50'), '25.50')
        self.assertEqual(payment_url('paypal', '50'), 'https://paypal.me/Rickard3dPrint/50.00SEK')
        self.assertEqual(payment_url('paypal'), DESTINATIONS['paypal'])

    def test_invalid_amounts_cannot_enter_payment_url(self):
        for amount in ('0', '-10', '100000', 'NaN', 'Infinity', '1.001', 'https://evil.invalid', '1/other'):
            with self.subTest(amount=amount), self.assertRaises(ValueError):
                payment_url('paypal', amount)

    def test_swish_is_explicit_external_page_not_invented_recipient(self):
        self.assertEqual(payment_url('swish', '50'), 'https://tokke2.github.io/recept/stod.html')
        self.assertEqual(payment_url('kofi', '50'), 'https://ko-fi.com/tokke2')

    def test_license_grants_private_and_commercial_use_and_is_distributed(self):
        text = (ROOT / 'LICENSE').read_text()
        self.assertIn('privata och kommersiella', text)
        self.assertIn('Rickard Längkvist', text)
        self.assertTrue(managed_file('LICENSE'))
        self.assertTrue(managed_file('COPYRIGHT'))

    def test_support_has_no_settings_override(self):
        text = (ROOT / 'donations.py').read_text()
        self.assertNotIn('load_json', text)
        self.assertNotIn('update_settings', text)
        menu = (ROOT / 'main.pyw').read_text()
        self.assertIn('label="♥ Stöd utvecklingen"', menu)
        self.assertIn('show_license(self)', menu)
