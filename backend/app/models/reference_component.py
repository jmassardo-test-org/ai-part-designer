"""
Reference Component Models

Models for storing reference components (electronics, hardware) with
mechanical specifications extracted from datasheets and CAD files.
"""

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from app.models.base import Base

# =============================================================================
# Reference Component
# =============================================================================


class ReferenceComponent(Base):
    """
    User-uploaded or library component with mechanical specifications.

    Examples: Raspberry Pi, Arduino, displays, buttons, connectors, sensors.
    """

    __tablename__ = "reference_components"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)

    # Ownership
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,  # Null for library components
        index=True,
    )

    # Basic info
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    category = Column(String(100), nullable=False, index=True)
    subcategory = Column(String(100), nullable=True)
    manufacturer = Column(String(255), nullable=True)
    model_number = Column(String(255), nullable=True)

    # Source type
    source_type = Column(
        String(50),
        nullable=False,
        default="uploaded",
        index=True,
    )  # "uploaded", "library", "community"

    # Source files
    datasheet_file_id = Column(
        UUID(as_uuid=True),
        ForeignKey("files.id", ondelete="SET NULL"),
        nullable=True,
    )
    cad_file_id = Column(
        UUID(as_uuid=True),
        ForeignKey("files.id", ondelete="SET NULL"),
        nullable=True,
    )
    thumbnail_url = Column(String(500), nullable=True)

    # Extracted specifications (from datasheet/CAD)
    dimensions = Column(
        JSONB,
        nullable=True,
        comment="Overall dimensions: {length, width, height, unit}",
    )
    mounting_holes = Column(
        JSONB,
        nullable=True,
        comment="Array of mounting holes: [{x, y, diameter, thread_size, depth}]",
    )
    connectors = Column(
        JSONB,
        nullable=True,
        comment="Array of connectors: [{name, type, position, cutout_width, cutout_height}]",
    )
    clearance_zones = Column(
        JSONB,
        nullable=True,
        comment="Array of clearance zones: [{name, type, bounds, description}]",
    )
    thermal_properties = Column(
        JSONB,
        nullable=True,
        comment="Thermal specs: {max_temp, heat_dissipation, requires_venting}",
    )

    # Electrical properties (optional)
    electrical_properties = Column(
        JSONB,
        nullable=True,
        comment="Electrical specs: {voltage, current, power}",
    )

    # Extraction status
    extraction_status = Column(
        String(50),
        nullable=False,
        default="pending",
    )  # "pending", "processing", "complete", "failed", "manual"
    extraction_error = Column(Text, nullable=True)
    confidence_score = Column(
        Float,
        nullable=True,
        comment="AI extraction confidence 0.0-1.0",
    )

    # Verification
    is_verified = Column(
        Boolean,
        default=False,
        nullable=False,
        comment="Admin-verified specifications",
    )
    verified_by = Column(UUID(as_uuid=True), nullable=True)
    verified_at = Column(DateTime(timezone=True), nullable=True)

    # Metadata
    tags = Column(JSONB, default=list)
    notes = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(tz=datetime.UTC),
        nullable=False,
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(tz=datetime.UTC),
        onupdate=lambda: datetime.now(tz=datetime.UTC),
        nullable=False,
    )
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    user = relationship("User", foreign_keys=[user_id])
    datasheet_file = relationship("File", foreign_keys=[datasheet_file_id])
    cad_file = relationship("File", foreign_keys=[cad_file_id])
    library_entry = relationship(
        "ComponentLibrary",
        back_populates="component",
        uselist=False,
    )

    # Indexes
    __table_args__ = (
        Index("ix_ref_components_category_subcategory", "category", "subcategory"),
        Index("ix_ref_components_manufacturer_model", "manufacturer", "model_number"),
        Index("ix_ref_components_source_verified", "source_type", "is_verified"),
    )

    def __repr__(self) -> str:
        return f"<ReferenceComponent {self.name} ({self.category})>"


# =============================================================================
# Component Library
# =============================================================================


