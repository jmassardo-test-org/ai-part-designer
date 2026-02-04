"""Single Board Computer definitions for CAD v2.

Accurate dimensions from official documentation:
- Raspberry Pi: https://www.raspberrypi.com/documentation/computers/
- Arduino: https://docs.arduino.cc/hardware/
"""

from app.cad_v2.schemas.base import BoundingBox, Dimension, Point3D
from app.cad_v2.schemas.components import (
    ComponentCategory,
    ComponentDefinition,
    KeepoutZone,
    MountingHole,
    PortDefinition,
)
from app.cad_v2.schemas.enclosure import WallSide


def get_board_components() -> list[ComponentDefinition]:
    """Get all board component definitions."""
    return [
        _raspberry_pi_5(),
        _raspberry_pi_4b(),
        _raspberry_pi_3b_plus(),
        _raspberry_pi_zero_2w(),
        _arduino_uno_r3(),
        _arduino_nano(),
        _esp32_devkit(),
    ]


def _raspberry_pi_5() -> ComponentDefinition:
    """Raspberry Pi 5 - Official dimensions from mechanical drawing."""
    return ComponentDefinition(
        id="raspberry-pi-5",
        name="Raspberry Pi 5",
        category=ComponentCategory.BOARD,
        aliases=[
            "rpi5",
            "pi 5",
            "pi5",
            "raspberry pi 5",
            "rpi 5",
        ],
        dimensions=BoundingBox(
            width=Dimension(value=85.0),
            depth=Dimension(value=56.0),
            height=Dimension(value=17.0),  # Including tallest component
        ),
        mounting_holes=[
            # Standard Raspberry Pi mounting pattern (M2.5)
            MountingHole(x=3.5, y=3.5, diameter=Dimension(value=2.7)),
            MountingHole(x=61.5, y=3.5, diameter=Dimension(value=2.7)),
            MountingHole(x=3.5, y=52.5, diameter=Dimension(value=2.7)),
            MountingHole(x=61.5, y=52.5, diameter=Dimension(value=2.7)),
        ],
        ports=[
            # USB-C Power (left side of back edge)
            PortDefinition(
                name="usb-c-power",
                position=Point3D(x=11.2, y=56.0, z=0),
                width=Dimension(value=9.0),
                height=Dimension(value=3.5),
                side=WallSide.BACK,
            ),
            # Micro HDMI 0
            PortDefinition(
                name="micro-hdmi-0",
                position=Point3D(x=26.0, y=56.0, z=0),
                width=Dimension(value=7.0),
                height=Dimension(value=3.5),
                side=WallSide.BACK,
            ),
            # Micro HDMI 1
            PortDefinition(
                name="micro-hdmi-1",
                position=Point3D(x=39.0, y=56.0, z=0),
                width=Dimension(value=7.0),
                height=Dimension(value=3.5),
                side=WallSide.BACK,
            ),
            # USB-A 3.0 (stacked, lower)
            PortDefinition(
                name="usb-a-2",
                position=Point3D(x=85.0, y=29.0, z=0),
                width=Dimension(value=15.0),
                height=Dimension(value=16.0),
                side=WallSide.RIGHT,
            ),
            # USB-A 3.0 (stacked, upper)
            PortDefinition(
                name="usb-a-3",
                position=Point3D(x=85.0, y=47.0, z=0),
                width=Dimension(value=15.0),
                height=Dimension(value=16.0),
                side=WallSide.RIGHT,
            ),
            # Ethernet
            PortDefinition(
                name="ethernet",
                position=Point3D(x=85.0, y=10.25, z=0),
                width=Dimension(value=16.0),
                height=Dimension(value=13.5),
                side=WallSide.RIGHT,
            ),
            # GPIO Header
            PortDefinition(
                name="gpio-header",
                position=Point3D(x=7.1, y=50.0, z=0),
                width=Dimension(value=50.8),
                height=Dimension(value=5.0),
                side=WallSide.TOP,
            ),
            # 3.5mm Audio Jack
            PortDefinition(
                name="audio-jack",
                position=Point3D(x=53.5, y=56.0, z=0),
                width=Dimension(value=7.0),
                height=Dimension(value=6.0),
                side=WallSide.BACK,
            ),
        ],
        keepout_zones=[
            KeepoutZone(
                name="sd-card",
                position=Point3D(x=0, y=22.0, z=-3.0),
                width=Dimension(value=5.0),
                depth=Dimension(value=17.0),
                height=Dimension(value=3.0),
                reason="SD card protrudes from edge",
            ),
            KeepoutZone(
                name="pcie-connector",
                position=Point3D(x=22.0, y=0, z=0),
                width=Dimension(value=22.0),
                depth=Dimension(value=5.0),
                height=Dimension(value=4.0),
                reason="PCIe FFC connector",
            ),
        ],
        datasheet_url="https://datasheets.raspberrypi.com/rpi5/raspberry-pi-5-mechanical-drawing.pdf",
        notes="Requires 5V/5A power via USB-C. Active cooling recommended for sustained loads.",
    )


