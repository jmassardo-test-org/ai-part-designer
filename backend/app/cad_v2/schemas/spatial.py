"""Spatial positioning schemas for CAD v2.

This module defines schemas for positioning and alignment:
- Relative positioning (relative to other components/features)
- Alignment options (center, edge, corner)
- Spacing and margins
- Constraints

These schemas enable intuitive placement without explicit coordinates.
"""

from enum import StrEnum
from typing import Annotated, Literal, Union

from pydantic import BaseModel, ConfigDict, Field

from app.cad_v2.schemas.base import Dimension, Point3D
from app.cad_v2.schemas.enclosure import WallSide


class HorizontalAlignment(StrEnum):
    """Horizontal alignment options."""

    LEFT = "left"
    CENTER = "center"
    RIGHT = "right"


class VerticalAlignment(StrEnum):
    """Vertical alignment options."""

    TOP = "top"
    CENTER = "center"
    BOTTOM = "bottom"


class DepthAlignment(StrEnum):
    """Depth (Z-axis) alignment options."""

    FRONT = "front"
    CENTER = "center"
    BACK = "back"
    FLOOR = "floor"  # On the bottom surface
    CEILING = "ceiling"  # At the top


class Alignment2D(BaseModel):
    """2D alignment on a surface.

    Used for positioning features on walls.
    """

    model_config = ConfigDict(frozen=True)

    horizontal: HorizontalAlignment = Field(
        default=HorizontalAlignment.CENTER,
        description="Horizontal alignment",
    )
    vertical: VerticalAlignment = Field(
        default=VerticalAlignment.CENTER,
        description="Vertical alignment",
    )


class Alignment3D(BaseModel):
    """3D alignment within enclosure.

    Used for positioning components in the interior volume.
    """

    model_config = ConfigDict(frozen=True)

    horizontal: HorizontalAlignment = Field(
        default=HorizontalAlignment.CENTER,
        description="X-axis alignment",
    )
    vertical: VerticalAlignment = Field(
        default=VerticalAlignment.CENTER,
        description="Y-axis alignment",
    )
    depth: DepthAlignment = Field(
        default=DepthAlignment.FLOOR,
        description="Z-axis alignment",
    )


class Margin(BaseModel):
    """Margins from enclosure walls.

    Specifies minimum distance from walls for placement.
    """

    model_config = ConfigDict(frozen=True)

    left: Dimension = Field(
        default_factory=lambda: Dimension(value=0),
        description="Left margin",
    )
    right: Dimension = Field(
        default_factory=lambda: Dimension(value=0),
        description="Right margin",
    )
    top: Dimension = Field(
        default_factory=lambda: Dimension(value=0),
        description="Top margin",
    )
    bottom: Dimension = Field(
        default_factory=lambda: Dimension(value=0),
        description="Bottom margin",
    )
    front: Dimension = Field(
        default_factory=lambda: Dimension(value=0),
        description="Front margin",
    )
    back: Dimension = Field(
        default_factory=lambda: Dimension(value=0),
        description="Back margin",
    )

    @classmethod
    def uniform(cls, value: float) -> "Margin":
        """Create uniform margins on all sides."""
        dim = Dimension(value=value)
        return cls(
            left=dim,
            right=dim,
            top=dim,
            bottom=dim,
            front=dim,
            back=dim,
        )

    @classmethod
    def symmetric(cls, horizontal: float, vertical: float, depth: float = 0) -> "Margin":
        """Create symmetric margins."""
        h = Dimension(value=horizontal)
        v = Dimension(value=vertical)
        d = Dimension(value=depth)
        return cls(
            left=h,
            right=h,
            top=v,
            bottom=v,
            front=d,
            back=d,
        )


class AbsolutePosition(BaseModel):
    """Absolute positioning with explicit coordinates.

    Position specified relative to enclosure origin
    (center of bottom surface by default).
    """

    model_config = ConfigDict(frozen=True)

    type: Literal["absolute"] = "absolute"
    position: Point3D = Field(..., description="Explicit position coordinates")
    origin: str = Field(
        default="center_bottom",
        description="Origin reference: 'center_bottom', 'corner', 'center'",
    )


