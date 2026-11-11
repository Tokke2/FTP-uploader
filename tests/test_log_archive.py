from datetime import date, datetime
import os
from pathlib import Path
import tempfile
import unittest
from log_archive import archive_logs
from unresolved_errors import ErrorRegister
from error_summary import ErrorSummary


class LogArchiveTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.today = date(2026, 11, 4)

    def test_old_records_archived_current_kept(self):
        path = self.root / 'update.log'
        path.write_text('2026-11-03 23:59:00 FEL: old\ntraceback details\n2026-11-04 09:00:00 INFO today\n')
        archive_logs(self.root, today=self.today, compact=True)
        archived = list((self.root / 'archive/2026-11-03').glob('*.log'))
        self.assertEqual(len(archived), 1)
        self.assertIn('traceback details', archived[0].read_text())
        self.assertEqual(path.read_text(), '2026-11-04 09:00:00 INFO today\n')

    def test_running_snapshot_never_changes_original(self):
        path = self.root / 'gallery_20261103_220000.log'
        text = '[23:59:59] FEL: old\n[00:00:01] INFO current\n'
        path.write_text(text)
        archive_logs(self.root, today=self.today)
        self.assertEqual(path.read_text(), text)
        archived = next((self.root / 'archive/2026-11-03').glob('*.log'))
        self.assertNotIn('current', archived.read_text())

    def test_undated_old_file_uses_mtime_and_idempotent_archive(self):
        path = self.root / 'helpers_errors.log'
        path.write_text('FEL: yesterday\n')
        stamp = datetime(2026, 11, 3, 12).timestamp()
        os.utime(path, (stamp, stamp))
        archive_logs(self.root, today=self.today)
        archive_logs(self.root, today=self.today)
        self.assertEqual(len(list((self.root / 'archive/2026-11-03').glob('*'))), 1)
        archive_logs(self.root, today=self.today, compact=True)
        self.assertFalse(path.exists())

    def test_active_error_log_never_archived(self):
        path = self.root / 'unresolved_errors.log'
        path.write_text('2026-11-03 active error\n')
        archive_logs(self.root, today=self.today, compact=True)
        self.assertTrue(path.exists())
        self.assertFalse((self.root / 'archive').exists())

    def test_register_keeps_resolved_history_and_reopens_recurrence(self):
        register = ErrorRegister(self.root)
        identifier = register.observe('source.log', 'FEL: ConnectionError: offline')
        register.detail(identifier, 'traceback context')
        self.assertIn('ConnectionError', register.log_file.read_text())
        self.assertIn('traceback context', register.log_file.read_text())
        register.resolve(identifier)
        self.assertFalse(register.active())
        self.assertNotIn('offline', register.log_file.read_text())
        self.assertEqual(register.observe('source.log', 'FEL: ConnectionError: offline'), identifier)
        self.assertEqual(register.active()[0]['count'], 2)
        self.assertTrue(register.state_file.exists())

    def test_collector_ignores_archives_and_register_log(self):
        archive = self.root / 'archive/2026-11-03'
        archive.mkdir(parents=True)
        (archive / 'old.log').write_text('FEL: must not reopen\n')
        source = self.root / 'update.log'
        source.write_text('[10:00:00] FEL: ConnectionError: failed\n  traceback context\n')
        collector = ErrorSummary([self.root], self.root / 'all_errors.log')
        try:
            collector.collect()
            active = collector.register.active()
            self.assertEqual(len(active), 1)
            self.assertIn('traceback context', active[0]['details'])
            collector.register.resolve(active[0]['id'])
            collector.collect()
            self.assertFalse(collector.register.active())
            with source.open('a') as output:
                output.write('[11:00:00] FEL: ConnectionError: failed\n')
            collector.collect()
            self.assertEqual(len(collector.register.active()), 1)
        finally:
            collector.close()


class RetentionTests(unittest.TestCase):
    def test_fourteen_day_boundary_and_no_symlink_traversal(self):
        from datetime import timedelta
        from log_archive import prune_archives
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            today = date(2026, 11, 11)
            for age in (1, 14, 15, 100):
                archive = root / 'archive' / (today - timedelta(days=age)).isoformat()
                archive.mkdir(parents=True)
                (archive / 'old.log').write_text('old')
            prune_archives(root, today)
            self.assertTrue((root / 'archive/2026-10-28/old.log').is_file())
            self.assertFalse((root / 'archive/2026-10-27').exists())
            self.assertFalse((root / 'archive/2026-08-03').exists())
            self.assertTrue((root / 'archive/2026-11-10/old.log').is_file())

    def test_expired_sources_are_not_rearchived_and_today_survives(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source = root / 'update.log'
            source.write_text('2026-10-01 12:00:00 old\n2026-11-11 12:00:00 today\n')
            archive_logs(root, date(2026, 11, 11), compact=True)
            self.assertEqual(source.read_text(), '2026-11-11 12:00:00 today\n')
            self.assertFalse((root / 'archive/2026-10-01').exists())
            unresolved = root / 'unresolved_errors.log'
            unresolved.write_text('2026-10-01 unresolved\n')
            archive_logs(root, date(2026, 11, 11), compact=True)
            self.assertTrue(unresolved.exists())

    def test_already_owned_instance_does_not_skip_startup_archiving(self):
        from unittest.mock import Mock, patch
        import log_archive
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            collector = Mock()
            collector.state = {}
            with patch.object(log_archive, 'PREPARED', False), \
                 patch('single_instance.owns_instance', return_value=True), \
                 patch('app_paths.logs_dir', return_value=root), \
                 patch('error_summary.ErrorSummary', return_value=collector), \
                 patch.object(log_archive.socket, 'socket', side_effect=AssertionError('must not rebind owned port')), \
                 patch.object(log_archive, 'archive_logs') as archive:
                log_archive.prepare_logs()
                archive.assert_called_once_with(root, compact=True)
                collector.collect.assert_called_once()
                self.assertTrue(log_archive.PREPARED)

    def test_startup_header_supplies_legacy_session_date(self):
        from log_archive import split_days
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'startup.log'
            path.write_text('# Start:      2026-11-10 09:00:00\n[09:00:00.123] old session\n# Start:      2026-11-11 09:00:00\n[09:00:00.123] new session\n')
            groups = split_days(path)
            self.assertIn(b'old session', groups[date(2026, 11, 10)])
            self.assertIn(b'new session', groups[date(2026, 11, 11)])
