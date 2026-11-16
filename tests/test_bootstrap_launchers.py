from pathlib import Path
import os
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class BootstrapLauncherTests(unittest.TestCase):
    def test_shell_syntax(self):
        subprocess.run(['sh', '-n', str(ROOT / 'Starta.sh')], check=True)

    def test_existing_python_starts_without_installation_prompt_and_forwards_args(self):
        with tempfile.TemporaryDirectory(prefix='start space ') as directory:
            folder = Path(directory)
            (folder / 'Starta.sh').write_bytes((ROOT / 'Starta.sh').read_bytes())
            (folder / 'start.pyw').touch()
            fake = folder / 'python3'
            fake.write_text('#!/bin/sh\nif [ "$1" = "-I" ]; then exit 0; fi\nprintf "%s\\n" "$@"\n')
            fake.chmod(0o755)
            # Keep dirname available, but use the fake Python before the real PATH.
            result = subprocess.run(['sh', str(folder / 'Starta.sh'), '--autostart'],
                                    env={**os.environ, 'PATH': str(folder) + ':' + os.environ['PATH']},
                                    input='', capture_output=True, text=True, timeout=10)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout.splitlines(), [str(folder / 'start.pyw'), '--autostart'])
            self.assertNotIn('install', result.stdout.lower())

    def test_no_bat_and_windows_store_aliases_excluded(self):
        self.assertFalse(list(ROOT.glob('*.bat')))
        text = (ROOT / 'Starta.vbs').read_text(encoding='utf-16')
        self.assertIn('\\windowsapps\\', text)
        self.assertLess(text.index('If Len(found) = 0 Then'), text.index('MsgBox("Python saknas'))
