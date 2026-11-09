"""Dò ESP8266 bridge trong LAN bằng UDP broadcast.

ESP8266 lắng nghe cổng 8266 và trả lời gói "ROBOT?" bằng
"ROBOT!<ip>:<port>\\n" (xem esp8266/src/main.cpp).
"""

import socket
import time

DISCOVERY_PORT = 8266
REQUEST = b"ROBOT?"
DEFAULT_TCP_PORT = 8080


def parse_response(data):
    """Phân tích phản hồi "ROBOT!<ip>:<port>" → (host, port) hoặc None."""
    text = data.decode("ascii", "ignore").strip()
    if not text.startswith("ROBOT!"):
        return None
    endpoint = text[len("ROBOT!") :]
    host, _, raw_port = endpoint.partition(":")
    if not host:
        return None
    try:
        port = int(raw_port) if raw_port else DEFAULT_TCP_PORT
    except ValueError:
        return None
    return host, port


def discover(timeout=1.5, port=DISCOVERY_PORT):
    """Broadcast "ROBOT?" và trả về (ip, port) của ESP, hoặc None.

    Gửi lặp 3 lần để chống mất gói UDP; chỉ nhận phản hồi từ ESP.
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    sock.settimeout(0.3)
    try:
        for _ in range(3):
            try:
                sock.sendto(REQUEST, ("255.255.255.255", port))
            except OSError:
                pass
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            try:
                data, _addr = sock.recvfrom(128)
            except socket.timeout:
                continue
            except OSError:
                break
            endpoint = parse_response(data)
            if endpoint is not None:
                return endpoint
    finally:
        sock.close()
    return None
