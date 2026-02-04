"""
Tests for CAD Templates Module.

Tests template registration, lookup, and generator functions.
"""

import pytest

from app.cad.templates import (
    TEMPLATE_REGISTRY,
    register_template,
    get_template_generator,
    generate_from_template,
    ProjectBoxParams,
)


# =============================================================================
# Template Registry Tests
# =============================================================================

class TestTemplateRegistry:
    """Tests for the template registry."""

    def test_registry_exists(self):
        """Test that registry is defined."""
        assert TEMPLATE_REGISTRY is not None
        assert isinstance(TEMPLATE_REGISTRY, dict)

    def test_project_box_registered(self):
        """Test project box template is registered."""
        assert "project-box" in TEMPLATE_REGISTRY

    def test_registry_has_templates(self):
        """Test registry is not empty."""
        assert len(TEMPLATE_REGISTRY) > 0


# =============================================================================
# Template Lookup Tests
# =============================================================================

class TestGetTemplateGenerator:
    """Tests for get_template_generator function."""

    def test_get_existing_template(self):
        """Test getting an existing template."""
        generator = get_template_generator("project-box")
        
        assert generator is not None
        assert callable(generator)

    def test_get_nonexistent_template(self):
        """Test getting a nonexistent template returns None."""
        generator = get_template_generator("nonexistent-template")
        
        assert generator is None


# =============================================================================
# Template Registration Tests
# =============================================================================

class TestRegisterTemplate:
    """Tests for the register_template decorator."""

    def test_register_new_template(self):
        """Test registering a new template."""
        @register_template("test-template")
        def test_generator(**params):
            from build123d import Box
            return Box(10, 10, 10)
        
        assert "test-template" in TEMPLATE_REGISTRY
        assert TEMPLATE_REGISTRY["test-template"] is test_generator
        
        # Cleanup
        del TEMPLATE_REGISTRY["test-template"]

    def test_decorator_preserves_function(self):
        """Test that decorator preserves the original function."""
        @register_template("preserve-test")
        def my_generator(**params):
            """My generator docstring."""
            from build123d import Box
            return Box(10, 10, 10)
        
        assert my_generator.__name__ == "my_generator"
        assert "docstring" in my_generator.__doc__
        
        # Cleanup
        del TEMPLATE_REGISTRY["preserve-test"]


# =============================================================================
# Generate From Template Tests
# =============================================================================

class TestGenerateFromTemplate:
    """Tests for generate_from_template function."""

    def test_generate_project_box(self):
        """Test generating a project box."""
        from build123d import Part, Compound
        
        result = generate_from_template("project-box", {
            "length": 80.0,
            "width": 50.0,
            "height": 30.0,
        })
        
        assert result is not None
        # Should return a Build123d Part or Compound
        assert isinstance(result, (Part, Compound))

    def test_generate_with_defaults(self):
        """Test generating with default parameters."""
        from build123d import Part, Compound
        
        result = generate_from_template("project-box", {})
        
        assert result is not None
        assert isinstance(result, (Part, Compound))

    def test_generate_nonexistent_raises(self):
        """Test generating from nonexistent template raises ValueError."""
        with pytest.raises(ValueError, match="Template not found"):
            generate_from_template("nonexistent", {})

    def test_generate_with_extra_params(self):
        """Test that extra parameters are ignored."""
        from build123d import Part, Compound
        
        # Should not raise
        result = generate_from_template("project-box", {
            "length": 100.0,
            "extra_param": "ignored",
            "another_extra": 42,
        })
        
        assert result is not None


# =============================================================================
# ProjectBoxParams Tests
# =============================================================================

