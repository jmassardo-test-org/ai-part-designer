"""
Marketplace API endpoints.

Allows browsing public designs, featured designs, and categories.
"""

from __future__ import annotations

import logging
from datetime import UTC
from typing import TYPE_CHECKING, Any
from uuid import UUID  # noqa: TC003 — FastAPI needs UUID at runtime for path params

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, desc, func, or_, select

from app.api.deps import get_current_user, get_current_user_optional
from app.core.database import get_db
from app.core.licenses import (
    LICENSE_METADATA,
    LicenseType,
    is_valid_license_type,
)
from app.core.rate_limiter import RateLimiter
from app.models.design import Design
from app.models.marketplace import DesignSave
from app.models.project import Project
from app.models.user import User
from app.schemas.license import (
    LicenseViolationReportCreate,
    LicenseViolationReportResponse,
)
from app.schemas.marketplace import (
    CategoryResponse,
    DesignSummaryResponse,
    MarketplaceDesignResponse,
    PaginatedDesignResponse,
    PublishDesignRequest,
    PublishDesignResponse,
    RemixRequest,
    RemixResponse,
)
from app.schemas.rating import (
    DesignCommentCreate,
    DesignCommentResponse,
    DesignCommentUpdate,
    DesignRatingCreate,
    DesignRatingResponse,
    DesignRatingSummary,
    DesignReportCreate,
    DesignReportResponse,
    DesignReportStatus,
)
from app.services.design_comment_service import DesignCommentService
from app.services.design_rating_service import DesignRatingService
from app.services.design_report_service import DesignReportService
from app.services.license_service import LicenseService

