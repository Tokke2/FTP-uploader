import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch

from auto_update import check_release, apply_release, latest_release, release_commit


class UpdateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.commit_patch = patch('auto_update.release_commit', return_value='a' * 40)
        self.commit_patch.start()
        self.addCleanup(self.commit_patch.stop)
        (self.base / 'main.pyw').write_text('APP_VERSION = "2.8.4"\n')

    def test_new_release(self):
        with patch('auto_update.latest_release', return_value='v3.0.0'):
            self.assertEqual(check_release(self.base), ('v3.0.0', 'a' * 40))

    def test_current_release(self):
        import json
        (self.base / '.release-state.json').write_text(json.dumps({'tag': 'v2.8.4', 'commit': 'a' * 40}))
        with patch('auto_update.latest_release', return_value='v2.8.4'), patch('auto_update.release_files', return_value={'main.pyw': 'hash'}), patch('auto_update.files_match_release', return_value=True):
            self.assertIsNone(check_release(self.base))

    def test_same_version_and_commit_but_changed_file_updates(self):
        import json
        (self.base / '.release-state.json').write_text(json.dumps({'tag': 'v2.8.4', 'commit': 'a' * 40}))
        with patch('auto_update.latest_release', return_value='v2.8.4'), patch('auto_update.release_files', return_value={'main.pyw': 'b' * 40}):
            self.assertEqual(check_release(self.base), ('v2.8.4', 'a' * 40))

    def test_same_version_changed_commit_updates(self):
        import json
        (self.base / '.release-state.json').write_text(json.dumps({'tag': 'v2.8.4', 'commit': 'b' * 40}))
        with patch('auto_update.latest_release', return_value='v2.8.4'):
            self.assertEqual(check_release(self.base), ('v2.8.4', 'a' * 40))

    def test_unknown_same_version_installs_once(self):
        with patch('auto_update.latest_release', return_value='v2.8.4'):
            self.assertEqual(check_release(self.base), ('v2.8.4', 'a' * 40))

    def test_never_downgrade(self):
        with patch('auto_update.latest_release', return_value='v2.7.0'):
            self.assertIsNone(check_release(self.base))

    def test_numeric_comparison(self):
        with patch('auto_update.latest_release', return_value='v2.10.0'):
            self.assertIsNotNone(check_release(self.base))

    def archive(self, extra=None, version='3.0.0'):
        import io
        import zipfile
        output = io.BytesIO()
        with zipfile.ZipFile(output, 'w') as zipped:
            for name in ('main.pyw', 'start.pyw', 'helpers.py', 'ensure_deps.py', 'requirements.txt'):
                content = ('APP_VERSION = "%s"' % version) if name == 'main.pyw' else ''
                zipped.writestr('release-root/' + name, content)
            for name, content in (extra or {}).items():
                zipped.writestr(name, content)
        output.seek(0)
        return output

    def test_installs_exact_release_without_git(self):
        (self.base / 'config').mkdir()
        settings = self.base / 'config/settings.json'
        settings.write_text('keep user settings')
        with patch('auto_update.urllib.request.urlopen') as response:
            response.return_value.__enter__.return_value = self.archive(
                {'release-root/config/settings.json': 'must not install'})
            message = apply_release(self.base, ('v3.0.0', 'a' * 40))
            url = response.call_args.args[0].full_url
            self.assertTrue(url.endswith('/zipball/' + 'a' * 40))
            self.assertNotIn('/main', url)
        import json
        self.assertEqual(json.loads((self.base / '.release-state.json').read_text())['commit'], 'a' * 40)
        self.assertIn('Installerad release', message)
        self.assertIn('3.0.0', (self.base / 'main.pyw').read_text())
        self.assertEqual(settings.read_text(), 'keep user settings')
        backup = next((self.base / 'backups/releases').glob('release-*'))
        self.assertIn('2.8.4', (backup / 'main.pyw').read_text())
        import shutil
        shutil.rmtree(backup)

    def test_development_checkout_never_overwritten(self):
        (self.base / '.git').mkdir()
        with patch('auto_update.urllib.request.urlopen') as response:
            with self.assertRaisesRegex(RuntimeError, 'Utvecklingskopia'):
                apply_release(self.base, ('v3.0.0', 'a' * 40))
            response.assert_not_called()

    def test_rejects_archive_traversal(self):
        with patch('auto_update.urllib.request.urlopen') as response:
            response.return_value.__enter__.return_value = self.archive({'release-root/../evil.py': ''})
            with self.assertRaisesRegex(ValueError, 'Osäker'):
                apply_release(self.base, ('v3.0.0', 'a' * 40))
        self.assertIn('2.8.4', (self.base / 'main.pyw').read_text())

    def test_tag_must_match_app_version(self):
        with patch('auto_update.urllib.request.urlopen') as response:
            response.return_value.__enter__.return_value = self.archive(version='2.9.0')
            with self.assertRaisesRegex(ValueError, 'stämmer inte'):
                apply_release(self.base, ('v3.0.0', 'a' * 40))
        self.assertIn('2.8.4', (self.base / 'main.pyw').read_text())

    def test_invalid_code_does_not_touch_installation(self):
        with patch('auto_update.urllib.request.urlopen') as response:
            response.return_value.__enter__.return_value = self.archive({'release-root/bad.py': 'def !'})
            with self.assertRaises(SyntaxError):
                apply_release(self.base, ('v3.0.0', 'a' * 40))
        self.assertIn('2.8.4', (self.base / 'main.pyw').read_text())

    def test_failed_install_restores_previous_files(self):
        import shutil
        copy = shutil.copy2

        def fail_one_install(source, target, *args, **kwargs):
            if Path(source).parent.name == 'staged' and Path(source).name == 'ensure_deps.py':
                raise OSError('simulated write failure')
            return copy(source, target, *args, **kwargs)

        with patch('auto_update.urllib.request.urlopen') as response, patch('shutil.copy2', side_effect=fail_one_install):
            response.return_value.__enter__.return_value = self.archive()
            with self.assertRaisesRegex(OSError, 'simulated'):
                apply_release(self.base, ('v3.0.0', 'a' * 40))
        self.assertIn('2.8.4', (self.base / 'main.pyw').read_text())
        self.assertFalse((self.base / 'start.pyw').exists())
        self.assertFalse((self.base / '.release-update.lock').exists())
        for backup in (self.base / 'backups/releases').glob('release-*'):
            shutil.rmtree(backup)

    def test_resolves_annotated_release_tag_without_main(self):
        import io
        import json
        with patch('auto_update.urllib.request.urlopen') as response:
            response.side_effect = [io.BytesIO(json.dumps({'object': {'type': 'tag', 'sha': 'b' * 40}}).encode()),
                                    io.BytesIO(json.dumps({'object': {'type': 'commit', 'sha': 'a' * 40}}).encode())]
            self.assertEqual(release_commit('v1.0.0'), 'a' * 40)
            urls = [call.args[0].full_url for call in response.call_args_list]
            self.assertTrue(urls[0].endswith('/git/ref/tags/v1.0.0'))
            self.assertTrue(urls[1].endswith('/git/tags/' + 'b' * 40))
            self.assertTrue(all('/main' not in url for url in urls))

    def test_bad_release_tag(self):
        with patch('auto_update.urllib.request.urlopen') as response:
            response.return_value.__enter__.return_value.read.return_value = b'{"tag_name":"--evil"}'
            with self.assertRaises(ValueError):
                latest_release()
