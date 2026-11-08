import socket
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs

# Địa chỉ IP và Port của ESP8266
ESP_IP = '192.168.4.1'
ESP_PORT = 8080

HTML_PAGE = """<!DOCTYPE html>
<html>
<head>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Điều khiển Robot Mecanum</title>
    <style>
        body { font-family: Arial; text-align: center; background-color: #222; color: white; margin-top: 50px;}
        .btn { background-color: #4CAF50; color: white; padding: 20px 40px; font-size: 24px; margin: 10px; border: none; border-radius: 10px; cursor: pointer;}
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
        <button class="btn" onmousedown="sendCmd('V,0.5,0,0')" onmouseup="sendCmd('STOP')" ontouchstart="sendCmd('V,0.5,0,0')" ontouchend="sendCmd('STOP')">▲ Tiến</button>
        <button class="btn empty"></button>
        <button class="btn" onmousedown="sendCmd('V,0,0.5,0')" onmouseup="sendCmd('STOP')" ontouchstart="sendCmd('V,0,0.5,0')" ontouchend="sendCmd('STOP')">◀ Ngang</button>
        <button class="btn btn-stop" onclick="sendCmd('STOP')">STOP</button>
        <button class="btn" onmousedown="sendCmd('V,0,-0.5,0')" onmouseup="sendCmd('STOP')" ontouchstart="sendCmd('V,0,-0.5,0')" ontouchend="sendCmd('STOP')">Ngang ▶</button>
        <button class="btn empty"></button>
        <button class="btn" onmousedown="sendCmd('V,-0.5,0,0')" onmouseup="sendCmd('STOP')" ontouchstart="sendCmd('V,-0.5,0,0')" ontouchend="sendCmd('STOP')">▼ Lùi</button>
        <button class="btn empty"></button>
    </div>
    <div style="margin-top: 30px;">
        <button class="btn" onmousedown="sendCmd('V,0,0,1.0')" onmouseup="sendCmd('STOP')" ontouchstart="sendCmd('V,0,0,1.0')" ontouchend="sendCmd('STOP')">Xoay Trái</button>
        <button class="btn" onmousedown="sendCmd('V,0,0,-1.0')" onmouseup="sendCmd('STOP')" ontouchstart="sendCmd('V,0,0,-1.0')" ontouchend="sendCmd('STOP')">Xoay Phải</button>
    </div>
    <p class="status" id="status">Sẵn sàng</p>
    <script>
        function sendCmd(cmd) {
            document.getElementById('status').innerText = 'Gửi: ' + cmd;
            fetch('/cmd?c=' + encodeURIComponent(cmd))
                .then(r => r.text())
                .then(t => document.getElementById('status').innerText = 'OK: ' + cmd)
                .catch(e => document.getElementById('status').innerText = 'Lỗi: ' + e);
        }
    </script>
</body>
</html>
"""


class RobotWebHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(HTML_PAGE.encode('utf-8'))

        elif parsed.path == '/cmd':
            params = parse_qs(parsed.query)
            cmd = params.get('c', [''])[0]
            if not cmd:
                self.send_response(400)
                self.end_headers()
                self.wfile.write(b'Missing command')
                return
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(1)
                s.connect((ESP_IP, ESP_PORT))
                s.sendall((cmd + '\n').encode('utf-8'))
                s.close()
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b'OK')
            except Exception as e:
                self.send_response(500)
                self.end_headers()
                self.wfile.write(str(e).encode('utf-8'))
        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b'Not found')

    def log_message(self, format, *args):
        pass  # Tắt log HTTP để gọn terminal


if __name__ == '__main__':
    print("Web Server đang chạy tại: http://localhost:8000")
    print("Hãy mở trình duyệt và truy cập http://localhost:8000")
    print("Trên điện thoại: http://<IP_máy_tính>:8000")
    server = HTTPServer(('0.0.0.0', 8000), RobotWebHandler)
    server.serve_forever()
