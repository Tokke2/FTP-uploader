from pathlib import Path
from unittest.mock import Mock
import unittest
from processing_progress import InlineProgress

ROOT = Path(__file__).resolve().parents[1]


class InlineVideoProgressTests(unittest.TestCase):
    def setUp(self):
        self.bar, self.variable, self.label = Mock(), Mock(), Mock()
        self.progress = InlineProgress(self.bar, self.variable, self.label)

    def test_unknown_duration_animates_immediately_and_does_not_reset(self):
        self.progress.update()
        self.progress.update()
        self.bar.start.assert_called_once_with(12)
        self.bar.configure.assert_called_with(mode='indeterminate')
        self.label.configure.assert_called_with(text='Arbetar…')

    def test_measured_progress_switches_to_percentage(self):
        self.progress.update()
        self.progress.update(42)
        self.bar.stop.assert_called_once()
        self.bar.configure.assert_called_with(mode='determinate')
        self.variable.set.assert_called_with(42)
        self.label.configure.assert_called_with(text='42 %')

    def test_next_file_restarts_animation(self):
        self.progress.update(100)
        self.progress.update()
        self.bar.start.assert_called_once()
        self.variable.set.assert_called_with(0)

    def test_failure_stops_animation_without_false_hundred_percent(self):
        self.progress.update()
        self.progress.stop('Fel')
        self.variable.set.assert_called_with(0)
        self.label.configure.assert_called_with(text='Fel')
        self.assertFalse(self.progress.running)

    def test_ui_keeps_bar_reference_and_start_precedes_worker(self):
        ui = (ROOT / 'plugins/video_processor_ui.py').read_text()
        self.assertIn('self.current_progress_bar = ttk.Progressbar(', ui)
        worker = (ROOT / 'plugins/video_processor.py').read_text()
        start = worker[worker.index('    def start_processing('):worker.index('    def _process_all_worker(')]
        self.assertLess(start.index('self._visible_file_progress()'), start.index('threading.Thread('))
        self.assertIn("('current_busy', None)", worker)
