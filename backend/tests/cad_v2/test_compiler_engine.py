"""Tests for CAD v2 compilation engine."""

import tempfile

import pytest
from build123d import Box, Part

from app.cad_v2.compiler.engine import (
    CompilationEngine,
    CompilationResult,
    ExportFormat,
)
from app.cad_v2.schemas.base import BoundingBox, Dimension
from app.cad_v2.schemas.enclosure import (
    EnclosureSpec,
    LidSpec,
    LidType,
    SnapFitSpec,
    VentilationSpec,
    WallSide,
    WallSpec,
)


def create_test_part(name: str = "test") -> Part:
    """Create a simple Build123d Part for testing exports.

    Args:
        name: Part identifier (unused, for debugging).

    Returns:
        A simple Box Part that can be exported.
    """
    return Box(10, 10, 10)


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def simple_enclosure() -> EnclosureSpec:
    """Create a simple enclosure spec for testing."""
    return EnclosureSpec(
        exterior=BoundingBox(
            width=Dimension(value=100),
            depth=Dimension(value=80),
            height=Dimension(value=40),
        ),
        walls=WallSpec(thickness=Dimension(value=2.5)),
    )


@pytest.fixture
def enclosure_with_lid() -> EnclosureSpec:
    """Create an enclosure with snap-fit lid."""
    return EnclosureSpec(
        exterior=BoundingBox(
            width=Dimension(value=100),
            depth=Dimension(value=80),
            height=Dimension(value=40),
        ),
        walls=WallSpec(thickness=Dimension(value=2.5)),
        corner_radius=Dimension(value=3),
        lid=LidSpec(
            type=LidType.SNAP_FIT,
            separate_part=True,
            snap_fit=SnapFitSpec(
                lip_height=Dimension(value=4),
                lip_thickness=Dimension(value=1.5),
                clearance=Dimension(value=0.2),
            ),
        ),
    )


@pytest.fixture
def ventilated_enclosure() -> EnclosureSpec:
    """Create an enclosure with ventilation."""
    return EnclosureSpec(
        exterior=BoundingBox(
            width=Dimension(value=100),
            depth=Dimension(value=80),
            height=Dimension(value=40),
        ),
        walls=WallSpec(thickness=Dimension(value=2.5)),
        ventilation=VentilationSpec(
            enabled=True,
            sides=[WallSide.LEFT, WallSide.RIGHT],
            slot_width=Dimension(value=2),
            slot_length=Dimension(value=20),
            slot_spacing=Dimension(value=4),
            margin=Dimension(value=5),
        ),
    )


@pytest.fixture
def engine() -> CompilationEngine:
    """Create a compilation engine instance."""
    return CompilationEngine()


# ============================================================================
# CompilationResult Tests
# ============================================================================


