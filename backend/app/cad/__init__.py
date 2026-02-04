"""
CAD Engine Package (DEPRECATED).

.. deprecated:: 2.0.0
    This module is deprecated. Use :mod:`app.cad_v2` instead.
    The v2 system uses a declarative schema approach with Build123d.

Provides 3D geometry generation using Build123d and OpenCASCADE.

Modules:
    primitives: Basic shape generation (box, cylinder, sphere, cone)
    operations: Boolean and transformation operations
    export: File format export (STEP, STL, OBJ, 3MF)
    templates: Parameterized template implementations
    exceptions: CAD-specific exceptions

Migration Guide:
    - Old: from app.cad import create_box
    - New: from app.cad_v2.compiler import CompilationEngine
    
    - Old: generate_from_template("enclosure", params)
    - New: engine.compile_enclosure(EnclosureSpec(...))
    
    See docs/adrs/adr-016-declarative-cad-schema.md for details.
"""

# IMPORTANT: Apply OCP compatibility patch BEFORE any build123d imports
# This fixes the HashCode() → __hash__() API change in OCP 7.9.x
from app.cad.ocp_compat import apply_ocp_compat_patch  # noqa: E402
apply_ocp_compat_patch()

import warnings

# Emit deprecation warning on import
warnings.warn(
    "app.cad is deprecated and will be removed in v3.0. "
    "Use app.cad_v2 for new enclosure designs. "
    "See docs/adrs/adr-016-declarative-cad-schema.md for migration guide.",
    DeprecationWarning,
    stacklevel=2,
)

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

# Import Gridfinity module to register templates
from app.cad import gridfinity  # noqa: F401

# Import dovetail module to register templates
from app.cad import dovetails  # noqa: F401

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
