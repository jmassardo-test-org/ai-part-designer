"""
Design Lists API endpoints.

Allows users to create and manage lists for organizing saved designs.
"""

from __future__ import annotations

import logging
from datetime import UTC
from typing import TYPE_CHECKING
from uuid import UUID  # noqa: TC003

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import and_, delete, func, select, update

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.design import Design
from app.models.marketplace import DesignList, DesignListItem
from app.models.user import User
from app.schemas.marketplace import (
    AddToListRequest,
    DesignSummaryResponse,
    ListCreate,
    ListItemResponse,
    ListItemWithDesign,
    ListResponse,
    ListUpdate,
    ListWithItems,
    ReorderRequest,
    UpdateListItemRequest,
)

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

router = APIRouter()


# =============================================================================
# Helper Functions
# =============================================================================


async def get_user_list(
    list_id: UUID,
    user_id: UUID,
    db: AsyncSession,
) -> DesignList:
    """Get a list owned by the user, or raise 404."""
    query = select(DesignList).where(
        and_(
            DesignList.id == list_id,
            DesignList.user_id == user_id,
            DesignList.deleted_at.is_(None),
        )
    )
    result = await db.execute(query)
    list_obj = result.scalar_one_or_none()

    if not list_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="List not found",
        )

    return list_obj


