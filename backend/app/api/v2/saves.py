"""
Design Saves API endpoints.

Allows users to save/unsave designs and check save status.
"""

from __future__ import annotations

import logging
from datetime import UTC
from typing import TYPE_CHECKING
from uuid import UUID

from fastapi import APIRouter, Body, Depends, HTTPException, Query, status
from sqlalchemy import and_, delete, func, select, update

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.design import Design
from app.models.marketplace import DesignList, DesignListItem, DesignSave
from app.models.user import User
from app.schemas.marketplace import (
    DesignSummaryResponse,
    ListItemWithDesign,
    ListResponse,
    PaginatedSavesResponse,
    SaveResponse,
    SaveStatusResponse,
    UnsaveResponse,
)

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

router = APIRouter()


# =============================================================================
# Constants
# =============================================================================


DEFAULT_LIST_NAME = "Saved Designs"


# =============================================================================
# Helper Functions
# =============================================================================


async def get_or_create_default_list(user_id: UUID, db: AsyncSession) -> DesignList:
    """Get or create the user's default 'Saved Designs' list."""
    query = select(DesignList).where(
        and_(
            DesignList.user_id == user_id,
            DesignList.name == DEFAULT_LIST_NAME,
            DesignList.deleted_at.is_(None),
        )
    )
    result = await db.execute(query)
    list_obj = result.scalar_one_or_none()

    if not list_obj:
        list_obj = DesignList(
            user_id=user_id,
            name=DEFAULT_LIST_NAME,
            description="Your saved designs",
            icon="heart",
            color="#ef4444",
            is_public=False,
            position=0,
        )
        db.add(list_obj)
        await db.flush()

    return list_obj


# =============================================================================
# Save Endpoints
# =============================================================================


@router.post("/{design_id}", response_model=SaveResponse)
async def save_design(
    design_id: UUID,
    list_ids: list[UUID] | None = Body(None, embed=True),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SaveResponse:
    """
    Save a design to your account.

    Optionally add to specific lists. If no lists specified,
    adds to the default 'Saved Designs' list.
    """
    # Verify design exists and is accessible
    design_query = select(Design).where(
        and_(
            Design.id == design_id,
            Design.deleted_at.is_(None),
        )
    )
    result = await db.execute(design_query)
    design = result.scalar_one_or_none()

    if not design:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Design not found",
        )

    # Check if design is public or owned by user
    if not design.is_public and design.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot save private design",
        )

    # Check if already saved
    existing_save_query = select(DesignSave).where(
        and_(
            DesignSave.user_id == current_user.id,
            DesignSave.design_id == design_id,
        )
    )
    existing_result = await db.execute(existing_save_query)
    existing_save = existing_result.scalar_one_or_none()

    from datetime import datetime

    if not existing_save:
        # Create save record
        save_record = DesignSave(
            user_id=current_user.id,
            design_id=design_id,
        )
        db.add(save_record)

        # Increment save count
        design.save_count = (design.save_count or 0) + 1

    # Determine which lists to add to
    target_lists: list[DesignList] = []

    if list_ids:
        # Add to specified lists
        for list_id in list_ids:
            list_query = select(DesignList).where(
                and_(
                    DesignList.id == list_id,
                    DesignList.user_id == current_user.id,
                    DesignList.deleted_at.is_(None),
                )
            )
            list_result = await db.execute(list_query)
            list_obj = list_result.scalar_one_or_none()

            if list_obj:
                target_lists.append(list_obj)
    else:
        # Add to default list
        default_list = await get_or_create_default_list(current_user.id, db)
        target_lists.append(default_list)

    # Add to lists (avoid duplicates)
    added_lists: list[ListResponse] = []

    for list_obj in target_lists:
        # Check if already in list
        existing_item_query = select(DesignListItem).where(
            and_(
                DesignListItem.list_id == list_obj.id,
                DesignListItem.design_id == design_id,
            )
        )
        existing_item_result = await db.execute(existing_item_query)

        if not existing_item_result.scalar_one_or_none():
            # Get max position
            max_pos_query = select(func.max(DesignListItem.position)).where(
                DesignListItem.list_id == list_obj.id
            )
            pos_result = await db.execute(max_pos_query)
            max_pos = pos_result.scalar() or 0

            item = DesignListItem(
                list_id=list_obj.id,
                design_id=design_id,
                position=max_pos + 1,
            )
            db.add(item)

        # Get item count for response
        count_query = select(func.count(DesignListItem.id)).where(
            DesignListItem.list_id == list_obj.id
        )
        count_result = await db.execute(count_query)
        item_count = (count_result.scalar() or 0) + 1  # +1 for the new item

        added_lists.append(
            ListResponse(
                id=list_obj.id,
                name=list_obj.name,
                description=list_obj.description,
                icon=list_obj.icon,
                color=list_obj.color,
                is_public=list_obj.is_public,
                position=list_obj.position,
                item_count=item_count,
                created_at=list_obj.created_at,
                updated_at=list_obj.updated_at,
            )
        )

    await db.commit()

    logger.info(f"User {current_user.id} saved design {design_id}")

    return SaveResponse(
        design_id=design_id,
        saved_at=datetime.now(UTC),
        lists=added_lists,
    )


