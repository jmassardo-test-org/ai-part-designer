# CAD v2 - Declarative Schema + Build123d Architecture
#
# This module provides a declarative schema-based approach to CAD generation.
# Instead of AI generating raw code, it outputs validated JSON that compiles
# to Build123d geometry.
#
# See: docs/adrs/adr-016-declarative-cad-schema.md

# IMPORTANT: Apply OCP compatibility patch BEFORE any build123d imports
# This fixes the HashCode() → __hash__() API change in OCP 7.9.x
from app.cad.ocp_compat import apply_ocp_compat_patch  # noqa: E402
apply_ocp_compat_patch()

from app.cad_v2.schemas import (
    # Base types
    Axis,
    BoundingBox,
    Dimension,
    Point2D,
    Point3D,
    Rotation,
    Tolerance,
    Unit,
    Vector3D,
    # Component types
    ComponentCategory,
    ComponentDefinition,
    ComponentMount,
    ComponentRef,
    MountingType,
    StandoffSpec,
    # Enclosure types
    EnclosureSpec,
    LidSpec,
    LidType,
    WallSide,
    WallSpec,
    # Feature types
    BaseCutout,
    ButtonCutout,
    DisplayCutout,
    Feature,
    PortCutout,
    RectangleCutout,
    VentPattern,
    # Pattern types
    CircularPattern,
    CustomPattern,
    GridPattern,
    LinearPattern,
    Pattern,
    PatternPresets,
    # Spatial types
    Alignment2D,
    Alignment3D,
    HorizontalAlignment,
    Margin,
    Position,
    RelativePosition,
    VerticalAlignment,
    WallPosition,
)

__all__ = [
    # Base types
    "Axis",
    "BoundingBox",
    "Dimension",
    "Point2D",
    "Point3D",
    "Rotation",
    "Tolerance",
    "Unit",
    "Vector3D",
    # Component types
    "ComponentCategory",
    "ComponentDefinition",
    "ComponentMount",
    "ComponentRef",
    "MountingType",
    "StandoffSpec",
    # Enclosure types
    "EnclosureSpec",
    "LidSpec",
    "LidType",
    "WallSide",
    "WallSpec",
    # Feature types
    "BaseCutout",
    "ButtonCutout",
    "DisplayCutout",
    "Feature",
    "PortCutout",
    "RectangleCutout",
    "VentPattern",
    # Pattern types
    "CircularPattern",
    "CustomPattern",
    "GridPattern",
    "LinearPattern",
    "Pattern",
    "PatternPresets",
    # Spatial types
    "Alignment2D",
    "Alignment3D",
    "HorizontalAlignment",
    "Margin",
    "Position",
    "RelativePosition",
    "VerticalAlignment",
    "WallPosition",
]
