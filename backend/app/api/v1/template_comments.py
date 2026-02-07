"""
API routes for template comments.

Handles CRUD operations for template comments with threading support.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db, get_optional_user
from app.models.user import User
from app.schemas.rating import (
    CommentCreate,
    CommentModerationAction,
    CommentResponse,
    CommentUpdate,
    CommentUserInfo,
)
from app.services.rating_service import CommentService

router = APIRouter(prefix="/templates/{template_id}/comments", tags=["template-comments"])


# =============================================================================
# Comment CRUD
# =============================================================================


@router.post(
    "",
    response_model=CommentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_template_comment(
    template_id: UUID,
    data: CommentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CommentResponse:
    """Create a new comment on a template.

    Supports threaded replies via parent_id.
    """
    service = CommentService(db)
    comment = await service.create_comment(template_id, current_user.id, data)
    await db.commit()

    return CommentResponse(
        id=comment.id,
        template_id=comment.template_id,
        user_id=comment.user_id,
        parent_id=comment.parent_id,
        content=comment.content,
        is_hidden=comment.is_hidden,
        is_edited=comment.is_edited,
        edited_at=comment.edited_at,
        created_at=comment.created_at,
        updated_at=comment.updated_at,
        user=CommentUserInfo(
            id=current_user.id,
            display_name=current_user.display_name,
        ),
        reply_count=0,
    )


@router.get(
    "",
    response_model=list[CommentResponse],
)
async def get_template_comments(
    template_id: UUID,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    current_user: User | None = Depends(get_optional_user),
) -> list[CommentResponse]:
    """Get comments for a template.

    Returns top-level comments with reply counts.
    Hidden comments are excluded unless user is admin.
    """
    is_admin = bool(current_user and current_user.is_admin)
    service = CommentService(db)
    comments, _ = await service.get_template_comments(
        template_id,
        include_hidden=is_admin,
        limit=limit,
        offset=offset,
    )

    result = []
    for comment in comments:
        reply_count = await service.get_reply_count(comment.id)
        result.append(
            CommentResponse(
                id=comment.id,
                template_id=comment.template_id,
                user_id=comment.user_id,
                parent_id=comment.parent_id,
                content=comment.content,
                is_hidden=comment.is_hidden,
                is_edited=comment.is_edited,
                edited_at=comment.edited_at,
                created_at=comment.created_at,
                updated_at=comment.updated_at,
                user=CommentUserInfo(
                    id=comment.user.id,
                    display_name=comment.user.display_name,
                )
                if comment.user
                else None,
                reply_count=reply_count,
            )
        )

    return result


@router.get(
    "/{comment_id}/replies",
    response_model=list[CommentResponse],
)
async def get_template_comment_replies(
    _template_id: UUID,
    comment_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User | None = Depends(get_optional_user),
) -> list[CommentResponse]:
    """Get replies to a specific comment."""
    is_admin = bool(current_user and current_user.is_admin)
    service = CommentService(db)
    replies = await service.get_comment_replies(comment_id, include_hidden=is_admin)

    result = []
    for reply in replies:
        reply_count = await service.get_reply_count(reply.id)
        result.append(
            CommentResponse(
                id=reply.id,
                template_id=reply.template_id,
                user_id=reply.user_id,
                parent_id=reply.parent_id,
                content=reply.content,
                is_hidden=reply.is_hidden,
                is_edited=reply.is_edited,
                edited_at=reply.edited_at,
                created_at=reply.created_at,
                updated_at=reply.updated_at,
                user=CommentUserInfo(
                    id=reply.user.id,
                    display_name=reply.user.display_name,
                )
                if reply.user
                else None,
                reply_count=reply_count,
            )
        )

    return result


@router.patch(
    "/{comment_id}",
    response_model=CommentResponse,
)
async def update_template_comment(
    _template_id: UUID,
    comment_id: UUID,
    data: CommentUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CommentResponse:
    """Update a comment.

    Users can only update their own comments.
    """
    service = CommentService(db)
    comment = await service.update_comment(comment_id, current_user.id, data)

    if not comment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Comment not found or you don't have permission to edit it",
        )

    await db.commit()

    reply_count = await service.get_reply_count(comment.id)
    return CommentResponse(
        id=comment.id,
        template_id=comment.template_id,
        user_id=comment.user_id,
        parent_id=comment.parent_id,
        content=comment.content,
        is_hidden=comment.is_hidden,
        is_edited=comment.is_edited,
        edited_at=comment.edited_at,
        created_at=comment.created_at,
        updated_at=comment.updated_at,
        user=CommentUserInfo(
            id=current_user.id,
            display_name=current_user.display_name,
        ),
        reply_count=reply_count,
    )


@router.delete(
    "/{comment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_template_comment(
    _template_id: UUID,
    comment_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    """Delete a comment.

    Users can delete their own comments. Admins can delete any comment.
    """
    service = CommentService(db)
    deleted = await service.delete_comment(
        comment_id,
        current_user.id,
        is_admin=current_user.is_admin,
    )

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Comment not found or you don't have permission to delete it",
        )

    await db.commit()


# =============================================================================
# Comment Moderation (Admin Only)
# =============================================================================


@router.post(
    "/{comment_id}/moderate",
    response_model=CommentResponse,
)
async def moderate_template_comment(
    _template_id: UUID,
    comment_id: UUID,
    data: CommentModerationAction,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CommentResponse:
    """Moderate a comment (admin only).

    Actions: hide, unhide, delete
    """
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )

    service = CommentService(db)

    if data.action == "hide":
        comment = await service.hide_comment(comment_id, current_user.id, data.reason)
    elif data.action == "unhide":
        comment = await service.unhide_comment(comment_id)
    elif data.action == "delete":
        deleted = await service.delete_comment(comment_id, current_user.id, is_admin=True)
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Comment not found",
            )
        await db.commit()
        # Return empty response for delete
        raise HTTPException(status_code=status.HTTP_204_NO_CONTENT)
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown action: {data.action}",
        )

    if not comment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Comment not found",
        )

    await db.commit()

    reply_count = await service.get_reply_count(comment.id)
    return CommentResponse(
        id=comment.id,
        template_id=comment.template_id,
        user_id=comment.user_id,
        parent_id=comment.parent_id,
        content=comment.content,
        is_hidden=comment.is_hidden,
        is_edited=comment.is_edited,
        edited_at=comment.edited_at,
        created_at=comment.created_at,
        updated_at=comment.updated_at,
        reply_count=reply_count,
    )
