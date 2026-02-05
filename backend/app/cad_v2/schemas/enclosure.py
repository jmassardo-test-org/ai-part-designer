"""Enclosure schema definitions for CAD v2.

This module defines the schemas for enclosure-type designs:
- Overall enclosure specifications
- Wall and lid configurations
- Mounting and ventilation options

Enclosures are the primary use case for the CAD v2 system,
designed to house electronics like Raspberry Pi, LCDs, and buttons.
"""

from enum import StrEnum
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.cad_v2.schemas.base import BoundingBox, Dimension, Point3D


class LidType(StrEnum):
    """Types of lid attachments."""

    SNAP_FIT = "snap_fit"  # Clips that snap together
    SCREW_ON = "screw_on"  # Screw holes for fasteners
    SLIDE_ON = "slide_on"  # Slides into grooves
    FRICTION = "friction"  # Press-fit
    HINGE = "hinge"  # Hinged lid (one side attached)
    NONE = "none"  # No separate lid (integrated)


class WallSide(StrEnum):
    """Sides of an enclosure."""

    FRONT = "front"  # -Y face (toward user)
    BACK = "back"  # +Y face (away from user)
    LEFT = "left"  # -X face
    RIGHT = "right"  # +X face
    TOP = "top"  # +Z face
    BOTTOM = "bottom"  # -Z face


class WallSpec(BaseModel):
    """Specification for enclosure walls.

    Allows different thicknesses for different walls,
    useful for structural or aesthetic reasons.
    """

    model_config = ConfigDict(frozen=True)

    thickness: Dimension = Field(
        default_factory=lambda: Dimension(value=2.0),
        description="Default wall thickness",
    )
    front: Dimension | None = Field(default=None, description="Front wall override")
    back: Dimension | None = Field(default=None, description="Back wall override")
    left: Dimension | None = Field(default=None, description="Left wall override")
    right: Dimension | None = Field(default=None, description="Right wall override")
    top: Dimension | None = Field(default=None, description="Top wall override")
    bottom: Dimension | None = Field(default=None, description="Bottom wall override")

    def get_thickness(self, side: WallSide) -> Dimension:
        """Get wall thickness for a specific side."""
        override = getattr(self, side.value, None)
        return override if override is not None else self.thickness


class SnapFitSpec(BaseModel):
    """Snap-fit connection specification."""

    model_config = ConfigDict(frozen=True)

    lip_height: Dimension = Field(
        default_factory=lambda: Dimension(value=2.0),
        description="Height of the snap-fit lip",
    )
    lip_thickness: Dimension = Field(
        default_factory=lambda: Dimension(value=1.0),
        description="Thickness of the lip material",
    )
    clearance: Dimension = Field(
        default_factory=lambda: Dimension(value=0.2),
        description="Gap for easy assembly",
    )


class ScrewSpec(BaseModel):
    """Screw mounting specification."""

    model_config = ConfigDict(frozen=True)

    hole_diameter: Dimension = Field(
        default_factory=lambda: Dimension(value=3.0),
        description="Screw hole diameter (e.g., M3 = 3.0mm)",
    )
    head_diameter: Dimension = Field(
        default_factory=lambda: Dimension(value=6.0),
        description="Screw head countersink diameter",
    )
    head_depth: Dimension = Field(
        default_factory=lambda: Dimension(value=2.0),
        description="Countersink depth",
    )
    boss_diameter: Dimension = Field(
        default_factory=lambda: Dimension(value=8.0),
        description="Diameter of screw boss/post",
    )
    positions: list[Point3D] = Field(
        default_factory=list,
        description="Screw hole positions (auto-generated if empty)",
    )

    @classmethod
    def m2(cls) -> "ScrewSpec":
        """M2 screw specification."""
        return cls(
            hole_diameter=Dimension(value=2.0),
            head_diameter=Dimension(value=4.0),
            head_depth=Dimension(value=1.5),
            boss_diameter=Dimension(value=5.0),
        )

    @classmethod
    def m3(cls) -> "ScrewSpec":
        """M3 screw specification (default)."""
        return cls()

    @classmethod
    def m4(cls) -> "ScrewSpec":
        """M4 screw specification."""
        return cls(
            hole_diameter=Dimension(value=4.0),
            head_diameter=Dimension(value=8.0),
            head_depth=Dimension(value=2.5),
            boss_diameter=Dimension(value=10.0),
        )


class LidSpec(BaseModel):
    """Lid configuration for enclosures.

    Defines how the lid attaches to the body and any
    additional lid-specific features.
    """

    model_config = ConfigDict(frozen=True)

    type: LidType = Field(default=LidType.SNAP_FIT, description="Lid attachment type")
    side: WallSide = Field(default=WallSide.TOP, description="Which side is the lid")
    snap_fit: SnapFitSpec | None = Field(default=None, description="Snap-fit params")
    screws: ScrewSpec | None = Field(default=None, description="Screw mounting params")
    separate_part: bool = Field(
        default=True,
        description="Generate lid as separate part for printing",
    )
    lip_inside: bool = Field(
        default=True,
        description="Lip on inside (True) or outside (False) of body",
    )

    @model_validator(mode="after")
    def validate_attachment_params(self) -> "LidSpec":
        """Ensure appropriate params are set for lid type."""
        if self.type == LidType.SNAP_FIT and self.snap_fit is None:
            # Use defaults
            object.__setattr__(self, "snap_fit", SnapFitSpec())
        if self.type == LidType.SCREW_ON and self.screws is None:
            # Use defaults
            object.__setattr__(self, "screws", ScrewSpec.m3())
        return self


