/*
  DigitalReadSerial

  Reads a digital input on pin 2, prints the result to the Serial Monitor

  This example code is in the public domain.

  https://www.arduino.cc/en/Tutorial/BuiltInExamples/DigitalReadSerial
*/
#include <util/atomic.h>

int nCams = 4;
// digital pin 2 has a pushbutton attached to it. Give it a name:
// Using no PWM pins
byte cams[] = {2,4,7,8};
// Using PWM pins
byte leds[] = {3,5,6,9};
byte states[] = {0,0,0,0};
byte currentCam = 0;
bool fromInput = false;
char msg = NULL;

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
    char byteRead = Serial.read();

    if (isAlpha(byteRead)) {
      msg = byteRead;
    } else {
    
    int number = byteRead - '0';
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
        nCams = number;
        break;
    }
    msg = NULL;
  }
  }

}

