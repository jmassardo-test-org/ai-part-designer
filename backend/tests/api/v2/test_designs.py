"""
Tests for v2 designs API endpoints.

These tests use the auth_client fixture which provides proper JWT authentication
and database session management.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy import select

from app.models.design import Design
from app.models.job import Job
from app.models.project import Project

if TYPE_CHECKING:
    from httpx import AsyncClient
    from sqlalchemy.ext.asyncio import AsyncSession


@pytest_asyncio.fixture
async def test_project(db_session: AsyncSession, test_user) -> Project:
    """Create a test project for the test user."""
    project = Project(
        user_id=test_user.id,
        name="Test Project",
        description="A test project for v2 designs",
    )
    db_session.add(project)
    await db_session.commit()
    await db_session.refresh(project)
    return project


@pytest_asyncio.fixture
async def test_completed_job(db_session: AsyncSession, test_user, test_project) -> Job:
    """Create a completed job for testing save design."""
    job = Job(
        user_id=test_user.id,
        job_type="cad_compile",
        status="completed",
        input_params={
            "description": "Test enclosure for Arduino Nano",
            "export_format": "step",
        },
        result={
            "generated_schema": {
                "exterior": {
                    "width": {"value": 100},
                    "depth": {"value": 80},
                    "height": {"value": 50},
                },
            },
            "parts": ["body", "lid"],
            "downloads": {
                "body": "/api/v2/downloads/test-job/body.step",
                "lid": "/api/v2/downloads/test-job/lid.step",
            },
            "warnings": [],
        },
    )
    db_session.add(job)
    await db_session.commit()
    await db_session.refresh(job)
    return job


@pytest_asyncio.fixture
async def test_pending_job(db_session: AsyncSession, test_user) -> Job:
    """Create a pending (non-completed) job for testing error cases."""
    job = Job(
        user_id=test_user.id,
        job_type="cad_compile",
        status="processing",
        input_params={"description": "Test"},
    )
    db_session.add(job)
    await db_session.commit()
    await db_session.refresh(job)
    return job


@pytest_asyncio.fixture
async def test_design(db_session: AsyncSession, test_project, test_completed_job, test_user) -> Design:
    """Create a test design."""
    design = Design(
        project_id=test_project.id,
        user_id=test_user.id,  # Required field
        name="Existing Test Design",
        description="An existing design for testing",
        source_type="v2_generated",
        status="ready",
        tags=["test", "arduino"],
        extra_data={
            "job_id": str(test_completed_job.id),
            "enclosure_spec": test_completed_job.result.get("generated_schema"),
        },
    )
    db_session.add(design)
    await db_session.commit()
    await db_session.refresh(design)
    return design


class TestSaveDesignV2:
    """Tests for POST /api/v2/designs/save endpoint."""

    @pytest.mark.asyncio
    async def test_save_design_success(
        self,
        auth_client: AsyncClient,
        test_completed_job: Job,
        test_project: Project,
    ):
        """Test successfully saving a design from a completed job."""
        response = await auth_client.post(
            "/api/v2/designs/save",
            json={
                "job_id": str(test_completed_job.id),
                "name": "My Arduino Case",
                "description": "Custom case for Arduino Nano",
                "project_id": str(test_project.id),
                "tags": ["arduino", "custom"],
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "My Arduino Case"
        assert data["description"] == "Custom case for Arduino Nano"
        assert data["source_type"] == "v2_generated"
        assert data["status"] == "ready"
        assert "arduino" in data["tags"]
        assert "custom" in data["tags"]
        assert data["project_id"] == str(test_project.id)
        assert "id" in data
        assert "created_at" in data

    @pytest.mark.asyncio
    async def test_save_design_creates_default_project(
        self,
        auth_client: AsyncClient,
        test_completed_job: Job,
        db_session: AsyncSession,
        test_user,
    ):
        """Test that saving a design creates a default project if none specified."""
        response = await auth_client.post(
            "/api/v2/designs/save",
            json={
                "job_id": str(test_completed_job.id),
                "name": "My Arduino Case",
            },
        )

        assert response.status_code == 201
        data = response.json()

        # Verify a default project was created
        result = await db_session.execute(
            select(Project).where(
                Project.user_id == test_user.id,
                Project.name == "My Designs",
            )
        )
        default_project = result.scalar_one_or_none()
        assert default_project is not None
        assert data["project_id"] == str(default_project.id)

    @pytest.mark.asyncio
    async def test_save_design_invalid_job_id_format(self, auth_client: AsyncClient):
        """Test saving with invalid job_id format returns 400."""
        response = await auth_client.post(
            "/api/v2/designs/save",
            json={
                "job_id": "not-a-valid-uuid",
                "name": "Test Design",
            },
        )

        assert response.status_code == 400
        assert "Invalid job_id format" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_save_design_job_not_found(self, auth_client: AsyncClient):
        """Test saving with non-existent job returns 404."""
        response = await auth_client.post(
            "/api/v2/designs/save",
            json={
                "job_id": str(uuid4()),
                "name": "Test Design",
            },
        )

        assert response.status_code == 404
        assert "Job not found" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_save_design_job_not_completed(
        self,
        auth_client: AsyncClient,
        test_pending_job: Job,
    ):
        """Test saving with incomplete job returns 400."""
        response = await auth_client.post(
            "/api/v2/designs/save",
            json={
                "job_id": str(test_pending_job.id),
                "name": "Test Design",
            },
        )

        assert response.status_code == 400
        assert "not completed" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_save_design_unauthenticated(self, client: AsyncClient):
        """Test saving without authentication returns 401."""
        response = await client.post(
            "/api/v2/designs/save",
            json={
                "job_id": str(uuid4()),
                "name": "Test Design",
            },
        )

        assert response.status_code == 401


class TestGetDesignV2:
    """Tests for GET /api/v2/designs/{design_id} endpoint."""

    @pytest.mark.asyncio
    async def test_get_design_success(
        self,
        auth_client: AsyncClient,
        test_design: Design,
    ):
        """Test successfully getting an existing design."""
        response = await auth_client.get(f"/api/v2/designs/{test_design.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(test_design.id)
        assert data["name"] == test_design.name
        assert data["description"] == test_design.description

    @pytest.mark.asyncio
    async def test_get_design_not_found(self, auth_client: AsyncClient):
        """Test getting non-existent design returns 404."""
        response = await auth_client.get(f"/api/v2/designs/{uuid4()}")

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_design_unauthenticated(self, client: AsyncClient):
        """Test getting design without authentication returns 401."""
        response = await client.get(f"/api/v2/designs/{uuid4()}")

        assert response.status_code == 401


class TestListDesignsV2:
    """Tests for GET /api/v2/designs/ endpoint."""

    @pytest.mark.asyncio
    async def test_list_designs_empty(self, auth_client: AsyncClient):
        """Test listing designs when none exist."""
        response = await auth_client.get("/api/v2/designs/")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["designs"] == []
        assert data["page"] == 1
        assert data["per_page"] == 20

    @pytest.mark.asyncio
    async def test_list_designs_with_data(
        self,
        auth_client: AsyncClient,
        test_design: Design,
    ):
        """Test listing designs returns existing designs."""
        response = await auth_client.get("/api/v2/designs/")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert len(data["designs"]) == 1
        assert data["designs"][0]["id"] == str(test_design.id)
        assert data["designs"][0]["name"] == test_design.name

    @pytest.mark.asyncio
    async def test_list_designs_pagination(
        self,
        auth_client: AsyncClient,
        test_design: Design,
        db_session: AsyncSession,
        test_project: Project,
        test_user,
    ):
        """Test pagination parameters work correctly."""
        # Create additional designs
        for i in range(5):
            design = Design(
                project_id=test_project.id,
                user_id=test_user.id,
                name=f"Design {i}",
                source_type="v2_generated",
                status="ready",
            )
            db_session.add(design)
        await db_session.commit()

        # Test page size limit
        response = await auth_client.get("/api/v2/designs/?per_page=2")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 6  # 1 from fixture + 5 created
        assert len(data["designs"]) == 2
        assert data["per_page"] == 2

        # Test page 2
        response = await auth_client.get("/api/v2/designs/?page=2&per_page=2")
        assert response.status_code == 200
        data = response.json()
        assert len(data["designs"]) == 2
        assert data["page"] == 2

    @pytest.mark.asyncio
    async def test_list_designs_filter_by_project(
        self,
        auth_client: AsyncClient,
        test_design: Design,
        test_project: Project,
        db_session: AsyncSession,
        test_user,
    ):
        """Test filtering designs by project_id."""
        # Create another project with a design
        other_project = Project(
            user_id=test_user.id,
            name="Other Project",
        )
        db_session.add(other_project)
        await db_session.commit()
        await db_session.refresh(other_project)

        other_design = Design(
            project_id=other_project.id,
            user_id=test_user.id,
            name="Other Design",
            source_type="v2_generated",
            status="ready",
        )
        db_session.add(other_design)
        await db_session.commit()

        # Filter by test_project
        response = await auth_client.get(f"/api/v2/designs/?project_id={test_project.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["designs"][0]["id"] == str(test_design.id)

    @pytest.mark.asyncio
    async def test_list_designs_unauthenticated(self, client: AsyncClient):
        """Test listing designs without authentication returns 401."""
        response = await client.get("/api/v2/designs/")

        assert response.status_code == 401
