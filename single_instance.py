# Copyright (c) 2026 Rickard Längkvist
"""Acquire before updates/dependencies/Tk; forward subsequent launches over loopback."""
import atexit
import os
import socket
import sys
import threading

PORT = 47200
PROTOCOL = b'FTP-UPLOADER/1'
_primary = None


def _allow_foreground(pid):
    if sys.platform == 'win32':
        import ctypes
        from ctypes import wintypes
        function = ctypes.windll.user32.AllowSetForegroundWindow
        function.argtypes = [wintypes.DWORD]
        function.restype = wintypes.BOOL
        function(pid)


def _read_line(connection, limit=128):
    result = b''
    while len(result) < limit and not result.endswith(b'\n'):
        part = connection.recv(1)
        if not part:
            break
        result += part
    return result


class SingleInstance:
    def __init__(self, port=PORT):
        self.port = port
        self._socket = None
        self._thread = None
        self._show = threading.Event()
        self._stop = threading.Event()

    def acquire(self):
        if self.is_held():
            return True
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            # POSIX permits immediate restart after closed connections, not a second
            # listening socket (SO_REUSEPORT is deliberately never enabled).
            server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, int(sys.platform != 'win32'))
            if sys.platform == 'win32':
                server.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
            server.bind(('127.0.0.1', self.port))
            server.listen(16)
            server.settimeout(0.2)
        except OSError:
            server.close()
            return False
        self.port = server.getsockname()[1]
        self._socket = server
        self._stop.clear()
        self._thread = threading.Thread(target=self._serve, args=(server,), daemon=True,
                                        name='FTP-uploader activation')
        self._thread.start()
        return True

    def _serve(self, server):
        while not self._stop.is_set():
            try:
                connection, _ = server.accept()
            except socket.timeout:
                continue
            except OSError:
                break
            with connection:
                try:
                    connection.settimeout(1)
                    request = _read_line(connection)
                    if request != PROTOCOL + b' SHOW\n':
                        continue
                    connection.sendall(PROTOCOL + b' OK ' + str(os.getpid()).encode('ascii') + b'\n')
                    # Client grants Windows foreground rights before acknowledging.
                    try:
                        _read_line(connection, 16)
                        connection.recv(1)  # Let the client close first, avoiding server TIME_WAIT.
                    except OSError:
                        pass
                    self._show.set()  # Tk consumes this on its main thread, even after slow startup.
                except OSError:
                    continue

    def activate_existing(self):
        try:
            with socket.create_connection(('127.0.0.1', self.port), timeout=2) as client:
                client.sendall(PROTOCOL + b' SHOW\n')
                response = _read_line(client)
                prefix = PROTOCOL + b' OK '
                if not response.startswith(prefix):
                    return False
                pid = int(response[len(prefix):].strip())
                try:
                    _allow_foreground(pid)
                except OSError:
                    pass
                client.sendall(b'ACK\n')
                return True
        except (OSError, ValueError):
            return False

    def consume_show_request(self):
        requested = self._show.is_set()
        if requested:
            self._show.clear()
        return requested

    def is_held(self):
        return self._socket is not None

    def release(self):
        self._stop.set()
        if self._socket is not None:
            self._socket.close()
            self._socket = None
        if self._thread is not None and self._thread is not threading.current_thread():
            self._thread.join(timeout=1.5)
        self._thread = None


def ensure_primary():
    """Return the one process-owned guard, or None after focusing the existing app."""
    global _primary
    if _primary is not None and _primary.is_held():
        return _primary
    from startup_diagnostics import phase
    phase('Kontrollerar instanslås')
    guard = SingleInstance()
    if guard.acquire():
        _primary = guard
        atexit.register(guard.release)
        phase('Instanslås erhållet')
        return guard
    phase('Instansport upptagen', 'Försöker aktivera den redan körande appen; ingen extra instans startas.')
    import sys
    if '--autostart' in sys.argv:
        phase('Autostart: befintlig instans', 'Ingen SHOW-begäran skickas; befintligt fönster lämnas orört.')
        return None
    if guard.activate_existing():
        phase('Aktivering skickad', 'Denna extra start avslutas normalt. Befintlig app ska behandla begäran.')
        return None
    raise RuntimeError('Appens instansport används, men den befintliga appen svarar inte. '
                       'En äldre eller låst instans kan fortfarande köras. Använd visa_app.pyw från samma programmapp. '
                       'Se logs/startup-early.log. Ingen extra instans startas.')


def owns_instance():
    """True only when this Python process owns the primary guard."""
    return _primary is not None and _primary.is_held()
