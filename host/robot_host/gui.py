"""Giao diện Tkinter điều khiển robot Mecanum."""

import math
import time
import tkinter as tk
import tkinter.font as tkfont
from collections import deque
from tkinter import ttk


BG = "#ffffff"
HEADER_BG = "#ffffff"
PANEL = "#f6f8fa"
CARD = "#ffffff"
CARD_ALT = "#f3f6f9"
BORDER = "#d0d7de"
TEXT = "#1f2328"
MUTED = "#57606a"
DIM = "#67717b"
ACCENT = "#0969da"
ACCENT_HOVER = "#0550ae"
GREEN = "#1a7f37"
YELLOW = "#f57c00"
RED = "#cf222e"
PURPLE = "#8250df"
INPUT = "#ffffff"
TROUGH = "#eaeef2"
CHART_BG = "#ffffff"
WHEEL_COLORS = ("#e53935", "#1565c0", "#f6c026", "#00838f")

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
    """Giao diện Tkinter điều khiển robot Mecanum:
    - Hiển thị telemetry, odometry, biểu đồ
    - Điều khiển chuyển động, PWM thủ công, PID online
    - E-STOP khẩn cấp, log"""
    def __init__(self, link, config, simulated=False):
        self.link = link
        self.config = config
        self.simulated = simulated
        self.directions = set()
        self.rpm_vars = []
        self.rpm_labels = []
        self.sp_labels = []
        self.wheel_bars = []
        self.history = deque(maxlen=220)
        self._last_telemetry_t = None
        self._last_error = ""
        self._chart_limit = 120.0
        self._estop_blink = True
        self._estop_button_color = GREEN

        self.root = tk.Tk()
        self.root.title("Mecanum Control Center")
        self.root.geometry("1260x820")
        self.root.minsize(1120, 720)
        self.root.configure(bg=BG)
        self.root.grid_rowconfigure(1, weight=1)
        self.root.grid_columnconfigure(0, weight=1)

        families = set(tkfont.families(self.root))
        # Prioritize fonts that support Vietnamese diacritics
        self.font_family = (
            "Arial"
            if "Arial" in families
            else "Times New Roman" if "Times New Roman" in families
            else "Segoe UI" if "Segoe UI" in families
            else "DejaVu Sans"
        )
        self.mono_family = (
            "Consolas"
            if "Consolas" in families
            else "DejaVu Sans Mono"
            if "DejaVu Sans Mono" in families
            else "Courier New"
        )

        self._build_style()
        self._build_header()
        self._build_body()
        self._build_footer()
        self._bind_keys()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self.root.after(50, self._tick)

    def _build_style(self):
        """Thiết lập style Tkinter (theme, màu sắc, font)"""
        style = ttk.Style(self.root)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure(".", font=(self.font_family, 10), background=BG, foreground=TEXT)
        style.configure("TEntry", font=(self.font_family, 10))
        style.configure("TSpinbox", font=(self.font_family, 10))
        style.configure("TScale", font=(self.font_family, 10))
        style.configure("TNotebook", background=BG, borderwidth=0, tabmargins=(0, 0, 0, 0))
        style.configure(
            "TNotebook.Tab",
            background=PANEL,
            foreground=MUTED,
            padding=(16, 9),
            borderwidth=0,
            font=(self.font_family, 9, "bold"),
        )
        style.map(
            "TNotebook.Tab",
            background=[("selected", CARD)],
            foreground=[("selected", TEXT)],
        )
        style.configure(
            "Dark.TEntry",
            fieldbackground=INPUT,
            foreground=TEXT,
            insertcolor=TEXT,
            bordercolor=BORDER,
            lightcolor=BORDER,
            darkcolor=BORDER,
            padding=6,
        )
        style.configure(
            "Dark.TSpinbox",
            fieldbackground=INPUT,
            foreground=TEXT,
            arrowcolor=TEXT,
            bordercolor=BORDER,
            lightcolor=BORDER,
            darkcolor=BORDER,
            padding=6,
        )
        style.configure(
            "Vertical.TScrollbar",
            background=CARD_ALT,
            troughcolor=PANEL,
            bordercolor=BORDER,
            arrowcolor=MUTED,
        )

    def _label(self, parent, text, size=10, color=TEXT, bold=False, mono=False, bg=None, **kwargs):
        """Tạo label Tkinter với font và màu sắc"""
        family = self.mono_family if mono else self.font_family
        weight = "bold" if bold else "normal"
        if bg is None:
            try:
                bg = parent.cget("bg")
            except tk.TclError:
                bg = BG
        return tk.Label(
            parent,
            text=text,
            bg=bg,
            fg=color,
            font=(family, size, weight),
            **kwargs
        )

    def _button(self, parent, text, command=None, kind="neutral", size=10, width=None, height=None,
                bold=True, padx=12, pady=7, **kwargs):
        """Tạo button Tkinter với palette màu"""
        palettes = {
            "neutral": (CARD_ALT, "#e7edf3", TEXT),
            "accent": (ACCENT, ACCENT_HOVER, "#ffffff"),
            "danger": (RED, "#a40e26", "#ffffff"),
            "success": (GREEN, "#116329", "#ffffff"),
        }
        normal, hover, foreground = palettes.get(kind, palettes["neutral"])
        options = dict(
            text=text,
            command=command,
            bg=normal,
            fg=foreground,
            activebackground=hover,
            activeforeground=foreground,
            relief="flat",
            bd=0,
            highlightthickness=0,
            cursor="hand2",
            font=(self.font_family, size, "bold" if bold else "normal"),
            padx=padx,
            pady=pady,
        )
        if width is not None:
            options["width"] = width
        if height is not None:
            options["height"] = height
        options.update(kwargs)
        button = tk.Button(parent, **options)
        button.bind("<Enter>", lambda event: button.configure(bg=hover), add="+")
        button.bind("<Leave>", lambda event: button.configure(bg=normal), add="+")
        return button

    def _hold_button(self, parent, text, name, kind="neutral", **kwargs):
        """Tạo button giữ nút (hold) cho điều khiển chuyển động"""
        button = self._button(parent, text, command=None, kind=kind, **kwargs)
        button.bind("<ButtonPress-1>", lambda event, n=name: self._press(n), add="+")
        button.bind("<ButtonRelease-1>", lambda event, n=name: self._release(n), add="+")
        button.bind("<Leave>", lambda event, n=name: self._release(n), add="+")
        return button

    def _card(self, parent, title, subtitle=None):
        """Tạo khung card với tiêu đề và subtitle"""
        outer = tk.Frame(parent, bg=CARD, highlightbackground=BORDER, highlightthickness=1)
        head = tk.Frame(outer, bg=CARD)
        head.pack(fill="x", padx=14, pady=(10, 0))
        tk.Frame(head, bg=ACCENT, width=3, height=14).pack(side="left", padx=(0, 8))
        self._label(head, title, size=10, bold=True).pack(side="left")
        if subtitle:
            self._label(head, subtitle, size=8, color=MUTED).pack(side="right")
        body = tk.Frame(outer, bg=CARD)
        body.pack(fill="both", expand=True, padx=14, pady=(10, 10))
        return outer, body

    def _build_header(self):
        """Xây dựng header: logo, status, E-STOP button"""
        header = tk.Frame(self.root, bg=HEADER_BG, height=76)
        header.grid(row=0, column=0, sticky="ew")
        header.grid_propagate(False)
        tk.Frame(header, bg=ACCENT, height=2).pack(fill="x", side="bottom")

        inner = tk.Frame(header, bg=HEADER_BG)
        inner.pack(fill="both", expand=True, padx=18, pady=10)

        brand = tk.Frame(inner, bg=HEADER_BG)
        brand.pack(side="left")
        self._label(brand, "MECANUM // PID", size=18, bold=True, bg=HEADER_BG).pack(anchor="w")
        self._label(
            brand,
            "STM32F103  ·  4× JGB37-520  ·  4× BTS7960",
            size=8,
            color=MUTED,
            bg=HEADER_BG,
        ).pack(anchor="w")

        status = tk.Frame(inner, bg=HEADER_BG)
        status.pack(side="left", padx=(36, 0))
        line = tk.Frame(status, bg=HEADER_BG)
        line.pack(anchor="w")
        self.status_dot = tk.Canvas(line, width=12, height=12, bg=HEADER_BG, highlightthickness=0)
        self.status_dot.pack(side="left", padx=(0, 7))
        self._status_dot_id = self.status_dot.create_oval(2, 2, 10, 10, fill=MUTED, outline="")
        self.status_var = tk.StringVar(value="Đang khởi tạo...")
        self.pin_var = tk.StringVar(value="Pin: --V")
        self.status_label = tk.Label(
            line,
            textvariable=self.status_var,
            bg=HEADER_BG,
            fg=MUTED,
            font=(self.font_family, 10, "bold"),
        )
        self.status_label.pack(side="left")
        self.pin_label = tk.Label(
            line,
            textvariable=self.pin_var,
            bg=HEADER_BG,
            fg=MUTED,
            font=(self.font_family, 9),
        )
        self.pin_label.pack(side="left", padx=(8, 0))
        self.age_var = tk.StringVar(value="telemetry --")
        self._label(line, "", size=9, color=DIM, bg=HEADER_BG, textvariable=self.age_var).pack(
            side="left", padx=(12, 0)
        )

        badges = tk.Frame(status, bg=HEADER_BG)
        badges.pack(anchor="w", pady=(5, 0))
        self.mode_var = tk.StringVar(value="VẬN TỐC")
        self.mode_badge = tk.Label(
            badges,
            textvariable=self.mode_var,
            bg=CARD_ALT,
            fg=ACCENT,
            padx=10,
            pady=3,
            font=(self.font_family, 8, "bold"),
        )
        self.mode_badge.pack(side="left")
        self.transport_badge = tk.Label(
            badges,
            text=self.config.transport_label,
            bg=YELLOW if self.simulated else GREEN,
            fg="#ffffff",
            padx=10,
            pady=3,
            font=(self.font_family, 8, "bold"),
        )
        self.transport_badge.pack(side="left", padx=(8, 0))

        self._button(
            inner,
            "E-STOP",
            self._emergency_stop,
            kind="danger",
            size=12,
            width=12,
            pady=11,
        ).pack(side="right")

    def _build_body(self):
        """Xây dựng body: left (connection, motion, odometry), center (drive, telemetry), right (tabs)"""
        body = tk.Frame(self.root, bg=BG)
        body.grid(row=1, column=0, sticky="nsew", padx=16, pady=14)
        body.grid_rowconfigure(0, weight=1)
        body.grid_columnconfigure(0, minsize=280)
        body.grid_columnconfigure(1, weight=1)
        body.grid_columnconfigure(2, minsize=350)

        left = tk.Frame(body, bg=BG)
        left.grid(row=0, column=0, sticky="nsw", padx=(0, 12))
        center = tk.Frame(body, bg=BG)
        center.grid(row=0, column=1, sticky="nsew")
        right = tk.Frame(body, bg=BG)
        right.grid(row=0, column=2, sticky="nse", padx=(12, 0))

        self._build_connection_card(left)
        self._build_motion_card(left)
        self._build_odometry_card(left)
        self._build_drive_card(center)
        self._build_telemetry_card(center)

        self.notebook = ttk.Notebook(right)
        self.notebook.pack(fill="both", expand=True)
        calibration_tab = tk.Frame(self.notebook, bg=BG)
        log_tab = tk.Frame(self.notebook, bg=BG)
        self.notebook.add(calibration_tab, text="HIỆU CHUẨN")
        self.notebook.add(log_tab, text="NHẬT KÝ")
        self._build_calibration_tab(calibration_tab)
        self._build_log_tab(log_tab)

    def _build_connection_card(self, parent):
        """Xây dựng card kết nối (kênh, địa chỉ, chi tiết)"""
        card, body = self._card(parent, "KẾT NỐI", "UART")
        card.pack(fill="x", pady=(0, 10))
        rows = (
            ("Kênh", self.config.transport_label),
            ("Địa chỉ", self.config.connection_label),
            ("Chi tiết", self.config.connection_detail),
        )
        for row, (name, value) in enumerate(rows):
            self._label(body, name, size=8, color=MUTED).grid(row=row, column=0, sticky="w", pady=3)
            self._label(body, value, size=9, mono=True).grid(row=row, column=1, sticky="e", pady=3)
        body.grid_columnconfigure(1, weight=1)

    def _build_motion_card(self, parent):
        """Xây dựng card chuyển động (tốc độ, xoay, phím tắt)"""
        card, body = self._card(parent, "CHUYỂN ĐỘNG", "m/s · rad/s")
        card.pack(fill="x", pady=(0, 10))

        head = tk.Frame(body, bg=CARD)
        head.pack(fill="x")
        self._label(head, "Tịnh tiến", size=9, color=MUTED).pack(side="left")
        self.speed_value_label = self._label(head, "0.40", size=9, mono=True, color=ACCENT)
        self.speed_value_label.pack(side="right")
        self.speed_var = tk.DoubleVar(value=0.4)
        speed_scale = tk.Scale(
            body,
            from_=0.05,
            to=self.config.max_linear_speed,
            resolution=0.05,
            orient="horizontal",
            variable=self.speed_var,
            showvalue=False,
            bg=CARD,
            fg=TEXT,
            troughcolor=TROUGH,
            activebackground=ACCENT,
            sliderrelief="flat",
            highlightthickness=0,
            bd=0,
            sliderlength=18,
            width=12,
            command=lambda value: self._update_motion_labels(),
        )
        speed_scale.pack(fill="x", pady=(2, 10))

        head = tk.Frame(body, bg=CARD)
        head.pack(fill="x")
        self._label(head, "Xoay", size=9, color=MUTED).pack(side="left")
        self.turn_value_label = self._label(head, "1.00", size=9, mono=True, color=PURPLE)
        self.turn_value_label.pack(side="right")
        self.turn_var = tk.DoubleVar(value=1.0)
        turn_scale = tk.Scale(
            body,
            from_=0.1,
            to=self.config.max_angular_speed,
            resolution=0.1,
            orient="horizontal",
            variable=self.turn_var,
            showvalue=False,
            bg=CARD,
            fg=TEXT,
            troughcolor=TROUGH,
            activebackground=PURPLE,
            sliderrelief="flat",
            highlightthickness=0,
            bd=0,
            sliderlength=18,
            width=12,
            command=lambda value: self._update_motion_labels(),
        )
        turn_scale.pack(fill="x", pady=(2, 10))

        presets = tk.Frame(body, bg=CARD)
        presets.pack(fill="x")
        self._label(presets, "Tốc độ", size=8, color=MUTED).pack(side="left")
        for value in (0.2, 0.4, 0.6):
            self._button(
                presets,
                "%.1f" % value,
                command=lambda v=value: self.speed_var.set(v),
                size=8,
                padx=8,
                pady=3,
            ).pack(side="right", padx=(4, 0))

        self.help_var = tk.StringVar(
            value="W/S tiến lùi · A/D ngang · Q/E xoay · Space dừng"
        )
        self._label(body, "", size=8, color=DIM, textvariable=self.help_var, wraplength=245, justify="left").pack(
            anchor="w", pady=(10, 0)
        )

    def _build_odometry_card(self, parent):
        """Xây dựng card odometry (vị trí, quãng đường, reset)"""
        card, body = self._card(parent, "ODOMETRY", "vị trí")
        card.pack(fill="x")
        self.pose_var = tk.StringVar(value="x 0.000 m   y 0.000 m   θ 0.0°")
        self.distance_var = tk.StringVar(value="quãng đường 0.000 m")
        self._label(body, "", size=9, mono=True, textvariable=self.pose_var).pack(anchor="w")
        self._label(body, "", size=9, mono=True, color=MUTED, textvariable=self.distance_var).pack(
            anchor="w", pady=(4, 0)
        )
        # Thêm dòng hiển thị đơn vị rõ ràng
        self._label(body, "(m cho x,y; deg cho θ)", size=7, color=DIM, bg=CARD_ALT).pack(anchor="w", pady=(4, 0))
        self._button(
            body,
            "Reset odometry",
            command=self.link.reset_odometry,
            size=8,
            padx=10,
            pady=4,
        ).pack(anchor="w", pady=(10, 0))

    def _build_drive_card(self, parent):
        """Xây dựng card lái xe (nút bấm điều khiển)"""
        card, body = self._card(parent, "LÁI XE", "giữ nút để chạy")
        card.pack(fill="x", pady=(0, 12))

        pad = tk.Frame(body, bg=CARD)
        pad.pack(side="left", padx=(0, 20))
        layout = (
            ("↖", "fwd_left", 0, 0),
            ("↑", "forward", 0, 1),
            ("↗", "fwd_right", 0, 2),
            ("←", "left", 1, 0),
            ("■", "stop", 1, 1),
            ("→", "right", 1, 2),
            ("↙", "back_left", 2, 0),
            ("↓", "back", 2, 1),
            ("↘", "back_right", 2, 2),
        )
        for text, name, row, column in layout:
            if name == "stop":
                button = self._button(
                    pad,
                    "STOP",
                    self._emergency_stop,
                    kind="danger",
                    size=10,
                    width=5,
                    height=2,
                    pady=4,
                )
            else:
                button = self._hold_button(
                    pad,
                    text,
                    name,
                    size=16,
                    width=4,
                    height=2,
                    pady=2,
                )
            button.grid(row=row, column=column, padx=3, pady=3)

        turns = tk.Frame(body, bg=CARD)
        turns.pack(side="left", fill="x", expand=True)
        self._hold_button(
            turns,
            "↺  Xoay trái",
            "ccw",
            size=10,
            pady=8,
        ).pack(fill="x", pady=(0, 6))
        self._hold_button(
            turns,
            "↻  Xoay phải",
            "cw",
            size=10,
            pady=8,
        ).pack(fill="x")

        info = tk.Frame(turns, bg=CARD_ALT, highlightbackground=BORDER, highlightthickness=1)
        info.pack(fill="x", pady=(12, 0))
        inner = tk.Frame(info, bg=CARD_ALT)
        inner.pack(fill="x", padx=10, pady=8)
        self._label(inner, "LỆNH HIỆN TẠI", size=7, color=MUTED, bg=CARD_ALT).pack(anchor="w")
        self.target_var = tk.StringVar(value="vx 0.00   vy 0.00   ω 0.00")
        self._label(
            inner,
            "",
            size=9,
            mono=True,
            bg=CARD_ALT,
            textvariable=self.target_var,
            wraplength=210,
            justify="left",
        ).pack(anchor="w", pady=(3, 0))

    def _build_telemetry_card(self, parent):
        """Xây dựng card telemetry (RPM, setpoint, biểu đồ)"""
        card, body = self._card(parent, "TELEMETRY", "RPM thực tế / đặt")
        card.pack(fill="both", expand=True)

        tiles = tk.Frame(body, bg=CARD)
        tiles.pack(fill="x")
        names = ("FL", "FR", "RL", "RR")
        for index in range(4):
            tiles.grid_columnconfigure(index, weight=1)
            tile = tk.Frame(tiles, bg=CARD_ALT, highlightbackground=BORDER, highlightthickness=1)
            tile.grid(row=0, column=index, sticky="nsew", padx=(0 if index == 0 else 6, 0))
            inner = tk.Frame(tile, bg=CARD_ALT)
            inner.pack(fill="x", padx=10, pady=(8, 7))
            self._label(inner, names[index], size=8, color=MUTED, bg=CARD_ALT).pack(anchor="w")
            actual = self._label(
                inner,
                "--",
                size=18,
                bold=True,
                mono=True,
                color=WHEEL_COLORS[index],
                bg=CARD_ALT,
            )
            actual.pack(anchor="w", pady=(1, 0))
            setpoint = self._label(inner, "SP --", size=8, mono=True, color=DIM, bg=CARD_ALT)
            setpoint.pack(anchor="w")
            bar = tk.Canvas(inner, height=8, bg=CARD_ALT, highlightthickness=0)
            bar.pack(fill="x", pady=(7, 0))
            self.rpm_labels.append(actual)
            self.sp_labels.append(setpoint)
            self.wheel_bars.append(bar)

        chart_head = tk.Frame(body, bg=CARD)
        chart_head.pack(fill="x", pady=(14, 6))
        self._label(chart_head, "LỊCH SỬ RPM", size=8, color=MUTED).pack(side="left")
        legend = tk.Frame(chart_head, bg=CARD)
        legend.pack(side="right")
        for index, name in enumerate(names):
            item = tk.Frame(legend, bg=CARD)
            item.pack(side="left", padx=(8, 0))
            tk.Frame(item, bg=WHEEL_COLORS[index], width=7, height=7).pack(side="left", padx=(0, 4))
            self._label(item, name, size=7, color=MUTED).pack(side="left")

        self.chart = tk.Canvas(
            body,
            height=170,
            bg=CHART_BG,
            highlightbackground=BORDER,
            highlightthickness=1,
        )
        self.chart.pack(fill="both", expand=True)

    def _build_calibration_tab(self, parent):
        """Xây dựng tab hiệu chuẩn (PID, dead-zone, PWM thủ công)"""
        rpm_card, rpm_body = self._card(parent, "RPM TRỰC TIẾP", "4 bánh")
        rpm_card.pack(fill="x", pady=(0, 10))
        for index in range(4):
            row = index // 2
            column = index % 2
            cell = tk.Frame(rpm_body, bg=CARD)
            cell.grid(row=row, column=column, sticky="we", padx=(0, 8), pady=3)
            self._label(cell, "B%d" % (index + 1), size=8, color=MUTED).pack(side="left")
            variable = tk.DoubleVar(value=0.0)
            spin = ttk.Spinbox(
                cell,
                from_=-self.config.max_wheel_rpm,
                to=self.config.max_wheel_rpm,
                increment=5.0,
                textvariable=variable,
                width=9,
                style="Dark.TSpinbox",
            )
            spin.pack(side="right")
            self.rpm_vars.append(variable)
        rpm_body.grid_columnconfigure(0, weight=1)
        rpm_body.grid_columnconfigure(1, weight=1)
        actions = tk.Frame(rpm_body, bg=CARD)
        actions.grid(row=2, column=0, columnspan=2, sticky="w", pady=(8, 0))
        self._button(actions, "Áp dụng", self._apply_rpm, kind="accent", size=9, padx=10, pady=5).pack(
            side="left"
        )
        self._button(actions, "Về 0", self._zero_rpm, size=9, padx=10, pady=5).pack(
            side="left", padx=(6, 0)
        )

        pwm_card, pwm_body = self._card(parent, "PWM THỦ CÔNG", "vòng hở")
        pwm_card.pack(fill="x", pady=(0, 10))
        self.manual_index_var = tk.IntVar(value=1)
        self.manual_duty_var = tk.DoubleVar(value=0.1)
        self._label(pwm_body, "Bánh", size=8, color=MUTED).grid(row=0, column=0, sticky="w")
        ttk.Spinbox(
            pwm_body,
            from_=1,
            to=4,
            textvariable=self.manual_index_var,
            width=5,
            style="Dark.TSpinbox",
        ).grid(row=0, column=1, sticky="w", padx=(6, 14))
        self._label(pwm_body, "Duty", size=8, color=MUTED).grid(row=0, column=2, sticky="w")
        ttk.Spinbox(
            pwm_body,
            from_=-1.0,
            to=1.0,
            increment=0.01,
            textvariable=self.manual_duty_var,
            width=8,
            style="Dark.TSpinbox",
        ).grid(row=0, column=3, sticky="w", padx=(6, 0))
        pwm_actions = tk.Frame(pwm_body, bg=CARD)
        pwm_actions.grid(row=1, column=0, columnspan=4, sticky="w", pady=(8, 0))
        self._button(pwm_actions, "Gửi PWM", self._apply_manual, kind="accent", size=9, padx=10, pady=5).pack(
            side="left"
        )
        self._button(pwm_actions, "Thoát PWM", self._exit_manual, size=9, padx=10, pady=5).pack(
            side="left", padx=(6, 0)
        )

        pid_card, pid_body = self._card(parent, "PID ONLINE", "tinh chỉnh")
        pid_card.pack(fill="x", pady=(0, 10))
        self.pid_index_var = tk.IntVar(value=1)
        self.kp_var = tk.DoubleVar(value=0.0035)
        self.ki_var = tk.DoubleVar(value=0.015)
        self.kd_var = tk.DoubleVar(value=0.00015)
        fields = (
            ("Bánh", self.pid_index_var, 1, 4, 1, 0),
            ("Kp", self.kp_var, 0.0, 1.0, 0.0001, 1),
            ("Ki", self.ki_var, 0.0, 1.0, 0.0001, 2),
            ("Kd", self.kd_var, 0.0, 0.1, 0.00001, 3),
        )
        for name, variable, from_value, to_value, increment, column in fields:
            self._label(pid_body, name, size=8, color=MUTED).grid(
                row=0 if column < 2 else 1,
                column=(column % 2) * 2,
                sticky="w",
                pady=3,
            )
            ttk.Spinbox(
                pid_body,
                from_=from_value,
                to=to_value,
                increment=increment,
                textvariable=variable,
                width=10,
                style="Dark.TSpinbox",
            ).grid(
                row=0 if column < 2 else 1,
                column=(column % 2) * 2 + 1,
                sticky="w",
                padx=(6, 10),
                pady=3,
            )
        self._button(
            pid_body,
            "Gửi PID",
            self._apply_pid,
            kind="accent",
            size=9,
            padx=10,
            pady=5,
        ).grid(row=2, column=0, columnspan=2, sticky="w", pady=(8, 0))

        dz_card, dz_body = self._card(parent, "DEAD-ZONE", "bù ma sát")
        dz_card.pack(fill="x")
        self.dz_index_var = tk.IntVar(value=1)
        self.dz_value_var = tk.DoubleVar(value=0.08)
        self._label(dz_body, "Bánh", size=8, color=MUTED).grid(row=0, column=0, sticky="w")
        ttk.Spinbox(
            dz_body,
            from_=1,
            to=4,
            textvariable=self.dz_index_var,
            width=5,
            style="Dark.TSpinbox",
        ).grid(row=0, column=1, sticky="w", padx=(6, 14))
        self._label(dz_body, "Giá trị", size=8, color=MUTED).grid(row=0, column=2, sticky="w")
        ttk.Spinbox(
            dz_body,
            from_=0.0,
            to=0.5,
            increment=0.01,
            textvariable=self.dz_value_var,
            width=8,
            style="Dark.TSpinbox",
        ).grid(row=0, column=3, sticky="w", padx=(6, 0))
        self._button(
            dz_body,
            "Gửi dead-zone",
            self._apply_deadzone,
            kind="accent",
            size=9,
            padx=10,
            pady=5,
        ).grid(row=1, column=0, columnspan=4, sticky="w", pady=(8, 0))

    def _build_log_tab(self, parent):
        """Xây dựng tab nhật ký (log)"""
        toolbar = tk.Frame(parent, bg=BG)
        toolbar.pack(fill="x", pady=(0, 8))
        self._label(toolbar, "SỰ KIỆN", size=9, bold=True, bg=BG).pack(side="left")
        self._button(toolbar, "Xóa", self._clear_log, size=8, padx=10, pady=3).pack(side="right")

        frame = tk.Frame(parent, bg=BG)
        frame.pack(fill="both", expand=True)
        self.log_text = tk.Text(
            frame,
            bg=INPUT,
            fg=TEXT,
            insertbackground=TEXT,
            relief="flat",
            bd=0,
            highlightbackground=BORDER,
            highlightthickness=1,
            wrap="word",
            font=(self.mono_family, 9),
            width=1,
            height=1,
            padx=8,
            pady=8,
            state="disabled",
        )
        scroll = ttk.Scrollbar(frame, orient="vertical", command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=scroll.set)
        self.log_text.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")
        self.log_text.tag_configure("time", foreground=DIM)
        self.log_text.tag_configure("info", foreground=TEXT)
        self.log_text.tag_configure("warn", foreground=YELLOW)
        self.log_text.tag_configure("error", foreground=RED)
        self._log("Giao diện sẵn sàng")

    def _build_footer(self):
        """Xây dựng footer (tần số lệnh, kết nối)"""
        footer = tk.Frame(self.root, bg=BG)
        footer.grid(row=2, column=0, sticky="ew", padx=18, pady=(0, 10))
        self._label(
            footer,
            "Lệnh 20 Hz  ·  Telemetry 50 Hz  ·  Timeout 500 ms",
            size=8,
            color=DIM,
            bg=BG,
        ).pack(side="left")
        self.footer_var = tk.StringVar(value=self.config.connection_label)
        self._label(footer, "", size=8, color=MUTED, bg=BG, textvariable=self.footer_var).pack(side="right")

    def _bind_keys(self):
        """Bind phím tắt (W/A/S/D/Q/E/Space)"""
        self.root.bind("<KeyPress>", self._on_key_press)
        self.root.bind("<KeyRelease>", self._on_key_release)
        self.root.bind("<FocusOut>", self._on_focus_out)
        self.root.bind("<Unmap>", self._on_focus_out)

    def _on_focus_out(self, _event):
        """Cửa sổ mất focus/bị ẩn: xóa mọi hướng đang giữ để robot không chạy mãi."""
        if self.directions:
            self.directions.clear()
            self._recompute()

    def _on_key_press(self, event):
        """Xử lý phím nhấn: space = E-STOP, W/A/S/D/Q/E = chuyển động"""
        if isinstance(event.widget, (tk.Entry, ttk.Entry, ttk.Spinbox, tk.Text, tk.Scale)):
            return
        if event.keysym == "space":
            self._emergency_stop()
            return
        direction = DIRECTION_KEYS.get(event.char)
        if direction:
            self.directions.add(direction)
            self._recompute()

    def _on_key_release(self, event):
        """Xử lý phím thả: cập nhật directions"""
        direction = DIRECTION_KEYS.get(event.char)
        if direction:
            self.directions.discard(direction)
            self._recompute()

    def _press(self, name):
        """Thêm direction vào set và recompute velocity"""
        self.directions.add(name)
        self._recompute()

    def _release(self, name):
        """Xóa direction khỏi set và recompute velocity"""
        self.directions.discard(name)
        self._recompute()

    def _update_motion_labels(self):
        """Cập nhật label tốc độ và xoay"""
        self.speed_value_label.configure(text="%.2f m/s" % float(self.speed_var.get()))
        self.turn_value_label.configure(text="%.2f rad/s" % float(self.turn_var.get()))

    def _recompute(self):
        """Tính toán velocity từ directions và scale"""
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
        """E-STOP: gửi STOP, clear directions, log warning"""
        self.directions.clear()
        self.link.stop()
        self._log("STOP khẩn cấp đã gửi", "warn")

    def _apply_rpm(self):
        """Áp dụng RPM từ input fields"""
        try:
            rpms = [float(v.get()) for v in self.rpm_vars]
        except (tk.TclError, ValueError):
            self._log("Giá trị RPM không hợp lệ", "error")
            return
        self.link.set_rpm(*rpms)
        self._log("RPM đặt: %.1f, %.1f, %.1f, %.1f" % tuple(rpms))

    def _zero_rpm(self):
        """Đặt tất cả RPM về 0"""
        for variable in self.rpm_vars:
            variable.set(0.0)
        self._apply_rpm()

    def _apply_manual(self):
        """Áp dụng PWM thủ công cho một bánh"""
        try:
            index = int(self.manual_index_var.get())
            duty = float(self.manual_duty_var.get())
        except (tk.TclError, ValueError):
            self._log("PWM thủ công không hợp lệ", "error")
            return
        if index < 1 or index > 4:
            self._log("Kênh PWM phải nằm trong 1..4", "error")
            return
        self.link.set_manual(index, duty)
        self._log("PWM bánh %d, duty %.3f" % (index, duty), "warn")

    def _exit_manual(self):
        """Thoát PWM thủ công, đặt velocity về 0"""
        self.directions.clear()
        self.link.set_velocity(0.0, 0.0, 0.0)
        self._log("Đã thoát PWM thủ công")

    def _apply_pid(self):
        """Áp dụng PID gains online"""
        try:
            index = int(self.pid_index_var.get())
            kp = float(self.kp_var.get())
            ki = float(self.ki_var.get())
            kd = float(self.kd_var.get())
        except (tk.TclError, ValueError):
            self._log("PID không hợp lệ", "error")
            return
        if index < 1 or index > 4:
            self._log("Chỉ số PID phải nằm trong 1..4", "error")
            return
        self.link.set_pid(index, kp, ki, kd)
        self._log("PID bánh %d: Kp=%.6f Ki=%.6f Kd=%.6f" % (index, kp, ki, kd))

    def _apply_deadzone(self):
        """Áp dụng dead-zone online"""
        try:
            index = int(self.dz_index_var.get())
            value = float(self.dz_value_var.get())
        except (tk.TclError, ValueError):
            self._log("Giá trị dead-zone không hợp lệ", "error")
            return
        if index < 1 or index > 4:
            self._log("Chỉ số dead-zone phải nằm trong 1..4", "error")
            return
        self.link.set_deadzone(index, value)
        self._log("Dead-zone bánh %d = %.3f" % (index, value))

    def _log(self, message, level="info"):
        """Ghi log vào text widget"""
        stamp = time.strftime("%H:%M:%S")
        self.log_text.configure(state="normal")
        self.log_text.insert("end", "[%s] " % stamp, "time")
        self.log_text.insert("end", message + "\n", level)
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    def _clear_log(self):
        """Xóa log"""
        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.configure(state="disabled")

    def _draw_wheel_bar(self, index, actual, setpoint):
        """Vẽ thanh RPM cho bánh index"""
        canvas = self.wheel_bars[index]
        canvas.delete("all")
        width = max(canvas.winfo_width(), 40)
        height = max(canvas.winfo_height(), 8)
        middle = width / 2.0
        limit = max(self.config.max_wheel_rpm, 1.0)
        canvas.create_line(0, height / 2.0, width, height / 2.0, fill=BORDER, width=2)
        if actual is None:
            return
        actual = max(-limit, min(limit, actual))
        setpoint = max(-limit, min(limit, setpoint))
        x_actual = middle + actual / limit * (width / 2.0 - 2)
        x_setpoint = middle + setpoint / limit * (width / 2.0 - 2)
        canvas.create_line(
            middle,
            height / 2.0,
            x_actual,
            height / 2.0,
            fill=WHEEL_COLORS[index],
            width=6,
            capstyle="round",
        )
        canvas.create_line(x_setpoint, 0, x_setpoint, height, fill=YELLOW, width=2)

    def _draw_chart(self):
        """Vẽ biểu đồ RPM theo thời gian"""
        canvas = self.chart
        canvas.delete("all")
        width = max(canvas.winfo_width(), 220)
        height = max(canvas.winfo_height(), 110)
        left = 38
        right = 10
        top = 12
        bottom = 14
        plot_width = max(width - left - right, 10)
        plot_height = max(height - top - bottom, 10)

        peak = 0.0
        for sample in self.history:
            for value in sample:
                peak = max(peak, abs(value))
        target = max(60.0, min(self.config.max_wheel_rpm, peak * 1.25 if peak > 0.0 else 100.0))
        self._chart_limit += (target - self._chart_limit) * 0.15
        limit = max(self._chart_limit, 60.0)

        for step in range(5):
            y = top + plot_height * step / 4.0
            value = limit * (1.0 - step / 2.0)
            canvas.create_line(left, y, width - right, y, fill=BORDER)
            canvas.create_text(
                left - 6,
                y,
                text="%+.0f" % value,
                anchor="e",
                fill=DIM,
                font=(self.mono_family, 7),
            )

        count = len(self.history)
        if count >= 2:
            for wheel in range(4):
                points = []
                for index, sample in enumerate(self.history):
                    value = max(-limit, min(limit, sample[wheel]))
                    x = left + plot_width * index / float(count - 1)
                    y = top + plot_height * (1.0 - (value + limit) / (2.0 * limit))
                    points.extend((x, y))
                canvas.create_line(
                    *points,
                    fill=WHEEL_COLORS[wheel],
                    width=2,
                    smooth=True,
                )
        elif count == 1:
            for wheel in range(4):
                value = max(-limit, min(limit, self.history[0][wheel]))
                y = top + plot_height * (1.0 - (value + limit) / (2.0 * limit))
                canvas.create_oval(
                    left - 2,
                    y - 2,
                    left + 2,
                    y + 2,
                    fill=WHEEL_COLORS[wheel],
                    outline="",
                )

    def _tick(self):
        """Cập nhật GUI mỗi 50 ms: status, telemetry, odometry, chart"""
        snapshot = self.link.snapshot()
        telemetry = snapshot["telemetry"]
        fresh = self.link.telemetry_fresh()

        if snapshot["connected"] and fresh:
            status = "MÔ PHỎNG" if self.simulated else "ĐÃ KẾT NỐI"
            color = YELLOW if self.simulated else GREEN
            # Đặt lại màu E-STOP khi có kết nối
            self._estop_button_color = GREEN
        elif snapshot["connected"]:
            status = "CHỜ TELEMETRY"
            color = YELLOW
            self._estop_button_color = YELLOW
        else:
            status = "MẤT KẾT NỐI"
            color = RED
            # Nhấp nháy E-STOP khi mất kết nối
            if not hasattr(self, '_estop_blink') or self._estop_blink:
                self._estop_button_color = RED
                self._estop_blink = not self._estop_blink
            else:
                self._estop_button_color = BG
                self._estop_blink = not self._estop_blink
        self.status_var.set(status)
        self.status_label.configure(fg=color)
        self.status_dot.itemconfig(self._status_dot_id, fill=color)

        if snapshot["age_s"] is not None:
            self.age_var.set("telemetry %.0f ms" % (snapshot["age_s"] * 1000.0))
        else:
            self.age_var.set("telemetry --")

        error = snapshot["error"]
        if error and error != self._last_error:
            self._log(error, "error")
        self._last_error = error

        mode = snapshot["mode"]
        labels = {"velocity": ("VẬN TỐC", ACCENT), "rpm": ("RPM", YELLOW), "manual": ("PWM", PURPLE)}
        mode_text, mode_color = labels.get(mode, (mode.upper(), ACCENT))
        self.mode_var.set(mode_text)
        self.mode_badge.configure(bg=mode_color, fg="#ffffff")

        if mode == "rpm":
            target = "B1 %.1f · B2 %.1f\nB3 %.1f · B4 %.1f" % tuple(snapshot["target_rpm"])
        elif mode == "manual":
            target = "Bánh %d · duty %.3f" % snapshot["manual"]
        else:
            target = "vx %.2f   vy %.2f   ω %.2f" % tuple(snapshot["target_velocity"])
        self.target_var.set(target)

        if telemetry is not None:
            actual = telemetry.rpm_actual
            setpoint = telemetry.rpm_setpoint
            for index in range(4):
                self.rpm_labels[index].configure(text="%+.1f" % actual[index])
                self.sp_labels[index].configure(text="SP %+.1f" % setpoint[index])
                self._draw_wheel_bar(index, actual[index], setpoint[index])
            if telemetry.t_ms != self._last_telemetry_t:
                self.history.append(tuple(actual))
                self._last_telemetry_t = telemetry.t_ms
        else:
            for index in range(4):
                self.rpm_labels[index].configure(text="--")
                self.sp_labels[index].configure(text="SP --")
                self._draw_wheel_bar(index, None, None)

        self._draw_chart()
        self._update_motion_labels()

        pose = snapshot["pose"]
        self.pose_var.set(
            "x %.3f m   y %.3f m   θ %.1f°"
            % (pose.x, pose.y, math.degrees(pose.theta))
        )
        self.distance_var.set("quãng đường %.3f m" % snapshot["distance_m"])
        self.footer_var.set(
            "Mô phỏng · lệnh %d Hz" % int(1.0 / max(self.config.command_period_s, 1e-6))
            if self.simulated
            else "%s · %s" % (self.config.connection_label, self.config.connection_detail)
        )
        self.root.after(50, self._tick)

    def _on_close(self):
        """Đóng cửa sổ GUI"""
        self.root.destroy()

    def run(self):
        """Chạy mainloop Tkinter"""
        self.root.mainloop()
