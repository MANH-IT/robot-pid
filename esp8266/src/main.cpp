/*
 * ESP8266 BRIDGE – CẦU NỐI TCP ↔ UART CHO ROBOT MECANUM
 *
 * Chức năng:
 * - Kết nối WiFi STA (SSID/mật khẩu trong secrets.h, xem secrets.example.h)
 * - Lắng nghe TCP port 8080
 * - Chuyển byte TCP → UART0 (TX/RX với STM32)
 * - Chuyển byte UART0 → TCP (telemetry)
 * - Không xử lý logic, chỉ bridge trong suốt
 *
 * Kết nối:
 * - GPIO13 (RX) ← PA2 (TX của STM32)
 * - GPIO15 (TX) → PA3 (RX của STM32)
 *
 * QUAN TRỌNG: ESP8266 chỉ có MỘT UART phần cứng đầy đủ (UART0).
 * UART1 (Serial1) chỉ truyền được và không có RX, nên bridge dùng UART0
 * qua Serial.swap() → RX=GPIO13, TX=GPIO15. USB (GPIO1/GPIO3) bị ngắt
 * khỏi UART0 sau swap, nên log debug được gửi qua TCP thay vì Serial.
 */

#include <Arduino.h>
#include <ESP8266WiFi.h>
#include <ESP8266mDNS.h>
#include <WiFiUdp.h>
#include <stdarg.h>
#include <stdio.h>

#include "secrets.h"

/* ============================================================
 * CẤU HÌNH
 * ============================================================ */
#define TCP_PORT        8080
#define LINK_BAUD       115200
#define DISCOVERY_PORT  8266

/* UART0 sau swap: GPIO13 (RX), GPIO15 (TX) – kết nối STM32 */
#define STM32_RX_PIN    13   /* ESP RX ← STM32 TX (PA2) */
#define STM32_TX_PIN    15   /* ESP TX → STM32 RX (PA3) */

/* Log debug qua TCP: đệm vài dòng trước khi client kết nối */
#define LOG_LINE_MAX    96
#define LOG_QUEUE_LINES 8

/* ============================================================
 * BIẾN TOÀN CỤC
 * ============================================================ */
WiFiServer server(TCP_PORT);
WiFiClient client;
WiFiUDP udp;

/* Theo dõi hoạt động của client TCP: nếu client BỊ TREO (không nhận/gửi byte
 * nào trong CLIENT_IDLE_TIMEOUT_MS) thì gỡ client xuống và phục vụ client
 * mới. Không dùng client.connected() đơn thuần vì TCP có thể treo không FIN
 * khiến ESP không bao giờ nhận client mới (GUI đứng im nhưng connected). */
#define CLIENT_IDLE_TIMEOUT_MS 10000u
static uint32_t last_activity_ms;

static char log_queue[LOG_QUEUE_LINES][LOG_LINE_MAX];
static uint8_t log_head;
static uint8_t log_count;

/* Bộ đệm lọc dòng UART -> TCP: chỉ chuyển tiếp dòng bắt đầu bằng 'T' hoặc 'V' */
static char uart_line[256];
static size_t uart_line_len;
static uint8_t uart_line_overflow;

/* ============================================================
 * LOG QUA TCP (không dùng Serial để tránh nhiễu đường UART)
 * ============================================================ */
static void log_flush(void)
{
    while (log_count > 0u && client && client.connected()) {
        client.println(log_queue[log_head]);
        log_head = (uint8_t)((log_head + 1u) % LOG_QUEUE_LINES);
        log_count--;
    }
}

static void logf(const char *fmt, ...)
{
    char line[LOG_LINE_MAX];
    va_list args;

    va_start(args, fmt);
    vsnprintf(line, sizeof(line), fmt, args);
    va_end(args);

    if (client && client.connected()) {
        client.println(line);
        return;
    }

    if (log_count < LOG_QUEUE_LINES) {
        uint8_t slot = (uint8_t)((log_head + log_count) % LOG_QUEUE_LINES);
        strncpy(log_queue[slot], line, LOG_LINE_MAX - 1u);
        log_queue[slot][LOG_LINE_MAX - 1u] = '\0';
        log_count++;
    }
}

/* ============================================================
 * SETUP
 * ============================================================ */
