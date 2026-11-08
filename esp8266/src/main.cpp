/*
 * ESP8266 BRIDGE – CẦU NỐI TCP ↔ UART CHO ROBOT MECANUM
 *
 * Chức năng:
 * - Phát WiFi AP "MecanumRobot" (pass: 12345678)
 * - Lắng nghe TCP port 8080
 * - Chuyển byte TCP → UART2 (TX/RX với STM32)
 * - Chuyển byte UART2 → TCP (telemetry)
 * - Không xử lý logic, chỉ bridge trong suốt
 *
 * Kết nối:
 * - GPIO13 (RX) ← PA2 (TX của STM32)
 * - GPIO15 (TX) → PA3 (RX của STM32)
 * - Debug: Serial (USB) @ 115200
 */

#include <Arduino.h>
#include <ESP8266WiFi.h>

/* ============================================================
 * CẤU HÌNH
 * ============================================================ */
#define WIFI_SSID       "MecanumRobot"
#define WIFI_PASSWORD   "12345678"
#define TCP_PORT        8080

/* UART2 của ESP8266: GPIO13 (RX), GPIO15 (TX) – kết nối STM32 */
#define STM32_RX_PIN    13   /* ESP RX ← STM32 TX (PA2) */
#define STM32_TX_PIN    15   /* ESP TX → STM32 RX (PA3) */

/* UART debug (USB) */
#define DEBUG_BAUD      115200

/* ============================================================
 * BIẾN TOÀN CỤC
 * ============================================================ */
WiFiServer server(TCP_PORT);
WiFiClient client;

/* ============================================================
 * SETUP
 * ============================================================ */
void setup() {
    /* --- UART debug (USB) --- */
    Serial.begin(DEBUG_BAUD);
    delay(100);
    Serial.println();
    Serial.println(F("========================================"));
    Serial.println(F("  ESP8266 BRIDGE – ROBOT MECANUM"));
    Serial.println(F("========================================"));

    /* --- UART2 kết nối STM32 --- */
    Serial1.begin(DEBUG_BAUD, SERIAL_8N1, SERIAL_FULL, STM32_TX_PIN);
    Serial.println(F("[UART] UART2 @ 115200 (GPIO13/GPIO15)"));

    /* --- WiFi AP mode --- */
    WiFi.mode(WIFI_AP);
    WiFi.softAP(WIFI_SSID, WIFI_PASSWORD, 6);  // Kênh 6 (ít nhiễu hơn kênh 1)
    IPAddress ip = WiFi.softAPIP();
    Serial.print(F("[WiFi] AP SSID: "));
    Serial.println(WIFI_SSID);
    Serial.print(F("[WiFi] Password: "));
    Serial.println(WIFI_PASSWORD);
    Serial.print(F("[WiFi] IP: "));
    Serial.println(ip);

    /* --- TCP server --- */
    server.begin();
    server.setNoDelay(true);
    Serial.print(F("[TCP] Server port: "));
    Serial.println(TCP_PORT);
    Serial.println(F("[READY] Cho ket noi TCP..."));
    Serial.println(F("========================================"));
}

/* ============================================================
 * LOOP
 * ============================================================ */
void loop() {
    /* --- Chấp nhận client mới --- */
    if (!client || !client.connected()) {
        WiFiClient newClient = server.available();
        if (newClient) {
            client = newClient;
            client.setNoDelay(true);
            Serial.print(F("[TCP] Client connected: "));
            Serial.println(client.remoteIP());
        }
    }

    /* --- TCP → UART2 (lệnh từ host) --- */
    if (client && client.connected()) {
        while (client.available()) {
            uint8_t byte = (uint8_t)client.read();
            Serial1.write(byte);
        }
    }

    /* --- UART2 → TCP (telemetry từ STM32) --- */
    while (Serial1.available()) {
        uint8_t byte = (uint8_t)Serial1.read();
        if (client && client.connected()) {
            client.write(byte);
        }
    }
}