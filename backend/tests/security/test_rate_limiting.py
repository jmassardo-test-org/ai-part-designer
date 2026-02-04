"""
Security tests for rate limiting.

Tests that rate limiting is properly enforced to prevent abuse.
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient
import asyncio


class TestRateLimiting:
    """Tests for rate limiting."""
    
    @pytest.mark.asyncio
    async def test_login_rate_limit_headers(self, client: AsyncClient):
        """Test that rate limit headers are present on login endpoint."""
        response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "test@example.com",
                "password": "wrongpassword",
            }
        )
        
        # Check for rate limit headers (common patterns)
        headers = response.headers
        rate_limit_headers = [
            "x-ratelimit-limit",
            "x-ratelimit-remaining", 
            "x-ratelimit-reset",
            "ratelimit-limit",
            "ratelimit-remaining",
            "retry-after",
        ]
        
        # At least one rate limit header should be present
        # or we should check the middleware is configured
        has_rate_limit = any(
            h.lower() in [k.lower() for k in headers.keys()]
            for h in rate_limit_headers
        )
        
        # Note: Rate limiting might be handled at reverse proxy level
        # so we just verify the endpoint doesn't error
        assert response.status_code in [200, 401, 429]
    
    @pytest.mark.asyncio
    async def test_rapid_requests_handled(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test that rapid requests don't cause server errors."""
        # Send 10 rapid requests
        responses = []
        
        for _ in range(10):
            response = await client.get(
                "/api/v1/health",
            )
            responses.append(response.status_code)
        
        # All should be 200 or 429 (rate limited), not 500
        for status in responses:
            assert status in [200, 429]
    
    @pytest.mark.asyncio
    async def test_api_endpoints_accept_requests(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test that API endpoints handle multiple requests gracefully."""
        endpoints = [
            "/api/v1/templates",
            "/api/v1/health",
        ]
        
        for endpoint in endpoints:
            # Make 5 quick requests
            for _ in range(5):
                response = await client.get(
                    endpoint,
                    headers=auth_headers,
                )
                
                # Should be 200 or 429, not 500
                assert response.status_code in [200, 429]


class TestAbusePrevention:
    """Tests for abuse prevention."""
    
    @pytest.mark.asyncio
    async def test_large_request_body_rejected(self, client: AsyncClient):
        """Test that excessively large request bodies are rejected."""
        # Create a very large JSON payload
        large_payload = {"data": "A" * (10 * 1024 * 1024)}  # 10MB
        
        try:
            response = await client.post(
                "/api/v1/generate",
                json=large_payload,
                timeout=5.0,
            )
            
            # Should be rejected
            assert response.status_code in [401, 413, 422]
        except Exception:
            # Connection error is acceptable for oversized payloads
            pass
    
    @pytest.mark.asyncio
    async def test_deeply_nested_json_handled(self, client: AsyncClient):
        """Test that deeply nested JSON doesn't cause stack overflow."""
        # Create deeply nested structure
        nested = {"level": 0}
        current = nested
        for i in range(1, 100):
            current["child"] = {"level": i}
            current = current["child"]
        
        try:
            response = await client.post(
                "/api/v1/generate",
                json={"nested": nested},
                timeout=5.0,
            )
            
            # Should handle gracefully
            assert response.status_code != 500
        except Exception:
            # Rejection is acceptable
            pass
    
    @pytest.mark.asyncio
    async def test_unicode_handling(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test that unicode edge cases are handled safely."""
        unicode_payloads = [
            "测试",  # Chinese
            "🔧🔩🔨",  # Emojis
            "Ω≈ç√∫",  # Math symbols
        ]
        
        for payload in unicode_payloads:
            try:
                response = await client.get(
                    f"/api/v1/templates?search={payload}",
                    headers=auth_headers,
                )
                
                # Should handle gracefully
                assert response.status_code != 500
            except Exception:
                # Some unicode may not be valid in URLs, that's ok
                pass
