# Quy trình hiệu chuẩn trên robot thật

Thông số trong repo là điểm khởi đầu. Robot chỉ chạy tốt sau khi đo các đại lượng dưới đây.

## 0. Chuẩn bị an toàn

1. Kê bánh khỏi mặt bàn hoặc đặt robot trong khu vực trống, không có người.
2. Có công tắc dừng khẩn cấp cắt nguồn 12 V động cơ; nếu đấu thêm E-STOP về PB0, lưu ý firmware sẽ **chốt dừng tới khi reset nguồn**.
3. Kiểm tra chiều quay bánh trước khi cho robot chạy trên mặt đất.
4. Mở GUI:

```bash
cd host
source .venv/bin/activate
python3 main.py --port /dev/ttyUSB0
```

Tab **RPM trực tiếp** có các ô:
- 4 RPM đặt trực tiếp.
- `PWM thủ công: index,duty` để áp duty vòng hở cho một bánh.
- `PID online: index,kp,ki,kd`.
- Nút **Thoát PWM** để trở về chế độ vận tốc.

## 1. Kiểm tra chiều encoder và thứ tự bánh

Với bánh đã kê:

1. Gửi `PWM thủ công` bánh 1, duty `0.10`.
2. Xem RPM thực bánh 1 trên GUI.
3. Nếu RPM âm trong khi bánh quay theo chiều tiến, đặt `ENC1_INVERT 1` trong `firmware/include/board.h`.
4. Lặp lại cho bánh 2, 3, 4.
5. Kiểm tra đúng bánh nào là FL/FR/RL/RR. Nếu sai, đổi dây motor/encoder tương ứng, không đổi công thức động học.

> **Lưu ý bánh 4 (RR):** firmware hiện chỉ ngắt cạnh A của encoder 4 (PB8) và đọc B thụ động (PB9), nên đếm **x2** thay vì x4. RPM telemetry của bánh 4 sẽ thấp khoảng một nửa so với thực tế. Trước khi hiệu chuẩn odometry, cần sửa firmware (thêm EXTI cho PB9 hoặc dùng timer encoder) hoặc thêm hệ số bù/nhân đôi delta riêng cho bánh 4.

Kiểm tra nhanh bằng lệnh:

```
M,1,0.10
M,1,-0.10
STOP
```

## 2. Đo dead-zone

Dead-zone là duty nhỏ nhất để bánh bắt đầu quay đều, đo riêng chiều tiến và lùi.

### 2.1 Phương pháp tăng dần

Với từng bánh:

1. Gửi `M,<i>,0.04`, đợi 0.5 s.
2. Nếu bánh chưa quay, tăng thêm `0.01`.
3. Ghi lại duty đầu tiên bánh quay liên tục: `D_fwd`.
4. Làm lại với duty âm: `M,<i>,-0.04` … ghi `D_rev`.
5. Lấy `D_i = (D_fwd + D_rev) / 2` hoặc giá trị lớn hơn nếu ma sát hai chiều lệch nhiều.

Ví dụ kết quả:

| Bánh | D_fwd | D_rev | D dùng |
|---|---|---|---|
| 1 | 0.07 | 0.09 | 0.08 |
| 2 | 0.08 | 0.10 | 0.09 |
| 3 | 0.07 | 0.08 | 0.08 |
| 4 | 0.09 | 0.11 | 0.10 |

Gửi online:

```
D,1,0.08
D,2,0.09
D,3,0.08
D,4,0.10
```

Hoặc sửa `DEADZONE_DEFAULT` và khởi tạo riêng từng bánh trong `control.c` nếu muốn lưu cố định.

Giới hạn: firmware hiện dùng một dead-zone đối xứng cho mỗi bánh. Nếu `D_fwd` và `D_rev` lệch lớn, dùng giá trị lớn hơn để tránh kẹt, sau đó PID sẽ bù phần dư.

## 3. Đo đặc tính PWM → RPM

Mục đích: biết duty nào cho bao nhiêu RPM, có tải và không tải; chọn `MAX_WHEEL_RPM` và gain PID hợp lý.

1. Kê bánh, đo không tải.
2. Với duty `0.1, 0.2, ..., 1.0`, gửi `M,<i>,<duty>`, đợi 1 s cho ổn định, ghi RPM thực.
3. Lặp lại khi bánh chạm mặt đất hoặc có tải.
4. Lập bảng cho từng bánh.

Ví dụ:

| Duty | RPM không tải | RPM có tải |
|---|---|---|
| 0.10 | 18 | 10 |
| 0.25 | 62 | 48 |
| 0.50 | 145 | 128 |
| 0.75 | 228 | 205 |
| 1.00 | 330 | 300 |

Dùng bảng để:
- Đặt `MAX_WHEEL_RPM` gần tốc độ tối đa thực tế (ví dụ 300 thay vì 333).
- Chọn `Kp` sao cho sai lệch lớn không làm PID bão hòa quá lâu.
- Phát hiện bánh yếu/ma sát lớn.

## 4. Hiệu chỉnh PID

Mục tiêu: thời gian xác lập < 0.3 s, overshoot < 10% với bước nhảy 100–150 RPM.

### 4.1 Chuẩn bị

1. Nạp dead-zone đã đo.
2. Đặt `Ki = 0`, `Kd = 0`:

