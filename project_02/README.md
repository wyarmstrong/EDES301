# Etch-a-Sketch PCB — EDES301 Project 2

A custom PCB for a digital Etch-a-Sketch built on the PocketBeagle. Two potentiometers control the X and Y axes on a 1.8" SPI display. Three LEDs show the current drawing color, and two buttons let you reset the canvas or cycle through colors. A USB-C port is included for expansion.

## Components
- PocketBeagle (main processor)
- HS24S010B 1.8" SPI TFT display
- 2x RK09K1110A0J potentiometers
- 3x LEDs (red, green, blue)
- 2x tactile switches
- USB-C connector
- Supporting resistors (1k, 10k, 5.1k)

## Board
- 5" x 4" 2-layer PCB
- Display and controls on front, PocketBeagle header on back

## Folder Structure
```
project_02/
  hardware/      KiCad project files
  MFG/           Gerber files
  docs/          Screenshots and mechanical drawing
  README.md
  BOM.csv
```
