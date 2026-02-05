"""Feature schemas for CAD v2.

This module defines schemas for enclosure features:
- Cutouts (rectangular, circular, custom)
- Port openings (USB, HDMI, etc.)
- Ventilation patterns
- Text and labels
- Mounting holes

Features are applied to enclosure walls and modify the geometry.
"""

from enum import StrEnum
from typing import Annotated, Literal, Union

from pydantic import BaseModel, ConfigDict, Field

from app.cad_v2.schemas.base import Dimension, Point2D, Point3D
from app.cad_v2.schemas.enclosure import WallSide


class CutoutShape(StrEnum):
    """Shape of cutout openings."""

    RECTANGLE = "rectangle"
    CIRCLE = "circle"
    ROUNDED_RECT = "rounded_rect"
    OVAL = "oval"
    SLOT = "slot"  # Elongated rounded rectangle
    CUSTOM = "custom"  # Custom polygon


class RectangleCutout(BaseModel):
    """Rectangular cutout specification."""

    model_config = ConfigDict(frozen=True)

    shape: Literal["rectangle"] = "rectangle"
    width: Dimension = Field(..., description="Cutout width")
    height: Dimension = Field(..., description="Cutout height")
    corner_radius: Dimension | None = Field(
        default=None,
        description="Corner radius (None = sharp corners)",
    )


class CircleCutout(BaseModel):
    """Circular cutout specification."""

    model_config = ConfigDict(frozen=True)

    shape: Literal["circle"] = "circle"
    diameter: Dimension = Field(..., description="Cutout diameter")


class SlotCutout(BaseModel):
    """Slot (elongated rounded rectangle) cutout specification."""

    model_config = ConfigDict(frozen=True)

    shape: Literal["slot"] = "slot"
    length: Dimension = Field(..., description="Slot length (end to end)")
    width: Dimension = Field(..., description="Slot width")
    orientation: Literal["horizontal", "vertical"] = Field(
        default="horizontal",
        description="Slot orientation",
    )


class OvalCutout(BaseModel):
    """Oval/ellipse cutout specification."""

    model_config = ConfigDict(frozen=True)

    shape: Literal["oval"] = "oval"
    width: Dimension = Field(..., description="Major axis dimension")
    height: Dimension = Field(..., description="Minor axis dimension")


class PolygonCutout(BaseModel):
    """Custom polygon cutout specification."""

    model_config = ConfigDict(frozen=True)

    shape: Literal["polygon"] = "polygon"
    points: Annotated[
        list[Point2D],
        Field(min_length=3, description="Polygon vertices in order"),
    ]


CutoutSpec = Union[
    RectangleCutout,
    CircleCutout,
    SlotCutout,
    OvalCutout,
    PolygonCutout,
]


class FeatureType(StrEnum):
    """Types of features that can be added to enclosures."""

    CUTOUT = "cutout"
    PORT = "port"
    VENT = "vent"
    MOUNTING_HOLE = "mounting_hole"
    TEXT = "text"
    BOSS = "boss"  # Raised cylinder for screws
    RIB = "rib"  # Structural reinforcement


class BaseCutout(BaseModel):
    """Base cutout feature on an enclosure wall.

    Cutouts are through-holes in the enclosure walls,
    used for displays, buttons, ports, etc.
    """

    model_config = ConfigDict(frozen=True)

    type: Literal["cutout"] = "cutout"
    side: WallSide = Field(..., description="Which wall to cut")
    position: Point2D = Field(
        ...,
        description="Position on wall (from wall center)",
    )
    cutout: CutoutSpec = Field(..., description="Cutout shape and dimensions")
    label: str | None = Field(default=None, description="Optional label")
    depth: Dimension | None = Field(
        default=None,
        description="Depth (None = through entire wall)",
    )


class PortCutout(BaseModel):
    """Port cutout with standard dimensions.

    Pre-defined cutouts for common ports (USB, HDMI, etc.)
    with appropriate dimensions and tolerances.
    """

    model_config = ConfigDict(frozen=True)

    type: Literal["port"] = "port"
    side: WallSide = Field(..., description="Which wall")
    position: Point2D = Field(..., description="Position on wall")
    port_type: str = Field(
        ...,
        description="Port type: 'usb-c', 'usb-a', 'micro-hdmi', 'hdmi', 'ethernet', etc.",
    )
    clearance: Dimension = Field(
        default_factory=lambda: Dimension(value=0.5),
        description="Extra clearance around port",
    )


class ButtonCutout(BaseModel):
    """Cutout for a button with optional bezel.

    Optimized for tactile buttons with options for
    raised bezels or flush mounting.
    """

    model_config = ConfigDict(frozen=True)

    type: Literal["button"] = "button"
    side: WallSide = Field(..., description="Which wall")
    position: Point2D = Field(..., description="Position on wall")
    diameter: Dimension = Field(
        default_factory=lambda: Dimension(value=6.0),
        description="Button hole diameter",
    )
    bezel: bool = Field(
        default=False,
        description="Add raised bezel around button",
    )
    bezel_height: Dimension = Field(
        default_factory=lambda: Dimension(value=1.0),
        description="Bezel height above surface",
    )
    label: str | None = Field(default=None, description="Button label")


