"""
Tests for DesignCommentService.

Tests comment creation, threading, updates, deletion (soft/hard),
and moderation for marketplace designs.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import uuid4

import pytest
import pytest_asyncio
from tests.factories import DesignFactory, ProjectFactory, UserFactory

from app.models.rating import DesignComment
from app.schemas.rating import DesignCommentCreate, DesignCommentUpdate
from app.services.design_comment_service import DesignCommentService

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.models.design import Design
    from app.models.user import User


# =============================================================================
# Fixtures
# =============================================================================


@pytest_asyncio.fixture
async def owner(db_session: AsyncSession) -> User:
    """Create a design owner user."""
    return await UserFactory.create(db_session, email="owner@test.com", display_name="Owner")


@pytest_asyncio.fixture
async def commenter(db_session: AsyncSession) -> User:
    """Create a user who posts comments."""
    return await UserFactory.create(
        db_session, email="commenter@test.com", display_name="Commenter"
    )


@pytest_asyncio.fixture
async def commenter_2(db_session: AsyncSession) -> User:
    """Create a second commenter for multi-user tests."""
    return await UserFactory.create(
        db_session, email="commenter2@test.com", display_name="Commenter 2"
    )


@pytest_asyncio.fixture
async def admin_user(db_session: AsyncSession) -> User:
    """Create an admin user for moderation tests."""
    return await UserFactory.create_admin(
        db_session, email="moderator@test.com", display_name="Moderator"
    )


@pytest_asyncio.fixture
async def public_design(db_session: AsyncSession, owner: User) -> Design:
    """Create a public marketplace design."""
    project = await ProjectFactory.create(db_session, user=owner)
    return await DesignFactory.create(
        db_session,
        project=project,
        user=owner,
        is_public=True,
        name="Public Design",
    )


@pytest_asyncio.fixture
async def private_design(db_session: AsyncSession, owner: User) -> Design:
    """Create a private design."""
    project = await ProjectFactory.create(db_session, user=owner)
    return await DesignFactory.create(
        db_session,
        project=project,
        user=owner,
        is_public=False,
        name="Private Design",
    )


@pytest_asyncio.fixture
def comment_service(db_session: AsyncSession) -> DesignCommentService:
    """Create a DesignCommentService instance."""
    return DesignCommentService(db_session)


# =============================================================================
# create_comment Tests
# =============================================================================


class TestCreateComment:
    """Tests for the create_comment method."""

    @pytest.mark.asyncio
    async def test_create_comment_with_valid_data_returns_comment(
        self,
        comment_service: DesignCommentService,
        public_design: Design,
        commenter: User,
    ) -> None:
        """Creating a comment with valid data returns a properly formed response."""
        data = DesignCommentCreate(content="Great design, love this!")

        result = await comment_service.create_comment(
            design_id=public_design.id, user=commenter, data=data
        )

        assert result.design_id == public_design.id
        assert result.user_id == commenter.id
        assert result.content == "Great design, love this!"
        assert result.parent_id is None
        assert result.is_hidden is False
        assert result.is_edited is False
        assert result.reply_count == 0
        assert result.user_name == "Commenter"

    @pytest.mark.asyncio
    async def test_create_reply_to_existing_comment(
        self,
        comment_service: DesignCommentService,
        public_design: Design,
        commenter: User,
        commenter_2: User,
    ) -> None:
        """Creating a reply to an existing comment sets parent_id correctly."""
        # Arrange: create parent comment
        parent = await comment_service.create_comment(
            design_id=public_design.id,
            user=commenter,
            data=DesignCommentCreate(content="First!"),
        )

        # Act: reply to parent
        reply = await comment_service.create_comment(
            design_id=public_design.id,
            user=commenter_2,
            data=DesignCommentCreate(content="Nice point!", parent_id=parent.id),
        )

        # Assert
        assert reply.parent_id == parent.id
        assert reply.content == "Nice point!"
        assert reply.user_name == "Commenter 2"

    @pytest.mark.asyncio
    async def test_create_reply_to_invalid_parent_raises_error(
        self,
        comment_service: DesignCommentService,
        public_design: Design,
        commenter: User,
    ) -> None:
        """Replying to a non-existent parent comment raises ValueError."""
        data = DesignCommentCreate(content="Reply to nothing", parent_id=uuid4())

        with pytest.raises(ValueError, match="Parent comment not found"):
            await comment_service.create_comment(
                design_id=public_design.id, user=commenter, data=data
            )

    @pytest.mark.asyncio
    async def test_create_comment_on_nonexistent_design_raises_error(
        self,
        comment_service: DesignCommentService,
        commenter: User,
    ) -> None:
        """Commenting on a non-existent design raises ValueError."""
        data = DesignCommentCreate(content="Lost comment")

        with pytest.raises(ValueError, match="Design not found or not public"):
            await comment_service.create_comment(design_id=uuid4(), user=commenter, data=data)

    @pytest.mark.asyncio
    async def test_create_comment_on_private_design_raises_error(
        self,
        comment_service: DesignCommentService,
        private_design: Design,
        commenter: User,
    ) -> None:
        """Commenting on a private design raises ValueError."""
        data = DesignCommentCreate(content="Secret comment")

        with pytest.raises(ValueError, match="Design not found or not public"):
            await comment_service.create_comment(
                design_id=private_design.id, user=commenter, data=data
            )


# =============================================================================
# update_comment Tests
# =============================================================================


class TestUpdateComment:
    """Tests for the update_comment method."""

    @pytest.mark.asyncio
    async def test_update_comment_by_owner_succeeds(
        self,
        comment_service: DesignCommentService,
        public_design: Design,
        commenter: User,
    ) -> None:
        """The comment owner can update their own comment."""
        # Arrange
        original = await comment_service.create_comment(
            design_id=public_design.id,
            user=commenter,
            data=DesignCommentCreate(content="Original text"),
        )

        # Act
        updated = await comment_service.update_comment(
            comment_id=original.id,
            user=commenter,
            data=DesignCommentUpdate(content="Updated text"),
        )

        # Assert
        assert updated.content == "Updated text"
        assert updated.is_edited is True
        assert updated.edited_at is not None

    @pytest.mark.asyncio
    async def test_update_comment_by_non_owner_raises_error(
        self,
        comment_service: DesignCommentService,
        public_design: Design,
        commenter: User,
        commenter_2: User,
    ) -> None:
        """A non-owner cannot update someone else's comment."""
        # Arrange: commenter creates comment
        comment = await comment_service.create_comment(
            design_id=public_design.id,
            user=commenter,
            data=DesignCommentCreate(content="My comment"),
        )

        # Act/Assert: commenter_2 tries to edit
        with pytest.raises(ValueError, match="Not authorized to edit this comment"):
            await comment_service.update_comment(
                comment_id=comment.id,
                user=commenter_2,
                data=DesignCommentUpdate(content="Hacked!"),
            )

    @pytest.mark.asyncio
    async def test_update_nonexistent_comment_raises_error(
        self,
        comment_service: DesignCommentService,
        commenter: User,
    ) -> None:
        """Updating a non-existent comment raises ValueError."""
        with pytest.raises(ValueError, match="Comment not found"):
            await comment_service.update_comment(
                comment_id=uuid4(),
                user=commenter,
                data=DesignCommentUpdate(content="Ghost edit"),
            )


