"""Direct compatibility example: connect a suitable servo driver before running."""

import time

import board
from adafruit_motor.servo import Servo

from adafruit_blinka_raspberry_pi_pwm import PWMOut

with PWMOut(board.D18, frequency=50) as output:
    servo = Servo(output)
    for angle in (45, 90, 135, 90):
        servo.angle = angle
        time.sleep(1)
    servo.angle = None
