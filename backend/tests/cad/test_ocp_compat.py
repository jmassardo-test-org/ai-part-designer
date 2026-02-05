"""
Tests for OCP compatibility layer.

Tests the monkey-patch that fixes OCP 7.9.x HashCode() → __hash__() compatibility.
"""

from __future__ import annotations


class TestOCPCompatPatch:
    """Tests for the OCP compatibility patch."""

    def test_apply_patch_idempotent(self) -> None:
        """Test that applying the patch multiple times is safe."""
        from app.cad.ocp_compat import apply_ocp_compat_patch, is_patched

        # First application (may already be applied by import)
        apply_ocp_compat_patch()
        assert is_patched()

        # Second application should return False (already patched)
        result2 = apply_ocp_compat_patch()
        assert result2 is False
        assert is_patched()

    def test_is_patched_returns_true_after_import(self) -> None:
        """Test that importing the module applies the patch."""
        from app.cad.ocp_compat import is_patched

        # The patch is auto-applied on module import
        assert is_patched()

    def test_topodsshape_has_hashcode_after_patch(self) -> None:
        """Test that TopoDS_Shape has HashCode method after patch."""
        # Import applies patch
        from app.cad.ocp_compat import apply_ocp_compat_patch

        apply_ocp_compat_patch()

        from OCP.TopoDS import TopoDS_Shape

        assert hasattr(TopoDS_Shape, "HashCode")
        assert callable(getattr(TopoDS_Shape, "HashCode", None))

    def test_hashcode_returns_valid_integer(self) -> None:
        """Test that patched HashCode returns valid integers."""
        from app.cad.ocp_compat import apply_ocp_compat_patch

        apply_ocp_compat_patch()

        from build123d import Box

        box = Box(10, 10, 10)
        # Access the underlying TopoDS_Shape
        wrapped = box.wrapped

        # HashCode should work
        hash_value = wrapped.HashCode(2147483647)

        assert isinstance(hash_value, int)
        assert 0 <= hash_value < 2147483647

    def test_hashcode_with_custom_upper_bound(self) -> None:
        """Test that HashCode respects upper_bound parameter."""
        from app.cad.ocp_compat import apply_ocp_compat_patch

        apply_ocp_compat_patch()

        from build123d import Box

        box = Box(10, 10, 10)
        wrapped = box.wrapped

        # Test with custom upper bound
        hash_value = wrapped.HashCode(1000)

        assert isinstance(hash_value, int)
        assert 0 <= hash_value < 1000


class TestBuild123dEdgeOperations:
    """Tests that Build123d edge operations work after patch."""

    def test_edges_method_works(self) -> None:
        """Test that Part.edges() works after patch."""
        from app.cad import create_box  # This applies the patch

        box = create_box(100, 50, 25)

        # This would fail without the patch
        edges = box.edges()

        # A box has 12 edges
        assert len(edges) == 12

    def test_filter_by_axis_works(self) -> None:
        """Test that edges().filter_by(Axis) works after patch."""
        from build123d import Axis

        from app.cad import create_box

        box = create_box(100, 50, 25)
        edges = box.edges()

        # Filter to vertical edges (parallel to Z axis)
        vertical_edges = edges.filter_by(Axis.Z)

        # A box has 4 vertical edges
        assert len(vertical_edges) == 4

    def test_fillet_operation_works(self) -> None:
        """Test that fillet() works after patch."""
        from build123d import Axis, fillet

        from app.cad import create_box

        box = create_box(100, 50, 25)
        vertical_edges = box.edges().filter_by(Axis.Z)

        # Apply fillet to vertical edges
        result = fillet(vertical_edges, 5)

        # Result should still be a valid Part
        assert result is not None
        assert result.volume > 0
        # Volume should be slightly less due to fillet
        assert result.volume < box.volume

    def test_chamfer_operation_works(self) -> None:
        """Test that chamfer() works after patch."""
        from build123d import Axis, chamfer

        from app.cad import create_box

        box = create_box(100, 50, 25)
        vertical_edges = box.edges().filter_by(Axis.Z)

        # Apply chamfer to vertical edges
        result = chamfer(vertical_edges, 3)

        # Result should still be a valid Part
        assert result is not None
        assert result.volume > 0


class TestCADModulesWorkWithPatch:
    """Integration tests that CAD modules work with the patch."""

    def test_gridfinity_bin_generation(self) -> None:
        """Test that Gridfinity bin generation works."""
        from app.cad.gridfinity import generate_gridfinity_bin

        result = generate_gridfinity_bin(
            grid_x=1,
            grid_y=1,
            height_units=2,
        )

        assert result is not None
        assert result.volume > 0

    def test_gridfinity_baseplate_generation(self) -> None:
        """Test that Gridfinity baseplate generation works."""
        from app.cad.gridfinity import generate_gridfinity_baseplate

        result = generate_gridfinity_baseplate(
            grid_x=2,
            grid_y=2,
        )

        assert result is not None
        assert result.volume > 0

    def test_snap_fit_generation(self) -> None:
        """Test that snap-fit clip generation works."""
        from app.cad.mounting import create_snap_fit

        result = create_snap_fit()

        assert result is not None
        assert result.clip is not None

    def test_din_rail_mount_generation(self) -> None:
        """Test that DIN rail mount generation works."""
        from app.cad.mounting import create_din_rail_mount

        result = create_din_rail_mount()

        assert result is not None
        assert result.mount is not None

    def test_wall_mount_generation(self) -> None:
        """Test that wall mount generation works."""
        from app.cad.mounting import create_wall_mount

        result = create_wall_mount()

        assert result is not None
        assert result.bracket is not None

    def test_enclosure_generation(self) -> None:
        """Test that enclosure generation works."""
        from app.cad.enclosure import EnclosureConfig, EnclosureGenerator

        config = EnclosureConfig(
            length=100,
            width=60,
            height=40,
        )
        generator = EnclosureGenerator(config)
        result = generator.generate()

        assert result is not None
        assert len(result.parts) > 0

    def test_cad_v2_compilation(self) -> None:
        """Test that cad_v2 compilation works."""
        from app.cad_v2.compiler import CompilationEngine
        from app.cad_v2.schemas import BoundingBox, Dimension, EnclosureSpec

        spec = EnclosureSpec(
            exterior=BoundingBox(
                width=Dimension(value=100.0),
                depth=Dimension(value=60.0),
                height=Dimension(value=40.0),
            ),
        )

        engine = CompilationEngine()
        result = engine.compile_enclosure(spec)

        assert result.success
        assert "body" in result.parts
        assert result.parts["body"].volume > 0
