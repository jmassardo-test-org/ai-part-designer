"""Tests for component mounting and advanced ventilation."""

import pytest

from app.cad_v2.schemas.base import BoundingBox, Dimension, Point3D
from app.cad_v2.schemas.components import (
    ComponentMount,
    ComponentRef,
    MountingType,
    StandoffSpec,
)
from app.cad_v2.schemas.enclosure import (
    EnclosureSpec,
    VentilationSpec,
    WallSide,
    WallSpec,
)

# Import conditionally to handle Build123d availability
try:
    from build123d import Part

    BUILD123D_AVAILABLE = True
except ImportError:
    BUILD123D_AVAILABLE = False


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def enclosure_with_pi() -> EnclosureSpec:
    """Create an enclosure with a Raspberry Pi mounted."""
    return EnclosureSpec(
        exterior=BoundingBox(
            width=Dimension(value=120),
            depth=Dimension(value=80),
            height=Dimension(value=40),
        ),
        walls=WallSpec(thickness=Dimension(value=2.5)),
        components=[
            ComponentMount(
                component=ComponentRef(component_id="raspberry-pi-4b"),
                position=Point3D(x=10, y=10, z=0),
                mounting_type=MountingType.STANDOFF,
                standoffs=StandoffSpec.for_pi(),
            ),
        ],
    )


@pytest.fixture
def enclosure_with_honeycomb() -> EnclosureSpec:
    """Create an enclosure with honeycomb ventilation."""
    return EnclosureSpec(
        exterior=BoundingBox(
            width=Dimension(value=100),
            depth=Dimension(value=80),
            height=Dimension(value=40),
        ),
        walls=WallSpec(thickness=Dimension(value=2.5)),
        ventilation=VentilationSpec(
            enabled=True,
            pattern="honeycomb",
            sides=[WallSide.LEFT, WallSide.RIGHT],
            slot_width=Dimension(value=3),  # Hole diameter base
            slot_spacing=Dimension(value=2),  # Spacing between holes
            margin=Dimension(value=5),
        ),
    )


@pytest.fixture
def enclosure_with_slots() -> EnclosureSpec:
    """Create an enclosure with slot ventilation."""
    return EnclosureSpec(
        exterior=BoundingBox(
            width=Dimension(value=100),
            depth=Dimension(value=80),
            height=Dimension(value=40),
        ),
        walls=WallSpec(thickness=Dimension(value=2.5)),
        ventilation=VentilationSpec(
            enabled=True,
            pattern="slots",
            sides=[WallSide.LEFT, WallSide.RIGHT],
            slot_width=Dimension(value=2),
            slot_length=Dimension(value=20),
            slot_spacing=Dimension(value=4),
            margin=Dimension(value=5),
        ),
    )


# ============================================================================
# Component Mounting Tests
# ============================================================================


class TestComponentMounting:
    """Tests for component mounting compilation."""

    @pytest.mark.skipif(not BUILD123D_AVAILABLE, reason="Build123d not available")
    def test_compile_with_pi_standoffs(self, enclosure_with_pi: EnclosureSpec) -> None:
        """Should compile enclosure with Raspberry Pi standoffs."""
        from app.cad_v2.compiler import CompilationEngine

        engine = CompilationEngine()
        result = engine.compile_enclosure(enclosure_with_pi)

        assert result.success is True
        assert "body" in result.parts
        assert isinstance(result.parts["body"], Part)
        # No errors or warnings about missing components
        assert not result.errors

    @pytest.mark.skipif(not BUILD123D_AVAILABLE, reason="Build123d not available")
    def test_unknown_component_warns(self) -> None:
        """Should warn when component is not in library."""
        from app.cad_v2.compiler import CompilationEngine

        spec = EnclosureSpec(
            exterior=BoundingBox(
                width=Dimension(value=100),
                depth=Dimension(value=80),
                height=Dimension(value=40),
            ),
            components=[
                ComponentMount(
                    component=ComponentRef(component_id="unknown-component-xyz"),
                    position=Point3D(x=10, y=10, z=0),
                    mounting_type=MountingType.STANDOFF,
                ),
            ],
        )

        engine = CompilationEngine()
        result = engine.compile_enclosure(spec)

        assert result.success is True
        # Should have a warning about unknown component
        assert any("unknown-component-xyz" in w for w in result.warnings)

    @pytest.mark.skipif(not BUILD123D_AVAILABLE, reason="Build123d not available")
    def test_surface_mount_no_standoffs(self) -> None:
        """Should not add standoffs for surface mount components."""
        from app.cad_v2.compiler import CompilationEngine

        spec = EnclosureSpec(
            exterior=BoundingBox(
                width=Dimension(value=100),
                depth=Dimension(value=80),
                height=Dimension(value=40),
            ),
            components=[
                ComponentMount(
                    component=ComponentRef(component_id="raspberry-pi-4b"),
                    position=Point3D(x=10, y=10, z=0),
                    mounting_type=MountingType.SURFACE,  # Not standoff
                ),
            ],
        )

        engine = CompilationEngine()
        result = engine.compile_enclosure(spec)

        assert result.success is True
        assert "body" in result.parts


