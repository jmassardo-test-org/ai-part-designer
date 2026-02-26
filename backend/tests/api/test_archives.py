"""
Tests for admin archive API endpoints.

Tests listing, restoring, and deleting archived designs
with proper authentication and authorization checks.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

from tests.factories import Counter, DesignFactory, ProjectFactory, UserFactory

if TYPE_CHECKING:
    from httpx import AsyncClient
    from sqlalchemy.ext.asyncio import AsyncSession


@pytest.fixture(autouse=True)
def reset_counters():
    """Reset factory counters before each test."""
    Counter.reset()


@pytest.mark.asyncio
class TestArchiveEndpoints:
    """Tests for admin archive API endpoints."""

    async def test_list_archives_requires_admin(
        self, client: AsyncClient, auth_headers: dict
    ) -> None:
        """Non-admin users get 403 when listing archives."""
        response = await client.get(
            "/api/v1/admin/archives/designs",
            headers=auth_headers,
        )
        assert response.status_code == 403

    async def test_list_archives_returns_paginated_results(
        self,
        client: AsyncClient,
        admin_headers: dict,
        db_session: AsyncSession,
    ) -> None:
        """Admin can list archived designs with pagination."""
        user = await UserFactory.create(db_session)
        project = await ProjectFactory.create(db_session, user=user)

        # Create archived designs
        for i in range(3):
            await DesignFactory.create(
                db_session,
                user=user,
                project=project,
                status="archived",
                archived_at=datetime.now(tz=UTC) - timedelta(hours=i),
                archive_location=f"designs/test/{i}",
            )

        response = await client.get(
            "/api/v1/admin/archives/designs?page=1&per_page=2",
            headers=admin_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 3
        assert len(data["items"]) == 2
        assert data["page"] == 1
        assert data["per_page"] == 2
        assert data["pages"] == 2

    async def test_restore_archive_success(
        self,
        client: AsyncClient,
        admin_headers: dict,
        db_session: AsyncSession,
    ) -> None:
        """Admin can restore an archived design."""
        design = await DesignFactory.create(
            db_session,
            status="archived",
            archived_at=datetime.now(tz=UTC),
            archive_location="designs/test/20260224_100000",
        )

        with patch("app.services.design_archive.storage_client") as mock_storage:
            mock_storage.list_files = AsyncMock(return_value=[])
            mock_storage.copy_file = AsyncMock()

            response = await client.post(
                f"/api/v1/admin/archives/designs/{design.id}/restore",
                headers=admin_headers,
            )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(design.id)
        assert data["status"] == "ready"
        assert "restored_at" in data

    async def test_restore_archive_not_found(
        self,
        client: AsyncClient,
        admin_headers: dict,
    ) -> None:
        """Restoring a non-existent design returns 404."""
        response = await client.post(
            f"/api/v1/admin/archives/designs/{uuid4()}/restore",
            headers=admin_headers,
        )
        assert response.status_code == 404

    async def test_delete_archive_success(
        self,
        client: AsyncClient,
        admin_headers: dict,
        db_session: AsyncSession,
    ) -> None:
        """Admin can permanently delete an archived design."""
        design = await DesignFactory.create(
            db_session,
            status="archived",
            archived_at=datetime.now(tz=UTC),
            archive_location="designs/test/20260224_100000",
        )

        with patch("app.services.design_archive.storage_client") as mock_storage:
            mock_storage.list_files = AsyncMock(return_value=[])
            mock_storage.delete_files = AsyncMock(return_value=0)

            response = await client.delete(
                f"/api/v1/admin/archives/designs/{design.id}",
                headers=admin_headers,
            )

        assert response.status_code == 204

    async def test_delete_archive_not_found(
        self,
        client: AsyncClient,
        admin_headers: dict,
    ) -> None:
        """Deleting a non-existent archived design returns 404."""
        response = await client.delete(
            f"/api/v1/admin/archives/designs/{uuid4()}",
            headers=admin_headers,
        )
        assert response.status_code == 404

    async def test_regular_user_gets_403(self, client: AsyncClient, auth_headers: dict) -> None:
        """Regular user gets 403 on all archive endpoints."""
        fake_id = uuid4()

        list_resp = await client.get(
            "/api/v1/admin/archives/designs",
            headers=auth_headers,
        )
        assert list_resp.status_code == 403

        restore_resp = await client.post(
            f"/api/v1/admin/archives/designs/{fake_id}/restore",
            headers=auth_headers,
        )
        assert restore_resp.status_code == 403

        delete_resp = await client.delete(
            f"/api/v1/admin/archives/designs/{fake_id}",
            headers=auth_headers,
        )
        assert delete_resp.status_code == 403

    async def test_list_archives_empty_returns_empty_list(
        self,
        client: AsyncClient,
        admin_headers: dict,
    ) -> None:
        """Listing archives with no archived designs returns empty list."""
        response = await client.get(
            "/api/v1/admin/archives/designs",
            headers=admin_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["total"] == 0
        assert data["pages"] == 0
