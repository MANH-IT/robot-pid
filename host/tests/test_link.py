"""Test hàng đợi lệnh và chế độ của RobotLink."""

from robot_host.config import RobotConfig
from robot_host.kinematics import inverse_kinematics
from robot_host.link import RobotLink
from robot_host.protocol import Telemetry, format_rpm
from robot_host.tcp_link import TcpLink


def make_link():
    return RobotLink(RobotConfig())


def test_default_command_is_zero_velocity():
    link = make_link()
    kind, line = link._peek_command()
    assert kind == "periodic"
    assert line == "R,0.00,0.00,0.00,0.00\n"


def test_set_velocity_sends_host_kinematics_rpm():
    link = make_link()
    link.set_velocity(0.2, -0.1, 0.5)
    expected = format_rpm(inverse_kinematics(0.2, -0.1, 0.5, link.config))
    assert link._peek_command() == ("periodic", expected)


def test_stop_has_priority_and_commit_clears_it():
    link = make_link()
    link.set_pid(2, 0.1, 0.2, 0.3)
    link.stop()

    kind, line = link._peek_command()
    assert (kind, line) == ("stop", "STOP\n")

    link._commit_command(kind, expected_line=line)
    kind, line = link._peek_command()
    assert kind == "line"
    assert line == "P,2,0.100000,0.200000,0.300000\n"


def test_ping_has_priority_over_tuning_lines():
    link = make_link()
    link.set_deadzone(1, 0.05)
    link.ping()

    kind, line = link._peek_command()
    assert (kind, line) == ("ping", "PING\n")
    link._commit_command(kind, expected_line=line)

    kind, line = link._peek_command()
    assert (kind, line) == ("line", "D,1,0.0500\n")


def test_mismatched_commit_keeps_line_queued():
    link = make_link()
    link.set_pid(1, 0.1, 0.2, 0.3)
    kind, line = link._peek_command()
    link._commit_command(kind, expected_line="P,1,9,9,9\n")
    assert link._peek_command() == (kind, line)


def test_rpm_and_manual_modes_repeat_periodically():
    link = make_link()
    link.set_rpm(1.0, 2.0, 3.5, -4.0)
    assert link._peek_command() == ("periodic", "R,1.00,2.00,3.50,-4.00\n")

    link.set_manual(3, 0.25)
    assert link._peek_command() == ("periodic", "M,3,0.2500\n")


def test_velocity_after_manual_switches_mode():
    link = make_link()
    link.set_manual(1, 0.5)
    link.set_velocity(0.0, 0.0, 0.0)
    assert link._peek_command() == ("periodic", "R,0.00,0.00,0.00,0.00\n")


def test_command_rate_default_is_50_hz():
    config = RobotConfig()
    assert config.command_rate_hz == 50.0
    assert config.command_period_s == 0.02


def test_telemetry_freshness():
    link = make_link()
    assert link.telemetry_fresh() is False
    link._update_telemetry(Telemetry(1, [0, 0, 0, 0], [0, 0, 0, 0]))
    assert link.telemetry_fresh() is True


def test_parse_discovery_response():
    from robot_host.discovery import parse_response

    assert parse_response(b"ROBOT!172.20.10.10:8080\n") == ("172.20.10.10", 8080)
    assert parse_response(b"ROBOT!10.0.0.5\n") == ("10.0.0.5", 8080)
    assert parse_response(b"T,1,0,0,0,0,0,0,0,0\n") is None
    assert parse_response(b"ROBOT!") is None
    assert parse_response(b"ROBOT!1.2.3.4:abc\n") is None


def test_tcp_link_set_endpoint_and_reconnect():
    config = RobotConfig(transport="tcp", tcp_host="1.2.3.4", tcp_port=8080)
    link = TcpLink(config)
    assert link.set_endpoint("10.0.0.9", 9000) is True
    assert config.tcp_host == "10.0.0.9"
    assert config.tcp_port == 9000
    assert link.reconnect() is True
    assert link._peek_command()[0] == "stop"
