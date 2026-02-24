"""
Tests for comment notification integration.

Verifies that commenting on designs creates the correct notifications
for design owners, mentioned users, and thread participants.
"""

from uuid import uuid4

import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.comments import _comments
from app.models.design import Design
from app.models.notification import (
    Notification,
    NotificationPreference,
    NotificationType,
)
from app.models.project import Project


# =============================================================================
# Fixtures
# =============================================================================


@pytest_asyncio.fixture(autouse=True)
async def _clear_comments():
    """Clear in-memory comments store before and after each test."""
    _comments.clear()
    yield
    _comments.clear()


@pytest_asyncio.fixture
async def owner_design(
    db_session: AsyncSession,
    test_user,
) -> Design:
    """Create a public design owned by test_user.

    Public so that test_user_2 can access and comment on it.
    """
    project = Project(
        id=uuid4(),
        user_id=test_user.id,
        name="Owner Notification Project",
    )
    db_session.add(project)
    await db_session.flush()

    design = Design(
        id=uuid4(),
        project_id=project.id,
        user_id=test_user.id,
        name="Notification Test Design",
        source_type="ai_generated",
        status="completed",
        is_public=True,
    )
    db_session.add(design)
    await db_session.commit()
    await db_session.refresh(design)
    return design


async def _get_notifications_for_user(
    db: AsyncSession,
    user_id,
    notification_type: NotificationType | None = None,
) -> list[Notification]:
    """Query persisted notifications for a user, optionally filtered by type."""
    conditions = [Notification.user_id == user_id]
    if notification_type:
        conditions.append(Notification.type == notification_type)
    result = await db.execute(
        select(Notification).where(*conditions).order_by(Notification.created_at.desc())
    )
    return list(result.scalars().all())


# =============================================================================
# Notification Tests
# =============================================================================


