# CAD v2 Component Library Scope

## Overview

This document defines the scope of the component library for the CAD v2 system. The library contains pre-defined component definitions with accurate dimensions, mounting patterns, and port locations.

## MVP Component List (Phase 2)

### Single Board Computers

| Component | Priority | Notes |
|-----------|----------|-------|
| Raspberry Pi 5 | P0 | Primary test case |
| Raspberry Pi 4 Model B | P0 | Common board |
| Raspberry Pi 3 Model B+ | P1 | Legacy support |
| Raspberry Pi Zero 2 W | P1 | Compact projects |
| Arduino Uno R3 | P2 | Popular microcontroller |
| Arduino Nano | P2 | Compact microcontroller |
| ESP32 DevKit | P2 | WiFi/BLE projects |

### Displays

| Component | Priority | Notes |
|-----------|----------|-------|
| 20x4 Character LCD (HD44780) | P0 | Primary test case |
| 16x2 Character LCD (HD44780) | P1 | Common display |
| 0.96" OLED (SSD1306) | P1 | Compact display |
| 1.3" OLED (SH1106) | P2 | Slightly larger OLED |
| 3.5" TFT LCD (RPi) | P2 | Touchscreen option |

### Input Devices

| Component | Priority | Notes |
|-----------|----------|-------|
| 6mm Tactile Button | P0 | Primary test case |
| 12mm Tactile Button | P1 | Larger buttons |
| Arcade Button (24mm) | P2 | Game controllers |
| Rotary Encoder | P2 | Menu navigation |
| Potentiometer (9mm) | P2 | Analog input |

### Connectors

| Component | Priority | Notes |
|-----------|----------|-------|
| USB-C Port | P0 | Power/data |
| Micro USB Port | P1 | Legacy power |
| USB-A Port | P1 | Peripherals |
| Barrel Jack (5.5x2.1mm) | P1 | Power input |
| Micro HDMI Port | P0 | Pi 5/4 video |
| Full HDMI Port | P1 | Standard video |
| 3.5mm Audio Jack | P2 | Audio output |
| Ethernet Port (RJ45) | P1 | Network |
| SD Card Slot | P1 | Storage |

---

## Component Definition Structure

Each component includes:

### Required Fields

```python
class ComponentDefinition(BaseModel):
    id: str                      # Unique identifier (kebab-case)
    name: str                    # Human-readable name
    category: ComponentCategory  # boards, displays, buttons, connectors
    dimensions: BoundingBox      # Overall size (width x depth x height)
```

### Optional Fields

```python
    aliases: list[str] = []           # Alternative names for fuzzy matching
    mounting_holes: list[MountingHole] = []  # Screw holes with positions
    ports: list[PortDefinition] = []  # Connectors with positions
    keepout_zones: list[KeepoutZone] = []  # Areas requiring clearance
    mounting_options: list[MountingOption] = []  # How component can be mounted
    datasheet_url: str | None = None  # Reference documentation
    notes: str | None = None          # Special considerations
```

---

## Detailed Component Specifications

### Raspberry Pi 5

```yaml
id: raspberry-pi-5
name: Raspberry Pi 5
category: boards
aliases:
  - rpi5
  - pi 5
  - raspberry pi 5
  - pi5

dimensions:
  width: 85mm
  depth: 56mm
  height: 17mm  # Including tallest component

mounting_holes:
  - x: 3.5mm    # From corner
    y: 3.5mm
    diameter: 2.7mm
    type: through
  - x: 61.5mm
    y: 3.5mm
    diameter: 2.7mm
    type: through
  - x: 3.5mm
    y: 52.5mm
    diameter: 2.7mm
    type: through
  - x: 61.5mm
    y: 52.5mm
    diameter: 2.7mm
    type: through

ports:
  - name: usb-c-power
    position: {x: 11.2mm, y: 56mm, z: 0}
    dimensions: {width: 9mm, height: 3.5mm}
    side: back
  - name: micro-hdmi-0
    position: {x: 26mm, y: 56mm, z: 0}
    dimensions: {width: 7mm, height: 3.5mm}
    side: back
  - name: micro-hdmi-1
    position: {x: 39mm, y: 56mm, z: 0}
    dimensions: {width: 7mm, height: 3.5mm}
    side: back
  - name: usb-a-2
    position: {x: 85mm, y: 29mm, z: 0}
    dimensions: {width: 15mm, height: 16mm}
    side: right
  - name: usb-a-3
    position: {x: 85mm, y: 47mm, z: 0}
    dimensions: {width: 15mm, height: 16mm}
    side: right
  - name: ethernet
    position: {x: 85mm, y: 10.25mm, z: 0}
    dimensions: {width: 16mm, height: 13.5mm}
    side: right
  - name: gpio-header
    position: {x: 7.1mm, y: 0, z: 0}
    dimensions: {width: 50.8mm, height: 5mm}
    side: front

keepout_zones:
  - name: sd-card
    position: {x: 0, y: 22mm, z: -3mm}
    dimensions: {width: 5mm, depth: 17mm, height: 3mm}
    reason: "SD card protrudes from edge"

notes: |
  - Requires 5V/5A power via USB-C
  - Active cooling recommended for sustained loads
  - GPIO header is 40-pin, 2.54mm pitch
```

