# Sơ đồ chân và đấu dây

Thiết kế dây dưới đây được tính lại theo **BOM hiện tại** ([bom.md](bom.md)):

- Pin Li-ion 5S 4 Ah (18 V danh định, 21 V khi đầy) có BMS.
- Buck 20 A: 21 V → 12 V cho 4 × driver cầu H.
- LM2596: 21 V → 5 V / 3 A cho Blue Pill, logic driver, encoder.
- Buck 3.3 V: 5 V → 3.3 V / > 500 mA cho ESP8266 (hoặc cấp NodeMCU qua Vin 5 V).
- 4 × JGB37-520 12 V 333 RPM + encoder Hall; 4 × driver cầu H; STM32F103C8T6.

> Các giá trị dòng của động cơ là **giả thiết tiêu biểu**, phải đối chiếu datasheet lô hàng thực tế. Nếu sai khác nhiều, tính lại theo mục 2.

## 1. Sơ đồ khối nguồn

```
Pin 5S 18 V (21 V đầy) 4 Ah + BMS
  P+ ──► Cầu chì 15 A ──► E-STOP ──► Bus pin
  P- ───────────────────────────────► Điểm sao GND
                                         │
        ┌────────────────────────────────┼─────────────────────────────┐
        │                                │                             │
   Buck 20 A 21V→12V              LM2596 21V→5V                 Buck 3.3V
        │                                │                        (5V→3.3V)
   Bus 12 V                         Bus 5 V                          │
        │                          ┌─────┼──────────┐           Bus 3.3 V
        │                          │     │          │                │
   4 × driver VM            Blue Pill 5V  Driver VCC Encoder VCC  NodeMCU V3
        │                          │         │          │             │
   4 × động cơ JGB37-520      STM32 3.3V logic  R_EN/L_EN       (TX/RX 3.3V)
        │
   Encoder A/B ──► cầu chia 10k/20k ──► PA0/PA1, PA6/PA7, PB6/PB7, PB8/PB9
```

Nguyên tắc:

- Cầu chì và E-STOP nằm **ngay sau pin**, trước mọi buck.
- Buck 12 V chỉ nuôi động cơ; buck 5 V nuôi logic; buck 3.3 V chỉ nuôi ESP.
- Tất cả GND nối về **một điểm sao** tại cực âm pin/BMS.

## 2. Tính toán phụ tải và chọn nguồn

### 2.1 Giả thiết động cơ JGB37-520 12 V 333 RPM

| Thông số | Giá trị dùng tính toán |
|---|---|
| Điện áp định mức | 12 V |
| Dòng không tải | 0,18 A |
| Dòng định mức | 0,60 A |
| Dòng kẹt (stall) | 3,2 A |
| 4 động cơ – định mức | 2,4 A |
| 4 động cơ – stall | 12,8 A |
| Công suất 4 động cơ – định mức | 28,8 W |
| Công suất 4 động cơ – stall | 153,6 W |

### 2.2 Dòng từng rail

| Rail | Tải | Dòng trung bình | Dòng đỉnh |
|---|---|---|---|
| 12 V | 4 × JGB37-520 | 2,4 A | 12,8 A (stall) |
| 5 V | Blue Pill | 0,05 A | 0,05 A |
| 5 V | 4 × logic driver cầu H | 0,06 A | 0,06 A |
| 5 V | 4 × encoder Hall | 0,08 A | 0,08 A |
| 5 V | Đầu vào buck 3.3 V | 0,27 A | 0,39 A |
| **5 V** | **Tổng** | **0,46 A** | **0,58 A** |
| 3,3 V | ESP8266 / NodeMCU V3 | 0,08 A | 0,35 A (thiết kế 0,5 A) |

### 2.3 Dòng pin và thời gian chạy

Dùng hiệu suất thực tế: buck 12 V ≈ 0,90; LM2596 ≈ 0,78; buck 3.3 V ≈ 0,85.

```
Chế độ định mức:
P_pin = 28,8/0,90 + (5 × 0,46)/0,78 = 32,0 + 2,95 ≈ 35,0 W
I_pin = 35,0 / 18,5 ≈ 1,89 A

Chế độ stall:
P_pin = 153,6/0,90 + 2,95 ≈ 173,6 W
I_pin = 173,6 / 18,5 ≈ 9,4 A
```

