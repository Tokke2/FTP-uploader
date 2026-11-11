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
