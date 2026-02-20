"""
Tests for shares API endpoints.

Tests design sharing functionality.
"""

from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Notification, NotificationPreference
from app.models.notification import NotificationType

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
