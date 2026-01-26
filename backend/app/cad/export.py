"""
CAD geometry export to STEP and STL formats.

Provides high-quality export with configurable precision for
manufacturing and 3D printing workflows.

Example:
    >>> from app.cad.primitives import create_box
    >>> from app.cad.export import export_step, export_stl
    >>> box = create_box(50, 50, 25)
    >>> step_data = export_step(box)
    >>> stl_data = export_stl(box, quality="high")
"""

from __future__ import annotations

import io
import tempfile
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING

import cadquery as cq
from OCP.STEPControl import STEPControl_Writer, STEPControl_AsIs
from OCP.StlAPI import StlAPI_Writer
from OCP.BRepMesh import BRepMesh_IncrementalMesh
from OCP.Interface import Interface_Static

from app.cad.exceptions import ExportError, ValidationError

if TYPE_CHECKING:
    from typing import Union


class ExportQuality(str, Enum):
    """Export quality presets for STL generation."""
    
    DRAFT = "draft"      # Fast preview, larger file
    STANDARD = "standard"  # Balanced quality/size
    HIGH = "high"        # Fine detail, larger file
    ULTRA = "ultra"      # Maximum detail, slow


class ExportFormat(str, Enum):
    """Supported export formats."""
    
    STEP = "STEP"
    STL = "STL"


# Quality preset configurations (angular_tolerance, linear_tolerance)
QUALITY_PRESETS = {
    ExportQuality.DRAFT: (0.5, 0.5),     # ~5° facets
    ExportQuality.STANDARD: (0.1, 0.1),  # ~1° facets
    ExportQuality.HIGH: (0.05, 0.05),    # ~0.5° facets
    ExportQuality.ULTRA: (0.01, 0.01),   # ~0.1° facets
}


def export_step(
    shape: cq.Workplane,
    *,
    author: str | None = None,
    organization: str | None = None,
    product_name: str = "CAD Export",
) -> bytes:
    """
    Export shape to STEP format (AP214).
    
    STEP is the preferred format for CAD interchange and manufacturing.
    It preserves exact geometry with no tessellation loss.
    
    Args:
        shape: CadQuery shape to export
        author: Author metadata (optional)
        organization: Organization metadata (optional)
        product_name: Product name in STEP header
    
    Returns:
        STEP file content as bytes
    
    Raises:
        ExportError: If export fails
    
    Example:
        >>> box = create_box(100, 50, 25)
        >>> step_bytes = export_step(box, author="Engineer", product_name="Bracket")
        >>> Path("bracket.step").write_bytes(step_bytes)
    """
    try:
        # Set STEP metadata
        if author:
            Interface_Static.SetCVal("write.step.product.context", author)
        if organization:
            Interface_Static.SetCVal("write.step.assembly", organization)
        
        # Create writer and transfer shape
        writer = STEPControl_Writer()
        writer.Transfer(shape.val().wrapped, STEPControl_AsIs)
        
        # Write to temp file (OCP doesn't support direct bytes output)
        with tempfile.NamedTemporaryFile(suffix=".step", delete=False) as f:
            temp_path = f.name
        
        try:
            status = writer.Write(temp_path)
            if status != 1:  # IFSelect_RetDone = 1
                raise ExportError(
                    "STEP write failed",
                    details={"format": "STEP", "status_code": status}
                )
            
            return Path(temp_path).read_bytes()
        finally:
            Path(temp_path).unlink(missing_ok=True)
            
    except ExportError:
        raise
    except Exception as e:
        raise ExportError(
            f"STEP export failed: {e}",
            details={"format": "STEP"}
        )


def export_stl(
    shape: cq.Workplane,
    *,
    quality: ExportQuality | str = ExportQuality.STANDARD,
    binary: bool = True,
    angular_tolerance: float | None = None,
    linear_tolerance: float | None = None,
) -> bytes:
    """
    Export shape to STL format (triangulated mesh).
    
    STL is used for 3D printing and visualization. Uses configurable
    tessellation quality to balance file size vs geometric accuracy.
    
    Args:
        shape: CadQuery shape to export
        quality: Quality preset ("draft", "standard", "high", "ultra")
        binary: True for binary STL (smaller), False for ASCII
        angular_tolerance: Override angular tolerance in radians
        linear_tolerance: Override linear tolerance in mm
    
    Returns:
        STL file content as bytes
    
    Raises:
        ValidationError: If quality preset is invalid
        ExportError: If export fails
    
    Example:
        >>> box = create_box(50, 50, 50)
        >>> stl_draft = export_stl(box, quality="draft")  # Quick preview
        >>> stl_fine = export_stl(box, quality="high")    # For printing
    """
    # Resolve quality preset
    if isinstance(quality, str):
        try:
            quality = ExportQuality(quality.lower())
        except ValueError:
            raise ValidationError(
                f"Invalid quality preset: {quality}",
                details={"valid_presets": [q.value for q in ExportQuality]}
            )
    
    # Get tolerances (custom or preset)
    angular_tol, linear_tol = QUALITY_PRESETS[quality]
    if angular_tolerance is not None:
        angular_tol = angular_tolerance
    if linear_tolerance is not None:
        linear_tol = linear_tolerance
    
    try:
        # Tessellate the shape
        ocp_shape = shape.val().wrapped
        mesh = BRepMesh_IncrementalMesh(ocp_shape, linear_tol, False, angular_tol)
        mesh.Perform()
        
        if not mesh.IsDone():
            raise ExportError(
                "Mesh generation failed",
                details={
                    "format": "STL",
                    "angular_tolerance": angular_tol,
                    "linear_tolerance": linear_tol,
                }
            )
        
        # Configure STL writer
        writer = StlAPI_Writer()
        # ASCIIMode is a property, not a method in newer OCP versions
        writer.ASCIIMode = not binary
        
        # Write to temp file
        with tempfile.NamedTemporaryFile(suffix=".stl", delete=False) as f:
            temp_path = f.name
        
        try:
            success = writer.Write(ocp_shape, temp_path)
            if not success:
                raise ExportError("STL write failed", details={"format": "STL"})
            
            return Path(temp_path).read_bytes()
        finally:
            Path(temp_path).unlink(missing_ok=True)
            
    except ExportError:
        raise
    except Exception as e:
        raise ExportError(
            f"STL export failed: {e}",
            details={"format": "STL"}
        )


