# Kiến trúc hệ thống

## 1. Phân tầng điều khiển

```
┌────────────────────────────────────────────────────────────┐
│ CẤP CAO: Laptop/PC (Windows/Linux/macOS, Python)           │
│  - GUI Tkinter / teleop                                     │
│  - Động học nghịch Mecanum (vx, vy, ω) → RPM 4 bánh         │
│  - Odometry (RPM thực → x, y, θ)                            │
│  - Gửi lệnh 20 Hz, nhận telemetry 50 Hz                     │
└──────────────────────────────┬─────────────────────────────┘
                               │ WiFi TCP (hoặc USB-UART)
┌──────────────────────────────┴─────────────────────────────┐
│ ESP8266 NodeMCU V3: cầu nối trong suốt TCP ↔ UART           │
└──────────────────────────────┬─────────────────────────────┘
                               │ UART2 115200 8N1
                               │ TX/RX dạng text, newline
┌──────────────────────────────┴─────────────────────────────┐
│ CẤP THẤP: STM32F103C8T6 @ 72 MHz                           │
│  - TIM2/TIM3/TIM4 encoder mode cho bánh 1–3 (x4)            │
│  - EXTI8 + giải mã mềm cho bánh 4 (thực tế x2)              │
│  - Đo RPM mỗi 10 ms                                         │
│  - 4 PID độc lập, anti-windup, derivative-on-measurement   │
│  - TIM1 CH1–CH4 PWM 20 kHz + 4 chân DIR                     │
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
2. Host tính động học nghịch → 4 RPM đặt, đóng gói `V,...` / `R,...` / `M,...`, gửi 20 Hz qua USB-UART hoặc TCP tới ESP8266.
3. ESP8266 chuyển nguyên văn byte xuống UART2; STM32 nhận UART ngắt từng byte, parser dòng lệnh, cập nhật setpoint.
4. Mỗi 10 ms: đọc delta encoder, tính RPM thực, chạy 4 PID, xuất PWM + DIR.
5. Mỗi 20 ms: gửi `T,...` gồm RPM thực và RPM đặt.
6. Host parse telemetry, cập nhật đồ thị và odometry.
7. Nếu quá 500 ms không có lệnh hợp lệ, STM32 dừng động cơ.
8. Nếu có cạnh xuống trên chân E-STOP (PB0), STM32 dừng ngay và **chốt** trạng thái dừng cho tới khi khởi động lại firmware (reset MCU hoặc cắt nguồn hoàn toàn).

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

- Encoder: JGB37-520 Hall 2 kênh A/B. Mỗi vòng motor có 11 PPR; sau hộp giảm tốc 1:30 và giải mã x4: `11 × 30 × 4 = 1320 CPR` (bánh 1–3).
- Bánh 4 hiện chỉ giải mã x2 nên CPR hiệu dụng là `11 × 30 × 2 = 660` (`ENCODER4_CPR`); xem bảng bên dưới.
- Chu kỳ đo `dt = 10 ms`.
- `RPM = Δcount · 60 / (CPR · dt)`, với `CPR = 1320` cho bánh 1–3 và `660` cho bánh 4.

Cách đọc trong firmware hiện tại:

| Bánh | Timer / chân | Chế độ | Hệ số thực tế |
|---|---|---|---|
| 1 – FL | TIM2, PA0/PA1 | Encoder phần cứng TI12 | x4 |
| 2 – FR | TIM3, PA6/PA7 | Encoder phần cứng TI12 | x4 |
| 3 – RL | TIM4, PB6/PB7 | Encoder phần cứng TI12 | x4 |
| 4 – RR | EXTI8 PB8, B đọc qua PB9 | Giải mã mềm, **chỉ ngắt cạnh A** | **x2 (660 CPR)** |

> **Đã sửa:** bánh 4 chỉ đếm 2 cạnh mỗi chu kỳ encoder (x2) nên firmware dùng CPR riêng `ENCODER4_CPR = 660` cho bánh 4 — RPM báo đúng, nhưng độ phân giải chỉ bằng một nửa. Muốn x4 hoàn toàn, cần cấu hình thêm EXTI cho kênh B (PB9) hoặc dùng timer khác; nếu giữ nguyên code, RPM đã đúng nhưng định lượng yếu hơn (nhiễu hơn).

Timer encoder dùng `TIM_ENCODERMODE_TI12`, bộ lọc `IC1Filter = IC2Filter = 6`.

## 5. PID

Mỗi bánh có một `PidController`:

- Sai lệch `e = RPM_set - RPM_actual`.
- `P = Kp·e`.
- `I` có điều kiện: chỉ tích phân khi đầu ra chưa bão hòa hoặc sai lệch đang kéo đầu ra ra khỏi bão hòa (anti-windup). `I` bị kẹp trong `[-0.5, 0.5]`.
- `D` tính trên tốc độ đo: `D = -Kd·d(RPM_actual)/dt`, có lọc thông thấp alpha = 0.30 để giảm nhiễu lượng tử encoder.
- Bù dead-zone: cộng `Dz` cùng dấu với setpoint khi đầu ra cùng dấu, giúp động cơ vượt ma sát tĩnh.
- Đầu ra chuẩn hóa `[-1, 1]`, sau đó map sang compare `0..3599` của timer.

Thông số mặc định trong `robot_config.h` chỉ để khởi động: `Kp = 0.0035`, `Ki = 0.015`, `Kd = 0.00015`, dead-zone `0.08`, `MAX_WHEEL_RPM = 333`. Bắt buộc hiệu chuẩn trên robot thật.

## 6. PWM và driver

- Timer clock 72 MHz, `ARR = 3599`, prescaler 0 → PWM 20 kHz.
- TIM1 CH1–CH4 → chân PWM bánh 1–4: PA8, PA9, PA10, PA11.
- 4 chân DIR → PB12, PB13, PB14, PB15.
- Tiến: `DIR = 0`, PWM = duty.
- Lùi: `DIR = 1`, PWM = duty.
- Dừng/coast: PWM = 0.
- `motor_brake_all()` hiện không được dùng; với sơ đồ PWM+DIR nó sẽ cho `DIR = 1` + PWM = 100%, tức chạy lùi hết ga chứ không phải phanh.

> **Cảnh báo tương thích:** firmware hiện xuất **1 PWM + 1 DIR cho mỗi bánh**. `motor.c` **không có lớp ánh xạ** `DIR` sang cặp `RPWM/LPWM`; nó chỉ đặt mức chân DIR và giữ PWM trên TIM1. Module BTS7960 trong BOM cần **2 kênh PWM riêng (RPWM và LPWM)**. Đấu DIR trực tiếp vào LPWM sẽ không đảo chiều đúng (cả hai đầu vào cùng mức cao → phanh). Nếu dùng BTS7960, phải đổi firmware sang chế độ 8 PWM như thiết kế cũ (khi đó TIM3 không còn cho encoder bánh 2 và phải remap E-STOP khỏi PB0), hoặc dùng driver hỗ trợ PWM+DIR.

## 7. E-STOP

- Ngõ vào PB0 / EXTI0, cạnh xuống, pull-up nội.
- Ngắt gọi `control_emergency_stop()`: đặt `emergency_flag = 1`, dừng tất cả PWM, reset PID và setpoint.
- Trong `control_step()`, khi `emergency_flag` bật thì mọi lệnh chuyển động bị bỏ qua và PWM giữ 0.
- Ở boot: `main.c` kiểm tra mức pin E-STOP; nếu đang LOW (nút giữ) → chốt dừng ngay.
- Cờ này không có lệnh UART để clear; chỉ được xóa khi khởi động lại firmware (nhấn nút reset MCU hoặc cắt nguồn hoàn toàn).
- Nên dùng E-STOP hai lớp: cắt nguồn động cơ bằng tiếp điểm công suất và đưa tín hiệu về PB0.

## 8. Odometry

Host tích phân vận tốc thân trong hệ tọa độ thế giới:

```
x += (vx·cosθ - vy·sinθ)·dt
y += (vx·sinθ + vy·cosθ)·dt
θ += ω·dt
```

`dt` lấy từ timestamp `t_ms` trong telemetry, không phụ thuộc tốc độ vẽ GUI. Góc θ được chuẩn hóa về `[-π, π]`.

## 9. Giới hạn và hướng phát triển

- Bánh 4 chỉ giải mã x2 (xem mục 4); RPM đã báo đúng (CPR riêng 660) nhưng độ phân giải/nhiễu kém hơn — muốn x4 cần EXTI kênh B hoặc timer.
- Firmware PWM+DIR chưa tương thích trực tiếp với BTS7960 (xem mục 6).
- E-STOP chốt tới khi khởi động lại firmware (reset MCU hoặc cắt nguồn); chưa có lệnh clear từ host.
- Chưa có IMU; odometry sẽ trôi khi bánh trượt.
- Chưa có PID vị trí/heading; hiện tại là vòng kín tốc độ.
- WiFi thêm độ trễ và jitter so với USB-UART; timeout 500 ms vẫn bảo vệ robot nhưng nên ưu tiên USB-UART khi hiệu chuẩn PID.
- Chế độ PWM thủ công chỉ điều khiển một bánh tại một thời điểm; các bánh còn lại dừng.
- Có thể thêm web app chạy trực tiếp trên ESP8266, lưu PID vào flash, hoặc ROS 2 bridge.
