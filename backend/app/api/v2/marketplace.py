"""
Marketplace API endpoints.

Allows browsing public designs, featured designs, and categories.
"""

from __future__ import annotations

import logging
from datetime import UTC
from typing import TYPE_CHECKING, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, desc, func, or_, select

from app.api.deps import get_current_user_optional
from app.core.database import get_db
from app.models.design import Design
from app.models.marketplace import DesignSave
from app.models.user import User
from app.schemas.marketplace import (
    CategoryResponse,
    DesignSummaryResponse,
    MarketplaceDesignResponse,
    PaginatedDesignResponse,
    PublishDesignRequest,
    PublishDesignResponse,
)

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

router = APIRouter()


# =============================================================================
# Constants
# =============================================================================


VALID_CATEGORIES = [
    "raspberry-pi",
    "arduino",
    "electronics",
    "3d-printing",
    "iot",
    "wearables",
    "robotics",
    "audio",
    "power",
    "other",
]


# =============================================================================
# Helper Functions
# =============================================================================


def _design_to_summary(design: Design, author_name: str) -> DesignSummaryResponse:
    """Convert a Design model to a summary response."""
    return DesignSummaryResponse(
        id=design.id,
        name=design.name,
        description=design.description,
        thumbnail_url=design.thumbnail_url,
        category=design.category,
        tags=design.tags or [],
        save_count=design.save_count,
        remix_count=design.remix_count,
        is_starter=design.is_starter,
        created_at=design.created_at,
        published_at=design.published_at,
        author_id=design.user_id,
        author_name=author_name,
    )


# =============================================================================
# Browse Endpoints
# =============================================================================


@router.get("/designs", response_model=PaginatedDesignResponse)
async def browse_designs(
    category: str | None = Query(None, description="Filter by category"),
    tags: list[str] | None = Query(None, description="Filter by tags"),
    sort: str = Query(
        "popular",
        description="Sort order",
        pattern="^(popular|recent|trending|saves)$",
    ),
    search: str | None = Query(None, description="Search in name/description"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    db: AsyncSession = Depends(get_db),
    current_user: User | None = Depends(get_current_user_optional),
) -> PaginatedDesignResponse:
    """
    Browse public marketplace designs.

    Supports filtering by category and tags, sorting, and text search.
    """
    # Base query: public and published designs
    query = (
        select(Design, User.display_name.label("author_name"))
        .join(User, Design.user_id == User.id)
        .where(Design.is_public == True)  # noqa: E712
        .where(Design.published_at.isnot(None))
        .where(Design.deleted_at.is_(None))
    )

    # Apply category filter
    if category:
        query = query.where(Design.category == category)

    # Apply tag filter
    if tags:
        for tag in tags:
            query = query.where(Design.tags.contains([tag]))

    # Apply search
    if search:
        search_pattern = f"%{search.lower()}%"
        query = query.where(
            or_(
                func.lower(Design.name).like(search_pattern),
                func.lower(Design.description).like(search_pattern),
            )
        )

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Apply sorting
    if sort == "popular" or sort == "saves":
        query = query.order_by(desc(Design.save_count))
    elif sort == "recent":
        query = query.order_by(desc(Design.published_at))
    elif sort == "trending":
        # Trending: combination of recency and saves
        # Designs with more saves in less time rank higher
        query = query.order_by(
            desc(
                Design.save_count
                / (func.extract("epoch", func.now() - Design.published_at) / 86400 + 1)
            )
        )

    # Apply pagination
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)

    # Execute query
    result = await db.execute(query)
    rows = result.all()

    # Convert to response
    items = [_design_to_summary(row.Design, row.author_name) for row in rows]

    total_pages = (total + page_size - 1) // page_size if total > 0 else 1

    return PaginatedDesignResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        has_next=page < total_pages,
        has_prev=page > 1,
    )


@router.get("/featured", response_model=list[DesignSummaryResponse])
async def get_featured_designs(
    limit: int = Query(6, ge=1, le=20, description="Number of featured designs"),
    db: AsyncSession = Depends(get_db),
) -> list[DesignSummaryResponse]:
    """
    Get featured/curated designs for homepage display.

    Returns designs that have been marked as featured by admins.
    """
    query = (
        select(Design, User.display_name.label("author_name"))
        .join(User, Design.user_id == User.id)
        .where(Design.featured_at.isnot(None))
        .where(Design.is_public == True)  # noqa: E712
        .where(Design.deleted_at.is_(None))
        .order_by(desc(Design.featured_at))
        .limit(limit)
    )

    result = await db.execute(query)
    rows = result.all()

    return [_design_to_summary(row.Design, row.author_name) for row in rows]


