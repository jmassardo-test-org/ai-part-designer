"""Component mounting schemas for CAD v2.

This module defines schemas for mounting components inside enclosures:
- Component references (by ID from component library)
- Mounting positions and orientations
- Standoff and mounting hole specifications
- Port exposure requirements

Components are referenced by ID from the component library,
which provides exact dimensions and mounting patterns.
"""

from enum import StrEnum
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

from app.cad_v2.schemas.base import Dimension, Point3D, Rotation
from app.cad_v2.schemas.enclosure import WallSide


class MountingType(StrEnum):
    """How a component is mounted."""

    STANDOFF = "standoff"  # Raised on standoffs with screws
    SURFACE = "surface"  # Directly on surface (glue/tape)
    CLIP = "clip"  # Clip-in mounting
    PRESS_FIT = "press_fit"  # Press into cavity
    BRACKET = "bracket"  # L-bracket or similar


class StandoffType(StrEnum):
    """Standoff designs."""

    CYLINDRICAL = "cylindrical"  # Round standoffs
    HEXAGONAL = "hexagonal"  # Hex standoffs (easier to print)
    SQUARE = "square"  # Square standoffs


class StandoffSpec(BaseModel):
    """Standoff specification for component mounting.

    Standoffs raise components off the enclosure floor,
    providing clearance for through-hole components and airflow.
    """

    model_config = ConfigDict(frozen=True)

    height: Dimension = Field(
        default_factory=lambda: Dimension(value=5.0),
        description="Standoff height from surface",
    )
    outer_diameter: Dimension = Field(
        default_factory=lambda: Dimension(value=6.0),
        description="Outer diameter of standoff",
    )
    hole_diameter: Dimension = Field(
        default_factory=lambda: Dimension(value=2.5),
        description="Screw hole diameter (e.g., 2.5mm for M2.5)",
    )
    type: StandoffType = Field(
        default=StandoffType.CYLINDRICAL,
        description="Standoff shape",
    )

    @classmethod
    def for_pi(cls) -> "StandoffSpec":
        """Standard standoffs for Raspberry Pi (M2.5)."""
        return cls(
            height=Dimension(value=5.0),
            outer_diameter=Dimension(value=6.0),
            hole_diameter=Dimension(value=2.5),
        )

    @classmethod
    def for_lcd(cls) -> "StandoffSpec":
        """Standard standoffs for LCD displays (M3)."""
        return cls(
            height=Dimension(value=3.0),
            outer_diameter=Dimension(value=7.0),
            hole_diameter=Dimension(value=3.0),
        )


class PortExposure(BaseModel):
    """Specification for exposing component ports through enclosure walls.

    When a component has ports (USB, HDMI, etc.), this specifies
    which ports should have cutouts in the enclosure walls.
    """

    model_config = ConfigDict(frozen=True)

    port_name: str = Field(..., description="Port name from component definition")
    side: WallSide = Field(..., description="Which wall to cut through")
    clearance: Dimension = Field(
        default_factory=lambda: Dimension(value=0.5),
        description="Extra clearance around port",
    )
    label: str | None = Field(default=None, description="Optional label near cutout")


class ComponentRef(BaseModel):
    """Reference to a component from the component library.

    Components are looked up by ID in the component registry.
    The registry provides dimensions, mounting holes, and port positions.
    """

    model_config = ConfigDict(frozen=True)

    component_id: str = Field(
        ...,
        description="Component ID from library (e.g., 'raspberry-pi-5')",
    )
    alias: str | None = Field(
        default=None,
        description="Natural language alias used in prompt (for debugging)",
    )