# =============================================================================
# delete_comment Tests
# =============================================================================


class TestDeleteComment:
    """Tests for the delete_comment method."""

    @pytest.mark.asyncio
    async def test_delete_comment_without_replies_hard_deletes(
        self,
        comment_service: DesignCommentService,
        public_design: Design,
        commenter: User,
        db_session: AsyncSession,
    ) -> None:
        """Deleting a comment with no replies removes it from the database."""
        # Arrange
        comment = await comment_service.create_comment(
            design_id=public_design.id,
            user=commenter,
            data=DesignCommentCreate(content="Ephemeral thought"),
        )

        # Act
        await comment_service.delete_comment(comment_id=comment.id, user=commenter)

        # Assert: comment is gone from DB
        from sqlalchemy import select

        stmt = select(DesignComment).where(DesignComment.id == comment.id)
        result = await db_session.execute(stmt)
        assert result.scalar_one_or_none() is None

    @pytest.mark.asyncio
    async def test_delete_comment_with_replies_soft_deletes(
        self,
        comment_service: DesignCommentService,
        public_design: Design,
        commenter: User,
        commenter_2: User,
        db_session: AsyncSession,
    ) -> None:
        """Deleting a comment that has replies hides it instead of removing it."""
        # Arrange: create parent and reply
        parent = await comment_service.create_comment(
            design_id=public_design.id,
            user=commenter,
            data=DesignCommentCreate(content="Parent comment"),
        )
        await comment_service.create_comment(
            design_id=public_design.id,
            user=commenter_2,
            data=DesignCommentCreate(content="Reply to parent", parent_id=parent.id),
        )

        # Act: delete parent
        await comment_service.delete_comment(comment_id=parent.id, user=commenter)

        # Assert: parent still exists but is hidden
        from sqlalchemy import select

        stmt = select(DesignComment).where(DesignComment.id == parent.id)
        result = await db_session.execute(stmt)
        hidden_comment = result.scalar_one()
        assert hidden_comment.is_hidden is True
        assert hidden_comment.hidden_reason == "Deleted by user"

    @pytest.mark.asyncio
    async def test_delete_comment_by_non_owner_raises_error(
        self,
        comment_service: DesignCommentService,
        public_design: Design,
        commenter: User,
        commenter_2: User,
    ) -> None:
        """A non-owner cannot delete someone else's comment."""
        comment = await comment_service.create_comment(
            design_id=public_design.id,
            user=commenter,
            data=DesignCommentCreate(content="My comment"),
        )

        with pytest.raises(ValueError, match="Not authorized to delete this comment"):
            await comment_service.delete_comment(comment_id=comment.id, user=commenter_2)

    @pytest.mark.asyncio
    async def test_delete_nonexistent_comment_raises_error(
        self,
        comment_service: DesignCommentService,
        commenter: User,
    ) -> None:
        """Deleting a non-existent comment raises ValueError."""
        with pytest.raises(ValueError, match="Comment not found"):
            await comment_service.delete_comment(comment_id=uuid4(), user=commenter)


