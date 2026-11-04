"""Liên kết UART thật tới STM32, tự động kết nối lại."""

import threading
import time

from .link import RobotLink
from .protocol import format_stop, parse_telemetry


class SerialLink(RobotLink):
    def __init__(self, config):
        RobotLink.__init__(self, config)
        self._serial = None
        self._serial_lock = threading.Lock()
        self._threads = []

    def start(self):
        reader = threading.Thread(target=self._reader_loop, name="serial-reader")
        writer = threading.Thread(target=self._writer_loop, name="serial-writer")
        reader.daemon = True
        writer.daemon = True
        self._threads = [reader, writer]
        reader.start()
        writer.start()

    def _reader_loop(self):
        try:
            import serial
        except ImportError:
            self._set_connected(False, "Thiếu pyserial: pip install pyserial")
            return

        while not self._stop_event.is_set():
            ser = None
            try:
                ser = serial.Serial(
                    self.config.serial_port,
                    self.config.baudrate,
                    timeout=0.05,
                    write_timeout=0.2,
                )
                with self._serial_lock:
                    self._serial = ser
                self._set_connected(True, "")
                while not self._stop_event.is_set():
                    raw = ser.readline()
                    if not raw:
                        continue
                    try:
                        line = raw.decode("ascii", "ignore")
                    except Exception:
                        continue
                    telemetry = parse_telemetry(line)
                    if telemetry is not None:
                        self._update_telemetry(telemetry)
            except Exception as exc:
                self._set_connected(False, str(exc))
            finally:
                with self._serial_lock:
                    self._serial = None
                if ser is not None:
                    try:
                        ser.close()
                    except Exception:
                        pass
            if not self._stop_event.is_set():
                self._stop_event.wait(1.0)

    def _writer_loop(self):
        command_period = self.config.command_period_s
        while not self._stop_event.is_set():
            started = time.monotonic()
            line = self._command_line()
            with self._serial_lock:
                ser = self._serial
                if ser is not None:
                    try:
                        ser.write(line.encode("ascii"))
                    except Exception as exc:
                        self._set_connected(False, str(exc))
            elapsed = time.monotonic() - started
            remaining = command_period - elapsed
            if remaining > 0.0:
                self._stop_event.wait(remaining)

    def _on_close(self):
        with self._serial_lock:
            ser = self._serial
            self._serial = None
            if ser is not None:
                try:
                    ser.write(format_stop().encode("ascii"))
                    ser.flush()
                except Exception:
                    pass
                try:
                    ser.close()
                except Exception:
                    pass

    def close(self):
        RobotLink.close(self)
        for thread in self._threads:
            thread.join(timeout=1.0)
