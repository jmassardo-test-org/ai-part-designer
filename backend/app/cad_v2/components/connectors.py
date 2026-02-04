"""Connector definitions for CAD v2.

Includes common connectors for power, data, and video.
"""

from app.cad_v2.schemas.base import BoundingBox, Dimension, Point3D
from app.cad_v2.schemas.components import (
    ComponentCategory,
    ComponentDefinition,
    MountingHole,
    PortDefinition,
)
from app.cad_v2.schemas.enclosure import WallSide


def get_connector_components() -> list[ComponentDefinition]:
    """Get all connector component definitions."""
    return [
        _usb_c_receptacle(),
        _usb_a_receptacle(),
        _micro_usb_receptacle(),
        _barrel_jack_55x21(),
        _hdmi_receptacle(),
        _micro_hdmi_receptacle(),
        _ethernet_rj45(),
        _audio_jack_35mm(),
        _sd_card_slot(),
    ]


def _usb_c_receptacle() -> ComponentDefinition:
    """USB-C Panel Mount Receptacle."""
    return ComponentDefinition(
        id="usb-c-receptacle",
        name="USB-C Receptacle",
        category=ComponentCategory.CONNECTOR,
        aliases=[
            "usb-c",
            "usb c",
            "usb type-c",
            "usbc",
            "usb c port",
        ],
        dimensions=BoundingBox(
            width=Dimension(value=9.0),
            depth=Dimension(value=7.5),
            height=Dimension(value=3.5),
        ),
        mounting_holes=[],
        ports=[
            PortDefinition(
                name="opening",
                position=Point3D(x=4.5, y=0, z=1.75),
                width=Dimension(value=9.0),
                height=Dimension(value=3.5),
                side=WallSide.FRONT,
            ),
        ],
        notes="""
Panel cutout: 9mm x 3.5mm with 0.5mm radius corners
Reversible connector
USB 2.0, 3.0, or 3.1 depending on device
""".strip(),
    )


def _usb_a_receptacle() -> ComponentDefinition:
    """USB-A Panel Mount Receptacle."""
    return ComponentDefinition(
        id="usb-a-receptacle",
        name="USB-A Receptacle",
        category=ComponentCategory.CONNECTOR,
        aliases=[
            "usb-a",
            "usb a",
            "usb type-a",
            "usb port",
            "usb",
        ],
        dimensions=BoundingBox(
            width=Dimension(value=14.5),
            depth=Dimension(value=14.0),
            height=Dimension(value=7.0),
        ),
        mounting_holes=[],
        ports=[
            PortDefinition(
                name="opening",
                position=Point3D(x=7.25, y=0, z=3.5),
                width=Dimension(value=13.0),
                height=Dimension(value=6.0),
                side=WallSide.FRONT,
            ),
        ],
        notes="""
Panel cutout: 13mm x 6mm (standard USB-A opening)
Stacked dual ports require 15mm x 16mm cutout
""".strip(),
    )


def _micro_usb_receptacle() -> ComponentDefinition:
    """Micro-USB Panel Mount Receptacle."""
    return ComponentDefinition(
        id="micro-usb-receptacle",
        name="Micro-USB Receptacle",
        category=ComponentCategory.CONNECTOR,
        aliases=[
            "micro-usb",
            "micro usb",
            "microusb",
            "micro usb port",
        ],
        dimensions=BoundingBox(
            width=Dimension(value=8.0),
            depth=Dimension(value=5.0),
            height=Dimension(value=3.0),
        ),
        mounting_holes=[],
        ports=[
            PortDefinition(
                name="opening",
                position=Point3D(x=4.0, y=0, z=1.5),
                width=Dimension(value=8.0),
                height=Dimension(value=3.0),
                side=WallSide.FRONT,
            ),
        ],
        notes="""
Panel cutout: 8mm x 3mm
Legacy connector, prefer USB-C for new designs
""".strip(),
    )


def _barrel_jack_55x21() -> ComponentDefinition:
    """5.5mm x 2.1mm DC Barrel Jack."""
    return ComponentDefinition(
        id="barrel-jack-5521",
        name="DC Barrel Jack 5.5x2.1mm",
        category=ComponentCategory.CONNECTOR,
        aliases=[
            "barrel jack",
            "dc jack",
            "power jack",
            "5.5x2.1",
            "barrel connector",
            "dc power jack",
        ],
        dimensions=BoundingBox(
            width=Dimension(value=14.0),
            depth=Dimension(value=9.0),
            height=Dimension(value=11.0),
        ),
        mounting_holes=[],
        ports=[
            PortDefinition(
                name="opening",
                position=Point3D(x=7.0, y=0, z=5.5),
                width=Dimension(value=8.0),  # Outer barrel diameter
                height=Dimension(value=8.0),
                side=WallSide.FRONT,
            ),
        ],
        notes="""
Panel cutout: 8mm diameter
Standard Arduino/hobby power connector
Center positive is typical (verify for your PSU)
""".strip(),
    )


