"""Lớp liên kết chung giữa GUI và robot (serial thật hoặc mô phỏng)."""

import threading
import time
from collections import deque

from .odometry import Odometry
from .protocol import (
    format_deadzone,
    format_manual,
    format_pid,
    format_ping,
    format_rpm,
    format_stop,
    format_velocity,
)


class RobotLink(object):
    """Lớp liên kết chung giữa GUI và robot:
    - Serial thật hoặc mô phỏng
    - Quản lý telemetry, mode, target, odometry
    - Thread-safe với lock"""
    def __init__(self, config):
        self.config = config
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._telemetry = None
        self._telemetry_monotonic = 0.0
        self._connected = False
        self._error = ""
        self._mode = "velocity"
        self._target_velocity = (0.0, 0.0, 0.0)
        self._target_rpm = (0.0, 0.0, 0.0, 0.0)
        self._manual = (1, 0.0)
        self._pending_stop = False
        self._pending_ping = False
        self._pending_lines = deque()
        self.odometry = Odometry(config)

    def start(self):
        raise NotImplementedError

    def close(self):
        self._stop_event.set()
        self._on_close()

    def _on_close(self):
        pass

    def set_velocity(self, vx, vy, omega):
        with self._lock:
            self._mode = "velocity"
            self._target_velocity = (float(vx), float(vy), float(omega))

    def set_rpm(self, rpm1, rpm2, rpm3, rpm4):
        with self._lock:
            self._mode = "rpm"
            self._target_rpm = (float(rpm1), float(rpm2), float(rpm3), float(rpm4))

    def set_manual(self, index, duty):
        with self._lock:
            self._mode = "manual"
            self._manual = (int(index), float(duty))

    def stop(self):
        with self._lock:
            self._mode = "velocity"
            self._target_velocity = (0.0, 0.0, 0.0)
            self._target_rpm = (0.0, 0.0, 0.0, 0.0)
            self._pending_stop = True

    def ping(self):
        with self._lock:
            self._pending_ping = True

    def set_pid(self, index, kp, ki, kd):
        with self._lock:
            self._pending_lines.append(format_pid(index, kp, ki, kd))

    def set_deadzone(self, index, deadzone):
        with self._lock:
            self._pending_lines.append(format_deadzone(index, deadzone))

    def reset_odometry(self):
        with self._lock:
            self.odometry.reset()

    def _set_connected(self, connected, error=""):
        with self._lock:
            self._connected = bool(connected)
            self._error = str(error)

    def _update_telemetry(self, telemetry):
        with self._lock:
            self._telemetry = telemetry
            self._telemetry_monotonic = time.monotonic()
            self.odometry.update(telemetry.rpm_actual, telemetry.t_ms)

    def _command_line(self):
        with self._lock:
            if self._pending_lines:
                return self._pending_lines.popleft()
            if self._pending_stop:
                self._pending_stop = False
                return format_stop()
            if self._pending_ping:
                self._pending_ping = False
                return format_ping()
            if self._mode == "rpm":
                return format_rpm(self._target_rpm)
            if self._mode == "manual":
                return format_manual(self._manual[0], self._manual[1])
            return format_velocity(*self._target_velocity)

    def snapshot(self):
        with self._lock:
            telemetry = self._telemetry
            age_s = None
            if telemetry is not None:
                age_s = time.monotonic() - self._telemetry_monotonic
            pose = self.odometry.pose.copy()
            distance = self.odometry.total_distance_m
            return {
                "connected": self._connected,
                "error": self._error,
                "telemetry": telemetry,
                "age_s": age_s,
                "pose": pose,
                "distance_m": distance,
                "mode": self._mode,
                "target_velocity": self._target_velocity,
                "target_rpm": self._target_rpm,
                "manual": self._manual,
            }

    def telemetry_fresh(self):
        with self._lock:
            if self._telemetry is None:
                return False
            age = time.monotonic() - self._telemetry_monotonic
        return age <= self.config.telemetry_timeout_s

