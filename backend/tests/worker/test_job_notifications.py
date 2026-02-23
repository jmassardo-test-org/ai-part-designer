"""
Tests for job completion/failure notification persistence.

Verifies that worker tasks create DB notifications via
notify_job_completed / notify_job_failed, and that both
WebSocket push and DB persist happen together.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification import (
    DEFAULT_PREFERENCES,
    Notification,
    NotificationPreference,
    NotificationPriority,
    NotificationType,
)
from app.services.notification_service import (
    NotificationService,
    notify_job_completed,
    notify_job_failed,
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest_asyncio.fixture
async def user_id(test_user) -> UUID:
    """Return the test user's UUID."""
    return test_user.id


# =============================================================================
# notify_job_completed Tests
# =============================================================================


class TestJobCompletedNotification:
    """Tests for notify_job_completed helper."""

    @pytest.mark.asyncio
    async def test_job_completed_creates_notification(
        self, db_session: AsyncSession, user_id: UUID
    ) -> None:
        """Verify that notify_job_completed persists a JOB_COMPLETED notification."""
        # Arrange
        job_id = uuid4()
        job_type = "CAD generation"
        design_name = "test-bracket"

        # Act
        notification = await notify_job_completed(
            db=db_session,
            user_id=user_id,
            job_id=job_id,
            job_type=job_type,
            design_name=design_name,
        )

        # Assert
        assert notification is not None
        assert notification.type == NotificationType.JOB_COMPLETED
        assert notification.user_id == user_id
        assert notification.title == "Job completed"
        assert job_type in notification.message
        assert design_name in notification.message

    @pytest.mark.asyncio
    async def test_job_completed_notification_contains_job_details(
        self, db_session: AsyncSession, user_id: UUID
    ) -> None:
        """Verify notification data includes job_id, entity_type, and action_url."""
        # Arrange
        job_id = uuid4()
        job_type = "AI generation"
        design_name = "gear-housing"

        # Act
        notification = await notify_job_completed(
            db=db_session,
            user_id=user_id,
            job_id=job_id,
            job_type=job_type,
            design_name=design_name,
        )

        # Assert
        assert notification is not None
        assert notification.data is not None
        assert notification.data["entity_type"] == "job"
        assert notification.data["entity_id"] == str(job_id)
        assert notification.data["action_url"] == f"/jobs/{job_id}"
        assert notification.data["action_label"] == "View Result"

    @pytest.mark.asyncio
    async def test_job_completed_has_normal_priority(
        self, db_session: AsyncSession, user_id: UUID
    ) -> None:
        """Verify JOB_COMPLETED uses default NORMAL priority (no priority key in data)."""
        # Arrange
        job_id = uuid4()

        # Act
        notification = await notify_job_completed(
            db=db_session,
            user_id=user_id,
            job_id=job_id,
            job_type="CAD generation",
            design_name="widget",
        )

        # Assert — NORMAL priority is the default, so it won't be stored in data
        assert notification is not None
        assert notification.data is not None
        assert "priority" not in notification.data

    @pytest.mark.asyncio
    async def test_job_completed_persisted_in_db(
        self, db_session: AsyncSession, user_id: UUID
    ) -> None:
        """Verify the notification is actually stored and queryable."""
        # Arrange
        job_id = uuid4()

        # Act
        notification = await notify_job_completed(
            db=db_session,
            user_id=user_id,
            job_id=job_id,
            job_type="CAD generation",
            design_name="bracket",
        )

        # Assert — re-query from session to confirm persistence
        assert notification is not None
        result = await db_session.execute(
            select(Notification).where(Notification.id == notification.id)
        )
        fetched = result.scalar_one_or_none()
        assert fetched is not None
        assert fetched.type == NotificationType.JOB_COMPLETED
        assert fetched.user_id == user_id


# =============================================================================
# notify_job_failed Tests
# =============================================================================


