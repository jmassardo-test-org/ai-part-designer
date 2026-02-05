"""
Tests for Enclosure Schemas Module.

Tests enclosure style types, lid closures, ventilation patterns,
standoff types, and configuration schemas.
"""

from app.enclosure.schemas import (
    BossStyle,
    EnclosureStyleType,
    LidClosureType,
    StandoffOptions,
    StandoffType,
    VentilationPattern,
)

# =============================================================================
# EnclosureStyleType Tests
# =============================================================================


class TestEnclosureStyleType:
    """Tests for EnclosureStyleType enum."""

    def test_minimal_style(self):
        """Test minimal style type."""
        assert EnclosureStyleType.MINIMAL == "minimal"

    def test_rugged_style(self):
        """Test rugged style type."""
        assert EnclosureStyleType.RUGGED == "rugged"

    def test_vented_style(self):
        """Test vented style type."""
        assert EnclosureStyleType.VENTED == "vented"

    def test_stackable_style(self):
        """Test stackable style type."""
        assert EnclosureStyleType.STACKABLE == "stackable"

    def test_desktop_style(self):
        """Test desktop style type."""
        assert EnclosureStyleType.DESKTOP == "desktop"

    def test_custom_style(self):
        """Test custom style type."""
        assert EnclosureStyleType.CUSTOM == "custom"

    def test_all_styles_are_strings(self):
        """Test all styles are strings."""
        for style in EnclosureStyleType:
            assert isinstance(style.value, str)


# =============================================================================
# LidClosureType Tests
# =============================================================================


class TestLidClosureType:
    """Tests for LidClosureType enum."""

    def test_snap_fit_closure(self):
        """Test snap fit closure."""
        assert LidClosureType.SNAP_FIT == "snap_fit"

    def test_screw_closure(self):
        """Test screw closure."""
        assert LidClosureType.SCREW == "screw"

    def test_slide_closure(self):
        """Test slide closure."""
        assert LidClosureType.SLIDE == "slide"

    def test_friction_closure(self):
        """Test friction closure."""
        assert LidClosureType.FRICTION == "friction"

    def test_hinge_closure(self):
        """Test hinge closure."""
        assert LidClosureType.HINGE == "hinge"

    def test_magnetic_closure(self):
        """Test magnetic closure."""
        assert LidClosureType.MAGNETIC == "magnetic"

    def test_all_closures_are_strings(self):
        """Test all closures are strings."""
        for closure in LidClosureType:
            assert isinstance(closure.value, str)


# =============================================================================
# VentilationPattern Tests
# =============================================================================


class TestVentilationPattern:
    """Tests for VentilationPattern enum."""

    def test_none_pattern(self):
        """Test no ventilation pattern."""
        assert VentilationPattern.NONE == "none"

    def test_parallel_slots_pattern(self):
        """Test parallel slots pattern."""
        assert VentilationPattern.PARALLEL_SLOTS == "parallel_slots"

    def test_grid_pattern(self):
        """Test grid pattern."""
        assert VentilationPattern.GRID == "grid"

    def test_honeycomb_pattern(self):
        """Test honeycomb pattern."""
        assert VentilationPattern.HONEYCOMB == "honeycomb"

    def test_perforated_pattern(self):
        """Test perforated pattern."""
        assert VentilationPattern.PERFORATED == "perforated"

    def test_louvers_pattern(self):
        """Test louvers pattern."""
        assert VentilationPattern.LOUVERS == "louvers"

    def test_all_patterns_are_strings(self):
        """Test all patterns are strings."""
        for pattern in VentilationPattern:
            assert isinstance(pattern.value, str)


# =============================================================================
# StandoffType Tests
# =============================================================================


