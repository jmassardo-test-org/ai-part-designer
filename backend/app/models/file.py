"""
File model for tracking uploaded files.
"""

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import (
    BigInteger,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.user import User


class File(Base):
    """
    Model for tracking uploaded files.
    
    Stores metadata about files uploaded by users, including
    CAD files (STEP, STL, IGES), images, and other documents.
    
    Files are stored in object storage (S3/MinIO) with references
    stored in this table.
    """

    __tablename__ = "files"

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

    # File info
    filename: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Sanitized filename for storage",
    )
    original_filename: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Original filename from upload",
    )
    mime_type: Mapped[str] = mapped_column(
        String(127),
        nullable=False,
        index=True,
    )
    size_bytes: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
    )

    # Storage location
    storage_bucket: Mapped[str] = mapped_column(
        String(63),
        nullable=False,
        default="uploads",
    )
    storage_path: Mapped[str] = mapped_column(
        String(1024),
        nullable=False,
        comment="Path within the bucket",
    )

    # File type classification
    file_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        comment="cad, image, document, other",
    )
    cad_format: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
        index=True,
        comment="step, stl, iges, obj, etc.",
    )

    # Status
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="uploading",
        index=True,
    )  # uploading, processing, ready, failed, deleted

    # Processing results
    thumbnail_url: Mapped[str | None] = mapped_column(
        String(1024),
        nullable=True,
    )
    preview_url: Mapped[str | None] = mapped_column(
        String(1024),
        nullable=True,
    )

    # CAD-specific metadata
    geometry_info: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="Bounding box, volume, surface area, etc.",
    )

    # Checksum for integrity
    checksum_sha256: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
    )

    # Virus scan results
    scan_status: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
        comment="pending, clean, infected, error",
    )
    scan_result: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
    )

    # Soft delete
    is_deleted: Mapped[bool] = mapped_column(
        default=False,
        nullable=False,
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default="now()",
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default="now()",
        onupdate=datetime.utcnow,
        nullable=False,
    )

    # Relationships
    user: Mapped["User"] = relationship(
        "User",
        lazy="joined",
    )

    # Indexes
    __table_args__ = (
        Index(
            "idx_files_user_active",
            "user_id",
            "created_at",
            postgresql_where="is_deleted = false",
        ),
        Index(
            "idx_files_cad_format",
            "user_id",
            "cad_format",
            postgresql_where="file_type = 'cad' AND is_deleted = false",
        ),
    )

    def __repr__(self) -> str:
        return f"<File(id={self.id}, filename={self.filename}, status={self.status})>"

    @property
    def is_cad_file(self) -> bool:
        """Check if this is a CAD file."""
        return self.file_type == "cad"

    @property
    def is_ready(self) -> bool:
        """Check if file is ready for use."""
        return self.status == "ready" and not self.is_deleted

    @property
    def download_url(self) -> str:
        """Get the download URL for this file."""
        return f"/api/v1/files/{self.id}/download"

    def soft_delete(self) -> None:
        """Mark file as deleted."""
        self.is_deleted = True
        self.deleted_at = datetime.utcnow()
        self.status = "deleted"

    def mark_ready(self) -> None:
        """Mark file as ready after processing."""
        self.status = "ready"

    def mark_failed(self, reason: str | None = None) -> None:
        """Mark file as failed."""
        self.status = "failed"
        if reason:
            self.geometry_info = self.geometry_info or {}
            self.geometry_info["error"] = reason


# Allowed MIME types and extensions for CAD files
CAD_MIME_TYPES = {
    "application/step": "step",
    "application/stp": "step",
    "model/step": "step",
    "model/stl": "stl",
    "application/sla": "stl",
    "application/vnd.ms-pki.stl": "stl",
    "model/x.stl-binary": "stl",
    "model/x.stl-ascii": "stl",
    "application/iges": "iges",
    "model/iges": "iges",
    "application/x-3ds": "3ds",
    "model/obj": "obj",
    "application/x-tgif": "obj",
}

CAD_EXTENSIONS = {
    ".step": "step",
    ".stp": "step",
    ".stl": "stl",
    ".iges": "iges",
    ".igs": "iges",
    ".3ds": "3ds",
    ".obj": "obj",
    ".3mf": "3mf",
}

# File size limits by tier (in bytes)
FILE_SIZE_LIMITS = {
    "free": 10 * 1024 * 1024,       # 10 MB
    "basic": 50 * 1024 * 1024,      # 50 MB
    "pro": 200 * 1024 * 1024,       # 200 MB
    "enterprise": 1024 * 1024 * 1024,  # 1 GB
}
