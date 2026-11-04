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

## Cấu trúc

| File | Nhiệm vụ |
|---|---|
| `src/main.c` | clock, GPIO, EXTI, TIM1/TIM3 PWM, USART2, vòng lặp |
| `src/encoder.c` | giải mã quadrature x4 bằng bảng trạng thái |
| `src/pid.c` | PID anti-windup, derivative-on-measurement, dead-zone feedforward |
| `src/motor.c` | map duty → RPWM/LPWM cho BTS7960 |
| `src/control.c` | 4 encoder + 4 PID + động học nghịch + timeout + chế độ PWM thủ công |
| `src/protocol.c` | parser UART dạng dòng, telemetry 50 Hz |
| `include/board.h` | chân encoder, LED |
| `include/robot_config.h` | hình học, CPR, gain mặc định, chu kỳ, timeout |

## Thông số mặc định

```c
#define WHEEL_RADIUS_M 0.04f
#define WHEELBASE_M 0.25f
#define TRACK_WIDTH_M 0.20f
#define ENCODER_CPR 1320.0f
#define MAX_WHEEL_RPM 333.0f
#define PWM_TIM_ARR 3599u
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
   - nếu timeout: PWM = 0, reset PID,
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
- Nếu host gửi lệnh `V,...`, cả host và firmware đều tính động học nghịch; phải dùng cùng `WHEEL_RADIUS_M`, `WHEELBASE_M`, `TRACK_WIDTH_M`.
- Nếu host gửi lệnh `R,...`, chỉ host cần đúng hình học; firmware chỉ chạy PID tốc độ.
- Telemetry gửi RPM ×10 dạng số nguyên, không dùng printf float.
