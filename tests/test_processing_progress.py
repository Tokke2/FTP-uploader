import ast
import contextvars
from pathlib import Path
import threading
from types import SimpleNamespace
import unittest
from unittest.mock import Mock
from processing_progress import ProcessingProgress

ROOT = Path(__file__).resolve().parents[1]


class ProcessingProgressTests(unittest.TestCase):
    def controller(self):
        controller = ProcessingProgress(Mock())
        controller._open = Mock()
        controller.render = Mock()
        return controller

    def test_worker_only_posts_events_and_ui_poll_opens_window(self):
        controller = self.controller()
        def work():
            token = controller.begin('Bilder')
            for value in range(1000):
                controller.stage(token, 'Bild', value / 10)
            controller.finish(token)
        worker = threading.Thread(target=work)
        worker.start()
        worker.join()
        controller._open.assert_not_called()
        controller.render.assert_not_called()
        self.assertLessEqual(len(controller.events), 3)
        controller.poll()
        controller._open.assert_called_once()
        job = controller.render.call_args.args[0]
        self.assertTrue(job['done'])
        self.assertIn('finished', job)

    def test_different_jobs_do_not_mix_percentages(self):
        controller = self.controller()
        first, second = controller.begin('A'), controller.begin('B')
        controller.stage(first, 'A image', 20)
        controller.stage(second, 'B image', 70)
        controller.poll()
        self.assertEqual(controller.jobs[first]['percent'], 20)
        self.assertEqual(controller.jobs[second]['percent'], 70)

    def test_stage_change_resets_unknown_progress(self):
        controller = self.controller()
        token = controller.begin('Job')
        controller.stage(token, 'Images', 100)
        controller.poll()
        controller.stage(token, 'QuickTime conversion')
        controller.poll()
        self.assertIsNone(controller.jobs[token]['percent'])

    def test_error_and_cancelled_are_not_success(self):
        controller = self.controller()
        token = controller.begin('Job')
        controller.finish(token, failed=True, cancelled=True)
        controller.poll()
        self.assertTrue(controller.jobs[token]['failed'])
        self.assertTrue(controller.jobs[token]['cancelled'])

    def test_destroy_stops_polling(self):
        controller = self.controller()
        controller.app.after.reset_mock()
        controller._destroyed(SimpleNamespace(widget=controller.app))
        controller.poll()
        controller.app.after.assert_not_called()

    def test_real_pipeline_reports_and_restores_callback_even_on_error(self):
        source = ast.parse((ROOT / 'main.pyw').read_text())
        method = next(node for node in ast.walk(source) if isinstance(node, ast.FunctionDef) and node.name == 'run_pipeline')
        import traceback
        namespace = {'_log_job': contextvars.ContextVar('test-job'), '_event': Mock(),
                     '_event_exception': Mock(), 'traceback': traceback}
        exec(compile(ast.fix_missing_locations(ast.Module(body=[method], type_ignores=[])), '<pipeline>', 'exec'), namespace)
        progress, previous = Mock(), Mock()
        def fail(context, log):
            context['progress_callback'](50, 'Bild 1/2')
            raise ValueError('bad image')
        plugin = SimpleNamespace(PLUGIN_NAME='Images', execute=fail)
        owner = SimpleNamespace(context={'progress_callback': previous}, _processing_progress=progress,
                                get_plugins=lambda **kwargs: [('image', plugin)], _log_error=Mock())
        with self.assertRaises(ValueError):
            namespace['run_pipeline'](owner)
        self.assertIs(owner.context['progress_callback'], previous)
        self.assertEqual(owner._pipeline_busy, 0)
        previous.assert_called_once_with(50, 'Bild 1/2')
        self.assertTrue(progress.finish.call_args.kwargs['failed'])
