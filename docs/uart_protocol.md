# Giao thức UART

## 1. Tham số vật lý

| Thông số | Giá trị |
|---|---|
| UART | USART2 |
| Chân STM32 | PA2 = TX, PA3 = RX |
| Baudrate | 115200 |
| Frame | 8 data, no parity, 1 stop (8N1) |
| Logic | 3,3 V |
| Kết thúc dòng | `\n` (firmware bỏ qua `\r`) |
| Độ dài dòng tối đa | 95 ký tự |
| Chu kỳ lệnh host | 20 Hz |
| Chu kỳ telemetry | 20 ms (50 Hz) |

Nối chéo TX/RX, nối chung GND. Không nối 5 V của Blue Pill với ESP8266 hoặc USB-UART.

Host có thể kết nối theo hai cách:

- **USB-UART có dây:** `/dev/ttyUSB0` hoặc `COMx`, dùng trực tiếp giao thức dưới đây.
- **WiFi qua ESP8266:** NodeMCU V3 làm cầu nối trong suốt TCP ↔ UART. Laptop mở TCP tới ESP và gửi đúng các dòng lệnh; không cần thêm lớp giao thức. Xem [esp8266.md](esp8266.md).

## 2. Host → STM32

### 2.1 Lệnh vận tốc thân

```
V,<vx>,<vy>,<omega>\n
```

- `vx`: m/s, dương là tiến.
- `vy`: m/s, dương là sang trái.
- `omega`: rad/s, dương là quay ngược chiều kim đồng hồ.

Ví dụ:

```
V,0.3000,0.0000,0.0000
V,0.0000,0.2500,0.0000
V,0.0000,0.0000,1.2000
```

Có thể bỏ tiền tố `V,` khi gửi đúng 3 số:

```
0.3,0,0
```

### 2.2 Lệnh RPM trực tiếp

```
R,<rpm1>,<rpm2>,<rpm3>,<rpm4>\n
```

Thứ tự bánh: FL, FR, RL, RR. RPM dương = bánh quay chiều tiến.
Firmware kẹp từng giá trị vào `[-333, +333]`.
Có thể bỏ tiền tố `R,` khi gửi đúng 4 số.

Ví dụ:

```
R,100,100,100,100
-50,50,-50,50
```

### 2.3 Dừng

```
STOP\n
```

Đặt setpoint 0, reset PID, PWM về 0 ngay. Các chu kỳ sau PID giữ 0 RPM; driver để bánh quay tự do (coast).

### 2.4 Ping

```
PING\n
```

Phản hồi: `PONG\n`.

### 2.5 Chỉnh PID online

```
P,<index>,<kp>,<ki>,<kd>\n
```

- `index`: 1..4.
- Hệ số dạng thập phân.

Ví dụ:

```
P,1,0.0035,0.015,0.00015
```

### 2.6 Chỉnh bù dead-zone online

```
D,<index>,<deadzone>\n
```

- `index`: 1..4.
- `deadzone`: 0.0 .. 0.5 (tỷ lệ duty). Firmware kẹp giá trị.

Ví dụ:

```
D,1,0.08
D,2,0.09
```

### 2.7 PWM thủ công để hiệu chuẩn

```
M,<index>,<duty>\n
```

- `index`: 1..4.
- `duty`: -1.0 .. 1.0, dấu quyết định chiều quay.

Lệnh này đưa **một bánh** sang chế độ vòng hở, bỏ qua PID, để đo dead-zone và đặc tính PWM–RPM.
Các bánh còn lại dừng. Host phải gửi lặp lại `M,...` (20 Hz) để duy trì chế độ; gửi `V,...`, `R,...` hoặc `STOP` sẽ thoát chế độ thủ công.
Timeout 500 ms vẫn có hiệu lực.

Ví dụ:

```
M,1,0.10
M,1,-0.08
STOP
```

## 3. STM32 → Host

Telemetry 50 Hz:

```
T,<t_ms>,<a1>,<a2>,<a3>,<a4>,<s1>,<s2>,<s3>,<s4>\n
```

- `t_ms`: `HAL_GetTick()` (ms, uint32).
- `a1..a4`: RPM thực của 4 bánh, **nhân 10**, kiểu số nguyên.
- `s1..s4`: RPM đặt của 4 bánh, **nhân 10**, kiểu số nguyên.

Ví dụ:

```
T,123456,716,716,716,716,-10,20,-30,40
```

Nghĩa là RPM thực `[71.6, 71.6, 71.6, 71.6]`, RPM đặt `[-1.0, 2.0, -3.0, 4.0]`.

Gửi RPM ×10 để tránh printf số thực trên MCU, giảm flash và CPU.

## 4. Timeout an toàn

- Firmware chỉ chạy PID khi đã nhận ít nhất một lệnh hợp lệ.
- Nếu `now - last_valid_rx > 500 ms`, firmware:
  - đặt setpoint 4 bánh = 0,
  - reset PID,
  - đặt cả 8 kênh RPWM/LPWM = 0,
  - tiếp tục gửi telemetry.
- Host gửi lệnh 20 Hz ngay cả khi robot đứng yên (`V,0,0,0`) để duy trì kết nối.
- Sau timeout, cần một lệnh hợp lệ mới để chạy lại.

Các dòng lệnh không hợp lệ không được tính là "alive".

## 4.1 E-STOP phần cứng

- Chân PC0 là ngõ vào E-STOP (EXTI0, cạnh xuống, pull-up nội). Tiếp điểm E-STOP nối PC0–GND.
- Khi kích hoạt, firmware gọi `control_emergency_stop()`: dừng PWM ngay, reset PID, đặt setpoint 0 và bật cờ `emergency_flag`.
- Ở boot: nếu PC0 đang LOW (nút E-STOP đang giữ), `main.c` chốt dừng ngay từ đầu.
- Cờ này **chốt** cho tới khi khởi động lại firmware: mọi lệnh `V`, `R`, `M` sau đó đều bị bỏ qua; `STOP` cũng không xóa cờ.
- Cách duy nhất để chạy lại là reset MCU (nút reset) hoặc cắt nguồn hoàn toàn.
- Telemetry vẫn tiếp tục gửi 50 Hz với RPM thực và setpoint 0.
- Nên dùng E-STOP hai lớp: cắt 12 V động cơ bằng tiếp điểm công suất và đưa tín hiệu về PC0.

## 5. Ví dụ một phiên

```
Host → V,0.2000,0.0000,0.0000
STM32 → T,10020,286,286,286,286,286,286,286,286
STM32 → T,10040,290,289,290,289,286,286,286,286
Host → V,0.2000,0.0000,0.0000
...
Host → V,0.0000,0.0000,0.0000
```

## 6. Ghi chú triển khai

- Không có CRC/checksum. Trong môi trường nhiễu mạnh nên nâng cấp framing nhị phân có header + length + CRC.
- Parser dùng `strtof`, chấp nhận khoảng trắng quanh dấu phẩy.
- Dòng quá dài bị bỏ qua toàn bộ cho đến ký tự xuống dòng tiếp theo.
- `PING` và `STOP` được xử lý trước khi parse số.
- Nếu cần thêm lệnh, giữ nguyên các lệnh cũ để không phá vỡ host.
- Khi dùng WiFi, byte có thể đến theo gói TCP không trùng với ranh giới dòng; host và firmware đều phải đệm và tách theo `\n`. Link TCP trong host đã xử lý việc này.
- WiFi có thể thêm trễ 5–50 ms; khi hiệu chuẩn PID nên dùng USB-UART để giảm jitter.
