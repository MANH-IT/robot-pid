# Robot Mecanum PID

Robot di động 4 bánh Mecanum điều khiển phân tầng:

- **Cấp thấp – STM32F103C8T6 (Blue Pill):** đọc 4 encoder Hall (TIM2/TIM3/TIM4 ở chế độ encoder + 1 bộ giải mã mềm qua EXTI), chạy 4 bộ PID vòng kín chu kỳ 10 ms, xuất 4 kênh PWM 20 kHz + 4 chân DIR cho driver cầu H, có ngắt E-STOP phần cứng, giao tiếp UART2 115200 bps và tự dừng sau 500 ms mất lệnh.
- **Cấp cao – Laptop/PC:** tính động học nghịch Mecanum, gửi lệnh vận tốc hoặc RPM, nhận telemetry 50 Hz, vẽ đồ thị và tính odometry. Kết nối robot qua USB-UART hoặc WiFi qua ESP8266 (cầu nối trong suốt UART-WiFi).

## Cấu trúc repo

```
.
├── firmware/                 # PlatformIO + STM32Cube HAL
│   ├── include/
│   │   ├── board.h           # chân encoder, PWM/DIR, UART, E-STOP, LED
│   │   ├── robot_config.h    # hình học, CPR, PID mặc định, chu kỳ
│   │   └── stm32f1xx_hal_conf.h
│   ├── src/
│   │   ├── main.c            # clock, GPIO, TIM PWM/encoder, UART, vòng lặp 10 ms
│   │   ├── encoder.c/.h      # TIM2/3/4 phần cứng + giải mã mềm cho encoder 4
│   │   ├── motor.c/.h        # PWM + DIR cho driver cầu H
│   │   ├── pid.c/.h          # PID anti-windup, derivative-on-measurement
│   │   ├── control.c/.h      # 4 PID + động học nghịch + manual + E-STOP + timeout
│   │   └── protocol.c/.h     # UART line protocol, telemetry
│   └── platformio.ini
├── esp8266/                  # NodeMCU V3, cầu nối trong suốt TCP ↔ UART
│   ├── src/main.cpp
│   └── platformio.ini
├── host/                     # Python 3 cho Laptop/PC
│   ├── main.py               # GUI Tkinter hoặc chế độ monitor
│   ├── robot_host/
│   │   ├── config.py
│   │   ├── kinematics.py
│   │   ├── odometry.py
│   │   ├── protocol.py
│   │   ├── link.py
│   │   ├── serial_link.py
│   │   ├── tcp_link.py       # WiFi TCP tới ESP8266
│   │   ├── sim_link.py
│   │   └── gui.py
│   └── tests/
├── tools/
│   └── step_response.py      # đo step response PID, xuất CSV
├── docs/
│   ├── architecture.md
│   ├── uart_protocol.md
│   ├── pinout.md
│   ├── calibration.md
│   ├── esp8266.md            # cầu nối WiFi UART
│   └── bom.md                # danh mục linh kiện
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

Qua USB-UART có dây:

```bash
cd host
source .venv/bin/activate
python3 main.py --port /dev/ttyUSB0
```

Qua WiFi (ESP8266 cầu nối trong suốt):

```bash
python3 main.py --tcp 192.168.4.1:8080
```

Linux cần quyền cổng serial nếu dùng USB-UART:

```bash
sudo usermod -aG dialout $USER
```

Nếu robot đi ngang ngược chiều, thêm `--invert-vy`; nếu xoay ngược chiều, thêm `--invert-omega`.
Sau khi đo hình học thật, truyền `--wheelbase`, `--track`, `--wheel-radius` (mét).
Cấu hình ESP8266: [docs/esp8266.md](docs/esp8266.md).

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

### 5. Kết nối WiFi qua ESP8266

NodeMCU V3 (ESP8266) chạy như cầu nối trong suốt: nhận byte TCP từ laptop và chuyển nguyên văn xuống UART2 của STM32, theo chiều ngược lại cho telemetry. Firmware có sẵn tại `esp8266/src/main.cpp` (PlatformIO, `env:nodemcuv2`).

- ESP phát AP SSID `MecanumRobot`, mật khẩu `12345678`, IP `192.168.4.1`, TCP server cổng `8080`. SSID/mật khẩu này chỉ dùng cho demo; đổi trước khi triển khai.
- Mặc định host kết nối `192.168.4.1:8080`: `python3 main.py --tcp`.
- Có thể chỉ định địa chỉ: `python3 main.py --tcp 192.168.1.50:8080`.
- Nếu dùng USB-UART có dây, giữ `--port /dev/ttyUSB0`.
- Nạp: `pio run -d esp8266 -t upload`.
- Hướng dẫn nạp và cấu hình ESP: [docs/esp8266.md](docs/esp8266.md).

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

`rpm_actual_x10` / `rpm_setpoint_x10` là RPM × 10 (số nguyên) để tránh in số thực trên MCU.

Mất lệnh hợp lệ quá **500 ms** → STM32 đặt PWM = 0 và reset PID.
Chi tiết: [docs/uart_protocol.md](docs/uart_protocol.md).

## Phần cứng chính

| Khối | Linh kiện |
|---|---|
| Động cơ | 4 × JGB37-520 12 V, 333 RPM, hộp giảm tốc 1:30 |
| Encoder | Hall 2 kênh A/B: 11 PPR × hộp giảm tốc 1:30 × 4 = **1320 CPR** (bánh 1–3); bánh 4 hiện chỉ giải mã x2 = **660 CPR hiệu dụng** — xem [docs/architecture.md](docs/architecture.md) |
| Bánh | Mecanum đường kính 80 mm, R = 0.04 m |
| Driver | 4 × cầu H (BOM ghi BTS7960); firmware hiện xuất **PWM + DIR**, xem cảnh báo tương thích trong [docs/pinout.md](docs/pinout.md) |
| MCU | STM32F103C8T6 Blue Pill |
| Giao tiếp | NodeMCU V3 ESP8266 cầu nối trong suốt UART, hoặc USB-UART có dây |
| Host | Laptop/PC chạy Python 3 (Windows/Linux/macOS) |
| Nguồn | Pin Li-ion 5S 18 V danh định (21 V đầy) → buck 12 V (động cơ), buck 5 V (logic), buck 3,3 V (ESP8266) |

Danh mục linh kiện đầy đủ (số lượng, trạng thái mua): [docs/bom.md](docs/bom.md).
Sơ đồ chân và cảnh báo mức điện áp: [docs/pinout.md](docs/pinout.md).

## Hiệu chuẩn bắt buộc trên robot thật

Thông số lý thuyết chỉ là điểm khởi đầu. Giá trị khởi điểm trong `firmware/include/robot_config.h`: `Kp = 0.0035`, `Ki = 0.015`, `Kd = 0.00015`, dead-zone `0.08`, `MAX_WHEEL_RPM = 333`, `ENCODER_CPR = 1320`. Cần đo:

1. Dead-zone PWM từng bánh, riêng chiều tiến/lùi.
2. Đặc tính PWM → RPM có tải và không tải.
3. PID từng bánh: thời gian xác lập < 0.3 s, overshoot < 10%.
4. Bán kính bánh hiệu dụng `Reff` bằng cách chạy 2 m và so sánh odometry.
5. Dấu encoder và dấu `vy` (đi ngang) của từng bánh.

Quy trình chi tiết: [docs/calibration.md](docs/calibration.md).

## An toàn

- Encoder Hall thường dùng 5 V. **Không nối trực tiếp vào STM32 3,3 V** nếu chưa kiểm tra; dùng level shifter hoặc cầu chia áp.
- Nối chung GND giữa pin, buck, STM32, driver, ESP8266 và USB-UART.
- ESP8266 (NodeMCU V3) dùng logic 3,3 V, cấp qua VIN 5 V hoặc buck 3,3 V đủ dòng (đỉnh ~500 mA); không lấy từ chân 3V3 của Blue Pill.
- E-STOP có hai lớp: cắt nguồn động cơ và ngõ vào PB0/EXTI0 của STM32. Firmware **chốt** trạng thái dừng (`emergency_flag`); cờ chỉ được xóa khi reset MCU (nút reset) hoặc cắt nguồn hoàn toàn, không có lệnh UART để clear.
- Khi hiệu chuẩn PID, kê bánh khỏi mặt bàn hoặc đặt robot trong khu vực an toàn.
- Luôn có nút dừng khẩn cấp vật lý cắt nguồn động cơ.

## Giấy phép

MIT. Xem [LICENSE](LICENSE).
