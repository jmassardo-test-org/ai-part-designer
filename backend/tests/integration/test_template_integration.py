"""
Integration tests for template workflows.

Tests template browsing, parameter validation, and generation.
"""

from __future__ import annotations

from uuid import uuid4

import pytest

# =============================================================================
# Template Browsing Integration Tests
# =============================================================================


class TestTemplateBrowsingIntegration:
    """Integration tests for template browsing."""

    @pytest.mark.asyncio
    async def test_get_templates_with_get_many(self, db_session):
        """Test listing available templates using get_many."""
        from app.repositories import TemplateRepository

        template_repo = TemplateRepository(db_session)
        templates = await template_repo.get_many()

        # Should return a sequence
        assert hasattr(templates, "__iter__")

    @pytest.mark.asyncio
    async def test_get_template_by_id(self, db_session):
        """Test retrieving template by ID."""
        from app.models import Template
        from app.repositories import TemplateRepository

        # Create a test template with all required fields
        template_id = uuid4()
        template = Template(
            id=template_id,
            name="Test Template",
            slug=f"test-template-{uuid4().hex[:8]}",
            description="A test template for integration testing",
            category="enclosures",
            parameters={
                "length": {
                    "type": "number",
                    "default": 100,
                    "min": 10,
                    "max": 500,
                }
            },
            default_values={"length": 100},
            cadquery_script="result = cq.Workplane('XY').box(100, 50, 25)",
        )
        db_session.add(template)
        await db_session.commit()

        template_repo = TemplateRepository(db_session)
        fetched = await template_repo.get_by_id(template_id)

        assert fetched is not None
        assert fetched.name == "Test Template"


# =============================================================================
# Template Generation Integration Tests
# =============================================================================


class TestTemplateGenerationIntegration:
    """Integration tests for template-based generation."""

    def test_generate_box_from_primitives(self):
        """Test generating box using primitives module."""
        from app.cad.primitives import create_box

        result = create_box(100, 50, 25)

        assert result is not None

        # Verify dimensions using build123d bounding_box
        bbox = result.bounding_box()
        assert round(bbox.size.X, 0) == 100
        assert round(bbox.size.Y, 0) == 50
        assert round(bbox.size.Z, 0) == 25

    def test_generate_cylinder_from_primitives(self):
        """Test generating cylinder using primitives module."""
        from app.cad.primitives import create_cylinder

        result = create_cylinder(radius=25, height=100)

        assert result is not None

        # Verify height using build123d bounding_box
        bbox = result.bounding_box()
        assert round(bbox.size.Z, 0) == 100

    def test_generate_and_export_box(self, tmp_path):
        """Test generating and exporting a box."""
        from app.cad.export import export_to_file
        from app.cad.primitives import create_box

        box = create_box(50, 50, 50)
        step_path = tmp_path / "test.step"
        stl_path = tmp_path / "test.stl"

        export_to_file(box, step_path)
        export_to_file(box, stl_path)

        assert step_path.exists()
        assert stl_path.exists()
        assert step_path.stat().st_size > 0
        assert stl_path.stat().st_size > 0


# =============================================================================
# Template Parameter Validation Integration Tests
# =============================================================================


class TestTemplateParameterValidation:
    """Integration tests for template parameter validation."""

    @pytest.mark.asyncio
    async def test_template_validates_parameters(self, db_session):
        """Test that template validates parameters correctly."""
        from app.models import Template

        template = Template(
            id=uuid4(),
            name="Validation Test Template",
            slug=f"validation-test-{uuid4().hex[:8]}",
            category="enclosures",
            parameters={
                "length": {
                    "type": "number",
                    "default": 100,
                    "min": 10,
                    "max": 500,
                },
                "width": {
                    "type": "number",
                    "default": 50,
                    "min": 10,
                    "max": 300,
                },
            },
            default_values={"length": 100, "width": 50},
            cadquery_script="result = cq.Workplane('XY').box(100, 50, 25)",
        )
        db_session.add(template)
        await db_session.commit()

        # Valid parameters - validate_parameters returns a list of error strings
        errors = template.validate_parameters(
            {
                "length": 100,
                "width": 50,
            }
        )

        assert len(errors) == 0

    @pytest.mark.asyncio
    async def test_template_rejects_out_of_range(self, db_session):
        """Test template rejects out-of-range parameters."""
        from app.models import Template

        template = Template(
            id=uuid4(),
            name="Range Test Template",
            slug=f"range-test-{uuid4().hex[:8]}",
            category="enclosures",
            parameters={
                "length": {
                    "type": "number",
                    "default": 100,
                    "min": 10,
                    "max": 500,
                },
            },
            default_values={"length": 100},
            cadquery_script="result = cq.Workplane('XY').box(100, 50, 25)",
        )
        db_session.add(template)
        await db_session.commit()

        # Value too high - validate_parameters returns a list of error strings
        errors = template.validate_parameters({"length": 1000})

        assert len(errors) > 0


# =============================================================================
# Template Usage Tracking Integration Tests
# =============================================================================


class TestTemplateUsageTracking:
    """Integration tests for template usage tracking."""

    @pytest.mark.asyncio
    async def test_increment_template_usage(self, db_session):
        """Test incrementing template usage count."""
        from app.models import Template
        from app.repositories import TemplateRepository

        # Create template with required fields
        template_id = uuid4()
        template = Template(
            id=template_id,
            name="Usage Test Template",
            slug=f"usage-test-{uuid4().hex[:8]}",
            category="enclosures",
            parameters={},
            default_values={},
            cadquery_script="result = cq.Workplane('XY').box(100, 50, 25)",
        )
        db_session.add(template)
        await db_session.commit()

        template_repo = TemplateRepository(db_session)

        # Increment usage - note method is increment_use_count
        await template_repo.increment_use_count(template_id)
        await db_session.commit()

        # Check updated count
        await db_session.refresh(template)
        assert template.use_count >= 1