class TestCompilationResult:
    """Tests for CompilationResult class."""

    def test_success_result_has_parts(self) -> None:
        """Successful result should have parts dictionary."""
        result = CompilationResult(
            success=True,
            parts={"body": "mock_part"},
        )
        assert result.success is True
        assert "body" in result.parts

    def test_failed_result_has_errors(self) -> None:
        """Failed result should have error messages."""
        result = CompilationResult(
            success=False,
            errors=["Something went wrong"],
        )
        assert result.success is False
        assert len(result.errors) == 1

    def test_get_part_returns_existing_part(self) -> None:
        """get_part should return existing parts."""
        result = CompilationResult(
            success=True,
            parts={"body": "mock_body", "lid": "mock_lid"},
        )
        assert result.get_part("body") == "mock_body"
        assert result.get_part("lid") == "mock_lid"

    def test_get_part_raises_for_missing(self) -> None:
        """get_part should raise KeyError for missing parts."""
        result = CompilationResult(success=True, parts={"body": "mock"})
        with pytest.raises(KeyError, match="'lid' not found"):
            result.get_part("lid")

    def test_export_fails_on_unsuccessful_result(self) -> None:
        """export should raise error if compilation failed."""
        result = CompilationResult(success=False, errors=["Failed"])
        with pytest.raises(RuntimeError, match="Cannot export failed"):
            result.export("/tmp/output")

    def test_export_creates_files(self) -> None:
        """export should create STEP files with real Build123d parts."""
        result = CompilationResult(
            success=True,
            parts={"body": create_test_part("body")},
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            paths = result.export(tmpdir, ExportFormat.STEP)
            assert len(paths) == 1
            assert paths[0].exists()
            assert paths[0].suffix == ".step"
            # Verify file has content (not just a placeholder)
            assert paths[0].stat().st_size > 100

    def test_export_creates_stl_files(self) -> None:
        """export should create STL files with real Build123d parts."""
        result = CompilationResult(
            success=True,
            parts={"body": create_test_part("body"), "lid": create_test_part("lid")},
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            paths = result.export(tmpdir, ExportFormat.STL)
            assert len(paths) == 2
            assert all(p.suffix == ".stl" for p in paths)
            # Verify files have content
            assert all(p.stat().st_size > 100 for p in paths)

    def test_metadata_stored_correctly(self) -> None:
        """Metadata should be preserved in result."""
        result = CompilationResult(
            success=True,
            parts={},
            metadata={"key": "value", "count": 42},
        )
        assert result.metadata["key"] == "value"
        assert result.metadata["count"] == 42


# ============================================================================
# CompilationEngine Tests
# ============================================================================


class TestCompilationEngine:
    """Tests for CompilationEngine class."""

    def test_engine_initialization(self, engine: CompilationEngine) -> None:
        """Engine should initialize correctly."""
        assert engine is not None
        assert engine._enclosure_compiler is None  # Lazy initialization

    def test_enclosure_compiler_lazy_loaded(self, engine: CompilationEngine) -> None:
        """Enclosure compiler should be lazily initialized."""
        assert engine._enclosure_compiler is None
        compiler = engine.enclosure_compiler
        assert compiler is not None
        assert engine._enclosure_compiler is compiler
        # Second access should return same instance
        assert engine.enclosure_compiler is compiler

    def test_compile_simple_enclosure(
        self, engine: CompilationEngine, simple_enclosure: EnclosureSpec
    ) -> None:
        """Should compile a simple enclosure."""
        result = engine.compile_enclosure(simple_enclosure)
        assert result.success is True
        assert "body" in result.parts

    def test_compile_enclosure_with_lid(
        self, engine: CompilationEngine, enclosure_with_lid: EnclosureSpec
    ) -> None:
        """Should compile enclosure with separate lid."""
        result = engine.compile_enclosure(enclosure_with_lid)
        assert result.success is True
        assert "body" in result.parts
        # Note: lid only compiled when Build123d available
        # Placeholder mode only returns body

    def test_compile_ventilated_enclosure(
        self, engine: CompilationEngine, ventilated_enclosure: EnclosureSpec
    ) -> None:
        """Should compile enclosure with ventilation."""
        result = engine.compile_enclosure(ventilated_enclosure)
        assert result.success is True
        assert "body" in result.parts

    def test_result_contains_metadata(
        self, engine: CompilationEngine, simple_enclosure: EnclosureSpec
    ) -> None:
        """Compilation result should include metadata."""
        result = engine.compile_enclosure(simple_enclosure)
        assert "exterior" in result.metadata
        assert result.metadata["exterior"] == (100.0, 80.0, 40.0)
        assert result.metadata["wall_thickness"] == 2.5


# ============================================================================
# Validation Tests
# ============================================================================


class TestSpecValidation:
    """Tests for specification validation."""

    def test_validate_valid_spec(
        self, engine: CompilationEngine, simple_enclosure: EnclosureSpec
    ) -> None:
        """Valid spec should have no issues."""
        issues = engine.validate_spec(simple_enclosure)
        assert len(issues) == 0

    def test_validate_catches_tiny_enclosure(self, engine: CompilationEngine) -> None:
        """Should warn about enclosures that are too small."""
        tiny = EnclosureSpec(
            exterior=BoundingBox(
                width=Dimension(value=5),
                depth=Dimension(value=5),
                height=Dimension(value=3),
            ),
            walls=WallSpec(thickness=Dimension(value=1)),
        )
        issues = engine.validate_spec(tiny)
        assert len(issues) == 3  # width, depth, height all too small

    def test_validate_catches_thick_walls(self, engine: CompilationEngine) -> None:
        """Should warn about walls that are too thick."""
        thick_walls = EnclosureSpec(
            exterior=BoundingBox(
                width=Dimension(value=40),
                depth=Dimension(value=40),
                height=Dimension(value=20),
            ),
            walls=WallSpec(thickness=Dimension(value=15)),  # 37.5% of width
        )
        issues = engine.validate_spec(thick_walls)
        assert any("Wall thickness" in issue for issue in issues)

    def test_validate_catches_large_corner_radius(self, engine: CompilationEngine) -> None:
        """Should warn about corner radius exceeding limits."""
        large_radius = EnclosureSpec(
            exterior=BoundingBox(
                width=Dimension(value=40),
                depth=Dimension(value=30),
                height=Dimension(value=20),
            ),
            walls=WallSpec(thickness=Dimension(value=2)),
            corner_radius=Dimension(value=20),  # Max would be 15
        )
        issues = engine.validate_spec(large_radius)
        assert any("Corner radius" in issue for issue in issues)


# ============================================================================
# Edge Cases
# ============================================================================


class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_minimum_viable_enclosure(self, engine: CompilationEngine) -> None:
        """Should compile minimum viable enclosure."""
        minimal = EnclosureSpec(
            exterior=BoundingBox(
                width=Dimension(value=10),
                depth=Dimension(value=10),
                height=Dimension(value=5),
            ),
            walls=WallSpec(thickness=Dimension(value=1)),
        )
        result = engine.compile_enclosure(minimal)
        assert result.success is True

    def test_large_enclosure(self, engine: CompilationEngine) -> None:
        """Should compile large enclosure."""
        large = EnclosureSpec(
            exterior=BoundingBox(
                width=Dimension(value=500),
                depth=Dimension(value=400),
                height=Dimension(value=200),
            ),
            walls=WallSpec(thickness=Dimension(value=5)),
        )
        result = engine.compile_enclosure(large)
        assert result.success is True

    def test_fractional_dimensions(self, engine: CompilationEngine) -> None:
        """Should handle fractional dimensions."""
        fractional = EnclosureSpec(
            exterior=BoundingBox(
                width=Dimension(value=100.5),
                depth=Dimension(value=80.25),
                height=Dimension(value=40.125),
            ),
            walls=WallSpec(thickness=Dimension(value=2.54)),  # 0.1 inch
        )
        result = engine.compile_enclosure(fractional)
        assert result.success is True

    def test_zero_corner_radius(self, engine: CompilationEngine) -> None:
        """Should handle zero corner radius."""
        sharp = EnclosureSpec(
            exterior=BoundingBox(
                width=Dimension(value=100),
                depth=Dimension(value=80),
                height=Dimension(value=40),
            ),
            walls=WallSpec(thickness=Dimension(value=2.5)),
            corner_radius=None,  # Sharp corners
        )
        result = engine.compile_enclosure(sharp)
        assert result.success is True