```
P,1,0.002,0,0
P,2,0.002,0,0
P,3,0.002,0,0
P,4,0.002,0,0
```

3. Kê bánh hoặc đặt robot an toàn.

### 4.2 Tăng Kp

1. Gửi bước 100 RPM cho một bánh: `R,100,0,0,0` (hoặc dùng GUI).
2. Quan sát telemetry/GUI. Tăng `Kp` dần `0.002 → 0.003 → 0.004 → ...`.
3. Dừng khi đáp ứng nhanh nhưng overshoot còn dưới 10%.
4. Nếu dao động, giảm `Kp` hoặc thêm `Kd`.

### 4.3 Thêm Ki

1. Tăng `Ki` từ `0.005` đến `0.02` để khử sai số xác lập.
2. Nếu tích phân gây vọt lố, giảm `Ki` hoặc giảm `PID_I_MAX`.
3. Anti-windup đã có trong firmware; kiểm tra bánh bị kẹt không tích lũy vô hạn.

### 4.4 Thêm Kd

1. Tăng `Kd` rất nhỏ (`0.0001`, `0.0002`, ...).
2. Kd tính trên tốc độ đo và đã lọc alpha 0.30, nên tăng từ từ.
3. Nếu RPM giật do nhiễu encoder, giảm `Kd` hoặc giảm `PID_D_FILTER_ALPHA`.

### 4.5 Ghi kết quả

Khi đạt yêu cầu, cập nhật mặc định trong `firmware/src/control.c` hoặc `robot_config.h`.
Nếu mỗi bánh khác nhau, sửa vòng khởi tạo PID trong `control.c` để dùng gain riêng.

## 5. Hiệu chuẩn odometry

### 5.1 Bán kính bánh hiệu dụng

1. Đặt `--wheel-radius 0.04` ban đầu.
2. Đánh dấu điểm xuất phát, chạy thẳng chậm 2 m trên mặt phẳng.
3. Đọc quãng đường odometry trên GUI (`quãng đường = ... m`).
4. Đo quãng đường thực bằng thước: `D_actual`.
5. Tính:

```
R_eff = R_config · D_actual / D_odom
```

Ví dụ odometry báo 2.10 m nhưng thực tế 2.00 m:

```
R_eff = 0.04 · 2.00 / 2.10 = 0.0381 m
```

6. Chạy lại host với `--wheel-radius 0.0381`.
7. Cập nhật `WHEEL_RADIUS_M` trong `firmware/include/robot_config.h` nếu host gửi lệnh `V,...` (vì firmware cũng tính động học nghịch). Nếu host gửi lệnh `R,...` trực tiếp thì chỉ cần đúng bán kính trên host.

### 5.2 Khoảng cách trục và đi ngang

- `--wheelbase`: khoảng cách tâm bánh trước–sau.
- `--track`: khoảng cách tâm hai bánh trái–phải.
- Nếu robot đi ngang ngược chiều: thêm `--invert-vy` ở host và đặt `VY_INVERTED 1` trong firmware (phải đồng bộ).
- Nếu robot xoay ngược chiều: thêm `--invert-omega` ở host và đặt `OMEGA_INVERTED 1` trong firmware (phải đồng bộ).
- Nếu quay tại chỗ bị lệch góc, hiệu chỉnh `wheelbase`/`track` hoặc đo trực tiếp `YAW_ARM_M`.

### 5.3 Kiểm tra 360°

1. Reset odometry.
2. Cho robot quay tại chỗ 360° (ω không đổi trong thời gian `2π/ω`).
3. Đọc θ trên GUI. Sai số chấp nhận tùy ứng dụng; nếu lệch nhiều, hiệu chỉnh `YAW_ARM_M` theo tỷ lệ.

## 6. Kiểm tra timeout an toàn

1. Kê bánh hoặc đặt robot an toàn.
2. Cho robot chạy bằng GUI.
3. Rút dây UART hoặc tắt tiến trình host.
4. Robot phải dừng trong vòng 500 ms.
5. Cắm lại, gửi lệnh mới, robot chạy lại bình thường.

Nếu không dừng, kiểm tra:
- Host có thực sự gửi lệnh 20 Hz không.
- `ROBOT_UART_TIMEOUT_MS` trong firmware.
- Dây TX/RX và GND.

## 7. Checklist trước khi chạy tự động

- [ ] Đúng chiều 4 encoder.
- [ ] Đúng thứ tự FL/FR/RL/RR.
- [ ] Dead-zone từng bánh đã đo.
- [ ] PID từng bánh đạt settling < 0.3 s, overshoot < 10%.
- [ ] `Reff` đã hiệu chuẩn.
- [ ] Đi ngang đúng chiều.
- [ ] Xoay đúng chiều.
- [ ] Timeout 500 ms hoạt động.
- [ ] E-STOP vật lý hoạt động (cắt 12 V và/hoặc ngõ PB0 chốt dừng).
- [ ] Driver tương thích firmware PWM+DIR (hoặc đã đổi firmware sang RPWM/LPWM nếu dùng BTS7960).
- [ ] Encoder bánh 4 đã xử lý vấn đề đếm x2 (sửa firmware hoặc CPR riêng).
- [ ] Vùng chạy không có vật cản ngoài kịch bản test.
