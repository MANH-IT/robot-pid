# AI nhận diện người đi bộ

## 1. Mục tiêu

Phát hiện người trong ảnh camera trước, ước lượng mức nguy hiểm bằng diện tích/vị trí bounding box, rồi:

- **clear:** chạy tốc độ bình thường,
- **slow:** giảm tốc còn khoảng 35%,
- **stop:** dừng robot.

Đây là lớp an toàn mềm, **không thay thế** cảm biến vật lý hoặc nút dừng khẩn cấp.

## 2. Cài đặt

### 2.1 Laptop/PC

```bash
cd host
pip install -r requirements-vision.txt
```

### 2.2 Jetson Nano

Jetson Nano B01 chạy Ubuntu 18.04/20.04 tùy image. Khuyến nghị:

1. Dùng OpenCV có sẵn của JetPack nếu đã hỗ trợ camera/CSI.
2. Cài PyTorch và Ultralytics theo hướng dẫn chính thức của Ultralytics cho Jetson.
3. Nếu không cài được Ultralytics, export model sang ONNX và dùng backend `opencv`.

Kiểm tra:

```bash
python3 -c "import cv2; print(cv2.__version__)"
python3 -c "from ultralytics import YOLO; print('ultralytics ok')"
```

## 3. Chạy demo

### 3.1 Ultralytics (dễ nhất)

```bash
python3 ai_demo.py --port /dev/ttyUSB0 --backend ultralytics --model yolov8n.pt
```

Lần đầu sẽ tự tải `yolov8n.pt`.

### 3.2 OpenCV DNN + ONNX

Export model:

```bash
pip install ultralytics
yolo export model=yolov8n.pt format=onnx imgsz=640
```

Chạy:

```bash
python3 ai_demo.py --port /dev/ttyUSB0 --backend opencv --model yolov8n.onnx
```

Backend OpenCV hỗ trợ cả output YOLOv5 `(1, 25200, 85)` và YOLOv8 `(1, 84, 8400)`.
Chỉ lớp COCO `person` (class 0) được dùng.

### 3.3 Chạy mô phỏng

```bash
python3 ai_demo.py --sim --camera 0 --backend ultralytics
```

Robot mô phỏng vẫn nhận lệnh dừng/giảm tốc, tiện kiểm tra logic mà không cần phần cứng.

## 4. Cách hoạt động

`vision.py` gồm hai phần độc lập:

1. `YoloDetector`: phát hiện người, trả về `Detection(x1, y1, x2, y2, confidence)`.
2. `PedestrianSafety`: chuyển detection thành quyết định an toàn dựa trên:
   - `area_ratio = diện tích_box / diện tích_frame`
   - `bottom_ratio = y2 / chiều_cao_frame`
   - ngưỡng tin cậy tối thiểu.

Quy tắc mặc định:

| Điều kiện | Hành động |
|---|---|
| `area_ratio ≥ 0.18` | stop |
| `bottom_ratio ≥ 0.85` và `area_ratio ≥ 0.03` | stop |
| `area_ratio ≥ 0.07` | slow (35%) |
| còn lại | clear |

Các ngưỡng nằm trong `PedestrianSafety.__init__` và có thể chỉnh khi lắp camera.

## 5. Hiệu chỉnh vùng an toàn

1. Đặt robot ở vị trí vận hành, camera đúng góc thật.
2. Cho một người đứng ở khoảng cách an toàn mong muốn (ví dụ 1.5 m).
3. Xem `area_ratio` và `bottom_ratio` (có thể in tạm trong `ai_demo.py` hoặc dùng debugger).
4. Đặt `slow_area_ratio` và `stop_area_ratio` tương ứng.
5. Test với nhiều chiều cao người, ánh sáng, góc camera.
6. Test trường hợp người đi ngang, ngồi, hoặc bị che khuất một phần.

Camera càng thấp và hướng lên thì `bottom_ratio` càng nhạy với người ở gần. Camera cao nhìn xuống thì diện tích box tăng chậm hơn; cần giảm ngưỡng.

## 6. Tăng tốc trên Jetson

- Export TensorRT:

```bash
yolo export model=yolov8n.pt format=engine imgsz=640 half=True
```

Sau đó dùng backend Ultralytics với `--model yolov8n.engine`.

- Giảm `--imgsz` xuống 416 hoặc 320 nếu FPS thấp.
- Chỉ chạy detect mỗi 2–3 frame, giữ quyết định gần nhất giữa các frame.
- Dùng camera CSI với pipeline GStreamer thay vì USB nếu có thể.
- Đặt `cv2.setNumThreads(1)` nếu tranh CPU với luồng UART.

## 7. Giới hạn

- Khoảng cách ước lượng bằng diện tích box là phương pháp thô, phụ thuộc chiều cao người và góc camera. Không dùng làm cảm biến đo khoảng cách chính xác.
- YOLO có thể bỏ sót người bị che khuất, ngược sáng, hoặc quá nhỏ.
- Không có theo dõi đối tượng (tracking) nên box có thể nhảy giữa các frame; có thể thêm ByteTrack/DeepSORT.
- Nên bổ sung cảm biến siêu âm/LiDAR hoặc bumper vật lý cho vùng chết sát robot.

## 8. Tích hợp vào GUI (tùy chọn)

Hiện AI chạy trong tiến trình riêng (`ai_demo.py`) để đơn giản và an toàn khi thử nghiệm.
Muốn tích hợp vào GUI, tạo một thread đọc camera, gọi `detector.detect()` và `safety.evaluate()`,
sau đó gọi `link.set_velocity()` thay cho lệnh từ nút bấm. Khi AI ở trạng thái `stop`, phải có quyền override mọi lệnh thủ công.
