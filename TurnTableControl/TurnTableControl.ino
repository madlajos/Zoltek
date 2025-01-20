// Pin Definitions
#define STEP_PIN 9   // PUL+ connected to Arduino Pin 9
#define DIR_PIN 8    // DIR+ connected to Arduino Pin 8
#define ENA_PIN 7    // ENA+ connected to Arduino Pin 7 (optional)

// Movement Configuration
const long steps_per_revolution = 10000;  // 10,000 steps for a full 360-degree rotation
const int max_pulse_delay_us = 1000;      // Slowest pulse delay
const int min_pulse_delay_us = 200;       // Fastest pulse delay
const int accel_steps = 100;              // Number of steps for acceleration/deceleration

void setup() {
  // Initialize pins
  pinMode(STEP_PIN, OUTPUT);
  pinMode(DIR_PIN, OUTPUT);
  pinMode(ENA_PIN, OUTPUT);

  // Enable the driver (active LOW)
  digitalWrite(ENA_PIN, LOW);

  // Initialize serial communication
  Serial.begin(115200);
}

void loop() {
  if (Serial.available() > 0) {
    String command = Serial.readStringUntil('\n');  // Read input until newline
    command.trim();  // Remove any whitespace or newlines

    // Identify device
    if (command == "IDN?") {
      Serial.println("TTBL");
    }
    // Handle movement commands like "50,1" (CW) or "50,0" (CCW)
    else if (command.indexOf(',') != -1) {
      int commaIndex = command.indexOf(',');
      int degreeMove = command.substring(0, commaIndex).toInt();
      int direction = command.substring(commaIndex + 1).toInt();

      if (degreeMove > 0 && (direction == 0 || direction == 1)) {
        bool clockwise = (direction == 1);  // Determine direction based on 1 or 0
        moveTurntable(degreeMove, clockwise);
      } else {
        Serial.println("ERR: Invalid command format");
      }
    }
    // Unknown command
    else {
      Serial.println("ERR: Unknown Command");
    }
  }
}

// Function to check if the command format is valid (e.g., "20CW", "45CCW")
bool isValidMoveCommand(String cmd) {
  if (cmd.length() < 3) return false;
  String direction = cmd.substring(cmd.length() - 2);
  return (direction == "CW" || direction == "CCW") && isDigit(cmd[0]);
}

// Function to move turntable by a relative degree amount
void moveTurntable(int degrees, bool clockwise) {
  long steps_to_move = mapDegreesToSteps(degrees);

  rotateMotor(steps_to_move, clockwise);
  Serial.print("Moved ");
  Serial.print(degrees);
  Serial.print(clockwise ? " CW" : " CCW");
  Serial.println(" degrees.");
}


// Function to convert degrees to steps
long mapDegreesToSteps(int degrees) {
  return (long)degrees * steps_per_revolution / 360;
}
// Function to rotate the motor with acceleration/deceleration
void rotateMotor(long steps, bool clockwise) {
  digitalWrite(DIR_PIN, clockwise ? HIGH : LOW);

  long accel_end = accel_steps;
  long decel_start = steps - accel_steps;

  for (long i = 0; i < steps; i++) {
    int pulse_delay_us;

    if (i < accel_end) {
      pulse_delay_us = max_pulse_delay_us - 
                       ((max_pulse_delay_us - min_pulse_delay_us) * i / accel_steps);
    } else if (i >= decel_start) {
      pulse_delay_us = min_pulse_delay_us + 
                       ((max_pulse_delay_us - min_pulse_delay_us) * (i - decel_start) / accel_steps);
    } else {
      pulse_delay_us = min_pulse_delay_us;
    }

    digitalWrite(STEP_PIN, HIGH);
    delayMicroseconds(pulse_delay_us);
    digitalWrite(STEP_PIN, LOW);
    delayMicroseconds(pulse_delay_us);
  }
}
