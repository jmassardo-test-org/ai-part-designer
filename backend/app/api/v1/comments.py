"""
Comments API endpoints.

Handles design comments with threading and mentions.
"""

import re
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.core.database import get_db
from app.models import Design, DesignShare, User
from app.services.notification_service import (
    notify_comment_added,
    notify_comment_mention,
    notify_comment_reply,
)

router = APIRouter(prefix="/comments", tags=["comments"])

# Regex to match @mentions (alphanumeric, underscores, hyphens)
MENTION_PATTERN = re.compile(r"@([a-zA-Z0-9_-]+)")


# =============================================================================
# Schemas
# =============================================================================


class CommentCreate(BaseModel):
    """Create a new comment."""

    content: str = Field(..., min_length=1, max_length=5000)
    parent_id: UUID | None = None  # For replies
    # 3D annotation data (optional)
    position: dict[str, Any] | None = None  # {"x": 0, "y": 0, "z": 0}
    camera: dict[str, Any] | None = None  # Camera position for this annotation


class CommentUpdate(BaseModel):
    """Update an existing comment."""

    content: str = Field(..., min_length=1, max_length=5000)


class CommentAuthor(BaseModel):
    """Comment author info."""

    id: UUID
    display_name: str
    email: str
    avatar_url: str | None = None


class CommentResponse(BaseModel):
    """Comment response."""

    id: UUID
    design_id: UUID
    author: CommentAuthor
    content: str
    parent_id: UUID | None
    position: dict[str, Any] | None
    camera: dict[str, Any] | None
    reply_count: int
    is_edited: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class PaginatedCommentsResponse(BaseModel):
    """Paginated list of comments."""

    items: list[CommentResponse]
    total: int
    page: int
    page_size: int
    has_more: bool


# =============================================================================
# In-memory comment storage (replace with DB model)
# =============================================================================

# Temporary storage until Comment model is added
_comments: dict[str, dict[str, Any]] = {}


# =============================================================================
# Helper Functions
# =============================================================================


async def _resolve_mentions_to_user_ids(
    db: AsyncSession, mention_slugs: list[str], exclude_user_id: UUID
) -> list[UUID]:
    """Resolve @mention slugs to user IDs. Matches display_name (no spaces) or email prefix."""
    if not mention_slugs:
        return []

    from sqlalchemy import func

    from app.models import User

    # For each slug: match display_name (lowercase, no spaces) OR email prefix
    slug_conditions = []
    for slug in mention_slugs:
        slug_lower = slug.lower()
        slug_conditions.append(
            or_(
                func.lower(func.replace(User.display_name, " ", "")) == slug_lower,
                User.email.ilike(f"{slug_lower}%"),
            )
        )

    result = await db.execute(
        select(User.id).where(and_(User.id != exclude_user_id, or_(*slug_conditions))).distinct()
    )
    return [row[0] for row in result.all()]


async def check_design_access(
    design_id: UUID,
    user: User,
    db: AsyncSession,
    require_comment_permission: bool = True,
) -> Design:
    """Check if user has access to the design."""
    from app.models import Project

    # Get design
    result = await db.execute(
        select(Design).where(
            and_(
                Design.id == design_id,
                Design.deleted_at.is_(None),
            )
        )
    )
    design = result.scalar_one_or_none()

    if not design:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Design not found",
        )

    # Check if owner via project
    result = await db.execute(select(Project).where(Project.id == design.project_id))
    project = result.scalar_one_or_none()

    if project and project.user_id == user.id:
        return design

    # Check if design is public
    if design.is_public:
        return design

    # Check if shared with user
    result = await db.execute(
        select(DesignShare).where(
            and_(
                DesignShare.design_id == design_id,
                DesignShare.shared_with_user_id == user.id,
            )
        )
    )
    share = result.scalar_one_or_none()

    if not share:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this design",
        )

    if require_comment_permission and share.permission == "view":  # type: ignore[attr-defined]
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to comment on this design",
        )

    return design


# =============================================================================
# Endpoints
# =============================================================================


