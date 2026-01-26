"""
Component Library Seed Data

Popular components with verified dimensions, mounting holes, and connector positions.
All dimensions in millimeters.
"""

from datetime import datetime
from typing import Any
from uuid import uuid4

# =============================================================================
# Component Categories
# =============================================================================

CATEGORIES = {
    "sbc": "Single Board Computers",
    "mcu": "Microcontrollers",
    "display": "Displays",
    "input": "Input Devices",
    "connector": "Connectors",
    "sensor": "Sensors",
    "power": "Power Components",
    "audio": "Audio Components",
    "storage": "Storage",
}

# =============================================================================
# Single Board Computers
# =============================================================================

RASPBERRY_PI_5 = {
    "name": "Raspberry Pi 5",
    "model_number": "RPI5",
    "manufacturer": "Raspberry Pi Foundation",
    "category": "sbc",
    "description": "Latest Raspberry Pi with improved performance",
    "dimensions": {
        "length": 85.0,
        "width": 56.0,
        "height": 17.0,  # With ports
        "pcb_thickness": 1.6,
    },
    "mounting_holes": [
        {"x": 3.5, "y": 3.5, "diameter": 2.7, "type": "M2.5"},
        {"x": 61.5, "y": 3.5, "diameter": 2.7, "type": "M2.5"},
        {"x": 3.5, "y": 52.5, "diameter": 2.7, "type": "M2.5"},
        {"x": 61.5, "y": 52.5, "diameter": 2.7, "type": "M2.5"},
    ],
    "connectors": [
        {"name": "USB-C Power", "type": "usb-c", "x": 11.2, "y": 56.0, "width": 9.0, "height": 3.2, "side": "top"},
        {"name": "Micro HDMI 0", "type": "micro-hdmi", "x": 26.0, "y": 56.0, "width": 6.5, "height": 3.0, "side": "top"},
        {"name": "Micro HDMI 1", "type": "micro-hdmi", "x": 39.0, "y": 56.0, "width": 6.5, "height": 3.0, "side": "top"},
        {"name": "USB 3.0 (x2)", "type": "usb-a-stacked", "x": 85.0, "y": 29.0, "width": 17.5, "height": 15.5, "side": "right"},
        {"name": "USB 2.0 (x2)", "type": "usb-a-stacked", "x": 85.0, "y": 47.0, "width": 17.5, "height": 15.5, "side": "right"},
        {"name": "Ethernet", "type": "rj45", "x": 85.0, "y": 10.25, "width": 21.5, "height": 16.0, "side": "right"},
        {"name": "3.5mm Audio", "type": "audio-jack", "x": 53.5, "y": 56.0, "width": 7.0, "height": 6.0, "side": "top"},
        {"name": "40-pin GPIO", "type": "header-2x20", "x": 7.1, "y": 32.5, "width": 51.0, "height": 5.0, "side": "internal"},
    ],
    "clearance_zones": [
        {"name": "SD Card", "x": -3.0, "y": 22.0, "width": 15.0, "height": 12.0, "z_height": 2.0, "side": "left"},
        {"name": "Power Button", "x": 21.0, "y": 0.0, "width": 7.0, "height": 5.0, "z_height": 3.0, "side": "bottom"},
    ],
    "thermal": {
        "max_temp_c": 85,
        "recommended_ventilation": True,
        "heat_zones": [{"x": 35, "y": 30, "radius": 15}],
    },
    "weight_g": 46,
    "datasheet_url": "https://datasheets.raspberrypi.com/rpi5/raspberry-pi-5-product-brief.pdf",
}

RASPBERRY_PI_4B = {
    "name": "Raspberry Pi 4 Model B",
    "model_number": "RPI4B",
    "manufacturer": "Raspberry Pi Foundation",
    "category": "sbc",
    "description": "Popular SBC with dual HDMI and USB 3.0",
    "dimensions": {
        "length": 85.0,
        "width": 56.0,
        "height": 17.0,
        "pcb_thickness": 1.6,
    },
    "mounting_holes": [
        {"x": 3.5, "y": 3.5, "diameter": 2.7, "type": "M2.5"},
        {"x": 61.5, "y": 3.5, "diameter": 2.7, "type": "M2.5"},
        {"x": 3.5, "y": 52.5, "diameter": 2.7, "type": "M2.5"},
        {"x": 61.5, "y": 52.5, "diameter": 2.7, "type": "M2.5"},
    ],
    "connectors": [
        {"name": "USB-C Power", "type": "usb-c", "x": 11.2, "y": 56.0, "width": 9.0, "height": 3.2, "side": "top"},
        {"name": "Micro HDMI 0", "type": "micro-hdmi", "x": 26.0, "y": 56.0, "width": 6.5, "height": 3.0, "side": "top"},
        {"name": "Micro HDMI 1", "type": "micro-hdmi", "x": 39.0, "y": 56.0, "width": 6.5, "height": 3.0, "side": "top"},
        {"name": "USB 3.0 (x2)", "type": "usb-a-stacked", "x": 85.0, "y": 29.0, "width": 17.5, "height": 15.5, "side": "right"},
        {"name": "USB 2.0 (x2)", "type": "usb-a-stacked", "x": 85.0, "y": 47.0, "width": 17.5, "height": 15.5, "side": "right"},
        {"name": "Ethernet", "type": "rj45", "x": 85.0, "y": 10.25, "width": 21.5, "height": 16.0, "side": "right"},
        {"name": "3.5mm Audio", "type": "audio-jack", "x": 53.5, "y": 56.0, "width": 7.0, "height": 6.0, "side": "top"},
        {"name": "40-pin GPIO", "type": "header-2x20", "x": 7.1, "y": 32.5, "width": 51.0, "height": 5.0, "side": "internal"},
    ],
    "clearance_zones": [
        {"name": "SD Card", "x": -3.0, "y": 22.0, "width": 15.0, "height": 12.0, "z_height": 2.0, "side": "left"},
    ],
    "thermal": {
        "max_temp_c": 85,
        "recommended_ventilation": True,
        "heat_zones": [{"x": 35, "y": 30, "radius": 15}],
    },
    "weight_g": 46,
    "datasheet_url": "https://datasheets.raspberrypi.com/rpi4/raspberry-pi-4-datasheet.pdf",
}

