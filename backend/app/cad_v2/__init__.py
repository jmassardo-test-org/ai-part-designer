# CAD v2 - Declarative Schema + Build123d Architecture
#
# This module provides a declarative schema-based approach to CAD generation.
# Instead of AI generating raw code, it outputs validated JSON that compiles
# to Build123d geometry.
#
# See: docs/adrs/adr-016-declarative-cad-schema.md

# IMPORTANT: Apply OCP compatibility patch BEFORE any build123d imports
# This fixes the HashCode() → __hash__() API change in OCP 7.9.x
from app.cad.ocp_compat import apply_ocp_compat_patch

apply_ocp_compat_patch()

from app.cad_v2.schemas import (
    # Spatial types
    Alignment2D,
    Alignment3D,
    # Base types
    Axis,
    # Feature types
    BaseCutout,
    BoundingBox,
    ButtonCutout,
    # Pattern types
    CircularPattern,
    # Component types
    ComponentCategory,
    ComponentDefinition,
    ComponentMount,
    ComponentRef,
    CustomPattern,
    Dimension,
    DisplayCutout,
    # Enclosure types
    EnclosureSpec,
    Feature,
    GridPattern,
    HorizontalAlignment,
    LidSpec,
    LidType,
    LinearPattern,
    Margin,
    MountingType,
    Pattern,
    PatternPresets,
    Point2D,
    Point3D,
    PortCutout,
    Position,
    RectangleCutout,
    RelativePosition,
    Rotation,
    StandoffSpec,
    Tolerance,
    Unit,
    Vector3D,
    VentPattern,
    VerticalAlignment,
    WallPosition,
    WallSide,
    WallSpec,
)

__all__ = [
    # Spatial types
    "Alignment2D",
    "Alignment3D",
    # Base types
    "Axis",
    # Feature types
    "BaseCutout",
    "BoundingBox",
    "ButtonCutout",
    # Pattern types
    "CircularPattern",
    # Component types
    "ComponentCategory",
    "ComponentDefinition",
    "ComponentMount",
    "ComponentRef",
    "CustomPattern",
    "Dimension",
    "DisplayCutout",
    # Enclosure types
    "EnclosureSpec",
    "Feature",
    "GridPattern",
    "HorizontalAlignment",
    "LidSpec",
    "LidType",
    "LinearPattern",
    "Margin",
    "MountingType",
    "Pattern",
    "PatternPresets",
    "Point2D",
    "Point3D",
    "PortCutout",
    "Position",
    "RectangleCutout",
    "RelativePosition",
    "Rotation",
    "StandoffSpec",
    "Tolerance",
    "Unit",
    "Vector3D",
    "VentPattern",
    "VerticalAlignment",
    "WallPosition",
    "WallSide",
    "WallSpec",
]
