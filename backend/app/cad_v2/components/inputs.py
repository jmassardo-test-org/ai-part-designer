"""Input device definitions for CAD v2.

Includes buttons, switches, and rotary encoders.
"""

from app.cad_v2.schemas.base import BoundingBox, Dimension, Point3D
from app.cad_v2.schemas.components import (
    ComponentCategory,
    ComponentDefinition,
    MountingHole,
    PortDefinition,
)
from app.cad_v2.schemas.enclosure import WallSide


def get_input_components() -> list[ComponentDefinition]:
    """Get all input component definitions."""
    return [
        _tactile_button_6mm(),
        _tactile_button_12mm(),
        _arcade_button_24mm(),
        _rotary_encoder(),
        _potentiometer_9mm(),
    ]


def _tactile_button_6mm() -> ComponentDefinition:
    """6mm Tactile Button (through-hole)."""
    return ComponentDefinition(
        id="tactile-button-6mm",
        name="6mm Tactile Button",
        category=ComponentCategory.INPUT,
        aliases=[
            "tactile switch",
            "push button",
            "momentary button",
            "tact switch",
            "6mm button",
            "small button",
            "tactile button",
        ],
        dimensions=BoundingBox(
            width=Dimension(value=6.0),
            depth=Dimension(value=6.0),
            height=Dimension(value=5.0),  # Body height
        ),
        mounting_holes=[],  # Through-hole soldered
        ports=[
            PortDefinition(
                name="actuator",
                position=Point3D(x=3.0, y=3.0, z=5.0),
                width=Dimension(value=3.5),  # Actuator diameter
                height=Dimension(value=2.5),  # Actuator height above body
                side=WallSide.TOP,
            ),
        ],
        notes="""
Actuator diameter: 3.5mm
Actuator height above body: 2.5mm (total height ~7.5mm)
Pin spacing: 4.5mm x 4.5mm
Actuation force: 160-260gf typical
Travel: 0.25mm
Lifespan: 100,000+ cycles
Panel cutout: 4mm diameter recommended
""".strip(),
    )


def _tactile_button_12mm() -> ComponentDefinition:
    """12mm Tactile Button (through-hole)."""
    return ComponentDefinition(
        id="tactile-button-12mm",
        name="12mm Tactile Button",
        category=ComponentCategory.INPUT,
        aliases=[
            "12mm button",
            "large tactile button",
            "12mm tact switch",
        ],
        dimensions=BoundingBox(
            width=Dimension(value=12.0),
            depth=Dimension(value=12.0),
            height=Dimension(value=5.0),
        ),
        mounting_holes=[],
        ports=[
            PortDefinition(
                name="actuator",
                position=Point3D(x=6.0, y=6.0, z=5.0),
                width=Dimension(value=6.0),
                height=Dimension(value=4.0),
                side=WallSide.TOP,
            ),
        ],
        notes="""
Actuator diameter: 6mm typical
Pin spacing: 6.5mm x 6.5mm
Panel cutout: 7mm diameter recommended
""".strip(),
    )


def _arcade_button_24mm() -> ComponentDefinition:
    """24mm Arcade Button (snap-in)."""
    return ComponentDefinition(
        id="arcade-button-24mm",
        name="24mm Arcade Button",
        category=ComponentCategory.INPUT,
        aliases=[
            "arcade button",
            "24mm button",
            "sanwa button",
            "game button",
        ],
        dimensions=BoundingBox(
            width=Dimension(value=24.0),  # Mounting hole diameter
            depth=Dimension(value=24.0),
            height=Dimension(value=33.0),  # Total height including switch
        ),
        mounting_holes=[],  # Snap-in mounting
        ports=[
            PortDefinition(
                name="button-cap",
                position=Point3D(x=12.0, y=12.0, z=10.0),
                width=Dimension(value=24.0),  # Cap visible diameter
                height=Dimension(value=10.0),  # Cap height above panel
                side=WallSide.TOP,
            ),
        ],
        notes="""
Panel mounting hole: 24mm diameter
Button cap diameter: 24mm (sits flush with hole)
Requires ~30mm clearance below panel
Snap-in tabs for mounting
Microswitch included
""".strip(),
    )


def _rotary_encoder() -> ComponentDefinition:
    """Rotary Encoder with push button (EC11 style)."""
    return ComponentDefinition(
        id="rotary-encoder-ec11",
        name="Rotary Encoder EC11",
        category=ComponentCategory.INPUT,
        aliases=[
            "rotary encoder",
            "encoder",
            "ec11",
            "volume knob",
            "dial",
        ],
        dimensions=BoundingBox(
            width=Dimension(value=12.0),
            depth=Dimension(value=12.0),
            height=Dimension(value=25.0),  # Including shaft
        ),
        mounting_holes=[],  # Panel mount with nut
        ports=[
            PortDefinition(
                name="shaft",
                position=Point3D(x=6.0, y=6.0, z=12.0),
                width=Dimension(value=6.0),  # Shaft diameter
                height=Dimension(value=15.0),  # Shaft length above body
                side=WallSide.TOP,
            ),
        ],
        notes="""
Shaft diameter: 6mm (D-shaped)
Panel mounting hole: 7mm diameter
Body: 12mm x 12mm x ~12mm
20 detents per rotation typical
Push-button integrated
Requires 7mm panel cutout
""".strip(),
    )


def _potentiometer_9mm() -> ComponentDefinition:
    """9mm Potentiometer (panel mount)."""
    return ComponentDefinition(
        id="potentiometer-9mm",
        name="9mm Potentiometer",
        category=ComponentCategory.INPUT,
        aliases=[
            "potentiometer",
            "pot",
            "9mm pot",
            "volume pot",
            "analog dial",
        ],
        dimensions=BoundingBox(
            width=Dimension(value=9.0),
            depth=Dimension(value=9.0),
            height=Dimension(value=20.0),  # Including shaft
        ),
        mounting_holes=[],  # Panel mount
        ports=[
            PortDefinition(
                name="shaft",
                position=Point3D(x=4.5, y=4.5, z=10.0),
                width=Dimension(value=6.0),
                height=Dimension(value=12.0),
                side=WallSide.TOP,
            ),
        ],
        notes="""
Shaft diameter: 6mm (knurled)
Panel mounting hole: 7mm diameter
Linear or logarithmic taper available
""".strip(),
    )