RASPBERRY_PI_ZERO_2W = {
    "name": "Raspberry Pi Zero 2 W",
    "model_number": "RPI-ZERO-2W",
    "manufacturer": "Raspberry Pi Foundation",
    "category": "sbc",
    "description": "Compact SBC with wireless connectivity",
    "dimensions": {
        "length": 65.0,
        "width": 30.0,
        "height": 5.0,
        "pcb_thickness": 1.0,
    },
    "mounting_holes": [
        {"x": 3.5, "y": 3.5, "diameter": 2.7, "type": "M2.5"},
        {"x": 61.5, "y": 3.5, "diameter": 2.7, "type": "M2.5"},
        {"x": 3.5, "y": 26.5, "diameter": 2.7, "type": "M2.5"},
        {"x": 61.5, "y": 26.5, "diameter": 2.7, "type": "M2.5"},
    ],
    "connectors": [
        {"name": "Micro USB Power", "type": "micro-usb", "x": 6.0, "y": 30.0, "width": 8.0, "height": 3.0, "side": "top"},
        {"name": "Micro USB Data", "type": "micro-usb", "x": 19.5, "y": 30.0, "width": 8.0, "height": 3.0, "side": "top"},
        {"name": "Mini HDMI", "type": "mini-hdmi", "x": 35.5, "y": 30.0, "width": 11.0, "height": 3.5, "side": "top"},
        {"name": "40-pin GPIO", "type": "header-2x20-unpopulated", "x": 7.5, "y": 15.0, "width": 51.0, "height": 5.0, "side": "internal"},
    ],
    "clearance_zones": [
        {"name": "SD Card", "x": 65.0, "y": 8.0, "width": 15.0, "height": 12.0, "z_height": 2.0, "side": "right"},
    ],
    "thermal": {
        "max_temp_c": 85,
        "recommended_ventilation": False,
        "heat_zones": [{"x": 30, "y": 15, "radius": 8}],
    },
    "weight_g": 10,
    "datasheet_url": "https://datasheets.raspberrypi.com/rpizero2/raspberry-pi-zero-2-w-product-brief.pdf",
}

# =============================================================================
# Microcontrollers
# =============================================================================

ARDUINO_UNO_R3 = {
    "name": "Arduino Uno R3",
    "model_number": "A000066",
    "manufacturer": "Arduino",
    "category": "mcu",
    "description": "Classic Arduino board with ATmega328P",
    "dimensions": {
        "length": 68.6,
        "width": 53.4,
        "height": 15.0,
        "pcb_thickness": 1.6,
    },
    "mounting_holes": [
        {"x": 14.0, "y": 2.5, "diameter": 3.2, "type": "M3"},
        {"x": 15.2, "y": 50.8, "diameter": 3.2, "type": "M3"},
        {"x": 66.0, "y": 7.6, "diameter": 3.2, "type": "M3"},
        {"x": 66.0, "y": 35.6, "diameter": 3.2, "type": "M3"},
    ],
    "connectors": [
        {"name": "USB-B", "type": "usb-b", "x": 9.0, "y": 0.0, "width": 12.0, "height": 11.0, "side": "bottom"},
        {"name": "DC Jack", "type": "barrel-jack", "x": 0.0, "y": 7.6, "width": 9.0, "height": 14.0, "side": "left"},
        {"name": "Digital Pins", "type": "header-1x14", "x": 18.0, "y": 53.4, "width": 35.5, "height": 8.5, "side": "internal"},
        {"name": "Analog Pins", "type": "header-1x6", "x": 50.0, "y": 0.0, "width": 15.2, "height": 8.5, "side": "internal"},
        {"name": "Power Pins", "type": "header-1x8", "x": 18.0, "y": 0.0, "width": 20.3, "height": 8.5, "side": "internal"},
    ],
    "clearance_zones": [],
    "thermal": {
        "max_temp_c": 70,
        "recommended_ventilation": False,
        "heat_zones": [],
    },
    "weight_g": 25,
    "datasheet_url": "https://docs.arduino.cc/resources/datasheets/A000066-datasheet.pdf",
}