class VentilationSpec(BaseModel):
    """Ventilation pattern specification."""

    model_config = ConfigDict(frozen=True)

    enabled: bool = Field(default=False, description="Include ventilation")
    sides: list[WallSide] = Field(
        default_factory=lambda: [WallSide.LEFT, WallSide.RIGHT],
        description="Which sides have vents",
    )
    pattern: str = Field(
        default="slots",
        description="Vent pattern: 'slots', 'holes', 'honeycomb'",
    )
    slot_width: Dimension = Field(
        default_factory=lambda: Dimension(value=2.0),
        description="Width of vent slots",
    )
    slot_length: Dimension = Field(
        default_factory=lambda: Dimension(value=15.0),
        description="Length of vent slots",
    )
    slot_spacing: Dimension = Field(
        default_factory=lambda: Dimension(value=3.0),
        description="Spacing between slots",
    )
    margin: Dimension = Field(
        default_factory=lambda: Dimension(value=5.0),
        description="Margin from wall edges",
    )


class MountingTabSpec(BaseModel):
    """Mounting tab/flange specification for securing enclosure."""

    model_config = ConfigDict(frozen=True)

    enabled: bool = Field(default=False, description="Include mounting tabs")
    sides: list[WallSide] = Field(
        default_factory=lambda: [WallSide.BOTTOM],
        description="Which sides have tabs",
    )
    width: Dimension = Field(
        default_factory=lambda: Dimension(value=15.0),
        description="Tab width",
    )
    depth: Dimension = Field(
        default_factory=lambda: Dimension(value=10.0),
        description="Tab extension from body",
    )
    hole_diameter: Dimension = Field(
        default_factory=lambda: Dimension(value=4.0),
        description="Mounting hole diameter",
    )
    count_per_side: int = Field(
        default=2,
        ge=1,
        le=6,
        description="Number of tabs per side",
    )


class EnclosureSpec(BaseModel):
    """Complete enclosure specification.

    This is the top-level schema for defining an enclosure.
    It includes dimensions, wall configuration, lid, components,
    features, and mounting options.

    Example:
        >>> spec = EnclosureSpec(
        ...     exterior=BoundingBox(
        ...         width=Dimension(value=120),
        ...         depth=Dimension(value=80),
        ...         height=Dimension(value=40),
        ...     ),
        ...     walls=WallSpec(thickness=Dimension(value=2.5)),
        ...     lid=LidSpec(type=LidType.SNAP_FIT),
        ... )
    """

    model_config = ConfigDict(frozen=True)

    # Core dimensions
    exterior: BoundingBox = Field(..., description="Outer dimensions of enclosure")
    walls: WallSpec = Field(
        default_factory=WallSpec,
        description="Wall thickness configuration",
    )
    corner_radius: Dimension | None = Field(
        default=None,
        description="Fillet radius for exterior corners (None = sharp)",
    )

    # Lid configuration
    lid: LidSpec | None = Field(default=None, description="Lid configuration")

    # Components (mounted inside)
    components: Annotated[
        list[Any],  # Will be list[ComponentMount] when components.py is created
        Field(default_factory=list, description="Components mounted in enclosure"),
    ]

    # Features (cutouts, ports, vents)
    features: Annotated[
        list[Any],  # Will be list[Feature] when features.py is created
        Field(default_factory=list, description="Features on enclosure walls"),
    ]

    # Ventilation
    ventilation: VentilationSpec = Field(
        default_factory=VentilationSpec,
        description="Ventilation configuration",
    )

    # Mounting
    mounting_tabs: MountingTabSpec = Field(
        default_factory=MountingTabSpec,
        description="External mounting tabs",
    )

    # Metadata
    name: str | None = Field(default=None, description="Name for this design")
    description: str | None = Field(default=None, description="Design description")

    @property
    def interior(self) -> BoundingBox:
        """Calculate interior dimensions based on wall thickness."""
        wall = self.walls.thickness.mm
        return BoundingBox(
            width=Dimension(value=self.exterior.width_mm - 2 * wall),
            depth=Dimension(value=self.exterior.depth_mm - 2 * wall),
            height=Dimension(value=self.exterior.height_mm - wall),  # Open top
        )

    @model_validator(mode="after")
    def validate_interior_positive(self) -> "EnclosureSpec":
        """Ensure interior dimensions are positive."""
        interior = self.interior
        if interior.width_mm <= 0:
            raise ValueError(
                f"Interior width must be positive. "
                f"Exterior width ({self.exterior.width_mm}mm) - "
                f"2 × wall thickness ({self.walls.thickness.mm}mm) = "
                f"{interior.width_mm}mm"
            )
        if interior.depth_mm <= 0:
            raise ValueError(
                f"Interior depth must be positive. "
                f"Exterior depth ({self.exterior.depth_mm}mm) - "
                f"2 × wall thickness ({self.walls.thickness.mm}mm) = "
                f"{interior.depth_mm}mm"
            )
        if interior.height_mm <= 0:
            raise ValueError(
                f"Interior height must be positive. "
                f"Exterior height ({self.exterior.height_mm}mm) - "
                f"wall thickness ({self.walls.thickness.mm}mm) = "
                f"{interior.height_mm}mm"
            )
        return self
