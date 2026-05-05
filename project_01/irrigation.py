#!/usr/bin/env python3.11
# irrigation.py
# Wyatt Armstrong - EDES 301 - 2026
#
# Automatic plant watering system for PocketBeagle.
# Reads soil moisture, reservoir level, and ambient temp/humidity,
# then waters the plant on a schedule based on the plant type.
#
# Wiring:
#   P1.02  - water sensor (ADC via TXS0108E)
#   P1.14  - 3.3V for all sensors
#   P1.16  - GND
#   P1.18  - TXS0108E VA (1.8V ref)
#   P1.24  - 5V for pump
#   P1.26  - I2C SDA (soil sensor, LCD, BME280)
#   P1.28  - I2C SCL
#   P1.34  - pump gate via TXS0108E
#
# Run: sudo python3.11 irrigation.py
# Type RUN and press Enter to manually trigger the pump for 1 second.

import time
import os
import smbus2
import struct
import threading
from RPLCD.i2c import CharLCD

# pin and address config
PUMP_GPIO  = "26"
WATER_ADC  = "/sys/bus/iio/devices/iio:device0/in_voltage6_raw"
ADC_MAX    = 4095.0
BME_ADDR   = 0x76
SOIL_ADDR  = 0x36
I2C_BUS    = 2

# water sensor calibration - tune these to your reservoir
WATER_RAW_FULL  = 0.28
WATER_RAW_EMPTY = 0.05

# plant profiles
# moisture_min/max are raw sensor values in soil
# water_threshold is the moisture % below which watering starts
# water_cooldown is seconds between waterings (base value)
PLANTS = {
    "succulent": {
        "moisture_min":    200,
        "moisture_max":    380,
        "moisture_over":   520,
        "moisture_std":    50,
        "temp_min":        10,
        "temp_max":        35,
        "humidity_min":    10,
        "humidity_max":    50,
        "water_duration":  3,
        "water_cooldown":  86400,
        "water_threshold": 30,
    },
    "flower": {
        "moisture_min":    200,
        "moisture_max":    500,
        "moisture_over":   600,
        "moisture_std":    75,
        "temp_min":        15,
        "temp_max":        30,
        "humidity_min":    40,
        "humidity_max":    70,
        "water_duration":  3,
        "water_cooldown":  43200,
        "water_threshold": 40,
    },
    "vegetable": {
        "moisture_min":    220,
        "moisture_max":    520,
        "moisture_over":   650,
        "moisture_std":    80,
        "temp_min":        10,
        "temp_max":        32,
        "humidity_min":    50,
        "humidity_max":    80,
        "water_duration":  3,
        "water_cooldown":  21600,
        "water_threshold": 45,
    },
    "tropical": {
        "moisture_min":    250,
        "moisture_max":    550,
        "moisture_over":   680,
        "moisture_std":    90,
        "temp_min":        18,
        "temp_max":        35,
        "humidity_min":    60,
        "humidity_max":    90,
        "water_duration":  3,
        "water_cooldown":  28800,
        "water_threshold": 50,
    },
    "cactus": {
        "moisture_min":    200,
        "moisture_max":    350,
        "moisture_over":   480,
        "moisture_std":    40,
        "temp_min":        15,
        "temp_max":        40,
        "humidity_min":    5,
        "humidity_max":    40,
        "water_duration":  3,
        "water_cooldown":  172800,
        "water_threshold": 20,
    },
}

# change this to switch plant profiles
ACTIVE_PLANT  = "flower"
RESERVOIR_LOW = 0.20

# set by input thread when user types RUN
manual_run = False

def input_listener():
    global manual_run
    while True:
        try:
            if input().strip().upper() == "RUN":
                manual_run = True
                print("Manual run triggered")
        except:
            break

threading.Thread(target=input_listener, daemon=True).start()


# GPIO via sysfs
def gpio_setup(pin):
    if not os.path.exists("/sys/class/gpio/gpio{}".format(pin)):
        with open("/sys/class/gpio/export", "w") as f:
            f.write(pin)
    time.sleep(0.1)
    with open("/sys/class/gpio/gpio{}/direction".format(pin), "w") as f:
        f.write("out")
    gpio_write(pin, 0)

def gpio_write(pin, value):
    with open("/sys/class/gpio/gpio{}/value".format(pin), "w") as f:
        f.write(str(value))

def gpio_cleanup(pin):
    try:
        gpio_write(pin, 0)
    except:
        pass
    try:
        if os.path.exists("/sys/class/gpio/gpio{}".format(pin)):
            with open("/sys/class/gpio/unexport", "w") as f:
                f.write(pin)
    except:
        pass


# read reservoir level, returns 0.0 to 1.0
def get_water_level():
    try:
        with open(WATER_ADC, "r") as f:
            raw = int(f.read().strip()) / ADC_MAX
        return max(0.0, min(1.0, (raw - WATER_RAW_EMPTY) / (WATER_RAW_FULL - WATER_RAW_EMPTY)))
    except:
        return 0.0


