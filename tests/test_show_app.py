# Copyright (c) 2026 Rickard Längkvist
import importlib.machinery
import importlib.util
from pathlib import Path
import socket
import tempfile
import unittest
from unittest.mock import Mock, patch


def load_helper():
    path = Path(__file__).resolve().parents[1] / 'visa_app.pyw'
    loader = importlib.machinery.SourceFileLoader('show_app_test', str(path))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


class ShowAppTests(unittest.TestCase):
    def setUp(self):
        self.module = load_helper()
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.module.BASE = Path(self.temp.name)

    def test_legacy_process_receives_trigger_without_second_launch(self):
        connection = Mock()
        connection.__enter__ = Mock(return_value=connection)
        connection.__exit__ = Mock(return_value=False)
        connection.recv.side_effect = socket.timeout()
        with patch.object(self.module.socket, 'create_connection', return_value=connection), \
             patch.object(self.module.subprocess, 'Popen') as spawn:
            self.module.main()
            spawn.assert_not_called()
        self.assertEqual((self.module.BASE / 'instance_show.trigger').read_text(), 'show')
        self.assertTrue((self.module.BASE / 'logs/show-app.log').is_file())

    def test_explicit_start_passes_show_flag_and_legacy_trigger(self):
        (self.module.BASE / 'main.pyw').touch()
        with patch.object(self.module.socket, 'create_connection', side_effect=ConnectionRefusedError), \
             patch.object(self.module.subprocess, 'Popen') as spawn:
            self.module.main()
            self.assertIn('--show', spawn.call_args.args[0])
        self.assertTrue((self.module.BASE / 'instance_show.trigger').exists())

    def test_no_program_file_reports_problem_instead_of_starting_unknown_code(self):
        with patch.object(self.module.socket, 'create_connection', side_effect=ConnectionRefusedError):
            with self.assertRaises(FileNotFoundError):
                self.module.main()

    def test_connect_timeout_uses_trigger_without_starting_another_process(self):
        with patch.object(self.module.socket, 'create_connection', side_effect=TimeoutError('timed out')), \
             patch.object(self.module.subprocess, 'Popen') as spawn:
            self.module.main()
            spawn.assert_not_called()
        self.assertEqual((self.module.BASE / 'instance_show.trigger').read_text(), 'show')
        log = (self.module.BASE / 'logs/show-app.log').read_text()
        self.assertIn('fönstervisning är inte bekräftad', log)
        self.assertNotIn('FEL:', log)

    def test_send_failure_still_uses_compatibility_trigger(self):
        connection = Mock()
        connection.__enter__ = Mock(return_value=connection)
        connection.__exit__ = Mock(return_value=False)
        connection.sendall.side_effect = ConnectionResetError()
        with patch.object(self.module.socket, 'create_connection', return_value=connection):
            self.assertTrue(self.module.show_existing())
        self.assertTrue((self.module.BASE / 'instance_show.trigger').exists())
