"""
Tests for trash API endpoints.

Tests soft-deleted item management.
"""

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.design import Design
from app.models.project import Project

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
async def deleted_design(db_session: AsyncSession, test_user):
    """Create a soft-deleted design."""
    project = Project(
        id=uuid4(),
        user_id=test_user.id,
        name="Trash Test Project",
    )
    db_session.add(project)
    await db_session.flush()

    design = Design(
        id=uuid4(),
        user_id=test_user.id,
        project_id=project.id,
        name="Deleted Design",
        status="completed",
        deleted_at=datetime.now(UTC),  # Soft deleted
    )
    db_session.add(design)
    await db_session.commit()
    await db_session.refresh(design)

    yield design

    try:
        await db_session.delete(design)
        await db_session.delete(project)
        await db_session.commit()
    except Exception:
        pass


# =============================================================================
# List Trash Tests
# =============================================================================


class TestListTrash:
    """Tests for listing trashed items."""

    async def test_list_trash_success(self, client: AsyncClient, auth_headers: dict):
        """Should return list of trashed items."""
        response = await client.get("/api/v1/trash", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert "items" in data or isinstance(data, list)

    async def test_list_trash_unauthenticated(self, client: AsyncClient):
        """Should return 401 without authentication."""
        response = await client.get("/api/v1/trash")
        assert response.status_code == 401


# =============================================================================
# Restore Tests
# =============================================================================


class TestRestoreTrash:
    """Tests for restoring trashed items."""

    async def test_restore_design_not_found(self, client: AsyncClient, auth_headers: dict):
        """Should return 404 for non-existent item."""
        response = await client.post(
            "/api/v1/trash/00000000-0000-0000-0000-000000000000/restore", headers=auth_headers
        )

        assert response.status_code == 404


# =============================================================================
# Permanent Delete Tests
# =============================================================================


class TestPermanentDelete:
    """Tests for permanently deleting items."""

    async def test_permanent_delete_not_found(self, client: AsyncClient, auth_headers: dict):
        """Should return 404 for non-existent item."""
        response = await client.delete(
            "/api/v1/trash/00000000-0000-0000-0000-000000000000", headers=auth_headers
        )

        assert response.status_code == 404
