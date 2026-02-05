"""
Security tests for authorization vulnerabilities.

Tests for privilege escalation and access control.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import uuid4

import pytest

if TYPE_CHECKING:
    from httpx import AsyncClient


class TestAuthorization:
    """Tests for authorization and access control."""

    @pytest.mark.asyncio
    async def test_user_cannot_access_other_user_data(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test that users cannot access other users' data."""
        # Try to access a random user's data
        fake_user_id = uuid4()

        response = await client.get(f"/api/v1/users/{fake_user_id}", headers=auth_headers)

        # Should return 404 or 403, not the user's data
        assert response.status_code in [403, 404]

    @pytest.mark.asyncio
    async def test_user_cannot_access_other_user_projects(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test that users cannot access other users' projects."""
        fake_project_id = uuid4()

        response = await client.get(f"/api/v1/projects/{fake_project_id}", headers=auth_headers)

        # Should return 404 (not found for this user)
        assert response.status_code in [403, 404]

    @pytest.mark.asyncio
    async def test_user_cannot_modify_other_user_components(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test that users cannot modify other users' components."""
        fake_component_id = uuid4()

        response = await client.patch(
            f"/api/v1/components/{fake_component_id}",
            headers=auth_headers,
            json={"name": "Hacked Component"},
        )

        # Should return 404 or 403
        assert response.status_code in [403, 404, 405]

    @pytest.mark.asyncio
    async def test_user_cannot_access_admin_endpoints(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test that regular users cannot access admin endpoints."""
        admin_endpoints = [
            "/api/v1/admin/users",
            "/api/v1/admin/analytics",
            "/api/v1/admin/jobs",
        ]

        for endpoint in admin_endpoints:
            response = await client.get(endpoint, headers=auth_headers)

            # Should return 403 (forbidden) or 404 if not implemented
            assert response.status_code in [401, 403, 404]

    @pytest.mark.asyncio
    async def test_user_cannot_delete_other_user_data(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test that users cannot delete other users' data."""
        fake_design_id = uuid4()

        response = await client.delete(f"/api/v1/designs/{fake_design_id}", headers=auth_headers)

        # Should return 404 or 403
        assert response.status_code in [403, 404]


class TestRoleEscalation:
    """Tests for privilege escalation prevention."""

    @pytest.mark.asyncio
    async def test_user_cannot_change_own_role(self, client: AsyncClient, auth_headers: dict):
        """Test that users cannot elevate their own role."""
        response = await client.patch(
            "/api/v1/users/me", headers=auth_headers, json={"role": "admin"}
        )

        # Should either be rejected or role field ignored
        if response.status_code == 200:
            data = response.json()
            assert data.get("role") != "admin"

    @pytest.mark.asyncio
    async def test_user_cannot_change_own_tier(self, client: AsyncClient, auth_headers: dict):
        """Test that users cannot change their subscription tier directly."""
        response = await client.patch(
            "/api/v1/users/me", headers=auth_headers, json={"tier": "enterprise"}
        )

        # Should either be rejected or tier field ignored
        if response.status_code == 200:
            data = response.json()
            assert data.get("tier") != "enterprise"


class TestResourceIsolation:
    """Tests for proper resource isolation."""

    @pytest.mark.asyncio
    async def test_design_ids_not_predictable(self, client: AsyncClient, auth_headers: dict):
        """Test that design IDs are UUIDs and not sequential."""
        # Get user's designs
        response = await client.get("/api/v1/designs", headers=auth_headers)

        if response.status_code == 200:
            data = response.json()
            items = data.get("items", data.get("designs", [])) if isinstance(data, dict) else data

            if items and isinstance(items, list) and len(items) > 0:
                # Check that IDs look like UUIDs
                first_id = str(items[0].get("id", ""))
                assert len(first_id) == 36 or len(first_id) == 32  # UUID format
