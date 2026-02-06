"""Pattern schemas for CAD v2.

This module defines schemas for repeated patterns:
- Linear arrays (single row/column)
- Grid arrays (rows and columns)
- Circular arrays (around a center point)
- Custom patterns

Patterns are used for features like ventilation holes,
button clusters, and mounting hole arrays.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Annotated, Any, Literal, Union

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.cad_v2.schemas.base import Dimension, Point2D


class PatternType(StrEnum):
    """Types of patterns available."""

    LINEAR = "linear"
    GRID = "grid"
    CIRCULAR = "circular"
    CUSTOM = "custom"


class LinearPattern(BaseModel):
    """Linear array pattern (single row or column).

    Creates copies of a feature along a single axis.

    Example:
        >>> # 5 holes spaced 10mm apart horizontally
        >>> pattern = LinearPattern(
        ...     direction="horizontal",
        ...     count=5,
        ...     spacing=Dimension(value=10),
        ... )
    """

    model_config = ConfigDict(frozen=True)

    type: Literal["linear"] = "linear"
    direction: Literal["horizontal", "vertical"] = Field(
        default="horizontal",
        description="Pattern direction",
    )
    count: Annotated[int, Field(ge=1, le=100, description="Number of copies")]
    spacing: Dimension = Field(..., description="Distance between copies")
    center: bool = Field(
        default=True,
        description="Center pattern on position (vs start from position)",
    )

    @property
    def total_length(self) -> float:
        """Total pattern length in mm."""
        return (self.count - 1) * self.spacing.mm


class GridPattern(BaseModel):
    """Grid array pattern (rows and columns).

    Creates copies of a feature in a 2D grid.

    Example:
        >>> # 3x4 grid of holes
        >>> pattern = GridPattern(
        ...     rows=3,
        ...     columns=4,
        ...     row_spacing=Dimension(value=10),
        ...     column_spacing=Dimension(value=10),
        ... )
    """

    model_config = ConfigDict(frozen=True)

    type: Literal["grid"] = "grid"
    rows: Annotated[int, Field(ge=1, le=50, description="Number of rows")]
    columns: Annotated[int, Field(ge=1, le=50, description="Number of columns")]
    row_spacing: Dimension = Field(..., description="Spacing between rows")
    column_spacing: Dimension = Field(..., description="Spacing between columns")
    center: bool = Field(
        default=True,
        description="Center grid on position",
    )
    stagger: bool = Field(
        default=False,
        description="Offset alternating rows (honeycomb-like)",
    )
    stagger_offset: Dimension | None = Field(
        default=None,
        description="Stagger offset (defaults to half column spacing)",
    )

    @property
    def total_width(self) -> float:
        """Total pattern width in mm."""
        return (self.columns - 1) * self.column_spacing.mm

    @property
    def total_height(self) -> float:
        """Total pattern height in mm."""
        return (self.rows - 1) * self.row_spacing.mm

    @model_validator(mode="after")
    def validate_stagger(self) -> "GridPattern":
        """Set default stagger offset if staggering enabled."""
        if self.stagger and self.stagger_offset is None:
            offset = Dimension(value=self.column_spacing.mm / 2)
            object.__setattr__(self, "stagger_offset", offset)
        return self


class CircularPattern(BaseModel):
    """Circular array pattern (around a center point).

    Creates copies of a feature arranged in a circle.

    Example:
        >>> # 6 holes in a circle, radius 15mm
        >>> pattern = CircularPattern(
        ...     count=6,
        ...     radius=Dimension(value=15),
        ... )
    """

    model_config = ConfigDict(frozen=True)

    type: Literal["circular"] = "circular"
    count: Annotated[int, Field(ge=1, le=100, description="Number of copies")]
    radius: Dimension = Field(..., description="Circle radius")
    start_angle: float = Field(
        default=0.0,
        ge=0,
        lt=360,
        description="Starting angle in degrees",
    )
    sweep_angle: float = Field(
        default=360.0,
        gt=0,
        le=360,
        description="Total sweep angle (360 = full circle)",
    )
    rotate_instances: bool = Field(
        default=True,
        description="Rotate each instance to face outward",
    )


class CustomPattern(BaseModel):
    """Custom pattern with explicit positions.

    For non-regular arrangements like button clusters
    with specific layouts.

    Example:
        >>> # D-pad pattern (up, down, left, right, center)
        >>> pattern = CustomPattern(
        ...     positions=[
        ...         Point2D(x=0, y=15),   # Up
        ...         Point2D(x=0, y=-15),  # Down
        ...         Point2D(x=-15, y=0),  # Left
        ...         Point2D(x=15, y=0),   # Right
        ...         Point2D(x=0, y=0),    # Center
        ...     ],
        ...     labels=["up", "down", "left", "right", "select"],
        ... )
    """

    model_config = ConfigDict(frozen=True)

    type: Literal["custom"] = "custom"
    positions: Annotated[
        list[Point2D],
        Field(min_length=1, description="List of positions"),
    ]
    labels: Annotated[
        list[str],
        Field(default_factory=list, description="Optional labels for each position"),
    ]

    @model_validator(mode="after")
    def validate_labels(self) -> "CustomPattern":
        """Ensure labels match positions if provided."""
        if self.labels and len(self.labels) != len(self.positions):
            raise ValueError(
                f"Labels count ({len(self.labels)}) must match "
                f"positions count ({len(self.positions)})"
            )
        return self


# Union of all pattern types
Pattern = Union[
    LinearPattern,
    GridPattern,
    CircularPattern,
    CustomPattern,
]


class PatternedFeature(BaseModel):
    """A feature with a pattern applied.

    Combines a feature definition with a pattern to create
    multiple instances of the feature.
    """

    model_config = ConfigDict(frozen=True)

    # The base feature - will be imported from features.py when created to avoid circular import
    feature_type: str = Field(..., description="Feature type to pattern")
    feature_params: dict[str, Any] = Field(
        default_factory=dict,
        description="Feature parameters",
    )
    pattern: Pattern = Field(..., description="Pattern to apply")


# Pre-defined pattern presets
class PatternPresets:
    """Common pattern configurations."""

    @staticmethod
    def nav_cluster_dpad() -> CustomPattern:
        """D-pad navigation pattern (up/down/left/right/center)."""
        return CustomPattern(
            positions=[
                Point2D(x=0, y=12),  # Up
                Point2D(x=0, y=-12),  # Down
                Point2D(x=-12, y=0),  # Left
                Point2D(x=12, y=0),  # Right
                Point2D(x=0, y=0),  # Center/Select
            ],
            labels=["up", "down", "left", "right", "select"],
        )

    @staticmethod
    def nav_cluster_linear() -> LinearPattern:
        """Linear 5-button navigation (horizontal row)."""
        return LinearPattern(
            direction="horizontal",
            count=5,
            spacing=Dimension(value=12),
            center=True,
        )

    @staticmethod
    def vent_slots(width_mm: float = 40, count: int = 6) -> LinearPattern:
        """Ventilation slot pattern."""
        spacing = width_mm / (count - 1) if count > 1 else 0
        return LinearPattern(
            direction="horizontal",
            count=count,
            spacing=Dimension(value=spacing),
            center=True,
        )

    @staticmethod
    def honeycomb(rows: int = 5, cols: int = 7, spacing_mm: float = 5) -> GridPattern:
        """Honeycomb ventilation pattern."""
        return GridPattern(
            rows=rows,
            columns=cols,
            row_spacing=Dimension(value=spacing_mm * 0.866),  # sqrt(3)/2
            column_spacing=Dimension(value=spacing_mm),
            stagger=True,
            center=True,
        )

    @staticmethod
    def mounting_corners(width_mm: float, height_mm: float) -> CustomPattern:
        """Corner mounting hole pattern."""
        hw = width_mm / 2
        hh = height_mm / 2
        return CustomPattern(
            positions=[
                Point2D(x=-hw, y=-hh),  # Bottom-left
                Point2D(x=hw, y=-hh),  # Bottom-right
                Point2D(x=-hw, y=hh),  # Top-left
                Point2D(x=hw, y=hh),  # Top-right
            ],
        )
