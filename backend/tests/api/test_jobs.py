"""
Tests for Jobs API endpoints.

Tests job listing, status retrieval, cancellation, retry, and statistics.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import uuid4

import pytest

if TYPE_CHECKING:
    from httpx import AsyncClient
    from sqlalchemy.ext.asyncio import AsyncSession

# =============================================================================
# List Jobs Tests
# =============================================================================


class TestListJobs:
    """Tests for job listing endpoint."""

    @pytest.mark.asyncio
    async def test_list_jobs_empty(
        self,
        client: AsyncClient,
        test_user,
        auth_headers,
    ):
        """Test listing jobs when user has none."""
        response = await client.get(
            "/api/v1/jobs/",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()

        assert data["jobs"] == []
        assert data["total"] == 0
        assert data["has_more"] is False

    @pytest.mark.asyncio
    async def test_list_jobs_with_jobs(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_user,
        auth_headers,
        job_factory,
    ):
        """Test listing jobs when user has jobs."""
        await job_factory.create(db=db_session, user=test_user)
        await job_factory.create(db=db_session, user=test_user)
        await job_factory.create(db=db_session, user=test_user)

        response = await client.get(
            "/api/v1/jobs/",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()

        assert len(data["jobs"]) == 3
        assert data["total"] == 3

    @pytest.mark.asyncio
    async def test_list_jobs_pagination(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_user,
        auth_headers,
        job_factory,
    ):
        """Test job listing pagination."""
        for _ in range(5):
            await job_factory.create(db=db_session, user=test_user)

        # Get first page
        response = await client.get(
            "/api/v1/jobs/",
            headers=auth_headers,
            params={"skip": 0, "limit": 2},
        )

        assert response.status_code == 200
        data = response.json()

        assert len(data["jobs"]) == 2
        assert data["total"] == 5
        assert data["has_more"] is True

    @pytest.mark.asyncio
    async def test_list_jobs_filter_by_status(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_user,
        auth_headers,
        job_factory,
    ):
        """Test filtering jobs by status."""
        await job_factory.create(db=db_session, user=test_user, status="pending")
        await job_factory.create(db=db_session, user=test_user, status="completed")
        await job_factory.create(db=db_session, user=test_user, status="pending")

        response = await client.get(
            "/api/v1/jobs/",
            headers=auth_headers,
            params={"status_filter": "pending"},
        )

        assert response.status_code == 200
        data = response.json()

        assert len(data["jobs"]) == 2
        assert all(j["status"] == "pending" for j in data["jobs"])

    @pytest.mark.asyncio
    async def test_list_jobs_filter_by_type(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_user,
        auth_headers,
        job_factory,
    ):
        """Test filtering jobs by type."""
        await job_factory.create(db=db_session, user=test_user, job_type="ai_generation")
        await job_factory.create(db=db_session, user=test_user, job_type="export")
        await job_factory.create(db=db_session, user=test_user, job_type="ai_generation")

        response = await client.get(
            "/api/v1/jobs/",
            headers=auth_headers,
            params={"job_type": "ai_generation"},
        )

        assert response.status_code == 200
        data = response.json()

        assert len(data["jobs"]) == 2
        assert all(j["job_type"] == "ai_generation" for j in data["jobs"])

    @pytest.mark.asyncio
    async def test_list_jobs_only_own_jobs(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_user,
        auth_headers,
        user_factory,
        job_factory,
    ):
        """Test that users only see their own jobs."""
        other_user = await user_factory.create(db=db_session)

        await job_factory.create(db=db_session, user=test_user)
        await job_factory.create(db=db_session, user=other_user)

        response = await client.get(
            "/api/v1/jobs/",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()

        assert len(data["jobs"]) == 1


# =============================================================================
# Get Job Tests
# =============================================================================


class TestGetJob:
    """Tests for getting individual job details."""

    @pytest.mark.asyncio
    async def test_get_job_success(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_user,
        auth_headers,
        job_factory,
    ):
        """Test getting job details."""
        job = await job_factory.create(
            db=db_session,
            user=test_user,
            job_type="ai_generation",
            status="running",
            progress=50,
            progress_message="Processing...",
        )

        response = await client.get(
            f"/api/v1/jobs/{job.id}",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()

        assert data["id"] == str(job.id)
        assert data["job_type"] == "ai_generation"
        assert data["status"] == "running"
        assert data["progress"] == 50
        assert data["progress_message"] == "Processing..."

    @pytest.mark.asyncio
    async def test_get_job_not_found(
        self,
        client: AsyncClient,
        test_user,
        auth_headers,
    ):
        """Test getting non-existent job."""
        response = await client.get(
            f"/api/v1/jobs/{uuid4()}",
            headers=auth_headers,
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_job_other_user(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_user,
        auth_headers,
        user_factory,
        job_factory,
    ):
        """Test getting another user's job returns 404."""
        other_user = await user_factory.create(db=db_session)
        other_job = await job_factory.create(db=db_session, user=other_user)

        response = await client.get(
            f"/api/v1/jobs/{other_job.id}",
            headers=auth_headers,
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_completed_job_with_result(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_user,
        auth_headers,
        job_factory,
    ):
        """Test getting completed job shows result."""
        job = await job_factory.create_completed(
            db=db_session,
            user=test_user,
            result={
                "file_url": "https://storage.test/output.step",
                "thumbnail_url": "https://storage.test/thumb.png",
            },
        )

        response = await client.get(
            f"/api/v1/jobs/{job.id}",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "completed"
        assert data["progress"] == 100
        assert data["result"]["file_url"] == "https://storage.test/output.step"

    @pytest.mark.asyncio
    async def test_get_failed_job_with_error(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_user,
        auth_headers,
        job_factory,
    ):
        """Test getting failed job shows error."""
        job = await job_factory.create_failed(
            db=db_session,
            user=test_user,
            error_message="AI generation failed: invalid geometry",
        )

        response = await client.get(
            f"/api/v1/jobs/{job.id}",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "failed"
        assert "invalid geometry" in data["error_message"]


# =============================================================================
# Cancel Job Tests
# =============================================================================


class TestCancelJob:
    """Tests for job cancellation endpoint."""

    @pytest.mark.asyncio
    async def test_cancel_pending_job_success(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_user,
        auth_headers,
        job_factory,
    ):
        """Test cancelling a pending job."""
        job = await job_factory.create(
            db=db_session,
            user=test_user,
            status="pending",
        )

        response = await client.post(
            f"/api/v1/jobs/{job.id}/cancel",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()

        assert data["id"] == str(job.id)
        assert data["status"] == "cancelled"

        # Verify job is cancelled in DB
        await db_session.refresh(job)
        assert job.status == "cancelled"

    @pytest.mark.asyncio
    async def test_cancel_running_job_success(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_user,
        auth_headers,
        job_factory,
    ):
        """Test cancelling a running job."""
        job = await job_factory.create(
            db=db_session,
            user=test_user,
            status="running",
            progress=30,
        )

        response = await client.post(
            f"/api/v1/jobs/{job.id}/cancel",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "cancelled"

    @pytest.mark.asyncio
    async def test_cancel_completed_job_fails(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_user,
        auth_headers,
        job_factory,
    ):
        """Test that completed jobs cannot be cancelled."""
        job = await job_factory.create_completed(db=db_session, user=test_user)

        response = await client.post(
            f"/api/v1/jobs/{job.id}/cancel",
            headers=auth_headers,
        )

        assert response.status_code == 400
        assert "cannot be cancelled" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_cancel_failed_job_fails(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_user,
        auth_headers,
        job_factory,
    ):
        """Test that failed jobs cannot be cancelled."""
        job = await job_factory.create_failed(db=db_session, user=test_user)

        response = await client.post(
            f"/api/v1/jobs/{job.id}/cancel",
            headers=auth_headers,
        )

        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_cancel_job_not_found(
        self,
        client: AsyncClient,
        test_user,
        auth_headers,
    ):
        """Test cancelling non-existent job."""
        response = await client.post(
            f"/api/v1/jobs/{uuid4()}/cancel",
            headers=auth_headers,
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_cancel_other_user_job(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_user,
        auth_headers,
        user_factory,
        job_factory,
    ):
        """Test cancelling another user's job returns 404."""
        other_user = await user_factory.create(db=db_session)
        other_job = await job_factory.create(db=db_session, user=other_user)

        response = await client.post(
            f"/api/v1/jobs/{other_job.id}/cancel",
            headers=auth_headers,
        )

        assert response.status_code == 404


# =============================================================================
# Retry Job Tests
# =============================================================================


class TestRetryJob:
    """Tests for job retry endpoint."""

    @pytest.mark.asyncio
    async def test_retry_failed_job_success(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_user,
        auth_headers,
        job_factory,
    ):
        """Test retrying a failed job."""
        job = await job_factory.create_failed(
            db=db_session,
            user=test_user,
            retry_count=0,
            max_retries=3,
        )

        response = await client.post(
            f"/api/v1/jobs/{job.id}/retry",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "pending"
        assert data["progress"] == 0

        # Verify job is reset in DB
        await db_session.refresh(job)
        assert job.status == "pending"
        assert job.retry_count == 1
        assert job.error is None
        assert job.error_message is None

    @pytest.mark.asyncio
    async def test_retry_exhausted_retries_fails(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_user,
        auth_headers,
        job_factory,
    ):
        """Test that job with exhausted retries cannot be retried."""
        job = await job_factory.create_failed(
            db=db_session,
            user=test_user,
            retry_count=3,
            max_retries=3,
        )

        response = await client.post(
            f"/api/v1/jobs/{job.id}/retry",
            headers=auth_headers,
        )

        assert response.status_code == 400
        assert "exhausted" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_retry_completed_job_fails(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_user,
        auth_headers,
        job_factory,
    ):
        """Test that completed jobs cannot be retried."""
        job = await job_factory.create_completed(db=db_session, user=test_user)

        response = await client.post(
            f"/api/v1/jobs/{job.id}/retry",
            headers=auth_headers,
        )

        assert response.status_code == 400
        assert "only failed jobs" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_retry_pending_job_fails(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_user,
        auth_headers,
        job_factory,
    ):
        """Test that pending jobs cannot be retried."""
        job = await job_factory.create(db=db_session, user=test_user, status="pending")

        response = await client.post(
            f"/api/v1/jobs/{job.id}/retry",
            headers=auth_headers,
        )

        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_retry_job_not_found(
        self,
        client: AsyncClient,
        test_user,
        auth_headers,
    ):
        """Test retrying non-existent job."""
        response = await client.post(
            f"/api/v1/jobs/{uuid4()}/retry",
            headers=auth_headers,
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_retry_other_user_job(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_user,
        auth_headers,
        user_factory,
        job_factory,
    ):
        """Test retrying another user's job returns 404."""
        other_user = await user_factory.create(db=db_session)
        other_job = await job_factory.create_failed(db=db_session, user=other_user)

        response = await client.post(
            f"/api/v1/jobs/{other_job.id}/retry",
            headers=auth_headers,
        )

        assert response.status_code == 404


# =============================================================================
# Job Stats Tests
# =============================================================================


class TestJobStats:
    """Tests for job statistics endpoint."""

    @pytest.mark.asyncio
    async def test_get_stats_empty(
        self,
        client: AsyncClient,
        test_user,
        auth_headers,
    ):
        """Test getting stats with no jobs."""
        response = await client.get(
            "/api/v1/jobs/stats/summary",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()

        assert data["total"] == 0
        assert data["pending"] == 0
        assert data["running"] == 0
        assert data["completed"] == 0
        assert data["failed"] == 0

    @pytest.mark.asyncio
    async def test_get_stats_with_jobs(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_user,
        auth_headers,
        job_factory,
    ):
        """Test getting stats with various job statuses."""
        await job_factory.create(db=db_session, user=test_user, status="pending")
        await job_factory.create(db=db_session, user=test_user, status="pending")
        await job_factory.create(db=db_session, user=test_user, status="running")
        await job_factory.create_completed(db=db_session, user=test_user)
        await job_factory.create_completed(db=db_session, user=test_user)
        await job_factory.create_completed(db=db_session, user=test_user)
        await job_factory.create_failed(db=db_session, user=test_user)

        response = await client.get(
            "/api/v1/jobs/stats/summary",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()

        assert data["total"] == 7
        assert data["pending"] == 2
        assert data["running"] == 1
        assert data["completed"] == 3
        assert data["failed"] == 1

    @pytest.mark.asyncio
    async def test_get_stats_only_own_jobs(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_user,
        auth_headers,
        user_factory,
        job_factory,
    ):
        """Test that stats only include user's own jobs."""
        other_user = await user_factory.create(db=db_session)

        await job_factory.create(db=db_session, user=test_user)
        await job_factory.create(db=db_session, user=other_user)
        await job_factory.create(db=db_session, user=other_user)

        response = await client.get(
            "/api/v1/jobs/stats/summary",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()

        assert data["total"] == 1


# =============================================================================
# Celery Task Lifecycle Tests
# =============================================================================


class TestCeleryTaskCancellation:
    """Tests for Celery task cancellation during job cancellation."""

    @pytest.mark.asyncio
    async def test_cancel_job_with_celery_task_id_revokes_task(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_user,
        auth_headers,
        job_factory,
        mocker,
    ):
        """Test that cancelling a job with celery_task_id revokes the task."""
        # Create a running job with a celery_task_id
        job = await job_factory.create(
            db=db_session,
            user=test_user,
            status="running",
            celery_task_id="test-task-id-123",
        )

        # Mock celery_app.control.revoke
        mock_revoke = mocker.patch(
            "app.api.v1.jobs.celery_app.control.revoke",
        )

        response = await client.post(
            f"/api/v1/jobs/{job.id}/cancel",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "cancelled"

        # Verify revoke was called with correct parameters
        mock_revoke.assert_called_once_with(
            "test-task-id-123",
            terminate=True,
            signal="SIGTERM",  # Allow graceful cleanup
        )

    @pytest.mark.asyncio
    async def test_cancel_job_without_celery_task_id_succeeds(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_user,
        auth_headers,
        job_factory,
        mocker,
    ):
        """Test that cancelling a job without celery_task_id still works."""
        # Create a running job without a celery_task_id
        job = await job_factory.create(
            db=db_session,
            user=test_user,
            status="running",
            celery_task_id=None,
        )

        # Mock celery_app.control.revoke (should not be called)
        mock_revoke = mocker.patch(
            "app.api.v1.jobs.celery_app.control.revoke",
        )

        response = await client.post(
            f"/api/v1/jobs/{job.id}/cancel",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "cancelled"

        # Verify revoke was NOT called
        mock_revoke.assert_not_called()

    @pytest.mark.asyncio
    async def test_cancel_job_revoke_failure_does_not_fail_cancellation(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_user,
        auth_headers,
        job_factory,
        mocker,
    ):
        """Test that if revoke fails, job cancellation still succeeds."""
        job = await job_factory.create(
            db=db_session,
            user=test_user,
            status="running",
            celery_task_id="test-task-id-456",
        )

        # Mock celery_app.control.revoke to raise an exception
        mock_revoke = mocker.patch(
            "app.api.v1.jobs.celery_app.control.revoke",
            side_effect=Exception("Celery connection error"),
        )

        response = await client.post(
            f"/api/v1/jobs/{job.id}/cancel",
            headers=auth_headers,
        )

        # Job should still be cancelled despite revoke failure
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "cancelled"

        # Verify revoke was attempted
        mock_revoke.assert_called_once()


class TestCeleryTaskRetry:
    """Tests for Celery task re-queuing during job retry."""

    @pytest.mark.asyncio
    async def test_retry_job_requeues_ai_generation_task(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_user,
        auth_headers,
        job_factory,
        mocker,
    ):
        """Test that retrying an AI generation job re-queues the task."""
        # Create a failed AI generation job
        job = await job_factory.create_failed(
            db=db_session,
            user=test_user,
            job_type="ai_generation",
            retry_count=0,
            max_retries=3,
            input_params={
                "prompt": "Create a box",
                "context": {"size": "10mm"},
            },
        )

        # Mock the Celery task
        mock_task = mocker.MagicMock()
        mock_task.delay.return_value.id = "new-task-id-123"
        mocker.patch(
            "app.api.v1.jobs.generate_from_prompt",
            mock_task,
        )

        response = await client.post(
            f"/api/v1/jobs/{job.id}/retry",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "pending"

        # Verify task was re-queued
        mock_task.delay.assert_called_once_with(
            job_id=str(job.id),
            prompt="Create a box",
            _context={"size": "10mm"},
            user_id=str(test_user.id),
        )

        # Verify job has new celery_task_id
        await db_session.refresh(job)
        assert job.celery_task_id == "new-task-id-123"
        assert job.retry_count == 1

    @pytest.mark.asyncio
    async def test_retry_job_requeues_cad_v2_compile_task(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_user,
        auth_headers,
        job_factory,
        mocker,
    ):
        """Test that retrying a CAD v2 compile job re-queues the task."""
        job = await job_factory.create_failed(
            db=db_session,
            user=test_user,
            job_type="cad_v2_compile",
            retry_count=0,
            max_retries=3,
            input_params={
                "enclosure_schema": {"type": "box"},
                "export_format": "step",
            },
        )

        mock_task = mocker.MagicMock()
        mock_task.delay.return_value.id = "new-task-id-456"
        mocker.patch(
            "app.api.v1.jobs.compile_enclosure_v2",
            mock_task,
        )

        response = await client.post(
            f"/api/v1/jobs/{job.id}/retry",
            headers=auth_headers,
        )

        assert response.status_code == 200

        mock_task.delay.assert_called_once_with(
            job_id=str(job.id),
            enclosure_schema={"type": "box"},
            export_format="step",
            user_id=str(test_user.id),
        )

        await db_session.refresh(job)
        assert job.celery_task_id == "new-task-id-456"

    @pytest.mark.asyncio
    async def test_retry_job_requeues_format_conversion_task(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_user,
        auth_headers,
        job_factory,
        mocker,
    ):
        """Test that retrying a format conversion job re-queues the task."""
        job = await job_factory.create_failed(
            db=db_session,
            user=test_user,
            job_type="format_conversion",
            retry_count=0,
            max_retries=3,
            input_params={
                "source_url": "s3://bucket/file.step",
                "target_format": "stl",
            },
        )

        mock_task = mocker.MagicMock()
        mock_task.delay.return_value.id = "new-task-id-789"
        mocker.patch(
            "app.api.v1.jobs.convert_format",
            mock_task,
        )

        response = await client.post(
            f"/api/v1/jobs/{job.id}/retry",
            headers=auth_headers,
        )

        assert response.status_code == 200

        mock_task.delay.assert_called_once_with(
            job_id=str(job.id),
            source_url="s3://bucket/file.step",
            target_format="stl",
        )

        await db_session.refresh(job)
        assert job.celery_task_id == "new-task-id-789"

    @pytest.mark.asyncio
    async def test_retry_job_requeues_component_extraction_task(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_user,
        auth_headers,
        job_factory,
        mocker,
    ):
        """Test that retrying a component extraction job re-queues the task."""
        # Note: "full" is a valid job type for component extraction (CAD + datasheet)
        job = await job_factory.create_failed(
            db=db_session,
            user=test_user,
            job_type="full",
            retry_count=0,
            max_retries=3,
            input_params={},
        )

        mock_task = mocker.MagicMock()
        mock_task.delay.return_value.id = "new-task-id-abc"
        mocker.patch(
            "app.api.v1.jobs.extract_component_task",
            mock_task,
        )

        response = await client.post(
            f"/api/v1/jobs/{job.id}/retry",
            headers=auth_headers,
        )

        assert response.status_code == 200

        mock_task.delay.assert_called_once_with(str(job.id))

        await db_session.refresh(job)
        assert job.celery_task_id == "new-task-id-abc"

    @pytest.mark.asyncio
    async def test_retry_job_unsupported_type_logs_warning(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_user,
        auth_headers,
        job_factory,
    ):
        """Test that retrying a job with unsupported type logs warning but succeeds."""
        job = await job_factory.create_failed(
            db=db_session,
            user=test_user,
            job_type="unknown_type",
            retry_count=0,
            max_retries=3,
            input_params={},
        )

        response = await client.post(
            f"/api/v1/jobs/{job.id}/retry",
            headers=auth_headers,
        )

        # Job retry should succeed even if task can't be re-queued
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "pending"

        # Verify job state was updated but no celery_task_id
        await db_session.refresh(job)
        assert job.celery_task_id is None
        assert job.retry_count == 1

    @pytest.mark.asyncio
    async def test_retry_job_task_failure_rolls_back(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_user,
        auth_headers,
        job_factory,
        mocker,
    ):
        """Test that if task re-queuing fails, the retry is rolled back."""
        job = await job_factory.create_failed(
            db=db_session,
            user=test_user,
            job_type="ai_generation",
            retry_count=0,
            max_retries=3,
            input_params={"prompt": "Test"},
        )

        # Mock task to raise an exception
        mock_task = mocker.MagicMock()
        mock_task.delay.side_effect = Exception("Celery broker unavailable")
        mocker.patch(
            "app.api.v1.jobs.generate_from_prompt",
            mock_task,
        )

        response = await client.post(
            f"/api/v1/jobs/{job.id}/retry",
            headers=auth_headers,
        )

        # Should return 500 error
        assert response.status_code == 500
        assert "Failed to re-queue job" in response.json()["detail"]

        # Verify retry_count was rolled back
        await db_session.refresh(job)
        assert job.retry_count == 0
        assert job.status == "failed"  # Should still be failed
