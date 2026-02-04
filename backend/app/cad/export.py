"""
CAD geometry export to STEP and STL formats.

Provides high-quality export with configurable precision for
manufacturing and 3D printing workflows. Uses Build123d as the
CAD engine.

Example:
    >>> from build123d import Box, BuildPart
    >>> from app.cad.export import export_step, export_stl
    >>> with BuildPart() as part:
    ...     Box(50, 50, 25)
    >>> step_data = export_step(part.part)
    >>> stl_data = export_stl(part.part, quality="high")
"""

from __future__ import annotations

import io
import tempfile
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Any

from OCP.STEPControl import STEPControl_Writer, STEPControl_AsIs
from OCP.StlAPI import StlAPI_Writer
from OCP.BRepMesh import BRepMesh_IncrementalMesh
from OCP.Interface import Interface_Static
from OCP.TopoDS import TopoDS_Shape

from app.cad.exceptions import ExportError, ValidationError

if TYPE_CHECKING:
    pass

# Type alias for shapes we can export (Build123d Part or raw OCP shape)
ShapeType = Any  # Build123d Part, Shape, Solid, etc.


def _get_ocp_shape(shape: ShapeType) -> TopoDS_Shape:
    """Extract the underlying OCP TopoDS_Shape from Build123d shape types.
    
    Supports:
    - Build123d Part/Shape/Solid objects (shape.wrapped)
    - Raw TopoDS_Shape objects
    
    Args:
        shape: A CAD shape from Build123d or OCP
        
    Returns:
        The underlying TopoDS_Shape for export
        
    Raises:
        ExportError: If the shape type is not recognized
    """
    # Already a raw OCP shape
    if isinstance(shape, TopoDS_Shape):
        return shape
    
    # Build123d shapes have .wrapped directly
    if hasattr(shape, 'wrapped'):
        wrapped = shape.wrapped
        if isinstance(wrapped, TopoDS_Shape):
            return wrapped
    
    # Try Build123d Part's alternative access patterns
    if hasattr(shape, 'part') and hasattr(shape.part, 'wrapped'):
        return shape.part.wrapped
    
    raise ExportError(
        f"Unsupported shape type: {type(shape).__name__}",
        details={"shape_type": type(shape).__name__}
    )


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
    shape: ShapeType,
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
        shape: CadQuery or Build123d shape to export
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
        # Set STEP metadata using static methods
        if author:
            Interface_Static.SetCVal_s("write.step.product.context", author)
        if organization:
            Interface_Static.SetCVal_s("write.step.assembly", organization)
        
        # Create writer and transfer shape
        writer = STEPControl_Writer()
        ocp_shape = _get_ocp_shape(shape)
        writer.Transfer(ocp_shape, STEPControl_AsIs)
        
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
    shape: ShapeType,
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
        ocp_shape = _get_ocp_shape(shape)
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


