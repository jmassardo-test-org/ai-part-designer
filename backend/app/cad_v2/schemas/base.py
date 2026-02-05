"""Base types for CAD v2 declarative schemas.

This module defines fundamental types used throughout the CAD schema system:
- Units and dimensions
- Coordinate systems (2D and 3D points)
- Bounding boxes
- Rotations and transformations

All dimensions default to millimeters for consistency with manufacturing workflows.
"""

from __future__ import annotations

from enum import StrEnum
from typing import TYPE_CHECKING, Annotated

from pydantic import BaseModel, ConfigDict, Field, model_validator

if TYPE_CHECKING:
    from typing import Self
else:
    try:
        from typing import Self
    except ImportError:
        from typing import Self


class Unit(StrEnum):
    """Supported measurement units."""

    MILLIMETERS = "mm"
    INCHES = "in"


class Axis(StrEnum):
    """3D coordinate axes."""

    X = "x"
    Y = "y"
    Z = "z"


class Dimension(BaseModel):
    """A measurement with units.

    Dimensions are the fundamental building block for specifying sizes.
    They include a value and unit, with millimeters as the default.

    Examples:
        >>> Dimension(value=10)  # 10mm
        >>> Dimension(value=2.5, unit="in")  # 2.5 inches
    """

    model_config = ConfigDict(frozen=True)

    value: Annotated[float, Field(gt=0, description="The numeric value")]
    unit: Unit = Unit.MILLIMETERS

    @property
    def mm(self) -> float:
        """Convert dimension to millimeters."""
        if self.unit == Unit.MILLIMETERS:
            return self.value
        if self.unit == Unit.INCHES:
            return self.value * 25.4
        raise ValueError(f"Unknown unit: {self.unit}")

    @property
    def inches(self) -> float:
        """Convert dimension to inches."""
        if self.unit == Unit.INCHES:
            return self.value
        if self.unit == Unit.MILLIMETERS:
            return self.value / 25.4
        raise ValueError(f"Unknown unit: {self.unit}")

    def __str__(self) -> str:
        """Human-readable representation."""
        return f"{self.value}{self.unit.value}"


class Point2D(BaseModel):
    """A point in 2D space.

    Used for positions on a single face or surface.
    Coordinates are in the current unit system (default mm).
    """

    model_config = ConfigDict(frozen=True)

    x: float = 0.0
    y: float = 0.0

    def to_tuple(self) -> tuple[float, float]:
        """Convert to tuple for Build123d."""
        return (self.x, self.y)


class Point3D(BaseModel):
    """A point in 3D space.

    Used for positions within the enclosure volume.
    Coordinates are in the current unit system (default mm).
    """

    model_config = ConfigDict(frozen=True)

    x: float = 0.0
    y: float = 0.0
    z: float = 0.0

    def to_tuple(self) -> tuple[float, float, float]:
        """Convert to tuple for Build123d."""
        return (self.x, self.y, self.z)


class Vector3D(BaseModel):
    """A direction vector in 3D space.

    Used for specifying directions (e.g., extrusion direction, normal vectors).
    Vectors are normalized when used for directions.
    """

    model_config = ConfigDict(frozen=True)

    x: float = 0.0
    y: float = 0.0
    z: float = 0.0

    @model_validator(mode="after")
    def validate_non_zero(self) -> Self:
        """Ensure vector is not zero-length."""
        if self.x == 0 and self.y == 0 and self.z == 0:
            raise ValueError("Vector cannot be zero-length")
        return self

    def to_tuple(self) -> tuple[float, float, float]:
        """Convert to tuple for Build123d."""
        return (self.x, self.y, self.z)


class Rotation(BaseModel):
    """Rotation angles around each axis (Euler angles).

    Rotations are applied in XYZ order (roll, pitch, yaw).
    Angles are in degrees.
    """

    model_config = ConfigDict(frozen=True)

    x: Annotated[float, Field(ge=-360, le=360, description="Rotation around X axis")] = 0.0
    y: Annotated[float, Field(ge=-360, le=360, description="Rotation around Y axis")] = 0.0
    z: Annotated[float, Field(ge=-360, le=360, description="Rotation around Z axis")] = 0.0

    def is_identity(self) -> bool:
        """Check if rotation is identity (no rotation)."""
        return self.x == 0 and self.y == 0 and self.z == 0


class BoundingBox(BaseModel):
    """A 3D bounding box defined by width, depth, and height.

    The bounding box is axis-aligned and centered at the origin by default.
    Used for overall enclosure dimensions and component sizes.

    Coordinate system:
        - Width (X): Left to right
        - Depth (Y): Front to back
        - Height (Z): Bottom to top
    """

    model_config = ConfigDict(frozen=True)

    width: Dimension = Field(..., description="Size along X axis")
    depth: Dimension = Field(..., description="Size along Y axis")
    height: Dimension = Field(..., description="Size along Z axis")

    @property
    def width_mm(self) -> float:
        """Width in millimeters."""
        return self.width.mm

    @property
    def depth_mm(self) -> float:
        """Depth in millimeters."""
        return self.depth.mm

    @property
    def height_mm(self) -> float:
        """Height in millimeters."""
        return self.height.mm

    @property
    def volume_mm3(self) -> float:
        """Volume in cubic millimeters."""
        return self.width_mm * self.depth_mm * self.height_mm

    def to_tuple_mm(self) -> tuple[float, float, float]:
        """Convert to (width, depth, height) tuple in millimeters."""
        return (self.width_mm, self.depth_mm, self.height_mm)

    def __str__(self) -> str:
        """Human-readable representation."""
        return f"{self.width} × {self.depth} × {self.height}"


class Tolerance(BaseModel):
    """Manufacturing tolerance specification.

    Defines the acceptable deviation from nominal dimensions.
    """

    model_config = ConfigDict(frozen=True)

    plus: Dimension = Field(
        default_factory=lambda: Dimension(value=0.1),
        description="Maximum positive deviation",
    )
    minus: Dimension = Field(
        default_factory=lambda: Dimension(value=0.1),
        description="Maximum negative deviation",
    )

    @classmethod
    def symmetric(cls, value: float, unit: Unit = Unit.MILLIMETERS) -> Tolerance:
        """Create symmetric tolerance (±value)."""
        dim = Dimension(value=value, unit=unit)
        return cls(plus=dim, minus=dim)

    @classmethod
    def fit_3d_print(cls) -> Tolerance:
        """Standard tolerance for 3D printed parts (±0.2mm)."""
        return cls.symmetric(0.2)

    @classmethod
    def fit_tight(cls) -> Tolerance:
        """Tight fit tolerance (±0.1mm)."""
        return cls.symmetric(0.1)

    @classmethod
    def fit_loose(cls) -> Tolerance:
        """Loose fit tolerance (±0.5mm)."""
        return cls.symmetric(0.5)