- BMS và cầu chì phải chịu **≥ 10 A liên tục ngắn hạn**, tốt nhất ≥ 20 A đỉnh.
- Thời gian chạy lý thuyết: `4 Ah × 0,8 / 1,89 ≈ 1,7 h`; thực tế 1,2–1,5 h do tải thay đổi.
- Dòng khởi động có thể vượt 9,4 A trong vài trăm ms; chọn cầu chì **slow-blow**.

### 2.4 Kiểm tra công suất buck

| Buck | Dòng ra cần | Định mức | Hệ số dư |
|---|---|---|---|
| 21 V → 12 V | 12,8 A (stall), 2,4 A (định mức) | 20 A | 1,56× stall |
| 21 V → 5 V | 0,58 A | 3 A | 5,2× |
| 5 V → 3,3 V | 0,5 A | > 0,5 A | 1,0× (nên chọn ≥ 1 A) |

Lưu ý:

- Buck 12 V 20 A là đủ cho stall ngắn hạn; không chạy stall liên tục.
- LM2596 3 A chỉ đạt 3 A khi tản nhiệt tốt; tải thực 0,58 A nên không cần heatsink lớn.
- Buck 3.3 V loại "> 500 mA" đang sát đỉnh ESP; nếu mua mới nên chọn **≥ 1 A**.

## 3. Chọn dây và cầu chì

### 3.1 Tiết diện dây

Điện trở 14 AWG ≈ **8,286 mΩ/m**; ampacity chassis ≈ **15 A**.
Sụt áp: `ΔV = I × 2L × R_per_m` (L là chiều dài một chiều).

| Nhánh | Dòng lớn nhất | Dây | Ghi chú |
|---|---|---|---|
| Pin → cầu chì → bus | 9,4 A | 14 AWG (12 AWG nếu > 0,5 m) | đỏ (+), đen (−) |
| Bus 12 V → mỗi driver | 3,2 A/nhánh, 12,8 A tổng | 14 AWG bus, 14–16 AWG nhánh | giữ nhánh < 0,5 m |
| 5 V | 0,58 A | 20–22 AWG | |
| 3,3 V | 0,5 A | 22–24 AWG | |
| Encoder A/B | < 5 mA | 24–26 AWG | nên xoắn đôi |
| PWM, UART | < 1 mA | 24–26 AWG (jumper) | |

Ví dụ sụt áp: bus 12 V dài 0,5 m, dòng 12,8 A:

```
ΔV = 12,8 × 2 × 0,5 × 0,008286 ≈ 0,106 V  (≈ 0,9 %)
```

Giữ tổng chiều dài nhánh 12 V **< 1 m** để sụt áp < 2 %.

### 3.2 Cầu chì

| Vị trí | Định mức | Loại |
|---|---|---|
| Tổng, ngay sau pin | 15 A | ATO blade slow-blow |
| Mỗi động cơ (tùy chọn) | 5 A | slow-blow |
| 5 V (tùy chọn) | 1 A | |
| 3,3 V (tùy chọn) | 1 A | |

Kiểm tra: 15 A > 9,4 A đỉnh và ≤ ampacity 14 AWG (15 A); dòng định mức chỉ 1,9 A nên an toàn.

## 4. Đấu dây chi tiết

### 4.1 Pin → phân phối

| Từ | Tới | Dây |
|---|---|---|
| Pin P+ | Cầu chì 15 A | 14 AWG đỏ |
| Cầu chì | E-STOP | 14 AWG đỏ |
| E-STOP | Bus + (buck 12 V, LM2596) | 14 AWG đỏ |
| Pin P- | Điểm sao GND | 14 AWG đen |
| Bus GND | GND các buck, BTS, Blue Pill, ESP | 14–22 AWG đen |

- E-STOP phải có định mức **DC ≥ 20 A** (tiếp điểm DC dễ hàn dính nếu dùng công tắc AC).
- Đặt cầu chì sát cực pin nhất có thể.

### 4.2 Bus 12 V → driver cầu H → động cơ

Firmware hiện tại điều khiển mỗi bánh bằng **1 kênh PWM + 1 chân DIR**.