if TYPE_CHECKING:
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
        license_type=design.license_type,
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
    license_type: str | None = Query(None, description="Filter by exact license type"),
    allows_remix_filter: bool | None = Query(
        None, alias="allows_remix", description="Filter: only designs that allow remix",
    ),
    allows_commercial: bool | None = Query(
        None, description="Filter: only designs that allow commercial use",
    ),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    db: AsyncSession = Depends(get_db),
    _current_user: User | None = Depends(get_current_user_optional),
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

    # Apply license filters (Epic 13)
    if license_type:
        if not is_valid_license_type(license_type):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid license_type filter value",
            )
        query = query.where(Design.license_type == license_type)

    if allows_remix_filter is True:
        remix_types = [
            lt.value for lt, meta in LICENSE_METADATA.items() if meta.allows_remix
        ]
        query = query.where(
            or_(
                Design.license_type.in_(remix_types),
                and_(
                    Design.license_type == LicenseType.CUSTOM,
                    Design.custom_allows_remix == True,  # noqa: E712
                ),
                Design.license_type.is_(None),  # Legacy designs
            )
        )

    if allows_commercial is True:
        commercial_types = [
            lt.value for lt, meta in LICENSE_METADATA.items() if meta.allows_commercial
        ]
        query = query.where(
            or_(
                Design.license_type.in_(commercial_types),
                Design.license_type.is_(None),  # Legacy designs
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

    # Build license detail (Epic 13)
    license_service = LicenseService(db)
    license_info = license_service.get_license_detail(design) if design.license_type else None
    attribution = (
        design.extra_data.get("attribution")
        if design.extra_data
        else None
    )

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
        # Check extra_data for file paths (v2 designs store downloads there)
        has_step=bool(
            design.extra_data.get("downloads", {}).get("body") if design.extra_data else False
        ),
        has_stl=bool(
            design.extra_data.get("downloads", {}).get("stl") if design.extra_data else False
        ),
        license_type=design.license_type,
        license_info=license_info,
        attribution=attribution,
    )


# =============================================================================
# Publish Endpoints
# =============================================================================


@router.post("/designs/{design_id}/publish", response_model=PublishDesignResponse)
async def publish_design(
    design_id: UUID,
    request: PublishDesignRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PublishDesignResponse:
    """
    Publish a design to the marketplace.

    Makes the design publicly visible and searchable.
    """

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

    # Validate license (Epic 13)
    license_service = LicenseService(db)
    try:
        await license_service.validate_license_for_publish(
            design=design,
            license_type=request.license_type,
            custom_license_text=request.custom_license_text,
            custom_allows_remix=request.custom_allows_remix,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    # Update design
    from datetime import datetime

    design.is_public = True
    design.published_at = datetime.now(UTC)
    design.category = request.category
    if request.tags:
        design.tags = request.tags

    # Persist license fields (Epic 13)
    if request.license_type is not None:
        design.license_type = request.license_type
        design.custom_license_text = request.custom_license_text
        design.custom_allows_remix = request.custom_allows_remix

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
        license_type=design.license_type,
    )


@router.post("/designs/{design_id}/unpublish")
async def unpublish_design(
    design_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """
    Unpublish a design from the marketplace.

    The design becomes private again.
    """

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


# =============================================================================
# Rating Endpoints
# =============================================================================


@router.put(
    "/designs/{design_id}/ratings",
    response_model=DesignRatingResponse,
    status_code=status.HTTP_200_OK,
)
async def rate_design(
    design_id: UUID,
    data: DesignRatingCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DesignRatingResponse:
    """Create or update a rating for a marketplace design.

    Authenticated users can rate any public design they don't own.
    If the user has already rated this design, their rating is updated.
    """
    service = DesignRatingService(db)
    try:
        return await service.create_or_update_rating(design_id, current_user, data)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.delete(
    "/designs/{design_id}/ratings",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_design_rating(
    design_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    """Delete the current user's rating for a design."""
    service = DesignRatingService(db)
    try:
        await service.delete_rating(design_id, current_user)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get(
    "/designs/{design_id}/ratings",
    response_model=dict,
)
async def get_design_ratings(
    design_id: UUID,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get paginated ratings for a design with user information."""
    service = DesignRatingService(db)
    ratings, total = await service.get_design_ratings(design_id, page, page_size)
    return {
        "ratings": ratings,
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get(
    "/designs/{design_id}/ratings/summary",
    response_model=DesignRatingSummary,
)
async def get_design_rating_summary(
    design_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> DesignRatingSummary:
    """Get aggregate rating summary for a design."""
    service = DesignRatingService(db)
    return await service.get_rating_summary(design_id)


@router.get(
    "/designs/{design_id}/ratings/me",
    response_model=DesignRatingResponse | None,
)
async def get_my_design_rating(
    design_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DesignRatingResponse | None:
    """Get the current user's rating for a design."""
    service = DesignRatingService(db)
    return await service.get_user_rating(design_id, current_user.id)


# =============================================================================
# Comment Endpoints
# =============================================================================


@router.post(
    "/designs/{design_id}/comments",
    response_model=DesignCommentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_design_comment(
    design_id: UUID,
    data: DesignCommentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DesignCommentResponse:
    """Create a comment on a marketplace design.

    Supports threaded replies via parent_id.
    """
    service = DesignCommentService(db)
    try:
        return await service.create_comment(design_id, current_user, data)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.put(
    "/designs/comments/{comment_id}",
    response_model=DesignCommentResponse,
)
async def update_design_comment(
    comment_id: UUID,
    data: DesignCommentUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DesignCommentResponse:
    """Update a comment. Only the comment owner can edit."""
    service = DesignCommentService(db)
    try:
        return await service.update_comment(comment_id, current_user, data)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.delete(
    "/designs/comments/{comment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_design_comment(
    comment_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    """Delete a comment. Soft-deletes if it has replies."""
    service = DesignCommentService(db)
    try:
        await service.delete_comment(comment_id, current_user)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get(
    "/designs/{design_id}/comments",
    response_model=dict,
)
async def get_design_comments(
    design_id: UUID,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get threaded comments for a design."""
    service = DesignCommentService(db)
    comments, total = await service.get_design_comments(design_id, page, page_size)
    return {
        "comments": comments,
        "total": total,
        "page": page,
        "page_size": page_size,
    }


# =============================================================================
# Remix Endpoint
# =============================================================================


@router.post(
    "/designs/{design_id}/remix",
    response_model=RemixResponse,
    status_code=status.HTTP_201_CREATED,
)
async def remix_marketplace_design(
    design_id: UUID,
    data: RemixRequest | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> RemixResponse:
    """Remix (fork) a public marketplace design.

    Creates a copy of the design in the user's default project.
    Increments the original design's remix_count.
    """
    # Get the design
    design_stmt = select(Design).where(
        Design.id == design_id,
        Design.is_public == True,  # noqa: E712
        Design.deleted_at.is_(None),
    )
    result = await db.execute(design_stmt)
    design = result.scalar_one_or_none()

    if not design:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Design not found or not public",
        )

    # Check license allows remixing (Epic 13)
    license_service = LicenseService(db)
    allowed, reason = await license_service.check_remix_allowed(design, current_user)
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=reason or "This design's license does not allow remixing.",
        )

    # Get or create default project
    project_stmt = select(Project).where(
        Project.user_id == current_user.id,
        Project.name == "My Designs",
    )
    project_result = await db.execute(project_stmt)
    project = project_result.scalar_one_or_none()

    if not project:
        project = Project(
            name="My Designs",
            user_id=current_user.id,
            description="Default project for remixed designs",
        )
        db.add(project)
        await db.flush()

    # Build attribution if license requires it (Epic 13)
    remix_extra_data = dict(design.extra_data) if design.extra_data else {}
    if design.license_type:
        author_stmt = select(User).where(User.id == design.user_id)
        author_result = await db.execute(author_stmt)
        parent_author = author_result.scalar_one_or_none()
        if parent_author:
            attribution = await license_service.build_attribution(design, parent_author)
            remix_extra_data["attribution"] = attribution

    # Create the remix
    remix_name = data.name if data and data.name else f"{design.name} (Remix)"
    remix = Design(
        name=remix_name,
        description=design.description,
        user_id=current_user.id,
        project_id=project.id,
        template_id=design.template_id,
        extra_data=remix_extra_data,
        remixed_from_id=design.id,
        category=design.category,
        tags=design.tags,
        is_public=False,
        enclosure_spec=design.enclosure_spec,
        source_type=design.source_type,
    )
    db.add(remix)

    # Increment remix count on original
    design.remix_count = (design.remix_count or 0) + 1

    await db.commit()
    await db.refresh(remix)

    return RemixResponse(
        id=remix.id,
        name=remix.name,
        remixed_from_id=design.id,
        remixed_from_name=design.name,
        enclosure_spec=remix.enclosure_spec or {},
        created_at=remix.created_at,
    )


# =============================================================================
# Report Endpoint
# =============================================================================


@router.post(
    "/designs/{design_id}/report",
    response_model=DesignReportResponse,
    status_code=status.HTTP_201_CREATED,
)
async def report_design(
    design_id: UUID,
    data: DesignReportCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DesignReportResponse:
    """Report a marketplace design for content moderation.

    Each user can only report a design once.
    """
    service = DesignReportService(db)
    try:
        return await service.create_report(design_id, current_user, data)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get(
    "/designs/{design_id}/report/status",
    response_model=DesignReportStatus,
)
async def get_report_status(
    design_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DesignReportStatus:
    """Check if the current user has already reported a design."""
    service = DesignReportService(db)
    return await service.check_report_status(design_id, current_user.id)


# =============================================================================
# View Tracking Endpoint
# =============================================================================


@router.post(
    "/designs/{design_id}/view",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def track_design_view(
    design_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> None:
    """Increment the view count for a marketplace design.

    This is a fire-and-forget endpoint for analytics.
    No authentication required.
    """
    design = await db.get(Design, design_id)
    if design and design.is_public:
        design.view_count = (design.view_count or 0) + 1
        await db.commit()


# =============================================================================
# License Violation Report Endpoint (Epic 13)
# =============================================================================

# Strict rate limit for violation reports (5 per user per hour)
violation_report_limit = RateLimiter(
    max_requests=5,
    window_seconds=3600,
    key_prefix="rate_limit:violation_report",
)


@router.post(
    "/designs/{design_id}/report-violation",
    response_model=LicenseViolationReportResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(violation_report_limit)],
)
async def report_license_violation(
    design_id: UUID,
    data: LicenseViolationReportCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> LicenseViolationReportResponse:
    """Report a license violation on a marketplace design.

    Each user can only report a design for license violation once.
    Rate limited to 5 reports per hour per user to prevent abuse.
    """
    service = LicenseService(db)
    try:
        return await service.report_violation(
            design_id=design_id,
            reporter=current_user,
            violation_type=data.violation_type,
            description=data.description,
            evidence_url=data.evidence_url,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
