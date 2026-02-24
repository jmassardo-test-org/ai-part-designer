"""
Tests for shares API endpoints.

Tests design sharing functionality.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Notification, NotificationPreference
from app.models.notification import NotificationType

if TYPE_CHECKING:
    from app.models.project import Project
    from app.models.user import User

# =============================================================================
# Share Design Notification Tests
# =============================================================================


class TestShareDesignNotifications:
    """Tests for notification triggers when sharing designs."""

    @pytest.mark.asyncio
    async def test_share_design_sends_notification(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_user,
        test_user_2,
        test_project,
        design_factory,
        auth_headers,
    ):
        """Sharing a design with a user should create a notification for the recipient."""
        # Create design owned by test_user in personal project (no org = feature check skipped)
        design = await design_factory.create(db_session, project=test_project, name="Shared Design")

        response = await client.post(
            f"/api/v1/shares/designs/{design.id}",
            json={"email": test_user_2.email, "permission": "view"},
            headers=auth_headers,
        )

        assert response.status_code == 201

        # Verify notification was created for recipient
        result = await db_session.execute(
            select(Notification).where(
                Notification.user_id == test_user_2.id,
                Notification.type == NotificationType.DESIGN_SHARED,
            )
        )
        notifications = result.scalars().all()
        assert len(notifications) == 1
        assert "Shared Design" in notifications[0].message
        assert str(test_user.display_name or test_user.email) in notifications[0].message

    @pytest.mark.asyncio
    async def test_share_respects_preferences(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_user,
        test_user_2,
        test_project,
        design_factory,
        auth_headers,
    ):
        """When recipient has disabled design_shared notifications, no notification is created."""
        # Disable in-app notifications for design_shared for test_user_2
        pref = NotificationPreference(
            user_id=test_user_2.id,
            notification_type=NotificationType.DESIGN_SHARED,
            in_app_enabled=False,
            email_enabled=False,
        )
        db_session.add(pref)
        await db_session.commit()

        design = await design_factory.create(db_session, project=test_project, name="Quiet Share")

        response = await client.post(
            f"/api/v1/shares/designs/{design.id}",
            json={"email": test_user_2.email, "permission": "view"},
            headers=auth_headers,
        )

        assert response.status_code == 201

        # Verify NO notification was created (user disabled this type)
        result = await db_session.execute(
            select(Notification).where(
                Notification.user_id == test_user_2.id,
                Notification.type == NotificationType.DESIGN_SHARED,
            )
        )
        notifications = result.scalars().all()
        assert len(notifications) == 0

    @pytest.mark.asyncio
    async def test_share_permission_change_creates_notification(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_user: "User",
        test_user_2: "User",
        test_project: "Project",
        design_factory,
        auth_headers: dict[str, str],
    ) -> None:
        """Updating a share's permission should create a SHARE_PERMISSION_CHANGED notification."""
        # Arrange — create design and initial share
        design = await design_factory.create(
            db_session, project=test_project, name="Permission Test"
        )

        initial_response = await client.post(
            f"/api/v1/shares/designs/{design.id}",
            json={"email": test_user_2.email, "permission": "view"},
            headers=auth_headers,
        )
        assert initial_response.status_code == 201

        # Act — re-share with a different permission (triggers permission change path)
        update_response = await client.post(
            f"/api/v1/shares/designs/{design.id}",
            json={"email": test_user_2.email, "permission": "edit"},
            headers=auth_headers,
        )
        assert update_response.status_code == 201

        # Assert — a SHARE_PERMISSION_CHANGED notification exists for the recipient
        result = await db_session.execute(
            select(Notification).where(
                Notification.user_id == test_user_2.id,
                Notification.type == NotificationType.SHARE_PERMISSION_CHANGED,
            )
        )
        notifications = result.scalars().all()
        assert len(notifications) == 1
        assert "edit" in notifications[0].message
        assert "Permission Test" in notifications[0].message

    @pytest.mark.asyncio
    async def test_share_notification_contains_correct_data(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_user: "User",
        test_user_2: "User",
        test_project: "Project",
        design_factory,
        auth_headers: dict[str, str],
    ) -> None:
        """Notification data should contain action_url, actor info, and design name."""
        # Arrange
        design = await design_factory.create(
            db_session, project=test_project, name="Data Check Design"
        )

        # Act
        response = await client.post(
            f"/api/v1/shares/designs/{design.id}",
            json={"email": test_user_2.email, "permission": "comment"},
            headers=auth_headers,
        )
        assert response.status_code == 201

        # Assert — verify the notification data JSONB payload
        result = await db_session.execute(
            select(Notification).where(
                Notification.user_id == test_user_2.id,
                Notification.type == NotificationType.DESIGN_SHARED,
            )
        )
        notification = result.scalars().first()
        assert notification is not None

        # Title and message correctness
        assert notification.title == "Design shared with you"
        assert "Data Check Design" in notification.message
        assert "comment" in notification.message

        # Data payload should contain extended fields
        data = notification.data
        assert data is not None
        assert data["action_url"] == f"/designs/{design.id}"
        assert data["action_label"] == "View Design"
        assert data["actor_id"] == str(test_user.id)
        assert data["entity_type"] == "design"
        assert data["entity_id"] == str(design.id)
        assert data["permission"] == "comment"


# =============================================================================
# List Shares Tests
# =============================================================================


class TestListShares:
    """Tests for GET /api/v1/shares/designs/{design_id}."""

    async def test_list_shares_for_nonexistent_design(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Should return 404 for non-existent design."""
        fake_id = uuid4()
        response = await client.get(f"/api/v1/shares/designs/{fake_id}", headers=auth_headers)

        # Should return 404 for non-existent design
        assert response.status_code == 404

    async def test_list_shares_unauthenticated(self, client: AsyncClient):
        """Should return 401 without authentication."""
        fake_id = uuid4()
        response = await client.get(f"/api/v1/shares/designs/{fake_id}")

        assert response.status_code == 401


# =============================================================================
# Shared With Me Tests
# =============================================================================


class TestSharedWithMe:
    """Tests for GET /api/v1/shares/shared-with-me."""

    async def test_shared_with_me_success(self, client: AsyncClient, auth_headers: dict):
        """Should return designs shared with current user."""
        response = await client.get("/api/v1/shares/shared-with-me", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert "items" in data or isinstance(data, list)
