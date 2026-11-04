import pytest

from robot_host.config import RobotConfig
from robot_host.kinematics import forward_kinematics, inverse_kinematics, wheel_rad_s_to_rpm


def make_config(**kwargs):
    values = dict(wheel_radius_m=0.04, wheelbase_m=0.25, track_width_m=0.20, max_wheel_rpm=1000.0)
    values.update(kwargs)
    return RobotConfig(**values)


def test_zero_velocity_gives_zero_wheels():
    config = make_config()
    assert inverse_kinematics(0.0, 0.0, 0.0, config) == [0.0, 0.0, 0.0, 0.0]


def test_pure_forward_uses_all_wheels_equally():
    config = make_config()
    rpms = inverse_kinematics(0.5, 0.0, 0.0, config)
    expected = wheel_rad_s_to_rpm(0.5 / config.wheel_radius_m)
    for value in rpms:
        assert value == pytest.approx(expected)


def test_roundtrip_body_velocity():
    config = make_config()
    for vx, vy, omega in [(0.3, 0.0, 0.0), (0.0, 0.4, 0.0), (0.1, -0.2, 0.7), (-0.3, 0.25, -1.1)]:
        rpms = inverse_kinematics(vx, vy, omega, config)
        got_vx, got_vy, got_omega = forward_kinematics(rpms, config)
        assert got_vx == pytest.approx(vx)
        assert got_vy == pytest.approx(vy)
        assert got_omega == pytest.approx(omega)


def test_roundtrip_with_inverted_vy():
    config = make_config(vy_inverted=True)
    rpms = inverse_kinematics(0.1, 0.3, -0.2, config)
    got_vx, got_vy, got_omega = forward_kinematics(rpms, config)
    assert got_vx == pytest.approx(0.1)
    assert got_vy == pytest.approx(0.3)
    assert got_omega == pytest.approx(-0.2)


def test_roundtrip_with_inverted_omega():
    config = make_config(omega_inverted=True)
    rpms = inverse_kinematics(0.1, 0.3, -0.2, config)
    got_vx, got_vy, got_omega = forward_kinematics(rpms, config)
    assert got_vx == pytest.approx(0.1)
    assert got_vy == pytest.approx(0.3)
    assert got_omega == pytest.approx(-0.2)


def test_scale_to_limit_preserves_direction():
    config = make_config(max_wheel_rpm=200.0, scale_to_limit=True)
    rpms = inverse_kinematics(5.0, 0.0, 0.0, config)
    assert max(abs(value) for value in rpms) == pytest.approx(200.0)
    assert all(value > 0.0 for value in rpms)


def test_scale_to_limit_false_clamps_individually():
    config = make_config(max_wheel_rpm=100.0, scale_to_limit=False)
    rpms = inverse_kinematics(0.5, 0.2, 0.3, config)
    assert all(-100.0 <= value <= 100.0 for value in rpms)
    assert max(abs(value) for value in rpms) == pytest.approx(100.0)


def test_yaw_wheel_pattern():
    config = make_config()
    rpm = wheel_rad_s_to_rpm(1.0)
    rpms = inverse_kinematics(0.0, 0.0, 1.0, config)
    expected = config.yaw_arm_m / config.wheel_radius_m * rpm
    assert rpms[0] == pytest.approx(-expected)
    assert rpms[1] == pytest.approx(expected)
    assert rpms[2] == pytest.approx(-expected)
    assert rpms[3] == pytest.approx(expected)