class TestStandoffType:
    """Tests for StandoffType enum."""

    def test_solid_standoff(self):
        """Test solid standoff type."""
        assert StandoffType.SOLID == "solid"

    def test_hollow_standoff(self):
        """Test hollow standoff type."""
        assert StandoffType.HOLLOW == "hollow"

    def test_heat_set_insert_standoff(self):
        """Test heat set insert standoff type."""
        assert StandoffType.HEAT_SET_INSERT == "heat_set_insert"

    def test_threaded_standoff(self):
        """Test threaded standoff type."""
        assert StandoffType.THREADED == "threaded"

    def test_snap_fit_standoff(self):
        """Test snap fit standoff type."""
        assert StandoffType.SNAP_FIT == "snap_fit"

    def test_all_standoffs_are_strings(self):
        """Test all standoff types are strings."""
        for standoff in StandoffType:
            assert isinstance(standoff.value, str)


# =============================================================================
# BossStyle Tests
# =============================================================================


class TestBossStyle:
    """Tests for BossStyle enum."""

    def test_cylindrical_boss(self):
        """Test cylindrical boss style."""
        assert BossStyle.CYLINDRICAL == "cylindrical"

    def test_square_boss(self):
        """Test square boss style."""
        assert BossStyle.SQUARE == "square"

    def test_ribbed_boss(self):
        """Test ribbed boss style."""
        assert BossStyle.RIBBED == "ribbed"

    def test_gusseted_boss(self):
        """Test gusseted boss style."""
        assert BossStyle.GUSSETED == "gusseted"

    def test_all_boss_styles_are_strings(self):
        """Test all boss styles are strings."""
        for boss in BossStyle:
            assert isinstance(boss.value, str)


# =============================================================================
# StandoffOptions Tests
# =============================================================================


class TestStandoffOptions:
    """Tests for StandoffOptions Pydantic model."""

    def test_default_options(self):
        """Test default standoff options."""
        options = StandoffOptions()

        assert options.type == StandoffType.HOLLOW
        assert options.boss_style == BossStyle.CYLINDRICAL
        assert options.outer_diameter is None
        assert options.inner_diameter is None
        assert options.thread_size is None

    def test_custom_options(self):
        """Test custom standoff options."""
        options = StandoffOptions(
            type=StandoffType.THREADED,
            boss_style=BossStyle.GUSSETED,
            outer_diameter=6.0,
            inner_diameter=3.0,
        )

        assert options.type == StandoffType.THREADED
        assert options.boss_style == BossStyle.GUSSETED
        assert options.outer_diameter == 6.0
        assert options.inner_diameter == 3.0

    def test_solid_standoff(self):
        """Test solid standoff configuration."""
        options = StandoffOptions(
            type=StandoffType.SOLID,
            outer_diameter=8.0,
        )

        assert options.type == StandoffType.SOLID
        assert options.outer_diameter == 8.0

    def test_heat_set_insert(self):
        """Test heat set insert configuration."""
        options = StandoffOptions(
            type=StandoffType.HEAT_SET_INSERT,
            boss_style=BossStyle.CYLINDRICAL,
            outer_diameter=5.0,
            inner_diameter=4.0,
        )

        assert options.type == StandoffType.HEAT_SET_INSERT
        assert options.inner_diameter == 4.0


# =============================================================================
# Edge Cases
# =============================================================================


class TestEnclosureSchemaEdgeCases:
    """Tests for edge cases in enclosure schemas."""

    def test_all_enums_have_values(self):
        """Test all enums have at least one value."""
        enums = [
            EnclosureStyleType,
            LidClosureType,
            VentilationPattern,
            StandoffType,
            BossStyle,
        ]

        for enum_class in enums:
            assert len(list(enum_class)) > 0

    def test_standoff_options_json_serializable(self):
        """Test standoff options can be serialized to JSON."""
        options = StandoffOptions(
            type=StandoffType.HOLLOW,
            boss_style=BossStyle.RIBBED,
            outer_diameter=6.0,
        )

        # Should not raise
        json_data = options.model_dump()
        assert "type" in json_data
        assert json_data["outer_diameter"] == 6.0

    def test_standoff_options_from_dict(self):
        """Test creating standoff options from dict."""
        data = {
            "type": "threaded",
            "boss_style": "square",
            "outer_diameter": 8.0,
            "inner_diameter": 3.2,
        }

        options = StandoffOptions(**data)

        assert options.type == StandoffType.THREADED
        assert options.boss_style == BossStyle.SQUARE
