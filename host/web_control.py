"""Web điều khiển robot qua ESP8266 bridge.

Chạy: python3 web_control.py [--host 172.20.10.10] [--port 8080]
Hoặc đặt biến môi trường ROBOT_ESP_HOST / ROBOT_ESP_PORT.
"""

import argparse
import os
import socket
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs

# IP/port của ESP8266 (có thể override bằng --host/--port hoặc biến môi trường)
ESP_HOST = os.environ.get("ROBOT_ESP_HOST", "172.20.10.10")
ESP_PORT = int(os.environ.get("ROBOT_ESP_PORT", "8080"))

# Token tuỳ chọn: nếu đặt ROBOT_WEB_TOKEN, mọi yêu cầu /cmd và trang chủ phải
# kèm query ?token=<giá trị>. Không đặt = truy cập mở trong LAN (bất kỳ ai
# trong hotspot cũng điều khiển được robot).
WEB_TOKEN = os.environ.get("ROBOT_WEB_TOKEN", "").strip()

# Giữ một socket TCP duy nhất tới ESP (tránh mở/đóng liên tục mỗi lệnh)
_robot_socket = None
_robot_lock = threading.Lock()

HTML_PAGE = """<!DOCTYPE html>
<html>
<head>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Điều khiển Robot Mecanum</title>
    <style>
        body { font-family: Arial; text-align: center; background-color: #222; color: white; margin-top: 50px;}
        .btn { background-color: #4CAF50; color: white; padding: 20px 40px; font-size: 24px; margin: 10px; border: none; border-radius: 10px; cursor: pointer; user-select: none; touch-action: none;}
        .btn-stop { background-color: red; }
        .grid { display: grid; grid-template-columns: repeat(3, 1fr); width: 300px; margin: 0 auto; }
        .empty { visibility: hidden; }
        .status { margin-top: 20px; font-size: 14px; color: #aaa; }
    </style>
</head>
<body>
    <h2>Robot Mecanum</h2>
    <div class="grid">
        <button class="btn empty"></button>
        <button class="btn" data-cmd="V,0.5,0,0">▲ Tiến</button>
        <button class="btn empty"></button>
        <button class="btn" data-cmd="V,0,0.5,0">◀ Ngang</button>
        <button class="btn btn-stop" data-cmd="STOP">STOP</button>
        <button class="btn" data-cmd="V,0,-0.5,0">Ngang ▶</button>
        <button class="btn empty"></button>
        <button class="btn" data-cmd="V,-0.5,0,0">▼ Lùi</button>
        <button class="btn empty"></button>
    </div>
    <div style="margin-top: 30px;">
        <button class="btn" data-cmd="V,0,0,1.0">Xoay Trái</button>
        <button class="btn" data-cmd="V,0,0,-1.0">Xoay Phải</button>
    </div>
    <p class="status" id="status">Sẵn sàng</p>
    <script>
        // ESP tự dừng robot sau 500 ms nếu không nhận lệnh -> lặp lệnh khi giữ nút.
        const REPEAT_MS = 100;
        let repeatTimer = null;
        const token = new URLSearchParams(window.location.search).get('token') || '';

        function sendCmd(cmd) {
            fetch('/cmd?c=' + encodeURIComponent(cmd) + '&token=' + encodeURIComponent(token))
                .then(r => r.ok ? r.text() : Promise.reject(r.statusText))
                .then(() => { document.getElementById('status').innerText = 'OK: ' + cmd; })
                .catch(e => { document.getElementById('status').innerText = 'Lỗi: ' + e; });
        }

        function startCmd(cmd) {
            stopRepeat();
            sendCmd(cmd);
            repeatTimer = setInterval(() => sendCmd(cmd), REPEAT_MS);
        }

        function stopCmd() {
            stopRepeat();
            sendCmd('STOP');
        }

        function stopRepeat() {
            if (repeatTimer !== null) {
                clearInterval(repeatTimer);
                repeatTimer = null;
            }
        }

        document.querySelectorAll('.btn[data-cmd]').forEach(btn => {
            const cmd = btn.dataset.cmd;
            if (cmd === 'STOP') {
                btn.addEventListener('click', stopCmd);
                return;
            }
            ['mousedown', 'touchstart'].forEach(ev =>
                btn.addEventListener(ev, e => { e.preventDefault(); startCmd(cmd); }, {passive: false}));
            ['mouseup', 'mouseleave', 'touchend', 'touchcancel'].forEach(ev =>
                btn.addEventListener(ev, e => { e.preventDefault(); stopCmd(); }, {passive: false}));
        });

        // Thoát tab / mất focus: dừng robot ngay
        window.addEventListener('blur', stopCmd);
        document.addEventListener('visibilitychange', () => { if (document.hidden) stopCmd(); });
    </script>
</body>
</html>
"""


