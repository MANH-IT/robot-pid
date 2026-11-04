"""Odometry từ RPM thực tế của 4 bánh."""

import math

from .kinematics import body_to_world, forward_kinematics


class Pose(object):
    def __init__(self, x=0.0, y=0.0, theta=0.0):
        self.x = float(x)
        self.y = float(y)
        self.theta = float(theta)

    def copy(self):
        return Pose(self.x, self.y, self.theta)

    def __repr__(self):
        return "Pose(x=%.4f, y=%.4f, theta=%.4f)" % (self.x, self.y, self.theta)


class Odometry(object):
    def __init__(self, config):
        self.config = config
        self.pose = Pose()
        self.last_t_ms = None
        self.total_distance_m = 0.0
        self.last_vx = 0.0
        self.last_vy = 0.0
        self.last_omega = 0.0

    def reset(self):
        self.pose = Pose()
        self.last_t_ms = None
        self.total_distance_m = 0.0
        self.last_vx = 0.0
        self.last_vy = 0.0
        self.last_omega = 0.0

    def update(self, rpm_actual, t_ms):
        if self.last_t_ms is None:
            self.last_t_ms = int(t_ms)
            return self.pose

        dt = (int(t_ms) - self.last_t_ms) / 1000.0
        self.last_t_ms = int(t_ms)
        if dt <= 0.0 or dt > 1.0:
            return self.pose

        vx, vy, omega = forward_kinematics(rpm_actual, self.config)
        dx, dy, dtheta = body_to_world(vx, vy, omega, self.pose.theta, dt)
        self.pose.x += dx
        self.pose.y += dy
        self.pose.theta = math.atan2(math.sin(self.pose.theta + dtheta), math.cos(self.pose.theta + dtheta))
        self.total_distance_m += math.hypot(dx, dy)
        self.last_vx = vx
        self.last_vy = vy
        self.last_omega = omega
        return self.pose