ARDUINO_NANO = {
    "name": "Arduino Nano",
    "model_number": "A000005",
    "manufacturer": "Arduino",
    "category": "mcu",
    "description": "Compact Arduino board for breadboard use",
    "dimensions": {
        "length": 45.0,
        "width": 18.0,
        "height": 5.0,
        "pcb_thickness": 1.6,
    },
    "mounting_holes": [
        {"x": 1.3, "y": 1.3, "diameter": 1.5, "type": "M1.5"},
        {"x": 43.7, "y": 1.3, "diameter": 1.5, "type": "M1.5"},
        {"x": 1.3, "y": 16.7, "diameter": 1.5, "type": "M1.5"},
        {"x": 43.7, "y": 16.7, "diameter": 1.5, "type": "M1.5"},
    ],
    "connectors": [
        {"name": "Mini USB", "type": "mini-usb", "x": 20.0, "y": 18.0, "width": 8.0, "height": 4.0, "side": "top"},
        {"name": "Left Pins", "type": "header-1x15", "x": 0.0, "y": 1.5, "width": 2.54, "height": 38.0, "side": "left"},
        {"name": "Right Pins", "type": "header-1x15", "x": 18.0, "y": 1.5, "width": 2.54, "height": 38.0, "side": "right"},
    ],
    "clearance_zones": [],
    "thermal": {
        "max_temp_c": 70,
        "recommended_ventilation": False,
        "heat_zones": [],
    },
    "weight_g": 7,
    "datasheet_url": "https://docs.arduino.cc/resources/datasheets/A000005-datasheet.pdf",
}

ARDUINO_MEGA_2560 = {
    "name": "Arduino Mega 2560",
    "model_number": "A000067",
    "manufacturer": "Arduino",
    "category": "mcu",
    "description": "Arduino board with extended I/O",
    "dimensions": {
        "length": 101.6,
        "width": 53.3,
        "height": 15.0,
        "pcb_thickness": 1.6,
    },
    "mounting_holes": [
        {"x": 14.0, "y": 2.5, "diameter": 3.2, "type": "M3"},
        {"x": 15.2, "y": 50.8, "diameter": 3.2, "type": "M3"},
        {"x": 90.2, "y": 50.8, "diameter": 3.2, "type": "M3"},
        {"x": 96.5, "y": 2.5, "diameter": 3.2, "type": "M3"},
    ],
    "connectors": [
        {"name": "USB-B", "type": "usb-b", "x": 9.0, "y": 0.0, "width": 12.0, "height": 11.0, "side": "bottom"},
        {"name": "DC Jack", "type": "barrel-jack", "x": 0.0, "y": 7.6, "width": 9.0, "height": 14.0, "side": "left"},
    ],
    "clearance_zones": [],
    "thermal": {
        "max_temp_c": 70,
        "recommended_ventilation": False,
        "heat_zones": [],
    },
    "weight_g": 37,
    "datasheet_url": "https://docs.arduino.cc/resources/datasheets/A000067-datasheet.pdf",
}

ESP32_DEVKIT_V1 = {
    "name": "ESP32 DevKit V1",
    "model_number": "ESP32-DEVKIT-V1",
    "manufacturer": "Espressif",
    "category": "mcu",
    "description": "WiFi + Bluetooth development board",
    "dimensions": {
        "length": 51.4,
        "width": 28.0,
        "height": 6.0,
        "pcb_thickness": 1.6,
    },
    "mounting_holes": [
        {"x": 2.0, "y": 2.0, "diameter": 2.0, "type": "M2"},
        {"x": 49.4, "y": 2.0, "diameter": 2.0, "type": "M2"},
        {"x": 2.0, "y": 26.0, "diameter": 2.0, "type": "M2"},
        {"x": 49.4, "y": 26.0, "diameter": 2.0, "type": "M2"},
    ],
    "connectors": [
        {"name": "Micro USB", "type": "micro-usb", "x": 23.0, "y": 28.0, "width": 8.0, "height": 3.0, "side": "top"},
        {"name": "Left Pins", "type": "header-1x19", "x": 0.0, "y": 2.0, "width": 2.54, "height": 48.0, "side": "left"},
        {"name": "Right Pins", "type": "header-1x19", "x": 28.0, "y": 2.0, "width": 2.54, "height": 48.0, "side": "right"},
    ],
    "clearance_zones": [
        {"name": "Antenna", "x": 15.0, "y": 0.0, "width": 20.0, "height": 10.0, "z_height": 2.0, "side": "bottom"},
    ],
    "thermal": {
        "max_temp_c": 85,
        "recommended_ventilation": False,
        "heat_zones": [{"x": 25, "y": 14, "radius": 6}],
    },
    "weight_g": 9,
    "datasheet_url": "https://www.espressif.com/sites/default/files/documentation/esp32-wroom-32_datasheet_en.pdf",
}

