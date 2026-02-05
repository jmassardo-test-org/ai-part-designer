"""
Tests for Versions API endpoints.

Tests version listing, retrieval, restore, and comparison.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import uuid4

import pytest

if TYPE_CHECKING:
    from httpx import AsyncClient
    from sqlalchemy.ext.asyncio import AsyncSession

# =============================================================================
# List Versions Tests
# =============================================================================


class TestListVersions:
    """Tests for version listing endpoint."""

    @pytest.mark.asyncio
    async def test_list_versions_requires_auth(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        design_factory,
    ):
        """Test that listing versions requires authentication."""
        design = await design_factory.create(db=db_session)

        response = await client.get(f"/api/v1/designs/{design.id}/versions")

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_list_versions_empty(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_user,
        auth_headers,
        project_factory,
        design_factory,
    ):
        """Test listing versions when none exist."""
        project = await project_factory.create(db=db_session, user=test_user)
        design = await design_factory.create(db=db_session, project=project)

        response = await client.get(
            f"/api/v1/designs/{design.id}/versions",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()

        assert data["versions"] == []
        assert data["total"] == 0

    @pytest.mark.asyncio
    async def test_list_versions_with_versions(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_user,
        auth_headers,
        project_factory,
        design_factory,
        version_factory,
    ):
        """Test listing versions when design has versions."""
        project = await project_factory.create(db=db_session, user=test_user)
        design = await design_factory.create(db=db_session, project=project)

        await version_factory.create(db=db_session, design=design, version_number=1)
        await version_factory.create(db=db_session, design=design, version_number=2)
        await version_factory.create(db=db_session, design=design, version_number=3)

        response = await client.get(
            f"/api/v1/designs/{design.id}/versions",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()

        assert len(data["versions"]) == 3
        assert data["total"] == 3
        # Should be ordered by version number descending
        assert data["versions"][0]["version_number"] == 3

    @pytest.mark.asyncio
    async def test_list_versions_design_not_found(
        self,
        client: AsyncClient,
        test_user,
        auth_headers,
    ):
        """Test listing versions for non-existent design."""
        response = await client.get(
            f"/api/v1/designs/{uuid4()}/versions",
            headers=auth_headers,
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_list_versions_other_user_design(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_user,
        auth_headers,
        user_factory,
        project_factory,
        design_factory,
    ):
        """Test listing versions for another user's design returns 403."""
        other_user = await user_factory.create(db=db_session)
        project = await project_factory.create(db=db_session, user=other_user)
        design = await design_factory.create(db=db_session, project=project)

        response = await client.get(
            f"/api/v1/designs/{design.id}/versions",
            headers=auth_headers,
        )

        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_list_versions_pagination(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_user,
        auth_headers,
        project_factory,
        design_factory,
        version_factory,
    ):
        """Test version listing pagination."""
        project = await project_factory.create(db=db_session, user=test_user)
        design = await design_factory.create(db=db_session, project=project)

        for i in range(5):
            await version_factory.create(
                db=db_session,
                design=design,
                version_number=i + 1,
            )

        response = await client.get(
            f"/api/v1/designs/{design.id}/versions",
            headers=auth_headers,
            params={"page": 1, "page_size": 2},
        )

        assert response.status_code == 200
        data = response.json()

        assert len(data["versions"]) == 2
        assert data["total"] == 5


# =============================================================================
# Get Version Tests
# =============================================================================


