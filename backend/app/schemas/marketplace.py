"""
Pydantic schemas for marketplace, lists, and saves features.

Includes schemas for design browsing, user lists, and saving/bookmarking designs.
"""

from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

# =============================================================================
# Category & Tag Schemas
# =============================================================================


class CategoryResponse(BaseModel):
    """Response schema for a marketplace category."""

    name: str
    slug: str
    design_count: int


class TagResponse(BaseModel):
    """Response schema for a design tag."""

    name: str
    count: int


# =============================================================================
# Design List Schemas
# =============================================================================


class ListCreate(BaseModel):
    """Schema for creating a design list."""

    name: Annotated[str, Field(min_length=1, max_length=100)]
    description: Annotated[str | None, Field(max_length=500, default=None)]
    icon: Annotated[str, Field(max_length=50, default="folder")]
    color: Annotated[str, Field(max_length=20, default="#6366f1")]
    is_public: bool = False


class ListUpdate(BaseModel):
    """Schema for updating a design list."""

    name: Annotated[str | None, Field(min_length=1, max_length=100, default=None)]
    description: Annotated[str | None, Field(max_length=500, default=None)]
    icon: Annotated[str | None, Field(max_length=50, default=None)]
    color: Annotated[str | None, Field(max_length=20, default=None)]
    is_public: bool | None = None
    position: int | None = None


class ListResponse(BaseModel):
    """Response schema for a design list."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    description: str | None
    icon: str
    color: str
    is_public: bool
    position: int
    item_count: int
    created_at: datetime
    updated_at: datetime


class ListWithItems(ListResponse):
    """List with its items included."""

    items: list["ListItemResponse"]


# =============================================================================
# List Item Schemas
# =============================================================================


class AddToListRequest(BaseModel):
    """Schema for adding a design to a list."""

    design_id: UUID
    note: Annotated[str | None, Field(max_length=500, default=None)]


class UpdateListItemRequest(BaseModel):
    """Schema for updating a list item."""

    note: Annotated[str | None, Field(max_length=500, default=None)]


class ReorderRequest(BaseModel):
    """Schema for reordering list items."""

    item_ids: list[UUID]  # Ordered list of item IDs


class ListItemResponse(BaseModel):
    """Response schema for a list item."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    list_id: UUID
    design_id: UUID
    note: str | None
    position: int
    created_at: datetime
    # Include design summary
    design_name: str | None = None
    design_thumbnail_url: str | None = None


class ListItemWithDesign(ListItemResponse):
    """List item with full design info."""

    design: "DesignSummaryResponse"


# =============================================================================
# Design Save Schemas
# =============================================================================


class SaveRequest(BaseModel):
    """Schema for saving a design."""

    list_ids: list[UUID] | None = None  # Add to specific lists (optional)


class SaveResponse(BaseModel):
    """Response after saving a design."""

    model_config = ConfigDict(from_attributes=True)

    design_id: UUID
    saved_at: datetime
    lists: list[ListResponse]  # Lists the design was added to


class UnsaveResponse(BaseModel):
    """Response after unsaving a design."""

    design_id: UUID
    removed_from_lists: int


class SaveStatusResponse(BaseModel):
    """Check if a design is saved."""

    design_id: UUID
    is_saved: bool
    in_lists: list[UUID]  # List IDs containing this design


# =============================================================================
# Marketplace Design Schemas
# =============================================================================


class DesignSummaryResponse(BaseModel):
    """Summary of a design for marketplace listings."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    description: str | None
    thumbnail_url: str | None
    category: str | None
    tags: list[str]
    save_count: int
    remix_count: int
    is_starter: bool
    created_at: datetime
    published_at: datetime | None
    # Author info
    author_id: UUID
    author_name: str


class MarketplaceDesignResponse(DesignSummaryResponse):
    """Full design details for marketplace."""

    # Additional detail fields
    is_saved: bool = False  # Current user has saved
    in_lists: list[UUID] = []  # Which of user's lists contain it
    remixed_from_id: UUID | None = None
    remixed_from_name: str | None = None
    featured_at: datetime | None = None
    # Files available
    has_step: bool = False
    has_stl: bool = False


class PaginatedDesignResponse(BaseModel):
    """Paginated list of marketplace designs."""

    items: list[DesignSummaryResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
    has_next: bool
    has_prev: bool


class PaginatedSavesResponse(BaseModel):
    """Paginated list of saved designs."""

    items: list[ListItemWithDesign]
    total: int
    page: int
    page_size: int


# =============================================================================
# Publish Schemas
# =============================================================================


class PublishDesignRequest(BaseModel):
    """Schema for publishing a design to marketplace."""

    category: Annotated[str | None, Field(max_length=50, default=None)]
    tags: list[str] = []
    is_starter: bool = False  # Admin only


class PublishDesignResponse(BaseModel):
    """Response after publishing a design."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    published_at: datetime
    category: str | None
    is_starter: bool


# =============================================================================
# Starter Design Schemas (Phase 3B)
# =============================================================================


class StarterDesignResponse(BaseModel):
    """Response for a starter design in the gallery."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    description: str | None
    thumbnail_url: str | None
    category: str | None
    tags: list[str]
    remix_count: int
    # For preview
    exterior_dimensions: dict | None = None
    features: list[str] = []
    created_at: datetime


class StarterDetailResponse(StarterDesignResponse):
    """Detailed starter with full spec for remixing."""

    # The EnclosureSpec for editing
    enclosure_spec: dict | None = None
    # Author attribution
    author_id: UUID
    author_name: str


class StarterListResponse(BaseModel):
    """Paginated list of starter designs."""

    items: list[StarterDesignResponse]
    total: int
    page: int
    page_size: int


class RemixRequest(BaseModel):
    """Request to remix a starter design."""

    # Optional modifications to apply during remix
    name: str | None = None


class RemixResponse(BaseModel):
    """Response after remixing a design."""

    id: UUID  # New design ID
    name: str
    remixed_from_id: UUID
    remixed_from_name: str
    enclosure_spec: dict
    created_at: datetime


# Forward reference resolution
ListWithItems.model_rebuild()
ListItemWithDesign.model_rebuild()
