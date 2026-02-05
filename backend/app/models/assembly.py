"""
Assembly domain models: Assembly, AssemblyComponent, ComponentRelationship.

Assemblies are collections of designs/parts with position, rotation,
and relationship information for building complex multi-part structures.
"""

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, SoftDeleteMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.design import Design
    from app.models.project import Project
    from app.models.user import User


class Assembly(Base, TimestampMixin, SoftDeleteMixin):
    """
    Assembly model representing a collection of components/designs.

    Assemblies organize multiple parts into a coherent structure with
    positioning, relationships, and bill of materials tracking.
    """

    __tablename__ = "assemblies"

    # Primary key
    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    # Foreign keys
    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    project_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    root_design_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("designs.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Assembly info
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # Status
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="draft",
    )  # draft, in_progress, complete, archived

    # Thumbnail
    thumbnail_url: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    # Metadata (JSONB) - stored as 'metadata' in database
    extra_data: Mapped[dict] = mapped_column(
        "metadata",
        JSONB,
        nullable=False,
        default=dict,
    )
    # Example: {
    #   "total_parts": 15,
    #   "total_cost": 125.50,
    #   "units": "mm",
    #   "bounding_box": {"x": 200, "y": 150, "z": 100}
    # }

    # Version tracking
    version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
    )

    # Relationships
    user: Mapped["User"] = relationship(
        "User",
        lazy="joined",
    )
    project: Mapped["Project"] = relationship(
        "Project",
        lazy="joined",
    )
    root_design: Mapped["Design | None"] = relationship(
        "Design",
        lazy="joined",
    )
    components: Mapped[list["AssemblyComponent"]] = relationship(
        "AssemblyComponent",
        back_populates="assembly",
        lazy="selectin",
        cascade="all, delete-orphan",
    )
    component_relationships: Mapped[list["ComponentRelationship"]] = relationship(
        "ComponentRelationship",
        back_populates="assembly",
        lazy="selectin",
        cascade="all, delete-orphan",
    )
    bom_items: Mapped[list["BOMItem"]] = relationship(
        "BOMItem",
        back_populates="assembly",
        lazy="selectin",
        cascade="all, delete-orphan",
    )

    # Indexes
    __table_args__ = (
        Index("idx_assemblies_project", "project_id", "created_at"),
        Index("idx_assemblies_user", "user_id", "updated_at"),
    )

    def __repr__(self) -> str:
        return f"<Assembly(id={self.id}, name={self.name})>"

    @property
    def component_count(self) -> int:
        """Count of components in assembly."""
        return len(self.components)

    @property
    def total_quantity(self) -> int:
        """Total quantity of all parts."""
        return sum(c.quantity for c in self.components)


class AssemblyComponent(Base, TimestampMixin):
    """
    Component within an assembly.

    Links a design to an assembly with position, rotation, and quantity.
    Components can be custom designs or COTS (commercial off-the-shelf) parts.
    """

    __tablename__ = "assembly_components"

    # Primary key
    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    # Foreign keys
    assembly_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("assemblies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    design_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("designs.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Component info
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # Quantity
    quantity: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
    )

    # Position in 3D space (relative to assembly origin)
    position: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=lambda: {"x": 0, "y": 0, "z": 0},
    )
    # Example: {"x": 10.5, "y": 20.0, "z": 0.0}

    # Rotation (Euler angles in degrees)
    rotation: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=lambda: {"rx": 0, "ry": 0, "rz": 0},
    )
    # Example: {"rx": 0, "ry": 90, "rz": 0}

    # Scale (usually 1:1:1)
    scale: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=lambda: {"sx": 1, "sy": 1, "sz": 1},
    )

    # Component type
    is_cots: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )

    # Part identification
    part_number: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    # Color/material override for visualization
    color: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
    )  # Hex color like "#FF5500"

    # Additional component metadata (mapped to 'metadata' column)
    component_metadata: Mapped[dict] = mapped_column(
        "metadata",  # Column name in database
        JSONB,
        nullable=False,
        default=dict,
    )
    # Example: {
    #   "material": "PLA",
    #   "finish": "matte",
    #   "tolerance_class": "standard"
    # }

    # Relationships
    assembly: Mapped["Assembly"] = relationship(
        "Assembly",
        back_populates="components",
    )
    design: Mapped["Design | None"] = relationship(
        "Design",
        lazy="joined",
    )
    bom_item: Mapped["BOMItem | None"] = relationship(
        "BOMItem",
        back_populates="component",
        uselist=False,
    )

    # Indexes
    __table_args__ = (
        Index("idx_components_assembly", "assembly_id"),
        Index("idx_components_design", "design_id"),
    )

    def __repr__(self) -> str:
        return f"<AssemblyComponent(id={self.id}, name={self.name}, qty={self.quantity})>"