# soil sensor uses seesaw I2C protocol
def get_soil_raw(bus, retries=3):
    for attempt in range(retries):
        try:
            bus.write_i2c_block_data(SOIL_ADDR, 0x0F, [0x10])
            time.sleep(0.005)
            raw = bus.read_i2c_block_data(SOIL_ADDR, 0x0F, 2)
            value = (raw[0] << 8) | raw[1]
            if value in (0, 65535):
                raise ValueError("bad read")
            return value
        except Exception as e:
            if attempt < retries - 1:
                time.sleep(0.2)
            else:
                print("Soil read error: {}".format(e))
                return None

def get_soil_temp(bus, retries=3):
    for attempt in range(retries):
        try:
            bus.write_i2c_block_data(SOIL_ADDR, 0x00, [0x04])
            time.sleep(0.001)
            raw = bus.read_i2c_block_data(SOIL_ADDR, 0x00, 4)
            return ((raw[0] << 24) | (raw[1] << 16) | (raw[2] << 8) | raw[3]) / 65536.0
        except Exception as e:
            if attempt < retries - 1:
                time.sleep(0.2)
            else:
                print("Soil temp error: {}".format(e))
                return None

# convert raw reading to 0-100% (>100 means overwatered)
def soil_to_pct(raw, plant):
    if raw is None:
        return None
    p = PLANTS[plant]
    if raw <= p["moisture_min"]:
        return 0.0
    elif raw >= p["moisture_over"]:
        return round(100.0 + (raw - p["moisture_over"]) / (p["moisture_over"] * 0.1) * 10, 1)
    else:
        return round(min((raw - p["moisture_min"]) / (p["moisture_max"] - p["moisture_min"]) * 100.0, 100.0), 1)

# shorten cooldown if soil is critically dry
def get_dynamic_cooldown(moist_pct, plant):
    p = PLANTS[plant]
    if moist_pct is None:
        return p["water_cooldown"]
    diff = (p["water_threshold"] - moist_pct) / 100.0 * (p["moisture_max"] - p["moisture_min"])
    stds = diff / p["moisture_std"] if p["moisture_std"] > 0 else 0
    if stds >= 2.0:
        return 900     # 15 min
    elif stds >= 1.0:
        return 1800    # 30 min
    return p["water_cooldown"]


# BME280 direct smbus2 driver - no adafruit library needed
class BME280:
    def __init__(self, bus, addr):
        self._bus = bus
        self._addr = addr
        self._load_cal()
        bus.write_byte_data(addr, 0xF2, 0x01)
        bus.write_byte_data(addr, 0xF4, 0x27)

    def _read(self, reg, length, retries=5):
        for i in range(retries):
            try:
                return self._bus.read_i2c_block_data(self._addr, reg, length)
            except:
                if i < retries - 1:
                    time.sleep(0.3)
                else:
                    raise

    def _load_cal(self):
        cal = self._read(0x88, 24)
        self.T1 = (cal[1] << 8) | cal[0]
        self.T2 = struct.unpack_from('<h', bytes(cal[2:4]))[0]
        self.T3 = struct.unpack_from('<h', bytes(cal[4:6]))[0]
        self.H1 = self._read(0xA1, 1)[0]
        c2 = self._read(0xE1, 7)
        self.H2 = struct.unpack_from('<h', bytes(c2[0:2]))[0]
        self.H3 = c2[2]
        self.H4 = (c2[3] << 4) | (c2[4] & 0x0F)
        self.H5 = (c2[5] << 4) | (c2[4] >> 4)
        self.H6 = struct.unpack_from('<b', bytes([c2[6]]))[0]

    def read_all(self):
        d = self._read(0xF7, 8)
        adc_T = (d[3] << 12) | (d[4] << 4) | (d[5] >> 4)
        adc_H = (d[6] << 8) | d[7]
        v1 = (adc_T / 16384.0 - self.T1 / 1024.0) * self.T2
        v2 = ((adc_T / 131072.0 - self.T1 / 8192.0) ** 2) * self.T3
        tf = v1 + v2
        temp = tf / 5120.0
        h = tf - 76800.0
        if h == 0:
            hum = 0.0
        else:
            h = (adc_H - (self.H4 * 64.0 + (self.H5 / 16384.0) * h)) * \
                (self.H2 / 65536.0 * (1.0 + self.H6 / 67108864.0 * h *
                (1.0 + self.H3 / 67108864.0 * h)))
            hum = max(0.0, min(h * (1.0 - self.H1 * h / 524288.0), 100.0))
        return round(temp, 2), round(hum, 2)


# blend soil and air temp - soil weighted more since it's in the medium
def fused_temp(soil_t, bme_t):
    if soil_t is None and bme_t is None: return None
    if soil_t is None: return bme_t
    if bme_t is None: return soil_t
    return round(soil_t * 0.6 + bme_t * 0.4, 2)