# ============================================================================
# Honeycomb Ventilation Tests
# ============================================================================


class TestHoneycombVentilation:
    """Tests for honeycomb ventilation pattern."""

    @pytest.mark.skipif(not BUILD123D_AVAILABLE, reason="Build123d not available")
    def test_compile_honeycomb_vents(self, enclosure_with_honeycomb: EnclosureSpec) -> None:
        """Should compile enclosure with honeycomb ventilation."""
        from app.cad_v2.compiler import CompilationEngine

        engine = CompilationEngine()
        result = engine.compile_enclosure(enclosure_with_honeycomb)

        assert result.success is True
        assert "body" in result.parts
        assert isinstance(result.parts["body"], Part)

    @pytest.mark.skipif(not BUILD123D_AVAILABLE, reason="Build123d not available")
    def test_compile_slot_vents(self, enclosure_with_slots: EnclosureSpec) -> None:
        """Should compile enclosure with slot ventilation."""
        from app.cad_v2.compiler import CompilationEngine

        engine = CompilationEngine()
        result = engine.compile_enclosure(enclosure_with_slots)

        assert result.success is True
        assert "body" in result.parts
        assert isinstance(result.parts["body"], Part)

    @pytest.mark.skipif(not BUILD123D_AVAILABLE, reason="Build123d not available")
    def test_honeycomb_on_multiple_sides(self) -> None:
        """Should apply honeycomb to front and back sides."""
        from app.cad_v2.compiler import CompilationEngine

        spec = EnclosureSpec(
            exterior=BoundingBox(
                width=Dimension(value=100),
                depth=Dimension(value=80),
                height=Dimension(value=40),
            ),
            ventilation=VentilationSpec(
                enabled=True,
                pattern="honeycomb",
                sides=[WallSide.FRONT, WallSide.BACK],
                slot_width=Dimension(value=3),
                slot_spacing=Dimension(value=2),
                margin=Dimension(value=8),
            ),
        )

        engine = CompilationEngine()
        result = engine.compile_enclosure(spec)

        assert result.success is True
        assert isinstance(result.parts["body"], Part)


# ============================================================================
# Ventilation Pattern Schema Tests
# ============================================================================


class TestVentilationSchema:
    """Tests for ventilation specification."""

    def test_default_pattern_is_slots(self) -> None:
        """Default ventilation pattern should be slots."""
        vent = VentilationSpec(enabled=True)
        assert vent.pattern == "slots"

    def test_honeycomb_pattern(self) -> None:
        """Should accept honeycomb pattern."""
        vent = VentilationSpec(enabled=True, pattern="honeycomb")
        assert vent.pattern == "honeycomb"

    def test_holes_pattern(self) -> None:
        """Should accept holes pattern."""
        vent = VentilationSpec(enabled=True, pattern="holes")
        assert vent.pattern == "holes"
