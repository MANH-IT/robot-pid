"""Giao thức UART dạng text, newline-terminated.

Host -> STM32:
    V,<vx>,<vy>,<omega>          vận tốc thân (m/s, m/s, rad/s)
    R,<rpm1>,<rpm2>,<rpm3>,<rpm4>
    STOP
    PING
    P,<1..4>,<kp>,<ki>,<kd>      chỉnh PID online
    D,<1..4>,<deadzone>          chỉnh bù dead-zone online (0..0.5)

STM32 -> Host (50 Hz):
    T,<t_ms>,<rpm_act_x10 x4>,<rpm_set_x10 x4>

Telemetry gửi RPM nhân 10 dưới dạng số nguyên để tránh printf float trên MCU.
"""


class Telemetry(object):
    """Telemetry từ STM32:
    - t_ms: timestamp (ms)
    - rpm_actual: RPM thực tế 4 bánh
    - rpm_setpoint: RPM đặt 4 bánh"""
    def __init__(self, t_ms, rpm_actual, rpm_setpoint):
        self.t_ms = int(t_ms)
        self.rpm_actual = list(rpm_actual)
        self.rpm_setpoint = list(rpm_setpoint)

    def __repr__(self):
        return "Telemetry(t=%d, act=%s, sp=%s)" % (self.t_ms, self.rpm_actual, self.rpm_setpoint)


def format_velocity(vx, vy, omega):
    """Gửi lệnh vận tốc thân (m/s, m/s, rad/s)"""
    return "V,%.4f,%.4f,%.4f\n" % (float(vx), float(vy), float(omega))


def format_rpm(rpms):
    """Gửi lệnh RPM trực tiếp cho 4 bánh"""
    if len(rpms) != 4:
        raise ValueError("format_rpm cần đúng 4 giá trị")
    return "R,%.2f,%.2f,%.2f,%.2f\n" % tuple(float(r) for r in rpms)


def format_stop():
    """Gửi lệnh STOP: đặt setpoint 0, reset PID, PWM về 0"""
    return "STOP\n"


def format_ping():
    """Gửi lệnh PING: kiểm tra kết nối, STM32 trả PONG"""
    return "PING\n"


def format_pid(index, kp, ki, kd):
    """Gửi lệnh chỉnh PID online: P,<index>,<kp>,<ki>,<kd>"""
    return "P,%d,%.6f,%.6f,%.6f\n" % (int(index), float(kp), float(ki), float(kd))


def format_deadzone(index, deadzone):
    """Gửi lệnh chỉnh dead-zone online: D,<index>,<deadzone>"""
    return "D,%d,%.4f\n" % (int(index), float(deadzone))


def format_manual(index, duty):
    """Gửi lệnh PWM thủ công: M,<index>,<duty>"""
    return "M,%d,%.4f\n" % (int(index), float(duty))


def parse_telemetry(line):
    """Parse telemetry từ STM32:
    - Format: T,<t_ms>,<rpm_act x4>,<rpm_set x4>
    - RPM nhân 10 → chia 10 để trả về float
    - Trả về Telemetry object hoặc None nếu lỗi"""
    if line is None:
        return None
    line = line.strip()
    if not line:
        return None
    parts = line.split(",")
    if len(parts) != 10 or parts[0] != "T":
        return None
    try:
        t_ms = int(parts[1])
        values = [int(p) / 10.0 for p in parts[2:]]
    except ValueError:
        return None
    return Telemetry(t_ms, values[0:4], values[4:8])