class TestCommentNotifications:
    """Tests verifying notifications created by comment actions."""

    async def test_comment_notifies_design_owner(
        self,
        client: AsyncClient,
        auth_headers_2: dict,
        db_session: AsyncSession,
        test_user,
        test_user_2,
        owner_design: Design,
    ) -> None:
        """Creating a comment on someone else's design notifies the owner.

        Arrange: test_user owns the design; test_user_2 is the commenter.
        Act: test_user_2 posts a comment.
        Assert: A COMMENT_ADDED notification exists for test_user.
        """
        response = await client.post(
            f"/api/v1/comments/designs/{owner_design.id}",
            headers=auth_headers_2,
            json={"content": "Great design!"},
        )
        assert response.status_code == 201, response.text

        notifications = await _get_notifications_for_user(
            db_session, test_user.id, NotificationType.COMMENT_ADDED
        )
        assert len(notifications) == 1
        notif = notifications[0]
        assert notif.title == "New comment on your design"
        assert "Great design!" in notif.message

    async def test_comment_does_not_notify_self(
        self,
        client: AsyncClient,
        auth_headers: dict,
        db_session: AsyncSession,
        test_user,
        owner_design: Design,
    ) -> None:
        """Commenting on your own design should NOT create a COMMENT_ADDED notification.

        Arrange: test_user owns the design and is the commenter.
        Act: test_user posts a comment on their own design.
        Assert: No COMMENT_ADDED notification exists for test_user.
        """
        response = await client.post(
            f"/api/v1/comments/designs/{owner_design.id}",
            headers=auth_headers,
            json={"content": "Talking to myself"},
        )
        assert response.status_code == 201, response.text

        notifications = await _get_notifications_for_user(
            db_session, test_user.id, NotificationType.COMMENT_ADDED
        )
        assert len(notifications) == 0

    async def test_comment_mention_creates_notification(
        self,
        client: AsyncClient,
        auth_headers: dict,
        db_session: AsyncSession,
        test_user,
        test_user_2,
        owner_design: Design,
    ) -> None:
        """An @mention in a comment creates a COMMENT_MENTION notification.

        Arrange: test_user_2 has display_name "Test User 2".
        Act: test_user posts a comment with @TestUser2.
        Assert: A COMMENT_MENTION notification exists for test_user_2.
        """
        response = await client.post(
            f"/api/v1/comments/designs/{owner_design.id}",
            headers=auth_headers,
            json={"content": "Hey @TestUser2 check this out"},
        )
        assert response.status_code == 201, response.text

        notifications = await _get_notifications_for_user(
            db_session, test_user_2.id, NotificationType.COMMENT_MENTION
        )
        assert len(notifications) == 1
        notif = notifications[0]
        assert notif.title == "You were mentioned"
        assert "TestUser2" in notif.message or "check this out" in notif.message

    async def test_comment_reply_notifies_thread_participants(
        self,
        client: AsyncClient,
        auth_headers: dict,
        auth_headers_2: dict,
        db_session: AsyncSession,
        test_user,
        test_user_2,
        owner_design: Design,
    ) -> None:
        """Replying to a comment notifies the original comment author.

        Arrange: test_user_2 creates a top-level comment (parent).
        Act: test_user replies to that comment.
        Assert: A COMMENT_REPLY notification exists for test_user_2.
        """
        # test_user_2 creates parent comment
        parent_resp = await client.post(
            f"/api/v1/comments/designs/{owner_design.id}",
            headers=auth_headers_2,
            json={"content": "Initial comment"},
        )
        assert parent_resp.status_code == 201, parent_resp.text
        parent_id = parent_resp.json()["id"]

        # test_user replies to the parent comment
        reply_resp = await client.post(
            f"/api/v1/comments/designs/{owner_design.id}",
            headers=auth_headers,
            json={"content": "Thanks for the feedback!", "parent_id": parent_id},
        )
        assert reply_resp.status_code == 201, reply_resp.text

        notifications = await _get_notifications_for_user(
            db_session, test_user_2.id, NotificationType.COMMENT_REPLY
        )
        assert len(notifications) == 1
        notif = notifications[0]
        assert notif.title == "New reply to comment"
        assert "Thanks for the feedback!" in notif.message

    async def test_comment_notification_contains_preview(
        self,
        client: AsyncClient,
        auth_headers_2: dict,
        db_session: AsyncSession,
        test_user,
        test_user_2,
        owner_design: Design,
    ) -> None:
        """Notification message includes a preview of the comment text.

        Arrange: test_user owns the design.
        Act: test_user_2 posts a lengthy comment.
        Assert: The notification message contains the first part of the comment.
        """
        long_text = "A" * 150
        response = await client.post(
            f"/api/v1/comments/designs/{owner_design.id}",
            headers=auth_headers_2,
            json={"content": long_text},
        )
        assert response.status_code == 201, response.text

        notifications = await _get_notifications_for_user(
            db_session, test_user.id, NotificationType.COMMENT_ADDED
        )
        assert len(notifications) == 1
        notif = notifications[0]
        # The helper truncates preview to 100 chars and appends "..."
        assert "A" * 100 in notif.message
        assert "..." in notif.message

    async def test_comment_notification_respects_preferences(
        self,
        client: AsyncClient,
        auth_headers: dict,
        db_session: AsyncSession,
        test_user,
        test_user_2,
        owner_design: Design,
    ) -> None:
        """No notification is created when user disables in-app for the type.

        Arrange: test_user_2 disables in_app for COMMENT_MENTION.
        Act: test_user posts a comment mentioning test_user_2.
        Assert: No COMMENT_MENTION notification exists for test_user_2.
        """
        # Disable in-app notifications for COMMENT_MENTION
        pref = NotificationPreference(
            user_id=test_user_2.id,
            notification_type=NotificationType.COMMENT_MENTION,
            in_app_enabled=False,
            email_enabled=False,
        )
        db_session.add(pref)
        await db_session.commit()

        response = await client.post(
            f"/api/v1/comments/designs/{owner_design.id}",
            headers=auth_headers,
            json={"content": "Hey @TestUser2 look at this"},
        )
        assert response.status_code == 201, response.text

        notifications = await _get_notifications_for_user(
            db_session, test_user_2.id, NotificationType.COMMENT_MENTION
        )
        assert len(notifications) == 0
