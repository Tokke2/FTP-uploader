import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from auto_update import files_match_release, managed_file, release_files


def blob_hash(content):
    return hashlib.sha1(b'blob ' + str(len(content)).encode() + b'\0' + content).hexdigest()


class ReleaseFilesTests(unittest.TestCase):
    def test_compares_content_not_timestamp_or_size(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'main.pyw'
            path.write_bytes(b'version A')
            expected = {'main.pyw': blob_hash(b'version A')}
            self.assertTrue(files_match_release(folder, expected))
            path.write_bytes(b'version B')
            self.assertFalse(files_match_release(folder, expected))

    def test_missing_file_requires_update(self):
        with tempfile.TemporaryDirectory() as folder:
            self.assertFalse(files_match_release(folder, {'helpers.py': blob_hash(b'code')}))

    def test_metadata_and_user_data_excluded(self):
        for name in ('config/settings.json', 'out/index.html', '.release-state.json', 'logs/update.log'):
            self.assertFalse(managed_file(name))
        for name in ('main.pyw', 'requirements.txt', 'plugins/gallery_view.py', 'icon/icon.ico'):
            self.assertTrue(managed_file(name))

    def test_tree_request_uses_exact_release_commit(self):
        tree = {'tree': [{'path': 'main.pyw', 'type': 'blob', 'mode': '100644', 'sha': 'b' * 40},
                         {'path': 'config/settings.json', 'type': 'blob', 'sha': 'c' * 40}]}
        with patch('auto_update.urllib.request.urlopen', return_value=io.BytesIO(json.dumps(tree).encode())) as response:
            self.assertEqual(release_files('a' * 40), {'main.pyw': 'b' * 40})
            self.assertTrue(response.call_args.args[0].full_url.endswith('/git/trees/' + 'a' * 40 + '?recursive=1'))

    def test_incomplete_tree_not_treated_as_up_to_date(self):
        with patch('auto_update.urllib.request.urlopen', return_value=io.BytesIO(b'{"truncated":true,"tree":[]}')):
            with self.assertRaises(ValueError):
                release_files('a' * 40)
