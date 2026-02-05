"""
CAD Modification Service.

Provides high-level operations for modifying uploaded CAD files,
including transformations, feature additions, and file combining.

Migrated from CadQuery to Build123d.

Example:
    >>> from app.cad.modifier import CADModifier
    >>> modifier = CADModifier()
    >>> result = await modifier.apply_operations(file_path, operations)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING, Any

from build123d import (
    Axis,
    Part,
    import_step,
    import_stl,
)

from app.cad.exceptions import GeometryError, ImportError, ValidationError
from app.cad.export import ExportQuality
from app.cad.export import export_step as app_export_step
from app.cad.export import export_stl as app_export_stl
from app.cad.operations import (
    add_hole,
    chamfer,
    difference,
    fillet,
    intersection,
    mirror,
    rotate,
    scale,
    shell,
    translate,
    union,
)

if TYPE_CHECKING:
    from pathlib import Path

logger = logging.getLogger(__name__)


class OperationType(StrEnum):
    """Supported modification operations."""

    # Transformations
    TRANSLATE = "translate"
    ROTATE = "rotate"
    SCALE = "scale"
    SCALE_AXIS = "scale_axis"
    MIRROR = "mirror"

    # Features
    FILLET = "fillet"
    CHAMFER = "chamfer"
    SHELL = "shell"
    ADD_HOLE = "add_hole"
    ADD_POCKET = "add_pocket"
    ADD_BOSS = "add_boss"

    # Boolean
    UNION = "union"
    DIFFERENCE = "difference"
    INTERSECTION = "intersection"


@dataclass
class ModifyOperation:
    """
    A single modification operation to apply.

    Attributes:
        type: The type of operation
        params: Parameters for the operation
    """

    type: OperationType
    params: dict[str, Any]

    def validate(self) -> list[str]:
        """Validate operation parameters. Returns list of errors."""
        errors = []

        if self.type == OperationType.TRANSLATE:
            # At least one axis should be specified
            if not any(k in self.params for k in ["x", "y", "z"]):
                errors.append("Translate requires at least one axis (x, y, or z)")

        elif self.type == OperationType.ROTATE:
            if "angle" not in self.params:
                errors.append("Rotate requires 'angle' parameter")

        elif self.type == OperationType.SCALE:
            if "factor" not in self.params:
                errors.append("Scale requires 'factor' parameter")
            elif self.params["factor"] <= 0:
                errors.append("Scale factor must be positive")

        elif self.type == OperationType.SCALE_AXIS:
            if not any(k in self.params for k in ["x", "y", "z"]):
                errors.append("Scale axis requires at least one axis factor")

        elif self.type == OperationType.MIRROR:
            if "plane" not in self.params:
                errors.append("Mirror requires 'plane' parameter (XY, XZ, or YZ)")

        elif self.type == OperationType.FILLET:
            if "radius" not in self.params:
                errors.append("Fillet requires 'radius' parameter")
            elif self.params["radius"] <= 0:
                errors.append("Fillet radius must be positive")

        elif self.type == OperationType.CHAMFER:
            if "distance" not in self.params:
                errors.append("Chamfer requires 'distance' parameter")
            elif self.params["distance"] <= 0:
                errors.append("Chamfer distance must be positive")

        elif self.type == OperationType.SHELL:
            if "thickness" not in self.params:
                errors.append("Shell requires 'thickness' parameter")
            elif self.params["thickness"] == 0:
                errors.append("Shell thickness cannot be zero")

        elif self.type == OperationType.ADD_HOLE:
            if "diameter" not in self.params:
                errors.append("Add hole requires 'diameter' parameter")
            elif self.params["diameter"] <= 0:
                errors.append("Hole diameter must be positive")

        return errors


@dataclass
class ModifyResult:
    """Result of a modification operation."""

    shape: Part
    operations_applied: list[str]
    warnings: list[str]
    geometry_info: dict[str, Any]

    @classmethod
    def from_shape(cls, shape: Part, operations: list[str]) -> ModifyResult:
        """Create result from a shape."""
        # Calculate geometry info
        geometry_info = {
            "volume": round(shape.volume, 3),
            "area": round(shape.area, 3),
        }

        # Get bounding box
        try:
            bbox = shape.bounding_box()
            geometry_info["bounding_box"] = {
                "x": round(bbox.max.X - bbox.min.X, 3),
                "y": round(bbox.max.Y - bbox.min.Y, 3),
                "z": round(bbox.max.Z - bbox.min.Z, 3),
            }
            geometry_info["center"] = {
                "x": round((bbox.min.X + bbox.max.X) / 2, 3),
                "y": round((bbox.min.Y + bbox.max.Y) / 2, 3),
                "z": round((bbox.min.Z + bbox.max.Z) / 2, 3),
            }
        except Exception:
            pass

        return cls(
            shape=shape,
            operations_applied=operations,
            warnings=[],
            geometry_info=geometry_info,
        )


class CADModifier:
    """
    High-level service for modifying CAD geometry.

    Loads CAD files, applies modification operations, and exports results.
    Uses Build123d Part objects instead of CadQuery Workplanes.
    """

    def __init__(self) -> None:
        """Initialize the modifier."""
        self._operation_handlers = {
            OperationType.TRANSLATE: self._apply_translate,
            OperationType.ROTATE: self._apply_rotate,
            OperationType.SCALE: self._apply_scale,
            OperationType.SCALE_AXIS: self._apply_scale_axis,
            OperationType.MIRROR: self._apply_mirror,
            OperationType.FILLET: self._apply_fillet,
            OperationType.CHAMFER: self._apply_chamfer,
            OperationType.SHELL: self._apply_shell,
            OperationType.ADD_HOLE: self._apply_add_hole,
        }

    def load_step(self, file_path: Path) -> Part:
        """
        Load a STEP file into a Build123d Part.

        Args:
            file_path: Path to STEP file

        Returns:
            Build123d Part containing the geometry

        Raises:
            ImportError: If file cannot be loaded
        """
        if not file_path.exists():
            raise ImportError(f"File not found: {file_path}")

        try:
            result = import_step(str(file_path))
            logger.info(f"Loaded STEP file: {file_path}")
            return result
        except Exception as e:
            logger.error(f"Failed to load STEP file: {e}")
            raise ImportError(f"Failed to load STEP file: {e}")

    def load_stl(self, file_path: Path) -> Part:
        """
        Load an STL file into a Build123d Part.

        Note: STL files lose precision and parametric data.

        Args:
            file_path: Path to STL file

        Returns:
            Build123d Part containing the mesh geometry
        """
        if not file_path.exists():
            raise ImportError(f"File not found: {file_path}")

        try:
            result = import_stl(str(file_path))
            logger.info(f"Loaded STL file: {file_path}")
            return result
        except Exception as e:
            logger.error(f"Failed to load STL file: {e}")
            raise ImportError(f"Failed to load STL file: {e}")

    def apply_operations(
        self,
        shape: Part,
        operations: list[ModifyOperation],
    ) -> ModifyResult:
        """
        Apply a sequence of operations to a shape.

        Args:
            shape: Input shape to modify
            operations: List of operations to apply in order

        Returns:
            ModifyResult with modified shape and metadata

        Raises:
            ValidationError: If any operation has invalid parameters
            GeometryError: If an operation fails
        """
        # Validate all operations first
        all_errors = []
        for i, op in enumerate(operations):
            errors = op.validate()
            if errors:
                all_errors.extend([f"Operation {i + 1} ({op.type}): {e}" for e in errors])

        if all_errors:
            raise ValidationError("Invalid operations", details={"errors": all_errors})

        # Apply operations sequentially
        current_shape = shape
        applied = []

        for op in operations:
            handler = self._operation_handlers.get(op.type)
            if not handler:
                raise ValidationError(f"Unsupported operation: {op.type}")

            try:
                current_shape = handler(current_shape, op.params)
                applied.append(f"{op.type.value}: {op.params}")
                logger.debug(f"Applied {op.type.value}")
            except Exception as e:
                raise GeometryError(
                    f"Operation {op.type.value} failed: {e}",
                    details={"operation": op.type.value, "params": op.params},
                )

        return ModifyResult.from_shape(current_shape, applied)

    def combine_shapes(
        self,
        shapes: list[Part],
        operation: str = "union",
    ) -> Part:
        """
        Combine multiple shapes using boolean operations.

        Args:
            shapes: List of shapes to combine
            operation: "union", "difference", or "intersection"

        Returns:
            Combined shape
        """
        if len(shapes) < 2:
            raise ValidationError("At least 2 shapes required for combining")

        if operation == "union":
            return union(*shapes)
        if operation == "difference":
            return difference(shapes[0], *shapes[1:])
        if operation == "intersection":
            return intersection(*shapes)
        raise ValidationError(f"Unknown combine operation: {operation}")

    def export(
        self,
        shape: Part,
        output_path: Path,
        format: str = "step",
        quality: ExportQuality = ExportQuality.STANDARD,
    ) -> Path:
        """
        Export shape to file.

        Args:
            shape: Shape to export
            output_path: Output file path
            format: "step" or "stl"
            quality: STL quality setting

        Returns:
            Path to exported file
        """
        if format.lower() == "step":
            data = app_export_step(shape)
            output_path.write_bytes(data)
        elif format.lower() == "stl":
            data = app_export_stl(shape, quality=quality)
            output_path.write_bytes(data)
        else:
            raise ValidationError(f"Unsupported export format: {format}")

        return output_path

    # =========================================================================
    # Operation Handlers
    # =========================================================================

    def _apply_translate(self, shape: Part, params: dict[str, Any]) -> Part:
        """Apply translation."""
        return translate(
            shape,
            x=params.get("x", 0),
            y=params.get("y", 0),
            z=params.get("z", 0),
        )

    def _apply_rotate(self, shape: Part, params: dict[str, Any]) -> Part:
        """Apply rotation."""
        angle = params["angle"]
        axis_name = params.get("axis", "Z").upper()

        axis_map = {
            "X": Axis.X,
            "Y": Axis.Y,
            "Z": Axis.Z,
        }
        axis = axis_map.get(axis_name, Axis.Z)

        center = (
            params.get("center_x", 0),
            params.get("center_y", 0),
            params.get("center_z", 0),
        )

        return rotate(shape, angle, axis=axis, center=center)

    def _apply_scale(self, shape: Part, params: dict[str, Any]) -> Part:
        """Apply uniform scaling."""
        return scale(shape, params["factor"])

    def _apply_scale_axis(self, shape: Part, params: dict[str, Any]) -> Part:
        """Apply non-uniform scaling per axis."""
        from OCP.BRepBuilderAPI import BRepBuilderAPI_GTransform
        from OCP.gp import gp_GTrsf, gp_Mat

        sx = params.get("x", 1.0)
        sy = params.get("y", 1.0)
        sz = params.get("z", 1.0)

        if sx <= 0 or sy <= 0 or sz <= 0:
            raise ValidationError("All scale factors must be positive")

        # Create non-uniform transformation matrix
        trsf = gp_GTrsf()
        mat = gp_Mat(sx, 0, 0, 0, sy, 0, 0, 0, sz)
        trsf.SetVectorialPart(mat)

        # Apply to underlying wrapped shape
        transformer = BRepBuilderAPI_GTransform(shape.wrapped, trsf, True)

        # Return as Part
        from build123d import Shape

        return Part(Shape(transformer.Shape()).wrapped)

    def _apply_mirror(self, shape: Part, params: dict[str, Any]) -> Part:
        """Apply mirror transformation."""
        return mirror(shape, params["plane"])

    def _apply_fillet(self, shape: Part, params: dict[str, Any]) -> Part:
        """Apply fillet to edges."""
        return fillet(
            shape,
            radius=params["radius"],
            edges=params.get("edges", "all"),
        )

    def _apply_chamfer(self, shape: Part, params: dict[str, Any]) -> Part:
        """Apply chamfer to edges."""
        return chamfer(
            shape,
            distance=params["distance"],
            edges=params.get("edges", "all"),
        )

    def _apply_shell(self, shape: Part, params: dict[str, Any]) -> Part:
        """Apply shell (hollow out)."""
        return shell(
            shape,
            thickness=params["thickness"],
            faces_to_remove=params.get("faces"),
        )

    def _apply_add_hole(self, shape: Part, params: dict[str, Any]) -> Part:
        """Add a hole to the shape."""
        return add_hole(
            shape,
            diameter=params["diameter"],
            depth=params.get("depth"),
            position=(params.get("x", 0), params.get("y", 0)),
            face=params.get("face", ">Z"),
        )


# Module-level instance for convenience
modifier = CADModifier()