class TestJobFailedNotification:
    """Tests for notify_job_failed helper."""

    @pytest.mark.asyncio
    async def test_job_failed_creates_notification(
        self, db_session: AsyncSession, user_id: UUID
    ) -> None:
        """Verify that notify_job_failed persists a JOB_FAILED notification."""
        # Arrange
        job_id = uuid4()
        job_type = "CAD generation"
        design_name = "enclosure"
        error_message = "CadQuery kernel timeout"

        # Act
        notification = await notify_job_failed(
            db=db_session,
            user_id=user_id,
            job_id=job_id,
            job_type=job_type,
            design_name=design_name,
            error_message=error_message,
        )

        # Assert
        assert notification is not None
        assert notification.type == NotificationType.JOB_FAILED
        assert notification.user_id == user_id
        assert notification.title == "Job failed"
        assert error_message in notification.message

    @pytest.mark.asyncio
    async def test_job_failed_notification_has_high_priority(
        self, db_session: AsyncSession, user_id: UUID
    ) -> None:
        """Verify JOB_FAILED notification is created with HIGH priority."""
        # Arrange
        job_id = uuid4()

        # Act
        notification = await notify_job_failed(
            db=db_session,
            user_id=user_id,
            job_id=job_id,
            job_type="AI generation",
            design_name="part",
            error_message="Model inference failed",
        )

        # Assert
        assert notification is not None
        assert notification.data is not None
        assert notification.data.get("priority") == NotificationPriority.HIGH.value

    @pytest.mark.asyncio
    async def test_job_failed_notification_includes_error(
        self, db_session: AsyncSession, user_id: UUID
    ) -> None:
        """Verify failure notification message includes the error message."""
        # Arrange
        job_id = uuid4()
        error_message = "Shape self-intersection detected at edge 42"

        # Act
        notification = await notify_job_failed(
            db=db_session,
            user_id=user_id,
            job_id=job_id,
            job_type="CAD v2",
            design_name="enclosure",
            error_message=error_message,
        )

        # Assert
        assert notification is not None
        assert error_message in notification.message
        assert "CAD v2" in notification.message
        assert "enclosure" in notification.message

    @pytest.mark.asyncio
    async def test_job_failed_notification_contains_job_details(
        self, db_session: AsyncSession, user_id: UUID
    ) -> None:
        """Verify failure notification data includes job_id, entity_type, and action_url."""
        # Arrange
        job_id = uuid4()

        # Act
        notification = await notify_job_failed(
            db=db_session,
            user_id=user_id,
            job_id=job_id,
            job_type="CAD generation",
            design_name="widget",
            error_message="timeout",
        )

        # Assert
        assert notification is not None
        assert notification.data is not None
        assert notification.data["entity_type"] == "job"
        assert notification.data["entity_id"] == str(job_id)
        assert notification.data["action_url"] == f"/jobs/{job_id}"
        assert notification.data["action_label"] == "View Details"


# =============================================================================
# Preference Respect Tests
# =============================================================================


class TestJobNotificationPreferences:
    """Tests verifying notification respects user preferences."""

    @pytest.mark.asyncio
    async def test_job_notification_respects_preferences_disabled(
        self, db_session: AsyncSession, user_id: UUID
    ) -> None:
        """Verify no JOB_COMPLETED notification when user disables in_app for that type."""
        # Arrange — create a preference disabling JOB_COMPLETED in-app
        pref = NotificationPreference(
            user_id=user_id,
            notification_type=NotificationType.JOB_COMPLETED,
            in_app_enabled=False,
            email_enabled=False,
        )
        db_session.add(pref)
        await db_session.commit()

        job_id = uuid4()

        # Act
        notification = await notify_job_completed(
            db=db_session,
            user_id=user_id,
            job_id=job_id,
            job_type="CAD generation",
            design_name="bracket",
        )

        # Assert — should return None because in_app is disabled
        assert notification is None

        # Double-check nothing was persisted
        result = await db_session.execute(
            select(Notification).where(
                Notification.user_id == user_id,
                Notification.type == NotificationType.JOB_COMPLETED,
            )
        )
        assert result.scalar_one_or_none() is None

    @pytest.mark.asyncio
    async def test_job_failed_still_sent_when_completed_disabled(
        self, db_session: AsyncSession, user_id: UUID
    ) -> None:
        """Verify JOB_FAILED notifications still work when JOB_COMPLETED is disabled."""
        # Arrange — disable only JOB_COMPLETED
        pref = NotificationPreference(
            user_id=user_id,
            notification_type=NotificationType.JOB_COMPLETED,
            in_app_enabled=False,
            email_enabled=False,
        )
        db_session.add(pref)
        await db_session.commit()

        job_id = uuid4()

        # Act
        notification = await notify_job_failed(
            db=db_session,
            user_id=user_id,
            job_id=job_id,
            job_type="CAD generation",
            design_name="part",
            error_message="failed",
        )

        # Assert — JOB_FAILED should still be created
        assert notification is not None
        assert notification.type == NotificationType.JOB_FAILED

    @pytest.mark.asyncio
    async def test_default_preferences_enable_job_notifications(self) -> None:
        """Verify DEFAULT_PREFERENCES enable in_app for both job notification types."""
        # Assert
        assert DEFAULT_PREFERENCES[NotificationType.JOB_COMPLETED]["in_app"] is True
        assert DEFAULT_PREFERENCES[NotificationType.JOB_FAILED]["in_app"] is True
        # JOB_FAILED also defaults to email
        assert DEFAULT_PREFERENCES[NotificationType.JOB_FAILED]["email"] is True