### 20x4 Character LCD (HD44780)

```yaml
id: lcd-20x4-hd44780
name: 20x4 Character LCD
category: displays
aliases:
  - 20x4 lcd
  - 2004 lcd
  - character lcd 20x4
  - hd44780 20x4

dimensions:
  width: 98mm
  depth: 60mm
  height: 12mm  # Including backlight

visible_area:
  width: 77mm
  height: 26mm
  offset_x: 10.5mm  # From left edge
  offset_y: 17mm    # From top edge

mounting_holes:
  - x: 2.5mm
    y: 2.5mm
    diameter: 3.2mm
    type: through
  - x: 95.5mm
    y: 2.5mm
    diameter: 3.2mm
    type: through
  - x: 2.5mm
    y: 57.5mm
    diameter: 3.2mm
    type: through
  - x: 95.5mm
    y: 57.5mm
    diameter: 3.2mm
    type: through

notes: |
  - Viewing angle: 6 o'clock
  - Backlight: LED (white or blue/green)
  - Interface: Parallel 4-bit or 8-bit, or I2C with adapter
```

### 6mm Tactile Button

```yaml
id: tactile-button-6mm
name: 6mm Tactile Button
category: buttons
aliases:
  - tactile switch
  - push button
  - momentary button
  - tact switch

dimensions:
  width: 6mm
  depth: 6mm
  height: 5mm  # Body height, not including actuator

actuator:
  diameter: 3.5mm
  height: 2.5mm  # Above body

mounting:
  type: through-hole
  hole_diameter: 1mm
  hole_spacing: 4.5mm  # Between pins

notes: |
  - Actuation force: 160-260gf typical
  - Travel: 0.25mm
  - Lifespan: 100,000+ cycles
```

---

## Fuzzy Matching Rules

The component registry uses fuzzy matching to handle natural language:

### Matching Priority

1. **Exact ID match**: `raspberry-pi-5`
2. **Exact alias match**: `pi 5`
3. **Case-insensitive match**: `Raspberry Pi 5`
4. **Fuzzy match (Levenshtein)**: `rasberry pi5` → `raspberry-pi-5`
5. **Partial match**: `pi` → offers disambiguation

### Disambiguation

When multiple components match, return options:

```json
{
  "ambiguous": true,
  "query": "pi",
  "matches": [
    {"id": "raspberry-pi-5", "score": 0.8},
    {"id": "raspberry-pi-4", "score": 0.8},
    {"id": "raspberry-pi-zero-2w", "score": 0.7}
  ],
  "suggestion": "Did you mean 'Raspberry Pi 5'?"
}
```

---

## Extension Guidelines

### Adding New Components

1. Verify dimensions from official datasheet
2. Measure physical sample if possible
3. Include all mounting holes with accurate positions
4. Document port positions relative to board origin
5. Note any keepout zones or special requirements
6. Add common aliases for fuzzy matching
7. Include datasheet URL for reference

### Component Versioning

Components use semantic versioning when specs change:

```
raspberry-pi-5       # Current/latest
raspberry-pi-5-v1    # Specific revision if needed
```

### Community Contributions

Future: Allow user-submitted component definitions with:
- Validation against schema
- Dimension verification workflow
- Community review process

---

## Priority Definitions

| Priority | Description | Timeline |
|----------|-------------|----------|
| P0 | Required for MVP, test case validation | Phase 2 |
| P1 | Common components, should include | Phase 2 |
| P2 | Nice to have, can add later | Post-MVP |

---

*Document created: January 29, 2026*
*Last updated: January 29, 2026*
