# Copyright (c) 2026 Rickard Längkvist
import socket
import subprocess
import sys
from pathlib import Path
import unittest
from unittest.mock import patch
from single_instance import SingleInstance, PROTOCOL


class InstanceTests(unittest.TestCase):
    def setUp(self):
        self.first = SingleInstance(port=0)
        self.assertTrue(self.first.acquire())
        self.addCleanup(self.first.release)

    def receive_request(self):
        # Synchronize through the server event, never timing-sensitive sleeps.
        self.assertTrue(self.first._show.wait(2))
        self.assertTrue(self.first.consume_show_request())
        self.assertFalse(self.first.consume_show_request())

    def test_second_launch_cannot_acquire_and_activates_first(self):
        second = SingleInstance(self.first.port)
        self.assertFalse(second.acquire())
        self.assertTrue(second.activate_existing())
        self.receive_request()
        self.assertFalse(second.is_held())

    def test_activation_from_another_process_and_directory(self):
        root = Path(__file__).resolve().parents[1]
        script = ('import sys; sys.path.insert(0, %r); from single_instance import SingleInstance; '
                  'g=SingleInstance(%d); assert not g.acquire(); assert g.activate_existing()') % (str(root), self.first.port)
        process = subprocess.run([sys.executable, '-c', script], cwd=root.parent,
                                 capture_output=True, text=True, timeout=5)
        self.assertEqual(process.returncode, 0, process.stderr)
        self.receive_request()

    def test_many_repeated_launches_keep_one_owner(self):
        for _ in range(12):
            other = SingleInstance(self.first.port)
            self.assertFalse(other.acquire())
            self.assertTrue(other.activate_existing())
            self.receive_request()
        self.assertTrue(self.first.is_held())

    def test_release_allows_immediate_restart_after_activation(self):
        port = self.first.port
        self.assertTrue(SingleInstance(port).activate_existing())
        self.receive_request()
        self.first.release()
        replacement = SingleInstance(port)
        self.addCleanup(replacement.release)
        self.assertTrue(replacement.acquire())

    def test_unrecognized_local_client_cannot_activate(self):
        with socket.create_connection(('127.0.0.1', self.first.port)) as connection:
            connection.sendall(b'NOT-OUR-APP\n')
            self.assertEqual(connection.recv(128), b'')
        self.assertFalse(self.first.consume_show_request())

    def test_fragmented_protocol_request(self):
        with socket.create_connection(('127.0.0.1', self.first.port)) as connection:
            for byte in PROTOCOL + b' SHOW\n':
                connection.sendall(bytes([byte]))
            self.assertTrue(connection.recv(128).startswith(PROTOCOL + b' OK '))
            connection.sendall(b'ACK\n')
        self.receive_request()

    def test_launcher_claims_before_updates_and_dependencies(self):
        root = Path(__file__).resolve().parents[1]
        launcher = (root / 'start.pyw').read_text()
        main = (root / 'main.pyw').read_text()
        self.assertLess(launcher.index('ensure_primary()'), launcher.index('check_before_start(BASE)'))
        self.assertLess(main.index('ensure_primary()'), main.index('ensure_bootstrap(BASE_DIR)'))
        self.assertLess(main.index('ensure_primary()'), main.index('import tkinter as tk'))
        self.assertNotIn('%s körs redan.', main)

    def test_process_guard_reused_from_launcher_to_main(self):
        import single_instance
        with patch.object(single_instance, '_primary', self.first):
            self.assertIs(single_instance.ensure_primary(), self.first)

    def test_unknown_port_owner_is_not_treated_as_success(self):
        import single_instance
        with patch.object(single_instance, '_primary', None), patch.object(single_instance, 'SingleInstance') as guard:
            guard.return_value.acquire.return_value = False
            guard.return_value.activate_existing.return_value = False
            with self.assertRaises(RuntimeError):
                single_instance.ensure_primary()


class WindowActivationRegressionTests(unittest.TestCase):
    def test_real_tk_poll_consumes_ipc_without_a_trigger_file(self):
        import ast
        from types import SimpleNamespace
        from unittest.mock import Mock
        path = Path(__file__).resolve().parents[1] / 'main.pyw'
        tree = ast.parse(path.read_text())
        app = next(item for item in tree.body if isinstance(item, ast.ClassDef) and item.name == 'App')
        method = next(item for item in app.body if isinstance(item, ast.FunctionDef) and item.name == '_poll_show_trigger')
        scope = {'log_startup': Mock(), 'log_startup_exc': Mock()}
        exec(compile(ast.Module(body=[method], type_ignores=[]), str(path), 'exec'), scope)
        fake = SimpleNamespace(_instance_lock=Mock(), _show_trigger=Mock(), show_window=Mock(), after=Mock())
        fake._instance_lock.consume_show_request.return_value = True
        fake._show_trigger.exists.return_value = False
        fake._show_trigger.unlink.side_effect = FileNotFoundError()
        fake._poll_show_trigger = Mock()
        scope['_poll_show_trigger'](fake)
        fake._instance_lock.consume_show_request.assert_called_once()
        fake.show_window.assert_called_once()
        fake.after.assert_called_once_with(200, fake._poll_show_trigger)
        scope['log_startup_exc'].assert_not_called()

    def test_actual_socket_event_reaches_the_real_window_poll(self):
        import ast
        from types import SimpleNamespace
        from unittest.mock import Mock
        path = Path(__file__).resolve().parents[1] / 'main.pyw'
        tree = ast.parse(path.read_text())
        app = next(item for item in tree.body if isinstance(item, ast.ClassDef) and item.name == 'App')
        method = next(item for item in app.body if isinstance(item, ast.FunctionDef) and item.name == '_poll_show_trigger')
        scope = {'log_startup': Mock(), 'log_startup_exc': Mock()}
        exec(compile(ast.Module(body=[method], type_ignores=[]), str(path), 'exec'), scope)
        guard = SingleInstance(port=0)
        self.assertTrue(guard.acquire())
        try:
            self.assertTrue(SingleInstance(guard.port).activate_existing())
            self.assertTrue(guard._show.wait(2))
            fake = SimpleNamespace(_instance_lock=guard, _show_trigger=Mock(), show_window=Mock(), after=Mock(), _poll_show_trigger=Mock())
            fake._show_trigger.exists.return_value = False
            scope['_poll_show_trigger'](fake)
            fake.show_window.assert_called_once()
            self.assertFalse(guard.consume_show_request())
        finally:
            guard.release()