def _list_to_response(list_obj: DesignList, item_count: int = 0) -> ListResponse:
    """Convert a DesignList model to a response."""
    return ListResponse(
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


# =============================================================================
# List CRUD Endpoints
# =============================================================================


@router.get("/", response_model=list[ListResponse])
async def get_my_lists(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[ListResponse]:
    """
    Get all lists for the current user.

    Returns lists sorted by position.
    """
    query = (
        select(
            DesignList,
            func.count(DesignListItem.id).label("item_count"),
        )
        .outerjoin(DesignListItem, DesignList.id == DesignListItem.list_id)
        .where(DesignList.user_id == current_user.id)
        .where(DesignList.deleted_at.is_(None))
        .group_by(DesignList.id)
        .order_by(DesignList.position)
    )

    result = await db.execute(query)
    rows = result.all()

    return [_list_to_response(row.DesignList, row.item_count) for row in rows]


@router.post("/", response_model=ListResponse, status_code=status.HTTP_201_CREATED)
async def create_list(
    request: ListCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ListResponse:
    """
    Create a new design list.
    """
    # Get max position for ordering
    max_pos_query = select(func.max(DesignList.position)).where(
        and_(
            DesignList.user_id == current_user.id,
            DesignList.deleted_at.is_(None),
        )
    )
    result = await db.execute(max_pos_query)
    max_pos = result.scalar() or 0

    list_obj = DesignList(
        user_id=current_user.id,
        name=request.name,
        description=request.description,
        icon=request.icon,
        color=request.color,
        is_public=request.is_public,
        position=max_pos + 1,
    )

    db.add(list_obj)
    await db.commit()
    await db.refresh(list_obj)

    logger.info(f"Created list '{request.name}' for user {current_user.id}")

    return _list_to_response(list_obj, 0)


@router.get("/{list_id}", response_model=ListWithItems)
async def get_list(
    list_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ListWithItems:
    """
    Get a list with all its items.
    """
    list_obj = await get_user_list(list_id, current_user.id, db)

    # Get items with design info
    items_query = (
        select(DesignListItem, Design.name, Design.thumbnail_url)
        .join(Design, DesignListItem.design_id == Design.id)
        .where(DesignListItem.list_id == list_id)
        .order_by(DesignListItem.position)
    )

    result = await db.execute(items_query)
    rows = result.all()

    items = [
        ListItemResponse(
            id=row.DesignListItem.id,
            list_id=row.DesignListItem.list_id,
            design_id=row.DesignListItem.design_id,
            note=row.DesignListItem.note,
            position=row.DesignListItem.position,
            created_at=row.DesignListItem.created_at,
            design_name=row.name,
            design_thumbnail_url=row.thumbnail_url,
        )
        for row in rows
    ]

    return ListWithItems(
        id=list_obj.id,
        name=list_obj.name,
        description=list_obj.description,
        icon=list_obj.icon,
        color=list_obj.color,
        is_public=list_obj.is_public,
        position=list_obj.position,
        item_count=len(items),
        created_at=list_obj.created_at,
        updated_at=list_obj.updated_at,
        items=items,
    )


@router.put("/{list_id}", response_model=ListResponse)
async def update_list(
    list_id: UUID,
    request: ListUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ListResponse:
    """
    Update a list's name, description, color, etc.
    """
    list_obj = await get_user_list(list_id, current_user.id, db)

    # Update fields if provided
    if request.name is not None:
        list_obj.name = request.name
    if request.description is not None:
        list_obj.description = request.description
    if request.icon is not None:
        list_obj.icon = request.icon
    if request.color is not None:
        list_obj.color = request.color
    if request.is_public is not None:
        list_obj.is_public = request.is_public
    if request.position is not None:
        list_obj.position = request.position

    await db.commit()
    await db.refresh(list_obj)

    # Get item count
    count_query = select(func.count(DesignListItem.id)).where(DesignListItem.list_id == list_id)
    result = await db.execute(count_query)
    item_count = result.scalar() or 0

    logger.info(f"Updated list {list_id} for user {current_user.id}")

    return _list_to_response(list_obj, item_count)


@router.delete("/{list_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_list(
    list_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    """
    Delete a list.

    The designs themselves are not deleted, only removed from the list.
    """
    list_obj = await get_user_list(list_id, current_user.id, db)

    # Soft delete the list
    from datetime import datetime

    list_obj.deleted_at = datetime.now(UTC)

    # Also delete all items (they'll cascade but let's be explicit)
    await db.execute(delete(DesignListItem).where(DesignListItem.list_id == list_id))

    await db.commit()

    logger.info(f"Deleted list {list_id} for user {current_user.id}")


# =============================================================================
# List Item Endpoints
# =============================================================================


@router.get("/{list_id}/items", response_model=list[ListItemWithDesign])
async def get_list_items(
    list_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[ListItemWithDesign]:
    """
    Get all items in a list with full design info.
    """
    # Verify ownership
    await get_user_list(list_id, current_user.id, db)

    query = (
        select(DesignListItem, Design, User.display_name.label("author_name"))
        .join(Design, DesignListItem.design_id == Design.id)
        .join(User, Design.user_id == User.id)
        .where(DesignListItem.list_id == list_id)
        .order_by(DesignListItem.position)
    )

    result = await db.execute(query)
    rows = result.all()

    return [
        ListItemWithDesign(
            id=row.DesignListItem.id,
            list_id=row.DesignListItem.list_id,
            design_id=row.DesignListItem.design_id,
            note=row.DesignListItem.note,
            position=row.DesignListItem.position,
            created_at=row.DesignListItem.created_at,
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


@router.post(
    "/{list_id}/items", response_model=ListItemResponse, status_code=status.HTTP_201_CREATED
)
async def add_to_list(
    list_id: UUID,
    request: AddToListRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ListItemResponse:
    """
    Add a design to a list.
    """
    # Verify list ownership
    await get_user_list(list_id, current_user.id, db)

    # Verify design exists and is accessible
    design_query = select(Design).where(
        and_(
            Design.id == request.design_id,
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
            detail="Cannot add private design to list",
        )

    # Check for duplicate
    existing_query = select(DesignListItem).where(
        and_(
            DesignListItem.list_id == list_id,
            DesignListItem.design_id == request.design_id,
        )
    )
    existing_result = await db.execute(existing_query)
    if existing_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Design is already in this list",
        )

    # Get max position
    max_pos_query = select(func.max(DesignListItem.position)).where(
        DesignListItem.list_id == list_id
    )
    result = await db.execute(max_pos_query)
    scalar_result = result.scalar()
    max_pos = int(scalar_result) if isinstance(scalar_result, int) else 0

    # Create item
    item = DesignListItem(
        list_id=list_id,
        design_id=request.design_id,
        note=request.note,
        position=max_pos + 1,
    )

    db.add(item)
    await db.commit()
    await db.refresh(item)

    logger.info(f"Added design {request.design_id} to list {list_id}")

    return ListItemResponse(
        id=item.id,
        list_id=item.list_id,
        design_id=item.design_id,
        note=item.note,
        position=item.position,
        created_at=item.created_at,
        design_name=design.name,
        design_thumbnail_url=design.thumbnail_url,
    )


@router.put("/{list_id}/items/{item_id}", response_model=ListItemResponse)
async def update_list_item(
    list_id: UUID,
    item_id: UUID,
    request: UpdateListItemRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ListItemResponse:
    """
    Update a list item (e.g., change the note).
    """
    # Verify list ownership
    await get_user_list(list_id, current_user.id, db)

    # Get item
    query = (
        select(DesignListItem, Design.name, Design.thumbnail_url)
        .join(Design, DesignListItem.design_id == Design.id)
        .where(
            and_(
                DesignListItem.id == item_id,
                DesignListItem.list_id == list_id,
            )
        )
    )
    result = await db.execute(query)
    row = result.first()

    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item not found in list",
        )

    item = row.DesignListItem

    # Update note
    if request.note is not None:
        item.note = request.note

    await db.commit()
    await db.refresh(item)

    return ListItemResponse(
        id=item.id,
        list_id=item.list_id,
        design_id=item.design_id,
        note=item.note,
        position=item.position,
        created_at=item.created_at,
        design_name=row.name,
        design_thumbnail_url=row.thumbnail_url,
    )


@router.delete("/{list_id}/items/{design_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_from_list(
    list_id: UUID,
    design_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    """
    Remove a design from a list.
    """
    # Verify list ownership
    await get_user_list(list_id, current_user.id, db)

    # Delete the item
    result = await db.execute(
        delete(DesignListItem).where(
            and_(
                DesignListItem.list_id == list_id,
                DesignListItem.design_id == design_id,
            )
        )
    )

    if result.rowcount == 0:  # type: ignore[attr-defined]
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Design not found in list",
        )

    await db.commit()

    logger.info(f"Removed design {design_id} from list {list_id}")


@router.patch("/{list_id}/items/reorder", status_code=status.HTTP_204_NO_CONTENT)
async def reorder_list_items(
    list_id: UUID,
    request: ReorderRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    """
    Reorder items in a list.

    Provide the item IDs in the desired order.
    """
    # Verify list ownership
    await get_user_list(list_id, current_user.id, db)

    # Update positions
    for position, item_id in enumerate(request.item_ids):
        await db.execute(
            update(DesignListItem)
            .where(
                and_(
                    DesignListItem.id == item_id,
                    DesignListItem.list_id == list_id,
                )
            )
            .values(position=position)
        )

    await db.commit()

    logger.info(f"Reordered items in list {list_id}")
