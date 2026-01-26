"""
CAD Engine Package.

Provides 3D geometry generation using CadQuery and OpenCASCADE.

Modules:
    primitives: Basic shape generation (box, cylinder, sphere, cone)
    operations: Boolean and transformation operations
    export: File format export (STEP, STL, OBJ, 3MF)
    templates: Parameterized template implementations
    exceptions: CAD-specific exceptions
"""

from app.cad.exceptions import CADError, GeometryError, ExportError
from app.cad.primitives import (
    create_box,
    create_cylinder,
    create_sphere,
    create_cone,
)
from app.cad.operations import (
    union,
    difference,
    intersection,
    translate,
    rotate,
    scale,
    fillet,
    chamfer,
)
from app.cad.export import (
    export_step,
    export_stl,
    export_to_format,
    ExportFormat,
    ExportQuality,
)
from app.cad.templates import (
    generate_from_template,
    get_template_generator,
    register_template,
    TEMPLATE_REGISTRY,
)

__all__ = [
    # Exceptions
    "CADError",
    "GeometryError",
    "ExportError",
    # Primitives
    "create_box",
    "create_cylinder",
    "create_sphere",
    "create_cone",
    # Operations
    "union",
    "difference",
    "intersection",
    "translate",
    "rotate",
    "scale",
    "fillet",
    "chamfer",
    # Export
    "export_step",
    "export_stl",
    "export_to_format",
    "ExportFormat",
    "ExportQuality",
    # Templates
    "generate_from_template",
    "get_template_generator",
    "register_template",
    "TEMPLATE_REGISTRY",
]
