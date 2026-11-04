"""Giao diện Tkinter điều khiển robot Mecanum."""

import math
import tkinter as tk
from tkinter import ttk


DIRECTION_KEYS = {
    "w": "forward",
    "s": "back",
    "a": "left",
    "d": "right",
    "q": "ccw",
    "e": "cw",
    "W": "forward",
    "S": "back",
    "A": "left",
    "D": "right",
    "Q": "ccw",
    "E": "cw",
}


class RobotGUI(object):
    def __init__(self, link, config, simulated=False):
        self.link = link
        self.config = config
        self.simulated = simulated
        self.root = tk.Tk()
        self.root.title("Robot Mecanum - PID Telemetry")
        self.root.geometry("980x640")
        self.root.minsize(900, 600)

        self.directions = set()
        self.rpm_vars = []
        self.rpm_labels = []
        self.sp_labels = []
        self._build_ui()
        self._bind_keys()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self.root.after(50, self._tick)

    def _build_ui(self):
        top = ttk.Frame(self.root, padding=8)
        top.pack(fill="x")

        ttk.Label(top, text="Cổng:").pack(side="left")
        self.port_var = tk.StringVar(value=self.config.serial_port)
        port_entry = ttk.Entry(top, textvariable=self.port_var, width=18)
        port_entry.pack(side="left", padx=(4, 8))
        port_entry.configure(state="disabled" if self.simulated else "normal")

        ttk.Label(top, text="Baud:").pack(side="left")
        ttk.Label(top, text=str(self.config.baudrate)).pack(side="left", padx=(4, 16))

        self.status_var = tk.StringVar(value="Đang khởi tạo...")
        ttk.Label(top, textvariable=self.status_var, foreground="#1a5fb4").pack(side="left")

        self.age_var = tk.StringVar(value="")
        ttk.Label(top, textvariable=self.age_var).pack(side="right")

        body = ttk.Frame(self.root, padding=(8, 0, 8, 8))
        body.pack(fill="both", expand=True)

        left = ttk.Frame(body)
        left.pack(side="left", fill="y", padx=(0, 8))

        self.notebook = ttk.Notebook(left)
        self.notebook.pack(fill="both", expand=True)
        self._build_drive_tab()
        self._build_rpm_tab()

        right = ttk.Frame(body)
        right.pack(side="left", fill="both", expand=True)
        self._build_telemetry_panel(right)

        log = ttk.Frame(self.root, padding=(8, 0, 8, 8))
        log.pack(fill="x")
        self.log_text = tk.Text(log, height=5, state="disabled", wrap="none")
        self.log_text.pack(fill="x")

    def _build_drive_tab(self):
        tab = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(tab, text="Điều khiển")

        ttk.Label(tab, text="Tốc độ tịnh tiến (m/s)").grid(row=0, column=0, sticky="w")
        self.speed_var = tk.DoubleVar(value=0.4)
        ttk.Scale(tab, from_=0.05, to=self.config.max_linear_speed, variable=self.speed_var,
                  orient="horizontal", length=240).grid(row=1, column=0, columnspan=2, sticky="we", pady=(0, 8))
        self.speed_label = ttk.Label(tab, text="0.40")
        self.speed_label.grid(row=1, column=2, sticky="w", padx=(6, 0))

        ttk.Label(tab, text="Tốc độ xoay (rad/s)").grid(row=2, column=0, sticky="w")
        self.turn_var = tk.DoubleVar(value=1.0)
        ttk.Scale(tab, from_=0.1, to=self.config.max_angular_speed, variable=self.turn_var,
                  orient="horizontal", length=240).grid(row=3, column=0, columnspan=2, sticky="we", pady=(0, 8))
        self.turn_label = ttk.Label(tab, text="1.00")
        self.turn_label.grid(row=3, column=2, sticky="w", padx=(6, 0))

        pad = ttk.Frame(tab)
        pad.grid(row=4, column=0, columnspan=3, pady=12)

        buttons = [
            ("↖", "fwd_left", 0, 0), ("↑", "forward", 0, 1), ("↗", "fwd_right", 0, 2),
            ("←", "left", 1, 0), ("■", "stop", 1, 1), ("→", "right", 1, 2),
            ("↙", "back_left", 2, 0), ("↓", "back", 2, 1), ("↘", "back_right", 2, 2),
            ("↺", "ccw", 3, 0), ("E-STOP", "estop", 3, 1), ("↻", "cw", 3, 2),
        ]
        for text, name, row, column in buttons:
            button = ttk.Button(pad, text=text, width=8)
            button.grid(row=row, column=column, padx=3, pady=3)
            if name in ("stop", "estop"):
                button.configure(command=self._emergency_stop)
            else:
                button.bind("<ButtonPress-1>", lambda event, n=name: self._press(n))
                button.bind("<ButtonRelease-1>", lambda event, n=name: self._release(n))
                button.bind("<Leave>", lambda event, n=name: self._release(n))

        self.help_var = tk.StringVar(value="Phím: W/S tiến-lùi, A/D sang trái-phải, Q/E xoay, Space dừng")
        ttk.Label(tab, textvariable=self.help_var).grid(row=5, column=0, columnspan=3, sticky="w", pady=(8, 0))

    def _build_rpm_tab(self):
        tab = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(tab, text="RPM trực tiếp")

        for index in range(4):
            ttk.Label(tab, text="Bánh %d (RPM)" % (index + 1)).grid(row=index, column=0, sticky="w", pady=4)
            variable = tk.DoubleVar(value=0.0)
            spin = ttk.Spinbox(tab, from_=-self.config.max_wheel_rpm, to=self.config.max_wheel_rpm,
                               increment=5.0, textvariable=variable, width=12)
            spin.grid(row=index, column=1, sticky="w", padx=(8, 0))
            self.rpm_vars.append(variable)

        row = ttk.Frame(tab)
        row.grid(row=5, column=0, columnspan=2, sticky="w", pady=(12, 0))
        ttk.Button(row, text="Áp dụng", command=self._apply_rpm).pack(side="left")
        ttk.Button(row, text="Về 0", command=self._zero_rpm).pack(side="left", padx=6)
        ttk.Button(row, text="Gửi PID", command=self._apply_pid).pack(side="left", padx=6)

        ttk.Label(tab, text="PWM thủ công: index,duty (-1..1)").grid(row=6, column=0, columnspan=2, sticky="w", pady=(12, 0))
        manual_row = ttk.Frame(tab)
        manual_row.grid(row=7, column=0, columnspan=2, sticky="w")
        self.manual_var = tk.StringVar(value="1,0.10")
        ttk.Entry(manual_row, textvariable=self.manual_var, width=16).pack(side="left")
        ttk.Button(manual_row, text="Gửi PWM", command=self._apply_manual).pack(side="left", padx=6)
        ttk.Button(manual_row, text="Thoát PWM", command=self._exit_manual).pack(side="left")

        ttk.Label(tab, text="PID online: index,kp,ki,kd").grid(row=8, column=0, columnspan=2, sticky="w", pady=(12, 0))
        self.pid_var = tk.StringVar(value="1,0.0035,0.015,0.00015")
        ttk.Entry(tab, textvariable=self.pid_var, width=32).grid(row=9, column=0, columnspan=2, sticky="w")

        ttk.Label(tab, text="Chỉ dùng khi robot đã được kê bánh hoặc đặt trong khu vực an toàn.").grid(
            row=10, column=0, columnspan=2, sticky="w", pady=(12, 0))

    def _build_telemetry_panel(self, parent):
        status = ttk.LabelFrame(parent, text="Trạng thái", padding=8)
        status.pack(fill="x")
        self.link_var = tk.StringVar(value="--")
        self.mode_var = tk.StringVar(value="--")
        ttk.Label(status, textvariable=self.link_var).pack(anchor="w")
        ttk.Label(status, textvariable=self.mode_var).pack(anchor="w")

        rpm_frame = ttk.LabelFrame(parent, text="RPM thực tế / đặt", padding=8)
        rpm_frame.pack(fill="x", pady=(8, 0))
        for index in range(4):
            row = ttk.Frame(rpm_frame)
            row.pack(fill="x", pady=1)
            ttk.Label(row, text="Bánh %d:" % (index + 1), width=9).pack(side="left")
            actual = ttk.Label(row, text="0.0", width=12, anchor="e")
            actual.pack(side="left")
            ttk.Label(row, text="/").pack(side="left", padx=4)
            setpoint = ttk.Label(row, text="0.0", width=12, anchor="e")
            setpoint.pack(side="left")
            self.rpm_labels.append(actual)
            self.sp_labels.append(setpoint)

        self.canvas = tk.Canvas(parent, height=170, background="#101418", highlightthickness=0)
        self.canvas.pack(fill="x", pady=(8, 0))

        odom = ttk.LabelFrame(parent, text="Odometry", padding=8)
        odom.pack(fill="x", pady=(8, 0))
        self.pose_var = tk.StringVar(value="x = 0.000 m   y = 0.000 m   θ = 0.0°")
        self.distance_var = tk.StringVar(value="quãng đường = 0.000 m")
        ttk.Label(odom, textvariable=self.pose_var).pack(anchor="w")
        ttk.Label(odom, textvariable=self.distance_var).pack(anchor="w")
        ttk.Button(odom, text="Reset odometry", command=self.link.reset_odometry).pack(anchor="w", pady=(6, 0))

    def _bind_keys(self):
        self.root.bind("<KeyPress>", self._on_key_press)
        self.root.bind("<KeyRelease>", self._on_key_release)
        self.root.bind("<space>", lambda event: self._emergency_stop())

    def _on_key_press(self, event):
        if isinstance(event.widget, (tk.Entry, ttk.Entry, ttk.Spinbox, tk.Text)):
            return
        if event.keysym == "space":
            self._emergency_stop()
            return
        direction = DIRECTION_KEYS.get(event.char)
        if direction:
            self.directions.add(direction)
            self._recompute()

    def _on_key_release(self, event):
        direction = DIRECTION_KEYS.get(event.char)
        if direction:
            self.directions.discard(direction)
            self._recompute()

    def _press(self, name):
        self.directions.add(name)
        self._recompute()

    def _release(self, name):
        self.directions.discard(name)
        self._recompute()

    def _recompute(self):
        if "stop" in self.directions:
            self.directions.clear()
        speed = float(self.speed_var.get())
        turn = float(self.turn_var.get())
        vx = 0.0
        vy = 0.0
        omega = 0.0
        if "forward" in self.directions or "fwd_left" in self.directions or "fwd_right" in self.directions:
            vx += speed
        if "back" in self.directions or "back_left" in self.directions or "back_right" in self.directions:
            vx -= speed
        if "left" in self.directions or "fwd_left" in self.directions or "back_left" in self.directions:
            vy += speed
        if "right" in self.directions or "fwd_right" in self.directions or "back_right" in self.directions:
            vy -= speed
        if "ccw" in self.directions:
            omega += turn
        if "cw" in self.directions:
            omega -= turn
        scale = 1.0
        if abs(vx) > 0.0 and abs(vy) > 0.0:
            scale = 1.0 / math.sqrt(2.0)
        self.link.set_velocity(vx * scale, vy * scale, omega)

    def _emergency_stop(self):
        self.directions.clear()
        self.link.stop()
        self._log("E-STOP / STOP đã gửi")

    def _apply_rpm(self):
        try:
            rpms = [float(v.get()) for v in self.rpm_vars]
        except (tk.TclError, ValueError):
            self._log("Giá trị RPM không hợp lệ")
            return
        self.link.set_rpm(*rpms)
        self._log("RPM đặt: %.1f, %.1f, %.1f, %.1f" % tuple(rpms))

    def _zero_rpm(self):
        for variable in self.rpm_vars:
            variable.set(0.0)
        self._apply_rpm()

    def _apply_manual(self):
        parts = self.manual_var.get().split(",")
        if len(parts) != 2:
            self._log("PWM thủ công cần: index,duty")
            return
        try:
            index = int(parts[0])
            duty = float(parts[1])
        except ValueError:
            self._log("PWM thủ công không hợp lệ")
            return
        if index < 1 or index > 4:
            self._log("index PWM phải là 1..4")
            return
        self.link.set_manual(index, duty)
        self._log("PWM thủ công bánh %d, duty %.3f" % (index, duty))

    def _exit_manual(self):
        self.directions.clear()
        self.link.set_velocity(0.0, 0.0, 0.0)
        self._log("Đã thoát PWM thủ công")

    def _apply_pid(self):
        parts = self.pid_var.get().split(",")
        if len(parts) != 4:
            self._log("PID cần đúng 4 số: index,kp,ki,kd")
            return
        try:
            index = int(parts[0])
            kp = float(parts[1])
            ki = float(parts[2])
            kd = float(parts[3])
        except ValueError:
            self._log("PID không hợp lệ")
            return
        if index < 1 or index > 4:
            self._log("index PID phải là 1..4")
            return
        self.link.set_pid(index, kp, ki, kd)
        self._log("Đã gửi PID bánh %d" % index)

    def _log(self, message):
        self.log_text.configure(state="normal")
        self.log_text.insert("end", message + "\n")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    def _draw_bars(self, actual, setpoint):
        canvas = self.canvas
        canvas.delete("all")
        width = max(canvas.winfo_width(), 320)
        height = max(canvas.winfo_height(), 150)
        center = height / 2.0
        limit = max(self.config.max_wheel_rpm, 1.0)
        slot = width / 4.0
        canvas.create_line(0, center, width, center, fill="#3a4652")
        canvas.create_text(8, 10, anchor="w", fill="#8fa1b3", text="+%.0f RPM" % limit)
        canvas.create_text(8, height - 10, anchor="w", fill="#8fa1b3", text="-%.0f RPM" % limit)
        for index in range(4):
            x = slot * (index + 0.5)
            actual_value = max(-limit, min(limit, actual[index]))
            setpoint_value = max(-limit, min(limit, setpoint[index]))
            actual_len = actual_value / limit * (center - 16)
            set_x = setpoint_value / limit * (center - 16)
            canvas.create_rectangle(x - 24, center, x - 10, center - actual_len,
                                    fill="#26a269" if actual_value >= 0 else "#c01c28", outline="")
            canvas.create_line(x + 10, center, x + 10, center - set_x, fill="#f5c211", width=3)
            canvas.create_text(x, height - 24, text="B%d" % (index + 1), fill="#d8dee9")
            canvas.create_text(x, height - 8, text="%.0f" % actual_value, fill="#d8dee9")

    def _tick(self):
        snapshot = self.link.snapshot()
        telemetry = snapshot["telemetry"]
        fresh = self.link.telemetry_fresh()

        if snapshot["connected"] and fresh:
            state = "Đã kết nối" + (" (mô phỏng)" if self.simulated else "")
        elif snapshot["connected"]:
            state = "Đã mở cổng, chưa có telemetry"
        else:
            state = "Mất kết nối"
        if snapshot["error"]:
            state += " - " + snapshot["error"]
        self.status_var.set(state)

        if snapshot["age_s"] is not None:
            self.age_var.set("telemetry: %.0f ms" % (snapshot["age_s"] * 1000.0))
        else:
            self.age_var.set("telemetry: --")

        mode = snapshot["mode"]
        if mode == "rpm":
            target = "RPM trực tiếp: %.1f, %.1f, %.1f, %.1f" % tuple(snapshot["target_rpm"])
        elif mode == "manual":
            target = "PWM thủ công: bánh %d, duty %.3f" % snapshot["manual"]
        else:
            target = "Vận tốc: vx=%.2f vy=%.2f ω=%.2f" % tuple(snapshot["target_velocity"])
        self.mode_var.set(target)

        if telemetry is not None:
            actual = telemetry.rpm_actual
            setpoint = telemetry.rpm_setpoint
            for index in range(4):
                self.rpm_labels[index].configure(text="%+.1f" % actual[index])
                self.sp_labels[index].configure(text="%+.1f" % setpoint[index])
            self._draw_bars(actual, setpoint)
        else:
            for index in range(4):
                self.rpm_labels[index].configure(text="--")
                self.sp_labels[index].configure(text="--")

        pose = snapshot["pose"]
        self.pose_var.set("x = %.3f m   y = %.3f m   θ = %.1f°" % (pose.x, pose.y, math.degrees(pose.theta)))
        self.distance_var.set("quãng đường = %.3f m" % snapshot["distance_m"])
        self.speed_label.configure(text="%.2f" % float(self.speed_var.get()))
        self.turn_label.configure(text="%.2f" % float(self.turn_var.get()))
        self.root.after(50, self._tick)

    def _on_close(self):
        self.root.destroy()

    def run(self):
        self.root.mainloop()