def check_alerts(plant, bme_t, bme_h, soil_t, moist_pct, water_level):
    p = PLANTS[plant]
    alerts = []
    t = fused_temp(soil_t, bme_t)
    if t is not None:
        if t < p["temp_min"]:   alerts.append("TEMP LOW {:.1f}C".format(t))
        elif t > p["temp_max"]: alerts.append("TEMP HIGH {:.1f}C".format(t))
    if bme_h is not None and bme_h > 0:
        if bme_h < p["humidity_min"]:   alerts.append("HUM LOW {:.0f}%".format(bme_h))
        elif bme_h > p["humidity_max"]: alerts.append("HUM HIGH {:.0f}%".format(bme_h))
    if moist_pct is not None and moist_pct > 110: alerts.append("OVERWATERED")
    if moist_pct is not None and moist_pct == 0.0: alerts.append("SOIL CRITICAL")
    if water_level < RESERVOIR_LOW: alerts.append("RESERVOIR LOW")
    return alerts

def fmt_countdown(secs):
    if secs <= 0: return "SOIL OK"
    h, rem = divmod(int(secs), 3600)
    m, s = divmod(rem, 60)
    if h > 0:   return "{}h{:02d}m{:02d}s".format(h, m, s)
    elif m > 0: return "{}m{:02d}s".format(m, s)
    return "{}s".format(s)

def update_lcd(plant, moist_pct, water_level, alerts, countdown):
    try:
        lcd.clear()
        if alerts:
            lcd.cursor_pos = (0, 0)
            lcd.write_string("!{:<15}".format(alerts[0][:15]))
            lcd.cursor_pos = (1, 0)
            lcd.write_string("!{:<15}".format(alerts[1][:15]) if len(alerts) > 1 else "{:<16}".format(plant[:16]))
        else:
            lcd.cursor_pos = (0, 0)
            mstr = "{:.1f}%".format(moist_pct) if moist_pct is not None else "---"
            lcd.write_string("M:{} {}".format(mstr, plant[:6]))
            lcd.cursor_pos = (1, 0)
            lcd.write_string("R:{:.0f}% {}".format(water_level * 100, countdown)[:16])
    except Exception as e:
        print("LCD error: {}".format(e))
        try: lcd.clear()
        except: pass


# setup
gpio_setup(PUMP_GPIO)
bus = smbus2.SMBus(I2C_BUS)

bme = None
try:
    bme = BME280(bus, BME_ADDR)
    print("BME280 ready")
except Exception as e:
    print("BME280 not available: {}".format(e))

lcd = CharLCD(i2c_expander='PCF8574', address=0x27, port=2, cols=16, rows=2, dotsize=8)

plant         = ACTIVE_PLANT
p             = PLANTS[plant]
last_pump     = -999999
pump_running  = False
pump_end_time = 0
last_temp     = None
last_hum      = None

print("Starting... plant: {}".format(plant))
print("Type RUN to manually run the pump for 1 second")
for i in range(5, 0, -1):
    print("{}...".format(i))
    time.sleep(1)
print("Running")

try:
    while True:
        now         = time.time()
        water_level = get_water_level()
        soil_raw    = get_soil_raw(bus)
        soil_t      = get_soil_temp(bus)
        moist_pct   = soil_to_pct(soil_raw, plant)

        if bme is not None:
            try:
                last_temp, last_hum = bme.read_all()
            except Exception as e:
                print("BME280 error: {}".format(e))

        ft         = fused_temp(soil_t, last_temp)
        alerts     = check_alerts(plant, last_temp, last_hum, soil_t, moist_pct, water_level)
        cooldown   = get_dynamic_cooldown(moist_pct, plant)
        time_until = max(0, cooldown - (now - last_pump))
        countdown  = "WATERING" if pump_running else fmt_countdown(time_until)

        update_lcd(plant, moist_pct, water_level, alerts, countdown)

        print("Plant:{} Mst:{} Res:{:.0f}% T:{} H:{} Next:{}".format(
            plant,
            "{:.1f}%".format(moist_pct) if moist_pct is not None else "err",
            water_level * 100,
            "{:.1f}C".format(ft) if ft is not None else "n/a",
            "{:.0f}%".format(last_hum) if last_hum is not None else "n/a",
            countdown))

        if alerts:
            print("ALERTS: {}".format(", ".join(alerts)))

        if pump_running and now >= pump_end_time:
            gpio_write(PUMP_GPIO, 0)
            pump_running = False
            last_pump    = now
            print("Pump OFF")
            time.sleep(0.5)

        cooldown_ok = time_until <= 0
        needs_water = moist_pct is not None and moist_pct < p["water_threshold"]
        not_soaked  = moist_pct is None or moist_pct < 100.0

        if manual_run and not pump_running:
            manual_run    = False
            gpio_write(PUMP_GPIO, 1)
            pump_running  = True
            pump_end_time = now + 1
            print("Manual run - pump ON 1s")
        elif needs_water and cooldown_ok and not_soaked and not pump_running:
            gpio_write(PUMP_GPIO, 1)
            pump_running  = True
            pump_end_time = now + p["water_duration"]
            print("Pump ON - {}s".format(p["water_duration"]))

        time.sleep(2)

except KeyboardInterrupt:
    print("Shutting down")
    gpio_write(PUMP_GPIO, 0)
    gpio_cleanup(PUMP_GPIO)
    try: lcd.clear()
    except: pass
