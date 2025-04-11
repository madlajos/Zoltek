// Pin Definitions (same as original, plus relay)
#define STEP_PIN 0   // PUL+ connected to Arduino Pin 9
#define DIR_PIN 1    // DIR+ connected to Arduino Pin 8
#define ENA_PIN 0    // ENA+ connected to Arduino Pin 7 (optional)
#define RELAY_PIN 4  // Relay control pin

// Movement Configuration
const long steps_per_revolution = 10000;  // 10,000 steps for full 360-degree rotation
const int max_pulse_delay_us = 1000;      // Slowest pulse delay
const int min_pulse_delay_us = 400;       // Fastest pulse delay
const int accel_steps = 100;              // Number of steps for acceleration/deceleration

// Command Queue
const int COMMAND_QUEUE_SIZE = 10;
struct Command {
  float degrees;
  bool clockwise;
};
Command commandQueue[COMMAND_QUEUE_SIZE];
int queueStart = 0; // Start index of the queue
int queueEnd = 0;   // End index of the queue
bool isMoving = false;

// State Variables for Current Move
long totalSteps = 0;
long currentStep = 0;
bool moveClockwise = true;
long accelEnd = 0;
long decelStart = 0;
bool stepPhaseHigh = true;
int pulseDelayUs = max_pulse_delay_us;
unsigned long lastPhaseTime = 0;

// Relay State
bool relayState = false;

// Global variable to accumulate fractional step errors.
float leftoverFraction = 0.0;

// -----------------------------------------------------------------------------
// Setup
// -----------------------------------------------------------------------------
void setup() {
  pinMode(STEP_PIN, OUTPUT);
  pinMode(DIR_PIN, OUTPUT);
  pinMode(ENA_PIN, OUTPUT);
  pinMode(RELAY_PIN, OUTPUT);
  digitalWrite(ENA_PIN, LOW);  // Enable motor driver (active LOW)
  digitalWrite(RELAY_PIN, LOW); // Relay OFF by default
  Serial.begin(115200);
}

// -----------------------------------------------------------------------------
// Main Loop
// -----------------------------------------------------------------------------
void loop() {
  if (isMoving) {
    handleMotorMovement();
  } else if (!isQueueEmpty()) {
    startNextCommand();
  }
  handleSerial();
}

// -----------------------------------------------------------------------------
// Handle Serial Input
// -----------------------------------------------------------------------------
void handleSerial() {
  if (Serial.available() > 0) {
    String command = Serial.readStringUntil('\n');
    command.trim();

    // Handle relay commands
    if (command.startsWith("RELAY,")) {
      handleRelayCommand(command);
      return;
    }

    // Handle relay query command "RELAY?"
    if (command == "RELAY?") {
      // Reply with "1" if relayState is true (ON) and "0" otherwise.
      Serial.println(relayState ? "1" : "0");
      Serial.flush();  
      return;
    }

    // Identify device
    if (command == "IDN?") {
      Serial.println("TTBL");
      return;
    }

    // Enqueue movement commands
    if (command.indexOf(',') != -1) {
      int commaIndex = command.indexOf(',');
      float degreeMove = command.substring(0, commaIndex).toFloat();
      int direction = command.substring(commaIndex + 1).toInt();

      if (degreeMove >= 0 && (direction == 0 || direction == 1)) {  
        if (degreeMove == 0) {
          Serial.println("DONE"); // Immediately acknowledge 0,0 commands
          Serial.flush();
        } else {
          enqueueCommand(degreeMove, direction == 1);
        }
      } else {
        Serial.println("ERR: Invalid movement command format");
      }
      return;
    }

    // Unknown command
    Serial.println("ERR: Unknown Command");
  }
}

// -----------------------------------------------------------------------------
// Command Queue Functions
// -----------------------------------------------------------------------------
bool isQueueEmpty() {
  return queueStart == queueEnd;
}

bool isQueueFull() {
  return (queueEnd + 1) % COMMAND_QUEUE_SIZE == queueStart;
}

