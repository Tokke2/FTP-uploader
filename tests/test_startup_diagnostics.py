# Copyright (c) 2026 Rickard Längkvist
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


class EarlyDiagnosticsTests(unittest.TestCase):
    def test_unhandled_error_before_tk_is_logged_in_real_process(self):
        with tempfile.TemporaryDirectory() as folder:
            code = ('from startup_diagnostics import install,phase; '
                    'install(%r);phase("före Tk"); raise RuntimeError("test-early-failure")') % folder
            result = subprocess.run([sys.executable, '-c', code], cwd=ROOT,
                                    capture_output=True, text=True, timeout=10)
            self.assertNotEqual(result.returncode, 0)
            logs = Path(folder) / 'logs'
            self.assertIn('test-early-failure', (logs / 'startup-crash.log').read_text())
            early = (logs / 'startup-early.log').read_text()
            self.assertIn('före Tk', early)
            self.assertIn('STARTFEL', early)
            self.assertIn('pid=', early)

    def test_missing_module_is_not_silent(self):
        with tempfile.TemporaryDirectory() as folder:
            code = ('from startup_diagnostics import install; install(%r); '
                    'import deliberately_missing_gallery_module') % folder
            result = subprocess.run([sys.executable, '-c', code], cwd=ROOT,
                                    capture_output=True, text=True, timeout=10)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('ModuleNotFoundError', (Path(folder) / 'logs/startup-crash.log').read_text())

    def test_parent_captures_syntax_error_before_child_can_install_hooks(self):
        import python_discovery as discovery
        interpreter = Path(sys.executable)
        with tempfile.TemporaryDirectory() as folder:
            entry = Path(folder) / 'bad.pyw'
            entry.write_text('def invalid syntax!!!\n')
            with patch.object(discovery, 'find_python', return_value=interpreter), \
                 patch.object(discovery.sys, 'executable', str(Path(folder) / 'other/python')), \
                 patch.object(discovery.sys, 'argv', [str(entry)]), \
                 patch.dict(discovery.os.environ):
                discovery.os.environ.pop('FTP_UPLOADER_RUNTIME_SELECTED', None)
                with self.assertRaisesRegex(RuntimeError, 'avslutades direkt'):
                    discovery.select_for_start(entry)
            logs = list((Path(folder) / 'logs').glob('python-child_*.log'))
            self.assertEqual(len(logs), 1)
            self.assertIn('SyntaxError', logs[0].read_text())

    def test_main_hooks_precede_discovery_and_tk(self):
        main = (ROOT / 'main.pyw').read_text()
        self.assertLess(main.index('_install_diagnostics('), main.index('select_for_start('))
        self.assertLess(main.index('_install_diagnostics('), main.index('import tkinter as tk'))
        start = (ROOT / 'start.pyw').read_text()
        self.assertLess(start.index('install(BASE)'), start.index('select_for_start('))
        self.assertIn('if not ensure_bootstrap(BASE_DIR)', main)


class ReviewRegressionTests(unittest.TestCase):
    def method(self, filename, name, scope):
        import ast
        path = ROOT / filename
        tree = ast.parse(path.read_text())
        method = next(item for item in ast.walk(tree) if isinstance(item, ast.FunctionDef) and item.name == name)
        exec(compile(ast.Module(body=[method], type_ignores=[]), str(path), 'exec'), scope)
        return scope[name]

    def test_css_preview_percentage_is_literal_not_a_format_directive(self):
        from datetime import datetime
        from types import SimpleNamespace
        method = self.method('plugins/custom_css_editor.py', '_build_preview_html', {'datetime': datetime, 'Path': Path})
        fake = SimpleNamespace(app=SimpleNamespace(context={}), COLOR_PREVIEW_BANNER='#123456', COLOR_PREVIEW_BANNER_FG='#ffffff')
        html = method(fake, 'body{width:80%}', '<meta name="example" content="test">', '<footer>Footer</footer>')
        self.assertIn('width:100%', html)
        self.assertIn('body{width:80%}', html)
        self.assertIn('<footer>Footer</footer>', html)

    def test_error_filename_and_count_are_separate(self):
        from types import SimpleNamespace
        method = self.method('plugins/advanced_logger_guards.py', 'stats', {'UNKNOWN': '?'})
        fake = SimpleNamespace(logs_dir=Path('logs'), main_path=Path('gallery.log'), error_path=Path('errors.log'),
                               _main=None, _error=None, written=12, errors=3)
        stats = method(fake)
        self.assertEqual(stats['error_file'], 'errors.log')
        self.assertEqual(stats['errors'], 3)
