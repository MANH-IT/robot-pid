"""Liên kết TCP tới ESP8266 làm cầu nối trong suốt UART-WiFi."""

import socket
import threading
import time

from .link import RobotLink
from .protocol import format_stop, parse_telemetry


class TcpLink(RobotLink):
    """Liên kết TCP tới ESP8266 làm cầu nối trong suốt UART-WiFi.
    - Reader thread: đọc telemetry từ TCP
    - Writer thread: gửi lệnh 20 Hz
    - Auto-reconnect khi mất kết nối"""
    def __init__(self, config):
        RobotLink.__init__(self, config)
        self._socket = None
        self._socket_lock = threading.Lock()
        self._threads = []

    def start(self):
        reader = threading.Thread(target=self._reader_loop, name="tcp-reader")
        writer = threading.Thread(target=self._writer_loop, name="tcp-writer")
        reader.daemon = True
        writer.daemon = True
        self._threads = [reader, writer]
        reader.start()
        writer.start()

    def _connect(self):
        sock = socket.create_connection(
            (self.config.tcp_host, self.config.tcp_port),
            timeout=1.0,
        )
        sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        sock.settimeout(0.05)
        return sock

    def _reader_loop(self):
        buffer = b""
        while not self._stop_event.is_set():
            sock = None
            try:
                sock = self._connect()
                with self._socket_lock:
                    self._socket = sock
                self._set_connected(True, "")
                buffer = b""
                while not self._stop_event.is_set():
                    try:
                        chunk = sock.recv(256)
                    except socket.timeout:
                        continue
                    if not chunk:
                        raise ConnectionError("ESP8266 đóng kết nối")
                    buffer += chunk
                    while b"\n" in buffer:
                        raw, buffer = buffer.split(b"\n", 1)
                        telemetry = parse_telemetry(raw.decode("ascii", "ignore"))
                        if telemetry is not None:
                            self._update_telemetry(telemetry)
                    if len(buffer) > 4096:
                        buffer = buffer[-4096:]
            except Exception as exc:
                self._set_connected(False, str(exc))
            finally:
                with self._socket_lock:
                    self._socket = None
                if sock is not None:
                    try:
                        sock.close()
                    except Exception:
                        pass
            if not self._stop_event.is_set():
                self._stop_event.wait(1.0)

    def _writer_loop(self):
        command_period = self.config.command_period_s
        while not self._stop_event.is_set():
            started = time.monotonic()
            kind, line = self._peek_command()
            with self._socket_lock:
                sock = self._socket
                if sock is not None:
                    try:
                        sock.sendall(line.encode("ascii"))
                    except Exception as exc:
                        self._set_connected(False, str(exc))
                        try:
                            sock.shutdown(socket.SHUT_RDWR)
                        except Exception:
                            pass
                    else:
                        self._commit_command(kind, expected_line=line)
            elapsed = time.monotonic() - started
            remaining = command_period - elapsed
            if remaining > 0.0:
                self._stop_event.wait(remaining)

    def _on_close(self):
        with self._socket_lock:
            sock = self._socket
            self._socket = None
            if sock is not None:
                try:
                    sock.sendall(format_stop().encode("ascii"))
                except Exception:
                    pass
                try:
                    sock.shutdown(socket.SHUT_RDWR)
                except Exception:
                    pass
                try:
                    sock.close()
                except Exception:
                    pass

    def close(self):
        RobotLink.close(self)
        for thread in self._threads:
            thread.join(timeout=1.0)
