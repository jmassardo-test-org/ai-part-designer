"""
Integration tests for CAD v2 generation workflows.

Tests end-to-end v2 generation from schema compilation to file export.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from app.cad_v2.compiler.engine import CompilationEngine
from app.cad_v2.compiler.export import ExportFormat
from app.cad_v2.schemas.enclosure import (
    BoundingBox,
    Dimension,
    EnclosureSpec,
    LidSpec,
    LidType,
    VentilationSpec,
    WallSpec,
)

if TYPE_CHECKING:
    from pathlib import Path

# =============================================================================
# CAD v2 Compilation Integration Tests
# =============================================================================


class TestCADV2CompilationIntegration:
    """Integration tests for v2 enclosure compilation."""

    def test_compile_simple_box_produces_valid_geometry(self):
        """Test that simple box compilation produces valid geometry."""
        spec = EnclosureSpec(
            exterior=BoundingBox(
                width=Dimension(value=100),
                depth=Dimension(value=80),
                height=Dimension(value=50),
            ),
            walls=WallSpec(thickness=Dimension(value=2)),
        )

        engine = CompilationEngine()
        result = engine.compile_enclosure(spec)

        assert result.success
        assert "body" in result.parts
        assert len(result.errors) == 0

    def test_compile_with_snap_fit_lid(self):
        """Test compilation with snap-fit lid produces two parts."""
        spec = EnclosureSpec(
            exterior=BoundingBox(
                width=Dimension(value=120),
                depth=Dimension(value=80),
                height=Dimension(value=60),
            ),
            walls=WallSpec(thickness=Dimension(value=2.5)),
            corner_radius=Dimension(value=5),
            lid=LidSpec(type=LidType.SNAP_FIT, side="top"),
        )

        engine = CompilationEngine()
        result = engine.compile_enclosure(spec)

        assert result.success
        assert "body" in result.parts
        assert "lid" in result.parts
        assert len(result.parts) >= 2

    def test_compile_with_ventilation(self):
        """Test compilation with ventilation slots."""
        spec = EnclosureSpec(
            exterior=BoundingBox(
                width=Dimension(value=100),
                depth=Dimension(value=80),
                height=Dimension(value=50),
            ),
            walls=WallSpec(thickness=Dimension(value=2)),
            ventilation=VentilationSpec(
                enabled=True,
                sides=["left", "right"],
                pattern="slots",
            ),
        )

        engine = CompilationEngine()
        result = engine.compile_enclosure(spec)

        assert result.success
        # Ventilation should not cause errors
        assert len(result.errors) == 0

    def test_compile_exports_to_step(self, tmp_path: Path):
        """Test that compilation can export STEP files."""
        spec = EnclosureSpec(
            exterior=BoundingBox(
                width=Dimension(value=80),
                depth=Dimension(value=60),
                height=Dimension(value=40),
            ),
            walls=WallSpec(thickness=Dimension(value=2)),
        )

        engine = CompilationEngine()
        result = engine.compile_enclosure(spec)

        assert result.success

        # Export to STEP
        result.export(tmp_path, ExportFormat.STEP)

        # Check files exist
        step_file = tmp_path / "body.step"
        assert step_file.exists()
        assert step_file.stat().st_size > 1000  # Should be meaningful content

    def test_compile_exports_to_stl(self, tmp_path: Path):
        """Test that compilation can export STL files."""
        spec = EnclosureSpec(
            exterior=BoundingBox(
                width=Dimension(value=80),
                depth=Dimension(value=60),
                height=Dimension(value=40),
            ),
            walls=WallSpec(thickness=Dimension(value=2)),
        )

        engine = CompilationEngine()
        result = engine.compile_enclosure(spec)

        assert result.success

        # Export to STL
        result.export(tmp_path, ExportFormat.STL)

        # Check files exist
        stl_file = tmp_path / "body.stl"
        assert stl_file.exists()
        assert stl_file.stat().st_size > 500  # Should be meaningful content

    def test_compile_with_all_features(self, tmp_path: Path):
        """Test compilation with all major features enabled."""
        spec = EnclosureSpec(
            exterior=BoundingBox(
                width=Dimension(value=150),
                depth=Dimension(value=100),
                height=Dimension(value=60),
            ),
            walls=WallSpec(thickness=Dimension(value=2.5)),
            corner_radius=Dimension(value=5),
            lid=LidSpec(
                type=LidType.SNAP_FIT,
                side="top",
                gap=Dimension(value=0.3),
            ),
            ventilation=VentilationSpec(
                enabled=True,
                sides=["left", "right"],
                pattern="slots",
            ),
        )

        engine = CompilationEngine()
        result = engine.compile_enclosure(spec)

        assert result.success
        assert len(result.parts) >= 2  # body + lid

        # Export both formats
        result.export(tmp_path, ExportFormat.STEP)
        result.export(tmp_path, ExportFormat.STL)

        # All files should exist
        assert (tmp_path / "body.step").exists()
        assert (tmp_path / "body.stl").exists()
        assert (tmp_path / "lid.step").exists()
        assert (tmp_path / "lid.stl").exists()


# =============================================================================
# CAD v2 Error Handling Integration Tests
# =============================================================================


class TestCADV2ErrorHandling:
    """Integration tests for v2 error handling."""

    def test_invalid_dimensions_caught_by_validation(self):
        """Test that invalid dimensions are caught by Pydantic validation."""
        # Wall thickness larger than box dimensions is caught by validation
        with pytest.raises(Exception):
            EnclosureSpec(
                exterior=BoundingBox(
                    width=Dimension(value=10),
                    depth=Dimension(value=10),
                    height=Dimension(value=10),
                ),
                walls=WallSpec(thickness=Dimension(value=10)),  # Invalid - causes negative interior
            )

    def test_zero_dimension_handled(self):
        """Test that zero/negative dimensions are handled."""
        # This should be caught by Pydantic validation
        with pytest.raises(Exception):
            EnclosureSpec(
                exterior=BoundingBox(
                    width=Dimension(value=0),
                    depth=Dimension(value=80),
                    height=Dimension(value=50),
                ),
            )


# =============================================================================
# CAD v2 Metadata Tests
# =============================================================================


class TestCADV2Metadata:
    """Integration tests for v2 result metadata."""

    def test_result_contains_metadata(self):
        """Test that compilation result includes useful metadata."""
        spec = EnclosureSpec(
            exterior=BoundingBox(
                width=Dimension(value=100),
                depth=Dimension(value=80),
                height=Dimension(value=50),
            ),
            walls=WallSpec(thickness=Dimension(value=2)),
        )

        engine = CompilationEngine()
        result = engine.compile_enclosure(spec)

        assert result.success

        # Should have metadata about dimensions
        assert result.metadata is not None
        assert (
            "exterior" in result.metadata
            or "dimensions" in result.metadata
            or len(result.metadata) > 0
        )