ESP8266_NODEMCU = {
    "name": "ESP8266 NodeMCU",
    "model_number": "NodeMCU-ESP8266",
    "manufacturer": "Various",
    "category": "mcu",
    "description": "WiFi development board with ESP8266",
    "dimensions": {
        "length": 58.0,
        "width": 31.0,
        "height": 6.0,
        "pcb_thickness": 1.6,
    },
    "mounting_holes": [
        {"x": 2.0, "y": 2.0, "diameter": 2.0, "type": "M2"},
        {"x": 56.0, "y": 2.0, "diameter": 2.0, "type": "M2"},
        {"x": 2.0, "y": 29.0, "diameter": 2.0, "type": "M2"},
        {"x": 56.0, "y": 29.0, "diameter": 2.0, "type": "M2"},
    ],
    "connectors": [
        {"name": "Micro USB", "type": "micro-usb", "x": 26.0, "y": 31.0, "width": 8.0, "height": 3.0, "side": "top"},
        {"name": "Left Pins", "type": "header-1x15", "x": 0.0, "y": 2.0, "width": 2.54, "height": 38.0, "side": "left"},
        {"name": "Right Pins", "type": "header-1x15", "x": 31.0, "y": 2.0, "width": 2.54, "height": 38.0, "side": "right"},
    ],
    "clearance_zones": [
        {"name": "Antenna", "x": 20.0, "y": 0.0, "width": 18.0, "height": 10.0, "z_height": 2.0, "side": "bottom"},
    ],
    "thermal": {
        "max_temp_c": 85,
        "recommended_ventilation": False,
        "heat_zones": [],
    },
    "weight_g": 8,
    "datasheet_url": "https://www.espressif.com/sites/default/files/documentation/esp8266-technical_reference_en.pdf",
}

# =============================================================================
# Displays
# =============================================================================

LCD_16X2_I2C = {
    "name": "16x2 LCD Display with I2C",
    "model_number": "LCD1602-I2C",
    "manufacturer": "Various",
    "category": "display",
    "description": "16 character x 2 line LCD with I2C backpack",
    "dimensions": {
        "length": 80.0,
        "width": 36.0,
        "height": 12.0,
        "pcb_thickness": 1.6,
    },
    "mounting_holes": [
        {"x": 2.5, "y": 2.5, "diameter": 3.2, "type": "M3"},
        {"x": 77.5, "y": 2.5, "diameter": 3.2, "type": "M3"},
        {"x": 2.5, "y": 33.5, "diameter": 3.2, "type": "M3"},
        {"x": 77.5, "y": 33.5, "diameter": 3.2, "type": "M3"},
    ],
    "connectors": [
        {"name": "I2C Header", "type": "header-1x4", "x": 35.0, "y": 0.0, "width": 10.0, "height": 8.5, "side": "bottom"},
    ],
    "clearance_zones": [],
    "display_area": {
        "x": 6.5,
        "y": 8.0,
        "width": 66.0,
        "height": 16.0,
    },
    "thermal": {
        "max_temp_c": 60,
        "recommended_ventilation": False,
        "heat_zones": [],
    },
    "weight_g": 30,
}

LCD_20X4_I2C = {
    "name": "20x4 LCD Display with I2C",
    "model_number": "LCD2004-I2C",
    "manufacturer": "Various",
    "category": "display",
    "description": "20 character x 4 line LCD with I2C backpack",
    "dimensions": {
        "length": 98.0,
        "width": 60.0,
        "height": 14.0,
        "pcb_thickness": 1.6,
    },
    "mounting_holes": [
        {"x": 2.5, "y": 2.5, "diameter": 3.2, "type": "M3"},
        {"x": 95.5, "y": 2.5, "diameter": 3.2, "type": "M3"},
        {"x": 2.5, "y": 57.5, "diameter": 3.2, "type": "M3"},
        {"x": 95.5, "y": 57.5, "diameter": 3.2, "type": "M3"},
    ],
    "connectors": [
        {"name": "I2C Header", "type": "header-1x4", "x": 45.0, "y": 0.0, "width": 10.0, "height": 8.5, "side": "bottom"},
    ],
    "clearance_zones": [],
    "display_area": {
        "x": 9.0,
        "y": 12.0,
        "width": 77.0,
        "height": 25.0,
    },
    "thermal": {
        "max_temp_c": 60,
        "recommended_ventilation": False,
        "heat_zones": [],
    },
    "weight_g": 50,
}

