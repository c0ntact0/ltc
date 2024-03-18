/*
  DigitalReadSerial

  Reads a digital input on pin 2, prints the result to the Serial Monitor

  This example code is in the public domain.

  https://www.arduino.cc/en/Tutorial/BuiltInExamples/DigitalReadSerial
*/
#include <util/atomic.h>

#define CAMS 4


// digital pin 2 has a pushbutton attached to it. Give it a name:
// Using no PWM pins
byte cams[CAMS] = {2,4,7,8};
// Using PWM pins
byte leds[CAMS] = {3,5,6,9};
byte states[CAMS] = {0,0,0,0};
byte currentCam = 0;

// the setup routine runs once when you press reset:
void setup() {
  // initialize serial communication at 9600 bits per second:
  Serial.begin(9600);
  // make the pushbutton's pin an input:
  for (int i = 0;i < CAMS;i++) {
    pinMode(cams[i],INPUT);
    pinMode(leds[i],OUTPUT);
    digitalWrite(leds[i],states[i]);
  }
}

// the loop routine runs over and over again forever:
void loop() {
  // read the input pin:
    for (int i = 0;i < sizeof(cams);i++) {
      states[i] = digitalRead(cams[i]);
  }
  stateMachine();
  delay(10);  // delay in between reads for stability
}


void stateMachine() {
  
    byte newCam = 0;
    byte pressedCams = 0;
    byte oldCam = currentCam;
    for (int i = 0;i < sizeof(states);i++) {
      newCam = i + 1;
      if (states[i] == 1 && currentCam != newCam && pressedCams == 0) {
        pressedCams++;
        currentCam = newCam;
        for (int l = 0;l < CAMS;l++) {

          digitalWrite(leds[l],states[l]);
        }
        Serial.print(currentCam);
      }
    
    }
}