void enqueueCommand(float degrees, bool clockwise) {
  if (isQueueFull()) {
    Serial.println("ERR: Command Queue Full");
    return;
  }
  commandQueue[queueEnd] = {degrees, clockwise};
  queueEnd = (queueEnd + 1) % COMMAND_QUEUE_SIZE;
  // Serial.println("CMD: Command enqueued");
}

void startNextCommand() {
  if (isQueueEmpty()) {
    return;
  }

  Command cmd = commandQueue[queueStart];
  queueStart = (queueStart + 1) % COMMAND_QUEUE_SIZE;


  // Handle the case where degrees == 0
  if (cmd.degrees == 0) {
    Serial.println("DONE");
    Serial.flush();
    return;
  }

  // Start the move
  totalSteps = mapDegreesToSteps(cmd.degrees);
  currentStep = 0;
  moveClockwise = cmd.clockwise;
  accelEnd = accel_steps;
  decelStart = totalSteps - accel_steps;
  stepPhaseHigh = true;
  pulseDelayUs = max_pulse_delay_us;
  lastPhaseTime = micros();
  digitalWrite(DIR_PIN, moveClockwise ? HIGH : LOW);
  isMoving = true;

  //Serial.print("CMD: Started move for ");
  //Serial.print(cmd.degrees, 1);
  //Serial.println(cmd.clockwise ? " CW" : " CCW");
}

// -----------------------------------------------------------------------------
// Handle Motor Movement
// -----------------------------------------------------------------------------
void handleMotorMovement() {
  if (currentStep >= totalSteps) {
    isMoving = false;

    // Ensure previous serial messages are flushed
    Serial.flush();
    delay(200);  // Small delay to stabilize output

    // Send "DONE" as a single clean message
    Serial.println("DONE");
    Serial.flush(); 
    return;
  }

  unsigned long now = micros();
  if ((now - lastPhaseTime) < (unsigned long)pulseDelayUs) {
    return;
  }

  if (stepPhaseHigh) {
    digitalWrite(STEP_PIN, HIGH);
    stepPhaseHigh = false;
  } else {
    digitalWrite(STEP_PIN, LOW);
    currentStep++;

    if (currentStep < accelEnd) {
      pulseDelayUs = max_pulse_delay_us -
                     ((max_pulse_delay_us - min_pulse_delay_us) * currentStep / accel_steps);
    } else if (currentStep >= decelStart) {
      long decelStepsDone = currentStep - decelStart;
      pulseDelayUs = min_pulse_delay_us +
                     ((max_pulse_delay_us - min_pulse_delay_us) * decelStepsDone / accel_steps);
    } else {
      pulseDelayUs = min_pulse_delay_us;
    }
    stepPhaseHigh = true;
  }
  lastPhaseTime = now;
}

// -----------------------------------------------------------------------------
// Relay Control
// -----------------------------------------------------------------------------
void handleRelayCommand(const String &command) {
  int commaPos = command.indexOf(',');
  String relayValue = command.substring(commaPos + 1);

  if (relayValue == "0" || relayValue == "1") {
    relayState = (relayValue == "1");
    digitalWrite(RELAY_PIN, relayState ? HIGH : LOW);
    //Serial.print("RELAY: ");
    //Serial.println(relayState ? "1" : "0");
    //Serial.flush(); 

    delay(200);
  } else {
    Serial.println("ERR: Invalid relay command format");
    Serial.flush(); 
  }
}

// -----------------------------------------------------------------------------
// Convert Degrees to Steps with Fractional Accumulation
// -----------------------------------------------------------------------------
long mapDegreesToSteps(float degrees) {
  // Compute the exact number of steps as a floating point value.
  float exactSteps = degrees * steps_per_revolution / 360.0;
  // Add any leftover fraction from previous conversions.
  exactSteps += leftoverFraction;
  // Extract the whole number of steps.
  long wholeSteps = (long)exactSteps;
  // Store the fractional remainder.
  leftoverFraction = exactSteps - wholeSteps;
  return wholeSteps;
}
