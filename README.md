# Robot Mecanum PID + AI nhận diện người đi bộ

Robot di động 4 bánh Mecanum điều khiển phân tầng:

- **Cấp thấp – STM32F103C8T6 (Blue Pill):** đọc 4 encoder Hall bằng EXTI, chạy 4 bộ PID vòng kín chu kỳ 10 ms, xuất 8 kênh PWM 20 kHz qua 4 module BTS7960, giao tiếp UART 115200 bps, tự dừng sau 500 ms mất lệnh.
- **Cấp cao – Jetson Nano / Laptop / PC:** tính động học nghịch Mecanum, gửi lệnh vận tốc hoặc RPM, nhận telemetry 50 Hz, vẽ đồ thị, tính odometry, và chạy YOLO nhận diện người đi bộ để giảm tốc/dừng robot.

## Cấu trúc repo

```
.
├── firmware/                 # PlatformIO + STM32Cube HAL
│   ├── include/
│   │   ├── board.h           # sơ đồ chân encoder, LED
│   │   ├── robot_config.h    # hình học, CPR, PID mặc định, chu kỳ
│   │   └── stm32f1xx_hal_conf.h
│   ├── src/
│   │   ├── main.c            # clock, GPIO, TIM PWM, UART, vòng lặp 10 ms
│   │   ├── encoder.c/.h      # giải mã quadrature x4 bằng EXTI
│   │   ├── motor.c/.h        # BTS7960 RPWM/LPWM
│   │   ├── pid.c/.h          # PID anti-windup, derivative-on-measurement
│   │   ├── control.c/.h      # 4 PID + động học nghịch + timeout
│   │   └── protocol.c/.h     # UART line protocol, telemetry
│   └── platformio.ini
├── host/                     # Python 3 cho Jetson/Laptop
│   ├── main.py               # GUI Tkinter hoặc chế độ monitor
│   ├── ai_demo.py            # webcam + YOLO + dừng khi có người
│   ├── robot_host/
│   │   ├── config.py
│   │   ├── kinematics.py
│   │   ├── odometry.py
│   │   ├── protocol.py
│   │   ├── link.py
│   │   ├── serial_link.py
│   │   ├── sim_link.py
│   │   ├── gui.py
│   │   └── vision.py
│   └── tests/
├── tools/
│   └── step_response.py      # đo step response PID, xuất CSV
├── docs/
│   ├── architecture.md
│   ├── uart_protocol.md
│   ├── pinout.md
│   ├── calibration.md
│   └── ai.md
└── Makefile
```

## Chạy nhanh

### 1. Host mô phỏng (không cần phần cứng)

```bash
cd host
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
python3 main.py --sim
```

Phím tắt: `W/S` tiến-lùi, `A/D` đi ngang, `Q/E` xoay, `Space` dừng khẩn cấp.
Tab **RPM trực tiếp** gửi 4 RPM riêng và chỉnh PID online.

### 2. Host với robot thật

```bash
cd host
source .venv/bin/activate
python3 main.py --port /dev/ttyUSB0
```

Linux cần quyền cổng serial:

```bash
sudo usermod -aG dialout $USER
```

Nếu robot đi ngang ngược chiều, thêm `--invert-vy`; nếu xoay ngược chiều, thêm `--invert-omega`.
Sau khi đo hình học thật, truyền `--wheelbase`, `--track`, `--wheel-radius` (mét).

### 3. Nạp firmware

```bash
cd firmware
pio run
pio run -t upload
pio device monitor -b 115200
```

Dùng ST-Link. Nếu dùng USB-UART bootloader, đổi `upload_protocol` trong `platformio.ini`.

### 4. Kiểm thử

```bash
cd host
python3 -m pytest -q
```

### 5. AI nhận diện người đi bộ

```bash
cd host
pip install -r requirements-vision.txt
python3 ai_demo.py --port /dev/ttyUSB0 --backend ultralytics --model yolov8n.pt
```

Robot tự tiến chậm khi đường trống, giảm tốc khi người ở vùng chậm, dừng khi người ở gần.
Nhấn `Space` để tạm dừng, `Esc` để thoát. Chi tiết: [docs/ai.md](docs/ai.md).

## Giao thức UART tóm tắt

Host → STM32:

```
V,<vx>,<vy>,<omega>\n          # m/s, m/s, rad/s
R,<rpm1>,<rpm2>,<rpm3>,<rpm4>\n
STOP\n
PING\n
P,<1..4>,<kp>,<ki>,<kd>\n     # chỉnh PID online
D,<1..4>,<deadzone>\n         # bù dead-zone online
M,<1..4>,<duty>\n             # PWM vòng hở để hiệu chuẩn
```

STM32 → Host, 50 Hz:

```
T,<t_ms>,<rpm_actual_x10 x4>,<rpm_setpoint_x10 x4>\n
```

Mất lệnh hợp lệ quá **500 ms** → STM32 đặt PWM = 0 và reset PID.
Chi tiết: [docs/uart_protocol.md](docs/uart_protocol.md).

## Phần cứng chính

| Khối | Linh kiện |
|---|---|
| Động cơ | 4 × JGB37-520 12 V, 333 RPM, hộp giảm tốc 1:30 |
| Encoder | Hall 2 kênh A/B, 1320 xung/vòng trục ra sau giải mã x4 |
| Bánh | Mecanum đường kính 80 mm, R = 0.04 m |
| Driver | 4 × BTS7960 |
| MCU | STM32F103C8T6 Blue Pill |
| Máy tính | Jetson Nano B01 4 GB hoặc laptop/PC |
| Nguồn | Pin 4S Li-ion 14.8 V → buck 12 V (động cơ), buck 5 V (logic/Jetson) |

Sơ đồ chân và cảnh báo mức điện áp: [docs/pinout.md](docs/pinout.md).

## Hiệu chuẩn bắt buộc trên robot thật

Thông số lý thuyết chỉ là điểm khởi đầu. Cần đo:

1. Dead-zone PWM từng bánh, riêng chiều tiến/lùi.
2. Đặc tính PWM → RPM có tải và không tải.
3. PID từng bánh: thời gian xác lập < 0.3 s, overshoot < 10%.
4. Bán kính bánh hiệu dụng `Reff` bằng cách chạy 2 m và so sánh odometry.
5. Dấu encoder và dấu `vy` (đi ngang) của từng bánh.

Quy trình chi tiết: [docs/calibration.md](docs/calibration.md).

## An toàn

- Encoder Hall thường dùng 5 V. **Không nối trực tiếp vào STM32 3.3 V** nếu chưa kiểm tra; dùng level shifter hoặc cầu chia áp.
- Nối chung GND giữa pin, buck, STM32, BTS7960 và Jetson.
- Jetson Nano cần nguồn 5 V đủ dòng, không lấy từ chân 5 V của Blue Pill.
- Khi hiệu chuẩn PID, kê bánh khỏi mặt bàn hoặc đặt robot trong khu vực an toàn.
- Luôn có nút dừng khẩn cấp vật lý cắt nguồn động cơ.

## Giấy phép

MIT. Xem [LICENSE](LICENSE).
