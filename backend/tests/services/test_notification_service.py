"""
Tests for notification service.

Tests notification creation, delivery, preferences, and management.
"""

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    Notification,
    NotificationPreference,
    NotificationPriority,
    NotificationType,
    User,
)
from app.services.notification_service import NotificationService


# =============================================================================
# Fixtures
# =============================================================================


@pytest_asyncio.fixture
async def notification_service(db_session: AsyncSession) -> NotificationService:
    """Create a notification service instance."""
    return NotificationService(db_session)


@pytest_asyncio.fixture
async def test_user(db_session: AsyncSession) -> User:
    """Create a test user."""
    user = User(
        id=uuid4(),
        email="test@example.com",
        username="testuser",
        password_hash="hashed",
    )
    db_session.add(user)
    await db_session.commit()
    return user


@pytest_asyncio.fixture
async def actor_user(db_session: AsyncSession) -> User:
    """Create an actor user for notifications."""
    user = User(
        id=uuid4(),
        email="actor@example.com",
        username="actoruser",
        password_hash="hashed",
    )
    db_session.add(user)
    await db_session.commit()
    return user


# =============================================================================
# Notification Creation Tests
# =============================================================================


@pytest.mark.asyncio
async def test_create_notification_basic(
    notification_service: NotificationService,
    test_user: User,
    db_session: AsyncSession,
):
    """Test creating a basic notification."""
    notification = await notification_service.create_notification(
        user_id=test_user.id,
        notification_type=NotificationType.DESIGN_SHARED,
        title="Design Shared",
        message="Your design has been shared",
    )

    assert notification is not None
    assert notification.user_id == test_user.id
    assert notification.type == NotificationType.DESIGN_SHARED
    assert notification.title == "Design Shared"
    assert notification.message == "Your design has been shared"
    assert not notification.read

    # Verify saved to database
    await db_session.refresh(notification)
    assert notification.id is not None


@pytest.mark.asyncio
async def test_create_notification_with_all_fields(
    notification_service: NotificationService,
    test_user: User,
    actor_user: User,
    db_session: AsyncSession,
):
    """Test creating a notification with all optional fields."""
    entity_id = uuid4()
    data = {"extra": "info"}

    notification = await notification_service.create_notification(
        user_id=test_user.id,
        notification_type=NotificationType.DESIGN_COMMENT,
        title="New Comment",
        message="Someone commented on your design",
        action_url="/designs/123",
        action_label="View Comment",
        actor_id=actor_user.id,
        entity_type="design",
        entity_id=entity_id,
        data=data,
        priority=NotificationPriority.HIGH,
        expires_in_days=7,
    )

    assert notification is not None
    assert notification.user_id == test_user.id
    assert notification.data["action_url"] == "/designs/123"
    assert notification.data["action_label"] == "View Comment"
    assert notification.data["actor_id"] == str(actor_user.id)
    assert notification.data["entity_type"] == "design"
    assert notification.data["entity_id"] == str(entity_id)
    assert notification.data["priority"] == NotificationPriority.HIGH.value
    assert "expires_at" in notification.data
    assert notification.data["extra"] == "info"


@pytest.mark.asyncio
async def test_create_notification_respects_user_preferences(
    notification_service: NotificationService,
    test_user: User,
    db_session: AsyncSession,
):
    """Test notification respects user preferences."""
    # Disable design shared notifications for user
    pref = NotificationPreference(
        user_id=test_user.id,
        notification_type=NotificationType.DESIGN_SHARED,
        in_app_enabled=False,
        email_enabled=False,
    )
    db_session.add(pref)
    await db_session.commit()

    # Try to create notification
    notification = await notification_service.create_notification(
        user_id=test_user.id,
        notification_type=NotificationType.DESIGN_SHARED,
        title="Design Shared",
        message="Your design has been shared",
    )

    # Should return None because user disabled this notification type
    assert notification is None


# =============================================================================
# Notification Retrieval Tests
# =============================================================================


@pytest.mark.asyncio
async def test_get_user_notifications(
    notification_service: NotificationService,
    test_user: User,
    db_session: AsyncSession,
):
    """Test retrieving user notifications."""
    # Create multiple notifications
    for i in range(3):
        notif = Notification(
            user_id=test_user.id,
            type=NotificationType.SYSTEM,
            title=f"Notification {i}",
            message=f"Message {i}",
        )
        db_session.add(notif)
    await db_session.commit()

    # Get notifications
    notifications = await notification_service.get_user_notifications(
        user_id=test_user.id,
        limit=10,
    )

    assert len(notifications) == 3
    assert all(n.user_id == test_user.id for n in notifications)


