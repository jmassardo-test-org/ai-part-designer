"""
Tests for CAD v2 Celery tasks.

Tests async compilation and generation tasks.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest


class TestCompileEnclosureV2Task:
    """Tests for compile_enclosure_v2 Celery task."""

    def test_task_is_registered(self):
        """Test task is properly registered with Celery."""
        from app.worker.tasks.cad_v2 import compile_enclosure_v2

        assert compile_enclosure_v2.name == "app.worker.tasks.cad_v2.compile_enclosure_v2"

    def test_task_has_correct_retry_config(self):
        """Test task retry configuration."""
        from app.worker.tasks.cad_v2 import compile_enclosure_v2

        assert compile_enclosure_v2.max_retries == 2
        assert compile_enclosure_v2.default_retry_delay == 30

    def test_task_has_time_limits(self):
        """Test task has appropriate time limits."""
        from app.worker.tasks.cad_v2 import compile_enclosure_v2

        assert compile_enclosure_v2.soft_time_limit == 300
        assert compile_enclosure_v2.time_limit == 360


class TestGenerateFromDescriptionV2Task:
    """Tests for generate_from_description_v2 Celery task."""

    def test_task_is_registered(self):
        """Test task is properly registered with Celery."""
        from app.worker.tasks.cad_v2 import generate_from_description_v2

        assert (
            generate_from_description_v2.name
            == "app.worker.tasks.cad_v2.generate_from_description_v2"
        )

    def test_task_has_longer_time_limits(self):
        """Test AI generation task has longer time limits."""
        from app.worker.tasks.cad_v2 import generate_from_description_v2

        # AI generation needs more time
        assert generate_from_description_v2.soft_time_limit == 600
        assert generate_from_description_v2.time_limit == 720


class TestTasksExport:
    """Tests for task exports from package."""

    def test_tasks_exported_from_package(self):
        """Test v2 tasks are exported from worker.tasks package."""
        from app.worker.tasks import (
            compile_enclosure_v2,
            generate_from_description_v2,
        )

        assert compile_enclosure_v2 is not None
        assert generate_from_description_v2 is not None

    def test_tasks_in_all_list(self):
        """Test v2 tasks are in __all__ list."""
        from app.worker import tasks

        assert "compile_enclosure_v2" in tasks.__all__
        assert "generate_from_description_v2" in tasks.__all__


class TestFailJobHelper:
    """Tests for _fail_job helper function."""

    @pytest.mark.asyncio
    async def test_fail_job_updates_status(self):
        """Test _fail_job updates job status to failed."""
        from app.worker.tasks.cad_v2 import _fail_job

        mock_job_repo = MagicMock()
        mock_job_repo.update = AsyncMock()
        mock_session = MagicMock()
        mock_session.commit = AsyncMock()

        job_id = str(uuid4())
        user_id = str(uuid4())

        with patch("app.worker.tasks.cad_v2.send_job_failed") as mock_send:
            with patch(
                "app.services.notification_service.notify_job_failed",
                new_callable=AsyncMock,
            ):
                await _fail_job(
                    mock_job_repo,
                    mock_session,
                    job_id,
                    user_id,
                    "Test error message",
                )

        # Verify job was updated
        mock_job_repo.update.assert_called_once()
        call_kwargs = mock_job_repo.update.call_args[1]
        assert call_kwargs["status"] == "failed"
        assert call_kwargs["error_message"] == "Test error message"

        # Verify session was committed
        mock_session.commit.assert_called_once()

        # Verify WebSocket notification was sent
        mock_send.assert_called_once_with(user_id, job_id, "Test error message")

    @pytest.mark.asyncio
    async def test_fail_job_skips_ws_when_no_user(self):
        """Test _fail_job skips WebSocket when user_id is None."""
        from app.worker.tasks.cad_v2 import _fail_job

        mock_job_repo = MagicMock()
        mock_job_repo.update = AsyncMock()
        mock_session = MagicMock()
        mock_session.commit = AsyncMock()

        job_id = str(uuid4())

        with patch("app.worker.tasks.cad_v2.send_job_failed") as mock_send:
            await _fail_job(
                mock_job_repo,
                mock_session,
                job_id,
                None,  # No user
                "Test error",
            )

        # WebSocket should not be called
        mock_send.assert_not_called()
