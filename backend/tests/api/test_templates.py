"""
Tests for Templates API endpoints.

Tests template listing, detail retrieval, parameter validation, and generation.
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession


# =============================================================================
# List Templates Tests
# =============================================================================

class TestListTemplates:
    """Tests for template listing endpoint."""

    @pytest.mark.asyncio
    async def test_list_templates_empty(
        self,
        client: AsyncClient,
    ):
        """Test listing templates when none exist."""
        response = await client.get("/api/v1/templates")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["templates"] == []
        assert data["total"] == 0

    @pytest.mark.asyncio
    async def test_list_templates_with_templates(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        template_factory,
    ):
        """Test listing templates."""
        await template_factory.create(db=db_session, name="Box", category="mechanical")
        await template_factory.create(db=db_session, name="Cylinder", category="mechanical")
        await template_factory.create(db=db_session, name="Bracket", category="mechanical")
        
        response = await client.get("/api/v1/templates")
        
        assert response.status_code == 200
        data = response.json()
        
        assert len(data["templates"]) == 3
        assert data["total"] == 3
        assert "mechanical" in data["categories"]

    @pytest.mark.asyncio
    async def test_list_templates_filter_by_category(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        template_factory,
    ):
        """Test filtering templates by category."""
        await template_factory.create(db=db_session, category="mechanical")
        await template_factory.create(db=db_session, category="enclosures")
        await template_factory.create(db=db_session, category="mechanical")
        
        response = await client.get(
            "/api/v1/templates",
            params={"category": "mechanical"},
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert len(data["templates"]) == 2
        assert all(t["category"] == "mechanical" for t in data["templates"])

    @pytest.mark.asyncio
    async def test_list_templates_filter_by_tier(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        template_factory,
    ):
        """Test filtering templates by tier."""
        await template_factory.create(db=db_session, min_tier="free")
        await template_factory.create(db=db_session, min_tier="pro")
        await template_factory.create(db=db_session, min_tier="free")
        
        response = await client.get(
            "/api/v1/templates",
            params={"tier": "free"},
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Free users can only see free templates
        assert len(data["templates"]) == 2

    @pytest.mark.asyncio
    async def test_list_templates_search(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        template_factory,
    ):
        """Test searching templates by name/description."""
        await template_factory.create(db=db_session, name="Mounting Bracket")
        await template_factory.create(db=db_session, name="Cable Gland")
        await template_factory.create(db=db_session, name="Bracket Assembly")
        
        response = await client.get(
            "/api/v1/templates",
            params={"search": "bracket"},
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert len(data["templates"]) == 2
        assert all("Bracket" in t["name"] for t in data["templates"])

    @pytest.mark.asyncio
    async def test_list_templates_excludes_inactive(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        template_factory,
    ):
        """Test that inactive templates are excluded."""
        await template_factory.create(db=db_session, is_active=True)
        await template_factory.create(db=db_session, is_active=False)
        
        response = await client.get("/api/v1/templates")
        
        assert response.status_code == 200
        data = response.json()
        
        assert len(data["templates"]) == 1

    @pytest.mark.asyncio
    async def test_list_templates_pagination(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        template_factory,
    ):
        """Test template listing pagination."""
        for i in range(5):
            await template_factory.create(db=db_session, name=f"Template {i}")
        
        response = await client.get(
            "/api/v1/templates",
            params={"limit": 2, "offset": 0},
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert len(data["templates"]) == 2
        assert data["total"] == 5


# =============================================================================
# Get Template Tests
# =============================================================================

class TestGetTemplate:
    """Tests for getting individual template details."""

    @pytest.mark.asyncio
    async def test_get_template_success(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        template_factory,
    ):
        """Test getting template details."""
        template = await template_factory.create(
            db=db_session,
            name="Test Box",
            slug="test-box",
            category="mechanical",
            parameters={
                "length": {
                    "type": "number",
                    "label": "Length",
                    "default": 100,
                    "min": 10,
                    "max": 500,
                    "unit": "mm",
                },
                "width": {
                    "type": "number",
                    "label": "Width",
                    "default": 50,
                    "min": 10,
                    "max": 500,
                    "unit": "mm",
                },
            },
        )
        
        response = await client.get(f"/api/v1/templates/{template.slug}")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["name"] == "Test Box"
        assert data["slug"] == "test-box"
        assert data["category"] == "mechanical"
        assert "length" in data["parameters"]
        assert data["parameters"]["length"]["type"] == "number"
        assert data["parameters"]["length"]["default"] == 100

    @pytest.mark.asyncio
    async def test_get_template_not_found(
        self,
        client: AsyncClient,
    ):
        """Test getting non-existent template."""
        response = await client.get("/api/v1/templates/non-existent-template")
        
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_template_inactive(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        template_factory,
    ):
        """Test getting inactive template returns 404."""
        template = await template_factory.create(db=db_session, is_active=False)
        
        response = await client.get(f"/api/v1/templates/{template.slug}")
        
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_template_tier_restricted(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        template_factory,
    ):
        """Test getting pro template as free user returns 403."""
        template = await template_factory.create(
            db=db_session,
            min_tier="pro",
        )
        
        # Request without auth (treated as free tier)
        response = await client.get(f"/api/v1/templates/{template.slug}")
        
        assert response.status_code == 403
        assert "requires pro tier" in response.json()["detail"]


# =============================================================================
# Generate Template Tests
# =============================================================================

class TestGenerateTemplate:
    """Tests for template generation endpoint."""

    @pytest.mark.asyncio
    async def test_generate_requires_auth(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        template_factory,
    ):
        """Test that generation requires authentication."""
        template = await template_factory.create(db=db_session)
        
        response = await client.post(
            f"/api/v1/templates/{template.slug}/generate",
            json={"parameters": {}, "format": "step"},
        )
        
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_generate_template_not_found(
        self,
        client: AsyncClient,
        test_user,
        auth_headers,
    ):
        """Test generating from non-existent template."""
        response = await client.post(
            "/api/v1/templates/non-existent/generate",
            headers=auth_headers,
            json={"parameters": {}, "format": "step"},
        )
        
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_generate_invalid_parameters(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_user,
        auth_headers,
        template_factory,
    ):
        """Test generation with invalid parameters."""
        template = await template_factory.create(
            db=db_session,
            slug="test-box",
            parameters={
                "length": {
                    "type": "number",
                    "label": "Length",
                    "default": 100,
                    "min": 10,
                    "max": 500,
                },
            },
        )
        
        response = await client.post(
            f"/api/v1/templates/{template.slug}/generate",
            headers=auth_headers,
            json={
                "parameters": {"length": 1000},  # Exceeds max
                "format": "step",
            },
        )
        
        assert response.status_code == 422
        assert "Invalid parameters" in response.json()["detail"]["message"]

    @pytest.mark.asyncio
    async def test_generate_tier_restricted(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_user,
        auth_headers,
        template_factory,
    ):
        """Test generating from pro template as free user."""
        template = await template_factory.create(
            db=db_session,
            min_tier="pro",
        )
        
        response = await client.post(
            f"/api/v1/templates/{template.slug}/generate",
            headers=auth_headers,
            json={"parameters": {}, "format": "step"},
        )
        
        assert response.status_code == 403


# =============================================================================
# Parameter Validation Tests
# =============================================================================

class TestParameterValidation:
    """Tests for template parameter validation."""

    @pytest.mark.asyncio
    async def test_validate_number_in_range(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        template_factory,
    ):
        """Test that number parameters within range are valid."""
        template = await template_factory.create(
            db=db_session,
            parameters={
                "length": {
                    "type": "number",
                    "label": "Length",
                    "default": 100,
                    "min": 10,
                    "max": 500,
                },
            },
        )
        
        # Valid value should work
        response = await client.get(f"/api/v1/templates/{template.slug}")
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_validate_enum_options(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        template_factory,
    ):
        """Test that enum parameter options are returned."""
        template = await template_factory.create(
            db=db_session,
            parameters={
                "style": {
                    "type": "enum",
                    "label": "Style",
                    "default": "rounded",
                    "options": ["rounded", "chamfered", "sharp"],
                },
            },
        )
        
        response = await client.get(f"/api/v1/templates/{template.slug}")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["parameters"]["style"]["options"] == ["rounded", "chamfered", "sharp"]


# =============================================================================
# Categories Tests
# =============================================================================

class TestCategories:
    """Tests for template categories."""

    @pytest.mark.asyncio
    async def test_categories_returned_in_list(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        template_factory,
    ):
        """Test that categories are returned in list response."""
        await template_factory.create(db=db_session, category="mechanical")
        await template_factory.create(db=db_session, category="enclosures")
        await template_factory.create(db=db_session, category="hardware")
        
        response = await client.get("/api/v1/templates")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "mechanical" in data["categories"]
        assert "enclosures" in data["categories"]
        assert "hardware" in data["categories"]

    @pytest.mark.asyncio
    async def test_categories_unique(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        template_factory,
    ):
        """Test that categories list is unique."""
        await template_factory.create(db=db_session, category="mechanical")
        await template_factory.create(db=db_session, category="mechanical")
        await template_factory.create(db=db_session, category="mechanical")
        
        response = await client.get("/api/v1/templates")
        
        assert response.status_code == 200
        data = response.json()
        
        # Should only have one "mechanical" entry
        assert data["categories"].count("mechanical") == 1