def _hdmi_receptacle() -> ComponentDefinition:
    """Full-size HDMI Type-A Receptacle."""
    return ComponentDefinition(
        id="hdmi-receptacle",
        name="HDMI Receptacle",
        category=ComponentCategory.CONNECTOR,
        aliases=[
            "hdmi",
            "hdmi port",
            "hdmi type-a",
            "full hdmi",
        ],
        dimensions=BoundingBox(
            width=Dimension(value=15.0),
            depth=Dimension(value=12.0),
            height=Dimension(value=6.0),
        ),
        mounting_holes=[],
        ports=[
            PortDefinition(
                name="opening",
                position=Point3D(x=7.5, y=0, z=3.0),
                width=Dimension(value=15.0),
                height=Dimension(value=6.0),
                side=WallSide.FRONT,
            ),
        ],
        notes="""
Panel cutout: 15mm x 6mm
Tapered shape - narrower at bottom
""".strip(),
    )


def _micro_hdmi_receptacle() -> ComponentDefinition:
    """Micro-HDMI Type-D Receptacle."""
    return ComponentDefinition(
        id="micro-hdmi-receptacle",
        name="Micro-HDMI Receptacle",
        category=ComponentCategory.CONNECTOR,
        aliases=[
            "micro-hdmi",
            "micro hdmi",
            "hdmi type-d",
            "microhdmi",
        ],
        dimensions=BoundingBox(
            width=Dimension(value=7.0),
            depth=Dimension(value=5.5),
            height=Dimension(value=3.5),
        ),
        mounting_holes=[],
        ports=[
            PortDefinition(
                name="opening",
                position=Point3D(x=3.5, y=0, z=1.75),
                width=Dimension(value=7.0),
                height=Dimension(value=3.5),
                side=WallSide.FRONT,
            ),
        ],
        notes="""
Panel cutout: 7mm x 3.5mm
Used on Raspberry Pi 4/5 and compact devices
""".strip(),
    )


def _ethernet_rj45() -> ComponentDefinition:
    """RJ45 Ethernet Jack."""
    return ComponentDefinition(
        id="ethernet-rj45",
        name="RJ45 Ethernet Jack",
        category=ComponentCategory.CONNECTOR,
        aliases=[
            "ethernet",
            "rj45",
            "lan port",
            "network jack",
            "ethernet port",
        ],
        dimensions=BoundingBox(
            width=Dimension(value=16.0),
            depth=Dimension(value=16.0),
            height=Dimension(value=13.5),
        ),
        mounting_holes=[],
        ports=[
            PortDefinition(
                name="opening",
                position=Point3D(x=8.0, y=0, z=6.75),
                width=Dimension(value=16.0),
                height=Dimension(value=13.5),
                side=WallSide.FRONT,
            ),
        ],
        notes="""
Panel cutout: 16mm x 13.5mm
May include LED indicators (add 2mm height)
8P8C modular connector
""".strip(),
    )


def _audio_jack_35mm() -> ComponentDefinition:
    """3.5mm Audio Jack (TRS/TRRS)."""
    return ComponentDefinition(
        id="audio-jack-35mm",
        name="3.5mm Audio Jack",
        category=ComponentCategory.CONNECTOR,
        aliases=[
            "audio jack",
            "headphone jack",
            "3.5mm jack",
            "aux jack",
            "headphone",
        ],
        dimensions=BoundingBox(
            width=Dimension(value=7.0),
            depth=Dimension(value=14.0),
            height=Dimension(value=6.0),
        ),
        mounting_holes=[],
        ports=[
            PortDefinition(
                name="opening",
                position=Point3D(x=3.5, y=0, z=3.0),
                width=Dimension(value=7.0),  # Larger than 3.5mm for plug body
                height=Dimension(value=6.0),
                side=WallSide.FRONT,
            ),
        ],
        notes="""
Panel cutout: 6mm diameter (for plug insertion)
TRS (3 conductor) or TRRS (4 conductor)
May have internal switch contacts
""".strip(),
    )


def _sd_card_slot() -> ComponentDefinition:
    """Full-size SD Card Slot."""
    return ComponentDefinition(
        id="sd-card-slot",
        name="SD Card Slot",
        category=ComponentCategory.CONNECTOR,
        aliases=[
            "sd card",
            "sd slot",
            "memory card slot",
        ],
        dimensions=BoundingBox(
            width=Dimension(value=28.0),
            depth=Dimension(value=29.0),
            height=Dimension(value=3.0),
        ),
        mounting_holes=[],
        ports=[
            PortDefinition(
                name="opening",
                position=Point3D(x=14.0, y=0, z=1.5),
                width=Dimension(value=26.0),
                height=Dimension(value=3.0),
                side=WallSide.FRONT,
            ),
        ],
        notes="""
Panel cutout: 26mm x 3mm
Card insertion depth: ~15mm
Push-push or friction hold variants
""".strip(),
    )
