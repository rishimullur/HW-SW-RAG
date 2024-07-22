#include <Arduino.h>

// Pin definitions
#define EN_PIN    6 // Enable pin
#define DIR_PIN   3 // Direction pin
#define STEP_PIN  2 // Step pin

// Motor configuration
#define STEPS_PER_REV 200   // Steps per revolution for your motor
#define MICROSTEPS    16    // Microstep setting on your TMC2209

// Movement parameters
#define MOTOR_SPEED   5000  // Steps per second (increased from 1000)

// Timing calculations
unsigned long stepInterval = 1000000 / MOTOR_SPEED; // Microseconds between steps
unsigned long lastStepTime = 0;

void setup() {
  // Set pin modes
  pinMode(EN_PIN, OUTPUT);
  pinMode(DIR_PIN, OUTPUT);
  pinMode(STEP_PIN, OUTPUT);
  
  // Initialize pins
  digitalWrite(EN_PIN, LOW);  // Enable driver (LOW active)
  digitalWrite(DIR_PIN, LOW); // Set direction (choose LOW or HIGH based on desired direction)
  digitalWrite(STEP_PIN, LOW);
  
  // Initialize serial communication for debugging
  Serial.begin(115200);
  Serial.println("Motor Control System Initialized");
}

void loop() {
  unsigned long currentTime = micros();
  
  // Check if it's time for the next step
  if (currentTime - lastStepTime >= stepInterval) {
    lastStepTime = currentTime;
    
    // Toggle step pin
    digitalWrite(STEP_PIN, HIGH);
    delayMicroseconds(10); // Short delay for pulse width
    digitalWrite(STEP_PIN, LOW);
  }
}