OLED_096_I2C = {
    "name": "0.96\" OLED Display I2C",
    "model_number": "SSD1306-096",
    "manufacturer": "Various",
    "category": "display",
    "description": "0.96 inch 128x64 OLED display with I2C",
    "dimensions": {
        "length": 27.0,
        "width": 27.0,
        "height": 4.0,
        "pcb_thickness": 1.0,
    },
    "mounting_holes": [
        {"x": 2.0, "y": 2.0, "diameter": 2.0, "type": "M2"},
        {"x": 25.0, "y": 2.0, "diameter": 2.0, "type": "M2"},
        {"x": 2.0, "y": 25.0, "diameter": 2.0, "type": "M2"},
        {"x": 25.0, "y": 25.0, "diameter": 2.0, "type": "M2"},
    ],
    "connectors": [
        {"name": "I2C Header", "type": "header-1x4", "x": 8.5, "y": 0.0, "width": 10.0, "height": 2.54, "side": "bottom"},
    ],
    "clearance_zones": [],
    "display_area": {
        "x": 2.0,
        "y": 5.0,
        "width": 23.0,
        "height": 12.0,
    },
    "thermal": {
        "max_temp_c": 70,
        "recommended_ventilation": False,
        "heat_zones": [],
    },
    "weight_g": 5,
}

OLED_130_I2C = {
    "name": "1.3\" OLED Display I2C",
    "model_number": "SH1106-130",
    "manufacturer": "Various",
    "category": "display",
    "description": "1.3 inch 128x64 OLED display with I2C",
    "dimensions": {
        "length": 35.0,
        "width": 33.0,
        "height": 4.0,
        "pcb_thickness": 1.0,
    },
    "mounting_holes": [
        {"x": 2.5, "y": 2.5, "diameter": 2.5, "type": "M2.5"},
        {"x": 32.5, "y": 2.5, "diameter": 2.5, "type": "M2.5"},
        {"x": 2.5, "y": 30.5, "diameter": 2.5, "type": "M2.5"},
        {"x": 32.5, "y": 30.5, "diameter": 2.5, "type": "M2.5"},
    ],
    "connectors": [
        {"name": "I2C Header", "type": "header-1x4", "x": 12.0, "y": 0.0, "width": 10.0, "height": 2.54, "side": "bottom"},
    ],
    "clearance_zones": [],
    "display_area": {
        "x": 3.0,
        "y": 5.0,
        "width": 29.0,
        "height": 15.0,
    },
    "thermal": {
        "max_temp_c": 70,
        "recommended_ventilation": False,
        "heat_zones": [],
    },
    "weight_g": 8,
}

TFT_240_320 = {
    "name": "2.4\" TFT LCD 240x320",
    "model_number": "ILI9341-240",
    "manufacturer": "Various",
    "category": "display",
    "description": "2.4 inch TFT LCD with touchscreen",
    "dimensions": {
        "length": 71.0,
        "width": 52.0,
        "height": 7.0,
        "pcb_thickness": 1.6,
    },
    "mounting_holes": [
        {"x": 2.0, "y": 2.0, "diameter": 2.5, "type": "M2.5"},
        {"x": 69.0, "y": 2.0, "diameter": 2.5, "type": "M2.5"},
        {"x": 2.0, "y": 50.0, "diameter": 2.5, "type": "M2.5"},
        {"x": 69.0, "y": 50.0, "diameter": 2.5, "type": "M2.5"},
    ],
    "connectors": [
        {"name": "SPI Header", "type": "header-2x7", "x": 28.0, "y": 0.0, "width": 18.0, "height": 5.0, "side": "bottom"},
    ],
    "clearance_zones": [],
    "display_area": {
        "x": 5.0,
        "y": 8.0,
        "width": 49.0,
        "height": 37.0,
    },
    "thermal": {
        "max_temp_c": 70,
        "recommended_ventilation": False,
        "heat_zones": [],
    },
    "weight_g": 25,
}

# =============================================================================
# Input Devices
# =============================================================================

TACTILE_BUTTON_6X6 = {
    "name": "6x6mm Tactile Button",
    "model_number": "TS-1109",
    "manufacturer": "Various",
    "category": "input",
    "description": "Standard 6x6mm tactile switch",
    "dimensions": {
        "length": 6.0,
        "width": 6.0,
        "height": 5.0,  # Button height varies 4.3-9.5mm
        "pcb_thickness": 0.0,  # Through-hole
    },
    "mounting_holes": [],  # Through-hole pins
    "connectors": [],
    "clearance_zones": [
        {"name": "Button Travel", "x": 0.0, "y": 0.0, "width": 6.0, "height": 6.0, "z_height": 1.0, "side": "top"},
    ],
    "thermal": {
        "max_temp_c": 85,
        "recommended_ventilation": False,
        "heat_zones": [],
    },
    "weight_g": 0.5,
}

TACTILE_BUTTON_12X12 = {
    "name": "12x12mm Tactile Button",
    "model_number": "TS-1212",
    "manufacturer": "Various",
    "category": "input",
    "description": "Large 12x12mm tactile switch with cap",
    "dimensions": {
        "length": 12.0,
        "width": 12.0,
        "height": 7.3,
        "pcb_thickness": 0.0,
    },
    "mounting_holes": [],
    "connectors": [],
    "clearance_zones": [
        {"name": "Button Travel", "x": 0.0, "y": 0.0, "width": 12.0, "height": 12.0, "z_height": 1.5, "side": "top"},
    ],
    "thermal": {
        "max_temp_c": 85,
        "recommended_ventilation": False,
        "heat_zones": [],
    },
    "weight_g": 1.5,
}

