#include <Arduino.h>

// Define the PWM pin
const int pwm10 = 10;

void setup() {
  // Initialize serial communication at 115200 baud rate
  Serial.begin(115200);
  delay(50);  // Short delay to ensure the serial connection is established
  Serial.write("Setup started\n");
  
  // Set the PWM pin as an output
  pinMode(pwm10, OUTPUT);
}

void loop() {
  // Check if data is available to read from the serial port
  if (Serial.available() > 0) {
    // Read the incoming message as a String
    String msg = Serial.readString();
    
    // Convert the message to an integer
    int pwmValue = msg.toInt();

    // Check if the value is within the acceptable range (0 to 255)
    if (pwmValue >= 0 && pwmValue <= 255) {
      // Write the PWM value to the pin
      analogWrite(pwm10, pwmValue);
      Serial.print("PWM Value set to: ");
      Serial.println(pwmValue);
    } else {
      // Print an error message if the input is out of range
      Serial.println("Invalid PWM value. Please enter a number between 0 and 255.");
    }
  }
}