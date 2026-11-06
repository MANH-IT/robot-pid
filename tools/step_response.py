#!/usr/bin/env python3
"""Gửi bước RPM và ghi CSV để hiệu chỉnh PID."""

import argparse
import csv
import os
import socket
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "host"))

from robot_host.protocol import format_pid, format_rpm, format_stop, parse_telemetry


class SocketPort(object):
    def __init__(self, host, port, timeout=0.05):
        self._socket = socket.create_connection((host, port), timeout=1.0)
        self._socket.settimeout(timeout)
        self._buffer = b""

    def write(self, data):
        self._socket.sendall(data)

    def readline(self):
        while b"\n" not in self._buffer:
            try:
                chunk = self._socket.recv(256)
            except socket.timeout:
                return b""
            if not chunk:
                return b""
            self._buffer += chunk
        line, self._buffer = self._buffer.split(b"\n", 1)
        return line + b"\n"

    def close(self):
        self._socket.close()


def parse_tcp_endpoint(value):
    host = value
    port = 8080
    if ":" in value:
        host, raw_port = value.rsplit(":", 1)
        port = int(raw_port)
    return host, port


def parse_args():
    parser = argparse.ArgumentParser(description="Đo đáp ứng bước của một bánh")
    parser.add_argument("--port", default="/dev/ttyUSB0")
    parser.add_argument("--baud", type=int, default=115200)
    parser.add_argument("--tcp", metavar="HOST[:PORT]", help="kết nối TCP tới ESP8266")
    parser.add_argument("--wheel", type=int, default=1, choices=[1, 2, 3, 4])
    parser.add_argument("--rpm", type=float, default=100.0)
    parser.add_argument("--duration", type=float, default=3.0)
    parser.add_argument("--kp", type=float, default=None)
    parser.add_argument("--ki", type=float, default=None)
    parser.add_argument("--kd", type=float, default=None)
    parser.add_argument("--out", default="step_response.csv")
    return parser.parse_args()


def send(serial_port, text):
    serial_port.write(text.encode("ascii"))


def main():
    args = parse_args()
    if args.tcp:
        host, tcp_port = parse_tcp_endpoint(args.tcp)
        port = SocketPort(host, tcp_port)
    else:
        try:
            import serial
        except ImportError:
            print("Thiếu pyserial: pip install pyserial")
            return 1
        port = serial.Serial(args.port, args.baud, timeout=0.05, write_timeout=0.2)

    targets = [0.0, 0.0, 0.0, 0.0]
    targets[args.wheel - 1] = args.rpm

    try:
        if args.kp is not None and args.ki is not None and args.kd is not None:
            send(port, format_pid(args.wheel, args.kp, args.ki, args.kd))
            time.sleep(0.05)

        send(port, format_rpm(targets))
        start = time.monotonic()
        next_command = start
        step_time = None
        last_bad_time = None
        peak = 0.0
        samples = []

        while time.monotonic() - start < args.duration:
            now = time.monotonic()
            if now >= next_command:
                send(port, format_rpm(targets))
                next_command = now + 0.05
            raw = port.readline()
            if not raw:
                continue
            telemetry = parse_telemetry(raw.decode("ascii", "ignore"))
            if telemetry is None:
                continue
            if step_time is None:
                step_time = telemetry.t_ms
            value = telemetry.rpm_actual[args.wheel - 1]
            samples.append([telemetry.t_ms] + telemetry.rpm_actual + telemetry.rpm_setpoint)
            peak = max(peak, abs(value))
            if abs(value - args.rpm) > max(abs(args.rpm) * 0.02, 1.0):
                last_bad_time = telemetry.t_ms
    finally:
        send(port, format_stop())
        port.close()

    if samples:
        with open(args.out, "w", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow(
                ["t_ms", "rpm1", "rpm2", "rpm3", "rpm4", "sp1", "sp2", "sp3", "sp4"]
            )
            writer.writerows(samples)
        print("Đã ghi %d mẫu vào %s" % (len(samples), args.out))

    if args.rpm != 0.0:
        overshoot = (peak - abs(args.rpm)) / abs(args.rpm) * 100.0
        settle = 0.0
        if step_time is not None and last_bad_time is not None:
            settle = (last_bad_time - step_time) / 1000.0
        print("Bánh %d: peak=%.1f RPM, overshoot=%.1f%%, settle=%.2f s"
              % (args.wheel, peak, overshoot, settle))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
