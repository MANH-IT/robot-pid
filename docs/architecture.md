# Kiến trúc hệ thống

## 1. Phân tầng điều khiển

```
┌────────────────────────────────────────────────────────────┐
│ CẤP CAO: Laptop/PC (Windows/Linux/macOS, Python)           │
│  - GUI Tkinter / teleop                                     │
│  - Động học nghịch Mecanum (vx, vy, ω) → RPM 4 bánh         │
│  - Odometry (RPM thực → x, y, θ)                            │
│  - Gửi lệnh 50 Hz, nhận telemetry 50 Hz                     │
└──────────────────────────────┬─────────────────────────────┘
                               │ WiFi TCP (hoặc USB-UART)
┌──────────────────────────────┴─────────────────────────────┐
│ ESP8266 NodeMCU V3: cầu nối trong suốt TCP ↔ UART           │
└──────────────────────────────┬─────────────────────────────┘
                               │ UART2 115200 8N1
                               │ TX/RX dạng text, newline
┌──────────────────────────────┴─────────────────────────────┐
│ CẤP THẤP: STM32F103C8T6 @ 64 MHz (HSI)                     │
│  - TIM2/TIM4 encoder mode cho bánh 1 & 3 (x4)               │
│  - EXTI10/EXTI8 + giải mã mềm cho bánh 2 & 4 (x2)           │
│  - Đo RPM mỗi 10 ms                                         │
│  - 4 PID độc lập, anti-windup, derivative-on-measurement   │
│  - RPWM (TIM1) + LPWM (TIM3) 20 kHz — 8 kênh cho BTS7960      │
│  - E-STOP EXTI0 → chốt dừng khẩn cấp                        │
│  - Timeout 500 ms → PWM 0, reset PID                        │
└──────────────────────────────┬─────────────────────────────┘
                               │ 12 V power stage
                     4 × JGB37-520 + encoder Hall
```

Lý do phân tầng: vòng PID cần jitter thấp và phải chạy độc lập với GUI/WiFi. STM32 đảm bảo chu kỳ 10 ms ổn định; laptop có thể bận vẽ đồ thị hoặc mạng WiFi chập chờn mà không làm mất vòng kín. Nếu mất kết nối quá 500 ms, firmware tự dừng động cơ.

ESP8266 chỉ là cầu nối byte trong suốt, không xử lý giao thức. Mọi lệnh vẫn do laptop tạo ra theo [uart_protocol.md](uart_protocol.md). Firmware ESP hiện tại là `esp8266/src/main.cpp` cho NodeMCU V3 (xem [esp8266.md](esp8266.md)).

## 2. Luồng dữ liệu

1. GUI đặt vận tốc thân `(vx, vy, ω)` hoặc 4 RPM trực tiếp, hoặc duty PWM thủ công cho một bánh.
2. Host tính động học nghịch → 4 RPM đặt, đóng gói `V,...` / `R,...` / `M,...`, gửi 50 Hz qua USB-UART hoặc TCP tới ESP8266.
3. ESP8266 chuyển nguyên văn byte xuống UART2; STM32 nhận UART ngắt từng byte, parser dòng lệnh, cập nhật setpoint.
4. Mỗi 10 ms: đọc delta encoder, tính RPM thực, chạy 4 PID, xuất RPWM/LPWM.
5. Mỗi 20 ms: gửi `T,...` gồm RPM thực và RPM đặt.
6. Host parse telemetry, cập nhật đồ thị và odometry.
7. Nếu quá 500 ms không có lệnh hợp lệ, STM32 dừng động cơ.
8. Nếu có cạnh xuống trên chân E-STOP (PC0), STM32 dừng ngay và **chốt** trạng thái dừng cho tới khi khởi động lại firmware (reset MCU hoặc cắt nguồn hoàn toàn).

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

- Encoder: JGB37-520 Hall 2 kênh A/B. Mỗi vòng motor có 11 PPR; sau hộp giảm tốc 1:30 và giải mã x4: `11 × 30 × 4 = 1320 CPR` (bánh 1 & 3).
- Bánh 2 & 4 chỉ giải mã x2 nên CPR hiệu dụng là `11 × 30 × 2 = 660` (`ENCODER4_CPR`); xem bảng bên dưới.
- Chu kỳ đo `dt = 10 ms`.
- `RPM = Δcount · 60 / (CPR · dt)`, với `CPR = 1320` cho bánh 1 & 3 và `660` cho bánh 2 & 4.

Cách đọc trong firmware hiện tại:

| Bánh | Timer / chân | Chế độ | Hệ số thực tế |
|---|---|---|---|
| 1 – FL | TIM2, PA0/PA1 | Encoder phần cứng TI12 | x4 (1320 CPR) |
| 2 – FR | EXTI10 PB10, B đọc qua PB11 | Giải mã mềm, **chỉ ngắt cạnh A** | **x2 (660 CPR)** |
| 3 – RL | TIM4, PB6/PB7 | Encoder phần cứng TI12 | x4 (1320 CPR) |
| 4 – RR | EXTI8 PB8, B đọc qua PB9 | Giải mã mềm, **chỉ ngắt cạnh A** | **x2 (660 CPR)** |