class ComponentMount(BaseModel):
    """A component mounted inside the enclosure.

    Combines a component reference with position, orientation,
    and mounting specifications.

    Example:
        >>> mount = ComponentMount(
        ...     component=ComponentRef(component_id="raspberry-pi-5"),
        ...     position=Point3D(x=10, y=10, z=0),
        ...     mounting_type=MountingType.STANDOFF,
        ... )
    """

    model_config = ConfigDict(frozen=True)

    # What component
    component: ComponentRef = Field(..., description="Component from library")

    # Where to mount
    position: Point3D = Field(
        default_factory=Point3D,
        description="Position of component origin in enclosure coordinates",
    )
    rotation: Rotation = Field(
        default_factory=Rotation,
        description="Rotation from default orientation",
    )
    mount_side: WallSide = Field(
        default=WallSide.BOTTOM,
        description="Which wall/surface to mount on",
    )

    # How to mount
    mounting_type: MountingType = Field(
        default=MountingType.STANDOFF,
        description="Mounting method",
    )
    standoffs: StandoffSpec | None = Field(
        default=None,
        description="Standoff configuration (if mounting_type=STANDOFF)",
    )

    # Port exposure
    expose_ports: Annotated[
        list[PortExposure],
        Field(default_factory=list, description="Ports to expose through walls"),
    ]

    # Labels
    label: str | None = Field(
        default=None,
        description="Optional label for this component instance",
    )


class ComponentCategory(StrEnum):
    """Categories of components in the library."""

    BOARD = "board"  # PCBs, microcontrollers
    DISPLAY = "display"  # LCDs, OLEDs, TFTs
    INPUT = "input"  # Buttons, encoders, switches
    CONNECTOR = "connector"  # USB, HDMI, power jacks
    SENSOR = "sensor"  # Temperature, motion, etc.
    POWER = "power"  # Batteries, regulators
    OTHER = "other"


class MountingHole(BaseModel):
    """A mounting hole on a component."""

    model_config = ConfigDict(frozen=True)

    x: float = Field(..., description="X position from component origin")
    y: float = Field(..., description="Y position from component origin")
    diameter: Dimension = Field(..., description="Hole diameter")
    type: str = Field(default="through", description="Hole type: through, blind")


class PortDefinition(BaseModel):
    """A port/connector on a component."""

    model_config = ConfigDict(frozen=True)

    name: str = Field(..., description="Port identifier (e.g., 'usb-c-power')")
    position: Point3D = Field(..., description="Position relative to component origin")
    dimensions: Dimension | None = Field(
        default=None,
        description="Port opening dimensions",
    )
    width: Dimension | None = Field(default=None, description="Port width")
    height: Dimension | None = Field(default=None, description="Port height")
    side: WallSide = Field(..., description="Which side of component the port is on")


class KeepoutZone(BaseModel):
    """An area requiring clearance (no obstructions)."""

    model_config = ConfigDict(frozen=True)

    name: str = Field(..., description="Zone identifier")
    position: Point3D = Field(..., description="Zone position")
    width: Dimension = Field(..., description="Zone width")
    depth: Dimension = Field(..., description="Zone depth")
    height: Dimension = Field(..., description="Zone height")
    reason: str = Field(..., description="Why clearance is needed")


class ComponentDefinition(BaseModel):
    """Full component definition for the component library.

    This schema defines the structure of component library entries.
    It includes dimensions, mounting patterns, ports, and metadata.
    """

    model_config = ConfigDict(frozen=True)

    # Identity
    id: str = Field(..., description="Unique component ID (kebab-case)")
    name: str = Field(..., description="Human-readable name")
    category: ComponentCategory = Field(..., description="Component category")
    aliases: list[str] = Field(default_factory=list, description="Alternative names for matching")

    # Dimensions
    dimensions: "BoundingBox" = Field(..., description="Overall component dimensions")

    # Mounting
    mounting_holes: list[MountingHole] = Field(
        default_factory=list, description="Screw/mounting hole positions"
    )

    # Ports and connectors
    ports: list[PortDefinition] = Field(
        default_factory=list, description="Connector/port positions"
    )

    # Keepout zones
    keepout_zones: list[KeepoutZone] = Field(
        default_factory=list, description="Areas requiring clearance"
    )

    # Metadata
    datasheet_url: str | None = Field(default=None, description="Reference documentation")
    notes: str | None = Field(default=None, description="Special considerations")


# Avoid circular import - import at end
from app.cad_v2.schemas.base import BoundingBox

# Update forward reference
ComponentDefinition.model_rebuild()
