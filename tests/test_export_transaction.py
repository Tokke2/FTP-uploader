from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from export_transaction import ExportTransaction


class TransactionTests(unittest.TestCase):
    def test_abort_leaves_previous_gallery_unchanged(self):
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / 'gallery'
            output.mkdir()
            (output / 'index.html').write_text('old')
            tx = ExportTransaction(output)
            (tx.stage / 'index.html').write_text('new')
            tx.abort()
            self.assertEqual((output / 'index.html').read_text(), 'old')
            self.assertFalse(tx.stage.exists())

    def test_publish_keeps_backup_and_relocates_paths(self):
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / 'gallery'
            output.mkdir()
            (output / 'index.html').write_text('old')
            tx = ExportTransaction(output)
            (tx.stage / 'index.html').write_text('new')
            context = {'_gallery_generated': True, 'html_output': tx.stage / 'index.html',
                       'gallery': {'output_path': str(tx.stage)}}
            tx.publish(context)
            self.assertEqual((output / 'index.html').read_text(), 'new')
            self.assertEqual((tx.backup / 'index.html').read_text(), 'old')
            self.assertEqual(context['html_output'], output / 'index.html')
            self.assertEqual(context['gallery']['output_path'], str(output))

    def test_bad_links_and_cancellation_preserve_old_export(self):
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / 'gallery'
            output.mkdir()
            (output / 'index.html').write_text('old')
            tx = ExportTransaction(output)
            (tx.stage / 'index.html').write_text('<img src="missing.jpg">')
            with self.assertRaises(ValueError):
                tx.publish({'_gallery_generated': True})
            with self.assertRaises(RuntimeError):
                tx.publish({'_gallery_generated': True, 'cancel_check': lambda: True})
            self.assertEqual((output / 'index.html').read_text(), 'old')
            tx.abort()

    def test_failed_publish_restores_original_directory(self):
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / 'gallery'
            output.mkdir()
            (output / 'index.html').write_text('old')
            tx = ExportTransaction(output)
            (tx.stage / 'index.html').write_text('new')
            rename = Path.rename
            def fail_stage(path, target):
                if path == tx.stage:
                    raise OSError('disk error')
                return rename(path, target)
            with patch.object(Path, 'rename', fail_stage), self.assertRaises(OSError):
                tx.publish({'_gallery_generated': True})
            self.assertEqual((output / 'index.html').read_text(), 'old')
            tx.abort()

    def test_pipeline_publishes_before_ftp_and_cleans_failed_work(self):
        import contextvars
        import traceback
        from types import SimpleNamespace
        from unittest.mock import Mock
        from test_video_only_gallery import extract
        run = extract('main.pyw', 'run_pipeline', {'_event': Mock(), '_event_exception': Mock(),
                      '_log_job': contextvars.ContextVar('transaction-test'), 'traceback': traceback})
        for fail in (False, True):
            with self.subTest(fail=fail), tempfile.TemporaryDirectory() as folder:
                output = Path(folder) / 'gallery'
                output.mkdir()
                (output / 'index.html').write_text('old')
                def settings(context, log):
                    tx = ExportTransaction(output)
                    context['_export_transaction'] = tx
                    context['gallery'] = {'output_path': str(tx.stage)}
                    return context
                def html(context, log):
                    stage = context['_export_transaction'].stage
                    (stage / 'index.html').write_text('new')
                    if fail:
                        raise RuntimeError('conversion failed')
                    context['_gallery_generated'] = True
                    context['html_output'] = stage / 'index.html'
                    return context
                uploaded = []
                def ftp(context, log):
                    self.assertEqual(context['html_output'], output / 'index.html')
                    self.assertEqual((output / 'index.html').read_text(), 'new')
                    uploaded.append(True)
                plugins = [('settings', SimpleNamespace(execute=settings, PRIORITY=1, PLUGIN_NAME='Settings')),
                           ('html', SimpleNamespace(execute=html, PRIORITY=30, PLUGIN_NAME='HTML')),
                           ('ftp', SimpleNamespace(execute=ftp, PRIORITY=35, PLUGIN_NAME='FTP'))]
                app = SimpleNamespace(context={}, get_plugins=lambda **kwargs: plugins, _log_error=Mock())
                if fail:
                    with self.assertRaises(RuntimeError):
                        run(app)
                    self.assertEqual((output / 'index.html').read_text(), 'old')
                    self.assertEqual(uploaded, [])
                else:
                    run(app)
                    self.assertEqual(uploaded, [True])
                self.assertFalse(list(Path(folder).glob('.gallery-export-*')))
