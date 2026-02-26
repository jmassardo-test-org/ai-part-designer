"""
Tests for organization invite notification wiring.

Verifies that inviting a user to an organization creates the correct
in-app notification with proper type, priority, and data fields.
"""

from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification import Notification, NotificationPriority, NotificationType
from app.models.organization import Organization, OrganizationMember, OrganizationRole

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
async def invite_org(db_session: AsyncSession, test_user) -> Organization:
    """Create an organization owned by test_user for invite tests."""
    org = Organization(
        id=uuid4(),
        name="Invite Test Org",
        slug=f"invite-org-{uuid4().hex[:8]}",
        owner_id=test_user.id,
        settings={
            "allow_member_invites": False,
            "default_project_visibility": "private",
            "require_2fa": False,
            "allowed_domains": [],
        },
    )
    db_session.add(org)

    member = OrganizationMember(
        id=uuid4(),
        organization_id=org.id,
        user_id=test_user.id,
        role=OrganizationRole.OWNER,
    )
    db_session.add(member)
    await db_session.commit()
    await db_session.refresh(org)
    return org


# =============================================================================
# Invite Notification Tests
# =============================================================================


class TestOrgInviteNotifications:
    """Tests for notification creation when inviting users to organizations."""

    @pytest.mark.asyncio
    async def test_org_invite_creates_notification_for_existing_user(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_user,
        test_user_2,
        invite_org: Organization,
        auth_headers: dict[str, str],
    ) -> None:
        """Inviting an existing user should create an ORG_INVITE notification.

        Arranges an org owned by test_user, then invites test_user_2.
        Asserts a single ORG_INVITE notification is created for the invitee
        with the correct org name and role in the message.
        """
        # Arrange — org already created via fixture

        # Act
        response = await client.post(
            f"/api/v1/organizations/{invite_org.id}/invites",
            json={"email": test_user_2.email, "role": "member"},
            headers=auth_headers,
        )

        # Assert — invite succeeded
        assert response.status_code == 201

        # Assert — notification created
        result = await db_session.execute(
            select(Notification).where(
                Notification.user_id == test_user_2.id,
                Notification.type == NotificationType.ORG_INVITE,
            )
        )
        notifications = result.scalars().all()

        assert len(notifications) == 1
        notification = notifications[0]
        assert invite_org.name in notification.message
        assert "member" in notification.message

    @pytest.mark.asyncio
    async def test_org_invite_no_notification_for_nonexistent_user(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        invite_org: Organization,
        auth_headers: dict[str, str],
    ) -> None:
        """Inviting an email with no account should NOT create any notification.

        When the invitee email doesn't correspond to an existing user,
        no in-app notification can be sent because there is no recipient.
        """
        # Arrange
        nonexistent_email = f"nobody-{uuid4().hex[:8]}@example.com"

        # Act
        response = await client.post(
            f"/api/v1/organizations/{invite_org.id}/invites",
            json={"email": nonexistent_email, "role": "member"},
            headers=auth_headers,
        )

        # Assert — invite succeeded (created even if user doesn't exist)
        assert response.status_code == 201

        # Assert — no ORG_INVITE notifications exist at all
        result = await db_session.execute(
            select(Notification).where(
                Notification.type == NotificationType.ORG_INVITE,
            )
        )
        notifications = result.scalars().all()
        assert len(notifications) == 0

    @pytest.mark.asyncio
    async def test_org_invite_notification_contains_correct_data(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_user,
        test_user_2,
        invite_org: Organization,
        auth_headers: dict[str, str],
    ) -> None:
        """Notification data should include action_url, entity info, and role.

        The notification service stores action_url, actor_id, entity_type,
        entity_id, and role inside the JSONB data field.
        """
        # Arrange — nothing extra needed

        # Act
        response = await client.post(
            f"/api/v1/organizations/{invite_org.id}/invites",
            json={"email": test_user_2.email, "role": "member"},
            headers=auth_headers,
        )
        assert response.status_code == 201

        # Assert
        result = await db_session.execute(
            select(Notification).where(
                Notification.user_id == test_user_2.id,
                Notification.type == NotificationType.ORG_INVITE,
            )
        )
        notification = result.scalar_one()

        assert notification.data is not None
        assert notification.data["action_url"] == f"/organizations/{invite_org.id}/invites"
        assert notification.data["actor_id"] == str(test_user.id)
        assert notification.data["entity_type"] == "organization"
        assert notification.data["entity_id"] == str(invite_org.id)
        assert notification.data["role"] == "member"

    @pytest.mark.asyncio
    async def test_org_invite_notification_is_high_priority(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_user,
        test_user_2,
        invite_org: Organization,
        auth_headers: dict[str, str],
    ) -> None:
        """Organization invite notifications should have HIGH priority.

        The notify_org_invite helper passes priority=HIGH, which the
        service stores as data['priority'] = 'high' in the JSONB field.
        """
        # Arrange — nothing extra needed

        # Act
        response = await client.post(
            f"/api/v1/organizations/{invite_org.id}/invites",
            json={"email": test_user_2.email, "role": "member"},
            headers=auth_headers,
        )
        assert response.status_code == 201

        # Assert
        result = await db_session.execute(
            select(Notification).where(
                Notification.user_id == test_user_2.id,
                Notification.type == NotificationType.ORG_INVITE,
            )
        )
        notification = result.scalar_one()

        assert notification.data is not None
        assert notification.data["priority"] == NotificationPriority.HIGH.value