| Driver | Nối |
|---|---|
| VM / V+ | Bus 12 V |
| GND (power) | Power GND (điểm sao) |
| VCC (logic) | 5 V logic (nếu module yêu cầu) |
| GND (logic) | Logic GND |
| EN (nếu có) | 5 V (qua 10 kΩ hoặc nối thẳng) |
| PWM | PA8 / PA9 / PA10 / PA11 |
| DIR | PB12 / PB13 / PB14 / PB15 |
| M+ / M− | Hai cực động cơ |

Bảng ghép bánh và encoder:

| Bánh | PWM | DIR | Encoder A | Encoder B |
|---|---|---|---|---|
| 1 – FL (trước-trái) | PA8 (TIM1_CH1) | PB12 | PA0 (TIM2_CH1) | PA1 (TIM2_CH2) |
| 2 – FR (trước-phải) | PA9 (TIM1_CH2) | PB13 | PA6 (TIM3_CH1) | PA7 (TIM3_CH2) |
| 3 – RL (sau-trái) | PA10 (TIM1_CH3) | PB14 | PB6 (TIM4_CH1) | PB7 (TIM4_CH2) |
| 4 – RR (sau-phải) | PA11 (TIM1_CH4) | PB15 | PB8 (EXTI8) | PB9 (GPIO input) |

> **Cảnh báo tương thích BTS7960:** module BTS7960 dùng **RPWM + LPWM** (2 kênh PWM mỗi bánh), không phải PWM + DIR. Nếu đấu DIR vào LPWM, khi lùi cả RPWM và LPWM cùng mức cao sẽ là phanh, không đảo chiều. Chỉ dùng sơ đồ trên với driver có ngõ vào PWM + DIR. Với BTS7960, cần đổi firmware sang 8 PWM:
>
> - RPWM bánh 1–4: PA8, PA9, PA10, PA11 (TIM1_CH1–CH4)
> - LPWM bánh 1–4: PA6, PA7, PB0, PB1 (TIM3_CH1–CH4)
>
> nhưng khi đó TIM3 không còn dùng cho encoder bánh 2 và PB0 đang là E-STOP phải chuyển sang chân khác.

Lưu ý mức logic:

- Nếu module driver dùng buffer **74HC244** ở 5 V, mức cao 3,3 V có thể không đạt VIH ⇒ dùng **74HCT244** hoặc **TXS0108E** (8 kênh, 3,3 V → 5 V) cho 4 PWM + 4 DIR.
- Nếu đầu vào driver (VIH ≈ 2 V) nhận trực tiếp 3,3 V thì không cần level shifter; kiểm tra datasheet/module thực tế.
- **Không** nối 12 V vào VCC/PWM/DIR.
- Đặt tụ **1000 µF/25 V** gần thanh phân phối 12 V hoặc 470 µF mỗi module để giảm sụt áp khi đảo chiều.

### 4.3 Bus 5 V

| Tải | Nối |
|---|---|
| Blue Pill | Chân 5V và GND |
| 4 × driver VCC (logic) | 5 V (nếu module yêu cầu) |
| 4 × encoder VCC | 5 V |
| Buck 3.3 V input | 5 V |

- Dùng dây 20–22 AWG, nối hình sao từ bus 5 V, tránh daisy-chain dài.
- Đặt **470 µF/16 V + 100 nF** tại đầu vào LM2596 và đầu ra 5 V.

### 4.4 Bus 3.3 V → ESP8266 (NodeMCU V3)

Firmware bridge hiện tại chạy trên **NodeMCU V3** (`env:nodemcuv2`), dùng UART1:

| NodeMCU V3 | Nối |
|---|---|
| Vin (5 V) | Bus 5 V (khuyến nghị, qua regulator onboard) |
| 3V3 | Chỉ dùng khi đã ngắt USB; không cấp đồng thời Vin và 3V3 |
| GND | GND chung |
| GPIO13 (RX) | PA2 (USART2_TX của STM32) |
| GPIO15 (TX) | PA3 (USART2_RX của STM32) |
| EN / CH_PD | 3,3 V (module đã kéo sẵn) |
| GPIO0 | 3,3 V khi chạy bình thường |