void setup() {
    /* --- UART0 dùng cho STM32: swap sang GPIO13 (RX) / GPIO15 (TX) --- */
    Serial.begin(LINK_BAUD, SERIAL_8N1, SERIAL_FULL);
    Serial.swap();
    /* Xóa byte rác có thể còn trong buffer RX lúc boot */
    while (Serial.available()) {
        (void)Serial.read();
    }

    logf("========================================");
    logf("  ESP8266 BRIDGE – ROBOT MECANUM");
    logf("========================================");
    logf("[UART] UART0 @ %d (RX=GPIO%d, TX=GPIO%d)", LINK_BAUD, STM32_RX_PIN, STM32_TX_PIN);

    /* --- WiFi STA mode (kết nối Hotspot điện thoại) --- */
    WiFi.mode(WIFI_STA);
    /* Tắt modem sleep: mặc định ESP8266 ngủ giữa các beacon, gói TCP bị
     * giữ 100–500 ms → điều khiển cảm giác trễ, thả phím vẫn trôi. */
    WiFi.setSleepMode(WIFI_NONE_SLEEP);
    WiFi.setAutoReconnect(true);
    WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
    logf("[WiFi] Dang ket noi %s", WIFI_SSID);
    while (WiFi.status() != WL_CONNECTED) {
        delay(500);
    }
    logf("[WiFi] SSID: %s", WIFI_SSID);
    logf("[WiFi] IP cua ESP8266: %s", WiFi.localIP().toString().c_str());

    /* --- TCP server + discovery (UDP broadcast, mDNS) --- */
    server.begin();
    server.setNoDelay(true);
    udp.begin(DISCOVERY_PORT);
    if (MDNS.begin("robot")) {
        MDNS.addService("robot", "tcp", TCP_PORT);
    }
    logf("[TCP] Server port: %d", TCP_PORT);
    logf("[DISC] UDP %d / mdns robot.local", DISCOVERY_PORT);
    logf("[READY] Cho ket noi TCP...");
    logf("========================================");
}

/* ============================================================
 * LOOP
 * ============================================================ */
/* Trả lời gói dò tìm "ROBOT?" của host: "ROBOT!<ip>:<port>\n" */
static void handle_discovery(void)
{
    int size = udp.parsePacket();
    if (size <= 0) {
        return;
    }
    char request[16];
    int length = udp.read(request, sizeof(request) - 1);
    if (length <= 0) {
        return;
    }
    request[length] = '\0';
    if (strncmp(request, "ROBOT?", 6) == 0) {
        udp.beginPacket(udp.remoteIP(), udp.remotePort());
        udp.printf("ROBOT!%s:%d\n", WiFi.localIP().toString().c_str(), TCP_PORT);
        udp.endPacket();
    }
}

void loop() {
    handle_discovery();

    /* --- Chấp nhận client mới --- */
    if (!client || !client.connected()) {
        WiFiClient newClient = server.available();
        if (newClient) {
            client = newClient;
            client.setNoDelay(true);
            last_activity_ms = millis();
            log_flush();
            logf("[TCP] Client connected: %s", client.remoteIP().toString().c_str());
        }
    }

    /* --- Gỡ client treo (không byte nào 2 chiều trong 10 s) --- */
    if (client && client.connected()) {
        if ((uint32_t)(millis() - last_activity_ms) > CLIENT_IDLE_TIMEOUT_MS) {
            logf("[TCP] Client idle > %lus, dropped", CLIENT_IDLE_TIMEOUT_MS / 1000u);
            client.stop();
            client = WiFiClient();
        }
    }

    /* --- TCP → UART0 (lệnh từ host) --- */
    if (client && client.connected()) {
        uint8_t buf[128];
        size_t n = 0;
        while (client.available()) {
            if (n == sizeof(buf)) {
                Serial.write(buf, n);
                n = 0;
            }
            buf[n++] = (uint8_t)client.read();
        }
        if (n > 0u) {
            Serial.write(buf, n);
            /* Ghi nhận activity để client sống còn không bị gỡ nhầm */
            last_activity_ms = millis();
        }
    }

    /* --- UART0 → TCP (telemetry từ STM32), lọc bỏ ký tự rác --- */
    {
        while (Serial.available()) {
            char c = (char)Serial.read();
            if (c == '\r') {
                continue;
            }
            if (uart_line_overflow) {
                if (c == '\n') {
                    uart_line_len = 0u;
                    uart_line_overflow = 0u;
                }
                continue;
            }
            if (uart_line_len < sizeof(uart_line) - 1u) {
                uart_line[uart_line_len++] = c;
            } else {
                uart_line_overflow = 1u;
                continue;
            }
            if (c == '\n') {
                uint8_t forward = 0u;
                if (uart_line_len > 0u &&
                    (uart_line[0] == 'T' || uart_line[0] == 'V')) {
                    forward = 1u;
                }
                if (forward && client && client.connected()) {
                    size_t written = client.write((const uint8_t *)uart_line, uart_line_len);
                    if (written == 0u) {
                        /* Ghi thất bại: host đã ngắt nhưng FIN chưa kịp tới
                         * → gỡ client để host mới có thể vào sau. */
                        logf("[TCP] Write to host failed, disconnect");
                        client.stop();
                        client = WiFiClient();
                    } else {
                        last_activity_ms = millis();
                    }
                }
                uart_line_len = 0u;
                uart_line_overflow = 0u;
            }
        }
    }
}
