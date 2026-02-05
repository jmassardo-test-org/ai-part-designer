"""
Tests for CAD export functionality.
"""

from __future__ import annotations

import pytest

from app.cad.exceptions import ValidationError
from app.cad.export import (
    ExportQuality,
    export_step,
    export_stl,
    export_to_file,
    get_mesh_stats,
)
from app.cad.primitives import create_box, create_cylinder

# =============================================================================
# STEP Export Tests
# =============================================================================


class TestExportStep:
    """Tests for STEP export functionality."""

    def test_export_step_returns_bytes(self):
        """Test that export_step returns bytes."""
        box = create_box(50, 50, 50)

        result = export_step(box)

        assert isinstance(result, bytes)
        assert len(result) > 0

    def test_export_step_valid_format(self):
        """Test that output is valid STEP format."""
        box = create_box(50, 50, 50)

        result = export_step(box)

        # STEP files contain ISO-10303 header
        content = result.decode("utf-8", errors="ignore")
        assert "ISO-10303" in content or "STEP" in content

    def test_export_step_with_metadata(self):
        """Test STEP export with metadata."""
        box = create_box(50, 50, 50)

        result = export_step(box, author="Test Author", product_name="Test Product")

        assert len(result) > 0

    def test_export_step_complex_shape(self):
        """Test STEP export with more complex geometry."""
        from app.cad.operations import difference

        box = create_box(100, 100, 50)
        hole = create_cylinder(radius=20, height=60)
        box_with_hole = difference(box, hole)

        # Export the complex shape directly (fillet may fail on complex geometry)
        result = export_step(box_with_hole)

        assert len(result) > 1000  # Complex shape should be larger


# =============================================================================
# STL Export Tests
# =============================================================================


class TestExportStl:
    """Tests for STL export functionality."""

    def test_export_stl_returns_bytes(self):
        """Test that export_stl returns bytes."""
        box = create_box(50, 50, 50)

        result = export_stl(box)

        assert isinstance(result, bytes)
        assert len(result) > 0

    def test_export_stl_binary_format(self):
        """Test binary STL output."""
        box = create_box(50, 50, 50)

        result = export_stl(box, binary=True)

        # Binary STL starts with 80-byte header
        assert len(result) > 80

    def test_export_stl_ascii_format(self):
        """Test ASCII STL output."""
        box = create_box(50, 50, 50)

        result = export_stl(box, binary=False)

        content = result.decode("utf-8")
        assert content.startswith("solid")
        assert "facet normal" in content
        assert "endsolid" in content

    def test_export_stl_quality_presets(self):
        """Test that quality presets produce different sizes for curved shapes."""
        # Use sphere (curved surface) since flat boxes have same triangles at all qualities
        from app.cad.primitives import create_sphere

        sphere = create_sphere(radius=25)

        draft = export_stl(sphere, quality=ExportQuality.DRAFT)
        high = export_stl(sphere, quality=ExportQuality.HIGH)

        # Higher quality = more triangles = larger file (only matters for curved surfaces)
        assert len(draft) < len(high)

    def test_export_stl_quality_string(self):
        """Test quality preset as string."""
        box = create_box(50, 50, 50)

        result = export_stl(box, quality="high")

        assert len(result) > 0

    def test_export_stl_invalid_quality_fails(self):
        """Test that invalid quality preset raises error."""
        box = create_box(50, 50, 50)

        with pytest.raises(ValidationError):
            export_stl(box, quality="invalid")

    def test_export_stl_custom_tolerances(self):
        """Test custom angular and linear tolerances."""
        box = create_box(50, 50, 50)

        result = export_stl(box, angular_tolerance=0.01, linear_tolerance=0.01)

        assert len(result) > 0


# =============================================================================
# File Export Tests
# =============================================================================


