#!/usr/bin/env python3
import serial
import struct
import cv2 as cv
from picamera2 import Picamera2
import numpy as np
from datetime import datetime

width = 720
height = 680

# Initialize the serial port
# Use '/dev/serial0' as a universal alias across different Raspberry Pi models
ser = serial.Serial(
    port='/dev/serial0',
    baudrate=9600,
    parity=serial.PARITY_NONE,
    stopbits=serial.STOPBITS_ONE,
    bytesize=serial.EIGHTBITS,
    timeout=1
)


position=(30,40)
font=cv.FONT_HERSHEY_PLAIN
text_height=1.5
colour=(0,242,5)
weight=2
line=cv.LINE_AA
rec_colour=(20,30,200)
box_thickness=7

#center pixel
pixel_x = int(width/2)
pixel_y = int(height/2)


picam2 = Picamera2()
picam2.configure(picam2.create_preview_configuration(main={"size":(width,height), "format": "BGR888"},controls={"FrameRate":30}))
picam2.start()

frame = picam2.capture_array()
frame_height, frame_width = frame.shape[:2]  # numpy shape is (height, width, channels)
out_mp4 = cv.VideoWriter("face_track_proto.mp4", cv.VideoWriter_fourcc(*"mp4v"), 10, (frame_width, frame_height))

box_height = 1
box_width = 1
x_pos=1
y_pos=1

#used temp
x = 90
y = 90

face_cascade = cv.CascadeClassifier('./data/haarcascade_frontalface_default.xml')
eye_cascade = cv.CascadeClassifier('./data/haarcascade_eye.xml')

resize_dimensions = (int(width/4),int(height/4))
total=1
calc=1
try:
    while True:
        start = datetime.now()
        frame = picam2.capture_array()
        frame_gray = cv.cvtColor(frame, cv.COLOR_BGR2GRAY)
        #frame_gray = cv.resize(frame_gray_pre, resize_dimensions)
        faces = face_cascade.detectMultiScale(frame_gray, 1.3, 5)
        

        calc = (.9 * calc) + (0.1 * (1.0 / total))
        text = f"fps={int(calc)} loop_time={total}"
        cv.imshow('FRAME', frame_gray)
        cv.putText(frame, text, position, font, text_height, colour, weight, line)
        if cv.waitKey(1) == ord('q'):
            break
        #for face in faces:
        if len(faces) > 0:
            x,y,w,h=faces[0]
            cv.rectangle(frame, (x,y), (x+w, y+h),(0,0,255),3)
            message = ser.write(struct.pack('<BHH', 0xFF,  int((x)+(w/2)), int((y)+(h/2))))
            roi_gray = frame_gray[y:y+h,x:x+w]
            eyes = eye_cascade.detectMultiScale(roi_gray, 2.25, 25)

            #for eye in eyes:
                #### these lines need to be rechecked
                #e_x,e_y,e_w,e_h=eye
                #these lines need to be checked
                #cv.rectangle(frame, (e_x+x,e_y+y), (x+e_x+e_w, y+e_y+e_h),(0,0,255),3)
        cv.imshow("Camera", frame)
        out_mp4.write(frame)
        total = (datetime.now() - start).total_seconds()
except KeyboardInterrupt:
    pass
finally:
    ser.close() # Always close the port when finished
    cv.destroyAllWindows()
    out_mp4.release()
    picam2.stop()
    print("\nExiting Program")