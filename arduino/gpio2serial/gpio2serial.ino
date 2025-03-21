/*
  DigitalReadSerial

  Reads a digital input on pin 2, prints the result to the Serial Monitor

  This example code is in the public domain.

  https://www.arduino.cc/en/Tutorial/BuiltInExamples/DigitalReadSerial
*/
#include <util/atomic.h>

#define MAX_CAMS 4
int nCams = MAX_CAMS;
// digital pin 2 has a pushbutton attached to it. Give it a name:
// Using no PWM pins
byte cams[] = {2,4,7,8};
// Using PWM pins
byte leds[] = {3,5,6,9};
byte states[] = {0,0,0,0};
byte currentCam = 0;
bool fromInput = false;

// the setup routine runs once when you press reset:
void setup() {
  // initialize serial communication at 9600 bits per second:
  Serial.begin(9600);
  // make the pushbutton's pin an input:
  for (int i = 0;i < nCams;i++) {
    pinMode(cams[i],INPUT);
    pinMode(leds[i],OUTPUT);
    digitalWrite(leds[i],states[i]);
  }
}

// the loop routine runs over and over again forever:
void loop() {
  // read the input pin:
    for (int i = 0;i < nCams;i++) {
      states[i] = digitalRead(cams[i]);
  }
  serialRead();
  stateMachine();
  delay(10);  // delay in between reads for stability
}


void stateMachine() {
  
    byte newCam = 0;
    byte pressedCams = 0;
    byte oldCam = currentCam;
    for (int i = 0;i < nCams;i++) {
      newCam = i + 1;
      if (states[i] == 1 && currentCam != newCam && pressedCams == 0) {
        pressedCams++;
        currentCam = newCam;
        for (int l = 0;l < nCams;l++) {

          digitalWrite(leds[l],states[l]);
        }
        if (!fromInput) Serial.print(currentCam);
        fromInput = false;
      }
    
    }
}

void serialRead() {
  if (Serial.available()) {
    Serial.setTimeout(0);
    String byteRead = Serial.readString();
    byteRead.trim();
    char msg = byteRead.charAt(0);
    byteRead.remove(0,1);
    int number = byteRead.toInt();
    fromInput= true;
    switch (msg) {
      case 'C':
    for (int i = 0;i < nCams;i++) {
      if (i == number - 1) {
        states[i] = 1;

      } else {
        states[i] = 0;
      }
    }
        break;

      case 'N':
        for (int l = 0;l < MAX_CAMS;l++) {

          digitalWrite(leds[l],LOW);
        }
        nCams = number;

        if (0 <= currentCam - 1 && currentCam - 1 < nCams) {

          digitalWrite(leds[currentCam - 1],HIGH);
        }
        break;
    }
    Serial.setTimeout(1000); // default
  }
  

}