# =============================================================================
# WebSocket + DB Notification Co-occurrence Tests
# =============================================================================


class TestWebSocketAndDBNotification:
    """Tests verifying both WebSocket push and DB persist happen together."""

    @pytest.mark.asyncio
    async def test_both_ws_and_db_notification_sent_on_completion(
        self, db_session: AsyncSession, user_id: UUID
    ) -> None:
        """Verify that both send_job_complete and notify_job_completed are called on success.

        Simulates the worker pattern: WS push first, then DB persist.
        """
        # Arrange
        job_id = str(uuid4())
        result_data = {"success": True, "files": ["output.step"]}

        ws_called = False
        db_called = False

        # Act — replicate the worker task pattern
        with patch("app.worker.ws_utils.publish_ws_message", return_value=True) as mock_publish:
            from app.worker.ws_utils import send_job_complete

            send_job_complete(str(user_id), job_id, result_data)
            ws_called = mock_publish.called

        notification = await notify_job_completed(
            db=db_session,
            user_id=user_id,
            job_id=UUID(job_id),
            job_type="CAD generation",
            design_name="bracket",
        )
        db_called = notification is not None

        # Assert — both channels fired
        assert ws_called, "WebSocket publish_ws_message was not called"
        assert db_called, "DB notification was not created"
        assert notification is not None
        assert notification.type == NotificationType.JOB_COMPLETED

    @pytest.mark.asyncio
    async def test_both_ws_and_db_notification_sent_on_failure(
        self, db_session: AsyncSession, user_id: UUID
    ) -> None:
        """Verify that both send_job_failed and notify_job_failed are called on failure.

        Simulates the worker pattern: WS push first, then DB persist.
        """
        # Arrange
        job_id = str(uuid4())
        error_msg = "Build failed: invalid geometry"

        ws_called = False
        db_called = False

        # Act — replicate the worker task pattern
        with patch("app.worker.ws_utils.publish_ws_message", return_value=True) as mock_publish:
            from app.worker.ws_utils import send_job_failed

            send_job_failed(str(user_id), job_id, error_msg, "GeometryError")
            ws_called = mock_publish.called

        notification = await notify_job_failed(
            db=db_session,
            user_id=user_id,
            job_id=UUID(job_id),
            job_type="CAD generation",
            design_name="part",
            error_message=error_msg,
        )
        db_called = notification is not None

        # Assert — both channels fired
        assert ws_called, "WebSocket publish_ws_message was not called"
        assert db_called, "DB notification was not created"
        assert notification is not None
        assert notification.type == NotificationType.JOB_FAILED

    @pytest.mark.asyncio
    async def test_ws_message_contains_correct_payload(self) -> None:
        """Verify the WebSocket message payload structure for job_complete."""
        # Arrange
        user_id = str(uuid4())
        job_id = str(uuid4())
        result = {"success": True}

        # Act
        with patch("app.worker.ws_utils.publish_ws_message", return_value=True) as mock_publish:
            from app.worker.ws_utils import send_job_complete

            send_job_complete(user_id, job_id, result)

        # Assert
        mock_publish.assert_called_once()
        call_args = mock_publish.call_args
        assert call_args[0][0] == user_id
        payload = call_args[0][1]
        assert payload["type"] == "job_complete"
        assert payload["job_id"] == job_id
        assert payload["status"] == "completed"
        assert payload["progress"] == 100
        assert payload["result"] == result

    @pytest.mark.asyncio
    async def test_ws_failure_message_contains_error_details(self) -> None:
        """Verify the WebSocket message payload structure for job_failed."""
        # Arrange
        user_id = str(uuid4())
        job_id = str(uuid4())
        error = "Kernel crash"
        error_type = "RuntimeError"

        # Act
        with patch("app.worker.ws_utils.publish_ws_message", return_value=True) as mock_publish:
            from app.worker.ws_utils import send_job_failed

            send_job_failed(user_id, job_id, error, error_type)

        # Assert
        mock_publish.assert_called_once()
        payload = mock_publish.call_args[0][1]
        assert payload["type"] == "job_failed"
        assert payload["job_id"] == job_id
        assert payload["status"] == "failed"
        assert payload["error"] == error
        assert payload["error_type"] == error_type