def get_mesh_stats(shape: ShapeType, quality: ExportQuality | str = ExportQuality.STANDARD) -> dict:
    """
    Get tessellation statistics for a shape.
    
    Useful for estimating STL file size and complexity before export.
    
    Args:
        shape: CadQuery or Build123d shape to analyze
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
    ocp_shape = _get_ocp_shape(shape)
    mesh = BRepMesh_IncrementalMesh(ocp_shape, linear_tol, False, angular_tol)
    mesh.Perform()
    
    # Count triangles from faces
    from OCP.TopExp import TopExp_Explorer
    from OCP.TopAbs import TopAbs_FACE
    from OCP.BRep import BRep_Tool
    from OCP.TopLoc import TopLoc_Location
    from OCP.TopoDS import TopoDS
    
    vertex_count = 0
    triangle_count = 0
    
    explorer = TopExp_Explorer(ocp_shape, TopAbs_FACE)
    while explorer.More():
        shape = explorer.Current()
        face = TopoDS.Face_s(shape)  # Cast to TopoDS_Face
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


def export_model(
    shape: cq.Workplane,
    path: str | Path,
    *,
    format: str | None = None,
    quality: ExportQuality | str = ExportQuality.STANDARD,
    **kwargs,
) -> Path:
    """
    Export CAD model to file with specified format.
    
    This is a convenience wrapper that supports format specification
    either via path extension or explicit format parameter.
    
    Args:
        shape: CadQuery shape to export
        path: Output file path
        format: Export format (step, stl). If None, inferred from path extension
        quality: Quality preset for STL export
        **kwargs: Additional format-specific options
    
    Returns:
        Path to created file
    
    Raises:
        ValidationError: If format not supported
        ExportError: If export fails
    
    Example:
        >>> box = create_box(50, 50, 50)
        >>> export_model(box, "output/bracket.step")
        >>> export_model(box, "output/bracket.stl", quality="high")
        >>> export_model(box, "output/model", format="step")
    """
    path = Path(path)
    
    # Determine format from explicit param or extension
    if format:
        export_format = format.lower()
        # Ensure path has correct extension
        if not path.suffix:
            path = path.with_suffix(f".{export_format}")
    else:
        export_format = path.suffix.lower().lstrip(".")
    
    # Normalize format names
    format_map = {
        "stp": "step",
        "step": "step",
        "stl": "stl",
    }
    
    normalized_format = format_map.get(export_format)
    if not normalized_format:
        raise ValidationError(
            f"Unsupported export format: {export_format}",
            details={"supported": ["step", "stp", "stl"]}
        )
    
    # Ensure parent directory exists
    path.parent.mkdir(parents=True, exist_ok=True)
    
    # Export based on format
    if normalized_format == "step":
        data = export_step(shape, **kwargs)
    elif normalized_format == "stl":
        data = export_stl(shape, quality=quality, **kwargs)
    else:
        raise ValidationError(f"Unsupported format: {normalized_format}")
    
    path.write_bytes(data)
    return path


def convert_cad_format(
    source_path: str | Path,
    output_path: str | Path,
    target_format: str,
    *,
    quality: ExportQuality | str = ExportQuality.STANDARD,
) -> Path:
    """
    Convert CAD file from one format to another.
    
    Loads a CAD file and re-exports it in the target format.
    Currently supports STEP input and STEP/STL output.
    
    Args:
        source_path: Path to source CAD file
        output_path: Path for output file
        target_format: Target format (step, stl)
        quality: Quality preset for STL output
    
    Returns:
        Path to converted file
    
    Raises:
        ValidationError: If format not supported
        ExportError: If conversion fails
    
    Example:
        >>> convert_cad_format("model.step", "model.stl", "stl")
        >>> convert_cad_format("input.step", "output.step", "step")
    """
    source_path = Path(source_path)
    output_path = Path(output_path)
    
    if not source_path.exists():
        raise ValidationError(
            f"Source file not found: {source_path}",
            details={"path": str(source_path)}
        )
    
    # Load the source file
    source_ext = source_path.suffix.lower()
    
    try:
        if source_ext in (".step", ".stp"):
            # Import STEP file using Build123d
            from build123d import import_step
            shape = import_step(str(source_path))
        elif source_ext == ".stl":
            # STL files are mesh-only, can only convert to limited formats
            raise ValidationError(
                "STL to other format conversion not supported",
                details={"source_format": "stl", "message": "STL is mesh-only and cannot be converted to solid formats"}
            )
        else:
            raise ValidationError(
                f"Unsupported source format: {source_ext}",
                details={"supported_input": [".step", ".stp"]}
            )
    except ValidationError:
        raise
    except Exception as e:
        raise ExportError(
            f"Failed to load source file: {e}",
            details={"source": str(source_path)}
        )
    
    # Export to target format
    target_format = target_format.lower()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    try:
        if target_format in ("step", "stp"):
            data = export_step(shape)
            if not output_path.suffix:
                output_path = output_path.with_suffix(".step")
        elif target_format == "stl":
            data = export_stl(shape, quality=quality)
            if not output_path.suffix:
                output_path = output_path.with_suffix(".stl")
        else:
            raise ValidationError(
                f"Unsupported target format: {target_format}",
                details={"supported_output": ["step", "stp", "stl"]}
            )
        
        output_path.write_bytes(data)
        return output_path
        
    except (ValidationError, ExportError):
        raise
    except Exception as e:
        raise ExportError(
            f"Conversion failed: {e}",
            details={"source": str(source_path), "target_format": target_format}
        )
