import io
import json
from pathlib import Path
import unittest
import urllib.error
import urllib.request
from unittest.mock import patch
import auto_update


class UpdateNetworkTests(unittest.TestCase):
    def test_latest_404_falls_back_to_published_stable_releases(self):
        missing = urllib.error.HTTPError(auto_update.API, 404, 'Not Found', {}, None)
        releases = [{'tag_name': 'v9.0.0', 'draft': True},
                    {'tag_name': 'v8.0.0', 'prerelease': True},
                    {'tag_name': 'v1.0.0', 'draft': False, 'prerelease': False}]
        with patch('auto_update.open_release_url', side_effect=[missing, io.BytesIO(json.dumps(releases).encode())]) as opened:
            self.assertEqual(auto_update.latest_release(), 'v1.0.0')
        self.assertIn('/releases?per_page=100', opened.call_args.args[0].full_url)

    def test_no_fallback_to_branch_when_no_stable_release_exists(self):
        missing = urllib.error.HTTPError(auto_update.API, 404, 'Not Found', {}, None)
        with patch('auto_update.open_release_url', side_effect=[missing, io.BytesIO(b'[]')]):
            with self.assertRaisesRegex(ValueError, 'stabil release'):
                auto_update.latest_release()

    def test_transient_404_retried_bounded_times(self):
        request = urllib.request.Request(auto_update.API)
        missing = urllib.error.HTTPError(auto_update.API, 404, 'Not Found', {}, None)
        with patch('auto_update.urllib.request.urlopen', side_effect=missing) as opened, patch('time.sleep'):
            with self.assertRaises(urllib.error.HTTPError):
                auto_update.open_release_url(request)
        self.assertEqual(opened.call_count, 3)

    def test_error_message_includes_failed_address(self):
        missing = urllib.error.HTTPError(auto_update.API, 404, 'Not Found', {}, None)
        message = auto_update.update_error_message(missing)
        self.assertIn(auto_update.API, message)
        self.assertIn('404', message)
        self.assertIn('logs/update.log', message)

    def test_help_has_manual_update_command(self):
        source = (Path(__file__).resolve().parents[1] / 'main.pyw').read_text()
        self.assertIn('self.help_menu.add_command(label="Sök efter uppdateringar"', source)
        self.assertIn('check_before_start(BASE_DIR, parent=self, manual=True)', source)

    def test_release_startfiles_are_updated_too(self):
        for name in ('Starta.vbs', 'Starta.sh'):
            self.assertTrue(auto_update.managed_file(name))
