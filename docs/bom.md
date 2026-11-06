# Danh mục linh kiện (BOM)

Danh sách linh kiện thực tế cho robot Mecanum 4 bánh.
Trạng thái: ✅ Đã có · 🛒 Cần mua · — Chưa xác định.

| STT | Tên linh kiện | Thông số kỹ thuật chính | SL | Trạng thái |
|---|---|---|---|---|
| 1 | Vi điều khiển STM32F103C8T6 (Blue Pill) | ARM Cortex-M3, 72 MHz, 64 KB Flash, 20 KB SRAM | 1 | 🛒 Cần mua |
| 2 | Mạch nạp ST-Link V2 | Cổng USB, giao tiếp SWD | 1 | 🛒 Cần mua |
| 3 | Module WiFi ESP8266 (ESP-01S) | WiFi 2.4 GHz, giao tiếp UART, logic 3.3 V | 1 | 🛒 Cần mua |
| 4 | Module Driver cầu H BTS7960 | Cầu H công suất, điều khiển qua xung PWM (RPWM/LPWM) | 4 | 🛒 Cần mua |
| 5 | Động cơ DC giảm tốc JGB37-520 | 12 V, 333 RPM, tích hợp Encoder Hall 2 kênh A/B | 4 | ✅ Đã có |
| 6 | Bánh xe Mecanum | Đường kính 80 mm, con lăn góc 45° | 4 | ✅ Đã có |
| 7 | Khung gầm robot | Chất liệu mica, kích thước 200 × 200 mm | 1 | ✅ Đã có |
| 8 | Mạch hạ áp DC-DC (Buck) | Hạ áp 21 V xuống 12 V, chịu tải dòng lớn cho 4 động cơ | 1 | 🛒 Cần mua |
| 9 | Mạch hạ áp DC-DC (Buck) | Hạ áp 21 V xuống 5 V, dòng 3 A | 1 | 🛒 Cần mua |
| 10 | Đế lấy nguồn pin | Loại chân đế 4 cm, tương thích bộ pin thực tế | 1 | 🛒 Cần mua |
| 11 | Pin Li-ion | 5S (18 V danh định, 21 V khi sạc đầy), 4 Ah, tích hợp BMS | 1 | ✅ Đã có |
| 12 | Mạch hạ áp DC-DC (Buck) 3.3 V | Hạ áp 5 V xuống 3.3 V, cấp dòng đỉnh > 500 mA cho ESP8266 | 1 | 🛒 Cần mua |
| 13 | Dây điện Silicon | Loại 14 AWG (màu đỏ và đen), chịu dòng lớn | 2 m | 🛒 Cần mua |
| 14 | Dây Jumper | Đầu đực – cái, dài 20 cm | 20 sợi | ✅ Đã có |
| 15 | Cầu chì & Đế cầu chì | Chọn định mức theo dòng tải thực tế (dự phòng 10 A–20 A) | 1 bộ | 🛒 Cần mua |
| 16 | Nút dừng khẩn cấp | Công tắc tiếp điểm, chịu được dòng đóng cắt của hệ thống | 1 | 🛒 Cần mua |
| 17 | Tụ lọc nguồn | Tụ hóa (470 µF–1000 µF/25 V) & tụ gốm (104 – 0.1 µF) | 1 bộ | 🛒 Cần mua |
| 18 | Terminal & Connector | Đầu nối cắm nguồn, động cơ (XT60 hoặc terminal bắt vít) | 1 bộ | 🛒 Cần mua |

## Sơ đồ phân phối nguồn

```
Pin Li-ion 5S 18 V (21 V khi đầy)
   │
   ├── Cầu chì + E-Stop
   │
   ├── Buck 21 V → 12 V ──► VM 4 × BTS7960 ──► 4 × động cơ JGB37-520
   │
   ├── Buck 21 V → 5 V ───► Blue Pill 5V, logic BTS7960, encoder VCC
   │
   └── Buck 5 V → 3.3 V ──► ESP8266 (ESP-01S), mức logic UART
```

## Ghi chú

- Cầu chì tổng và nút dừng khẩn cấp là **bắt buộc** trước khi chạy robot thật.
- Buck 12 V phải chịu được dòng khởi động lớn của 4 động cơ; dùng dây 14 AWG cho nhánh nguồn động cơ.
- Buck 3.3 V cần cấp dòng đỉnh > 500 mA vì ESP8266 có thể hút dòng cao khi phát WiFi.
- ESP8266 dùng logic 3.3 V; không nối trực tiếp chân TX/RX 5 V vào module.
- Encoder Hall của JGB37-520 thường dùng 5 V: dùng level shifter hoặc cầu chia áp trước khi vào STM32 3.3 V.
- ESP8266 chạy như cầu nối trong suốt TCP ↔ UART; firmware STM32 không cần biết WiFi. Cấu hình: [esp8266.md](esp8266.md).
- Host hỗ trợ cả USB-UART có dây và WiFi TCP (`python3 main.py --tcp 192.168.4.1:8080`).
- Sơ đồ đấu dây chi tiết: [pinout.md](pinout.md).
