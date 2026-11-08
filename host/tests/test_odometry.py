import pytest

from robot_host.config import RobotConfig
from robot_host.kinematics import inverse_kinematics
from robot_host.odometry import Odometry


def config():
    """Tạo config cho test"""
    return RobotConfig(wheel_radius_m=0.04, wheelbase_m=0.25, track_width_m=0.20, max_wheel_rpm=1000.0)


def drive(odometry, rpm, duration_s, dt_s=0.01, start_ms=0):
    """Mô phỏng lái xe: gửi RPM trong duration_s giây"""
    odometry.update(rpm, start_ms)
    steps = int(round(duration_s / dt_s))
    for index in range(1, steps + 1):
        odometry.update(rpm, start_ms + int(index * dt_s * 1000))
    return odometry.pose


def test_straight_line_distance():
    cfg = config()
    odometry = Odometry(cfg)
    rpm = inverse_kinematics(0.5, 0.0, 0.0, cfg)
    pose = drive(odometry, rpm, 2.0)
    assert pose.x == pytest.approx(1.0, abs=1e-3)
    assert pose.y == pytest.approx(0.0, abs=1e-6)
    assert pose.theta == pytest.approx(0.0, abs=1e-6)
    assert odometry.total_distance_m == pytest.approx(1.0, abs=1e-3)


def test_lateral_drive():
    cfg = config()
    odometry = Odometry(cfg)
    rpm = inverse_kinematics(0.0, 0.5, 0.0, cfg)
    pose = drive(odometry, rpm, 1.0)
    assert pose.x == pytest.approx(0.0, abs=1e-6)
    assert pose.y == pytest.approx(0.5, abs=1e-3)


def test_rotation_in_place():
    cfg = config()
    odometry = Odometry(cfg)
    rpm = inverse_kinematics(0.0, 0.0, 0.5, cfg)
    pose = drive(odometry, rpm, 2.0)
    assert pose.x == pytest.approx(0.0, abs=1e-3)
    assert pose.y == pytest.approx(0.0, abs=1e-3)
    assert pose.theta == pytest.approx(1.0, abs=1e-3)


def test_reset():
    cfg = config()
    odometry = Odometry(cfg)
    rpm = inverse_kinematics(0.5, 0.0, 0.0, cfg)
    drive(odometry, rpm, 1.0)
    odometry.reset()
    assert odometry.pose.x == 0.0
    assert odometry.pose.y == 0.0
    assert odometry.pose.theta == 0.0
    assert odometry.total_distance_m == 0.0