@pytest.mark.asyncio
async def test_get_user_notifications_with_limit(
    notification_service: NotificationService,
    test_user: User,
    db_session: AsyncSession,
):
    """Test retrieving user notifications with limit."""
    # Create 5 notifications
    for i in range(5):
        notif = Notification(
            user_id=test_user.id,
            type=NotificationType.SYSTEM,
            title=f"Notification {i}",
            message=f"Message {i}",
        )
        db_session.add(notif)
    await db_session.commit()

    # Get only 2 notifications
    notifications = await notification_service.get_user_notifications(
        user_id=test_user.id,
        limit=2,
    )

    assert len(notifications) == 2


@pytest.mark.asyncio
async def test_get_unread_count(
    notification_service: NotificationService,
    test_user: User,
    db_session: AsyncSession,
):
    """Test getting unread notification count."""
    # Create mix of read and unread notifications
    for i in range(5):
        notif = Notification(
            user_id=test_user.id,
            type=NotificationType.SYSTEM,
            title=f"Notification {i}",
            message=f"Message {i}",
            read=i < 2,  # First 2 are read
        )
        db_session.add(notif)
    await db_session.commit()

    count = await notification_service.get_unread_count(test_user.id)

    assert count == 3  # 5 total - 2 read = 3 unread


@pytest.mark.asyncio
async def test_get_unread_count_no_notifications(
    notification_service: NotificationService,
    test_user: User,
):
    """Test getting unread count when no notifications exist."""
    count = await notification_service.get_unread_count(test_user.id)

    assert count == 0


# =============================================================================
# Notification Update Tests
# =============================================================================


@pytest.mark.asyncio
async def test_mark_notification_as_read(
    notification_service: NotificationService,
    test_user: User,
    db_session: AsyncSession,
):
    """Test marking a notification as read."""
    # Create unread notification
    notif = Notification(
        user_id=test_user.id,
        type=NotificationType.SYSTEM,
        title="Test",
        message="Test message",
        read=False,
    )
    db_session.add(notif)
    await db_session.commit()

    # Mark as read
    result = await notification_service.mark_as_read(
        notification_id=notif.id,
        user_id=test_user.id,
    )

    assert result is True

    # Verify notification is marked as read
    await db_session.refresh(notif)
    assert notif.read is True


@pytest.mark.asyncio
async def test_mark_all_as_read(
    notification_service: NotificationService,
    test_user: User,
    db_session: AsyncSession,
):
    """Test marking all notifications as read."""
    # Create multiple unread notifications
    for i in range(3):
        notif = Notification(
            user_id=test_user.id,
            type=NotificationType.SYSTEM,
            title=f"Test {i}",
            message=f"Message {i}",
            read=False,
        )
        db_session.add(notif)
    await db_session.commit()

    # Mark all as read
    count = await notification_service.mark_all_as_read(test_user.id)

    assert count == 3

    # Verify all are marked as read
    query = select(Notification).where(Notification.user_id == test_user.id)
    result = await db_session.execute(query)
    notifications = result.scalars().all()
    assert all(n.read for n in notifications)


@pytest.mark.asyncio
async def test_delete_notification(
    notification_service: NotificationService,
    test_user: User,
    db_session: AsyncSession,
):
    """Test deleting a notification."""
    # Create notification
    notif = Notification(
        user_id=test_user.id,
        type=NotificationType.SYSTEM,
        title="Test",
        message="Test message",
    )
    db_session.add(notif)
    await db_session.commit()
    notif_id = notif.id

    # Delete notification
    result = await notification_service.delete_notification(
        notification_id=notif_id,
        user_id=test_user.id,
    )

    assert result is True

    # Verify notification is deleted
    query = select(Notification).where(Notification.id == notif_id)
    result_check = await db_session.execute(query)
    assert result_check.scalar_one_or_none() is None


# =============================================================================
# Notification Preference Tests
# =============================================================================


@pytest.mark.asyncio
async def test_get_user_preferences_default(
    notification_service: NotificationService,
    test_user: User,
):
    """Test getting default user preferences."""
    prefs = await notification_service.get_user_preferences(test_user.id)

    # Should return default preferences for all types
    assert len(prefs) > 0
    # Verify defaults are enabled
    assert all(p.in_app_enabled for p in prefs)