class ComponentLibrary(Base):
    """
    Curated library of popular components.

    This is a subset of reference_components that are:
    - Verified by admins
    - Have accurate specifications
    - Popular/commonly used
    """

    __tablename__ = "component_library"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)

    # Link to reference component
    component_id = Column(
        UUID(as_uuid=True),
        ForeignKey("reference_components.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )

    # Library metadata
    category = Column(String(100), nullable=False, index=True)
    subcategory = Column(String(100), nullable=True, index=True)

    # Manufacturer info (denormalized for search)
    manufacturer = Column(String(255), nullable=True, index=True)
    model_number = Column(String(255), nullable=True)

    # Discovery
    popularity_score = Column(
        Integer,
        default=0,
        nullable=False,
        index=True,
    )
    usage_count = Column(Integer, default=0, nullable=False)

    # Tags for search
    tags = Column(JSONB, default=list)

    # Display
    display_order = Column(Integer, default=0)
    is_featured = Column(Boolean, default=False, index=True)

    # Timestamps
    added_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(tz=datetime.UTC),
        nullable=False,
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(tz=datetime.UTC),
        onupdate=lambda: datetime.now(tz=datetime.UTC),
        nullable=False,
    )

    # Relationships
    component = relationship(
        "ReferenceComponent",
        back_populates="library_entry",
    )

    # Indexes
    __table_args__ = (
        Index("ix_library_category_featured", "category", "is_featured"),
        Index("ix_library_popularity", "popularity_score", "usage_count"),
    )

    def __repr__(self) -> str:
        return f"<ComponentLibrary {self.component_id}>"


# =============================================================================
# Component Extraction Job
# =============================================================================


class ComponentExtractionJob(Base):
    """
    Background job for extracting specifications from datasheets/CAD.
    """

    __tablename__ = "component_extraction_jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)

    # Link to component
    component_id = Column(
        UUID(as_uuid=True),
        ForeignKey("reference_components.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Job type
    job_type = Column(
        String(50),
        nullable=False,
    )  # "datasheet", "cad", "full"

    # Status
    status = Column(
        String(50),
        nullable=False,
        default="pending",
        index=True,
    )  # "pending", "processing", "complete", "failed"

    # Progress
    progress = Column(Integer, default=0)
    current_step = Column(String(255), nullable=True)

    # Results
    extracted_data = Column(JSONB, nullable=True)
    confidence_score = Column(Float, nullable=True)

    # Error handling
    error_message = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0)

    # Timing
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    # Timestamps
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(tz=datetime.UTC),
        nullable=False,
    )

    # Relationship
    component = relationship("ReferenceComponent")

    def __repr__(self) -> str:
        return f"<ComponentExtractionJob {self.id} ({self.status})>"


# =============================================================================
# User Component (copied from library)
# =============================================================================


class UserComponent(Base):
    """
    Component added to a user's project from the library.

    This allows users to customize library components for their needs.
    """

    __tablename__ = "user_components"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)

    # Ownership
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Source
    source_component_id = Column(
        UUID(as_uuid=True),
        ForeignKey("reference_components.id", ondelete="SET NULL"),
        nullable=True,  # Null if created from scratch
    )

    # Project link (optional)
    project_id = Column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    # User customizations
    custom_name = Column(String(255), nullable=True)
    custom_notes = Column(Text, nullable=True)

    # Overridden specifications
    custom_dimensions = Column(JSONB, nullable=True)
    custom_mounting_holes = Column(JSONB, nullable=True)
    custom_connectors = Column(JSONB, nullable=True)
    custom_clearance_zones = Column(JSONB, nullable=True)

    # Timestamps
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(tz=datetime.UTC),
        nullable=False,
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(tz=datetime.UTC),
        onupdate=lambda: datetime.now(tz=datetime.UTC),
        nullable=False,
    )

    # Relationships
    user = relationship("User")
    source_component = relationship("ReferenceComponent")
    project = relationship("Project")

    def __repr__(self) -> str:
        return f"<UserComponent {self.id}>"
