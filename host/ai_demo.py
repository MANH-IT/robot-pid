#!/usr/bin/env python3
import argparse
import time

from robot_host.config import RobotConfig
from robot_host.serial_link import SerialLink
from robot_host.sim_link import SimulatedLink
from robot_host.vision import PedestrianSafety, create_detector


def parse_args():
    parser = argparse.ArgumentParser(description="Demo AI nhận diện người đi bộ + dừng robot")
    parser.add_argument("--port", default="/dev/ttyUSB0")
    parser.add_argument("--baud", type=int, default=115200)
    parser.add_argument("--sim", action="store_true")
    parser.add_argument("--camera", type=int, default=0)
    parser.add_argument("--backend", choices=["ultralytics", "opencv"], default="ultralytics")
    parser.add_argument("--model", default="yolov8n.pt", help="yolov8n.pt hoặc file .onnx")
    parser.add_argument("--conf", type=float, default=0.35)
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument("--speed", type=float, default=0.2, help="tốc độ tiến khi đường trống (m/s)")
    parser.add_argument("--max-rpm", type=float, default=333.0)
    parser.add_argument("--no-display", action="store_true")
    return parser.parse_args()


def main():
    args = parse_args()

    try:
        import cv2
    except ImportError:
        print("Thiếu opencv-python: pip install opencv-python")
        return 1

    try:
        detector = create_detector(args.backend, args.model, args.conf, args.imgsz)
    except Exception as exc:
        print("Không khởi tạo được detector: %s" % exc)
        return 1

    config = RobotConfig(serial_port=args.port, baudrate=args.baud, max_wheel_rpm=args.max_rpm)
    link = SimulatedLink(config) if args.sim else SerialLink(config)
    link.start()

    safety = PedestrianSafety(min_confidence=args.conf)
    capture = cv2.VideoCapture(args.camera)
    if not capture.isOpened():
        print("Không mở được camera %d" % args.camera)
        link.close()
        return 1

    paused = False
    last_time = time.monotonic()
    fps = 0.0

    try:
        while True:
            ok, frame = capture.read()
            if not ok:
                break

            detections = detector.detect(frame)
            decision = safety.evaluate(detections, frame.shape[1], frame.shape[0])

            if paused or decision.action == "stop":
                link.set_velocity(0.0, 0.0, 0.0)
            elif decision.action == "slow":
                link.set_velocity(args.speed * decision.speed_scale, 0.0, 0.0)
            else:
                link.set_velocity(args.speed, 0.0, 0.0)

            now = time.monotonic()
            dt = now - last_time
            last_time = now
            if dt > 0.0:
                fps = 0.9 * fps + 0.1 * (1.0 / dt) if fps > 0.0 else 1.0 / dt

            if not args.no_display:
                color = (0, 200, 0)
                if decision.action == "slow":
                    color = (0, 200, 255)
                elif decision.action == "stop":
                    color = (0, 0, 255)

                for detection in detections:
                    box_color = (0, 200, 0) if detection is not decision.closest else color
                    cv2.rectangle(
                        frame,
                        (int(detection.x1), int(detection.y1)),
                        (int(detection.x2), int(detection.y2)),
                        box_color,
                        2,
                    )
                    cv2.putText(
                        frame,
                        "person %.2f" % detection.confidence,
                        (int(detection.x1), max(int(detection.y1) - 6, 12)),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.5,
                        box_color,
                        1,
                        cv2.LINE_AA,
                    )

                status = "%s | %.1f FPS" % (decision.action.upper(), fps)
                if paused:
                    status += " | PAUSED"
                cv2.putText(frame, status, (10, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2, cv2.LINE_AA)
                cv2.putText(frame, decision.reason, (10, 54), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1, cv2.LINE_AA)
                cv2.imshow("Robot Mecanum AI", frame)

                key = cv2.waitKey(1) & 0xFF
                if key == 27:
                    break
                if key == 32:
                    paused = not paused
    finally:
        link.stop()
        time.sleep(0.1)
        link.close()
        capture.release()
        cv2.destroyAllWindows()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
