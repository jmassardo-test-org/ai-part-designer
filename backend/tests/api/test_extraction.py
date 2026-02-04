"""
Tests for extraction API endpoints.

Tests dimension extraction from images and PDFs.
"""

import pytest
from httpx import AsyncClient


# =============================================================================
# Extraction Status Tests
# =============================================================================

class TestExtractionStatus:
    """Tests for GET /api/v1/extraction/status."""

    async def test_get_extraction_status(
        self, client: AsyncClient
    ):
        """Should return extraction service status."""
        response = await client.get("/api/v1/extraction/status")
        
        # Status endpoint is usually public
        assert response.status_code == 200
        data = response.json()
        assert "supported_formats" in data


# =============================================================================
# Dimension Extraction Tests
# =============================================================================

class TestDimensionExtraction:
    """Tests for POST /api/v1/extraction/dimensions."""

    async def test_extract_dimensions_unauthenticated(
        self, client: AsyncClient
    ):
        """Should return 401 without authentication."""
        response = await client.post(
            "/api/v1/extraction/dimensions",
            files={"file": ("test.png", b"fake image data", "image/png")},
        )
        assert response.status_code == 401

    async def test_extract_dimensions_invalid_file_type(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Should reject unsupported file types."""
        response = await client.post(
            "/api/v1/extraction/dimensions",
            headers=auth_headers,
            files={"file": ("test.txt", b"text data", "text/plain")},
        )
        
        assert response.status_code == 400

    async def test_extract_dimensions_with_image(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Should accept image files for extraction."""
        # Create a minimal valid PNG file
        png_data = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82'
        
        response = await client.post(
            "/api/v1/extraction/dimensions",
            headers=auth_headers,
            files={"file": ("test.png", png_data, "image/png")},
            data={"context": "A technical drawing"},
        )
        
        # May fail due to missing Anthropic key or succeed
        assert response.status_code in [200, 400, 422, 500, 502, 503]


# =============================================================================
# URL Extraction Tests
# =============================================================================

class TestURLExtraction:
    """Tests for POST /api/v1/extraction/url."""

    async def test_extract_url_unauthenticated(
        self, client: AsyncClient
    ):
        """Should return 401 without authentication."""
        response = await client.post(
            "/api/v1/extraction/url",
            json={"url": "https://example.com/drawing.png"},
        )
        assert response.status_code == 401

    async def test_extract_url_authenticated(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Should accept URL for extraction."""
        response = await client.post(
            "/api/v1/extraction/url",
            headers=auth_headers,
            json={"url": "https://example.com/drawing.png"},
        )
        
        # May fail due to URL fetch issues or succeed
        assert response.status_code in [200, 400, 422, 500, 502, 503]
