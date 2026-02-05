"""
Tests for health check endpoints.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, patch

import pytest

if TYPE_CHECKING:
    from httpx import AsyncClient


class TestHealthEndpoints:
    """Tests for health check endpoints."""

    @pytest.mark.asyncio
    async def test_health_check(self, client: AsyncClient):
        """Test basic health check."""
        response = await client.get("/api/v1/health")

        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "healthy"
        assert "version" in data
        assert "environment" in data
        assert "timestamp" in data

    @pytest.mark.asyncio
    async def test_readiness_check(self, client: AsyncClient):
        """Test readiness check endpoint."""
        # Mock dependencies - patch at the source module
        with patch("app.core.database.async_session_maker") as mock_db:
            mock_session = AsyncMock()
            mock_session.execute = AsyncMock()
            mock_db.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_db.return_value.__aexit__ = AsyncMock()

            with patch("app.core.cache.get_redis") as mock_redis:
                mock_redis_client = AsyncMock()
                mock_redis_client.ping = AsyncMock()
                mock_redis.return_value = mock_redis_client

                response = await client.get("/api/v1/ready")

        assert response.status_code == 200
        data = response.json()

        assert "status" in data
        assert "checks" in data
        assert "timestamp" in data

    @pytest.mark.asyncio
    async def test_service_info(self, client: AsyncClient):
        """Test service info endpoint."""
        response = await client.get("/api/v1/info")

        assert response.status_code == 200
        data = response.json()

        assert "name" in data
        assert "version" in data
        assert "environment" in data
        assert "features" in data

    @pytest.mark.asyncio
    async def test_health_returns_correct_app_name(self, client: AsyncClient):
        """Test that health endpoint returns AssemblematicAI branding."""
        response = await client.get("/api/v1/info")

        assert response.status_code == 200
        data = response.json()

        # Should contain the new brand name
        assert "name" in data
        assert "Assemblematic" in data["name"] or "assemblematic" in data["name"].lower()
