#include <Arduino.h>

// Define the pins for the relays
const int relayPins[] = { 2, 3, 4, 5, 6, 7 };  // Array containing all relay pins


const int ledPin = 13;

void setup() {
  // Initialize the relay pins as outputs
  for (int i = 0; i < sizeof(relayPins) / sizeof(relayPins[0]); i++) {
    pinMode(relayPins[i], OUTPUT);
    digitalWrite(relayPins[i], LOW);
  }

  // Initialize serial communication
  Serial1.begin(115200);  // Use Serial1 instead of SerialUSB
}

void loop() {
  static unsigned long relayActivationTime[6] = { 0 };  // Initialize array to track relay activation time
  unsigned long currentMillis = millis();               // Get the current time

  while (Serial.available() > 0) {
    String command = Serial.readStringUntil('\n');  // Read the entire command until newline

    if (command.startsWith("IDN?")) {
      // Reply with the Arduino's name
      Serial.println("RPZERO");  // Modify this to match your Arduino's model
    } else {
      int commaIndex = command.indexOf(',');
      if (commaIndex != -1) {
        // Extract relayNumber and timeOnInMs from the command
        int relayNumber = command.substring(0, commaIndex).toInt();
        int timeOnInMs = command.substring(commaIndex + 1).toInt();

        // Activate the relay and record the activation time
        digitalWrite(relayPins[relayNumber - 1], HIGH);
        relayActivationTime[relayNumber - 1] = currentMillis + timeOnInMs;
      }
    }
  }

  // Check if it's time to turn off any relays
  for (int i = 1; i < 6; ++i) {
    if (relayActivationTime[i] != 0 && currentMillis >= relayActivationTime[i]) {
      digitalWrite(relayPins[i], LOW);  // Turn off the relay
      relayActivationTime[i] = 0;       // Reset the activation time
    }
  }
}