ROTARY_ENCODER = {
    "name": "Rotary Encoder with Button",
    "model_number": "KY-040",
    "manufacturer": "Various",
    "category": "input",
    "description": "Incremental rotary encoder with push button",
    "dimensions": {
        "length": 26.0,
        "width": 19.0,
        "height": 30.0,  # Including shaft
        "pcb_thickness": 1.6,
    },
    "mounting_holes": [
        {"x": 2.0, "y": 2.0, "diameter": 3.0, "type": "M3"},
        {"x": 24.0, "y": 2.0, "diameter": 3.0, "type": "M3"},
    ],
    "connectors": [
        {"name": "5-pin Header", "type": "header-1x5", "x": 5.0, "y": 0.0, "width": 13.0, "height": 8.5, "side": "bottom"},
    ],
    "clearance_zones": [
        {"name": "Knob Area", "x": 6.0, "y": 9.0, "width": 14.0, "height": 14.0, "z_height": 20.0, "side": "top"},
    ],
    "thermal": {
        "max_temp_c": 70,
        "recommended_ventilation": False,
        "heat_zones": [],
    },
    "weight_g": 12,
}

JOYSTICK_MODULE = {
    "name": "Analog Joystick Module",
    "model_number": "KY-023",
    "manufacturer": "Various",
    "category": "input",
    "description": "2-axis analog joystick with button",
    "dimensions": {
        "length": 34.0,
        "width": 26.0,
        "height": 32.0,  # Including stick
        "pcb_thickness": 1.6,
    },
    "mounting_holes": [
        {"x": 2.5, "y": 2.5, "diameter": 3.0, "type": "M3"},
        {"x": 31.5, "y": 2.5, "diameter": 3.0, "type": "M3"},
        {"x": 2.5, "y": 23.5, "diameter": 3.0, "type": "M3"},
        {"x": 31.5, "y": 23.5, "diameter": 3.0, "type": "M3"},
    ],
    "connectors": [
        {"name": "5-pin Header", "type": "header-1x5", "x": 10.0, "y": 0.0, "width": 13.0, "height": 8.5, "side": "bottom"},
    ],
    "clearance_zones": [
        {"name": "Joystick Movement", "x": 7.0, "y": 3.0, "width": 20.0, "height": 20.0, "z_height": 25.0, "side": "top"},
    ],
    "thermal": {
        "max_temp_c": 70,
        "recommended_ventilation": False,
        "heat_zones": [],
    },
    "weight_g": 15,
}

# =============================================================================
# Connectors
# =============================================================================

USB_A_PANEL_MOUNT = {
    "name": "USB-A Panel Mount",
    "model_number": "USB-A-PM",
    "manufacturer": "Various",
    "category": "connector",
    "description": "USB-A female panel mount connector",
    "dimensions": {
        "length": 30.0,
        "width": 13.0,
        "height": 5.5,
        "pcb_thickness": 0.0,
    },
    "mounting_holes": [
        {"x": 4.0, "y": 6.5, "diameter": 3.2, "type": "M3"},
        {"x": 26.0, "y": 6.5, "diameter": 3.2, "type": "M3"},
    ],
    "connectors": [],
    "cutout": {
        "width": 13.0,
        "height": 5.5,
        "corner_radius": 0.5,
    },
    "thermal": {
        "max_temp_c": 85,
        "recommended_ventilation": False,
        "heat_zones": [],
    },
    "weight_g": 8,
}

USB_C_PANEL_MOUNT = {
    "name": "USB-C Panel Mount",
    "model_number": "USB-C-PM",
    "manufacturer": "Various",
    "category": "connector",
    "description": "USB-C female panel mount connector",
    "dimensions": {
        "length": 25.0,
        "width": 12.0,
        "height": 6.5,
        "pcb_thickness": 0.0,
    },
    "mounting_holes": [
        {"x": 3.5, "y": 6.0, "diameter": 2.5, "type": "M2.5"},
        {"x": 21.5, "y": 6.0, "diameter": 2.5, "type": "M2.5"},
    ],
    "connectors": [],
    "cutout": {
        "width": 9.0,
        "height": 3.2,
        "corner_radius": 1.0,
    },
    "thermal": {
        "max_temp_c": 85,
        "recommended_ventilation": False,
        "heat_zones": [],
    },
    "weight_g": 5,
}

DC_BARREL_JACK = {
    "name": "DC Barrel Jack 5.5x2.1mm",
    "model_number": "DC-022",
    "manufacturer": "Various",
    "category": "connector",
    "description": "Standard DC barrel power jack",
    "dimensions": {
        "length": 14.0,
        "width": 9.0,
        "height": 11.0,
        "pcb_thickness": 0.0,
    },
    "mounting_holes": [],
    "connectors": [],
    "cutout": {
        "diameter": 8.0,
    },
    "thermal": {
        "max_temp_c": 85,
        "recommended_ventilation": False,
        "heat_zones": [],
    },
    "weight_g": 5,
}

