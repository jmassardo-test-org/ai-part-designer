"""
Tests for Templates API endpoints.

Tests template listing, detail retrieval, parameter validation, and generation.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import uuid4

import pytest

if TYPE_CHECKING:
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
        
        # Parameters are returned as a list
        param_names = [p["name"] for p in data["parameters"]]
        assert "length" in param_names
        
        # Find the length parameter
        length_param = next((p for p in data["parameters"] if p["name"] == "length"), None)
        assert length_param is not None
        assert length_param["type"] == "number"
        assert length_param["default"] == 100

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

        # Find the style parameter in the list
        style_param = next((p for p in data["parameters"] if p["name"] == "style"), None)
        assert style_param is not None
        assert style_param["options"] == ["rounded", "chamfered", "sharp"]


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


# =============================================================================
# Create Template Tests
# =============================================================================


class TestCreateTemplate:
    """Tests for template creation endpoint."""

    @pytest.mark.asyncio
    async def test_create_template_success(
        self,
        client: AsyncClient,
        test_user,
        auth_headers,
    ):
        """Test creating a new template successfully."""
        response = await client.post(
            "/api/v1/templates",
            headers=auth_headers,
            json={
                "name": "My Custom Box",
                "description": "A custom box template",
                "category": "enclosures",
                "tags": ["box", "custom", "3d-printable"],
                "parameters": {
                    "length": {"type": "number", "label": "Length", "min": 10, "max": 500},
                    "width": {"type": "number", "label": "Width", "min": 10, "max": 500},
                },
                "default_values": {"length": 100, "width": 50},
                "is_public": False,
            },
        )

        assert response.status_code == 201
        data = response.json()

        assert data["name"] == "My Custom Box"
        assert data["category"] == "enclosures"
        assert "slug" in data
        assert "my-custom-box" in data["slug"]

    @pytest.mark.asyncio
    async def test_create_template_requires_auth(
        self,
        client: AsyncClient,
    ):
        """Test that template creation requires authentication."""
        response = await client.post(
            "/api/v1/templates",
            json={
                "name": "Test Template",
                "category": "custom",
            },
        )

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_create_template_name_required(
        self,
        client: AsyncClient,
        test_user,
        auth_headers,
    ):
        """Test that template name is required."""
        response = await client.post(
            "/api/v1/templates",
            headers=auth_headers,
            json={
                "description": "A template without name",
                "category": "custom",
            },
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_create_template_category_required(
        self,
        client: AsyncClient,
        test_user,
        auth_headers,
    ):
        """Test that template category is required."""
        response = await client.post(
            "/api/v1/templates",
            headers=auth_headers,
            json={
                "name": "Template Without Category",
            },
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_create_template_unique_slug_generated(
        self,
        client: AsyncClient,
        test_user,
        auth_headers,
    ):
        """Test that unique slugs are generated for templates with same name."""
        # Create first template
        response1 = await client.post(
            "/api/v1/templates",
            headers=auth_headers,
            json={"name": "My Template", "category": "custom"},
        )
        assert response1.status_code == 201

        # Create second template with same name
        response2 = await client.post(
            "/api/v1/templates",
            headers=auth_headers,
            json={"name": "My Template", "category": "custom"},
        )
        assert response2.status_code == 201

        # Slugs should be different
        data1 = response1.json()
        data2 = response2.json()
        assert data1["slug"] != data2["slug"]


# =============================================================================
# Create Template From Design Tests
# =============================================================================


class TestCreateTemplateFromDesign:
    """Tests for creating templates from existing designs."""

    @pytest.mark.asyncio
    async def test_create_from_design_success(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_user,
        auth_headers,
        project_factory,
        design_factory,
    ):
        """Test creating a template from an existing design."""
        # Create project and design for the user
        from tests.factories import DesignFactory, ProjectFactory

        project = await ProjectFactory.create(db=db_session, user=test_user)
        design = await DesignFactory.create(
            db=db_session,
            project=project,
            name="Original Design",
            extra_data={
                "dimensions": {
                    "length": 100,
                    "width": 60,
                    "height": 40,
                }
            },
        )

        response = await client.post(
            "/api/v1/templates/from-design",
            headers=auth_headers,
            json={
                "design_id": str(design.id),
                "name": "Template From Design",
                "description": "A template created from my design",
                "category": "custom",
                "tags": ["converted", "design"],
            },
        )

        assert response.status_code == 201
        data = response.json()

        assert data["name"] == "Template From Design"
        assert data["category"] == "custom"

    @pytest.mark.asyncio
    async def test_create_from_design_not_found(
        self,
        client: AsyncClient,
        test_user,
        auth_headers,
    ):
        """Test creating template from non-existent design."""

        response = await client.post(
            "/api/v1/templates/from-design",
            headers=auth_headers,
            json={
                "design_id": str(uuid4()),
                "name": "Template",
                "category": "custom",
            },
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_create_from_design_not_owner(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_user,
        auth_headers,
        user_factory,
    ):
        """Test creating template from another user's design."""
        from tests.factories import DesignFactory, ProjectFactory, UserFactory

        # Create another user's design
        other_user = await UserFactory.create(db=db_session)
        other_project = await ProjectFactory.create(db=db_session, user=other_user)
        other_design = await DesignFactory.create(db=db_session, project=other_project)

        response = await client.post(
            "/api/v1/templates/from-design",
            headers=auth_headers,
            json={
                "design_id": str(other_design.id),
                "name": "Stolen Template",
                "category": "custom",
            },
        )

        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_create_from_design_requires_auth(
        self,
        client: AsyncClient,
    ):
        """Test that creating from design requires authentication."""

        response = await client.post(
            "/api/v1/templates/from-design",
            json={
                "design_id": str(uuid4()),
                "name": "Template",
                "category": "custom",
            },
        )

        assert response.status_code == 401