def _raspberry_pi_4b() -> ComponentDefinition:
    """Raspberry Pi 4 Model B - Official dimensions."""
    return ComponentDefinition(
        id="raspberry-pi-4b",
        name="Raspberry Pi 4 Model B",
        category=ComponentCategory.BOARD,
        aliases=[
            "rpi4",
            "pi 4",
            "pi4",
            "raspberry pi 4",
            "rpi 4",
            "pi 4b",
            "raspberry pi 4b",
        ],
        dimensions=BoundingBox(
            width=Dimension(value=85.0),
            depth=Dimension(value=56.0),
            height=Dimension(value=17.0),
        ),
        mounting_holes=[
            MountingHole(x=3.5, y=3.5, diameter=Dimension(value=2.7)),
            MountingHole(x=61.5, y=3.5, diameter=Dimension(value=2.7)),
            MountingHole(x=3.5, y=52.5, diameter=Dimension(value=2.7)),
            MountingHole(x=61.5, y=52.5, diameter=Dimension(value=2.7)),
        ],
        ports=[
            PortDefinition(
                name="usb-c-power",
                position=Point3D(x=11.2, y=56.0, z=0),
                width=Dimension(value=9.0),
                height=Dimension(value=3.5),
                side=WallSide.BACK,
            ),
            PortDefinition(
                name="micro-hdmi-0",
                position=Point3D(x=26.0, y=56.0, z=0),
                width=Dimension(value=7.0),
                height=Dimension(value=3.5),
                side=WallSide.BACK,
            ),
            PortDefinition(
                name="micro-hdmi-1",
                position=Point3D(x=39.5, y=56.0, z=0),
                width=Dimension(value=7.0),
                height=Dimension(value=3.5),
                side=WallSide.BACK,
            ),
            PortDefinition(
                name="usb-a-2",
                position=Point3D(x=85.0, y=29.0, z=0),
                width=Dimension(value=15.0),
                height=Dimension(value=16.0),
                side=WallSide.RIGHT,
            ),
            PortDefinition(
                name="usb-a-3",
                position=Point3D(x=85.0, y=47.0, z=0),
                width=Dimension(value=15.0),
                height=Dimension(value=16.0),
                side=WallSide.RIGHT,
            ),
            PortDefinition(
                name="ethernet",
                position=Point3D(x=85.0, y=10.25, z=0),
                width=Dimension(value=16.0),
                height=Dimension(value=13.5),
                side=WallSide.RIGHT,
            ),
            PortDefinition(
                name="audio-jack",
                position=Point3D(x=53.5, y=56.0, z=0),
                width=Dimension(value=7.0),
                height=Dimension(value=6.0),
                side=WallSide.BACK,
            ),
        ],
        keepout_zones=[
            KeepoutZone(
                name="sd-card",
                position=Point3D(x=0, y=22.0, z=-3.0),
                width=Dimension(value=5.0),
                depth=Dimension(value=17.0),
                height=Dimension(value=3.0),
                reason="SD card protrudes from edge",
            ),
        ],
        datasheet_url="https://datasheets.raspberrypi.com/rpi4/raspberry-pi-4-mechanical-drawing.pdf",
        notes="Requires 5V/3A power via USB-C. Same mounting pattern as Pi 3B+.",
    )