SD_CARD_SLOT = {
    "name": "Micro SD Card Slot",
    "model_number": "MicroSD-Slot",
    "manufacturer": "Various",
    "category": "connector",
    "description": "Push-push micro SD card socket",
    "dimensions": {
        "length": 14.0,
        "width": 14.5,
        "height": 2.0,
        "pcb_thickness": 0.0,
    },
    "mounting_holes": [],
    "connectors": [],
    "clearance_zones": [
        {"name": "Card Insertion", "x": 0.0, "y": 7.0, "width": 12.0, "height": 10.0, "z_height": 1.5, "side": "front"},
    ],
    "thermal": {
        "max_temp_c": 70,
        "recommended_ventilation": False,
        "heat_zones": [],
    },
    "weight_g": 2,
}

# =============================================================================
# Sensors
# =============================================================================

PIR_SENSOR_HC_SR501 = {
    "name": "PIR Motion Sensor HC-SR501",
    "model_number": "HC-SR501",
    "manufacturer": "Various",
    "category": "sensor",
    "description": "Passive infrared motion sensor module",
    "dimensions": {
        "length": 32.0,
        "width": 24.0,
        "height": 25.0,  # Including dome
        "pcb_thickness": 1.6,
    },
    "mounting_holes": [
        {"x": 2.5, "y": 12.0, "diameter": 2.0, "type": "M2"},
        {"x": 29.5, "y": 12.0, "diameter": 2.0, "type": "M2"},
    ],
    "connectors": [
        {"name": "3-pin Header", "type": "header-1x3", "x": 12.0, "y": 0.0, "width": 8.0, "height": 8.5, "side": "bottom"},
    ],
    "clearance_zones": [
        {"name": "Sensor Dome", "x": 4.0, "y": 0.0, "width": 24.0, "height": 24.0, "z_height": 15.0, "side": "top"},
    ],
    "thermal": {
        "max_temp_c": 60,
        "recommended_ventilation": False,
        "heat_zones": [],
    },
    "weight_g": 8,
}

ULTRASONIC_HC_SR04 = {
    "name": "Ultrasonic Sensor HC-SR04",
    "model_number": "HC-SR04",
    "manufacturer": "Various",
    "category": "sensor",
    "description": "Ultrasonic distance sensor module",
    "dimensions": {
        "length": 45.0,
        "width": 20.0,
        "height": 15.0,  # Including transducers
        "pcb_thickness": 1.6,
    },
    "mounting_holes": [
        {"x": 2.0, "y": 10.0, "diameter": 2.0, "type": "M2"},
        {"x": 43.0, "y": 10.0, "diameter": 2.0, "type": "M2"},
    ],
    "connectors": [
        {"name": "4-pin Header", "type": "header-1x4", "x": 17.0, "y": 0.0, "width": 10.0, "height": 8.5, "side": "bottom"},
    ],
    "clearance_zones": [
        {"name": "Left Transducer", "x": 3.0, "y": 3.0, "width": 16.0, "height": 14.0, "z_height": 12.0, "side": "front"},
        {"name": "Right Transducer", "x": 26.0, "y": 3.0, "width": 16.0, "height": 14.0, "z_height": 12.0, "side": "front"},
    ],
    "thermal": {
        "max_temp_c": 70,
        "recommended_ventilation": False,
        "heat_zones": [],
    },
    "weight_g": 10,
}

DHT22_SENSOR = {
    "name": "DHT22 Temperature & Humidity Sensor",
    "model_number": "DHT22",
    "manufacturer": "Aosong",
    "category": "sensor",
    "description": "Digital temperature and humidity sensor",
    "dimensions": {
        "length": 25.0,
        "width": 15.0,
        "height": 7.5,
        "pcb_thickness": 0.0,
    },
    "mounting_holes": [],
    "connectors": [
        {"name": "4-pin", "type": "sip-4", "x": 3.5, "y": 0.0, "width": 10.0, "height": 5.0, "side": "bottom"},
    ],
    "clearance_zones": [
        {"name": "Vent Holes", "x": 0.0, "y": 3.0, "width": 25.0, "height": 10.0, "z_height": 3.0, "side": "front"},
    ],
    "thermal": {
        "max_temp_c": 80,
        "recommended_ventilation": True,  # Needs airflow for accuracy
        "heat_zones": [],
    },
    "weight_g": 3,
}

BME280_MODULE = {
    "name": "BME280 Sensor Module",
    "model_number": "BME280-MOD",
    "manufacturer": "Various",
    "category": "sensor",
    "description": "Temperature, humidity, pressure sensor breakout",
    "dimensions": {
        "length": 13.0,
        "width": 10.0,
        "height": 3.0,
        "pcb_thickness": 1.0,
    },
    "mounting_holes": [
        {"x": 2.0, "y": 5.0, "diameter": 2.0, "type": "M2"},
    ],
    "connectors": [
        {"name": "4-pin Header", "type": "header-1x4", "x": 4.0, "y": 0.0, "width": 10.0, "height": 2.54, "side": "bottom"},
    ],
    "clearance_zones": [],
    "thermal": {
        "max_temp_c": 85,
        "recommended_ventilation": True,
        "heat_zones": [],
    },
    "weight_g": 1,
}

