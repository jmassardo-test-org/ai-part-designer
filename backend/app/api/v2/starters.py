"""
Starter Designs API endpoints.

Allows browsing vendor-published starter designs and remixing them.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any
from uuid import UUID  # noqa: TC003

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import desc, func, or_, select

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.design import Design
from app.models.project import Project
from app.models.user import User
from app.schemas.marketplace import (
    RemixRequest,
    RemixResponse,
    StarterDesignResponse,
    StarterDetailResponse,
    StarterListResponse,
)

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

router = APIRouter()


# =============================================================================
# Constants
# =============================================================================


STARTER_CATEGORIES = [
    "raspberry-pi",
    "arduino",
    "esp32",
    "electronics",
    "sensors",
    "power-supply",
    "audio",
    "display",
    "iot",
]


# =============================================================================
# Helper Functions
# =============================================================================


def _design_to_starter(design: Design) -> StarterDesignResponse:
    """Convert a Design model to a starter response."""
    # Extract features from enclosure_spec if available
    features: list[str] = []
    exterior_dims: dict[str, Any] | None = None

    if design.enclosure_spec:
        spec = design.enclosure_spec

        # Get dimensions
        if "exterior" in spec:
            ext = spec["exterior"]
            exterior_dims = {
                "width": ext.get("width", {}).get("value"),
                "depth": ext.get("depth", {}).get("value"),
                "height": ext.get("height", {}).get("value"),
                "unit": ext.get("width", {}).get("unit", "mm"),
            }

        # Extract feature types
        if "features" in spec:
            for feature in spec.get("features", []):
                feature_type = feature.get("type", "")
                if feature_type and feature_type not in features:
                    features.append(feature_type)

        # Add lid type
        if "lid" in spec:
            lid_type = spec["lid"].get("type")
            if lid_type:
                features.append(f"lid-{lid_type}")

        # Add ventilation
        if spec.get("ventilation", {}).get("enabled"):
            features.append("ventilation")

    return StarterDesignResponse(
        id=design.id,
        name=design.name,
        description=design.description,
        thumbnail_url=design.thumbnail_url,
        category=design.category,
        tags=design.tags or [],
        remix_count=design.remix_count,
        exterior_dimensions=exterior_dims,
        features=features,
        created_at=design.created_at,
    )


# =============================================================================
# Browse Endpoints
# =============================================================================


@router.get("/", response_model=StarterListResponse)
async def list_starter_designs(
    category: str | None = Query(None, description="Filter by category"),
    tags: list[str] | None = Query(None, description="Filter by tags"),
    search: str | None = Query(None, description="Search in name/description"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    db: AsyncSession = Depends(get_db),
) -> StarterListResponse:
    """
    List public starter designs for remixing.

    These are vendor-published template designs that users can
    use as starting points.
    """
    # Base query: starter designs only
    query = (
        select(Design)
        .where(Design.is_starter == True)  # noqa: E712
        .where(Design.is_public == True)  # noqa: E712
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

    # Apply sorting and pagination
    offset = (page - 1) * page_size
    query = query.order_by(desc(Design.remix_count), desc(Design.created_at))
    query = query.offset(offset).limit(page_size)

    result = await db.execute(query)
    designs = result.scalars().all()

    return StarterListResponse(
        items=[_design_to_starter(d) for d in designs],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/categories")
async def get_starter_categories(
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    """
    Get available starter categories with counts.
    """
    query = (
        select(
            Design.category,
            func.count(Design.id).label("count"),
        )
        .where(Design.is_starter == True)  # noqa: E712
        .where(Design.is_public == True)  # noqa: E712
        .where(Design.deleted_at.is_(None))
        .where(Design.category.isnot(None))
        .group_by(Design.category)
        .order_by(desc("count"))
    )

    result = await db.execute(query)
    rows = result.all()

    category_counts: dict[str, int] = {
        str(row[0]): int(row[1])
        for row in rows  # category, count
    }

    return [
        {
            "name": cat.replace("-", " ").title(),
            "slug": cat,
            "count": category_counts.get(cat, 0),
        }
        for cat in STARTER_CATEGORIES
        if category_counts.get(cat, 0) > 0
    ]


@router.get("/{design_id}", response_model=StarterDetailResponse)
async def get_starter_detail(
    design_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> StarterDetailResponse:
    """
    Get starter design details including EnclosureSpec for remixing.
    """
    query = (
        select(Design, User.display_name.label("author_name"))
        .join(User, Design.user_id == User.id)
        .where(Design.id == design_id)
        .where(Design.is_starter == True)  # noqa: E712
        .where(Design.is_public == True)  # noqa: E712
        .where(Design.deleted_at.is_(None))
    )

    result = await db.execute(query)
    row = result.first()

    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Starter design not found",
        )

    design = row.Design
    author_name = row.author_name

    # Extract features and dimensions
    features: list[str] = []
    exterior_dims: dict[str, Any] | None = None

    if design.enclosure_spec:
        spec = design.enclosure_spec

        if "exterior" in spec:
            ext = spec["exterior"]
            exterior_dims = {
                "width": ext.get("width", {}).get("value"),
                "depth": ext.get("depth", {}).get("value"),
                "height": ext.get("height", {}).get("value"),
                "unit": ext.get("width", {}).get("unit", "mm"),
            }

        if "features" in spec:
            for feature in spec.get("features", []):
                feature_type = feature.get("type", "")
                if feature_type and feature_type not in features:
                    features.append(feature_type)

    return StarterDetailResponse(
        id=design.id,
        name=design.name,
        description=design.description,
        thumbnail_url=design.thumbnail_url,
        category=design.category,
        tags=design.tags or [],
        remix_count=design.remix_count,
        exterior_dimensions=exterior_dims,
        features=features,
        created_at=design.created_at,
        enclosure_spec=design.enclosure_spec,
        author_id=design.user_id,
        author_name=author_name,
    )


# =============================================================================
# Remix Endpoints
# =============================================================================


@router.post("/{design_id}/remix", response_model=RemixResponse)
async def remix_design(
    design_id: UUID,
    request: RemixRequest | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> RemixResponse:
    """
    Create a remix (copy) of a starter design.

    The remix is a new design owned by the user with the
    same EnclosureSpec, ready for customization.
    """
    # Get starter design
    query = (
        select(Design)
        .where(Design.id == design_id)
        .where(Design.is_starter == True)  # noqa: E712
        .where(Design.is_public == True)  # noqa: E712
        .where(Design.deleted_at.is_(None))
    )

    result = await db.execute(query)
    starter = result.scalar_one_or_none()

    if not starter:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Starter design not found",
        )

    # Get or create default project
    project_query = (
        select(Project)
        .where(Project.user_id == current_user.id)
        .where(Project.name == "My Designs")
        .where(Project.deleted_at.is_(None))
    )
    project_result = await db.execute(project_query)
    project = project_result.scalar_one_or_none()

    if not project:
        project = Project(
            user_id=current_user.id,
            name="My Designs",
            description="Default project for your designs",
        )
        db.add(project)
        await db.flush()

    # Create remix name
    remix_name = request.name if request and request.name else f"{starter.name} (Remix)"

    # Create the remix design
    remix = Design(
        user_id=current_user.id,
        project_id=project.id,
        name=remix_name,
        description=f"Remixed from: {starter.name}",
        enclosure_spec=starter.enclosure_spec,
        remixed_from_id=starter.id,
        source_type="remix",
        status="draft",
        category=starter.category,
        tags=starter.tags,
        is_public=False,
        is_starter=False,
    )

    db.add(remix)

    # Increment remix count on original
    starter.remix_count = (starter.remix_count or 0) + 1

    await db.commit()
    await db.refresh(remix)

    # Notify original design owner (if different from remixer and if enabled)
    if starter.user_id != current_user.id:
        from app.services.notification_service import notify_design_remixed

        await notify_design_remixed(
            db=db,
            recipient_id=starter.user_id,
            actor_id=current_user.id,
            actor_name=current_user.display_name or current_user.email,
            design_id=starter.id,
            design_name=starter.name,
            remix_name=remix_name,
        )

    logger.info(f"User {current_user.id} remixed starter {design_id} -> {remix.id}")

    return RemixResponse(
        id=remix.id,
        name=remix.name,
        remixed_from_id=starter.id,
        remixed_from_name=starter.name,
        enclosure_spec=remix.enclosure_spec or {},
        created_at=remix.created_at,
    )


@router.get("/{design_id}/remixes", response_model=StarterListResponse)
async def list_design_remixes(
    design_id: UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> StarterListResponse:
    """
    List public remixes of a starter design.
    """
    # Base query: remixes of this design that are public
    query = (
        select(Design)
        .where(Design.remixed_from_id == design_id)
        .where(Design.is_public == True)  # noqa: E712
        .where(Design.deleted_at.is_(None))
    )

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Apply pagination
    offset = (page - 1) * page_size
    query = query.order_by(desc(Design.created_at))
    query = query.offset(offset).limit(page_size)

    result = await db.execute(query)
    designs = result.scalars().all()

    return StarterListResponse(
        items=[_design_to_starter(d) for d in designs],
        total=total,
        page=page,
        page_size=page_size,
    )
