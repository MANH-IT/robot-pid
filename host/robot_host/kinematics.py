"""Động học Mecanum.

Quy ước thứ tự bánh: [trước-trái, trước-phải, sau-trái, sau-phải] (FL, FR, RL, RR).
Trục thân robot: +vx hướng tới, +vy hướng sang trái, +omega quay ngược chiều kim đồng hồ.
Bánh quay dương khi robot tiến tới.

Ma trận nghịch đảo áp dụng cho cấu hình bánh Mecanum chữ X tiêu chuẩn:
    w_FL = ( vx - vy - k*w) / R
    w_FR = ( vx + vy + k*w) / R
    w_RL = ( vx + vy - k*w) / R
    w_RR = ( vx - vy + k*w) / R
với k = (wheelbase + track_width) / 2.
Nếu robot thực tế đi ngang ngược chiều, đặt vy_inverted=True trong RobotConfig.
Nếu chiều xoay ngược, đặt omega_inverted=True; firmware dùng OMEGA_INVERTED tương ứng.
"""

import math


def _clamp(value, low, high):
    """Giới hạn giá trị trong [low, high]"""
    if value < low:
        return low
    if value > high:
        return high
    return value


def _apply_vy_sign(vy, config):
    """Áp dụng dấu vy inverted nếu cấu hình"""
    return -vy if config.vy_inverted else vy


def wheel_rpm_to_rad_s(rpm):
    """Chuyển RPM sang rad/s"""
    return rpm * 2.0 * math.pi / 60.0


def wheel_rad_s_to_rpm(rad_s):
    """Chuyển rad/s sang RPM"""
    return rad_s * 60.0 / (2.0 * math.pi)


def inverse_kinematics(vx, vy, omega, config):
    """Chuyển vận tốc thân (m/s, m/s, rad/s) thành 4 tốc độ bánh (RPM).
    - vx: vận tốc tiến (m/s)
    - vy: vận tốc ngang (m/s)
    - omega: vận tốc xoay (rad/s)
    - config: cấu hình robot (bán kính, wheelbase, track, max_rpm, v.v.)
    Trả về list 4 phần tử. Nếu scale_to_limit=True và một bánh vượt max_wheel_rpm, toàn bộ vector được co lại để giữ đúng hướng chuyển động.
    """
    vy = _apply_vy_sign(vy, config)
    if config.omega_inverted:
        omega = -omega
    radius = config.wheel_radius_m
    arm = config.yaw_arm_m

    w1 = (vx - vy - arm * omega) / radius
    w2 = (vx + vy + arm * omega) / radius
    w3 = (vx + vy - arm * omega) / radius
    w4 = (vx - vy + arm * omega) / radius

    rpms = [wheel_rad_s_to_rpm(w1), wheel_rad_s_to_rpm(w2), wheel_rad_s_to_rpm(w3), wheel_rad_s_to_rpm(w4)]
    peak = max(abs(r) for r in rpms)

    if peak > config.max_wheel_rpm and peak > 0.0:
        if config.scale_to_limit:
            scale = config.max_wheel_rpm / peak
            rpms = [r * scale for r in rpms]
        else:
            rpms = [_clamp(r, -config.max_wheel_rpm, config.max_wheel_rpm) for r in rpms]

    return rpms


def forward_kinematics(rpms, config):
    """Chuyển 4 tốc độ bánh (RPM) thành vận tốc thân (vx, vy, omega).
    - rpms: list 4 RPM [FL, FR, RL, RR]
    - config: cấu hình robot
    Trả về (vx, vy, omega) trong m/s, m/s, rad/s"""
    if len(rpms) != 4:
        raise ValueError("forward_kinematics cần đúng 4 tốc độ bánh")

    radius = config.wheel_radius_m
    arm = config.yaw_arm_m
    w = [wheel_rpm_to_rad_s(r) for r in rpms]

    vx = radius * (w[0] + w[1] + w[2] + w[3]) / 4.0
    vy_left = radius * (-w[0] + w[1] + w[2] - w[3]) / 4.0
    omega = radius * (-w[0] + w[1] - w[2] + w[3]) / (4.0 * arm)
    vy = _apply_vy_sign(vy_left, config)
    if config.omega_inverted:
        omega = -omega
    return vx, vy, omega


def body_to_world(vx, vy, omega, theta, dt):
    """Tích phân một bước odometry trong hệ tọa độ thế giới.
    - vx, vy: vận tốc thân (m/s)
    - omega: vận tốc xoay (rad/s)
    - theta: góc hiện tại (rad)
    - dt: thời gian bước (s)
    Trả về (dx, dy, dtheta) trong hệ tọa độ thế giới"""
    cos_t = math.cos(theta)
    sin_t = math.sin(theta)
    dx = (vx * cos_t - vy * sin_t) * dt
    dy = (vx * sin_t + vy * cos_t) * dt
    dtheta = omega * dt
    return dx, dy, dtheta
