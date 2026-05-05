#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
EDES 301 – PocketBeagle LED Blink Program
Blink USR3 at 5 Hz using Adafruit_BBIO.

Author: Wyatt Armstrong
Course: EDES 301
Assignment: LED Blink Program
Date: 2026

Description:
    This program blinks the onboard USR3 LED at 5 Hz
    (5 full on/off cycles per second). It uses the
    Adafruit_BBIO.GPIO library to access the LED class
    driver exposed under /sys/class/leds.

License:
    MIT License

    Permission is hereby granted, free of charge, to any person obtaining a copy
    of this software and associated documentation files (the "Software"), to deal
    in the Software without restriction, including without limitation the rights
    to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
    copies of the Software, and to permit persons to whom the Software is
    furnished to do so, subject to the following conditions:

    The above copyright notice and this permission notice shall be included in all
    copies or substantial portions of the Software.

    THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND.

"""

# Python 2/3 compatible input handling
try:
    raw_input
except NameError:
    raw_input = input

import Adafruit_BBIO.GPIO as GPIO
import time

# Setup USR3 as output
GPIO.setup("USR3", GPIO.OUT)

# 5 Hz blink = 5 cycles/second
# One cycle = ON + OFF = 0.2 s
# Therefore ON = 0.1 s and OFF = 0.1 s for exactly 5 Hz
FREQUENCY = 5.0
HALF_PERIOD = 1.0 / (2.0 * FREQUENCY)  # 0.1 seconds

print("Blinking USR3 at 5 Hz. Press CTRL+C to stop.")

try:
    while True:
        GPIO.output("USR3", GPIO.HIGH)
        time.sleep(HALF_PERIOD)
        GPIO.output("USR3", GPIO.LOW)
        time.sleep(HALF_PERIOD)

except KeyboardInterrupt:
    print("\nStopping LED blink.")
    GPIO.output("USR3", GPIO.LOW)