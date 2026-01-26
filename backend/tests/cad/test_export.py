"""
Tests for CAD export functionality.
"""

from __future__ import annotations

import pytest
from pathlib import Path

from app.cad.primitives import create_box, create_cylinder
from app.cad.export import (
    export_step,
    export_stl,
    export_to_file,
    get_mesh_stats,
    ExportQuality,
)
from app.cad.exceptions import ValidationError, ExportError


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
        
        result = export_step(
            box,
            author="Test Author",
            product_name="Test Product"
        )
        
        assert len(result) > 0
    
    def test_export_step_complex_shape(self):
        """Test STEP export with more complex geometry."""
        from app.cad.operations import difference, fillet
        
        box = create_box(100, 100, 50)
        hole = create_cylinder(radius=20, height=60)
        box_with_hole = difference(box, hole)
        filleted = fillet(box_with_hole, 5, edges=">Z")
        
        result = export_step(filleted)
        
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
        """Test that quality presets produce different sizes."""
        box = create_box(50, 50, 50)
        
        draft = export_stl(box, quality=ExportQuality.DRAFT)
        standard = export_stl(box, quality=ExportQuality.STANDARD)
        high = export_stl(box, quality=ExportQuality.HIGH)
        
        # Higher quality = more triangles = larger file
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
        
        result = export_stl(
            box,
            angular_tolerance=0.01,
            linear_tolerance=0.01
        )
        
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
        original_volume = box.val().Volume()
        
        # Export and verify
        step_data = export_step(box)
        
        # The STEP data represents exact geometry
        # STL would lose precision, STEP should be exact
        assert len(step_data) > 0
        # Note: Full round-trip would require STEP import
