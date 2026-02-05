"""
Spatial Layout Models

Models for component spatial arrangement within enclosures.
Supports manual positioning and auto-layout.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    Float,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.project import Project
    from app.models.reference_component import ReferenceComponent


# =============================================================================
# Enums
# =============================================================================


class FaceDirection(str):
    """Direction a component face points relative to enclosure."""

    FRONT = "front"
    BACK = "back"
    LEFT = "left"
    RIGHT = "right"
    TOP = "top"
    BOTTOM = "bottom"


class LayoutStatus(str):
    """Status of a layout."""

    DRAFT = "draft"
    VALIDATED = "validated"
    FINALIZED = "finalized"


# =============================================================================
# Spatial Layout
# =============================================================================


class SpatialLayout(Base, TimestampMixin):
    """
    Spatial layout of components within an enclosure.

    A project can have multiple layouts (e.g., "Compact", "Spaced Out")
    to explore different arrangements before generating an enclosure.
    """

    __tablename__ = "spatial_layouts"

    # Primary key
    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    # Foreign keys
    project_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Layout metadata
    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="draft",
    )  # draft, validated, finalized

    # Enclosure dimensions (matches database columns)
    enclosure_length: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=100.0,
    )  # X-axis, mm
    enclosure_width: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=100.0,
    )  # Y-axis, mm
    enclosure_height: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=50.0,
    )  # Z-axis, mm

    # Whether auto-arrangement is enabled
    auto_arrange: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
    )

    # Minimum spacing between components
    min_spacing_x: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=5.0,
    )  # Min X spacing, mm
    min_spacing_y: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=5.0,
    )  # Min Y spacing, mm

    # Relationships
    project: Mapped[Project] = relationship(
        "Project",
        back_populates="layouts",
    )
    placements: Mapped[list[ComponentPlacement]] = relationship(
        "ComponentPlacement",
        back_populates="layout",
        cascade="all, delete-orphan",
        order_by="ComponentPlacement.created_at",
    )

    # Indexes
    __table_args__ = (Index("idx_layouts_project", "project_id"),)

    def __repr__(self) -> str:
        return f"<SpatialLayout(id={self.id}, name={self.name})>"

    @property
    def dimensions_tuple(self) -> tuple[float, float, float]:
        """Get enclosure dimensions as (length, width, height) tuple."""
        return (self.enclosure_length, self.enclosure_width, self.enclosure_height)

    @property
    def component_count(self) -> int:
        """Number of components in layout."""
        return len(self.placements)

    def get_bounding_box(self) -> dict:
        """
        Calculate bounding box of all placed components.

        Returns:
            Dict with min_x, max_x, min_y, max_y, min_z, max_z
        """
        if not self.placements:
            return {
                "min_x": 0,
                "max_x": 0,
                "min_y": 0,
                "max_y": 0,
                "min_z": 0,
                "max_z": 0,
            }

        min_x = min(p.x for p in self.placements)
        max_x = max(p.x + (p.width or 0) for p in self.placements)
        min_y = min(p.y for p in self.placements)
        max_y = max(p.y + (p.depth or 0) for p in self.placements)
        min_z = min(p.z for p in self.placements)
        max_z = max(p.z + (p.height or 0) for p in self.placements)

        return {
            "min_x": min_x,
            "max_x": max_x,
            "min_y": min_y,
            "max_y": max_y,
            "min_z": min_z,
            "max_z": max_z,
        }


# =============================================================================
# Component Placement
# =============================================================================


class ComponentPlacement(Base, TimestampMixin):
    """
    Position and orientation of a component within a layout.

    Origin is at bottom-left-front corner of enclosure interior.
    Rotation is around Z-axis (vertical) in 90° increments.
    """

    __tablename__ = "component_placements"

    # Primary key
    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    # Foreign keys
    layout_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("spatial_layouts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    component_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("reference_components.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Position (mm, relative to enclosure origin)
    x: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
    )
    y: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
    )
    z: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
    )  # Height above floor (for standoff height)

    # Rotation around Z-axis (0, 90, 180, 270)
    rotation_z: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
    )

    # Cached component dimensions (rotated)
    width: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )  # X-axis after rotation
    depth: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )  # Y-axis after rotation
    height: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )  # Z-axis (doesn't change with rotation)

    # Which enclosure face the component's "front" faces
    face_direction: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="front",
    )  # front, back, left, right

    # User locked this position
    locked: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )

    # Visual settings
    color_override: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
    )  # Hex color for visualization

    # Notes
    notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # Relationships
    layout: Mapped[SpatialLayout] = relationship(
        "SpatialLayout",
        back_populates="placements",
    )
    component: Mapped[ReferenceComponent] = relationship(
        "ReferenceComponent",
        lazy="joined",
    )

    # Indexes
    __table_args__ = (
        Index("idx_placements_layout", "layout_id"),
        Index("idx_placements_component", "component_id"),
        UniqueConstraint(
            "layout_id",
            "component_id",
            name="uq_placement_layout_component",
        ),
    )

    def __repr__(self) -> str:
        return f"<ComponentPlacement(id={self.id}, x={self.x}, y={self.y}, z={self.z})>"

    @property
    def position_tuple(self) -> tuple[float, float, float]:
        """Get position as (x, y, z) tuple."""
        return (self.x, self.y, self.z)

    @property
    def dimensions_tuple(self) -> tuple[float, float, float]:
        """Get dimensions as (width, depth, height) tuple."""
        return (self.width or 0, self.depth or 0, self.height or 0)

    def get_bounding_box(self) -> dict:
        """
        Get axis-aligned bounding box in enclosure coordinates.

        Returns:
            Dict with min_x, max_x, min_y, max_y, min_z, max_z
        """
        return {
            "min_x": self.x,
            "max_x": self.x + (self.width or 0),
            "min_y": self.y,
            "max_y": self.y + (self.depth or 0),
            "min_z": self.z,
            "max_z": self.z + (self.height or 0),
        }

    def intersects(self, other: ComponentPlacement, margin: float = 0) -> bool:
        """
        Check if this placement intersects with another.

        Args:
            other: Another placement to check
            margin: Additional clearance to require

        Returns:
            True if bounding boxes overlap (including margin)
        """
        # Get bounding boxes
        a = self.get_bounding_box()
        b = other.get_bounding_box()

        # Check for non-overlap in each axis
        if a["max_x"] + margin <= b["min_x"] or b["max_x"] + margin <= a["min_x"]:
            return False
        if a["max_y"] + margin <= b["min_y"] or b["max_y"] + margin <= a["min_y"]:
            return False
        return not (a["max_z"] + margin <= b["min_z"] or b["max_z"] + margin <= a["min_z"])

    def set_rotation(self, degrees: float) -> None:
        """
        Set rotation and update cached dimensions.

        Args:
            degrees: Rotation in degrees (will be rounded to nearest 90°)
        """
        # Round to nearest 90°
        self.rotation_z = round(degrees / 90) * 90 % 360

        # Swap width/depth for 90° and 270° rotations
        if self.rotation_z in (90, 270):
            self.width, self.depth = self.depth, self.width
