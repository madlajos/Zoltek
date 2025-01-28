// Pin Definitions (same as original, plus relay)
#define STEP_PIN 6   // PUL+ connected to Arduino Pin 9
#define DIR_PIN 7    // DIR+ connected to Arduino Pin 8
#define ENA_PIN 0    // ENA+ connected to Arduino Pin 7 (optional)
#define RELAY_PIN 2  // Relay control pin

// Movement Configuration (exactly as in your original)
const long steps_per_revolution = 10000;  // 10,000 steps for full 360-degree rotation
const int max_pulse_delay_us = 1000;      // Slowest pulse delay
const int min_pulse_delay_us = 200;       // Fastest pulse delay
const int accel_steps = 100;              // Number of steps for acceleration/deceleration

// --- Motor State Variables ---
bool isMoving = false;         // Whether the motor is currently moving
long totalSteps = 0;           // How many total steps we want to move
long currentStep = 0;          // Steps completed so far in this move
bool moveClockwise = true;     // Direction of the motor movement

// For acceleration/deceleration
long accelEnd = 0;             // last step index where we accelerate
long decelStart = 0;           // first step index where we decelerate

// Each step is split into two phases (HIGH then LOW)
// so that one step takes 2 * pulse_delay_us total
bool stepPhaseHigh = true;     // Are we currently in the "HIGH" portion of the step?
int pulseDelayUs = max_pulse_delay_us; // current pulse delay for half-step
unsigned long lastPhaseTime = 0;       // micros() at which we changed phase

// --- Relay State Variable ---
bool relayState = false;  // Track the relay state (false = OFF, true = ON)

// -----------------------------------------------------------------------------
// Setup
// -----------------------------------------------------------------------------
void setup() {
  // Initialize pins
  pinMode(STEP_PIN, OUTPUT);
  pinMode(DIR_PIN, OUTPUT);
  pinMode(ENA_PIN, OUTPUT);
  pinMode(RELAY_PIN, OUTPUT);

  // Enable the driver (active LOW)
  digitalWrite(ENA_PIN, LOW);

  // Relay OFF by default
  digitalWrite(RELAY_PIN, LOW);

  // Initialize serial
  Serial.begin(115200);
}

// -----------------------------------------------------------------------------
// Main Loop
// -----------------------------------------------------------------------------
void loop() {
  // 1) Handle motor movement in a non-blocking fashion
  if (isMoving) {
    handleMotorMovement();
  }

  // 2) Handle any incoming serial commands
  handleSerial();
}

// -----------------------------------------------------------------------------
// Handle incoming serial data
// -----------------------------------------------------------------------------
void handleSerial() {
  if (Serial.available() > 0) {
    String command = Serial.readStringUntil('\n'); // Read input until newline
    command.trim();                                // Remove leading/trailing whitespace

    // Handle relay control commands
    if (command.startsWith("RELAY,")) {
      int commaPos = command.indexOf(',');
      String relayValue = command.substring(commaPos + 1);

      if (relayValue == "0" || relayValue == "1") {
        setRelay(relayValue.toInt() == 1);
        Serial.print("RELAY: ");
        Serial.println(relayState ? "1" : "0");
      } else {
        Serial.println("ERR: Invalid relay command format (use RELAY,0 or RELAY,1)");
      }
      return;
    }

    // Handle relay state query
    if (command == "RELAY?") {
      Serial.println(relayState ? "1" : "0");
      return;
    }

    // Handle device identification
    if (command == "IDN?") {
      Serial.println("TTBL");
      return;
    }

    // Handle movement commands like "50.1,1" (CW) or "50.1,0" (CCW)
    if (command.indexOf(',') != -1) {
      int commaIndex = command.indexOf(',');
      float degreeMove = command.substring(0, commaIndex).toFloat();
      int direction = command.substring(commaIndex + 1).toInt();

      if (degreeMove > 0 && (direction == 0 || direction == 1)) {
        bool clockwise = (direction == 1);
        moveTurntable(degreeMove, clockwise);
      } else {
        Serial.println("ERR: Invalid movement command format");
      }
      return;
    }

    // Handle unknown commands
    Serial.println("ERR: Unknown Command");
  }
}

// -----------------------------------------------------------------------------
// Initiate a turntable move (relative degrees), non-blocking
// -----------------------------------------------------------------------------
void moveTurntable(float degrees, bool clockwise) {
  if (isMoving) {
    Serial.println("ERR: Motor is already moving");
    return;
  }

  // Convert degrees to steps
  totalSteps = mapDegreesToSteps(degrees);
  currentStep = 0;
  moveClockwise = clockwise;

  // Calculate where acceleration ends and deceleration begins
  accelEnd = accel_steps;
  decelStart = totalSteps - accel_steps; // if totalSteps < 2*accel_steps, logic still works

  // Set direction pin
  digitalWrite(DIR_PIN, moveClockwise ? HIGH : LOW);

  // Initialize the stepping state
  stepPhaseHigh = true;
  pulseDelayUs = max_pulse_delay_us;  // start with slow pulses (acceleration)
  lastPhaseTime = micros();

  // Begin movement
  isMoving = true;

  Serial.print("Moved ");
  Serial.print(degrees, 1); // Print with 1 decimal place for clarity
  Serial.print(clockwise ? " CW" : " CCW");
  Serial.println(" degrees.");
}

// -----------------------------------------------------------------------------
// Non-blocking "state machine" that replicates the original rotateMotor logic
// -----------------------------------------------------------------------------
void handleMotorMovement() {
  // Check if we've finished
  if (currentStep >= totalSteps) {
    isMoving = false;
    Serial.println("CMD: Movement complete");
    return;
  }

  // Check if it's time to transition to the next phase (HIGH->LOW or LOW->HIGH)
  unsigned long now = micros();
  if ((now - lastPhaseTime) < (unsigned long)pulseDelayUs) {
    return; // not enough time has passed yet
  }

  // Time to transition to the next phase
  if (stepPhaseHigh) {
    // We were LOW → we must go HIGH
    digitalWrite(STEP_PIN, HIGH);

    // Phase complete; next phase is going LOW
    stepPhaseHigh = false;
  } else {
    // We were HIGH → we must go LOW
    digitalWrite(STEP_PIN, LOW);

    // We have completed one full step: increment step counter
    currentStep++;

    // Recalculate pulse_delay_us for next step (accel/decel) - same logic as original
    if (currentStep < accelEnd) {
      // accelerating
      pulseDelayUs = max_pulse_delay_us - 
                     ((max_pulse_delay_us - min_pulse_delay_us) * currentStep / accel_steps);
    } 
    else if (currentStep >= decelStart) {
      // decelerating
      long decelStepsDone = currentStep - decelStart; 
      pulseDelayUs = min_pulse_delay_us + 
                     ((max_pulse_delay_us - min_pulse_delay_us) * decelStepsDone / accel_steps);
    } 
    else {
      // constant speed
      pulseDelayUs = min_pulse_delay_us;
    }

    // Next phase will be going HIGH again
    stepPhaseHigh = true;
  }

  // Update the time we changed phase
  lastPhaseTime = now;
}

// -----------------------------------------------------------------------------
// Convert degrees to steps (same as original)
// -----------------------------------------------------------------------------
long mapDegreesToSteps(float degrees) {
  return (long)(degrees * steps_per_revolution / 360.0);
}

// -----------------------------------------------------------------------------
// Turn the relay on/off
// -----------------------------------------------------------------------------
void setRelay(bool on) {
  relayState = on;
  digitalWrite(RELAY_PIN, on ? HIGH : LOW);
}
