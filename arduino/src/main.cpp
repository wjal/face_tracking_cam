#include <Arduino.h>
#include <Servo.h>
// put function declarations here:
#define SERVO_MAX       180
#define SERVO_MIN       0
#define pan_servo_pin   9
#define tilt_servo_pin  10
#define FRAME_WIDTH     720
#define FRAME_HEIGHT    680
#define X_ANGLE_START   110
#define Y_ANGLE_START   10
  // put your main code here, to run repeatedly:
char incomingByte = 0; // for incoming serial data
char dump = 0;
uint16_t x_coord = 0;
uint16_t y_coord = 0;
char g_buff[128];

uint16_t x_mid = FRAME_WIDTH/2;
uint16_t y_mid = FRAME_HEIGHT/2;
int16_t pan_servo_angle = X_ANGLE_START;
int16_t tilt_servo_angle = Y_ANGLE_START;
int16_t tilt_move = 0;
int16_t pan_move = 0;

Servo tilt_servo;
Servo pan_servo;

void setup() {
  Serial.begin(9600); // opens serial port, sets data rate to 9600 bps
  Serial.println("Setting up....");
  pan_servo.attach(pan_servo_pin);
  tilt_servo.attach(tilt_servo_pin);
  pan_servo.write(X_ANGLE_START);
  tilt_servo.write(Y_ANGLE_START);
  Serial.println("Setup complete.");
}

void loop() {
    if (Serial.available() >= 5) {
        if (Serial.read() == 0xFF) {
            uint8_t xLow = Serial.read();
            uint8_t xHigh = Serial.read();
            uint8_t yLow = Serial.read();
            uint8_t yHigh = Serial.read();
            
            x_coord = xLow | (xHigh << 8);
            y_coord = yLow | (yHigh << 8);
            

          if(x_coord > (x_mid + 35) || x_coord < (x_mid - 35)){
            pan_move = (int)(((float)((int16_t)x_coord - (int16_t)x_mid) / x_mid) * 12) + 1;
            pan_servo_angle-=pan_move;
            if(pan_servo_angle > SERVO_MAX){
              pan_servo_angle = SERVO_MAX;
            }else if(pan_servo_angle < SERVO_MIN){
              pan_servo_angle = SERVO_MIN;
            }
          }
            
          if(y_coord > (y_mid + 35) || y_coord < (y_mid - 35)){
            tilt_move = (int)(((float)((int16_t)y_coord - (int16_t)y_mid) / y_mid) * 12) + 1;
            tilt_servo_angle+=tilt_move;
            if(tilt_servo_angle > SERVO_MAX){
              tilt_servo_angle = SERVO_MAX;
            }else if(tilt_servo_angle < SERVO_MIN){
              tilt_servo_angle = SERVO_MIN;
            }
          }
          pan_servo.write(pan_servo_angle);
          tilt_servo.write(tilt_servo_angle);
          sprintf(g_buff, "pan angle: %d tilt: %d\n", pan_servo_angle, tilt_servo_angle);
          Serial.print(g_buff);
        }
    }
}