@pytest.mark.asyncio
async def test_update_notification_preference(
    notification_service: NotificationService,
    test_user: User,
    db_session: AsyncSession,
):
    """Test updating a notification preference."""
    result = await notification_service.update_preference(
        user_id=test_user.id,
        notification_type=NotificationType.DESIGN_SHARED,
        in_app_enabled=False,
        email_enabled=True,
    )

    assert result is not None
    assert result.notification_type == NotificationType.DESIGN_SHARED
    assert result.in_app_enabled is False
    assert result.email_enabled is True


@pytest.mark.asyncio
async def test_should_send_in_app_default_enabled(
    notification_service: NotificationService,
    test_user: User,
):
    """Test should_send_in_app returns True by default."""
    should_send = await notification_service.should_send_in_app(
        user_id=test_user.id,
        notification_type=NotificationType.DESIGN_SHARED,
    )

    assert should_send is True


@pytest.mark.asyncio
async def test_should_send_in_app_disabled(
    notification_service: NotificationService,
    test_user: User,
    db_session: AsyncSession,
):
    """Test should_send_in_app returns False when disabled."""
    # Disable in-app notifications
    pref = NotificationPreference(
        user_id=test_user.id,
        notification_type=NotificationType.DESIGN_SHARED,
        in_app_enabled=False,
    )
    db_session.add(pref)
    await db_session.commit()

    should_send = await notification_service.should_send_in_app(
        user_id=test_user.id,
        notification_type=NotificationType.DESIGN_SHARED,
    )

    assert should_send is False


@pytest.mark.asyncio
async def test_should_send_email_default_enabled(
    notification_service: NotificationService,
    test_user: User,
):
    """Test should_send_email returns True by default."""
    should_send = await notification_service.should_send_email(
        user_id=test_user.id,
        notification_type=NotificationType.DESIGN_SHARED,
    )

    assert should_send is True


@pytest.mark.asyncio
async def test_should_send_email_disabled(
    notification_service: NotificationService,
    test_user: User,
    db_session: AsyncSession,
):
    """Test should_send_email returns False when disabled."""
    # Disable email notifications
    pref = NotificationPreference(
        user_id=test_user.id,
        notification_type=NotificationType.DESIGN_SHARED,
        email_enabled=False,
    )
    db_session.add(pref)
    await db_session.commit()

    should_send = await notification_service.should_send_email(
        user_id=test_user.id,
        notification_type=NotificationType.DESIGN_SHARED,
    )

    assert should_send is False


# =============================================================================
# Bulk Operations Tests
# =============================================================================


@pytest.mark.asyncio
async def test_delete_old_notifications(
    notification_service: NotificationService,
    test_user: User,
    db_session: AsyncSession,
):
    """Test deleting old read notifications."""
    # Create old read notification
    old_notif = Notification(
        user_id=test_user.id,
        type=NotificationType.SYSTEM,
        title="Old",
        message="Old message",
        read=True,
        created_at=datetime.now(tz=UTC) - timedelta(days=40),
    )
    # Create recent notification
    recent_notif = Notification(
        user_id=test_user.id,
        type=NotificationType.SYSTEM,
        title="Recent",
        message="Recent message",
        read=True,
    )
    db_session.add_all([old_notif, recent_notif])
    await db_session.commit()

    # Delete notifications older than 30 days
    count = await notification_service.delete_old_notifications(days=30)

    assert count >= 1

    # Verify old notification is deleted but recent remains
    query = select(Notification).where(Notification.user_id == test_user.id)
    result = await db_session.execute(query)
    notifications = result.scalars().all()
    assert len(notifications) == 1
    assert notifications[0].title == "Recent"


# =============================================================================
# Edge Cases
# =============================================================================


@pytest.mark.asyncio
async def test_create_notification_with_null_data(
    notification_service: NotificationService,
    test_user: User,
):
    """Test creating notification with None data field."""
    notification = await notification_service.create_notification(
        user_id=test_user.id,
        notification_type=NotificationType.SYSTEM,
        title="Test",
        message="Test message",
        data=None,
    )

    assert notification is not None
    assert notification.data is not None  # Should be empty dict


@pytest.mark.asyncio
async def test_mark_as_read_nonexistent_notification(
    notification_service: NotificationService,
    test_user: User,
):
    """Test marking non-existent notification as read."""
    result = await notification_service.mark_as_read(
        notification_id=uuid4(),
        user_id=test_user.id,
    )

    assert result is False


@pytest.mark.asyncio
async def test_delete_nonexistent_notification(
    notification_service: NotificationService,
    test_user: User,
):
    """Test deleting non-existent notification."""
    result = await notification_service.delete_notification(
        notification_id=uuid4(),
        user_id=test_user.id,
    )

    assert result is False
