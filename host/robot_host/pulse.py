"""Tạo chuỗi xung bậc thang / xung vuông cho hiệu chỉnh PID.

Mỗi phần tử của plan là (rpm, thời_lượng_giây); GUI duyệt tuần tự theo
đồng hồ monotonic và gửi lệnh R,... tương ứng.
"""


def build_plan(amplitude_rpm, width_ms, period_ms, count, square, max_rpm):
    """Trả về danh sách (rpm, duration_s) cho các pha ON/OFF.

    - Bậc thang: ON = width, OFF = width.
    - Xung vuông: ON = width, OFF = period - width.
    Ném ValueError (tiếng Việt) nếu cấu hình không hợp lệ.
    """
    amplitude = float(amplitude_rpm)
    width_s = float(width_ms) / 1000.0
    period_s = float(period_ms) / 1000.0
    count = int(count)

    if width_s <= 0.0:
        raise ValueError("độ rộng ON phải > 0")
    if count < 1:
        raise ValueError("số xung phải >= 1")
    if amplitude == 0.0:
        raise ValueError("biên độ phải khác 0")
    if abs(amplitude) > float(max_rpm):
        raise ValueError("biên độ vượt %.0f RPM" % float(max_rpm))

    if square:
        if period_s <= width_s:
            raise ValueError("chu kỳ phải lớn hơn độ rộng ON")
        off_s = period_s - width_s
    else:
        off_s = width_s

    plan = []
    for _ in range(count):
        plan.append((amplitude, width_s))
        plan.append((0.0, off_s))
    return plan


def analyze_step(samples, target_rpm, on_duration_s):
    """Phân tích đáp ứng bậc thang từ samples [(t_s, rpm)] trong pha ON.

    Trả về dict hoặc None nếu không đủ mẫu:
      sample_count, peak_rpm, rise_time_ms, overshoot_pct,
      settling_time_ms, steady_error_rpm.
    """
    target = float(target_rpm)
    duration = float(on_duration_s)
    data = []
    for t_value, rpm in samples:
        t_value = float(t_value)
        if 0.0 <= t_value <= duration + 0.05:
            data.append((t_value, float(rpm)))
    if len(data) < 3 or abs(target) < 1e-6 or duration <= 0.0:
        return None

    sign = 1.0 if target > 0.0 else -1.0
    magnitude = abs(target)

    rise_time_ms = None
    for t_value, rpm in data:
        if rpm * sign >= 0.9 * magnitude:
            rise_time_ms = t_value * 1000.0
            break

    peak = max(sign * rpm for _, rpm in data)
    overshoot_pct = max(0.0, (peak - magnitude) / magnitude * 100.0)

    tolerance = max(0.05 * magnitude, 1.0)
    settling_time_ms = 0.0
    for index in range(len(data) - 1, -1, -1):
        t_value, rpm = data[index]
        if abs(rpm - target) > tolerance:
            if index + 1 < len(data):
                settling_time_ms = data[index + 1][0] * 1000.0
            else:
                settling_time_ms = t_value * 1000.0
            break

    tail = [rpm for t_value, rpm in data if t_value >= 0.8 * duration]
    if not tail:
        tail = [rpm for _, rpm in data[-max(1, len(data) // 5):]]
    steady_error = sum(tail) / len(tail) - target

    return {
        "sample_count": len(data),
        "peak_rpm": peak * sign,
        "rise_time_ms": rise_time_ms,
        "overshoot_pct": overshoot_pct,
        "settling_time_ms": settling_time_ms,
        "steady_error_rpm": steady_error,
    }
