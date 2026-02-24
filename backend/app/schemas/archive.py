"""
Archive Schemas

Pydantic schemas for design archival operations including
listing, restoring, and managing archived designs.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class ArchivedDesignResponse(BaseModel):
    """Response schema for an archived design."""

    id: UUID
    name: str
    archived_at: datetime
    archive_location: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ArchivedDesignListResponse(BaseModel):
    """Paginated list of archived designs."""

    items: list[ArchivedDesignResponse]
    total: int
    page: int = Field(ge=1)
    per_page: int = Field(ge=1)
    pages: int


class RestoreDesignResponse(BaseModel):
    """Response after restoring an archived design."""

    id: UUID
    name: str
    status: str
    restored_at: datetime

    class Config:
        from_attributes = True