# =============================================================================
# Power Components
# =============================================================================

BUCK_CONVERTER_MINI = {
    "name": "Mini Buck Converter 3A",
    "model_number": "MP1584",
    "manufacturer": "Various",
    "category": "power",
    "description": "Adjustable DC-DC step-down converter",
    "dimensions": {
        "length": 22.0,
        "width": 17.0,
        "height": 5.0,
        "pcb_thickness": 1.6,
    },
    "mounting_holes": [
        {"x": 2.0, "y": 2.0, "diameter": 2.0, "type": "M2"},
        {"x": 20.0, "y": 15.0, "diameter": 2.0, "type": "M2"},
    ],
    "connectors": [
        {"name": "Input +/-", "type": "screw-terminal-2", "x": 0.0, "y": 5.0, "width": 5.0, "height": 8.0, "side": "left"},
        {"name": "Output +/-", "type": "screw-terminal-2", "x": 22.0, "y": 5.0, "width": 5.0, "height": 8.0, "side": "right"},
    ],
    "clearance_zones": [
        {"name": "Adjustment Pot", "x": 8.0, "y": 6.0, "width": 6.0, "height": 6.0, "z_height": 3.0, "side": "top"},
    ],
    "thermal": {
        "max_temp_c": 85,
        "recommended_ventilation": True,
        "heat_zones": [{"x": 11, "y": 8.5, "radius": 5}],
    },
    "weight_g": 4,
}

# =============================================================================
# Complete Library
# =============================================================================

COMPONENT_LIBRARY = [
    # Single Board Computers
    RASPBERRY_PI_5,
    RASPBERRY_PI_4B,
    RASPBERRY_PI_ZERO_2W,
    
    # Microcontrollers
    ARDUINO_UNO_R3,
    ARDUINO_NANO,
    ARDUINO_MEGA_2560,
    ESP32_DEVKIT_V1,
    ESP8266_NODEMCU,
    
    # Displays
    LCD_16X2_I2C,
    LCD_20X4_I2C,
    OLED_096_I2C,
    OLED_130_I2C,
    TFT_240_320,
    
    # Input Devices
    TACTILE_BUTTON_6X6,
    TACTILE_BUTTON_12X12,
    ROTARY_ENCODER,
    JOYSTICK_MODULE,
    
    # Connectors
    USB_A_PANEL_MOUNT,
    USB_C_PANEL_MOUNT,
    DC_BARREL_JACK,
    SD_CARD_SLOT,
    
    # Sensors
    PIR_SENSOR_HC_SR501,
    ULTRASONIC_HC_SR04,
    DHT22_SENSOR,
    BME280_MODULE,
    
    # Power
    BUCK_CONVERTER_MINI,
]


async def seed_component_library(db) -> int:
    """
    Seed the database with the component library.
    
    Returns the number of components added.
    """
    from app.models.reference_component import ReferenceComponent, ComponentLibrary
    from sqlalchemy import select
    
    count = 0
    
    for component_data in COMPONENT_LIBRARY:
        # Check if component already exists
        result = await db.execute(
            select(ComponentLibrary).where(
                ComponentLibrary.model_number == component_data["model_number"]
            )
        )
        existing = result.scalar_one_or_none()
        
        if existing:
            continue
        
        # Create library component
        library_component = ComponentLibrary(
            id=uuid4(),
            name=component_data["name"],
            model_number=component_data["model_number"],
            manufacturer=component_data["manufacturer"],
            category=component_data["category"],
            description=component_data.get("description", ""),
            specifications={
                "dimensions": component_data["dimensions"],
                "mounting_holes": component_data.get("mounting_holes", []),
                "connectors": component_data.get("connectors", []),
                "clearance_zones": component_data.get("clearance_zones", []),
                "thermal": component_data.get("thermal", {}),
                "display_area": component_data.get("display_area"),
                "cutout": component_data.get("cutout"),
            },
            thumbnail_url=None,  # To be added later
            datasheet_url=component_data.get("datasheet_url"),
            is_verified=True,
            popularity_score=100,  # Default for seed data
        )
        
        db.add(library_component)
        count += 1
    
    await db.commit()
    return count


# For easy access
def get_component_by_name(name: str) -> dict | None:
    """Get component data by name."""
    for component in COMPONENT_LIBRARY:
        if component["name"].lower() == name.lower():
            return component
    return None


def get_components_by_category(category: str) -> list[dict]:
    """Get all components in a category."""
    return [c for c in COMPONENT_LIBRARY if c["category"] == category]


def list_all_categories() -> dict[str, str]:
    """Return all categories with descriptions."""
    return CATEGORIES