- NodeMCU V3 có thể hút ~300–500 mA khi phát WiFi; dùng buck 3,3 V ≥ 1 A nếu không cấp qua Vin.
- Đặt **470 µF/10 V + 100 nF** sát chân nguồn của module để chịu đỉnh dòng WiFi.
- PA2/PA3 của STM32 là 3,3 V nên nối trực tiếp TX↔RX (chéo).
- **ESP-01S không dùng được với sketch hiện tại** vì ESP-01S không có GPIO13/GPIO15. Nếu vẫn dùng ESP-01S, phải sửa `esp8266/src/main.cpp` sang UART0 (GPIO1/GPIO3) và nạp qua USB-TTL 3,3 V.

### 4.5 Encoder Hall → STM32

Mỗi JGB37-520 có 6 dây: `M1`, `M2`, `VCC`, `GND`, `A`, `B`.

Cầu chia áp cho A/B (5 V → 3,3 V):

```
Encoder A/B ──[ 10 kΩ ]──┬──► chân STM32 (xem bảng)
                         │
                      [ 20 kΩ ]
                         │
                        GND
```

```
Vout = 5 × 20 / (10 + 20) = 3,33 V
Dòng qua cầu chia ≈ 5 / 30 kΩ ≈ 0,167 mA
```

- Tần số xung mỗi kênh: `333/60 × 330 ≈ 1,83 kHz` (chu kỳ ≈ 546 µs).
- Nếu cần lọc nhiễu, chỉ dùng tụ **≤ 100 pF** (với 6,67 kΩ cho fc ≈ 240 kHz). **Không dùng 100 nF** vì sẽ lọc mất xung.
- Dùng cặp dây xoắn A/B, tránh song song sát dây động cơ.
- Nếu encoder là open-collector, bật pull-up nội trong firmware (đã bật `GPIO_PULLUP`) hoặc thêm 10 kΩ lên 3,3 V sau cầu chia.
- Nếu RPM hiển thị âm khi bánh tiến: đặt `ENCx_INVERT 1` trong `firmware/include/board.h`.
- Bánh 1–3 dùng encoder mode phần cứng TIM2/TIM3/TIM4 nên đếm x4. Bánh 4 (RR) chỉ có EXTI trên kênh A (PB8), kênh B (PB9) đọc thụ động ⇒ **thực tế đếm x2**, RPM báo thấp khoảng một nửa. Cần sửa firmware (thêm EXTI cho PB9 hoặc dùng timer encoder) hoặc thêm hệ số bù riêng cho bánh 4 trước khi dùng odometry.

### 4.6 ST-Link V2

| ST-Link | Blue Pill |
|---|---|
| 3,3 V | 3,3 V (chỉ tham chiếu; hoặc cấp nguồn khi nạp với động cơ OFF) |
| GND | GND |
| SWDIO | PA13 |
| SWCLK | PA14 |
| 5 V | **Không nối** |

- Khi nạp firmware, **ngắt nguồn 12 V động cơ**.
- Không nối 5 V của ST-Link vào Blue Pill khi Blue Pill đã được cấp 5 V từ LM2596.
- Tránh để ST-Link 3,3 V đấu song song với regulator onboard khi hệ thống đang chạy.

### 4.7 USB-UART có dây (thay WiFi)

| USB-UART (3,3 V) | STM32 |
|---|---|
| TX | PA3 (USART2_RX) |
| RX | PA2 (USART2_TX) |
| GND | GND |
| 3,3 V / 5 V | **Không nối** (chỉ dùng TX/RX/GND) |

Dùng CP2102/CH340 ở mức logic 3,3 V. Không nối 5 V TTL vào PA2/PA3.

### 4.8 Bảng chân STM32F103C8T6

