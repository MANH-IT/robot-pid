#!/usr/bin/env python3
import argparse
import math
import time

from robot_host.config import RobotConfig
from robot_host.gui import RobotGUI
from robot_host.serial_link import SerialLink
from robot_host.sim_link import SimulatedLink


def parse_args():
    parser = argparse.ArgumentParser(description="Điều khiển robot Mecanum qua UART")
    parser.add_argument("--port", default="/dev/ttyUSB0", help="cổng serial (mặc định /dev/ttyUSB0)")
    parser.add_argument("--baud", type=int, default=115200)
    parser.add_argument("--sim", action="store_true", help="chạy mô phỏng, không cần phần cứng")
    parser.add_argument("--monitor", action="store_true", help="chỉ in telemetry, không mở GUI")
    parser.add_argument("--wheel-radius", type=float, default=0.04, help="bán kính bánh hiệu dụng (m)")
    parser.add_argument("--wheelbase", type=float, default=0.25, help="khoảng cách trục trước-sau (m)")
    parser.add_argument("--track", type=float, default=0.20, help="khoảng cách hai bánh trái-phải (m)")
    parser.add_argument("--max-rpm", type=float, default=333.0)
    parser.add_argument("--invert-vy", action="store_true", help="đảo chiều đi ngang nếu lắp bánh ngược")
    parser.add_argument("--invert-omega", action="store_true", help="đảo chiều xoay nếu lắp bánh ngược")
    return parser.parse_args()


def run_monitor(link):
    link.set_velocity(0.0, 0.0, 0.0)
    print("Monitor telemetry. Ctrl+C để thoát.")
    try:
        while True:
            snapshot = link.snapshot()
            telemetry = snapshot["telemetry"]
            pose = snapshot["pose"]
            if telemetry is None:
                print("chưa có telemetry, connected=%s error=%s" % (snapshot["connected"], snapshot["error"]))
            else:
                age_ms = (snapshot["age_s"] or 0.0) * 1000.0
                print(
                    "t=%dms rpm=%s pose=(%.3f, %.3f, %.1fdeg) age=%.0fms"
                    % (
                        telemetry.t_ms,
                        ["%.1f" % value for value in telemetry.rpm_actual],
                        pose.x,
                        pose.y,
                        math.degrees(pose.theta),
                        age_ms,
                    )
                )
            time.sleep(0.2)
    except KeyboardInterrupt:
        pass


def main():
    args = parse_args()
    config = RobotConfig(
        wheel_radius_m=args.wheel_radius,
        wheelbase_m=args.wheelbase,
        track_width_m=args.track,
        max_wheel_rpm=args.max_rpm,
        vy_inverted=args.invert_vy,
        omega_inverted=args.invert_omega,
        serial_port=args.port,
        baudrate=args.baud,
    )

    if args.sim:
        link = SimulatedLink(config)
    else:
        link = SerialLink(config)

    link.start()
    try:
        if args.monitor:
            run_monitor(link)
        else:
            RobotGUI(link, config, simulated=args.sim).run()
    finally:
        link.stop()
        link.close()


if __name__ == "__main__":
    main()