class DisplayCutout(BaseModel):
    """Cutout for displays (LCD, OLED, etc.)

    Includes options for viewing area cutout with
    mounting flange for the display module.
    """

    model_config = ConfigDict(frozen=True)

    type: Literal["display"] = "display"
    side: WallSide = Field(..., description="Which wall")
    position: Point2D = Field(..., description="Position on wall")
    viewing_width: Dimension = Field(..., description="Visible area width")
    viewing_height: Dimension = Field(..., description="Visible area height")
    corner_radius: Dimension | None = Field(
        default=None,
        description="Corner radius for viewing area",
    )
    bezel_width: Dimension = Field(
        default_factory=lambda: Dimension(value=2.0),
        description="Bezel/flange width around viewing area",
    )


class VentPattern(BaseModel):
    """Ventilation pattern specification."""

    model_config = ConfigDict(frozen=True)

    type: Literal["vent"] = "vent"
    side: WallSide = Field(..., description="Which wall")
    position: Point2D = Field(..., description="Pattern center position")
    pattern: Literal["slots", "holes", "honeycomb", "grid"] = Field(
        default="slots",
        description="Ventilation pattern style",
    )
    area_width: Dimension = Field(..., description="Total pattern width")
    area_height: Dimension = Field(..., description="Total pattern height")
    slot_width: Dimension = Field(
        default_factory=lambda: Dimension(value=2.0),
        description="Individual slot/hole width",
    )
    slot_length: Dimension = Field(
        default_factory=lambda: Dimension(value=15.0),
        description="Individual slot length (for slots)",
    )
    spacing: Dimension = Field(
        default_factory=lambda: Dimension(value=3.0),
        description="Spacing between slots/holes",
    )


class MountingHoleFeature(BaseModel):
    """Mounting hole through enclosure wall."""

    model_config = ConfigDict(frozen=True)

    type: Literal["mounting_hole"] = "mounting_hole"
    side: WallSide = Field(..., description="Which wall")
    position: Point2D = Field(..., description="Position on wall")
    diameter: Dimension = Field(
        default_factory=lambda: Dimension(value=4.0),
        description="Hole diameter",
    )
    countersink: bool = Field(default=False, description="Add countersink")
    countersink_diameter: Dimension | None = Field(
        default=None,
        description="Countersink diameter",
    )
    countersink_depth: Dimension | None = Field(
        default=None,
        description="Countersink depth",
    )


class TextFeature(BaseModel):
    """Embossed or engraved text on enclosure surface."""

    model_config = ConfigDict(frozen=True)

    type: Literal["text"] = "text"
    side: WallSide = Field(..., description="Which wall")
    position: Point2D = Field(..., description="Text position")
    text: str = Field(..., description="Text content")
    font_size: Dimension = Field(
        default_factory=lambda: Dimension(value=5.0),
        description="Font height",
    )
    depth: Dimension = Field(
        default_factory=lambda: Dimension(value=0.5),
        description="Emboss/engrave depth",
    )
    emboss: bool = Field(
        default=True,
        description="True=raised text, False=engraved",
    )
    font: str = Field(default="sans-serif", description="Font family")


class BossFeature(BaseModel):
    """Screw boss (raised cylinder) for mounting."""

    model_config = ConfigDict(frozen=True)

    type: Literal["boss"] = "boss"
    position: Point3D = Field(..., description="Boss position")
    outer_diameter: Dimension = Field(
        default_factory=lambda: Dimension(value=8.0),
        description="Boss outer diameter",
    )
    inner_diameter: Dimension = Field(
        default_factory=lambda: Dimension(value=2.5),
        description="Screw hole diameter",
    )
    height: Dimension = Field(
        default_factory=lambda: Dimension(value=5.0),
        description="Boss height",
    )


class RibFeature(BaseModel):
    """Structural rib for reinforcement."""

    model_config = ConfigDict(frozen=True)

    type: Literal["rib"] = "rib"
    start: Point3D = Field(..., description="Rib start point")
    end: Point3D = Field(..., description="Rib end point")
    thickness: Dimension = Field(
        default_factory=lambda: Dimension(value=1.5),
        description="Rib thickness",
    )
    height: Dimension = Field(
        default_factory=lambda: Dimension(value=3.0),
        description="Rib height from surface",
    )


# Union of all feature types for enclosure.features list
Feature = Union[
    BaseCutout,
    PortCutout,
    ButtonCutout,
    DisplayCutout,
    VentPattern,
    MountingHoleFeature,
    TextFeature,
    BossFeature,
    RibFeature,
]
