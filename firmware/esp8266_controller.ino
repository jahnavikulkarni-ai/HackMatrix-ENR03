const uint8_t buttons[] = {D5, D6, D7};  
const uint8_t lights[]  = {D1, D2, D3};  

const uint8_t N = 3;
const unsigned long DEBOUNCE_MS = 40;

bool lightState[N] = {false, false, false};
bool lastReading[N] = {HIGH, HIGH, HIGH};
bool stableState[N] = {HIGH, HIGH, HIGH};
unsigned long lastChange[N] = {0, 0, 0};

void setup() {
  for (uint8_t i = 0; i < N; i++) {
    digitalWrite(lights[i], LOW);
    pinMode(lights[i], OUTPUT);
    pinMode(buttons[i], INPUT_PULLUP);
  }
}

void loop() {
  for (uint8_t i = 0; i < N; i++) {
    bool reading = digitalRead(buttons[i]);

    if (reading != lastReading[i]) {
      lastChange[i] = millis();
      lastReading[i] = reading;
    }

    if (millis() - lastChange[i] >= DEBOUNCE_MS) {
      if (reading != stableState[i]) {
        stableState[i] = reading;

        // Toggle only when the button is pressed.
        if (stableState[i] == LOW) {
          lightState[i] = !lightState[i];
          digitalWrite(lights[i],
                       lightState[i] ? HIGH : LOW);
        }
      }
    }
  }
}
