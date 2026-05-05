#!/usr/bin/env python3.11
# pump_test.py
# Wyatt Armstrong - EDES 301 - 2026
#
# Quick test to make sure the pump and MOSFET wiring works.
# Turns pump on for 5 seconds then off.
#
# Run: sudo python3.11 pump_test.py

import Adafruit_BBIO.GPIO as GPIO
import time

PUMP_PIN = "P1_34"

GPIO.setup(PUMP_PIN, GPIO.OUT)
GPIO.output(PUMP_PIN, GPIO.LOW)

print("Pump ON")
GPIO.output(PUMP_PIN, GPIO.HIGH)
time.sleep(5)

print("Pump OFF")
GPIO.output(PUMP_PIN, GPIO.LOW)

GPIO.cleanup()