@router.get("/categories", response_model=list[CategoryResponse])
async def get_categories(
    db: AsyncSession = Depends(get_db),
) -> list[CategoryResponse]:
    """
    Get available categories with design counts.
    """
    query = (
        select(
            Design.category,
            func.count(Design.id).label("count"),
        )
        .where(Design.is_public == True)  # noqa: E712
        .where(Design.published_at.isnot(None))
        .where(Design.deleted_at.is_(None))
        .where(Design.category.isnot(None))
        .group_by(Design.category)
        .order_by(desc("count"))
    )

    result = await db.execute(query)
    rows = result.all()

    # Include all valid categories, even those with 0 designs
    category_counts = {row.category: row.count for row in rows}

    return [
        CategoryResponse(
            name=cat.replace("-", " ").title(),
            slug=cat,
            design_count=category_counts.get(cat, 0),
        )
        for cat in VALID_CATEGORIES
    ]


@router.get("/designs/{design_id}", response_model=MarketplaceDesignResponse)
async def get_design_detail(
    design_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User | None = Depends(get_current_user_optional),
) -> MarketplaceDesignResponse:
    """
    Get full design details for marketplace view.

    Includes save status for authenticated users.
    """
    query = (
        select(Design, User.display_name.label("author_name"))
        .join(User, Design.user_id == User.id)
        .where(Design.id == design_id)
        .where(Design.deleted_at.is_(None))
    )

    result = await db.execute(query)
    row = result.first()

    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Design not found",
        )

    design = row.Design
    author_name = row.author_name

    # Check if design is public or user owns it
    if not design.is_public and (not current_user or design.user_id != current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This design is private",
        )

    # Check save status for current user
    is_saved = False
    in_lists: list[UUID] = []

    if current_user:
        save_query = select(DesignSave).where(
            and_(
                DesignSave.user_id == current_user.id,
                DesignSave.design_id == design_id,
            )
        )
        save_result = await db.execute(save_query)
        if save_result.scalar_one_or_none():
            is_saved = True

        # Get list IDs
        from app.models.marketplace import DesignListItem

        list_query = (
            select(DesignListItem.list_id)
            .where(DesignListItem.design_id == design_id)
            .join(DesignListItem.list)
            .where(DesignListItem.list.has(user_id=current_user.id))
        )
        list_result = await db.execute(list_query)
        in_lists = [row[0] for row in list_result.all()]

    # Get remixed from info
    remixed_from_name = None
    if design.remixed_from_id:
        parent_query = select(Design.name).where(Design.id == design.remixed_from_id)
        parent_result = await db.execute(parent_query)
        parent_name = parent_result.scalar_one_or_none()
        remixed_from_name = parent_name

    return MarketplaceDesignResponse(
        id=design.id,
        name=design.name,
        description=design.description,
        thumbnail_url=design.thumbnail_url,
        category=design.category,
        tags=design.tags or [],
        save_count=design.save_count,
        remix_count=design.remix_count,
        is_starter=design.is_starter,
        created_at=design.created_at,
        published_at=design.published_at,
        author_id=design.user_id,
        author_name=author_name,
        is_saved=is_saved,
        in_lists=in_lists,
        remixed_from_id=design.remixed_from_id,
        remixed_from_name=remixed_from_name,
        featured_at=design.featured_at,
        has_step=design.step_file_path is not None,
        has_stl=design.stl_file_path is not None,
    )


# =============================================================================
# Publish Endpoints
# =============================================================================


@router.post("/designs/{design_id}/publish", response_model=PublishDesignResponse)
async def publish_design(
    design_id: UUID,
    request: PublishDesignRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_optional),
) -> PublishDesignResponse:
    """
    Publish a design to the marketplace.

    Makes the design publicly visible and searchable.
    """
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )

    query = select(Design).where(
        and_(
            Design.id == design_id,
            Design.user_id == current_user.id,
            Design.deleted_at.is_(None),
        )
    )
    result = await db.execute(query)
    design = result.scalar_one_or_none()

    if not design:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Design not found or not owned by you",
        )

    # Validate category
    if request.category and request.category not in VALID_CATEGORIES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid category. Must be one of: {', '.join(VALID_CATEGORIES)}",
        )

    # Update design
    from datetime import datetime

    design.is_public = True
    design.published_at = datetime.now(UTC)
    design.category = request.category
    if request.tags:
        design.tags = request.tags

    # Only admins can set is_starter
    if request.is_starter:
        # Check if user is admin (implement admin check as needed)
        # For now, we'll skip this
        pass

    await db.commit()
    await db.refresh(design)

    logger.info(f"Design {design_id} published by user {current_user.id}")

    return PublishDesignResponse(
        id=design.id,
        published_at=design.published_at,
        category=design.category,
        is_starter=design.is_starter,
    )


@router.post("/designs/{design_id}/unpublish")
async def unpublish_design(
    design_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_optional),
) -> dict[str, Any]:
    """
    Unpublish a design from the marketplace.

    The design becomes private again.
    """
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )

    query = select(Design).where(
        and_(
            Design.id == design_id,
            Design.user_id == current_user.id,
            Design.deleted_at.is_(None),
        )
    )
    result = await db.execute(query)
    design = result.scalar_one_or_none()

    if not design:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Design not found or not owned by you",
        )

    design.is_public = False
    design.published_at = None

    await db.commit()

    logger.info(f"Design {design_id} unpublished by user {current_user.id}")

    return {"message": "Design unpublished successfully"}