| Chân | Chức năng | Nối tới |
|---|---|---|
| PA0 | TIM2_CH1 | Encoder #1 kênh A (TIM2 encoder) |
| PA1 | TIM2_CH2 | Encoder #1 kênh B (TIM2 encoder) |
| PA2 | USART2_TX | RX của ESP8266 hoặc USB-UART (3,3 V) |
| PA3 | USART2_RX | TX của ESP8266 hoặc USB-UART (3,3 V) |
| PA6 | TIM3_CH1 | Encoder #2 kênh A (TIM3 encoder) |
| PA7 | TIM3_CH2 | Encoder #2 kênh B (TIM3 encoder) |
| PA8 | TIM1_CH1 | PWM driver #1 |
| PA9 | TIM1_CH2 | PWM driver #2 |
| PA10 | TIM1_CH3 | PWM driver #3 |
| PA11 | TIM1_CH4 | PWM driver #4 |
| PB0 | EXTI0 | E-STOP (cạnh xuống, pull-up) |
| PB6 | TIM4_CH1 | Encoder #3 kênh A (TIM4 encoder) |
| PB7 | TIM4_CH2 | Encoder #3 kênh B (TIM4 encoder) |
| PB8 | EXTI8 | Encoder #4 kênh A (giải mã mềm) |
| PB9 | GPIO input | Encoder #4 kênh B (đọc thụ động) |
| PB12 | GPIO output | DIR driver #1 |
| PB13 | GPIO output | DIR driver #2 |
| PB14 | GPIO output | DIR driver #3 |
| PB15 | GPIO output | DIR driver #4 |
| PC13 | LED onboard | Active low |
| PA13 | SWDIO | ST-Link |
| PA14 | SWCLK | ST-Link |
| 3V3 | Nguồn logic | Cầu chia áp / tham chiếu 3,3 V |
| 5V | Nguồn vào Blue Pill | Bus 5 V |
| GND | Ground | Điểm sao GND |

Thứ tự bánh: **#1 = FL, #2 = FR, #3 = RL, #4 = RR**. Chân PB1, PB10, PB11 không dùng trong firmware hiện tại.

### 4.9 Timer và tần số PWM

- HCLK = 72 MHz; TIM1, TIM2, TIM3, TIM4 đều nhận clock 72 MHz.
- PWM: Prescaler = 0, ARR = 3599 ⇒ `72 MHz / 3600 = 20 kHz`.
- TIM1 CH1–CH4 (PA8–PA11) → PWM bánh 1–4.
- TIM2/TIM3/TIM4 ở encoder mode TI12 → encoder bánh 1–3.
- TIM3 **không còn** dùng để phát LPWM; xung LPWM của thiết kế cũ không còn trong firmware hiện tại.
- USART2 (PA2/PA3) @ 115200 8N1.

### 4.10 E-STOP → PB0

| Tín hiệu | Nối |
|---|---|
| Tiếp điểm E-STOP | PB0 (EXTI0) và GND |
| Chiều kích hoạt | Cạnh xuống (đóng về GND) |
| Pull | Pull-up nội trong STM32 |

- Khi E-STOP mở/đóng về GND, firmware vào `control_emergency_stop()`: dừng PWM ngay và chốt cờ dừng.
- Cờ dừng chỉ được xóa khi reset nguồn/vi điều khiển; không có lệnh UART để chạy lại sau E-STOP.
- Nên dùng E-STOP **hai lớp**: tiếp điểm công suất cắt 12 V động cơ + tiếp điểm tín hiệu về PB0.
- Không đưa điện áp 12 V/5 V trực tiếp vào PB0; chỉ dùng tiếp điểm khô nối GND.

## 5. Kế hoạch connector

| Ký hiệu | Chức năng | Loại đề xuất |
|---|---|---|
| J1 | Pin vào | XT60 (đực trên robot) |
| J2 | Bus 12 V | Terminal bắt vít 2P hoặc XT60 |
| J3–J6 | Động cơ M+/M− | Terminal bắt vít 2P trên driver cầu H |
| J7 | Bus 5 V | Terminal 2P |
| J8 | Bus 3,3 V | Terminal 2P |
| J9 | ST-Link | Header 1×4 2,54 mm |
| J10 | NodeMCU V3 | Header 2×15 2,54 mm |
| J11–J14 | Động cơ + encoder | JST-XH 6P hoặc Dupont 6P |
| J15 | USB-UART | Header 1×4 (TX, RX, GND) |
| J16 | Blue Pill 5V/GND | Terminal 2P |

- Dùng **cọc trụ đồng 40 mm** (16 cái trong BOM) để gá Blue Pill, 4 module driver, các buck và ESP lên khung mica; tránh chạm mass giữa các board.
- Xiết terminal bằng ferrule/đầu cos trước khi hàn dây 14 AWG.

