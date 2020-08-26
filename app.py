#!/usr/bin/env python
from importlib import import_module
from flask import Flask, render_template, Response, request
from camera_pi import Camera    
from time import sleep
#either run "sudo pigpiod" after each boot, or add the first part of the output of "whereis pigpiod" to the su crontab (by running "sudo crontab -e) after a "@reboot" so that it starts automatically
import pigpio
import threaded

#17 and 18 correspond to pins 11 and 12, the 6th row counting down from the end with the SD card on an RPi Zero
PAN_PIN = 17
TILT_PIN = 18

SERVO_180_DEGREE_DUTY_CYCLE = 2500 #9g hobby servo should be 2500
SERVO_0_DEGREE_DUTY_CYCLE = 500 #9g hobby servo should be 500
TILT_MAX_DEGREES = 180 #the degrees depend on your pan/tilt rig's specs
TILT_MIN_DEGREES = 128
PAN_MAX_DEGREES = 180
PAN_MIN_DEGREES = 47

convertDegreeToDutyCycle = (SERVO_180_DEGREE_DUTY_CYCLE - SERVO_0_DEGREE_DUTY_CYCLE)/180 #the duty cycle interval length per single degree

pi = pigpio.pi()
pi.set_mode(TILT_PIN, pigpio.OUTPUT)
pi.set_mode(PAN_PIN, pigpio.OUTPUT)

#these grab the current pin duty cycles (if any)
try:
    setPan = pi.get_servo_pulsewidth(PAN_PIN)
    setTilt = pi.get_servo_pulsewidth(TILT_PIN)
except:
    setPan = 0
    setTilt = 0

#the delay between updating the servos' values (lower value means faster motion):
delayTime = 0.001

#the maximum duty cycle change per update cycle (higher value means faster motion, but also increased "jumpiness"):
jumpDist = 10

@threaded.Threaded #this thread checks for updated pan/tilt values, and shifts the servos over with minimal bounce
def updateServos():
    global setPan,setTilt
    while(True):
        actualPan = pi.get_servo_pulsewidth(PAN_PIN) #grab the actual value of the pan servo
        panGap = abs(actualPan - setPan)
        if setPan != actualPan:
            if actualPan > setPan:
                try:
                    pi.set_servo_pulsewidth(PAN_PIN, actualPan - min(panGap,jumpDist))
                except:
                    pass
            else:
                try:
                    pi.set_servo_pulsewidth(PAN_PIN, actualPan + min(panGap,jumpDist))
                except:
                    pass
        actualTilt = pi.get_servo_pulsewidth(TILT_PIN)
        tiltGap = abs(actualTilt - setTilt)
        if setTilt != actualTilt:
            if actualTilt > setTilt:
                try:
                    pi.set_servo_pulsewidth(TILT_PIN, actualTilt - min(tiltGap,jumpDist))
                except:
                    pass
            else:
                try:
                    pi.set_servo_pulsewidth(TILT_PIN, actualTilt + min(tiltGap,jumpDist))
                except:
                    pass
        sleep(delayTime)

updater = updateServos()
updater.start()

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html',
        maxTilt = str(TILT_MAX_DEGREES),minTilt = str(TILT_MIN_DEGREES),maxPan = str(PAN_MAX_DEGREES),minPan = str(PAN_MIN_DEGREES),initPan = str(round(setPan/convertDegreeToDutyCycle)),initTilt = str(round(setTilt/convertDegreeToDutyCycle)))


def gen(camera):
    while True:
        frame = camera.get_frame()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

@app.route('/video_feed')
def video_feed():
    return Response(gen(Camera()),
        mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route("/set_pan")
def set_pan():
    global setPan
    setPan = round(int(request.args.get("pan"))*convertDegreeToDutyCycle)
    print("Received " + str(setPan))
    return "Received " + str(setPan)
  
@app.route("/set_tilt")
def set_tilt():
    global setTilt
    setTilt = round(int(request.args.get("tilt"))*convertDegreeToDutyCycle)
    print("Received " + str(setTilt))
    return "Received " + str(setTilt)

if __name__ == '__main__':
    app.run(host='0.0.0.0', threaded=True)