class ComponentRelationship(Base, TimestampMixin):
    """
    Relationship between components in an assembly.

    Defines how components connect: fastened, mated, inserted, etc.
    Used for constraint solving and assembly instructions.
    """

    __tablename__ = "component_relationships"

    # Primary key
    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    # Foreign keys
    assembly_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("assemblies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    parent_component_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("assembly_components.id", ondelete="CASCADE"),
        nullable=False,
    )
    child_component_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("assembly_components.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Relationship type
    relationship_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )
    # Types: fastened, mated, inserted, aligned, coaxial, tangent, offset

    # Human-readable name/description
    name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    # Constraint data for future constraint solving
    constraint_data: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )
    # Example: {
    #   "type": "fastened",
    #   "fastener_type": "M3x8",
    #   "fastener_count": 4,
    #   "torque_nm": 0.5
    # }

    # Assembly order (for instructions)
    assembly_order: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    # Relationships
    assembly: Mapped["Assembly"] = relationship(
        "Assembly",
        back_populates="component_relationships",
    )
    parent_component: Mapped["AssemblyComponent"] = relationship(
        "AssemblyComponent",
        foreign_keys=[parent_component_id],
    )
    child_component: Mapped["AssemblyComponent"] = relationship(
        "AssemblyComponent",
        foreign_keys=[child_component_id],
    )

    # Indexes
    __table_args__ = (
        Index("idx_relationships_assembly", "assembly_id"),
        Index("idx_relationships_parent", "parent_component_id"),
        Index("idx_relationships_child", "child_component_id"),
    )

    def __repr__(self) -> str:
        return f"<ComponentRelationship(id={self.id}, type={self.relationship_type})>"


class Vendor(Base, TimestampMixin, SoftDeleteMixin):
    """
    Vendor/supplier for COTS components.

    Supports integration with vendor APIs for pricing and availability.
    """

    __tablename__ = "vendors"

    # Primary key
    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    # Vendor info
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        unique=True,
    )
    display_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    website: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )
    logo_url: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    # API integration
    api_type: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )  # "mcmaster", "misumi", "digikey", "mouser", etc.

    api_base_url: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    # API credentials (encrypted at rest)
    api_credentials: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
    )

    # Supported categories
    categories: Mapped[list[str]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
    )
    # Example: ["fasteners", "bearings", "linear_motion", "electronics"]

    # Active status
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
    )

    # Relationships
    bom_items: Mapped[list["BOMItem"]] = relationship(
        "BOMItem",
        back_populates="vendor",
        lazy="dynamic",
    )

    def __repr__(self) -> str:
        return f"<Vendor(id={self.id}, name={self.name})>"


class BOMItem(Base, TimestampMixin):
    """
    Bill of Materials item for an assembly component.

    Tracks cost, vendor, lead time, and other procurement info.
    """

    __tablename__ = "bom_items"

    # Primary key
    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    # Foreign keys
    assembly_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("assemblies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    component_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("assembly_components.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    vendor_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("vendors.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Part identification
    part_number: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )
    vendor_part_number: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )
    description: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    # Category for grouping
    category: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="custom",
    )  # custom, fastener, electronic, mechanical, printed, etc.

    # Quantity (mirrors component quantity by default)
    quantity: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
    )

    # Pricing
    unit_cost: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 4),
        nullable=True,
    )
    currency: Mapped[str] = mapped_column(
        String(3),
        nullable=False,
        default="USD",
    )

    # Procurement info
    lead_time_days: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    minimum_order_quantity: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
    )
    in_stock: Mapped[bool | None] = mapped_column(
        Boolean,
        nullable=True,
    )
    last_price_check: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Notes
    notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # Relationships
    assembly: Mapped["Assembly"] = relationship(
        "Assembly",
        back_populates="bom_items",
    )
    component: Mapped["AssemblyComponent"] = relationship(
        "AssemblyComponent",
        back_populates="bom_item",
    )
    vendor: Mapped["Vendor | None"] = relationship(
        "Vendor",
        back_populates="bom_items",
    )

    # Indexes
    __table_args__ = (
        Index("idx_bom_assembly", "assembly_id"),
        Index("idx_bom_category", "category"),
        Index("idx_bom_vendor", "vendor_id"),
    )

    def __repr__(self) -> str:
        return f"<BOMItem(id={self.id}, part={self.part_number})>"

    @property
    def total_cost(self) -> Decimal | None:
        """Calculate total cost for this line item."""
        if self.unit_cost is not None:
            return self.unit_cost * self.quantity
        return None