## 6. Quy ước màu dây

| Nhóm | Màu |
|---|---|
| Pin + / bus 12 V | Đỏ (14 AWG) |
| GND | Đen (14–22 AWG) |
| Bus 5 V | Đỏ (20–22 AWG) |
| Bus 3,3 V | Cam (22–24 AWG) |
| Encoder A | Xanh lá |
| Encoder B | Xanh dương |
| PWM | Trắng / xám |
| UART TX | Xanh lá |
| UART RX | Xanh dương |

Luôn dán nhãn hai đầu dây; không chỉ dựa vào màu.

## 7. Nối đất và chống nhiễu

- Điểm sao GND tại **cực âm pin/BMS**; mọi GND quay về đây.
- Tách **power GND** (pin, buck, driver power, động cơ) và **logic GND** (Blue Pill, ESP, encoder, driver logic); nối hai phần tại đúng một điểm.
- Không cho dòng động cơ chạy qua dây GND logic.
- Dây động cơ xoắn đôi; dây encoder xoắn đôi và đi xa dây động cơ; nếu bắt buộc giao nhau thì vuông góc.
- Nếu cáp encoder dài > 30 cm, dùng cáp có vỏ bọc, nối shield một đầu về GND.
- Đặt tụ gốm 100 nF sát chân VCC/GND của Blue Pill, ESP và mỗi encoder.

## 8. Checklist trước khi cấp nguồn

- [ ] Đo 12 V, 5 V, 3,3 V bằng đồng hồ **trước khi** cắm Blue Pill/ESP.
- [ ] Kiểm tra cực tính pin, XT60, terminal.
- [ ] Đã nối GND chung (pin, buck, BTS, STM32, ESP, encoder).
- [ ] Cầu chì 15 A và E-STOP hoạt động, cắt được VM 12 V.
- [ ] Điện áp ra cầu chia encoder ≤ 3,3 V ở cả hai mức.
- [ ] Không cấp đồng thời Vin 5 V và 3V3 cho NodeMCU.
- [ ] ST-Link không nối 5 V; động cơ OFF khi nạp.
- [ ] Driver đúng loại PWM+DIR (hoặc đã đổi firmware sang RPWM/LPWM nếu dùng BTS7960).
- [ ] E-STOP nối PB0–GND hoạt động, firmware dừng và chốt.
- [ ] Encoder bánh 4 nối đúng PB8/PB9; hiểu rằng firmware chỉ đếm x2.
- [ ] Lần đầu cấp nguồn nên dùng nguồn bench có giới hạn dòng.
- [ ] Kiểm tra chiều quay từng bánh trước khi đặt robot xuống đất.

## 9. Vật tư bổ sung khuyến nghị

Các mục dưới đây **chưa có trong BOM hiện tại** nhưng cần cho hệ thống dây an toàn/ổn định:

| Vật tư | Thông số | SL | Ghi chú |
|---|---|---|---|
| Cầu chì + đế | 15 A ATO slow-blow | 1 | bắt buộc |
| Nút dừng khẩn cấp | DC ≥ 20 A | 1 | bắt buộc |
| Level shifter | 74HCT244 hoặc TXS0108E (8 kênh) | 1 | nếu driver cần logic 5 V cho 4 PWM + 4 DIR |
| Tụ 12 V | 1000 µF/25 V | 1–4 | gần driver cầu H |
| Tụ 5 V | 470 µF/16 V + 100 nF | 1 bộ | đầu vào/ra LM2596 |
| Tụ 3,3 V | 470 µF/10 V + 100 nF | 1 bộ | sát NodeMCU/ESP8266 |
| Điện trở chia áp | 10 kΩ + 20 kΩ | 8 bộ | cho 8 dây encoder |
| Dây 12 AWG | đỏ/đen | 0,5 m | nếu nhánh pin > 0,5 m |
| Cầu chì nhánh | 5 A slow-blow | 4 | tùy chọn, bảo vệ từng động cơ |
| Co nhiệt / đầu cos | phù hợp 14 AWG | 1 bộ | chống chập, đứt sợi |