class TestProjectBoxParams:
    """Tests for ProjectBoxParams dataclass."""

    def test_default_dimensions(self):
        """Test default outer dimensions."""
        params = ProjectBoxParams()
        
        assert params.length == 100.0
        assert params.width == 60.0
        assert params.height == 40.0

    def test_default_wall_thickness(self):
        """Test default wall thickness."""
        params = ProjectBoxParams()
        
        assert params.wall_thickness == 2.0

    def test_default_corner_options(self):
        """Test default corner options."""
        params = ProjectBoxParams()
        
        assert params.corner_radius == 3.0
        assert params.corner_style == "rounded"

    def test_default_lid_options(self):
        """Test default lid options."""
        params = ProjectBoxParams()
        
        assert params.lid_style == "overlap"
        assert params.lid_height == 10.0
        assert params.lid_tolerance == 0.3

    def test_default_screw_posts(self):
        """Test default screw post options."""
        params = ProjectBoxParams()
        
        assert params.screw_posts is True
        assert params.screw_post_diameter == 6.0
        assert params.screw_hole_diameter == 3.0
        assert params.screw_post_height == 0.0  # Auto

    def test_default_ventilation(self):
        """Test default ventilation options."""
        params = ProjectBoxParams()
        
        assert params.ventilation_slots is False
        assert params.slot_width == 2.0
        assert params.slot_length == 20.0
        assert params.slot_count == 3

    def test_default_cable_hole(self):
        """Test default cable hole options."""
        params = ProjectBoxParams()
        
        assert params.cable_hole is False
        assert params.cable_hole_diameter == 8.0
        assert params.cable_hole_position == "back"

    def test_custom_params(self):
        """Test custom parameter values."""
        params = ProjectBoxParams(
            length=150.0,
            width=100.0,
            height=60.0,
            corner_style="chamfered",
            lid_style="inset",
            ventilation_slots=True,
            cable_hole=True,
        )
        
        assert params.length == 150.0
        assert params.width == 100.0
        assert params.height == 60.0
        assert params.corner_style == "chamfered"
        assert params.lid_style == "inset"
        assert params.ventilation_slots is True
        assert params.cable_hole is True


# =============================================================================
# Project Box Generator Tests
# =============================================================================

class TestProjectBoxGenerator:
    """Tests for project box generator function."""

    def test_generates_valid_geometry(self):
        """Test that generator produces valid geometry."""
        from build123d import Part, Compound
        
        result = generate_from_template("project-box", {
            "length": 80.0,
            "width": 50.0,
            "height": 30.0,
        })
        
        # Should have solid geometry
        solids = result.solids()
        assert len(solids) >= 1

    def test_with_screw_posts(self):
        """Test generation with screw posts enabled."""
        from build123d import Part, Compound
        
        result = generate_from_template("project-box", {
            "length": 100.0,
            "width": 60.0,
            "height": 40.0,
            "screw_posts": True,
        })
        
        assert result is not None

    def test_without_screw_posts(self):
        """Test generation without screw posts."""
        from build123d import Part, Compound
        
        result = generate_from_template("project-box", {
            "length": 100.0,
            "width": 60.0,
            "height": 40.0,
            "screw_posts": False,
        })
        
        assert result is not None

    def test_with_rounded_corners(self):
        """Test generation with rounded corners."""
        from build123d import Part, Compound
        
        result = generate_from_template("project-box", {
            "corner_style": "rounded",
            "corner_radius": 5.0,
        })
        
        assert result is not None

    def test_with_chamfered_corners(self):
        """Test generation with chamfered corners."""
        from build123d import Part, Compound
        
        result = generate_from_template("project-box", {
            "corner_style": "chamfered",
            "corner_radius": 3.0,
        })
        
        assert result is not None

    def test_with_sharp_corners(self):
        """Test generation with sharp corners."""
        from build123d import Part, Compound
        
        result = generate_from_template("project-box", {
            "corner_style": "sharp",
        })
        
        assert result is not None

    def test_with_cable_hole_back(self):
        """Test generation with back cable hole."""
        from build123d import Part, Compound
        
        result = generate_from_template("project-box", {
            "cable_hole": True,
            "cable_hole_position": "back",
        })
        
        assert result is not None

    def test_with_cable_hole_left(self):
        """Test generation with left cable hole."""
        from build123d import Part, Compound
        
        result = generate_from_template("project-box", {
            "cable_hole": True,
            "cable_hole_position": "left",
        })
        
        assert result is not None


# =============================================================================
# Edge Cases
# =============================================================================

class TestTemplateEdgeCases:
    """Tests for edge cases in templates."""

    def test_very_large_box(self):
        """Test generating a very large box."""
        from build123d import Part, Compound
        
        result = generate_from_template("project-box", {
            "length": 500.0,
            "width": 400.0,
            "height": 200.0,
        })
        
        assert result is not None

    def test_zero_corner_radius(self):
        """Test with zero corner radius (sharp)."""
        from build123d import Part, Compound
        
        result = generate_from_template("project-box", {
            "corner_style": "rounded",
            "corner_radius": 0.0,
        })
        
        assert result is not None

    def test_zero_slot_count(self):
        """Test with zero ventilation slot count."""
        from build123d import Part, Compound
        
        result = generate_from_template("project-box", {
            "ventilation_slots": True,
            "slot_count": 0,
        })
        
        assert result is not None