def _raspberry_pi_3b_plus() -> ComponentDefinition:
    """Raspberry Pi 3 Model B+ - Official dimensions."""
    return ComponentDefinition(
        id="raspberry-pi-3b-plus",
        name="Raspberry Pi 3 Model B+",
        category=ComponentCategory.BOARD,
        aliases=[
            "rpi3b+",
            "pi 3b+",
            "pi3b+",
            "raspberry pi 3b+",
            "rpi 3b+",
            "pi 3 b+",
            "raspberry pi 3 model b+",
        ],
        dimensions=BoundingBox(
            width=Dimension(value=85.0),
            depth=Dimension(value=56.0),
            height=Dimension(value=17.0),
        ),
        mounting_holes=[
            MountingHole(x=3.5, y=3.5, diameter=Dimension(value=2.7)),
            MountingHole(x=61.5, y=3.5, diameter=Dimension(value=2.7)),
            MountingHole(x=3.5, y=52.5, diameter=Dimension(value=2.7)),
            MountingHole(x=61.5, y=52.5, diameter=Dimension(value=2.7)),
        ],
        ports=[
            PortDefinition(
                name="micro-usb-power",
                position=Point3D(x=10.6, y=56.0, z=0),
                width=Dimension(value=8.0),
                height=Dimension(value=3.0),
                side=WallSide.BACK,
            ),
            PortDefinition(
                name="hdmi",
                position=Point3D(x=32.0, y=56.0, z=0),
                width=Dimension(value=15.0),
                height=Dimension(value=6.0),
                side=WallSide.BACK,
            ),
            PortDefinition(
                name="usb-a-2",
                position=Point3D(x=85.0, y=29.0, z=0),
                width=Dimension(value=15.0),
                height=Dimension(value=16.0),
                side=WallSide.RIGHT,
            ),
            PortDefinition(
                name="usb-a-3",
                position=Point3D(x=85.0, y=47.0, z=0),
                width=Dimension(value=15.0),
                height=Dimension(value=16.0),
                side=WallSide.RIGHT,
            ),
            PortDefinition(
                name="ethernet",
                position=Point3D(x=85.0, y=10.25, z=0),
                width=Dimension(value=16.0),
                height=Dimension(value=13.5),
                side=WallSide.RIGHT,
            ),
            PortDefinition(
                name="audio-jack",
                position=Point3D(x=53.5, y=56.0, z=0),
                width=Dimension(value=7.0),
                height=Dimension(value=6.0),
                side=WallSide.BACK,
            ),
        ],
        keepout_zones=[
            KeepoutZone(
                name="sd-card",
                position=Point3D(x=0, y=22.0, z=-3.0),
                width=Dimension(value=5.0),
                depth=Dimension(value=17.0),
                height=Dimension(value=3.0),
                reason="SD card protrudes from edge",
            ),
        ],
        datasheet_url="https://datasheets.raspberrypi.com/rpi3/raspberry-pi-3-b-plus-mechanical-drawing.pdf",
        notes="Full-size HDMI and Micro-USB power. Same mounting pattern as Pi 4.",
    )


def _raspberry_pi_zero_2w() -> ComponentDefinition:
    """Raspberry Pi Zero 2 W - Official dimensions."""
    return ComponentDefinition(
        id="raspberry-pi-zero-2w",
        name="Raspberry Pi Zero 2 W",
        category=ComponentCategory.BOARD,
        aliases=[
            "pi zero 2",
            "pi zero 2 w",
            "rpi zero 2w",
            "zero 2 w",
            "raspberry pi zero 2 w",
            "pi zero",
        ],
        dimensions=BoundingBox(
            width=Dimension(value=65.0),
            depth=Dimension(value=30.0),
            height=Dimension(value=5.0),
        ),
        mounting_holes=[
            MountingHole(x=3.5, y=3.5, diameter=Dimension(value=2.7)),
            MountingHole(x=61.5, y=3.5, diameter=Dimension(value=2.7)),
            MountingHole(x=3.5, y=26.5, diameter=Dimension(value=2.7)),
            MountingHole(x=61.5, y=26.5, diameter=Dimension(value=2.7)),
        ],
        ports=[
            PortDefinition(
                name="micro-usb-power",
                position=Point3D(x=6.0, y=30.0, z=0),
                width=Dimension(value=8.0),
                height=Dimension(value=3.0),
                side=WallSide.BACK,
            ),
            PortDefinition(
                name="micro-usb-data",
                position=Point3D(x=20.0, y=30.0, z=0),
                width=Dimension(value=8.0),
                height=Dimension(value=3.0),
                side=WallSide.BACK,
            ),
            PortDefinition(
                name="mini-hdmi",
                position=Point3D(x=36.5, y=30.0, z=0),
                width=Dimension(value=11.0),
                height=Dimension(value=3.5),
                side=WallSide.BACK,
            ),
        ],
        keepout_zones=[
            KeepoutZone(
                name="sd-card",
                position=Point3D(x=0, y=8.0, z=-3.0),
                width=Dimension(value=5.0),
                depth=Dimension(value=14.0),
                height=Dimension(value=3.0),
                reason="SD card protrudes from edge",
            ),
        ],
        datasheet_url="https://datasheets.raspberrypi.com/rpizero2/raspberry-pi-zero-2-w-mechanical-drawing.pdf",
        notes="Compact form factor. Mini-HDMI and Micro-USB ports.",
    )


