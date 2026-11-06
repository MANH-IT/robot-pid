#include <ESP8266WiFi.h>

const char *AP_SSID = "Robot-PID";
const char *AP_PASS = "robotpid123";
const uint16_t TCP_PORT = 8080;

WiFiServer server(TCP_PORT);
WiFiClient client;

void setup() {
  Serial.begin(115200);
  WiFi.mode(WIFI_AP);
  WiFi.softAP(AP_SSID, AP_PASS);
  server.begin();
  server.setNoDelay(true);
}

void loop() {
  if (!client || !client.connected()) {
    WiFiClient next = server.available();
    if (next) {
      client = next;
      client.setNoDelay(true);
    }
  }

  if (client && client.connected()) {
    while (client.available()) {
      Serial.write(client.read());
    }
    while (Serial.available()) {
      client.write(Serial.read());
    }
  }
}
