# Danh mục linh kiện (BOM)

Danh sách linh kiện thực tế cho robot Mecanum 4 bánh.

| STT | Tên linh kiện | Thông số kỹ thuật chính | SL |
|---|---|---|---|
| 1 | Vi điều khiển STM32F103C8T6 (Blue Pill) | ARM Cortex-M3, 72MHz, 64KB Flash, 20KB SRAM | 1 |
| 2 | Mạch nạp ST-Link V2 | Cổng USB, giao tiếp SWD | 1 |
| 3 | Bo mạch phát triển sử dụng ESP8266EX, WiFi 2.4GHz. | WiFi 2.4GHz, giao tiếp UART, logic 3.3V | 1 |
| 4 | Module Driver cầu H BTS7960 | Cầu H công suất; BTS7960 dùng RPWM/LPWM. Firmware xuất **RPWM (TIM1) + LPWM (TIM3)** tương thích trực tiếp | 4 |
| 5 | Động cơ DC giảm tốc JGB37-520 | 12V, 333 RPM, tích hợp Encoder Hall 2 kênh A/B | 4 |
| 6 | Bánh xe Mecanum | Đường kính 80mm, con lăn góc 45° | 4 |
| 7 | Khung gầm robot | Chất liệu mica, kích thước 200 x 200 mm | 1 |
| 8 | Mạch hạ áp DC-DC (Mạch hạ áp 20 A) | Hạ áp 21V xuống 12V, chịu tải dòng lớn cho 4 động cơ | 1 |
| 9 | Mạch hạ áp DC-DC (Mạch LM2596 có led hiển thị ) | Hạ áp 21V xuống 5V, dòng 3A | 1 |
| 10 | Đế lấy nguồn pin | Loại chân đế 4cm, tương thích bộ pin thực tế | 1 |
| 11 | Pin Li-ion | 5S (18V danh định, 21V khi sạc đầy), 4Ah, tích hợp BMS | 1 |
| 12 | Mạch hạ áp DC-DC (Buck) 3.3V | Hạ áp 5V xuống 3.3V, cấp dòng đỉnh > 500mA cho ESP8266 | 1 |
| 13 | Dây điện Silicon | Loại 14AWG (màu đỏ - 1mét và đen – 1 mét), chịu dòng lớn | 2m |
| 14 | Dây Jumper | Đầu đực - cái, dài 20cm | 20 sợi |
| 15 | Terminal & Connector | Đầu nối cắm nguồn, động cơ (dạng XT60 hoặc Terminal bắt vít) | 1 bộ |
| 16 | Cọc trụ đồng đực cái 40 mm |  | 16 cái |
| 17 | Đế mở rộng chân cắm cho NodeMCU HW-389 |  | 1 |

## Sơ đồ phân phối nguồn

```
Pin Li-ion 5S 18 V (21 V khi đầy) 4 Ah + BMS
   │
   ├── Cầu chì tổng + Công tắc 3 chân (E-STOP)
   │
   ├── Buck 20 A: 21 V → 12 V ──► VM 4 × driver cầu H ──► 4 × JGB37-520
   │
   ├── LM2596: 21 V → 5 V ─────► Blue Pill 5V, logic driver, encoder VCC,
   │                              NodeMCU V3 VIN (dùng regulator onboard)
   │
   ├── Buck 5 V → 3,3 V ───────► rail 3,3 V dự phòng / cấp trực tiếp NodeMCU
   │
   └── MP1584 (dự phòng) ──────► rail điều chỉnh 0.8–20 V, tối đa 3 A
```

## Ghi chú

- Công tắc 3 chân ≥ 20 A dùng làm công tắc nguồn/E-STOP, nhưng **không thay thế cầu chì**. Cầu chì tổng, tụ lọc nguồn, level shifter (nếu driver cần logic 5 V cho 8 kênh RPWM/LPWM) và điện trở chia áp encoder chưa có trong BOM; xem [pinout.md](pinout.md) mục 9.
- Firmware có ngõ E-STOP trên PC0/EXTI0: chốt dừng khi có cạnh xuống, và chốt dừng ngay ở boot nếu nút đang giữ; chỉ reset MCU hoặc cắt nguồn mới chạy lại; nên đấu thêm một tiếp điểm E-STOP về PC0–GND bên cạnh tiếp điểm cắt 12 V.
- Buck 12 V phải chịu được dòng khởi động lớn của 4 động cơ (12,8 A stall); dùng dây 14 AWG cho nhánh nguồn động cơ.
- NodeMCU V3 thay ESP-01S: firmware `esp8266/src/main.cpp` dùng UART1 (GPIO13/RX, GPIO15/TX), 115200 8N1, logic 3,3 V; có USB CH340G để nạp firmware.
- Cấp nguồn NodeMCU V3 qua **VIN 5 V** (regulator onboard) hoặc USB. Nếu cấp 3,3 V trực tiếp vào chân 3V3 thì **ngắt USB** để tránh backfeed; không cấp 5 V vào chân 3V3.
- NodeMCU V3 có thể hút ~300–500 mA khi phát WiFi. Nếu nuôi bằng rail 3,3 V, nên dùng buck ≥ 1 A; mức ≥ 500 mA trong BOM là tối thiểu.
- MP1584 là buck điều chỉnh: **chỉnh đúng điện áp ra trước khi nối tải**, dùng dự phòng cho rail 5 V hoặc 3,3 V; không nối song song hai buck khác điện áp.
- BTS7960 ghi 43 A là dòng đỉnh của chip/module; dòng stall thực mỗi JGB37-520 chỉ ~3,2 A. Vẫn dùng dây 14 AWG cho nhánh 12 V và giữ nhánh ngắn.
- Firmware điều khiển **RPWM/LPWM** cho mỗi bánh (TIM1/TIM3) — tương thích trực tiếp BTS7960; xem [pinout.md](pinout.md) mục 4.2.
- Encoder Hall của JGB37-520 thường dùng 5 V: dùng cầu chia 10 kΩ/20 kΩ hoặc level shifter trước khi vào STM32 3,3 V.
- ESP8266 chạy như cầu nối trong suốt TCP ↔ UART; firmware STM32 không cần biết WiFi. Cấu hình: [esp8266.md](esp8266.md).
- Host hỗ trợ cả USB-UART có dây và WiFi TCP (`python3 main.py --tcp 192.168.4.1:8080`).
- Sơ đồ đấu dây chi tiết: [pinout.md](pinout.md).