def _arduino_uno_r3() -> ComponentDefinition:
    """Arduino Uno R3 - Official dimensions."""
    return ComponentDefinition(
        id="arduino-uno-r3",
        name="Arduino Uno R3",
        category=ComponentCategory.BOARD,
        aliases=[
            "arduino uno",
            "uno r3",
            "uno",
            "arduino",
        ],
        dimensions=BoundingBox(
            width=Dimension(value=68.6),
            depth=Dimension(value=53.4),
            height=Dimension(value=15.0),
        ),
        mounting_holes=[
            MountingHole(x=14.0, y=2.5, diameter=Dimension(value=3.2)),
            MountingHole(x=66.0, y=7.6, diameter=Dimension(value=3.2)),
            MountingHole(x=66.0, y=35.6, diameter=Dimension(value=3.2)),
            MountingHole(x=15.2, y=50.8, diameter=Dimension(value=3.2)),
        ],
        ports=[
            PortDefinition(
                name="usb-b",
                position=Point3D(x=9.0, y=0, z=0),
                width=Dimension(value=12.0),
                height=Dimension(value=11.0),
                side=WallSide.FRONT,
            ),
            PortDefinition(
                name="barrel-jack",
                position=Point3D(x=0, y=7.0, z=0),
                width=Dimension(value=9.0),
                height=Dimension(value=11.0),
                side=WallSide.LEFT,
            ),
        ],
        datasheet_url="https://docs.arduino.cc/resources/datasheets/A000066-datasheet.pdf",
        notes="5V logic. USB-B for programming. 7-12V barrel jack power.",
    )


def _arduino_nano() -> ComponentDefinition:
    """Arduino Nano - Official dimensions."""
    return ComponentDefinition(
        id="arduino-nano",
        name="Arduino Nano",
        category=ComponentCategory.BOARD,
        aliases=[
            "nano",
            "arduino nano v3",
        ],
        dimensions=BoundingBox(
            width=Dimension(value=43.2),
            depth=Dimension(value=18.5),
            height=Dimension(value=8.0),
        ),
        mounting_holes=[
            # Arduino Nano has no mounting holes - typically breadboard mounted
        ],
        ports=[
            PortDefinition(
                name="mini-usb",
                position=Point3D(x=21.6, y=0, z=0),
                width=Dimension(value=8.0),
                height=Dimension(value=4.0),
                side=WallSide.FRONT,
            ),
        ],
        notes="Breadboard-friendly form factor. No mounting holes - use pin headers.",
    )


def _esp32_devkit() -> ComponentDefinition:
    """ESP32 DevKit V1 - Common development board."""
    return ComponentDefinition(
        id="esp32-devkit-v1",
        name="ESP32 DevKit V1",
        category=ComponentCategory.BOARD,
        aliases=[
            "esp32",
            "esp32 devkit",
            "esp32-wroom",
            "esp32 dev board",
        ],
        dimensions=BoundingBox(
            width=Dimension(value=51.4),
            depth=Dimension(value=28.0),
            height=Dimension(value=8.0),
        ),
        mounting_holes=[
            # ESP32 DevKit has mounting holes at corners
            MountingHole(x=2.5, y=2.5, diameter=Dimension(value=3.0)),
            MountingHole(x=48.9, y=2.5, diameter=Dimension(value=3.0)),
            MountingHole(x=2.5, y=25.5, diameter=Dimension(value=3.0)),
            MountingHole(x=48.9, y=25.5, diameter=Dimension(value=3.0)),
        ],
        ports=[
            PortDefinition(
                name="micro-usb",
                position=Point3D(x=25.7, y=0, z=0),
                width=Dimension(value=8.0),
                height=Dimension(value=3.0),
                side=WallSide.FRONT,
            ),
        ],
        notes="WiFi and Bluetooth capable. 3.3V logic.",
    )