> **Lưu ý giải mã mềm:** bánh 2 (FR) và bánh 4 (RR) chỉ đếm x2 nên firmware dùng CPR riêng `ENCODER4_CPR = 660` cho cả hai bánh — RPM báo đúng, nhưng độ phân giải/nhiễu kém hơn bánh 1 & 3. Muốn x4 hoàn toàn, cần thêm EXTI cho kênh B (PB11/PB9) hoặc dùng timer cho encoder bánh 2/4.

Timer encoder dùng `TIM_ENCODERMODE_TI12`, bộ lọc `IC1Filter = IC2Filter = 6`.

## 5. PID

Mỗi bánh có một `PidController`:

- Sai lệch `e = RPM_set - RPM_actual`.
- `P = Kp·e`.
- `I` có điều kiện: chỉ tích phân khi đầu ra chưa bão hòa hoặc sai lệch đang kéo đầu ra ra khỏi bão hòa (anti-windup). `I` bị kẹp trong `[-0.5, 0.5]`.
- `D` tính trên tốc độ đo: `D = -Kd·d(RPM_actual)/dt`, có lọc thông thấp alpha = 0.30 để giảm nhiễu lượng tử encoder.
- Bù dead-zone: cộng `Dz` cùng dấu với setpoint khi đầu ra cùng dấu, giúp động cơ vượt ma sát tĩnh.
- Đầu ra chuẩn hóa `[-1, 1]`, sau đó map sang compare `0..3199` của timer.

Thông số mặc định trong `robot_config.h` chỉ để khởi động: `Kp = 0.0035`, `Ki = 0.015`, `Kd = 0.00015`, dead-zone `0.08`, `MAX_WHEEL_RPM = 333`. Bắt buộc hiệu chuẩn trên robot thật.

## 6. PWM và driver

- Timer clock 64 MHz (HSI / PLL ×16), `ARR = 3199`, prescaler 0 → PWM 20 kHz.
- **BTS7960 (IBT-2):** mỗi bánh cần 2 kênh PWM riêng (RPWM và LPWM). Firmware hiện tại xuất **8 kênh**:
  - RPWM bánh 1–4: PA8, PA9, PA10, PA11 (TIM1_CH1–CH4)
  - LPWM bánh 1–4: PA6, PA7, PB0, PB1 (TIM3_CH1–CH4)
- Tiến: `RPWM = duty`, `LPWM = 0`.
- Lùi: `RPWM = 0`, `LPWM = |duty|`.
- Dừng/coast: `RPWM = 0`, `LPWM = 0`.
- `motor_brake_all()`: `RPWM = LPWM = 100%` — **phanh tích cực** đúng chuẩn BTS7960.
- Encoder bánh 2 (TIM3 cũ) đã remap sang giải mã mềm EXTI10/PB10 + B đọc PB11 (x2). E-STOP đã chuyển từ PB0 sang **PC0**.

> **Tương thích:** firmware hiện tương thích trực tiếp 4 × BTS7960 RPWM/LPWM. Không nối cấp nguồn 12 V vào chân logic RPWM/LPWM/EN của module.

## 7. E-STOP

- Ngõ vào PC0 / EXTI0, cạnh xuống, pull-up nội.
- Ngắt gọi `control_emergency_stop()`: đặt `emergency_flag = 1`, dừng tất cả PWM, reset PID và setpoint.
- Trong `control_step()`, khi `emergency_flag` bật thì mọi lệnh chuyển động bị bỏ qua và PWM giữ 0.
- Ở boot: `main.c` kiểm tra mức pin E-STOP; nếu đang LOW (nút giữ) → chốt dừng ngay.
- Cờ này không có lệnh UART để clear; chỉ được xóa khi khởi động lại firmware (nhấn nút reset MCU hoặc cắt nguồn hoàn toàn).
- Nên dùng E-STOP hai lớp: cắt nguồn động cơ bằng tiếp điểm công suất và đưa tín hiệu về PC0.

## 8. Odometry

Host tích phân vận tốc thân trong hệ tọa độ thế giới:

```
x += (vx·cosθ - vy·sinθ)·dt
y += (vx·sinθ + vy·cosθ)·dt
θ += ω·dt
```

`dt` lấy từ timestamp `t_ms` trong telemetry, không phụ thuộc tốc độ vẽ GUI. Góc θ được chuẩn hóa về `[-π, π]`.

## 9. Giới hạn và hướng phát triển

- Encoder bánh 2 & 4 chỉ giải mã x2 (xem mục 4); RPM đã đúng (CPR 660) nhưng độ phân giải/nhiễu kém hơn.
- E-STOP chốt tới khi khởi động lại firmware (reset MCU hoặc cắt nguồn); chưa có lệnh clear từ host.
- Chưa có IMU; odometry sẽ trôi khi bánh trượt.
- Chưa có PID vị trí/heading; hiện tại là vòng kín tốc độ.
- WiFi thêm độ trễ và jitter so với USB-UART; timeout 500 ms vẫn bảo vệ robot nhưng nên ưu tiên USB-UART khi hiệu chuẩn PID.
- Chế độ PWM thủ công chỉ điều khiển một bánh tại một thời điểm; các bánh còn lại dừng.
- Có thể thêm web app chạy trực tiếp trên ESP8266, lưu PID vào flash, hoặc ROS 2 bridge.
