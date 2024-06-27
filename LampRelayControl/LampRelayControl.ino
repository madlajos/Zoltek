#include <Arduino.h>
#include <Adafruit_NeoPixel.h>

// Define the pins for the relays
const int relayPins[] = {2, 3, 4, 5, 6, 7};  // Array containing all relay pins

bool channelState[6] = {false};               // Initialize array to track the state of each channel
unsigned long relayActivationTime[6] = {0};  // Initialize array to track relay activation time
int lastActivatedChannel = -1;                // Initialize last activated channel variable

// NeoPixel LED settings
#define LED_PIN 28
#define NUM_LEDS 8

Adafruit_NeoPixel strip(NUM_LEDS, LED_PIN, NEO_GRB + NEO_KHZ800);

void setup() {
  // Initialize the relay pins as outputs
  for (int i = 0; i < sizeof(relayPins) / sizeof(relayPins[0]); i++) {
    pinMode(relayPins[i], OUTPUT);
    digitalWrite(relayPins[i], LOW);
  }

  // Initialize NeoPixel LED
  strip.begin();
  strip.show();  // Initialize all pixels to 'off'

  // Initialize serial communication
  Serial.begin(115200);  // Use Serial1 instead of SerialUSB
}

void loop() {
  // Check if Serial is available
  setLedColor(Serial ? 0 : 30, Serial ? 30 : 0, 0, 7);

  // Update LEDs 1-6 based on relay pin states
  for (int i = 0; i < sizeof(relayPins) / sizeof(relayPins[0]); i++) {
    // Determine LED color based on relay pin state
    uint8_t r = digitalRead(relayPins[i]) == HIGH ? 0 : 50;
    uint8_t g = digitalRead(relayPins[i]) == HIGH ? 50 : 0;

    // Set the color of the LED
    setLedColor(r, g, 0, i);
  }

  // Check if any relay needs to be turned off (time-controlled)
  unsigned long currentMillis = millis();  // Get the current time
  for (int i = 0; i < 6; ++i) {
    if (channelState[i] && relayActivationTime[i] != 0 && currentMillis >= relayActivationTime[i]) {
      digitalWrite(relayPins[i], LOW);  // Turn off the relay
      relayActivationTime[i] = 0;       // Reset the activation time
      channelState[i] = false;          // Update the channel state
      lastActivatedChannel = -1;        // Reset the last activated channel
    }
  }

  // Handle incoming commands
  while (Serial.available() > 0) {
    String command = Serial.readStringUntil('\n');  // Read the entire command until newline

    if (command.startsWith("IDN?")) {
      Serial.println("RPZERO");
    } else if (command.equals("1,0")) {
      for (int i = 0; i < 6; ++i) {
        if (channelState[i]) {
          digitalWrite(relayPins[i], LOW);  // Turn off the relay
          relayActivationTime[i] = 0;       // Reset the activation time
          channelState[i] = false;          // Update the channel state
        }
      }
      lastActivatedChannel = -1;            // Reset the last activated channel
    } else if (command.equals("LS?")) {
      int activeChannel = -1;
      for (int i = 0; i < 6; ++i) {
        if (channelState[i]) {
          activeChannel = i + 1;  // Channel numbers are 1-based
          break;
        }
      }
      Serial.println(activeChannel);
    } else {
      int commaIndex = command.indexOf(',');
      if (commaIndex != -1) {
        // Extract relayNumber and timeOnInMs from the command
        int relayNumber = command.substring(0, commaIndex).toInt();
        int timeOnInMs = command.substring(commaIndex + 1).toInt();

        // If a channel is already on
        if (lastActivatedChannel != -1) {
          // Turn off all channels
          for (int i = 0; i < 6; ++i) {
            if (channelState[i]) {
              digitalWrite(relayPins[i], LOW);  // Turn off the relay
              relayActivationTime[i] = 0;       // Reset the activation time
              channelState[i] = false;          // Update the channel state
            }
          }
          // Reset lastActivatedChannel if the new request is the same as the one which is already on
          if (lastActivatedChannel == relayNumber) {
            lastActivatedChannel = -1;
            continue;  // Do nothing and skip processing the command
          }
        }

        // Activate the new channel and record the activation time
        digitalWrite(relayPins[relayNumber - 1], HIGH);
        relayActivationTime[relayNumber - 1] = millis() + timeOnInMs;
        channelState[relayNumber - 1] = true;  // Update the channel state
        lastActivatedChannel = relayNumber;    // Update the last activated channel
      }
    }
  }
}

void setLedColor(uint8_t r, uint8_t g, uint8_t b, int ledIndex) {
  strip.setPixelColor(ledIndex, r, g, b);  // Set the color of the specified LED
  strip.show();
}