@router.post(
    "/designs/{design_id}", response_model=CommentResponse, status_code=status.HTTP_201_CREATED
)
async def create_comment(
    design_id: UUID,
    request: CommentCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CommentResponse:
    """
    Add a comment to a design.

    Supports:
    - Regular text comments
    - Replies (using parent_id)
    - 3D annotations (with position and camera data)
    """
    # Check access and get design
    design = await check_design_access(design_id, current_user, db, require_comment_permission=True)

    # Validate parent if provided
    parent = None
    if request.parent_id:
        parent_key = str(request.parent_id)
        if parent_key not in _comments:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Parent comment not found",
            )
        parent = _comments[parent_key]
        if str(parent["design_id"]) != str(design_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Parent comment belongs to a different design",
            )

    # Create comment
    import uuid

    comment_id = uuid.uuid4()
    now = datetime.now(tz=UTC)

    comment = {
        "id": comment_id,
        "design_id": design_id,
        "author_id": current_user.id,
        "author_email": current_user.email,
        "author_name": current_user.display_name or current_user.email,
        "content": request.content,
        "parent_id": request.parent_id,
        "position": request.position,
        "camera": request.camera,
        "is_edited": False,
        "created_at": now,
        "updated_at": now,
    }

    _comments[str(comment_id)] = comment

    # Count replies
    reply_count = sum(1 for c in _comments.values() if c.get("parent_id") == comment_id)

    # Send notifications
    actor_name = current_user.display_name or current_user.email
    design_name = design.name
    comment_preview = request.content[:200]

    # 1. Parse @mentions and notify mentioned users
    mention_slugs = list(set(MENTION_PATTERN.findall(request.content)))
    mentioned_user_ids = await _resolve_mentions_to_user_ids(db, mention_slugs, current_user.id)
    for recipient_id in mentioned_user_ids:
        await notify_comment_mention(
            db=db,
            recipient_id=recipient_id,
            actor_id=current_user.id,
            actor_name=actor_name,
            design_id=design_id,
            design_name=design_name,
            comment_preview=comment_preview,
        )

    # 2. Notify design owner on new comments (if not the commenter)
    from app.models import Project

    result = await db.execute(select(Project).where(Project.id == design.project_id))
    project = result.scalar_one_or_none()
    if project and project.user_id != current_user.id:
        await notify_comment_added(
            db=db,
            recipient_id=project.user_id,
            actor_id=current_user.id,
            actor_name=actor_name,
            design_id=design_id,
            design_name=design_name,
            comment_preview=comment_preview,
        )

    # 3. Notify thread participants on replies (parent author + other repliers)
    if parent:
        thread_participant_ids = {parent["author_id"]}
        for c in _comments.values():
            if c.get("parent_id") == request.parent_id and c.get("author_id"):
                thread_participant_ids.add(c["author_id"])
        for recipient_id in thread_participant_ids:
            if recipient_id != current_user.id:
                await notify_comment_reply(
                    db=db,
                    recipient_id=recipient_id,
                    actor_id=current_user.id,
                    actor_name=actor_name,
                    design_id=design_id,
                    design_name=design_name,
                    comment_preview=comment_preview,
                )

    return CommentResponse(
        id=comment_id,
        design_id=design_id,
        author=CommentAuthor(
            id=current_user.id,
            display_name=current_user.display_name or current_user.email,
            email=current_user.email,
            avatar_url=None,
        ),
        content=request.content,
        parent_id=request.parent_id,
        position=request.position,
        camera=request.camera,
        reply_count=reply_count,
        is_edited=False,
        created_at=now,
        updated_at=now,
    )


@router.get("/designs/{design_id}", response_model=PaginatedCommentsResponse)
async def list_comments(
    design_id: UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    parent_id: UUID | None = None,  # Filter to get replies
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PaginatedCommentsResponse:
    """
    List comments for a design.

    - Returns top-level comments by default
    - Use parent_id to get replies to a specific comment
    """
    # Check access (view permission is enough to read comments)
    await check_design_access(design_id, current_user, db, require_comment_permission=False)

    # Filter comments
    design_comments = [
        c
        for c in _comments.values()
        if str(c["design_id"]) == str(design_id) and c.get("parent_id") == parent_id
    ]

    # Sort by created_at desc
    design_comments.sort(key=lambda c: c["created_at"], reverse=True)

    # Paginate
    total = len(design_comments)
    offset = (page - 1) * page_size
    page_comments = design_comments[offset : offset + page_size]
    has_more = (offset + page_size) < total

    # Build response
    items = []
    for c in page_comments:
        # Count replies
        reply_count = sum(1 for x in _comments.values() if x.get("parent_id") == c["id"])

        items.append(
            CommentResponse(
                id=c["id"],
                design_id=c["design_id"],
                author=CommentAuthor(
                    id=c["author_id"],
                    display_name=c["author_name"],
                    email=c["author_email"],
                    avatar_url=None,
                ),
                content=c["content"],
                parent_id=c.get("parent_id"),
                position=c.get("position"),
                camera=c.get("camera"),
                reply_count=reply_count,
                is_edited=c.get("is_edited", False),
                created_at=c["created_at"],
                updated_at=c["updated_at"],
            )
        )

    return PaginatedCommentsResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        has_more=has_more,
    )