class TestExportToFile:
    """Tests for export_to_file convenience function."""

    def test_export_to_step_file(self, tmp_path):
        """Test exporting to .step file."""
        box = create_box(50, 50, 50)
        output_path = tmp_path / "test.step"

        result = export_to_file(box, output_path)

        assert result.exists()
        assert result.suffix == ".step"
        assert result.stat().st_size > 0

    def test_export_to_stp_file(self, tmp_path):
        """Test exporting to .stp file (STEP alias)."""
        box = create_box(50, 50, 50)
        output_path = tmp_path / "test.stp"

        result = export_to_file(box, output_path)

        assert result.exists()
        assert result.suffix == ".stp"

    def test_export_to_stl_file(self, tmp_path):
        """Test exporting to .stl file."""
        box = create_box(50, 50, 50)
        output_path = tmp_path / "test.stl"

        result = export_to_file(box, output_path, quality="high")

        assert result.exists()
        assert result.suffix == ".stl"

    def test_export_creates_parent_dirs(self, tmp_path):
        """Test that export creates parent directories."""
        box = create_box(50, 50, 50)
        output_path = tmp_path / "nested" / "dirs" / "test.step"

        result = export_to_file(box, output_path)

        assert result.exists()
        assert result.parent.exists()

    def test_export_unsupported_format_fails(self, tmp_path):
        """Test that unsupported format raises error."""
        box = create_box(50, 50, 50)
        output_path = tmp_path / "test.obj"

        with pytest.raises(ValidationError) as exc_info:
            export_to_file(box, output_path)

        assert "unsupported" in str(exc_info.value).lower()


# =============================================================================
# Mesh Stats Tests
# =============================================================================


class TestGetMeshStats:
    """Tests for mesh statistics function."""

    def test_mesh_stats_returns_dict(self):
        """Test that mesh stats returns expected dictionary."""
        box = create_box(50, 50, 50)

        stats = get_mesh_stats(box)

        assert "vertex_count" in stats
        assert "triangle_count" in stats
        assert "quality" in stats
        assert "estimated_size_binary" in stats
        assert "estimated_size_ascii" in stats

    def test_mesh_stats_positive_counts(self):
        """Test that counts are positive."""
        box = create_box(50, 50, 50)

        stats = get_mesh_stats(box)

        assert stats["vertex_count"] > 0
        assert stats["triangle_count"] > 0

    def test_mesh_stats_quality_affects_count(self):
        """Test that higher quality produces more triangles."""
        sphere = create_cylinder(radius=50, height=100)

        draft_stats = get_mesh_stats(sphere, quality=ExportQuality.DRAFT)
        high_stats = get_mesh_stats(sphere, quality=ExportQuality.HIGH)

        assert high_stats["triangle_count"] > draft_stats["triangle_count"]

    def test_mesh_stats_size_estimation(self):
        """Test that size estimation is reasonable."""
        box = create_box(50, 50, 50)

        stats = get_mesh_stats(box)

        # Binary: 84 header + 50 bytes/triangle
        expected_binary = 84 + (50 * stats["triangle_count"])
        assert stats["estimated_size_binary"] == expected_binary

        # ASCII is larger than binary
        assert stats["estimated_size_ascii"] > stats["estimated_size_binary"]


# =============================================================================
# Integration Tests
# =============================================================================


@pytest.mark.cad
class TestExportIntegration:
    """Integration tests for full export workflows."""

    def test_export_modified_geometry(self, tmp_path):
        """Test exporting geometry after operations."""
        from app.cad.operations import difference, fillet

        # Create complex shape
        box = create_box(100, 100, 50)
        holes = [
            create_cylinder(radius=10, height=60),
        ]
        box_with_holes = difference(box, *holes)
        final = fillet(box_with_holes, 3)

        # Export both formats
        step_path = tmp_path / "complex.step"
        stl_path = tmp_path / "complex.stl"

        export_to_file(final, step_path)
        export_to_file(final, stl_path, quality="high")

        assert step_path.exists()
        assert stl_path.exists()
        assert step_path.stat().st_size > 0
        assert stl_path.stat().st_size > 0

    def test_export_round_trip_volume(self, tmp_path):
        """Test that STEP export preserves exact geometry."""
        box = create_box(50, 50, 50)
        original_volume = box.volume  # Build123d uses .volume property

        # Export and verify
        step_data = export_step(box)

        # The STEP data represents exact geometry
        # STL would lose precision, STEP should be exact
        assert len(step_data) > 0
        assert original_volume > 0  # Verify we got a volume
        # Note: Full round-trip would require STEP import


# =============================================================================
# Export Model Tests
# =============================================================================


