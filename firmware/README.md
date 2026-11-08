# Firmware STM32F103C8T6

## Build và nạp

```bash
pio run
pio run -t upload
pio device monitor -b 115200
```

Nếu chưa có PlatformIO:

```bash
pip install platformio
```

Board: `bluepill_f103c8`, framework `stm32cube`, clock 72 MHz từ HSE 8 MHz.
Upload mặc định dùng ST-Link.

## Cấu trúc thư mục

| File | Nhiệm vụ |
|---|---|
| `src/main.c` | Clock, GPIO, TIM1 PWM/encoder, USART2, vòng lặp 10 ms |
| `src/encoder.c` | TIM2/3/4 phần cứngEncoder + giải mã mềm cho bánh 4 (x2) |
| `src/pid.c` | PID anti-windup, derivative-on-measurement, dead-zone feedforward |
| `src/motor.c` | PWM + DIR cho driver cầu H (không ánh xạ sang RPWM/LPWM) |
| `src/control.c` | 4 PID, động học nghịch, manual, E-STOP, timeout |
| `src/protocol.c` | Parser UART dòng lệnh, telemetry 50 Hz |
| `include/board.h` | Chân encoder, PWM/DIR, UART, E-STOP, LED |
| `include/robot_config.h` | Hình học, CPR, gain mặc định, chu kỳ, timeout |

## Thông số mặc định

```c
#define WHEEL_RADIUS_M 0.04f
#define WHEELBASE_M 0.25f
#define TRACK_WIDTH_M 0.20f
#define ENCODER_CPR 1320.0f   /* bánh 1–3, x4 (11×30×4) */
#define ENCODER4_CPR 660.0f   /* bánh 4, x2 (11×30×2) */
#define MAX_WHEEL_RPM 333.0f
#define PWM_TIM_ARR 3599u     /* 72 MHz / 20 kHz - 1 */
#define ROBOT_CONTROL_PERIOD_MS 10u
#define ROBOT_TELEMETRY_PERIOD_MS 20u
#define ROBOT_UART_TIMEOUT_MS 500u
#define PID_KP_DEFAULT 0.0035f
#define PID_KI_DEFAULT 0.015f
#define PID_KD_DEFAULT 0.00015f
#define DEADZONE_DEFAULT 0.08f
```

Các thông số này **phải được hiệu chuẩn** theo robot thật, xem `docs/calibration.md`.

## Vòng lặp chính

1. `protocol_process()`: lấy byte từ ring buffer, parse dòng lệnh.
2. Mỗi 10 ms:
   - đọc delta 4 encoder,
   - tính RPM thực,
   - nếu timeout (>500 ms): PWM = 0, reset PID,
   - nếu có lệnh: chạy 4 PID, cập nhật PWM.
3. Mỗi 20 ms: gửi telemetry.
4. Mỗi 500 ms: nhấp nháy LED PC13.

## Thêm bánh hoặc đổi chân

1. Sửa `include/board.h` cho chân encoder.
2. Sửa `HAL_TIM_PWM_MspInit` và `MX_GPIO_Init` trong `main.c`.
3. Sửa `motor.c` nếu đổi timer/kênh PWM.
4. Sửa `control.c` nếu đổi thứ tự bánh hoặc thêm bánh.
5. Cập nhật host tương ứng.

## Lưu ý

- `VY_INVERTED` trong `robot_config.h` phải khớp `--invert-vy` của host.
- `OMEGA_INVERTED` trong `robot_config.h` phải khớp `--invert-omega` của host.
- Nếu host gửi lệnh `V,...`, cả host và firmware đều tính động học nghịch; phải dùng chung `WHEEL_RADIUS_M`, `WHEELBASE_M`, `TRACK_WIDTH_M`.
- Nếu host gửi lệnh `R,...`, chỉ host cần đúng hình học; firmware chỉ chạy PID tốc độ.
- Telemetry gửi RPM ×10 dạng số nguyên, không dùng printf float.
- **E-STOP**: nút bấm normally-open (NO), ngắt xuống (falling edge). Cờ `emergency_flag` chỉ xóa khi reset MCU hoặc cắt nguồn hoàn toàn – không có lệnh UART để clear.
- Cân nhắc thêm tiếp điểm E-STOP vật lý cắt 12 V động cơ để đảm bảo an toàn tuyệt đối.