def export_to_file(
    shape: cq.Workplane,
    path: str | Path,
    *,
    quality: ExportQuality | str = ExportQuality.STANDARD,
    **kwargs,
) -> Path:
    """
    Export shape to file, inferring format from extension.
    
    Convenience function that automatically selects the right
    export format based on file extension.
    
    Args:
        shape: CadQuery shape to export
        path: Output file path (.step, .stp, .stl)
        quality: Quality preset for STL export
        **kwargs: Additional format-specific options
    
    Returns:
        Path to created file
    
    Raises:
        ValidationError: If file extension not supported
        ExportError: If export fails
    
    Example:
        >>> box = create_box(50, 50, 50)
        >>> export_to_file(box, "output/bracket.step")
        >>> export_to_file(box, "output/bracket.stl", quality="high")
    """
    path = Path(path)
    extension = path.suffix.lower()
    
    # Ensure parent directory exists
    path.parent.mkdir(parents=True, exist_ok=True)
    
    if extension in (".step", ".stp"):
        data = export_step(shape, **kwargs)
    elif extension == ".stl":
        data = export_stl(shape, quality=quality, **kwargs)
    else:
        raise ValidationError(
            f"Unsupported file extension: {extension}",
            details={"supported": [".step", ".stp", ".stl"]}
        )
    
    path.write_bytes(data)
    return path


def export_to_format(
    shape: cq.Workplane,
    format: ExportFormat | str,
    *,
    quality: ExportQuality | str = ExportQuality.STANDARD,
    **kwargs,
) -> bytes:
    """
    Export shape to a specific format.
    
    Args:
        shape: CadQuery shape to export
        format: Export format (STEP, STL)
        quality: Quality preset for STL export
        **kwargs: Additional format-specific options
    
    Returns:
        Bytes of the exported file
    
    Raises:
        ValidationError: If format not supported
        ExportError: If export fails
    """
    if isinstance(format, str):
        format = ExportFormat(format.upper())
    
    if format == ExportFormat.STEP:
        return export_step(shape, **kwargs)
    elif format == ExportFormat.STL:
        return export_stl(shape, quality=quality, **kwargs)
    else:
        raise ValidationError(
            f"Unsupported export format: {format}",
            details={"supported": ["STEP", "STL"]}
        )


def get_mesh_stats(shape: cq.Workplane, quality: ExportQuality | str = ExportQuality.STANDARD) -> dict:
    """
    Get tessellation statistics for a shape.
    
    Useful for estimating STL file size and complexity before export.
    
    Args:
        shape: CadQuery shape to analyze
        quality: Quality preset to use for mesh calculation
    
    Returns:
        Dictionary with vertex_count, triangle_count, estimated_size_bytes
    
    Example:
        >>> box = create_box(50, 50, 50)
        >>> stats = get_mesh_stats(box)
        >>> print(f"Triangles: {stats['triangle_count']}")
    """
    if isinstance(quality, str):
        quality = ExportQuality(quality.lower())
    
    angular_tol, linear_tol = QUALITY_PRESETS[quality]
    
    # Generate mesh
    ocp_shape = shape.val().wrapped
    mesh = BRepMesh_IncrementalMesh(ocp_shape, linear_tol, False, angular_tol)
    mesh.Perform()
    
    # Count triangles from faces
    from OCP.TopExp import TopExp_Explorer
    from OCP.TopAbs import TopAbs_FACE
    from OCP.BRep import BRep_Tool
    from OCP.TopLoc import TopLoc_Location
    
    vertex_count = 0
    triangle_count = 0
    
    explorer = TopExp_Explorer(ocp_shape, TopAbs_FACE)
    while explorer.More():
        face = explorer.Current()
        loc = TopLoc_Location()
        triangulation = BRep_Tool.Triangulation_s(face, loc)
        
        if triangulation is not None:
            vertex_count += triangulation.NbNodes()
            triangle_count += triangulation.NbTriangles()
        
        explorer.Next()
    
    # Estimate STL size (binary: 80 header + 4 count + 50 bytes/triangle)
    estimated_binary = 84 + (50 * triangle_count)
    # ASCII is roughly 200 bytes per triangle
    estimated_ascii = 200 * triangle_count
    
    return {
        "vertex_count": vertex_count,
        "triangle_count": triangle_count,
        "quality": quality.value,
        "estimated_size_binary": estimated_binary,
        "estimated_size_ascii": estimated_ascii,
    }
