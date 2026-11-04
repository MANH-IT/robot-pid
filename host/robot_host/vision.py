"""Nhận diện người đi bộ và chính sách an toàn.

Module này không import cv2/ultralytics ở cấp module để GUI và test vẫn chạy
khi chưa cài các gói thị giác. Chỉ khởi tạo detector mới cần các gói đó.
"""


class Detection(object):
    def __init__(self, x1, y1, x2, y2, confidence, class_name="person"):
        self.x1 = float(x1)
        self.y1 = float(y1)
        self.x2 = float(x2)
        self.y2 = float(y2)
        self.confidence = float(confidence)
        self.class_name = str(class_name)

    @property
    def width(self):
        return max(0.0, self.x2 - self.x1)

    @property
    def height(self):
        return max(0.0, self.y2 - self.y1)

    @property
    def area(self):
        return self.width * self.height

    @property
    def bottom(self):
        return self.y2

    def __repr__(self):
        return "Detection(%.1f, %.1f, %.1f, %.1f, conf=%.2f)" % (
            self.x1, self.y1, self.x2, self.y2, self.confidence
        )


class SafetyDecision(object):
    def __init__(self, action, speed_scale, reason, closest=None):
        self.action = action
        self.speed_scale = float(speed_scale)
        self.reason = reason
        self.closest = closest

    def __repr__(self):
        return "SafetyDecision(action=%s, scale=%.2f, reason=%s)" % (
            self.action, self.speed_scale, self.reason
        )


class PedestrianSafety(object):
    def __init__(
        self,
        min_confidence=0.35,
        stop_area_ratio=0.18,
        slow_area_ratio=0.07,
        near_bottom_ratio=0.85,
        near_area_ratio=0.03,
        slow_scale=0.35,
    ):
        self.min_confidence = float(min_confidence)
        self.stop_area_ratio = float(stop_area_ratio)
        self.slow_area_ratio = float(slow_area_ratio)
        self.near_bottom_ratio = float(near_bottom_ratio)
        self.near_area_ratio = float(near_area_ratio)
        self.slow_scale = float(slow_scale)

    def evaluate(self, detections, frame_width, frame_height):
        frame_area = max(float(frame_width) * float(frame_height), 1.0)
        best = None
        best_area = 0.0

        for detection in detections:
            if detection.class_name != "person":
                continue
            if detection.confidence < self.min_confidence:
                continue
            ratio = detection.area / frame_area
            if ratio > best_area:
                best_area = ratio
                best = detection

        if best is None:
            return SafetyDecision("clear", 1.0, "không có người trong vùng nguy hiểm")

        bottom_ratio = best.bottom / max(float(frame_height), 1.0)
        if best_area >= self.stop_area_ratio:
            return SafetyDecision("stop", 0.0, "người đi bộ quá gần (diện tích lớn)", best)
        if bottom_ratio >= self.near_bottom_ratio and best_area >= self.near_area_ratio:
            return SafetyDecision("stop", 0.0, "người đi bộ ở sát phía trước", best)
        if best_area >= self.slow_area_ratio:
            return SafetyDecision("slow", self.slow_scale, "người đi bộ trong vùng chậm", best)
        return SafetyDecision("clear", 1.0, "người đi bộ ở xa", best)


class YoloDetector(object):
    def __init__(self, backend="ultralytics", model_path="yolov8n.pt", confidence=0.35, imgsz=640, nms=0.45):
        self.backend = backend
        self.model_path = model_path
        self.confidence = float(confidence)
        self.imgsz = int(imgsz)
        self.nms = float(nms)
        self._model = None
        self._net = None
        self._cv2 = None
        self._numpy = None

        if backend == "ultralytics":
            from ultralytics import YOLO
            self._model = YOLO(model_path)
        elif backend == "opencv":
            import cv2
            import numpy
            self._cv2 = cv2
            self._numpy = numpy
            self._net = cv2.dnn.readNetFromONNX(model_path)
        else:
            raise ValueError("backend phải là 'ultralytics' hoặc 'opencv'")

    def detect(self, frame_bgr):
        if self.backend == "ultralytics":
            return self._detect_ultralytics(frame_bgr)
        return self._detect_opencv(frame_bgr)

    def _detect_ultralytics(self, frame_bgr):
        results = self._model.predict(
            source=frame_bgr,
            conf=self.confidence,
            imgsz=self.imgsz,
            verbose=False,
        )
        detections = []
        for result in results:
            names = result.names
            for box in result.boxes:
                class_id = int(box.cls[0].item())
                class_name = names.get(class_id, str(class_id)) if isinstance(names, dict) else names[class_id]
                if class_name != "person":
                    continue
                coordinates = box.xyxy[0].tolist()
                detections.append(
                    Detection(
                        coordinates[0],
                        coordinates[1],
                        coordinates[2],
                        coordinates[3],
                        float(box.conf[0].item()),
                        class_name,
                    )
                )
        return detections

    def _detect_opencv(self, frame_bgr):
        cv2 = self._cv2
        np = self._numpy
        height, width = frame_bgr.shape[:2]
        blob = cv2.dnn.blobFromImage(
            frame_bgr,
            scalefactor=1.0 / 255.0,
            size=(self.imgsz, self.imgsz),
            swapRB=True,
            crop=False,
        )
        self._net.setInput(blob)
        output = self._net.forward()
        predictions = output[0] if output.ndim == 3 else output

        if predictions.shape[0] <= 100 and predictions.shape[1] > predictions.shape[0]:
            predictions = predictions.T

        boxes = []
        scores = []
        for row in predictions:
            if row.shape[0] >= 85:
                objectness = float(row[4])
                class_scores = row[5:]
                class_id = int(np.argmax(class_scores))
                score = objectness * float(class_scores[class_id])
            else:
                class_scores = row[4:]
                class_id = int(np.argmax(class_scores))
                score = float(class_scores[class_id])

            if class_id != 0 or score < self.confidence:
                continue

            cx, cy, bw, bh = [float(value) for value in row[:4]]
            x = (cx - bw / 2.0) * width / self.imgsz
            y = (cy - bh / 2.0) * height / self.imgsz
            w = bw * width / self.imgsz
            h = bh * height / self.imgsz
            boxes.append([x, y, w, h])
            scores.append(score)

        detections = []
        if boxes:
            indices = cv2.dnn.NMSBoxes(boxes, scores, self.confidence, self.nms)
            for index in np.array(indices).flatten():
                x, y, w, h = boxes[int(index)]
                detections.append(Detection(x, y, x + w, y + h, scores[int(index)], "person"))
        return detections


def create_detector(backend="ultralytics", model_path="yolov8n.pt", confidence=0.35, imgsz=640):
    return YoloDetector(backend=backend, model_path=model_path, confidence=confidence, imgsz=imgsz)