def robot_send(cmd):
    """Gửi 1 dòng lệnh tới ESP qua socket TCP dùng lại."""
    global _robot_socket
    with _robot_lock:
        try:
            if _robot_socket is None:
                _robot_socket = socket.create_connection((ESP_HOST, ESP_PORT), timeout=1.0)
                _robot_socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            _robot_socket.sendall((cmd + "\n").encode("ascii"))
            return True, ""
        except OSError as exc:
            if _robot_socket is not None:
                try:
                    _robot_socket.close()
                except OSError:
                    pass
                _robot_socket = None
            return False, str(exc)


class RobotWebHandler(BaseHTTPRequestHandler):
    def _token_ok(self, parsed):
        """Trả True nếu không đặt ROBOT_WEB_TOKEN hoặc token khớp."""
        if not WEB_TOKEN:
            return True
        params = parse_qs(parsed.query)
        return params.get("token", [""])[0] == WEB_TOKEN

    def do_GET(self):
        parsed = urlparse(self.path)
        if not self._token_ok(parsed):
            self.send_response(401)
            self.end_headers()
            self.wfile.write(b"Unauthorized: them ?token=<ROBOT_WEB_TOKEN>")
            return
        if parsed.path == "/":
            self.send_response(200)
            self.send_header("Content-type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(HTML_PAGE.encode("utf-8"))
            return

        if parsed.path == "/cmd":
            params = parse_qs(parsed.query)
            cmd = params.get("c", [""])[0].strip()
            if not cmd:
                self.send_response(400)
                self.end_headers()
                self.wfile.write(b"Missing command")
                return
            ok, error = robot_send(cmd)
            if ok:
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b"OK")
            else:
                self.send_response(502)
                self.end_headers()
                self.wfile.write(error.encode("utf-8"))
            return

        self.send_response(404)
        self.end_headers()
        self.wfile.write(b"Not found")

    def log_message(self, format, *args):
        pass  # Tắt log HTTP để gọn terminal


def parse_args():
    parser = argparse.ArgumentParser(description="Web server điều khiển robot qua ESP8266")
    parser.add_argument("--host", default=ESP_HOST, help="IP của ESP8266 (mặc định %s)" % ESP_HOST)
    parser.add_argument("--port", type=int, default=ESP_PORT, help="TCP port của ESP8266 (mặc định %d)" % ESP_PORT)
    parser.add_argument("--listen", type=int, default=8000, help="port HTTP của web server (mặc định 8000)")
    return parser.parse_args()


def main():
    global ESP_HOST, ESP_PORT
    args = parse_args()
    ESP_HOST = args.host
    ESP_PORT = args.port
    print("Web server: http://localhost:%d" % args.listen)
    print("ESP8266   : %s:%d" % (ESP_HOST, ESP_PORT))
    print("Trên điện thoại: http://<IP_máy_tính>:%d" % args.listen)
    if not WEB_TOKEN:
        print("Cảnh báo: chưa đặt ROBOT_WEB_TOKEN → bất kỳ ai trong hotspot đều điều khiển được robot.")
        print("          Đặt ROBOT_WEB_TOKEN=<chuỗi bí mật> rồi truy cập http://<IP>:8000/?token=<chuỗi bí mật>")
    server = HTTPServer(("0.0.0.0", args.listen), RobotWebHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        robot_send("STOP")
        server.server_close()


if __name__ == "__main__":
    main()
