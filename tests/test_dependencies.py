import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch
import ensure_deps


class DependencyTests(unittest.TestCase):
    def test_every_start_checks_all_packages_without_pins(self):
        with tempfile.TemporaryDirectory() as directory:
            (Path(directory) / 'requirements.txt').write_text('Pillow==1.0\nsix\n')
            with patch.object(ensure_deps, 'hide_console'), patch.object(
                    ensure_deps, '_ensure_pip', return_value=True), patch.object(
                    ensure_deps, '_show_progress', return_value=(True, [])) as progress:
                self.assertTrue(ensure_deps.ensure_requirements(directory))
                self.assertTrue(ensure_deps.ensure_requirements(directory))
                self.assertEqual(progress.call_count, 2)
                jobs = progress.call_args.args[1]
                self.assertEqual([(n, v) for n, v, reason in jobs], [('Pillow', None), ('six', None)])

    def test_platform_filter(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'requirements.txt'
            path.write_text('Pillow\npython-xlib ; sys_platform == "linux"\npyobjc-framework-Quartz ; sys_platform == "darwin"\n')
            with patch('ensure_deps.sys.platform', 'linux'):
                self.assertEqual(ensure_deps._parse_requirements(path), [('Pillow', None), ('python-xlib', None)])
