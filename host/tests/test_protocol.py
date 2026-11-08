from robot_host.protocol import (
    format_deadzone,
    format_pid,
    format_rpm,
    format_stop,
    format_velocity,
    parse_telemetry,
)


# Test format_velocity: gửi lệnh vận tốc thân
def test_velocity_format():
    assert format_velocity(0.5, -0.25, 1.2) == "V,0.5000,-0.2500,1.2000\n"


# Test format_rpm: gửi lệnh RPM trực tiếp
def test_rpm_format():
    assert format_rpm([1, 2, 3.5, -4]) == "R,1.00,2.00,3.50,-4.00\n"


# Test format_stop và format_pid: gửi lệnh STOP và chỉnh PID
def test_stop_and_pid_format():
    assert format_stop() == "STOP\n"
    assert format_pid(1, 0.0035, 0.015, 0.00015) == "P,1,0.003500,0.015000,0.000150\n"
    assert format_deadzone(2, 0.08) == "D,2,0.0800\n"


# Test parse_telemetry: parse telemetry từ STM32
def test_parse_telemetry():
    telemetry = parse_telemetry("T,12345,10,-20,0,333,-1,2,-3,4\n")
    assert telemetry is not None
    assert telemetry.t_ms == 12345
    assert telemetry.rpm_actual == [1.0, -2.0, 0.0, 33.3]
    assert telemetry.rpm_setpoint == [-0.1, 0.2, -0.3, 0.4]


# Test parse_telemetry: reject bad lines
def test_parse_telemetry_rejects_bad_lines():
    assert parse_telemetry("") is None
    assert parse_telemetry("V,1,2,3") is None
    assert parse_telemetry("T,1,2,3") is None
    assert parse_telemetry("T,x,1,2,3,4,5,6,7,8") is None
