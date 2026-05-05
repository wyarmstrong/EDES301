# Adaptive Irrigation Controller
[HacksterIO Link](https://www.hackster.io/wyarmstrobng/adaptive-irrigation-controller-using-pocketbeagle-9c98e5)

Automatic plant watering system built on the PocketBeagle. Monitors soil moisture, reservoir level, and temperature/humidity, then waters the plant automatically based on the plant type you configure.

## Hardware

| Part | Details |
|------|---------|
| PocketBeagle | Main board |
| Adafruit Stemma Soil Sensor | I2C capacitive moisture + temp |
| Grove Analog Water Sensor | Reservoir level (analog) |
| GY-BME280 | Air temp and humidity (I2C) |
| 16x2 I2C LCD | PCF8574 backpack |
| 5V DC submersible pump | Water delivery |
| MTP3055VL MOSFET | Pump switching |
| TXS0108E level shifter | 3.3V to 1.8V/5V conversion |
| 1N4007 diode | Flyback protection |
| 100Ω + 10kΩ resistors | Gate resistors |
| 5V 2A power adapter | Wall power |

## Wiring

| PocketBeagle Pin | Connects To |
|-----------------|-------------|
| P1.02 | TXS0108E A1 (water sensor, 1.8V side) |
| P1.14 | 3.3V — all sensor VCC, TXS VB and OE |
| P1.16 | GND — everything |
| P1.18 | TXS0108E VA (1.8V reference) |
| P1.24 | 5V — pump positive |
| P1.26 | I2C SDA — soil sensor, LCD, BME280 |
| P1.28 | I2C SCL — soil sensor, LCD, BME280 |
| P1.34 | TXS0108E A2 (pump gate, 1.8V side) |

TXS B1 → water sensor signal pin
TXS B2 → 100Ω → MOSFET gate
MOSFET source → GND, drain → pump negative
1N4007 across pump (cathode to +, anode to -)

## Running

Copy files over:
```
scp irrigation.py pump_test.py debian@192.168.7.2:/var/lib/cloud9/python/
ssh debian@192.168.7.2
```

Verify I2C devices show up:
```
sudo i2cdetect -y -r 2
# should see 0x27 (LCD), 0x36 (soil sensor), 0x76 (BME280)
```

Test pump first:
```
cd /var/lib/cloud9/python
sudo python3.11 pump_test.py
```

Run the full system:
```
sudo python3.11 irrigation.py
```

## Autoboot

```
sudo nano /etc/systemd/system/irrigation.service
```

Paste:
```
[Unit]
Description=Irrigation System
After=network.target

[Service]
ExecStart=/usr/bin/python3.11 /var/lib/cloud9/python/irrigation.py
WorkingDirectory=/var/lib/cloud9/python
Restart=always
RestartSec=5
User=root

[Install]
WantedBy=multi-user.target
```

```
sudo systemctl daemon-reload
sudo systemctl enable irrigation.service
sudo systemctl start irrigation.service
```

## Usage

Set your plant type at the top of irrigation.py:
```python
ACTIVE_PLANT = "flower"  # succulent, flower, vegetable, tropical, cactus
```

LCD shows moisture %, reservoir level, and countdown to next watering. Alerts override the display when something is out of range.

Type `RUN` in the terminal while running to manually trigger the pump for 1 second.

To calibrate the water sensor, fill and empty the reservoir and note the Res% values, then update `WATER_RAW_FULL` and `WATER_RAW_EMPTY` in the code.

## Plant Profiles

| Plant | Interval | Threshold |
|-------|----------|-----------|
| Succulent | 24h | 30% |
| Flower | 12h | 40% |
| Vegetable | 6h | 45% |
| Tropical | 8h | 50% |
| Cactus | 48h | 20% |

If soil is critically dry (2+ standard deviations below threshold) the cooldown drops to 15 minutes. Moderately dry drops to 30 minutes.

## Links

- Hackster.io: [add link]
- GitHub: [add link]
