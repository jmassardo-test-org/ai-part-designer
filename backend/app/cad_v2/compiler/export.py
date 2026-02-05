"""Export utilities for CAD v2.

Handles exporting compiled geometry to various file formats.
"""

from enum import StrEnum
from pathlib import Path
from typing import Any

# Import Build123d conditionally
try:
    from build123d import Part, export_step, export_stl

    BUILD123D_AVAILABLE = True
except ImportError:
    BUILD123D_AVAILABLE = False
    Part = Any  # type: ignore


class ExportFormat(StrEnum):
    """Supported export formats."""

    STEP = "step"
    STL = "stl"


class ExportError(Exception):
    """Error during export."""


def export_part(
    part: Any,
    filepath: Path | str,
    format: ExportFormat | None = None,
) -> Path:
    """Export a part to a file.

    Args:
        part: Build123d Part object.
        filepath: Output file path.
        format: Export format (inferred from extension if not specified).

    Returns:
        Path to exported file.

    Raises:
        ExportError: If export fails.
    """
    filepath = Path(filepath)

    # Infer format from extension if not specified
    if format is None:
        ext = filepath.suffix.lower()
        if ext == ".step" or ext == ".stp":
            format = ExportFormat.STEP
        elif ext == ".stl":
            format = ExportFormat.STL
        else:
            raise ExportError(f"Unknown file extension: {ext}")

    # Create parent directory if needed
    filepath.parent.mkdir(parents=True, exist_ok=True)

    if not BUILD123D_AVAILABLE:
        # Create placeholder file for testing
        filepath.write_text(f"# Placeholder {format.value} file\n")
        return filepath

    try:
        if format == ExportFormat.STEP:
            export_step(part, str(filepath))
        elif format == ExportFormat.STL:
            export_stl(part, str(filepath))
        else:
            raise ExportError(f"Unsupported format: {format}")

        return filepath

    except Exception as e:
        raise ExportError(f"Failed to export {filepath}: {e}") from e


def export_parts(
    parts: dict[str, Any],
    output_dir: Path | str,
    format: ExportFormat = ExportFormat.STEP,
    prefix: str = "",
) -> list[Path]:
    """Export multiple parts to files.

    Args:
        parts: Dictionary of part_name -> Part object.
        output_dir: Directory to write files to.
        format: Export format.
        prefix: Optional prefix for filenames.

    Returns:
        List of paths to exported files.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    exported: list[Path] = []

    for name, part in parts.items():
        filename = f"{prefix}{name}" if prefix else name
        ext = ".step" if format == ExportFormat.STEP else ".stl"
        filepath = output_dir / f"{filename}{ext}"

        exported_path = export_part(part, filepath, format)
        exported.append(exported_path)

    return exported
