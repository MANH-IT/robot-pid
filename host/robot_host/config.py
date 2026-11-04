"""Cấu hình dùng chung cho host. Giữ đồng bộ với firmware/include/robot_config.h."""

import math


class RobotConfig(object):
    def __init__(
        self,
        wheel_radius_m=0.04,
        wheelbase_m=0.25,
        track_width_m=0.20,
        counts_per_rev=1320,
        max_wheel_rpm=333.0,
        vy_inverted=False,
        omega_inverted=False,
        scale_to_limit=True,
        serial_port="/dev/ttyUSB0",
        baudrate=115200,
        command_rate_hz=20.0,
        telemetry_timeout_s=0.5,
        max_linear_speed=1.2,
        max_angular_speed=2.5,
    ):
        self.wheel_radius_m = float(wheel_radius_m)
        self.wheelbase_m = float(wheelbase_m)
        self.track_width_m = float(track_width_m)
        self.counts_per_rev = int(counts_per_rev)
        self.max_wheel_rpm = float(max_wheel_rpm)
        self.vy_inverted = bool(vy_inverted)
        self.omega_inverted = bool(omega_inverted)
        self.scale_to_limit = bool(scale_to_limit)
        self.serial_port = str(serial_port)
        self.baudrate = int(baudrate)
        self.command_rate_hz = float(command_rate_hz)
        self.telemetry_timeout_s = float(telemetry_timeout_s)
        self.max_linear_speed = float(max_linear_speed)
        self.max_angular_speed = float(max_angular_speed)

    @property
    def yaw_arm_m(self):
        return 0.5 * (self.wheelbase_m + self.track_width_m)

    @property
    def wheel_circumference_m(self):
        return 2.0 * math.pi * self.wheel_radius_m

    @property
    def counts_per_meter(self):
        return self.counts_per_rev / self.wheel_circumference_m

    @property
    def command_period_s(self):
        return 1.0 / max(self.command_rate_hz, 1.0)

    def copy(self):
        return RobotConfig(
            wheel_radius_m=self.wheel_radius_m,
            wheelbase_m=self.wheelbase_m,
            track_width_m=self.track_width_m,
            counts_per_rev=self.counts_per_rev,
            max_wheel_rpm=self.max_wheel_rpm,
            vy_inverted=self.vy_inverted,
            omega_inverted=self.omega_inverted,
            scale_to_limit=self.scale_to_limit,
            serial_port=self.serial_port,
            baudrate=self.baudrate,
            command_rate_hz=self.command_rate_hz,
            telemetry_timeout_s=self.telemetry_timeout_s,
            max_linear_speed=self.max_linear_speed,
            max_angular_speed=self.max_angular_speed,
        )
