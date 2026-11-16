from pathlib import Path
import tempfile
import unittest
from error_summary import ErrorSummary


class ErrorSummaryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.output = self.root / 'all_errors.log'
        self.collector = ErrorSummary([self.root], self.output)
        self.addCleanup(self.collector.close)

    def text(self):
        return self.output.read_text(encoding='utf-8')

    def test_error_and_traceback_not_normal_info(self):
        (self.root / 'startup.log').write_text(
            '[12:00:00] INFO start\n[12:00:01] FEL: broken\nTraceback (most recent call last):\n'
            '  File "sample.py", line 1\nValueError: bad\n[12:00:02] INFO success\n')
        self.collector.collect()
        text = self.text()
        self.assertIn('startup.log', text)
        self.assertIn('line 1', text)
        self.assertIn('ValueError: bad', text)
        self.assertNotIn('INFO start', text)
        self.assertNotIn('INFO success', text)

    def test_incremental_and_no_self_ingestion(self):
        source = self.root / 'deps.log'
        source.write_text('FEL: first\n')
        self.collector.collect()
        first = self.text()
        self.collector.collect()
        self.assertEqual(first, self.text())
        with source.open('a') as output:
            output.write('FEL: second\n')
        self.collector.collect()
        self.assertEqual(self.text().count('FEL: first'), 1)
        self.assertEqual(self.text().count('FEL: second'), 1)

    def test_truncated_source_is_read_again(self):
        source = self.root / 'startup.log'
        source.write_text('FEL: long initial error\n')
        self.collector.collect()
        source.write_text('FEL: new\n')
        self.collector.collect()
        self.assertIn('FEL: new', self.text())

    def test_partial_line_preserved(self):
        source = self.root / 'update.log'
        source.write_bytes(b'Kunde inte ')
        self.collector.collect()
        self.assertEqual(self.text(), '')
        with source.open('ab') as output:
            output.write(b'uppdatera\n')
        self.collector.collect()
        self.assertEqual(self.text().count('Kunde inte uppdatera'), 1)

    def test_restart_does_not_repeat_history(self):
        (self.root / 'deps.log').write_text('FEL: only once\n')
        self.collector.collect()
        self.collector.close()
        collector = ErrorSummary([self.root], self.output)
        try:
            collector.collect()
            self.assertEqual(self.text().count('FEL: only once'), 1)
        finally:
            collector.close()

    def test_final_unterminated_traceback_and_idempotent_close(self):
        (self.root / 'launcher.log').write_text('Traceback (most recent call last):\nValueError: final')
        self.collector.close()
        self.collector.close()
        self.assertEqual(self.text().count('ValueError: final'), 1)
        collector = ErrorSummary([self.root], self.output)
        collector.close()
        self.assertEqual(self.text().count('ValueError: final'), 1)

    def test_rotates_summary(self):
        collector = ErrorSummary([self.root], self.root / 'small.log', max_bytes=300, backups=2)
        try:
            (self.root / 'deps.log').write_text('FEL: ' + 'x' * 200 + '\nFEL: ' + 'y' * 200 + '\n')
            # A different output filename is still excluded by absolute path.
            collector.collect()
            self.assertTrue((self.root / 'small.log.1').exists())
        finally:
            collector.close()

    def test_successful_plugin_and_statistics_summaries_are_not_errors(self):
        source = self.root / 'startup.log'
        source.write_text('[2026-11-16 12:32:15.103] 11. Plugins | 14 laddade; fel: inga\n'
                          '[17:39:27.393] [SYSTEM    ] Skrivna rader: 404 (varav fel 1)\n'
                          '[2026-11-16 12:32:16.242] [FEL] Verkligt fel\n')
        self.collector.collect()
        self.assertNotIn('fel: inga', self.text())
        self.assertNotIn('Skrivna rader', self.text())
        self.assertIn('Verkligt fel', self.text())