# =============================================================================
# get_design_comments Tests
# =============================================================================


class TestGetDesignComments:
    """Tests for the get_design_comments method."""

    @pytest.mark.asyncio
    async def test_get_design_comments_returns_threads(
        self,
        comment_service: DesignCommentService,
        public_design: Design,
        commenter: User,
        commenter_2: User,
    ) -> None:
        """Returns threaded comments with replies nested under parents."""
        # Arrange: create parent + reply
        parent = await comment_service.create_comment(
            design_id=public_design.id,
            user=commenter,
            data=DesignCommentCreate(content="Top-level comment"),
        )
        await comment_service.create_comment(
            design_id=public_design.id,
            user=commenter_2,
            data=DesignCommentCreate(content="Reply!", parent_id=parent.id),
        )

        # Act
        threads, total = await comment_service.get_design_comments(public_design.id)

        # Assert: 1 top-level thread, with 1 reply inside
        assert total == 1
        assert len(threads) == 1
        assert threads[0].content == "Top-level comment"
        assert threads[0].reply_count == 1
        assert len(threads[0].replies) == 1
        assert threads[0].replies[0].content == "Reply!"

    @pytest.mark.asyncio
    async def test_get_design_comments_empty_returns_empty(
        self,
        comment_service: DesignCommentService,
        public_design: Design,
    ) -> None:
        """Design with no comments returns empty list."""
        threads, total = await comment_service.get_design_comments(public_design.id)
        assert total == 0
        assert threads == []

    @pytest.mark.asyncio
    async def test_get_design_comments_hidden_content_masked(
        self,
        comment_service: DesignCommentService,
        public_design: Design,
        commenter: User,
        commenter_2: User,
        admin_user: User,
    ) -> None:
        """Hidden comments show '[hidden]' instead of their content."""
        # Arrange: create and hide a comment
        comment = await comment_service.create_comment(
            design_id=public_design.id,
            user=commenter,
            data=DesignCommentCreate(content="Offensive content"),
        )
        # Create a reply so the parent will still appear (soft-deleted)
        await comment_service.create_comment(
            design_id=public_design.id,
            user=commenter_2,
            data=DesignCommentCreate(content="Reply", parent_id=comment.id),
        )
        await comment_service.moderate_comment(comment.id, admin_user, "hide", "Offensive")

        # Act
        threads, total = await comment_service.get_design_comments(public_design.id)

        # Assert: hidden comment's content is masked
        assert total == 1
        assert threads[0].content == "[hidden]"
        assert threads[0].is_hidden is True


# =============================================================================
# moderate_comment Tests
# =============================================================================


class TestModerateComment:
    """Tests for the moderate_comment method."""

    @pytest.mark.asyncio
    async def test_moderate_comment_hide_succeeds(
        self,
        comment_service: DesignCommentService,
        public_design: Design,
        commenter: User,
        admin_user: User,
    ) -> None:
        """Admin can hide a comment via moderation."""
        comment = await comment_service.create_comment(
            design_id=public_design.id,
            user=commenter,
            data=DesignCommentCreate(content="Bad content"),
        )

        result = await comment_service.moderate_comment(
            comment_id=comment.id,
            admin_user=admin_user,
            action="hide",
            reason="Violates TOS",
        )

        assert result.is_hidden is True

    @pytest.mark.asyncio
    async def test_moderate_comment_unhide_succeeds(
        self,
        comment_service: DesignCommentService,
        public_design: Design,
        commenter: User,
        admin_user: User,
    ) -> None:
        """Admin can unhide a previously hidden comment."""
        # Arrange: create and hide
        comment = await comment_service.create_comment(
            design_id=public_design.id,
            user=commenter,
            data=DesignCommentCreate(content="Flagged wrongly"),
        )
        await comment_service.moderate_comment(comment.id, admin_user, "hide")

        # Act: unhide
        result = await comment_service.moderate_comment(comment.id, admin_user, "unhide")

        # Assert
        assert result.is_hidden is False

    @pytest.mark.asyncio
    async def test_moderate_comment_invalid_action_raises_error(
        self,
        comment_service: DesignCommentService,
        public_design: Design,
        commenter: User,
        admin_user: User,
    ) -> None:
        """An invalid moderation action raises ValueError."""
        comment = await comment_service.create_comment(
            design_id=public_design.id,
            user=commenter,
            data=DesignCommentCreate(content="Something"),
        )

        with pytest.raises(ValueError, match="Invalid moderation action"):
            await comment_service.moderate_comment(comment.id, admin_user, "ban")

    @pytest.mark.asyncio
    async def test_moderate_nonexistent_comment_raises_error(
        self,
        comment_service: DesignCommentService,
        admin_user: User,
    ) -> None:
        """Moderating a non-existent comment raises ValueError."""
        with pytest.raises(ValueError, match="Comment not found"):
            await comment_service.moderate_comment(uuid4(), admin_user, "hide")
