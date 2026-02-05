"""
Tests for v2 async generation endpoints.

Tests async compile endpoint and job status polling.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import uuid4

import pytest
import pytest_asyncio

from app.models.job import Job

if TYPE_CHECKING:
    from httpx import AsyncClient
    from sqlalchemy.ext.asyncio import AsyncSession


@pytest_asyncio.fixture
async def completed_job(db_session: AsyncSession, test_user) -> Job:
    """Create a completed job for testing."""
    job = Job(
        user_id=test_user.id,
        job_type="cad_v2_compile",
        status="completed",
        progress=100,
        progress_message="Complete",
        input_params={"enclosure_schema": {}, "export_format": "step"},
        result={
            "success": True,
            "parts": ["body", "lid"],
            "downloads": {
                "body": "/api/v2/downloads/test/body.step",
                "lid": "/api/v2/downloads/test/lid.step",
            },
        },
    )
    db_session.add(job)
    await db_session.commit()
    await db_session.refresh(job)
    return job


@pytest_asyncio.fixture
async def running_job(db_session: AsyncSession, test_user) -> Job:
    """Create a running job for testing."""
    job = Job(
        user_id=test_user.id,
        job_type="cad_v2_compile",
        status="running",
        progress=50,
        progress_message="Compiling geometry",
        input_params={"enclosure_schema": {}, "export_format": "step"},
    )
    db_session.add(job)
    await db_session.commit()
    await db_session.refresh(job)
    return job


@pytest_asyncio.fixture
async def failed_job(db_session: AsyncSession, test_user) -> Job:
    """Create a failed job for testing."""
    job = Job(
        user_id=test_user.id,
        job_type="cad_v2_compile",
        status="failed",
        progress=30,
        progress_message="Compilation failed",
        error_message="Schema validation error",
        input_params={"enclosure_schema": {}, "export_format": "step"},
    )
    db_session.add(job)
    await db_session.commit()
    await db_session.refresh(job)
    return job


class TestJobStatusEndpoint:
    """Tests for GET /api/v2/generate/job/{job_id}/status endpoint."""

    @pytest.mark.asyncio
    async def test_get_completed_job_status(
        self,
        client: AsyncClient,
        completed_job: Job,
    ):
        """Test getting status of completed job."""
        response = await client.get(f"/api/v2/generate/job/{completed_job.id}/status")

        assert response.status_code == 200
        data = response.json()
        assert data["job_id"] == str(completed_job.id)
        assert data["status"] == "completed"
        assert data["progress"] == 100
        assert data["result"] is not None
        assert data["result"]["success"] is True
        assert "body" in data["result"]["parts"]
        assert data["error"] is None

    @pytest.mark.asyncio
    async def test_get_running_job_status(
        self,
        client: AsyncClient,
        running_job: Job,
    ):
        """Test getting status of running job."""
        response = await client.get(f"/api/v2/generate/job/{running_job.id}/status")

        assert response.status_code == 200
        data = response.json()
        assert data["job_id"] == str(running_job.id)
        assert data["status"] == "running"
        assert data["progress"] == 50
        assert data["progress_message"] == "Compiling geometry"
        assert data["result"] is None  # Not complete yet
        assert data["error"] is None

    @pytest.mark.asyncio
    async def test_get_failed_job_status(
        self,
        client: AsyncClient,
        failed_job: Job,
    ):
        """Test getting status of failed job."""
        response = await client.get(f"/api/v2/generate/job/{failed_job.id}/status")

        assert response.status_code == 200
        data = response.json()
        assert data["job_id"] == str(failed_job.id)
        assert data["status"] == "failed"
        assert data["error"] == "Schema validation error"
        assert data["result"] is None

    @pytest.mark.asyncio
    async def test_get_job_status_not_found(self, client: AsyncClient):
        """Test getting status of non-existent job."""
        fake_id = str(uuid4())
        response = await client.get(f"/api/v2/generate/job/{fake_id}/status")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_get_job_status_invalid_id(self, client: AsyncClient):
        """Test getting status with invalid job ID format."""
        response = await client.get("/api/v2/generate/job/not-a-uuid/status")

        assert response.status_code == 400
        assert "invalid" in response.json()["detail"].lower()


class TestAsyncCompileEndpoint:
    """Tests for async mode in POST /api/v2/generate/compile endpoint."""

    @pytest.mark.asyncio
    async def test_sync_compile_still_works(self, client: AsyncClient):
        """Test sync compile (async_mode=false) still works."""
        # Simple valid schema
        schema = {
            "exterior": {
                "width": {"value": 100, "unit": "mm"},
                "depth": {"value": 80, "unit": "mm"},
                "height": {"value": 50, "unit": "mm"},
            },
            "wall_thickness": {"value": 2, "unit": "mm"},
        }

        response = await client.post(
            "/api/v2/generate/compile",
            json={
                "enclosure_schema": schema,
                "export_format": "step",
                "async_mode": False,
            },
        )

        # Should return GenerateV2Response (sync)
        assert response.status_code == 200
        data = response.json()
        assert "job_id" in data
        assert "success" in data

    @pytest.mark.asyncio
    async def test_async_compile_validation_error_returns_sync(
        self,
        client: AsyncClient,
    ):
        """Test async compile with invalid schema returns sync error."""
        # Invalid schema - missing required fields
        schema = {"invalid": "schema"}

        response = await client.post(
            "/api/v2/generate/compile",
            json={
                "enclosure_schema": schema,
                "export_format": "step",
                "async_mode": True,
            },
        )

        # Validation errors should be returned immediately, not queued
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
        assert len(data["errors"]) > 0
