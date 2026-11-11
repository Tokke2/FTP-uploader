import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from error_register_store import ErrorRegister
from log_clock import dated, timestamp


class ErrorStoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.register = ErrorRegister(self.root)

    def test_groups_mirrors_but_preserves_different_errors(self):
        first = self.register.observe('startup.log', '[2026-11-04 10:00:00] FEL: ConnectionError: offline')
        mirror = self.register.observe('errors.log', '[2026-11-04 10:00:01] [FEL       ] ConnectionError: offline')
        self.assertEqual(first, mirror)
        record = self.register.active()[0]
        self.assertEqual(record['sources'], ['startup.log', 'errors.log'])
        self.assertEqual(record['count'], 2)
        self.register.observe('startup.log', 'FEL: ConnectionError: different server')
        self.assertEqual(len(self.register.active()), 2)

    def test_tracebacks_with_different_exceptions_do_not_collapse(self):
        with self.register.batch():
            first = self.register.observe('crash.log', 'Traceback (most recent call last):')
            first = self.register.detail(first, 'ValueError: invalid image')
            second = self.register.observe('launcher.log', 'Traceback (most recent call last):')
            second = self.register.detail(second, 'ConnectionError: offline')
            mirror = self.register.observe('other.log', 'Traceback (most recent call last):')
            mirror = self.register.detail(mirror, 'ValueError: invalid image')
        self.assertNotEqual(first, second)
        self.assertEqual(first, mirror)
        self.assertEqual(len(self.register.active()), 2)

    def test_resolution_history_survives_reopening_and_restart(self):
        identifier = self.register.observe('source.log', 'FEL: offline')
        self.register.resolve(identifier, comment='Rättade serveradress', actor='tester', version='1.0.0')
        self.register.observe('second.log', 'FEL: offline')
        record = ErrorRegister(self.root).active()[0]
        self.assertEqual(record['history'][0]['comment'], 'Rättade serveradress')
        self.assertEqual(record['history'][0]['actor'], 'tester')
        self.assertEqual(record['history'][0]['version'], '1.0.0')
        self.assertEqual(record['history'][1]['action'], 'reopened')

    def test_traceback_batch_exports_only_once(self):
        with patch.object(self.register, '_export', wraps=self.register._export) as export:
            with self.register.batch():
                identifier = self.register.observe('source.log', 'FEL: broken')
                for i in range(100):
                    self.register.detail(identifier, 'traceback line %d' % i)
            self.assertEqual(export.call_count, 1)
        self.assertIn('line 99', self.register.log_file.read_text())

    def test_failed_batch_rolls_back(self):
        with self.assertRaises(RuntimeError):
            with self.register.batch():
                self.register.observe('source.log', 'FEL: rollback')
                raise RuntimeError()
        self.assertEqual(self.register.active(), [])

    def test_migrates_legacy_json_and_keeps_backup(self):
        legacy = {'old': {'id': 'old', 'status': 'open', 'details': 'FEL: legacy', 'code': 'old',
                           'first_seen': '2026-11-01', 'last_seen': '2026-11-02', 'source': 'source.log', 'count': 2}}
        path = self.root / '.error-register.json'
        path.write_text(json.dumps(legacy))
        migrated = ErrorRegister(self.root)
        self.assertEqual(migrated.active()[0]['id'], 'old')
        self.assertTrue(path.exists())

    def test_full_date_added_to_legacy_log_timestamps(self):
        self.assertRegex(timestamp(), r'^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{3}$')
        self.assertRegex(dated('12:34:56.789'), r'^\d{4}-\d{2}-\d{2} 12:34:56.789$')
        self.assertEqual(dated('2026-11-04 12:34:56.789'), '2026-11-04 12:34:56.789')
