# Kiến trúc hệ thống

## 1. Phân tầng điều khiển

```
┌────────────────────────────────────────────────────────────┐
│ CẤP CAO: Jetson Nano / Laptop (Ubuntu, Python)             │
│  - GUI Tkinter / teleop                                     │
│  - Động học nghịch Mecanum (vx, vy, ω) → RPM 4 bánh         │
│  - Odometry (RPM thực → x, y, θ)                            │
│  - YOLO nhận diện người đi bộ + chính sách an toàn          │
│  - Gửi lệnh 20 Hz, nhận telemetry 50 Hz                     │
└──────────────────────────────┬─────────────────────────────┘
                               │ UART2 115200 8N1
                               │ TX/RX dạng text, newline
┌──────────────────────────────┴─────────────────────────────┐
│ CẤP THẤP: STM32F103C8T6 @ 72 MHz                           │
│  - EXTI giải mã quadrature x4 cho 4 encoder (8 chân)        │
│  - Đo RPM mỗi 10 ms                                         │
│  - 4 PID độc lập, anti-windup, derivative-on-measurement   │
│  - 8 kênh PWM 20 kHz → 4 × BTS7960 (RPWM/LPWM)              │
│  - Timeout 500 ms → PWM 0, reset PID                        │
└──────────────────────────────┬─────────────────────────────┘
                               │ 12 V power stage
                     4 × JGB37-520 + encoder Hall
```

Lý do phân tầng: vòng PID cần jitter thấp và phải chạy độc lập với AI/GUI. STM32 đảm bảo chu kỳ 10 ms ổn định; Jetson có thể bận chạy YOLO mà không làm mất vòng kín.

## 2. Luồng dữ liệu

1. GUI hoặc AI đặt vận tốc thân `(vx, vy, ω)`.
2. Host tính động học nghịch → 4 RPM đặt, đóng gói `V,...` hoặc `R,...`, gửi 20 Hz.
3. STM32 nhận UART ngắt từng byte, parser dòng lệnh, cập nhật setpoint.
4. Mỗi 10 ms: đọc delta encoder, tính RPM thực, chạy 4 PID, xuất PWM.
5. Mỗi 20 ms: gửi `T,...` gồm RPM thực và RPM đặt.
6. Host parse telemetry, cập nhật đồ thị và odometry.
7. Nếu quá 500 ms không có lệnh hợp lệ, STM32 dừng động cơ.

## 3. Động học nghịch Mecanum

Thứ tự bánh: `FL, FR, RL, RR` (trước-trái, trước-phải, sau-trái, sau-phải).
Quy ước: `+vx` tới trước, `+vy` sang trái, `+ω` ngược chiều kim đồng hồ.

```
w_FL = ( vx - vy - k·ω) / R
w_FR = ( vx + vy + k·ω) / R
w_RL = ( vx + vy - k·ω) / R
w_RR = ( vx - vy + k·ω) / R

k = (wheelbase + track_width) / 2
R = bán kính bánh hiệu dụng
```

Động học thuận dùng cho odometry:

```
vx = R/4 · ( w_FL + w_FR + w_RL + w_RR)
vy = R/4 · (-w_FL + w_FR + w_RL - w_RR)
ω  = R/(4k) · (-w_FL + w_FR - w_RL + w_RR)
```

Nếu lắp bánh khiến chiều đi ngang bị đảo, đặt `vy_inverted=True` trong host và `VY_INVERTED 1` trong `robot_config.h`. Nếu chiều xoay bị đảo, dùng `omega_inverted=True` và `OMEGA_INVERTED 1`. Hai bên phải nhất quán.

## 4. Đo tốc độ

- Encoder: 1320 xung/vòng trục ra sau giải mã x4.
- Chu kỳ đo `dt = 10 ms`.
- `RPM = Δcount · 60 / (1320 · dt)`.
- Với 333 RPM, Δcount ≈ 73 xung/10 ms → đủ độ phân giải, không tràn biến 32-bit.

Giải mã quadrature dùng bảng 16 trạng thái trong `encoder.c`. Mỗi cạnh A hoặc B đều là ngắt EXTI, tương đương giải mã x4.

## 5. PID

Mỗi bánh có một `PidController`:

- Sai lệch `e = RPM_set - RPM_actual`.
- `P = Kp·e`.
- `I` có điều kiện: chỉ tích phân khi đầu ra chưa bão hòa hoặc sai lệch đang kéo đầu ra ra khỏi bão hòa (anti-windup).
- `D` tính trên tốc độ đo: `D = -Kd·d(RPM_actual)/dt`, có lọc thông thấp alpha = 0.30 để giảm nhiễu lượng tử encoder.
- Bù dead-zone: cộng `Dz` cùng dấu với setpoint khi đầu ra cùng dấu, giúp động cơ vượt ma sát tĩnh.
- Đầu ra chuẩn hóa `[-1, 1]`, sau đó map sang compare `0..3599` của timer.

Thông số mặc định chỉ để khởi động. Bắt buộc hiệu chuẩn trên robot thật.

## 6. PWM và driver

- Timer clock 72 MHz, `ARR = 3599`, prescaler 0 → PWM 20 kHz.
- TIM1 CH1–CH4: RPWM bánh 1–4.
- TIM3 CH1–CH4: LPWM bánh 1–4.
- Tiến: RPWM = duty, LPWM = 0.
- Lùi: LPWM = duty, RPWM = 0.
- Dừng: cả hai = 0 (coast). Khi timeout, `motor_stop_all()` đặt cả 8 kênh về 0.

## 7. Odometry

Host tích phân vận tốc thân trong hệ tọa độ thế giới:

```
x += (vx·cosθ - vy·sinθ)·dt
y += (vx·sinθ + vy·cosθ)·dt
θ += ω·dt
```

`dt` lấy từ timestamp `t_ms` trong telemetry, không phụ thuộc tốc độ vẽ GUI. Góc θ được chuẩn hóa về `[-π, π]`.

## 8. Giới hạn và hướng phát triển

- EXTI x4 có thể bỏ xung nếu A và B đổi đồng thời ở tốc độ rất cao; với 333 RPM và 1320 CPR, khoảng cách cạnh ≈ 136 µs nên an toàn trong thực tế. Có thể chuyển sang timer encoder mode nếu cần.
- Chưa có IMU; odometry sẽ trôi khi bánh trượt.
- Chưa có PID vị trí/heading; hiện tại là vòng kín tốc độ.
- Có thể thêm CAN/USB CDC, lưu PID vào flash, hoặc ROS 2 bridge.
