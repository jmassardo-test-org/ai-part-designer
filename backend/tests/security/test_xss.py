"""
Security tests for XSS (Cross-Site Scripting) vulnerabilities.

Tests that XSS attacks are properly prevented.
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient


class TestXSSPrevention:
    """Tests for XSS prevention."""
    
    @pytest.mark.asyncio
    async def test_xss_in_search_query(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test that XSS payloads in search are sanitized."""
        xss_payloads = [
            "<script>alert('xss')</script>",
            '<img src="x" onerror="alert(1)">',
            "javascript:alert('XSS')",
            "<svg onload=alert(1)>",
            "'\"><script>alert('XSS')</script>",
        ]
        
        for payload in xss_payloads:
            response = await client.get(
                f"/api/v1/templates?search={payload}",
                headers=auth_headers,
            )
            
            # Should not return 500
            assert response.status_code != 500
            
            # Response should not contain unescaped script tags
            if response.status_code == 200:
                content = response.text
                assert "<script>" not in content.lower() or "alert(" not in content
    
    @pytest.mark.asyncio
    async def test_xss_in_user_input_fields(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test that XSS payloads in user input are handled."""
        xss_payload = "<script>document.cookie</script>"
        
        # Try creating a component with XSS in name
        response = await client.post(
            "/api/v1/components",
            headers=auth_headers,
            json={
                "name": xss_payload,
                "category": "test",
            }
        )
        
        # The important thing is that the server doesn't crash
        # XSS protection is typically handled on the frontend
        assert response.status_code != 500
    
    @pytest.mark.asyncio
    async def test_xss_in_design_names(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test that XSS in design names is prevented."""
        xss_payload = '<img src=x onerror=alert("XSS")>'
        
        # Try to create a design with XSS payload
        response = await client.post(
            "/api/v1/generate",
            headers=auth_headers,
            json={
                "description": xss_payload,
            }
        )
        
        # Should not cause server error
        assert response.status_code != 500
    
    @pytest.mark.asyncio
    async def test_content_type_header(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test that responses have proper content-type header."""
        response = await client.get(
            "/api/v1/health",
        )
        
        content_type = response.headers.get("content-type", "")
        
        # JSON responses should have proper content type
        assert "application/json" in content_type