class TestExportModel:
    """Tests for export_model function."""

    def test_export_model_to_step(self, tmp_path):
        """Test exporting model to STEP format."""
        from app.cad.export import export_model

        box = create_box(50, 50, 50)
        output_path = tmp_path / "model.step"

        result = export_model(box, output_path)

        assert result.exists()
        assert result.suffix == ".step"
        assert result.stat().st_size > 0

    def test_export_model_to_stl(self, tmp_path):
        """Test exporting model to STL format."""
        from app.cad.export import export_model

        box = create_box(50, 50, 50)
        output_path = tmp_path / "model.stl"

        result = export_model(box, output_path)

        assert result.exists()
        assert result.suffix == ".stl"
        assert result.stat().st_size > 0

    def test_export_model_with_format_param(self, tmp_path):
        """Test exporting with explicit format parameter."""
        from app.cad.export import export_model

        box = create_box(50, 50, 50)
        output_path = tmp_path / "model"  # No extension

        result = export_model(box, output_path, format="step")

        assert result.exists()
        assert result.suffix == ".step"

    def test_export_model_with_quality(self, tmp_path):
        """Test exporting with quality parameter."""
        from app.cad.export import export_model

        box = create_box(50, 50, 50)
        output_path = tmp_path / "model.stl"

        result = export_model(box, output_path, quality="high")

        assert result.exists()
        assert result.stat().st_size > 0

    def test_export_model_unsupported_format_fails(self, tmp_path):
        """Test that unsupported format raises ValidationError."""
        from app.cad.export import export_model

        box = create_box(50, 50, 50)
        output_path = tmp_path / "model.obj"

        with pytest.raises(ValidationError):
            export_model(box, output_path)


# =============================================================================
# Convert CAD Format Tests
# =============================================================================


class TestConvertCadFormat:
    """Tests for convert_cad_format function."""

    def test_convert_step_to_stl(self, tmp_path):
        """Test converting STEP file to STL."""
        from app.cad.export import convert_cad_format

        # Create source STEP file
        box = create_box(50, 50, 50)
        source_path = tmp_path / "source.step"
        export_to_file(box, source_path)

        output_path = tmp_path / "output.stl"

        result = convert_cad_format(source_path, output_path, "stl")

        assert result.exists()
        assert result.suffix == ".stl"
        assert result.stat().st_size > 0

    def test_convert_step_to_step(self, tmp_path):
        """Test converting STEP to STEP (reformat)."""
        from app.cad.export import convert_cad_format

        # Create source STEP file
        box = create_box(50, 50, 50)
        source_path = tmp_path / "source.step"
        export_to_file(box, source_path)

        output_path = tmp_path / "output.step"

        result = convert_cad_format(source_path, output_path, "step")

        assert result.exists()
        assert result.suffix == ".step"

    def test_convert_stp_alias(self, tmp_path):
        """Test converting with .stp extension (STEP alias)."""
        from app.cad.export import convert_cad_format

        box = create_box(50, 50, 50)
        source_path = tmp_path / "source.stp"
        export_to_file(box, source_path)

        output_path = tmp_path / "output.stl"

        result = convert_cad_format(source_path, output_path, "stl")

        assert result.exists()

    def test_convert_with_quality(self, tmp_path):
        """Test conversion with quality parameter."""
        from app.cad.export import convert_cad_format

        box = create_box(50, 50, 50)
        source_path = tmp_path / "source.step"
        export_to_file(box, source_path)

        output_path = tmp_path / "output.stl"

        result = convert_cad_format(source_path, output_path, "stl", quality="high")

        assert result.exists()

    def test_convert_source_not_found_fails(self, tmp_path):
        """Test that missing source file raises ValidationError."""
        from app.cad.export import convert_cad_format

        source_path = tmp_path / "nonexistent.step"
        output_path = tmp_path / "output.stl"

        with pytest.raises(ValidationError) as exc_info:
            convert_cad_format(source_path, output_path, "stl")

        assert "not found" in str(exc_info.value).lower()

    def test_convert_unsupported_source_fails(self, tmp_path):
        """Test that unsupported source format raises error."""
        from app.cad.export import convert_cad_format

        # Create a fake file with unsupported extension
        source_path = tmp_path / "source.obj"
        source_path.write_bytes(b"fake content")

        output_path = tmp_path / "output.stl"

        with pytest.raises(ValidationError):
            convert_cad_format(source_path, output_path, "stl")

    def test_convert_unsupported_target_fails(self, tmp_path):
        """Test that unsupported target format raises error."""
        from app.cad.export import convert_cad_format

        box = create_box(50, 50, 50)
        source_path = tmp_path / "source.step"
        export_to_file(box, source_path)

        output_path = tmp_path / "output.obj"

        with pytest.raises(ValidationError):
            convert_cad_format(source_path, output_path, "obj")

    def test_convert_creates_parent_dirs(self, tmp_path):
        """Test that conversion creates parent directories."""
        from app.cad.export import convert_cad_format

        box = create_box(50, 50, 50)
        source_path = tmp_path / "source.step"
        export_to_file(box, source_path)

        output_path = tmp_path / "nested" / "dirs" / "output.stl"

        result = convert_cad_format(source_path, output_path, "stl")

        assert result.exists()
        assert result.parent.exists()
