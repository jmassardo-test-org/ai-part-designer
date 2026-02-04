"""Display component definitions for CAD v2.

Includes LCD character displays and OLED displays.
"""

from app.cad_v2.schemas.base import BoundingBox, Dimension, Point3D
from app.cad_v2.schemas.components import (
    ComponentCategory,
    ComponentDefinition,
    MountingHole,
    PortDefinition,
)
from app.cad_v2.schemas.enclosure import WallSide


def get_display_components() -> list[ComponentDefinition]:
    """Get all display component definitions."""
    return [
        _lcd_20x4(),
        _lcd_16x2(),
        _oled_096(),
        _oled_130(),
    ]


def _lcd_20x4() -> ComponentDefinition:
    """20x4 Character LCD with HD44780 controller."""
    return ComponentDefinition(
        id="lcd-20x4-hd44780",
        name="20x4 Character LCD",
        category=ComponentCategory.DISPLAY,
        aliases=[
            "20x4 lcd",
            "2004 lcd",
            "character lcd 20x4",
            "hd44780 20x4",
            "20x4 display",
            "2004a lcd",
            "lcd 20x4",
        ],
        dimensions=BoundingBox(
            width=Dimension(value=98.0),
            depth=Dimension(value=60.0),
            height=Dimension(value=12.0),  # Including backlight
        ),
        mounting_holes=[
            MountingHole(x=2.5, y=2.5, diameter=Dimension(value=3.2)),
            MountingHole(x=95.5, y=2.5, diameter=Dimension(value=3.2)),
            MountingHole(x=2.5, y=57.5, diameter=Dimension(value=3.2)),
            MountingHole(x=95.5, y=57.5, diameter=Dimension(value=3.2)),
        ],
        ports=[
            # Visible area (for cutout reference)
            PortDefinition(
                name="viewing-area",
                position=Point3D(x=49.0, y=30.0, z=12.0),  # Centered
                width=Dimension(value=77.0),
                height=Dimension(value=26.0),
                side=WallSide.TOP,
            ),
        ],
        notes="""
Viewing area: 77mm x 26mm
Character size: 4.84mm x 9.66mm (visible)
Backlight: LED (white, blue/green, or yellow/green)
Interface: Parallel 4-bit or 8-bit, or I2C with adapter module
Viewing angle: 6 o'clock
Offset from left edge to viewing area: 10.5mm
Offset from top edge to viewing area: 17mm
""".strip(),
    )


def _lcd_16x2() -> ComponentDefinition:
    """16x2 Character LCD with HD44780 controller."""
    return ComponentDefinition(
        id="lcd-16x2-hd44780",
        name="16x2 Character LCD",
        category=ComponentCategory.DISPLAY,
        aliases=[
            "16x2 lcd",
            "1602 lcd",
            "character lcd 16x2",
            "hd44780 16x2",
            "16x2 display",
            "1602a lcd",
            "lcd 16x2",
        ],
        dimensions=BoundingBox(
            width=Dimension(value=80.0),
            depth=Dimension(value=36.0),
            height=Dimension(value=12.0),
        ),
        mounting_holes=[
            MountingHole(x=2.5, y=2.5, diameter=Dimension(value=3.0)),
            MountingHole(x=77.5, y=2.5, diameter=Dimension(value=3.0)),
            MountingHole(x=2.5, y=33.5, diameter=Dimension(value=3.0)),
            MountingHole(x=77.5, y=33.5, diameter=Dimension(value=3.0)),
        ],
        ports=[
            PortDefinition(
                name="viewing-area",
                position=Point3D(x=40.0, y=18.0, z=12.0),
                width=Dimension(value=64.5),
                height=Dimension(value=14.5),
                side=WallSide.TOP,
            ),
        ],
        notes="""
Viewing area: 64.5mm x 14.5mm
Character size: 4.84mm x 9.66mm (visible)
Backlight: LED
Interface: Parallel 4-bit or 8-bit, or I2C with adapter
Offset from left edge to viewing area: 7.75mm
Offset from top edge to viewing area: 10.75mm
""".strip(),
    )


def _oled_096() -> ComponentDefinition:
    """0.96" OLED Display (SSD1306)."""
    return ComponentDefinition(
        id="oled-096-ssd1306",
        name='0.96" OLED Display',
        category=ComponentCategory.DISPLAY,
        aliases=[
            "0.96 oled",
            "ssd1306",
            "0.96 inch oled",
            "oled 128x64",
            "i2c oled",
            "small oled",
        ],
        dimensions=BoundingBox(
            width=Dimension(value=27.0),
            depth=Dimension(value=27.0),
            height=Dimension(value=4.0),
        ),
        mounting_holes=[
            MountingHole(x=2.0, y=2.0, diameter=Dimension(value=2.0)),
            MountingHole(x=25.0, y=2.0, diameter=Dimension(value=2.0)),
            MountingHole(x=2.0, y=25.0, diameter=Dimension(value=2.0)),
            MountingHole(x=25.0, y=25.0, diameter=Dimension(value=2.0)),
        ],
        ports=[
            PortDefinition(
                name="viewing-area",
                position=Point3D(x=13.5, y=15.0, z=4.0),
                width=Dimension(value=21.7),
                height=Dimension(value=10.9),
                side=WallSide.TOP,
            ),
        ],
        notes="""
Resolution: 128x64 pixels
Viewing area: 21.74mm x 10.86mm
Interface: I2C (0x3C or 0x3D) or SPI
Voltage: 3.3V or 5V (check module)
""".strip(),
    )


def _oled_130() -> ComponentDefinition:
    """1.3" OLED Display (SH1106)."""
    return ComponentDefinition(
        id="oled-130-sh1106",
        name='1.3" OLED Display',
        category=ComponentCategory.DISPLAY,
        aliases=[
            "1.3 oled",
            "sh1106",
            "1.3 inch oled",
            "oled 128x64 1.3",
        ],
        dimensions=BoundingBox(
            width=Dimension(value=35.0),
            depth=Dimension(value=33.0),
            height=Dimension(value=4.0),
        ),
        mounting_holes=[
            MountingHole(x=2.5, y=2.5, diameter=Dimension(value=2.5)),
            MountingHole(x=32.5, y=2.5, diameter=Dimension(value=2.5)),
            MountingHole(x=2.5, y=30.5, diameter=Dimension(value=2.5)),
            MountingHole(x=32.5, y=30.5, diameter=Dimension(value=2.5)),
        ],
        ports=[
            PortDefinition(
                name="viewing-area",
                position=Point3D(x=17.5, y=18.0, z=4.0),
                width=Dimension(value=30.0),
                height=Dimension(value=15.0),
                side=WallSide.TOP,
            ),
        ],
        notes="""
Resolution: 128x64 pixels
Viewing area: ~30mm x 15mm
Interface: I2C or SPI
Voltage: 3.3V or 5V (check module)
""".strip(),
    )
