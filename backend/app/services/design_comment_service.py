"""Design comment service for marketplace comment operations.

Provides business logic for creating, updating, deleting, and
querying design comments with threading support.
"""

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.design import Design
from app.models.rating import DesignComment
from app.models.user import User
from app.schemas.rating import (
    DesignCommentCreate,
    DesignCommentResponse,
    DesignCommentThread,
    DesignCommentUpdate,
)


class DesignCommentService:
    """Service for managing design comments.

    Handles creation, updates, deletion, and threaded retrieval
    of design comments.
    """

    def __init__(self, db: AsyncSession) -> None:
        """Initialize the service.

        Args:
            db: Async database session.
        """
        self.db = db

    async def create_comment(
        self,
        design_id: UUID,
        user: User,
        data: DesignCommentCreate,
    ) -> DesignCommentResponse:
        """Create a new comment on a design.

        Args:
            design_id: The design to comment on.
            user: The authenticated user.
            data: Comment data (content + optional parent_id for threading).

        Returns:
            The created comment.

        Raises:
            ValueError: If design not found or parent comment invalid.
        """
        # Validate design exists and is public
        design = await self.db.get(Design, design_id)
        if not design or not design.is_public or design.deleted_at is not None:
            raise ValueError("Design not found or not public")

        # Validate parent if threading
        if data.parent_id:
            parent = await self.db.get(DesignComment, data.parent_id)
            if not parent or parent.design_id != design_id:
                raise ValueError("Parent comment not found on this design")

        comment = DesignComment(
            design_id=design_id,
            user_id=user.id,
            content=data.content,
            parent_id=data.parent_id,
        )
        self.db.add(comment)
        await self.db.commit()
        await self.db.refresh(comment)

        return DesignCommentResponse(
            id=comment.id,
            design_id=comment.design_id,
            user_id=comment.user_id,
            parent_id=comment.parent_id,
            content=comment.content,
            is_hidden=comment.is_hidden,
            is_edited=comment.is_edited,
            edited_at=comment.edited_at,
            created_at=comment.created_at,
            updated_at=comment.updated_at,
            user_name=user.display_name or "Anonymous",
            reply_count=0,
        )

    async def update_comment(
        self,
        comment_id: UUID,
        user: User,
        data: DesignCommentUpdate,
    ) -> DesignCommentResponse:
        """Update an existing comment.

        Args:
            comment_id: The comment to update.
            user: The authenticated user (must be comment owner).
            data: Updated content.

        Returns:
            The updated comment.

        Raises:
            ValueError: If comment not found or user not owner.
        """
        comment = await self.db.get(DesignComment, comment_id)
        if not comment:
            raise ValueError("Comment not found")
        if comment.user_id != user.id:
            raise ValueError("Not authorized to edit this comment")

        comment.content = data.content
        comment.is_edited = True
        comment.edited_at = datetime.now(timezone.utc)
        comment.updated_at = datetime.now(timezone.utc)

        await self.db.commit()
        await self.db.refresh(comment)

        return DesignCommentResponse(
            id=comment.id,
            design_id=comment.design_id,
            user_id=comment.user_id,
            parent_id=comment.parent_id,
            content=comment.content,
            is_hidden=comment.is_hidden,
            is_edited=comment.is_edited,
            edited_at=comment.edited_at,
            created_at=comment.created_at,
            updated_at=comment.updated_at,
            user_name=user.display_name or "Anonymous",
        )

    async def delete_comment(self, comment_id: UUID, user: User) -> None:
        """Delete a comment (soft-delete by hiding if has replies, hard-delete otherwise).

        Args:
            comment_id: The comment to delete.
            user: The authenticated user (must be comment owner or admin).

        Raises:
            ValueError: If comment not found or not authorized.
        """
        comment = await self.db.get(DesignComment, comment_id)
        if not comment:
            raise ValueError("Comment not found")
        if comment.user_id != user.id and not getattr(user, "is_admin", False):
            raise ValueError("Not authorized to delete this comment")

        # Check for replies
        reply_count_stmt = (
            select(func.count())
            .select_from(DesignComment)
            .where(DesignComment.parent_id == comment_id)
        )
        reply_count = (await self.db.execute(reply_count_stmt)).scalar() or 0

        if reply_count > 0:
            # Soft-delete: hide the comment but keep for thread context
            comment.is_hidden = True
            comment.hidden_at = datetime.now(timezone.utc)
            comment.hidden_by_id = user.id
            comment.hidden_reason = "Deleted by user"
        else:
            await self.db.delete(comment)

        await self.db.commit()

    async def get_design_comments(
        self,
        design_id: UUID,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[DesignCommentThread], int]:
        """Get threaded comments for a design.

        Returns top-level comments with nested replies.

        Args:
            design_id: The design to get comments for.
            page: Page number (1-based).
            page_size: Items per page.

        Returns:
            Tuple of (comment threads, total top-level count).
        """
        # Count top-level comments
        count_stmt = (
            select(func.count())
            .select_from(DesignComment)
            .where(
                DesignComment.design_id == design_id,
                DesignComment.parent_id.is_(None),
            )
        )
        total = (await self.db.execute(count_stmt)).scalar() or 0

        # Fetch top-level comments with user info
        stmt = (
            select(DesignComment, User.display_name)
            .join(User, DesignComment.user_id == User.id)
            .where(
                DesignComment.design_id == design_id,
                DesignComment.parent_id.is_(None),
            )
            .order_by(DesignComment.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await self.db.execute(stmt)
        top_level = result.all()

        threads = []
        for comment, user_name in top_level:
            # Get reply count
            reply_count_stmt = (
                select(func.count())
                .select_from(DesignComment)
                .where(DesignComment.parent_id == comment.id)
            )
            reply_count = (await self.db.execute(reply_count_stmt)).scalar() or 0

            # Get replies
            replies_stmt = (
                select(DesignComment, User.display_name)
                .join(User, DesignComment.user_id == User.id)
                .where(DesignComment.parent_id == comment.id)
                .order_by(DesignComment.created_at.asc())
            )
            replies_result = await self.db.execute(replies_stmt)
            replies_rows = replies_result.all()

            reply_threads = []
            for reply, reply_user_name in replies_rows:
                reply_threads.append(
                    DesignCommentThread(
                        id=reply.id,
                        design_id=reply.design_id,
                        user_id=reply.user_id,
                        parent_id=reply.parent_id,
                        content="[hidden]" if reply.is_hidden else reply.content,
                        is_hidden=reply.is_hidden,
                        is_edited=reply.is_edited,
                        edited_at=reply.edited_at,
                        created_at=reply.created_at,
                        updated_at=reply.updated_at,
                        user_name=reply_user_name or "Anonymous",
                        reply_count=0,
                        replies=[],
                    )
                )

            threads.append(
                DesignCommentThread(
                    id=comment.id,
                    design_id=comment.design_id,
                    user_id=comment.user_id,
                    parent_id=comment.parent_id,
                    content="[hidden]" if comment.is_hidden else comment.content,
                    is_hidden=comment.is_hidden,
                    is_edited=comment.is_edited,
                    edited_at=comment.edited_at,
                    created_at=comment.created_at,
                    updated_at=comment.updated_at,
                    user_name=user_name or "Anonymous",
                    reply_count=reply_count,
                    replies=reply_threads,
                )
            )

        return threads, total

    async def moderate_comment(
        self,
        comment_id: UUID,
        admin_user: User,
        action: str,
        reason: str | None = None,
    ) -> DesignCommentResponse:
        """Moderate a comment (admin action).

        Args:
            comment_id: The comment to moderate.
            admin_user: The admin performing the action.
            action: "hide" or "unhide".
            reason: Reason for moderation.

        Returns:
            The updated comment.

        Raises:
            ValueError: If comment not found or invalid action.
        """
        comment = await self.db.get(DesignComment, comment_id)
        if not comment:
            raise ValueError("Comment not found")

        if action == "hide":
            comment.is_hidden = True
            comment.hidden_by_id = admin_user.id
            comment.hidden_at = datetime.now(timezone.utc)
            comment.hidden_reason = reason
        elif action == "unhide":
            comment.is_hidden = False
            comment.hidden_by_id = None
            comment.hidden_at = None
            comment.hidden_reason = None
        else:
            raise ValueError(f"Invalid moderation action: {action}")

        await self.db.commit()
        await self.db.refresh(comment)

        return DesignCommentResponse(
            id=comment.id,
            design_id=comment.design_id,
            user_id=comment.user_id,
            parent_id=comment.parent_id,
            content=comment.content,
            is_hidden=comment.is_hidden,
            is_edited=comment.is_edited,
            edited_at=comment.edited_at,
            created_at=comment.created_at,
            updated_at=comment.updated_at,
        )