@router.get("/{comment_id}", response_model=CommentResponse)
async def get_comment(
    comment_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CommentResponse:
    """Get a specific comment."""
    comment_key = str(comment_id)

    if comment_key not in _comments:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Comment not found",
        )

    c = _comments[comment_key]

    # Check access
    await check_design_access(c["design_id"], current_user, db, require_comment_permission=False)

    # Count replies
    reply_count = sum(1 for x in _comments.values() if x.get("parent_id") == c["id"])

    return CommentResponse(
        id=c["id"],
        design_id=c["design_id"],
        author=CommentAuthor(
            id=c["author_id"],
            display_name=c["author_name"],
            email=c["author_email"],
            avatar_url=None,
        ),
        content=c["content"],
        parent_id=c.get("parent_id"),
        position=c.get("position"),
        camera=c.get("camera"),
        reply_count=reply_count,
        is_edited=c.get("is_edited", False),
        created_at=c["created_at"],
        updated_at=c["updated_at"],
    )


@router.patch("/{comment_id}", response_model=CommentResponse)
async def update_comment(
    comment_id: UUID,
    request: CommentUpdate,
    current_user: User = Depends(get_current_user),
    _db: AsyncSession = Depends(get_db),
) -> CommentResponse:
    """Update a comment. Only the author can update their own comments."""
    comment_key = str(comment_id)

    if comment_key not in _comments:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Comment not found",
        )

    c = _comments[comment_key]

    # Check ownership
    if c["author_id"] != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only edit your own comments",
        )

    # Update comment
    c["content"] = request.content
    c["is_edited"] = True
    c["updated_at"] = datetime.now(tz=UTC)

    # Count replies
    reply_count = sum(1 for x in _comments.values() if x.get("parent_id") == c["id"])

    return CommentResponse(
        id=c["id"],
        design_id=c["design_id"],
        author=CommentAuthor(
            id=c["author_id"],
            display_name=c["author_name"],
            email=c["author_email"],
            avatar_url=None,
        ),
        content=c["content"],
        parent_id=c.get("parent_id"),
        position=c.get("position"),
        camera=c.get("camera"),
        reply_count=reply_count,
        is_edited=c.get("is_edited", False),
        created_at=c["created_at"],
        updated_at=c["updated_at"],
    )


@router.delete("/{comment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_comment(
    comment_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """
    Delete a comment.

    Only the comment author or design owner can delete comments.
    """
    comment_key = str(comment_id)

    if comment_key not in _comments:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Comment not found",
        )

    c = _comments[comment_key]

    # Check if author
    if c["author_id"] == current_user.id:
        # Author can delete
        pass
    else:
        # Check if design owner
        from app.models import Project

        result = await db.execute(select(Design).where(Design.id == c["design_id"]))
        design = result.scalar_one_or_none()

        if design:
            result = await db.execute(select(Project).where(Project.id == design.project_id))
            project = result.scalar_one_or_none()

            if not project or project.user_id != current_user.id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You can only delete your own comments or comments on your designs",
                )

    # Delete comment and its replies
    del _comments[comment_key]

    # Also delete all replies
    reply_keys = [k for k, v in _comments.items() if v.get("parent_id") == comment_id]
    for key in reply_keys:
        del _comments[key]


@router.get("/designs/{design_id}/annotations", response_model=list[CommentResponse])
async def list_annotations(
    design_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[CommentResponse]:
    """
    List only 3D annotation comments for a design.

    These are comments with position data that appear on the 3D model.
    """
    # Check access
    await check_design_access(design_id, current_user, db, require_comment_permission=False)

    # Filter to annotations only (comments with position)
    annotations = [
        c
        for c in _comments.values()
        if str(c["design_id"]) == str(design_id) and c.get("position") is not None
    ]

    # Sort by created_at
    annotations.sort(key=lambda c: c["created_at"])

    items = []
    for c in annotations:
        reply_count = sum(1 for x in _comments.values() if x.get("parent_id") == c["id"])

        items.append(
            CommentResponse(
                id=c["id"],
                design_id=c["design_id"],
                author=CommentAuthor(
                    id=c["author_id"],
                    display_name=c["author_name"],
                    email=c["author_email"],
                    avatar_url=None,
                ),
                content=c["content"],
                parent_id=c.get("parent_id"),
                position=c.get("position"),
                camera=c.get("camera"),
                reply_count=reply_count,
                is_edited=c.get("is_edited", False),
                created_at=c["created_at"],
                updated_at=c["updated_at"],
            )
        )

    return items
