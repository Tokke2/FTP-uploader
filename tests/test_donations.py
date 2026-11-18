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
        with Image.open(QR_FILE) as source:
            factor = max(1, (source.width + 239) // 240)
            displayed = source.resize((source.width // factor, source.height // factor), Image.Resampling.NEAREST)
            decoded = zxingcpp.read_barcode(displayed)
            self.assertIsNotNone(decoded)
            self.assertEqual(decoded.text, SWISH_PAYLOAD)


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


    def test_personal_support_text_is_voluntary_and_not_a_paywall(self):
        from donations import SUPPORT_TEXT
        self.assertIn('privat och i företag', SUPPORT_TEXT)
        self.assertIn('Ingen donation krävs', SUPPORT_TEXT)
        self.assertIn('inga funktioner låses upp', SUPPORT_TEXT)
        self.assertIn('Rickard Längkvist', SUPPORT_TEXT)

    def test_donation_dialog_is_available_under_help(self):
        text = (ROOT / 'main.pyw').read_text()
        self.assertIn('self.help_menu.add_command(label="Donationer / Stöd utvecklingen…"', text)
        self.assertNotIn('self.menubar.add_command(label="♥ Stöd utvecklingen"', text)
        dialog = (ROOT / 'donations.py').read_text()
        self.assertIn("window.bind('<Escape>'", dialog)
        self.assertIn("label(SUPPORT_TEXT)", dialog)

    def test_support_dialog_fits_smaller_screens(self):
        from donations import support_window_size
        self.assertEqual(support_window_size(1920,1080),(760,780))
        self.assertEqual(support_window_size(640,480),(600,400))
        self.assertEqual(support_window_size(360,640),(320,560))

    def test_responsive_native_dialog_wires_direct_buttons_and_single_window(self):
        import sys
        from types import SimpleNamespace
        from donations import show_donations
        widgets=[]
        class Widget:
            def __init__(self, master=None, **kwargs):
                self.master,self.options,self.bindings=master,kwargs,{}
                widgets.append(self)
            def cget(self,key): return self.options[key]
            def configure(self,**kwargs): self.options.update(kwargs)
            config=configure
            def bind(self,event,callback): self.bindings[event]=callback
            def pack(self,**kwargs): pass
            def grid(self,**kwargs): self.grid_options=kwargs
            def grid_forget(self): pass
            def columnconfigure(self,*args,**kwargs): pass
            def geometry(self,value): self.geometry_value=value
            def minsize(self,*args): pass
            def title(self,*args): pass
            def protocol(self,*args): pass
            def winfo_screenwidth(self): return 1280
            def winfo_screenheight(self): return 800
            def winfo_exists(self): return True
            def deiconify(self): pass
            def lift(self): pass
            def focus_set(self): pass
            def destroy(self): pass
            def create_window(self,*args,**kwargs): return 1
            def itemconfigure(self,*args,**kwargs): pass
            def bbox(self,*args): return (0,0,700,1200)
            def yview(self,*args): pass
            def set(self,*args): pass
            def yview_scroll(self,*args): pass
            def width(self): return 264
            def subsample(self,*args): return self
        fake=SimpleNamespace(Toplevel=Widget,Frame=Widget,Label=Widget,Canvas=Widget,
                             Scrollbar=Widget,Button=Widget,PhotoImage=Widget,TclError=RuntimeError,
                             messagebox=SimpleNamespace(showerror=lambda *args,**kwargs:self.fail('Payment failed')))
        parent=SimpleNamespace()
        with patch.dict(sys.modules,{'tkinter':fake}),patch('app_icon.apply_tk_window_icon'),patch('donations.open_payment',return_value=True) as payment:
            show_donations(parent)
            original_window=parent._donation_window
            canvases=[w for w in widgets if '<Configure>' in w.bindings and 'yscrollcommand' in w.options]
            self.assertEqual(len(canvases),1)
            for width in (740,360): canvases[0].bindings['<Configure>'](SimpleNamespace(width=width))
            for prefix,key in (('PayPal','paypal'),('Ko-fi','kofi')):
                button=next(w for w in widgets if w.options.get('text','').startswith(prefix))
                button.options['command']()
                payment.assert_called_with(key)
            count=len(widgets)
            show_donations(parent)
            self.assertIs(parent._donation_window,original_window)
            self.assertEqual(len(widgets),count)
            self.assertIn('<Escape>',original_window.bindings)
