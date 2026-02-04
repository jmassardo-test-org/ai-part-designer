"""Tests for CAD export functionality."""

import tempfile
from pathlib import Path
from typing import Any

import pytest
from build123d import Box, Part

from app.cad_v2.compiler.export import (
    ExportError,
    ExportFormat,
    export_part,
    export_parts,
)


def create_test_part() -> Part:
    """Create a simple Build123d Part for testing exports.
    
    Returns:
        A simple Box Part that can be exported.
    """
    return Box(10, 10, 10)


# ============================================================================
# ExportFormat Tests
# ============================================================================


class TestExportFormat:
    """Tests for ExportFormat enum."""

    def test_step_format(self) -> None:
        """STEP format should have correct value."""
        assert ExportFormat.STEP.value == "step"

    def test_stl_format(self) -> None:
        """STL format should have correct value."""
        assert ExportFormat.STL.value == "stl"

    def test_format_is_string(self) -> None:
        """Export format should be a string enum."""
        assert isinstance(ExportFormat.STEP, str)
        assert ExportFormat.STEP == "step"


# ============================================================================
# export_part Tests
# ============================================================================


class TestExportPart:
    """Tests for export_part function."""

    def test_export_infers_step_from_extension(self) -> None:
        """Should infer STEP format from .step extension."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = export_part(create_test_part(), Path(tmpdir) / "output.step")
            assert path.exists()
            assert path.suffix == ".step"
            assert path.stat().st_size > 100  # Real content

    def test_export_infers_stp_extension(self) -> None:
        """Should infer STEP format from .stp extension."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = export_part(create_test_part(), Path(tmpdir) / "output.stp")
            assert path.exists()
            assert path.suffix == ".stp"

    def test_export_infers_stl_from_extension(self) -> None:
        """Should infer STL format from .stl extension."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = export_part(create_test_part(), Path(tmpdir) / "output.stl")
            assert path.exists()
            assert path.suffix == ".stl"

    def test_export_uses_explicit_format(self) -> None:
        """Should use explicitly specified format."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = export_part(
                create_test_part(),
                Path(tmpdir) / "output.step",
                format=ExportFormat.STEP,
            )
            assert path.exists()

    def test_export_raises_for_unknown_extension(self) -> None:
        """Should raise error for unknown extension."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with pytest.raises(ExportError, match="Unknown file extension"):
                export_part(create_test_part(), Path(tmpdir) / "output.xyz")

    def test_export_creates_parent_directory(self) -> None:
        """Should create parent directories if needed."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = export_part(
                create_test_part(),
                Path(tmpdir) / "nested" / "dirs" / "output.step",
            )
            assert path.exists()
            assert path.parent.exists()

    def test_export_returns_absolute_path(self) -> None:
        """Should return absolute path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = export_part(create_test_part(), Path(tmpdir) / "output.step")
            assert path.is_absolute()

    def test_export_file_has_content(self) -> None:
        """Export should create file with real content."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = export_part(create_test_part(), Path(tmpdir) / "output.step")
            # Real STEP file should have substantial content
            content = path.read_text()
            assert "ISO-10303-21" in content or path.stat().st_size > 1000


# ============================================================================
# export_parts Tests
# ============================================================================


class TestExportParts:
    """Tests for export_parts function."""

    def test_export_multiple_parts(self) -> None:
        """Should export multiple parts."""
        with tempfile.TemporaryDirectory() as tmpdir:
            parts = {"body": create_test_part(), "lid": create_test_part()}
            paths = export_parts(parts, tmpdir)
            assert len(paths) == 2
            assert all(p.exists() for p in paths)

    def test_export_parts_with_step_format(self) -> None:
        """Should export as STEP when specified."""
        with tempfile.TemporaryDirectory() as tmpdir:
            parts = {"body": create_test_part()}
            paths = export_parts(parts, tmpdir, format=ExportFormat.STEP)
            assert all(p.suffix == ".step" for p in paths)

    def test_export_parts_with_stl_format(self) -> None:
        """Should export as STL when specified."""
        with tempfile.TemporaryDirectory() as tmpdir:
            parts = {"body": create_test_part()}
            paths = export_parts(parts, tmpdir, format=ExportFormat.STL)
            assert all(p.suffix == ".stl" for p in paths)

    def test_export_parts_with_prefix(self) -> None:
        """Should prepend prefix to filenames."""
        with tempfile.TemporaryDirectory() as tmpdir:
            parts = {"body": create_test_part(), "lid": create_test_part()}
            paths = export_parts(parts, tmpdir, prefix="enclosure_")
            assert any("enclosure_body" in str(p) for p in paths)
            assert any("enclosure_lid" in str(p) for p in paths)

    def test_export_parts_creates_directory(self) -> None:
        """Should create output directory if needed."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir) / "exports" / "cad"
            parts = {"body": create_test_part()}
            paths = export_parts(parts, output_dir)
            assert output_dir.exists()
            assert len(paths) == 1

    def test_export_empty_parts_dict(self) -> None:
        """Should handle empty parts dictionary."""
        with tempfile.TemporaryDirectory() as tmpdir:
            paths = export_parts({}, tmpdir)
            assert len(paths) == 0


# ============================================================================
# Error Handling Tests
# ============================================================================


class TestExportErrorHandling:
    """Tests for export error handling."""

    def test_export_error_message(self) -> None:
        """ExportError should have descriptive message."""
        error = ExportError("Failed to export file.step")
        assert "Failed to export" in str(error)

    def test_export_error_is_exception(self) -> None:
        """ExportError should be an Exception subclass."""
        assert issubclass(ExportError, Exception)

    def test_raises_export_error_for_invalid_extension(self) -> None:
        """Should raise ExportError for unsupported extensions."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with pytest.raises(ExportError):
                export_part("mock", Path(tmpdir) / "test.obj")
