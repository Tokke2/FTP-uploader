import ast
from pathlib import Path
import unittest
from unittest.mock import patch
import quiet_process

ROOT=Path(__file__).resolve().parents[1]


class QuietProcessTests(unittest.TestCase):
    def test_windows_hides_every_supported_launch_and_keeps_pipes(self):
        for name in ('Popen','run','check_output','check_call','call'):
            with self.subTest(name=name),patch.object(quiet_process.sys,'platform','win32'),patch.object(quiet_process._subprocess,name) as actual:
                getattr(quiet_process,name)(['ffprobe','video.mp4'],stdout=-1,timeout=3)
                self.assertTrue(actual.call_args.kwargs['creationflags'] & 0x08000000)
                self.assertEqual(actual.call_args.kwargs['stdout'],-1)
                self.assertEqual(actual.call_args.kwargs['timeout'],3)

    def test_new_console_is_never_allowed_on_windows(self):
        with patch.object(quiet_process.sys,'platform','win32'):
            flags=quiet_process.hidden_options({'creationflags':0x10|0x200})['creationflags']
            self.assertFalse(flags & 0x10)
            self.assertTrue(flags & 0x200)
            self.assertTrue(flags & 0x08000000)

    def test_non_windows_options_are_unchanged(self):
        options={'capture_output':True,'text':True}
        with patch.object(quiet_process.sys,'platform','linux'):
            self.assertEqual(quiet_process.hidden_options(options),options)
        self.assertNotIn('creationflags',options)

    def test_app_process_launches_use_shared_console_policy(self):
        for path in [*ROOT.glob('*.py'),*ROOT.glob('*.pyw'),*(ROOT/'plugins').glob('*.py')]:
            if path.name=='quiet_process.py':continue
            for node in ast.walk(ast.parse(path.read_bytes())):
                if isinstance(node,ast.Import):
                    self.assertFalse(any(a.name=='subprocess' for a in node.names),str(path))
                elif isinstance(node,ast.ImportFrom):
                    self.assertNotEqual(node.module,'subprocess',str(path))
