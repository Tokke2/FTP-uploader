# Copyright (c) 2026 Rickard Längkvist
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch
from local_learning import LocalLearning, error_suggestions, record_export


class LearningTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / 'learning.sqlite3'
        self.engine = LocalLearning(self.path)
        self.gallery = {'images_path': '/photos', 'jpeg_quality': 85, 'download_mode': 'off',
                        'password': 'NEVER-STORE-SECRET', 'title': 'PRIVATE-TITLE'}
        self.report = {'totals': {'source_bytes': 3000000, 'web_bytes': 1500000},
                       'images': [{'web_bytes': 1500000}]}

    def test_empty_and_small_samples_do_not_invent_knowledge(self):
        self.assertIn('Inga observationer', self.engine.suggestions()[0])
        self.engine.observe_export(self.gallery, self.report)
        self.assertTrue(any('För få' in text for text in self.engine.suggestions()))

    def test_learns_habits_and_large_image_results_after_three_exports(self):
        for _ in range(3):
            self.engine.observe_export(self.gallery, self.report)
        result = '\n'.join(self.engine.suggestions())
        self.assertIn('/photos', result)
        self.assertIn('3/3', result)
        self.assertIn('50.0%', result)
        self.assertIn('3 av 3', result)
        self.assertNotIn('NEVER-STORE-SECRET', self.path.read_bytes().decode(errors='ignore'))
        self.assertNotIn('PRIVATE-TITLE', self.path.read_bytes().decode(errors='ignore'))
        self.assertEqual(self.gallery['jpeg_quality'], 85)

    def test_persistence_pause_and_clear(self):
        self.engine.observe_export(self.gallery, self.report)
        self.engine.set_enabled(False)
        reopened = LocalLearning(self.path)
        self.assertFalse(reopened.enabled())
        reopened.observe_export(self.gallery, self.report)
        self.assertIn('1 senaste', reopened.suggestions()[0])
        reopened.clear()
        self.assertIn('Inga observationer', reopened.suggestions()[0])
        self.assertFalse(reopened.enabled())
        reopened.set_enabled(True)
        reopened.observe_export(self.gallery, self.report)
        self.assertIn('1 senaste', reopened.suggestions()[0])

    def test_bounded_storage_and_recent_window(self):
        for _ in range(205):
            self.engine.observe_export(self.gallery, self.report)
        with self.engine.connect() as connection:
            self.assertEqual(connection.execute('SELECT count(*) FROM exports').fetchone()[0], 200)
        self.assertIn('20 senaste', self.engine.suggestions()[0])

    def test_old_error_resolution_is_only_a_suggestion_not_an_automatic_fix(self):
        records = [{'code': 'E123', 'count': 5, 'status': 'open',
                    'history': [{'action': 'resolved', 'comment': 'Bytte exportmapp'}]}]
        text = '\n'.join(error_suggestions(records))
        self.assertIn('Bytte exportmapp', text)
        self.assertIn('inte en verifierad lösning', text)
        self.assertEqual(records[0]['status'], 'open')
        records[0]['status'] = 'resolved'
        self.assertNotIn('Bytte exportmapp', '\n'.join(error_suggestions(records)))

    def test_learning_failure_does_not_break_export(self):
        with patch('local_learning.LocalLearning', side_effect=OSError('read only')):
            log = Mock()
            record_export(self.gallery, self.report, log)
            log.assert_called_once()
