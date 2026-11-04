# Sơ đồ chân và đấu dây

## 1. Bảng chân STM32F103C8T6

| Chân | Chức năng | Nối tới |
|---|---|---|
| PA2 | USART2_TX | RX của Jetson/Laptop (3.3 V) |
| PA3 | USART2_RX | TX của Jetson/Laptop (3.3 V) |
| PA8 | TIM1_CH1 | BTS7960 #1 RPWM |
| PA6 | TIM3_CH1 | BTS7960 #1 LPWM |
| PA9 | TIM1_CH2 | BTS7960 #2 RPWM |
| PA7 | TIM3_CH2 | BTS7960 #2 LPWM |
| PA10 | TIM1_CH3 | BTS7960 #3 RPWM |
| PB0 | TIM3_CH3 | BTS7960 #3 LPWM |
| PA11 | TIM1_CH4 | BTS7960 #4 RPWM |
| PB1 | TIM3_CH4 | BTS7960 #4 LPWM |
| PB6 | EXTI6 | Encoder #1 kênh A |
| PB7 | EXTI7 | Encoder #1 kênh B |
| PB8 | EXTI8 | Encoder #2 kênh A |
| PB9 | EXTI9 | Encoder #2 kênh B |
| PB10 | EXTI10 | Encoder #3 kênh A |
| PB11 | EXTI11 | Encoder #3 kênh B |
| PB12 | EXTI12 | Encoder #4 kênh A |
| PB13 | EXTI13 | Encoder #4 kênh B |
| PC13 | LED onboard | Active low |
| 3V3 | Nguồn logic | Cảm biến/level shifter 3.3 V |
| GND | Ground | GND chung toàn hệ thống |
| 5V | Nguồn vào Blue Pill | Buck 5 V |

Thứ tự bánh: **#1 = trước-trái (FL), #2 = trước-phải (FR), #3 = sau-trái (RL), #4 = sau-phải (RR)**.

## 2. Timer và tần số PWM

- HCLK = 72 MHz.
- TIM1 và TIM3 đều nhận clock timer 72 MHz.
- Prescaler = 0, ARR = 3599 → `72e6 / 3600 = 20 kHz`.
- 8 kênh PWM độc lập:
  - TIM1 CH1–CH4 → RPWM 4 bánh.
  - TIM3 CH1–CH4 → LPWM 4 bánh.

## 3. Đấu BTS7960 (mỗi động cơ một module)

| BTS7960 | Nối |
|---|---|
| VCC | 5 V logic |
| GND | GND chung |
| VM | 12 V từ buck động cơ |
| GND (power) | GND pin |
| RPWM | Chân RPWM tương ứng STM32 |
| LPWM | Chân LPWM tương ứng STM32 |
| R_EN | 5 V (hoặc điều khiển enable nếu có) |
| L_EN | 5 V |
| M+ / M- | Hai cực động cơ |

Lưu ý:

- Một số module BTS7960 có sẵn level shifter/regulator 5 V; kiểm tra mức logic đầu vào. Nếu module yêu cầu 5 V logic, dùng level shifter 3.3 V → 5 V cho RPWM/LPWM.
- **Không** nối thẳng 12 V vào chân logic.
- Đặt tụ 1000 µF gần mỗi module hoặc gần thanh phân phối 12 V để giảm sụt áp khi đổi chiều.
- Thêm cầu chì tổng (ví dụ 15 A) và công tắc dừng khẩn cấp cắt nguồn VM.

## 4. Encoder Hall

Mỗi động cơ JGB37-520 có 6 dây thường gặp:

| Dây | Chức năng |
|---|---|
| M1 / M2 | Động cơ |
| VCC | 5 V (theo datasheet động cơ) |
| GND | GND |
| A | Xung kênh A |
| B | Xung kênh B |

Đấu A/B qua level shifter hoặc cầu chia áp về 3.3 V trước khi vào STM32.
Ví dụ cầu chia: 10 kΩ từ tín hiệu 5 V xuống chân STM32, 20 kΩ từ chân STM32 xuống GND → 3.33 V.
Với tần số xung thấp (< 10 kHz mỗi kênh), cầu chia thụ động đủ dùng; nếu cần chống nhiễu, dùng 74LVC245 hoặc optocoupler tốc độ cao.

Nếu động cơ quay nhưng RPM hiển thị âm, đặt `ENCx_INVERT 1` trong `firmware/include/board.h`.

## 5. Nguồn

```
Pin 4S Li-ion 14.8 V (16.8 V khi đầy)
   │
   ├── Cầu chì + công tắc E-STOP
   │
   ├── Buck 12 V / ≥10 A ──► VM 4 × BTS7960
   │
   ├── Buck 5 V / ≥3 A ───► Blue Pill 5V, logic BTS7960, encoder VCC
   │
   └── Buck 5 V / ≥4 A ───► Jetson Nano (dùng buck riêng)
```

- Jetson Nano không cấp nguồn cho động cơ.
- Nối chung GND giữa tất cả các khối.
- Đo điện áp thực trước khi cắm Jetson/STM32.
- Thêm tụ bulk và tụ gốm tại đầu vào mỗi buck.

## 6. UART với Jetson Nano

Jetson Nano header J41:

| Jetson | STM32 |
|---|---|
| Pin 8 (UART1_TX, 3.3 V) | PA3 (USART2_RX) |
| Pin 10 (UART1_RX, 3.3 V) | PA2 (USART2_TX) |
| Pin 6 (GND) | GND |

Cấu hình thiết bị trên Jetson thường là `/dev/ttyTHS1`. Kiểm tra bằng:

```bash
ls -l /dev/ttyTHS*
python3 -m serial.tools.miniterm /dev/ttyTHS1 115200
```

Nếu dùng laptop, dùng USB-UART CP2102/CH340 ở 3.3 V và `/dev/ttyUSB0`.

## 7. Những chân nên tránh

- PA13/PA14: SWDIO/SWCLK, giữ cho nạp/debug.
- PA15, PB3, PB4: JTAG mặc định; nếu cần dùng phải remap SWJ.
- PA0/PA1/PA4/PA5/PA12, PB5, PB14/PB15: đang để trống, có thể dùng cho nút nhấn, relay enable, IMU trong tương lai.
