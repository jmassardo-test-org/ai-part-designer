"""
Alignment service for CAD file positioning and assembly.

Provides operations to align multiple CAD files using various alignment modes:
- Face alignment (coplanar surfaces)
- Edge alignment (parallel/coincident edges)
- Center alignment (bounding box centers)
- Origin alignment (move to origin)

Migrated from CadQuery to Build123d.

Example:
    >>> from app.cad.alignment import AlignmentService, AlignmentMode
    >>> service = AlignmentService()
    >>> result = service.align_shapes(shape1, shape2, AlignmentMode.CENTER)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import StrEnum

from build123d import (
    Axis,
    Location,
    Part,
    Vector,
)

from app.cad.exceptions import GeometryError, ValidationError

logger = logging.getLogger(__name__)


class AlignmentMode(StrEnum):
    """Available alignment modes."""

    FACE = "face"  # Align faces to be coplanar
    EDGE = "edge"  # Align edges to be parallel/coincident
    CENTER = "center"  # Align bounding box centers
    ORIGIN = "origin"  # Move to origin
    STACK_Z = "stack_z"  # Stack on top of each other (Z axis)
    STACK_X = "stack_x"  # Stack side by side (X axis)
    STACK_Y = "stack_y"  # Stack side by side (Y axis)


class AlignmentAxis(StrEnum):
    """Axis for alignment operations."""

    X = "x"
    Y = "y"
    Z = "z"
    XY = "xy"
    XZ = "xz"
    YZ = "yz"
    XYZ = "xyz"


@dataclass
class BoundingBox:
    """Axis-aligned bounding box for a shape."""

    x_min: float
    y_min: float
    z_min: float
    x_max: float
    y_max: float
    z_max: float

    @property
    def center(self) -> tuple[float, float, float]:
        """Get the center point of the bounding box."""
        return (
            (self.x_min + self.x_max) / 2,
            (self.y_min + self.y_max) / 2,
            (self.z_min + self.z_max) / 2,
        )

    @property
    def size(self) -> tuple[float, float, float]:
        """Get the size of the bounding box (length, width, height)."""
        return (
            self.x_max - self.x_min,
            self.y_max - self.y_min,
            self.z_max - self.z_min,
        )

    @property
    def min_point(self) -> tuple[float, float, float]:
        """Get the minimum corner point."""
        return (self.x_min, self.y_min, self.z_min)

    @property
    def max_point(self) -> tuple[float, float, float]:
        """Get the maximum corner point."""
        return (self.x_max, self.y_max, self.z_max)


@dataclass
class TransformationResult:
    """Result of an alignment operation."""

    transformed_shape: Part
    translation: tuple[float, float, float]
    rotation: tuple[float, float, float] | None = None  # Euler angles in degrees
    original_bbox: BoundingBox | None = None
    final_bbox: BoundingBox | None = None


@dataclass
class AlignmentResult:
    """Result of aligning multiple shapes."""

    combined_shape: Part
    transformations: list[TransformationResult]
    total_bbox: BoundingBox


class AlignmentService:
    """
    Service for aligning and combining CAD shapes.

    Supports multiple alignment modes and can combine shapes into assemblies.
    Uses Build123d Part objects instead of CadQuery Workplanes.
    """

    def __init__(self):
        self._tolerance = 1e-6

    def get_bounding_box(self, shape: Part) -> BoundingBox:
        """
        Calculate the axis-aligned bounding box for a shape.

        Args:
            shape: Build123d Part with geometry

        Returns:
            BoundingBox with min/max coordinates
        """
        try:
            # Use Build123d's built-in bounding_box method
            bb = shape.bounding_box()

            return BoundingBox(
                x_min=bb.min.X,
                y_min=bb.min.Y,
                z_min=bb.min.Z,
                x_max=bb.max.X,
                y_max=bb.max.Y,
                z_max=bb.max.Z,
            )
        except Exception as e:
            logger.error(f"Failed to calculate bounding box: {e}")
            raise GeometryError(f"Failed to calculate bounding box: {e}")

    def translate_shape(self, shape: Part, x: float = 0, y: float = 0, z: float = 0) -> Part:
        """
        Translate (move) a shape by the given offsets.

        Args:
            shape: Shape to translate
            x: Translation along X axis
            y: Translation along Y axis
            z: Translation along Z axis

        Returns:
            Translated shape (new Part)
        """
        # Apply translation via Location
        loc = Location(Vector(x, y, z))
        return shape.moved(loc)

    def rotate_shape(
        self,
        shape: Part,
        angle: float,
        axis: AlignmentAxis = AlignmentAxis.Z,
        center: tuple[float, float, float] = (0, 0, 0),
    ) -> Part:
        """
        Rotate a shape around an axis.

        Args:
            shape: Shape to rotate
            angle: Rotation angle in degrees
            axis: Axis to rotate around
            center: Center point for rotation

        Returns:
            Rotated shape (new Part)
        """
        # Map axis enum to Build123d Axis
        axis_map = {
            AlignmentAxis.X: Axis.X,
            AlignmentAxis.Y: Axis.Y,
            AlignmentAxis.Z: Axis.Z,
        }

        if axis not in axis_map:
            raise ValidationError(f"Invalid rotation axis: {axis}. Use X, Y, or Z.")

        build_axis = axis_map[axis]

        # For rotation around a point, we need to translate, rotate, translate back
        cx, cy, cz = center

        # Move to origin, rotate, move back
        moved = self.translate_shape(shape, -cx, -cy, -cz)
        rotated = moved.rotate(build_axis, angle)
        return self.translate_shape(rotated, cx, cy, cz)

    def align_to_origin(self, shape: Part) -> TransformationResult:
        """
        Move shape so its bounding box center is at the origin.

        Args:
            shape: Shape to align

        Returns:
            TransformationResult with aligned shape and transformation data
        """
        bbox = self.get_bounding_box(shape)
        center = bbox.center

        # Translate to center at origin
        translation = (-center[0], -center[1], -center[2])
        translated = self.translate_shape(shape, *translation)

        final_bbox = self.get_bounding_box(translated)

        return TransformationResult(
            transformed_shape=translated,
            translation=translation,
            original_bbox=bbox,
            final_bbox=final_bbox,
        )

    def align_to_ground(self, shape: Part) -> TransformationResult:
        """
        Move shape so its bottom is on the Z=0 plane (ground).

        Args:
            shape: Shape to align

        Returns:
            TransformationResult with grounded shape
        """
        bbox = self.get_bounding_box(shape)

        # Only translate in Z to put bottom at 0
        translation = (0, 0, -bbox.z_min)
        translated = self.translate_shape(shape, *translation)

        final_bbox = self.get_bounding_box(translated)

        return TransformationResult(
            transformed_shape=translated,
            translation=translation,
            original_bbox=bbox,
            final_bbox=final_bbox,
        )

    def align_centers(
        self,
        shape1: Part,
        shape2: Part,
        axes: AlignmentAxis = AlignmentAxis.XYZ,
    ) -> tuple[TransformationResult, TransformationResult]:
        """
        Align two shapes so their bounding box centers coincide.

        Args:
            shape1: Reference shape (stays in place)
            shape2: Shape to move
            axes: Which axes to align

        Returns:
            Tuple of TransformationResults for both shapes
        """
        bbox1 = self.get_bounding_box(shape1)
        bbox2 = self.get_bounding_box(shape2)

        center1 = bbox1.center
        center2 = bbox2.center

        # Calculate translation needed
        tx = (center1[0] - center2[0]) if "x" in axes.value.lower() else 0
        ty = (center1[1] - center2[1]) if "y" in axes.value.lower() else 0
        tz = (center1[2] - center2[2]) if "z" in axes.value.lower() else 0

        translated = self.translate_shape(shape2, tx, ty, tz)
        final_bbox = self.get_bounding_box(translated)

        # Shape1 doesn't move
        result1 = TransformationResult(
            transformed_shape=shape1,
            translation=(0, 0, 0),
            original_bbox=bbox1,
            final_bbox=bbox1,
        )

        result2 = TransformationResult(
            transformed_shape=translated,
            translation=(tx, ty, tz),
            original_bbox=bbox2,
            final_bbox=final_bbox,
        )

        return result1, result2

    def _fuse_parts(self, parts: list[Part]) -> Part:
        """
        Fuse multiple parts into a single part using boolean union.

        Args:
            parts: List of parts to fuse

        Returns:
            Combined Part
        """
        if len(parts) == 0:
            raise ValidationError("Cannot fuse empty list of parts")
        if len(parts) == 1:
            return parts[0]

        result = parts[0]
        for part in parts[1:]:
            result = result.fuse(part)
        return result

    def stack_shapes(
        self,
        shapes: list[Part],
        axis: AlignmentAxis = AlignmentAxis.Z,
        gap: float = 0,
        center_other_axes: bool = True,
    ) -> AlignmentResult:
        """
        Stack multiple shapes along an axis.

        Args:
            shapes: List of shapes to stack
            axis: Axis to stack along (X, Y, or Z)
            gap: Gap between shapes
            center_other_axes: Whether to center shapes on other axes

        Returns:
            AlignmentResult with combined shape and transformations
        """
        if len(shapes) < 2:
            raise ValidationError("Stack requires at least 2 shapes")

        transformations = []
        current_position = 0.0

        axis_map = {
            AlignmentAxis.X: 0,
            AlignmentAxis.Y: 1,
            AlignmentAxis.Z: 2,
        }
        axis_idx = axis_map.get(axis, 2)

        for _i, shape in enumerate(shapes):
            bbox = self.get_bounding_box(shape)
            size = bbox.size
            center = bbox.center

            # Calculate translation
            translation = [0.0, 0.0, 0.0]

            # Center on other axes if requested
            if center_other_axes:
                for j in range(3):
                    if j != axis_idx:
                        translation[j] = -center[j]

            # Position along stack axis
            # Move so min edge is at current_position
            min_coords = [bbox.x_min, bbox.y_min, bbox.z_min]
            translation[axis_idx] = current_position - min_coords[axis_idx]

            translated = self.translate_shape(shape, *translation)
            final_bbox = self.get_bounding_box(translated)

            transformations.append(
                TransformationResult(
                    transformed_shape=translated,
                    translation=tuple(translation),
                    original_bbox=bbox,
                    final_bbox=final_bbox,
                )
            )

            # Update position for next shape
            current_position += size[axis_idx] + gap

        # Combine all shapes
        combined = self._fuse_parts([t.transformed_shape for t in transformations])

        total_bbox = self.get_bounding_box(combined)

        return AlignmentResult(
            combined_shape=combined,
            transformations=transformations,
            total_bbox=total_bbox,
        )

    def side_by_side(
        self,
        shapes: list[Part],
        axis: AlignmentAxis = AlignmentAxis.X,
        gap: float = 10,
        align_bottoms: bool = True,
    ) -> AlignmentResult:
        """
        Arrange shapes side by side along an axis.

        Args:
            shapes: Shapes to arrange
            axis: Axis to arrange along
            gap: Gap between shapes
            align_bottoms: Whether to align bottom surfaces

        Returns:
            AlignmentResult with arranged shapes
        """
        return self.stack_shapes(shapes, axis=axis, gap=gap, center_other_axes=not align_bottoms)

    def align_shapes(
        self,
        reference: Part,
        target: Part,
        mode: AlignmentMode,
        options: dict | None = None,
    ) -> AlignmentResult:
        """
        Align target shape to reference shape using specified mode.

        Args:
            reference: Reference shape (stays in place)
            target: Shape to move/align
            mode: Alignment mode to use
            options: Additional options for specific modes

        Returns:
            AlignmentResult with aligned shapes
        """
        options = options or {}

        if mode == AlignmentMode.ORIGIN:
            result = self.align_to_origin(target)
            total_bbox = result.final_bbox
            return AlignmentResult(
                combined_shape=result.transformed_shape,
                transformations=[result],
                total_bbox=total_bbox,
            )

        if mode == AlignmentMode.CENTER:
            axes = options.get("axes", AlignmentAxis.XYZ)
            result1, result2 = self.align_centers(reference, target, axes)
            combined = self._fuse_parts([result1.transformed_shape, result2.transformed_shape])
            total_bbox = self.get_bounding_box(combined)
            return AlignmentResult(
                combined_shape=combined,
                transformations=[result1, result2],
                total_bbox=total_bbox,
            )

        if mode == AlignmentMode.STACK_Z:
            return self.stack_shapes(
                [reference, target], AlignmentAxis.Z, gap=options.get("gap", 0)
            )

        if mode == AlignmentMode.STACK_X:
            return self.stack_shapes(
                [reference, target], AlignmentAxis.X, gap=options.get("gap", 0)
            )

        if mode == AlignmentMode.STACK_Y:
            return self.stack_shapes(
                [reference, target], AlignmentAxis.Y, gap=options.get("gap", 0)
            )

        if mode == AlignmentMode.FACE:
            # Align face to face (place target on top of reference)
            bbox_ref = self.get_bounding_box(reference)
            bbox_target = self.get_bounding_box(target)

            # Center horizontally, place on top
            tx = bbox_ref.center[0] - bbox_target.center[0]
            ty = bbox_ref.center[1] - bbox_target.center[1]
            tz = bbox_ref.z_max - bbox_target.z_min

            translated = self.translate_shape(target, tx, ty, tz)
            combined = self._fuse_parts([reference, translated])

            final_bbox = self.get_bounding_box(translated)
            total_bbox = self.get_bounding_box(combined)

            return AlignmentResult(
                combined_shape=combined,
                transformations=[
                    TransformationResult(
                        transformed_shape=reference,
                        translation=(0, 0, 0),
                        original_bbox=bbox_ref,
                        final_bbox=bbox_ref,
                    ),
                    TransformationResult(
                        transformed_shape=translated,
                        translation=(tx, ty, tz),
                        original_bbox=bbox_target,
                        final_bbox=final_bbox,
                    ),
                ],
                total_bbox=total_bbox,
            )

        if mode == AlignmentMode.EDGE:
            # Align edges - align left edges by default
            bbox_ref = self.get_bounding_box(reference)
            bbox_target = self.get_bounding_box(target)

            # Align left edges (x_min) and bottom (z_min)
            tx = bbox_ref.x_min - bbox_target.x_min
            ty = bbox_ref.y_min - bbox_target.y_min
            tz = bbox_ref.z_min - bbox_target.z_min

            translated = self.translate_shape(target, tx, ty, tz)
            combined = self._fuse_parts([reference, translated])

            final_bbox = self.get_bounding_box(translated)
            total_bbox = self.get_bounding_box(combined)

            return AlignmentResult(
                combined_shape=combined,
                transformations=[
                    TransformationResult(
                        transformed_shape=reference,
                        translation=(0, 0, 0),
                        original_bbox=bbox_ref,
                        final_bbox=bbox_ref,
                    ),
                    TransformationResult(
                        transformed_shape=translated,
                        translation=(tx, ty, tz),
                        original_bbox=bbox_target,
                        final_bbox=final_bbox,
                    ),
                ],
                total_bbox=total_bbox,
            )

        raise ValidationError(f"Unknown alignment mode: {mode}")

    def combine_shapes(
        self,
        shapes: list[Part],
        operation: str = "union",
    ) -> Part:
        """
        Combine multiple shapes using boolean operations.

        Args:
            shapes: List of shapes to combine
            operation: Boolean operation (union, intersect, cut)

        Returns:
            Combined shape
        """
        if len(shapes) < 2:
            raise ValidationError("Combine requires at least 2 shapes")

        result = shapes[0]

        for shape in shapes[1:]:
            if operation == "union":
                result = result.fuse(shape)
            elif operation == "intersect":
                result = result.intersect(shape)
            elif operation == "cut":
                result = result.cut(shape)
            else:
                raise ValidationError(f"Unknown operation: {operation}")

        return result
