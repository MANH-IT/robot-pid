"""Mô phỏng robot để thử GUI/động học khi chưa có phần cứng."""

import math
import random
import threading
import time

from .kinematics import inverse_kinematics
from .link import RobotLink
from .protocol import Telemetry


class SimulatedLink(RobotLink):
    def __init__(self, config, time_constant_s=0.08, noise_rpm=0.8, seed=1):
        RobotLink.__init__(self, config)
        self.time_constant_s = float(time_constant_s)
        self.noise_rpm = float(noise_rpm)
        self.random = random.Random(seed)
        self._rpm = [0.0, 0.0, 0.0, 0.0]
        self._t_ms = 0.0
        self._thread = None

    def start(self):
        self._set_connected(True, "")
        self._thread = threading.Thread(target=self._loop, name="sim-link")
        self._thread.daemon = True
        self._thread.start()

    def _target_rpms(self):
        with self._lock:
            mode = self._mode
            velocity = self._target_velocity
            rpm = self._target_rpm
            manual = self._manual
        if mode == "rpm":
            return list(rpm)
        if mode == "manual":
            index = max(1, min(4, int(manual[0]))) - 1
            result = [0.0, 0.0, 0.0, 0.0]
            result[index] = float(manual[1]) * self.config.max_wheel_rpm
            return result
        return inverse_kinematics(velocity[0], velocity[1], velocity[2], self.config)

    def _loop(self):
        dt = 0.01
        emit_period = 0.02
        next_emit = 0.0
        next_tick = time.monotonic()
        alpha = 1.0 - math.exp(-dt / max(self.time_constant_s, 1e-6))
        deadzone_rpm = 4.0

        while not self._stop_event.is_set():
            targets = self._target_rpms()
            for index in range(4):
                target = targets[index]
                if abs(target) < deadzone_rpm and abs(self._rpm[index]) < deadzone_rpm:
                    target = 0.0
                self._rpm[index] += (target - self._rpm[index]) * alpha
                self._rpm[index] += self.random.gauss(0.0, self.noise_rpm) * dt
                limit = self.config.max_wheel_rpm
                if self._rpm[index] > limit:
                    self._rpm[index] = limit
                if self._rpm[index] < -limit:
                    self._rpm[index] = -limit
                if abs(self._rpm[index]) < 0.05 and target == 0.0:
                    self._rpm[index] = 0.0

            self._t_ms += dt * 1000.0
            next_emit -= dt
            if next_emit <= 0.0:
                next_emit = emit_period
                telemetry = Telemetry(int(self._t_ms), list(self._rpm), targets)
                self._update_telemetry(telemetry)

            next_tick += dt
            delay = next_tick - time.monotonic()
            if delay > 0.0:
                self._stop_event.wait(delay)
            else:
                next_tick = time.monotonic()

    def close(self):
        RobotLink.close(self)
        if self._thread is not None:
            self._thread.join(timeout=1.0)
