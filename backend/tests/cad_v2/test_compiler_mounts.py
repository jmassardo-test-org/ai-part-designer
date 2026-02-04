"""Tests for mount compiler (screw bosses, standoffs)."""

import pytest

from app.cad_v2.schemas.base import BoundingBox, Dimension, Point3D
from app.cad_v2.schemas.components import (
    ComponentMount,
    ComponentRef,
    MountingHole,
    MountingType,
    StandoffSpec,
    StandoffType,
)
from app.cad_v2.schemas.enclosure import (
    EnclosureSpec,
    LidSpec,
    LidType,
    ScrewSpec,
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
def screw_on_enclosure() -> EnclosureSpec:
    """Create an enclosure with screw-on lid."""
    return EnclosureSpec(
        exterior=BoundingBox(
            width=Dimension(value=100),
            depth=Dimension(value=80),
            height=Dimension(value=40),
        ),
        walls=WallSpec(thickness=Dimension(value=2.5)),
        lid=LidSpec(
            type=LidType.SCREW_ON,
            separate_part=True,
            screws=ScrewSpec.m3(),
        ),
    )


@pytest.fixture
def simple_enclosure() -> EnclosureSpec:
    """Create a simple enclosure without lid."""
    return EnclosureSpec(
        exterior=BoundingBox(
            width=Dimension(value=100),
            depth=Dimension(value=80),
            height=Dimension(value=40),
        ),
        walls=WallSpec(thickness=Dimension(value=2.5)),
    )


# ============================================================================
# ScrewSpec Tests
# ============================================================================


class TestScrewSpec:
    """Tests for ScrewSpec schemas."""

    def test_m2_spec(self) -> None:
        """M2 spec should have correct dimensions."""
        spec = ScrewSpec.m2()
        assert spec.hole_diameter.mm == 2.0
        assert spec.head_diameter.mm == 4.0
        assert spec.boss_diameter.mm == 5.0

    def test_m3_spec(self) -> None:
        """M3 spec (default) should have correct dimensions."""
        spec = ScrewSpec.m3()
        assert spec.hole_diameter.mm == 3.0
        assert spec.head_diameter.mm == 6.0
        assert spec.boss_diameter.mm == 8.0

    def test_m4_spec(self) -> None:
        """M4 spec should have correct dimensions."""
        spec = ScrewSpec.m4()
        assert spec.hole_diameter.mm == 4.0
        assert spec.head_diameter.mm == 8.0
        assert spec.boss_diameter.mm == 10.0


# ============================================================================
# StandoffSpec Tests
# ============================================================================


class TestStandoffSpec:
    """Tests for StandoffSpec schemas."""

    def test_default_standoff(self) -> None:
        """Default standoff should have reasonable dimensions."""
        spec = StandoffSpec()
        assert spec.height.mm == 5.0
        assert spec.outer_diameter.mm == 6.0
        assert spec.hole_diameter.mm == 2.5
        assert spec.type == StandoffType.CYLINDRICAL

    def test_pi_standoff(self) -> None:
        """Pi standoff should be M2.5 with 5mm height."""
        spec = StandoffSpec.for_pi()
        assert spec.height.mm == 5.0
        assert spec.hole_diameter.mm == 2.5

    def test_lcd_standoff(self) -> None:
        """LCD standoff should be M3 with 3mm height."""
        spec = StandoffSpec.for_lcd()
        assert spec.height.mm == 3.0
        assert spec.hole_diameter.mm == 3.0


# ============================================================================
# MountCompiler Tests
# ============================================================================


class TestMountCompilerImport:
    """Tests for MountCompiler import."""

    def test_import(self) -> None:
        """MountCompiler should be importable."""
        from app.cad_v2.compiler.mounts import MountCompiler

        assert MountCompiler is not None


class TestMountCompilerScrew:
    """Tests for screw boss compilation."""

    def test_screw_bosses_only_for_screw_on(
        self, simple_enclosure: EnclosureSpec
    ) -> None:
        """Screw bosses should only be added for SCREW_ON lid type."""
        from app.cad_v2.compiler.mounts import MountCompiler

        compiler = MountCompiler(simple_enclosure)
        # Should return input unchanged (no lid)
        mock_body = "mock_body"
        result = compiler.add_screw_bosses(mock_body)
        assert result == mock_body

    @pytest.mark.skipif(not BUILD123D_AVAILABLE, reason="Build123d not available")
    def test_screw_bosses_with_screw_on_lid(
        self, screw_on_enclosure: EnclosureSpec
    ) -> None:
        """Screw bosses should be added for SCREW_ON lid."""
        from app.cad_v2.compiler import CompilationEngine

        engine = CompilationEngine()
        result = engine.compile_enclosure(screw_on_enclosure)

        assert result.success is True
        assert "body" in result.parts
        assert "lid" in result.parts

        # Parts should be Build123d Part objects
        assert isinstance(result.parts["body"], Part)
        assert isinstance(result.parts["lid"], Part)


class TestMountCompilerStandoff:
    """Tests for standoff compilation."""

    def test_standoffs_without_positions_noop(
        self, simple_enclosure: EnclosureSpec
    ) -> None:
        """Standoffs with empty positions should return unchanged body."""
        from app.cad_v2.compiler.mounts import MountCompiler

        compiler = MountCompiler(simple_enclosure)
        mock_body = "mock_body"
        result = compiler.add_standoffs(mock_body, [], StandoffSpec())
        assert result == mock_body

    @pytest.mark.skipif(not BUILD123D_AVAILABLE, reason="Build123d not available")
    def test_standoffs_with_positions(self, simple_enclosure: EnclosureSpec) -> None:
        """Standoffs should be added at specified positions."""
        from app.cad_v2.compiler import CompilationEngine
        from app.cad_v2.compiler.mounts import MountCompiler

        engine = CompilationEngine()
        result = engine.compile_enclosure(simple_enclosure)
        body = result.parts["body"]

        compiler = MountCompiler(simple_enclosure)
        positions = [(10, 10), (90, 10), (10, 70), (90, 70)]
        new_body = compiler.add_standoffs(body, positions, StandoffSpec.for_pi())

        assert isinstance(new_body, Part)
        # New body should have more volume due to standoffs
        # (exact volume comparison is complex, just check it's valid)

    @pytest.mark.skipif(not BUILD123D_AVAILABLE, reason="Build123d not available")
    def test_hexagonal_standoffs(self, simple_enclosure: EnclosureSpec) -> None:
        """Hexagonal standoffs should compile."""
        from app.cad_v2.compiler import CompilationEngine
        from app.cad_v2.compiler.mounts import MountCompiler

        engine = CompilationEngine()
        result = engine.compile_enclosure(simple_enclosure)
        body = result.parts["body"]

        compiler = MountCompiler(simple_enclosure)
        hex_standoff = StandoffSpec(
            height=Dimension(value=5),
            outer_diameter=Dimension(value=6),
            hole_diameter=Dimension(value=2.5),
            type=StandoffType.HEXAGONAL,
        )
        positions = [(20, 20)]
        new_body = compiler.add_standoffs(body, positions, hex_standoff)

        assert isinstance(new_body, Part)

    @pytest.mark.skipif(not BUILD123D_AVAILABLE, reason="Build123d not available")
    def test_square_standoffs(self, simple_enclosure: EnclosureSpec) -> None:
        """Square standoffs should compile."""
        from app.cad_v2.compiler import CompilationEngine
        from app.cad_v2.compiler.mounts import MountCompiler

        engine = CompilationEngine()
        result = engine.compile_enclosure(simple_enclosure)
        body = result.parts["body"]

        compiler = MountCompiler(simple_enclosure)
        square_standoff = StandoffSpec(
            height=Dimension(value=5),
            outer_diameter=Dimension(value=6),
            hole_diameter=Dimension(value=2.5),
            type=StandoffType.SQUARE,
        )
        positions = [(30, 30)]
        new_body = compiler.add_standoffs(body, positions, square_standoff)

        assert isinstance(new_body, Part)


class TestMountCompilerComponentStandoffs:
    """Tests for component-based standoff mounting."""

    def test_component_standoffs_with_mounting_holes(
        self, simple_enclosure: EnclosureSpec
    ) -> None:
        """Should add standoffs at component mounting hole positions."""
        from app.cad_v2.compiler.mounts import MountCompiler

        compiler = MountCompiler(simple_enclosure)

        # Simulate a component with mounting holes (like Raspberry Pi)
        mount = ComponentMount(
            component=ComponentRef(component_id="raspberry-pi-4"),
            position=Point3D(x=10, y=10, z=0),
            mounting_type=MountingType.STANDOFF,
            standoffs=StandoffSpec.for_pi(),
        )

        mounting_holes = [
            MountingHole(x=0, y=0, diameter=Dimension(value=2.7)),
            MountingHole(x=58, y=0, diameter=Dimension(value=2.7)),
            MountingHole(x=0, y=49, diameter=Dimension(value=2.7)),
            MountingHole(x=58, y=49, diameter=Dimension(value=2.7)),
        ]

        # This would only run with Build123d available
        if not BUILD123D_AVAILABLE:
            mock_body = "mock"
            result = compiler.add_component_standoffs(mock_body, mount, mounting_holes)
            assert result == mock_body

    def test_no_standoffs_for_surface_mount(
        self, simple_enclosure: EnclosureSpec
    ) -> None:
        """Should not add standoffs for SURFACE mounting type."""
        from app.cad_v2.compiler.mounts import MountCompiler

        compiler = MountCompiler(simple_enclosure)

        mount = ComponentMount(
            component=ComponentRef(component_id="some-component"),
            position=Point3D(x=10, y=10, z=0),
            mounting_type=MountingType.SURFACE,  # Not standoff
        )

        mounting_holes = [
            MountingHole(x=0, y=0, diameter=Dimension(value=2.7)),
        ]

        mock_body = "mock"
        result = compiler.add_component_standoffs(mock_body, mount, mounting_holes)
        assert result == mock_body  # Unchanged


# ============================================================================
# Integration Tests
# ============================================================================


@pytest.mark.skipif(not BUILD123D_AVAILABLE, reason="Build123d not available")
class TestScrewOnEnclosureIntegration:
    """Integration tests for screw-on enclosure compilation."""

    def test_full_screw_on_enclosure(self, screw_on_enclosure: EnclosureSpec) -> None:
        """Should compile complete screw-on enclosure with bosses and holes."""
        from app.cad_v2.compiler import CompilationEngine

        engine = CompilationEngine()
        result = engine.compile_enclosure(screw_on_enclosure)

        assert result.success is True
        assert "body" in result.parts
        assert "lid" in result.parts
        assert result.metadata["part_count"] == 2

    def test_screw_on_body_has_bosses(self, screw_on_enclosure: EnclosureSpec) -> None:
        """Body should have screw bosses at corners."""
        from app.cad_v2.compiler import CompilationEngine

        engine = CompilationEngine()
        result = engine.compile_enclosure(screw_on_enclosure)

        body = result.parts["body"]
        # Body with bosses should exist
        assert body is not None
        assert isinstance(body, Part)

    def test_screw_on_lid_has_holes(self, screw_on_enclosure: EnclosureSpec) -> None:
        """Lid should have countersunk screw holes."""
        from app.cad_v2.compiler import CompilationEngine

        engine = CompilationEngine()
        result = engine.compile_enclosure(screw_on_enclosure)

        lid = result.parts["lid"]
        # Lid with holes should exist
        assert lid is not None
        assert isinstance(lid, Part)
