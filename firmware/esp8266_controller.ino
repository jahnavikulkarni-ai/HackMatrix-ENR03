#include <ESP8266WiFi.h>
#include <ESP8266WebServer.h>
#include <Servo.h>

// =========================
// Wi-Fi
// =========================
const char* SSID     = "MyHotspotName"; // Update with your hotspot name if needed
const char* PASSWORD = "MyPassword123"; // Update with your password if needed

// iPhone hotspot commonly uses 172.20.10.x
IPAddress local_IP(172, 20, 10, 50);
IPAddress gateway(172, 20, 10, 1);
IPAddress subnet(255, 255, 255, 0);
IPAddress dns(172, 20, 10, 1);

// =========================
// Hardware
// =========================
const int LED_PIN   = D1;   // BC547 base through ~1k
const int SERVO_PIN = D2;

// =========================
// Web server
// =========================
ESP8266WebServer server(80);
Servo servo;

// =========================
// Handlers
// =========================
void handleRoot() {
  server.send(
    200,
    "text/plain",
    "ESP8266 controller online"
  );
}

void handleLedOn() {
  digitalWrite(LED_PIN, HIGH);
  server.send(200, "text/plain", "LED ON");
}

void handleLedOff() {
  digitalWrite(LED_PIN, LOW);
  server.send(200, "text/plain", "LED OFF");
}

void handleServo() {
  if (!server.hasArg("angle")) {
    server.send(400, "text/plain", "Missing angle");
    return;
  }

  int angle = server.arg("angle").toInt();
  angle = constrain(angle, 0, 180);

  servo.write(angle);

  server.send(
    200,
    "text/plain",
    "Servo angle: " + String(angle)
  );
}

void handleStatus() {
  String response = "ONLINE\n";
  response += "IP: ";
  response += WiFi.localIP().toString();
  response += "\nRSSI: ";
  response += String(WiFi.RSSI());

  server.send(200, "text/plain", response);
}

// =========================
// Setup
// =========================
void setup() {

  // LED
  pinMode(LED_PIN, OUTPUT);
  digitalWrite(LED_PIN, LOW);

  // Servo
  servo.attach(SERVO_PIN);
  servo.write(90);

  // Wi-Fi
  WiFi.mode(WIFI_STA);

  // Static IP
  if (!WiFi.config(local_IP, gateway, subnet, dns)) {
    // Don't halt if configuration fails.
  }

  WiFi.begin(SSID, PASSWORD);

  // Wait for Wi-Fi
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
  }

  // Web endpoints
  server.on("/", handleRoot);
  server.on("/led/on", handleLedOn);
  server.on("/led/off", handleLedOff);
  server.on("/servo", handleServo);
  server.on("/status", handleStatus);

  server.begin();
}

// =========================
// Main loop
// =========================
void loop() {
  server.handleClient();
}