@router.delete("/{design_id}", response_model=UnsaveResponse)
async def unsave_design(
    design_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> UnsaveResponse:
    """
    Unsave a design.

    Removes from all lists and deletes the save record.
    """
    # Get all list items for this design
    list_items_query = (
        select(DesignListItem)
        .join(DesignList, DesignListItem.list_id == DesignList.id)
        .where(
            and_(
                DesignListItem.design_id == design_id,
                DesignList.user_id == current_user.id,
            )
        )
    )
    result = await db.execute(list_items_query)
    items = result.scalars().all()

    removed_count = len(items)

    # Delete list items
    for item in items:
        await db.delete(item)

    # Delete save record
    delete_save_result = await db.execute(
        delete(DesignSave).where(
            and_(
                DesignSave.user_id == current_user.id,
                DesignSave.design_id == design_id,
            )
        )
    )

    # Decrement save count if save existed
    if delete_save_result.rowcount > 0:  # type: ignore[attr-defined]
        await db.execute(
            update(Design).where(Design.id == design_id).values(save_count=Design.save_count - 1)
        )

    await db.commit()

    logger.info(f"User {current_user.id} unsaved design {design_id}")

    return UnsaveResponse(
        design_id=design_id,
        removed_from_lists=removed_count,
    )


@router.get("/", response_model=PaginatedSavesResponse)
async def get_my_saves(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PaginatedSavesResponse:
    """
    Get all designs saved by the current user.
    """
    # Base query: all save records for user
    base_query = (
        select(DesignSave, Design, User.display_name.label("author_name"))
        .join(Design, DesignSave.design_id == Design.id)
        .join(User, Design.user_id == User.id)
        .where(DesignSave.user_id == current_user.id)
        .where(Design.deleted_at.is_(None))
    )

    # Get total count
    count_query = select(func.count()).select_from(
        select(DesignSave)
        .join(Design, DesignSave.design_id == Design.id)
        .where(DesignSave.user_id == current_user.id)
        .where(Design.deleted_at.is_(None))
        .subquery()
    )
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Apply pagination
    offset = (page - 1) * page_size
    query = base_query.offset(offset).limit(page_size).order_by(DesignSave.created_at.desc())

    result = await db.execute(query)
    rows = result.all()

    items = [
        ListItemWithDesign(
            id=row.DesignSave.id,
            list_id=UUID(
                "00000000-0000-0000-0000-000000000000"
            ),  # Placeholder, not in a specific list view
            design_id=row.DesignSave.design_id,
            note=None,
            position=0,
            created_at=row.DesignSave.created_at,
            design_name=row.Design.name,
            design_thumbnail_url=row.Design.thumbnail_url,
            design=DesignSummaryResponse(
                id=row.Design.id,
                name=row.Design.name,
                description=row.Design.description,
                thumbnail_url=row.Design.thumbnail_url,
                category=row.Design.category,
                tags=row.Design.tags or [],
                save_count=row.Design.save_count,
                remix_count=row.Design.remix_count,
                is_starter=row.Design.is_starter,
                created_at=row.Design.created_at,
                published_at=row.Design.published_at,
                author_id=row.Design.user_id,
                author_name=row.author_name,
            ),
        )
        for row in rows
    ]

    return PaginatedSavesResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{design_id}/check", response_model=SaveStatusResponse)
async def check_saved(
    design_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SaveStatusResponse:
    """
    Check if a design is saved and which lists it's in.
    """
    # Check if saved
    save_query = select(DesignSave).where(
        and_(
            DesignSave.user_id == current_user.id,
            DesignSave.design_id == design_id,
        )
    )
    save_result = await db.execute(save_query)
    is_saved = save_result.scalar_one_or_none() is not None

    # Get list IDs
    list_query = (
        select(DesignListItem.list_id)
        .join(DesignList, DesignListItem.list_id == DesignList.id)
        .where(
            and_(
                DesignListItem.design_id == design_id,
                DesignList.user_id == current_user.id,
                DesignList.deleted_at.is_(None),
            )
        )
    )
    list_result = await db.execute(list_query)
    in_lists = [row[0] for row in list_result.all()]

    return SaveStatusResponse(
        design_id=design_id,
        is_saved=is_saved,
        in_lists=in_lists,
    )