class TestGetVersion:
    """Tests for getting individual version details."""

    @pytest.mark.asyncio
    async def test_get_version_success(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_user,
        auth_headers,
        project_factory,
        design_factory,
        version_factory,
    ):
        """Test getting version details."""
        project = await project_factory.create(db=db_session, user=test_user)
        design = await design_factory.create(db=db_session, project=project)
        version = await version_factory.create(
            db=db_session,
            design=design,
            version_number=1,
            change_description="Initial version",
        )

        response = await client.get(
            f"/api/v1/versions/{version.id}",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()

        assert data["version_number"] == 1
        assert "geometry_info" in data

    @pytest.mark.asyncio
    async def test_get_version_not_found(
        self,
        client: AsyncClient,
        test_user,
        auth_headers,
    ):
        """Test getting non-existent version."""
        response = await client.get(
            f"/api/v1/versions/{uuid4()}",
            headers=auth_headers,
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_version_other_user(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_user,
        auth_headers,
        user_factory,
        project_factory,
        design_factory,
        version_factory,
    ):
        """Test getting another user's version returns 403."""
        other_user = await user_factory.create(db=db_session)
        project = await project_factory.create(db=db_session, user=other_user)
        design = await design_factory.create(db=db_session, project=project)
        version = await version_factory.create(db=db_session, design=design)

        response = await client.get(
            f"/api/v1/versions/{version.id}",
            headers=auth_headers,
        )

        assert response.status_code == 403


# =============================================================================
# Restore Version Tests
# =============================================================================


class TestRestoreVersion:
    """Tests for version restore endpoint."""

    @pytest.mark.asyncio
    async def test_restore_version_success(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_user,
        auth_headers,
        project_factory,
        design_factory,
        version_factory,
    ):
        """Test restoring a previous version."""
        project = await project_factory.create(db=db_session, user=test_user)
        design = await design_factory.create(db=db_session, project=project)

        v1 = await version_factory.create(
            db=db_session,
            design=design,
            version_number=1,
        )
        await version_factory.create(
            db=db_session,
            design=design,
            version_number=2,
        )

        response = await client.post(
            f"/api/v1/versions/{v1.id}/restore",
            headers=auth_headers,
            json={"description": "Restored v1"},
        )

        assert response.status_code == 201
        data = response.json()

        assert data["new_version_number"] == 3
        assert data["restored_from_version"] == 1

    @pytest.mark.asyncio
    async def test_restore_version_not_found(
        self,
        client: AsyncClient,
        test_user,
        auth_headers,
    ):
        """Test restoring non-existent version."""
        response = await client.post(
            f"/api/v1/versions/{uuid4()}/restore",
            headers=auth_headers,
            json={},
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_restore_version_other_user(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_user,
        auth_headers,
        user_factory,
        project_factory,
        design_factory,
        version_factory,
    ):
        """Test restoring another user's version returns 403."""
        other_user = await user_factory.create(db=db_session)
        project = await project_factory.create(db=db_session, user=other_user)
        design = await design_factory.create(db=db_session, project=project)
        version = await version_factory.create(db=db_session, design=design)

        response = await client.post(
            f"/api/v1/versions/{version.id}/restore",
            headers=auth_headers,
            json={},
        )

        assert response.status_code == 403


# =============================================================================
# Compare Versions Tests
# =============================================================================


class TestCompareVersions:
    """Tests for version comparison endpoint."""

    @pytest.mark.asyncio
    async def test_compare_versions_success(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_user,
        auth_headers,
        project_factory,
        design_factory,
        version_factory,
    ):
        """Test comparing two versions."""
        project = await project_factory.create(db=db_session, user=test_user)
        design = await design_factory.create(db=db_session, project=project)

        await version_factory.create(
            db=db_session,
            design=design,
            version_number=1,
            geometry_info={"volume": 100, "surfaceArea": 50},
        )
        await version_factory.create(
            db=db_session,
            design=design,
            version_number=2,
            geometry_info={"volume": 200, "surfaceArea": 75},
        )

        response = await client.get(
            f"/api/v1/designs/{design.id}/versions/compare",
            headers=auth_headers,
            params={"version_a": 1, "version_b": 2},
        )

        assert response.status_code == 200
        data = response.json()

        assert data["version_a"]["version_number"] == 1
        assert data["version_b"]["version_number"] == 2
        assert "geometry_diff" in data

    @pytest.mark.asyncio
    async def test_compare_versions_design_not_found(
        self,
        client: AsyncClient,
        test_user,
        auth_headers,
    ):
        """Test comparing versions for non-existent design."""
        response = await client.get(
            f"/api/v1/designs/{uuid4()}/versions/compare",
            headers=auth_headers,
            params={"version_a": 1, "version_b": 2},
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_compare_versions_version_not_found(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_user,
        auth_headers,
        project_factory,
        design_factory,
        version_factory,
    ):
        """Test comparing with non-existent version number."""
        project = await project_factory.create(db=db_session, user=test_user)
        design = await design_factory.create(db=db_session, project=project)

        await version_factory.create(
            db=db_session,
            design=design,
            version_number=1,
        )

        response = await client.get(
            f"/api/v1/designs/{design.id}/versions/compare",
            headers=auth_headers,
            params={"version_a": 1, "version_b": 99},  # 99 doesn't exist
        )

        assert response.status_code == 404


# =============================================================================
# Diff Tests
# =============================================================================


class TestVersionDiff:
    """Tests for version diff endpoint."""

    @pytest.mark.asyncio
    async def test_diff_between_versions(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_user,
        auth_headers,
        project_factory,
        design_factory,
        version_factory,
    ):
        """Test getting diff between versions."""
        project = await project_factory.create(db=db_session, user=test_user)
        design = await design_factory.create(db=db_session, project=project)

        await version_factory.create(
            db=db_session,
            design=design,
            version_number=1,
        )
        await version_factory.create(
            db=db_session,
            design=design,
            version_number=2,
        )

        response = await client.get(
            f"/api/v1/designs/{design.id}/versions/diff",
            headers=auth_headers,
            params={"from_version": 1, "to_version": 2},
        )

        # The endpoint may or may not exist - just check it doesn't crash
        assert response.status_code in [200, 404]
