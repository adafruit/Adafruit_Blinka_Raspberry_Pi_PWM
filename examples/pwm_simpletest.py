"""Fade an LED connected through a suitable series resistor to GPIO 18."""

import time

import board

from adafruit_blinka_raspberry_pi_pwm import PWMOut

with PWMOut(board.D18, frequency=500) as output:
    while True:
        for duty_cycle in range(0, 65536, 1024):
            output.duty_cycle = duty_cycle
            time.sleep(0.02)
        for duty_cycle in range(65535, -1, -1024):
            output.duty_cycle = duty_cycle
            time.sleep(0.02)