class AlignedPosition(BaseModel):
    """Alignment-based positioning.

    Position specified by alignment and optional offset.
    """

    model_config = ConfigDict(frozen=True)

    type: Literal["aligned"] = "aligned"
    alignment: Alignment3D = Field(
        default_factory=Alignment3D,
        description="Alignment specification",
    )
    offset: Point3D = Field(
        default_factory=Point3D,
        description="Offset from aligned position",
    )
    margin: Margin = Field(
        default_factory=Margin,
        description="Minimum distance from walls",
    )


class RelativePosition(BaseModel):
    """Position relative to another component or feature.

    Enables placement like "below the LCD" or "next to the USB port".
    """

    model_config = ConfigDict(frozen=True)

    type: Literal["relative"] = "relative"
    reference: str = Field(
        ...,
        description="ID or label of reference component/feature",
    )
    relation: Literal["above", "below", "left_of", "right_of", "in_front", "behind"] = Field(
        ...,
        description="Spatial relation to reference",
    )
    gap: Dimension = Field(
        default_factory=lambda: Dimension(value=5),
        description="Gap between items",
    )
    alignment: HorizontalAlignment | VerticalAlignment = Field(
        default=HorizontalAlignment.CENTER,
        description="Alignment relative to reference",
    )


class WallPosition(BaseModel):
    """Position on a specific wall.

    For features like cutouts, ports, and buttons.
    """

    model_config = ConfigDict(frozen=True)

    type: Literal["wall"] = "wall"
    side: WallSide = Field(..., description="Which wall")
    alignment: Alignment2D = Field(
        default_factory=Alignment2D,
        description="Alignment on wall surface",
    )
    offset_x: Dimension = Field(
        default_factory=lambda: Dimension(value=0),
        description="Horizontal offset from aligned position",
    )
    offset_y: Dimension = Field(
        default_factory=lambda: Dimension(value=0),
        description="Vertical offset from aligned position",
    )
    margin: Dimension = Field(
        default_factory=lambda: Dimension(value=5),
        description="Minimum distance from wall edges",
    )


# Union of all position types
Position = Union[
    AbsolutePosition,
    AlignedPosition,
    RelativePosition,
    WallPosition,
]


class Constraint(BaseModel):
    """Spatial constraint for automatic layout.

    Constraints are used when the exact position isn't specified,
    allowing the system to calculate optimal placement.
    """

    model_config = ConfigDict(frozen=True)

    type: str = Field(..., description="Constraint type")
    value: float | str | None = Field(default=None, description="Constraint value")


class MinDistanceConstraint(BaseModel):
    """Minimum distance from another item."""

    model_config = ConfigDict(frozen=True)

    type: Literal["min_distance"] = "min_distance"
    from_item: str = Field(..., description="Reference item ID")
    distance: Dimension = Field(..., description="Minimum distance")


class MaxDistanceConstraint(BaseModel):
    """Maximum distance from another item."""

    model_config = ConfigDict(frozen=True)

    type: Literal["max_distance"] = "max_distance"
    from_item: str = Field(..., description="Reference item ID")
    distance: Dimension = Field(..., description="Maximum distance")


class AlignWithConstraint(BaseModel):
    """Align with another item."""

    model_config = ConfigDict(frozen=True)

    type: Literal["align_with"] = "align_with"
    with_item: str = Field(..., description="Reference item ID")
    axis: Literal["x", "y", "z"] = Field(..., description="Alignment axis")


class CenterBetweenConstraint(BaseModel):
    """Center between two items."""

    model_config = ConfigDict(frozen=True)

    type: Literal["center_between"] = "center_between"
    item_a: str = Field(..., description="First reference item")
    item_b: str = Field(..., description="Second reference item")
    axis: Literal["x", "y", "z"] = Field(..., description="Centering axis")


SpatialConstraint = Union[
    MinDistanceConstraint,
    MaxDistanceConstraint,
    AlignWithConstraint,
    CenterBetweenConstraint,
]


class LayoutHint(BaseModel):
    """Hint for automatic layout optimization.

    Provides preferences when there are multiple valid positions.
    """

    model_config = ConfigDict(frozen=True)

    prefer_side: WallSide | None = Field(
        default=None,
        description="Preferred wall side",
    )
    prefer_alignment: HorizontalAlignment | None = Field(
        default=None,
        description="Preferred horizontal alignment",
    )
    avoid_sides: Annotated[
        list[WallSide],
        Field(default_factory=list, description="Sides to avoid"),
    ]
    priority: int = Field(
        default=0,
        ge=-10,
        le=10,
        description="Layout priority (-10 to 10, higher = more important)",
    )
