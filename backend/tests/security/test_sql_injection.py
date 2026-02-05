"""
Security tests for SQL injection vulnerabilities.

Tests that SQL injection attacks are properly prevented.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from httpx import AsyncClient


class TestSQLInjection:
    """Tests for SQL injection prevention."""

    @pytest.mark.asyncio
    async def test_sql_injection_in_search_params(self, client: AsyncClient, auth_headers: dict):
        """Test that SQL injection in search params is prevented."""
        # Common SQL injection payloads
        payloads = [
            "' OR '1'='1",
            "'; DROP TABLE users; --",
            "1' OR '1'='1' --",
            "admin'--",
            "' UNION SELECT * FROM users --",
        ]

        for payload in payloads:
            response = await client.get(
                f"/api/v1/templates?search={payload}",
                headers=auth_headers,
            )

            # Should not return a 500 error (which would indicate unhandled SQL)
            assert response.status_code != 500, (
                f"SQL injection payload caused server error: {payload}"
            )
            # Should return 200 or 400/422
            assert response.status_code in [200, 400, 422], (
                f"Unexpected status code for SQL injection test: {response.status_code}"
            )

    @pytest.mark.asyncio
    async def test_sql_injection_in_filter_params(self, client: AsyncClient, auth_headers: dict):
        """Test that SQL injection in filter params is prevented."""
        payloads = [
            "enclosures' OR '1'='1",
            "'; DELETE FROM templates; --",
        ]

        for payload in payloads:
            response = await client.get(
                f"/api/v1/templates?category={payload}",
                headers=auth_headers,
            )

            assert response.status_code != 500

    @pytest.mark.asyncio
    async def test_sql_injection_in_order_by(self, client: AsyncClient, auth_headers: dict):
        """Test that SQL injection in sort params is prevented."""
        payloads = [
            "name; DROP TABLE users",
            "(SELECT password FROM users)",
        ]

        for payload in payloads:
            response = await client.get(
                f"/api/v1/templates?sort={payload}",
                headers=auth_headers,
            )

            # Should either succeed or return validation error
            assert response.status_code in [200, 400, 422]

    @pytest.mark.asyncio
    async def test_sql_injection_in_id_params(self, client: AsyncClient, auth_headers: dict):
        """Test that SQL injection in ID parameters is prevented."""
        payloads = [
            "1' OR '1'='1",
            "00000000-0000-0000-0000-000000000000' OR 1=1 --",
        ]

        for payload in payloads:
            response = await client.get(
                f"/api/v1/templates/{payload}",
                headers=auth_headers,
            )

            # Should return 404 or 422, not 500
            assert response.status_code in [404, 422], (
                f"Unexpected status for ID injection: {response.status_code}"
            )
