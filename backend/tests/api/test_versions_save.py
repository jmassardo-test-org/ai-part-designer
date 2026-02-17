"""
Tests for POST /api/v1/designs/{design_id}/versions endpoint.

Tests the create-version-from-edit flow that saves an edited design
as a new version of the existing design.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import uuid4

import pytest

if TYPE_CHECKING:
    from httpx import AsyncClient
    from sqlalchemy.ext.asyncio import AsyncSession


class TestCreateVersionFromEdit:
    """Tests for the POST /designs/{design_id}/versions endpoint."""

    @pytest.mark.asyncio
    async def test_create_version_requires_auth(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        design_factory,
    ):
        """Test that creating a version requires authentication."""
        design = await design_factory.create(db=db_session)

        response = await client.post(
            f"/api/v1/designs/{design.id}/versions",
            json={
                "job_id": "test-job-123",
                "change_description": "Updated dimensions",
            },
        )

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_create_version_success(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_user,
        auth_headers,
        project_factory,
        design_factory,
    ):
        """Test successfully creating a version from an edit."""
        project = await project_factory.create(db=db_session, user=test_user)
        design = await design_factory.create(db=db_session, project=project)

        response = await client.post(
            f"/api/v1/designs/{design.id}/versions",
            headers=auth_headers,
            json={
                "job_id": "compile-job-456",
                "change_description": "Increased width from 120mm to 150mm",
            },
        )

        assert response.status_code == 201
        data = response.json()

        assert "version_id" in data
        assert data["version_number"] == 1
        assert data["design_id"] == str(design.id)
        assert "created successfully" in data["message"]

    @pytest.mark.asyncio
    async def test_create_version_with_parameters(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_user,
        auth_headers,
        project_factory,
        design_factory,
    ):
        """Test creating a version with parameters included."""
        project = await project_factory.create(db=db_session, user=test_user)
        design = await design_factory.create(db=db_session, project=project)

        response = await client.post(
            f"/api/v1/designs/{design.id}/versions",
            headers=auth_headers,
            json={
                "job_id": "compile-job-789",
                "change_description": "Added ventilation slots",
                "parameters": {
                    "width": 150,
                    "depth": 100,
                    "height": 60,
                    "ventilation": True,
                },
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["version_number"] == 1

    @pytest.mark.asyncio
    async def test_create_version_increments_version_number(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_user,
        auth_headers,
        project_factory,
        design_factory,
        version_factory,
    ):
        """Test that version number increments correctly."""
        project = await project_factory.create(db=db_session, user=test_user)
        design = await design_factory.create(db=db_session, project=project)

        # Create an initial version
        await version_factory.create(
            db=db_session, design=design, version_number=1
        )

        response = await client.post(
            f"/api/v1/designs/{design.id}/versions",
            headers=auth_headers,
            json={
                "job_id": "compile-job-inc",
                "change_description": "Second edit",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["version_number"] == 2

    @pytest.mark.asyncio
    async def test_create_version_nonexistent_design_returns_404(
        self,
        client: AsyncClient,
        auth_headers,
    ):
        """Test that a 404 is returned for a nonexistent design."""
        fake_id = uuid4()

        response = await client.post(
            f"/api/v1/designs/{fake_id}/versions",
            headers=auth_headers,
            json={
                "job_id": "job-xyz",
                "change_description": "Should not work",
            },
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_create_version_other_user_returns_403(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_user,
        test_user_2,
        auth_headers_2,
        project_factory,
        design_factory,
    ):
        """Test that another user cannot create a version on someone else's design."""
        project = await project_factory.create(db=db_session, user=test_user)
        design = await design_factory.create(db=db_session, project=project)

        response = await client.post(
            f"/api/v1/designs/{design.id}/versions",
            headers=auth_headers_2,
            json={
                "job_id": "job-hack",
                "change_description": "Unauthorized edit",
            },
        )

        # Should be 403 (access denied) or 404 (hidden)
        assert response.status_code in (403, 404)

    @pytest.mark.asyncio
    async def test_create_version_missing_job_id_returns_422(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_user,
        auth_headers,
        project_factory,
        design_factory,
    ):
        """Test that missing job_id returns a validation error."""
        project = await project_factory.create(db=db_session, user=test_user)
        design = await design_factory.create(db=db_session, project=project)

        response = await client.post(
            f"/api/v1/designs/{design.id}/versions",
            headers=auth_headers,
            json={
                "change_description": "Missing job_id",
            },
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_create_version_missing_description_returns_422(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_user,
        auth_headers,
        project_factory,
        design_factory,
    ):
        """Test that missing change_description returns a validation error."""
        project = await project_factory.create(db=db_session, user=test_user)
        design = await design_factory.create(db=db_session, project=project)

        response = await client.post(
            f"/api/v1/designs/{design.id}/versions",
            headers=auth_headers,
            json={
                "job_id": "some-job",
            },
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_create_version_empty_description_returns_422(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_user,
        auth_headers,
        project_factory,
        design_factory,
    ):
        """Test that empty change_description returns a validation error."""
        project = await project_factory.create(db=db_session, user=test_user)
        design = await design_factory.create(db=db_session, project=project)

        response = await client.post(
            f"/api/v1/designs/{design.id}/versions",
            headers=auth_headers,
            json={
                "job_id": "some-job",
                "change_description": "",
            },
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_create_version_with_file_url(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_user,
        auth_headers,
        project_factory,
        design_factory,
    ):
        """Test creating a version with an explicit file_url."""
        project = await project_factory.create(db=db_session, user=test_user)
        design = await design_factory.create(db=db_session, project=project)

        response = await client.post(
            f"/api/v1/designs/{design.id}/versions",
            headers=auth_headers,
            json={
                "job_id": "compile-job-url",
                "change_description": "Custom file URL",
                "file_url": "https://storage.example.com/custom-file.stl",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["version_number"] == 1
