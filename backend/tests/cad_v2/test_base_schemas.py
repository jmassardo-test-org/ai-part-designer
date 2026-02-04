"""Tests for CAD v2 base schemas."""

import pytest
from pydantic import ValidationError

from app.cad_v2.schemas.base import (
    Axis,
    BoundingBox,
    Dimension,
    Point2D,
    Point3D,
    Rotation,
    Tolerance,
    Unit,
    Vector3D,
)


class TestDimension:
    """Tests for Dimension schema."""

    def test_dimension_defaults_to_millimeters(self) -> None:
        """Dimension should default to millimeters."""
        dim = Dimension(value=10)
        assert dim.unit == Unit.MILLIMETERS
        assert dim.value == 10

    def test_dimension_with_inches(self) -> None:
        """Dimension should accept inches."""
        dim = Dimension(value=2.5, unit=Unit.INCHES)
        assert dim.unit == Unit.INCHES
        assert dim.value == 2.5

    def test_dimension_mm_conversion(self) -> None:
        """Dimension.mm should return value in millimeters."""
        dim_mm = Dimension(value=25.4)
        assert dim_mm.mm == 25.4

        dim_in = Dimension(value=1.0, unit=Unit.INCHES)
        assert dim_in.mm == pytest.approx(25.4)

    def test_dimension_inches_conversion(self) -> None:
        """Dimension.inches should return value in inches."""
        dim_in = Dimension(value=1.0, unit=Unit.INCHES)
        assert dim_in.inches == 1.0

        dim_mm = Dimension(value=25.4)
        assert dim_mm.inches == pytest.approx(1.0)

    def test_dimension_rejects_zero(self) -> None:
        """Dimension should reject zero values."""
        with pytest.raises(ValidationError) as exc_info:
            Dimension(value=0)
        assert "greater than 0" in str(exc_info.value)

    def test_dimension_rejects_negative(self) -> None:
        """Dimension should reject negative values."""
        with pytest.raises(ValidationError):
            Dimension(value=-5)

    def test_dimension_str_representation(self) -> None:
        """Dimension __str__ should return human-readable format."""
        dim = Dimension(value=10.5)
        assert str(dim) == "10.5mm"

        dim_in = Dimension(value=2, unit=Unit.INCHES)
        assert str(dim_in) == "2.0in"

    def test_dimension_is_frozen(self) -> None:
        """Dimension should be immutable."""
        dim = Dimension(value=10)
        with pytest.raises(ValidationError):
            dim.value = 20  # type: ignore


class TestPoint2D:
    """Tests for Point2D schema."""

    def test_point2d_defaults_to_origin(self) -> None:
        """Point2D should default to (0, 0)."""
        point = Point2D()
        assert point.x == 0.0
        assert point.y == 0.0

    def test_point2d_with_values(self) -> None:
        """Point2D should accept x and y values."""
        point = Point2D(x=10.5, y=-5.3)
        assert point.x == 10.5
        assert point.y == -5.3

    def test_point2d_to_tuple(self) -> None:
        """Point2D.to_tuple should return (x, y) tuple."""
        point = Point2D(x=3, y=4)
        assert point.to_tuple() == (3, 4)


class TestPoint3D:
    """Tests for Point3D schema."""

    def test_point3d_defaults_to_origin(self) -> None:
        """Point3D should default to (0, 0, 0)."""
        point = Point3D()
        assert point.x == 0.0
        assert point.y == 0.0
        assert point.z == 0.0

    def test_point3d_with_values(self) -> None:
        """Point3D should accept x, y, and z values."""
        point = Point3D(x=1, y=2, z=3)
        assert point.x == 1
        assert point.y == 2
        assert point.z == 3

    def test_point3d_to_tuple(self) -> None:
        """Point3D.to_tuple should return (x, y, z) tuple."""
        point = Point3D(x=1, y=2, z=3)
        assert point.to_tuple() == (1, 2, 3)


class TestVector3D:
    """Tests for Vector3D schema."""

    def test_vector3d_with_values(self) -> None:
        """Vector3D should accept component values."""
        vec = Vector3D(x=1, y=0, z=0)
        assert vec.x == 1
        assert vec.y == 0
        assert vec.z == 0

    def test_vector3d_rejects_zero_vector(self) -> None:
        """Vector3D should reject zero-length vector."""
        with pytest.raises(ValidationError) as exc_info:
            Vector3D(x=0, y=0, z=0)
        assert "cannot be zero-length" in str(exc_info.value)

    def test_vector3d_to_tuple(self) -> None:
        """Vector3D.to_tuple should return (x, y, z) tuple."""
        vec = Vector3D(x=1, y=2, z=3)
        assert vec.to_tuple() == (1, 2, 3)


class TestRotation:
    """Tests for Rotation schema."""

    def test_rotation_defaults_to_identity(self) -> None:
        """Rotation should default to no rotation."""
        rot = Rotation()
        assert rot.x == 0.0
        assert rot.y == 0.0
        assert rot.z == 0.0
        assert rot.is_identity()

    def test_rotation_with_values(self) -> None:
        """Rotation should accept angle values."""
        rot = Rotation(x=45, y=90, z=180)
        assert rot.x == 45
        assert rot.y == 90
        assert rot.z == 180
        assert not rot.is_identity()

    def test_rotation_validates_range(self) -> None:
        """Rotation should validate angle ranges."""
        # Valid at boundaries
        Rotation(x=-360, y=360, z=0)

        # Invalid beyond range
        with pytest.raises(ValidationError):
            Rotation(x=361)
        with pytest.raises(ValidationError):
            Rotation(y=-361)


class TestBoundingBox:
    """Tests for BoundingBox schema."""

    def test_boundingbox_creation(self) -> None:
        """BoundingBox should accept width, depth, height."""
        box = BoundingBox(
            width=Dimension(value=100),
            depth=Dimension(value=80),
            height=Dimension(value=40),
        )
        assert box.width_mm == 100
        assert box.depth_mm == 80
        assert box.height_mm == 40

    def test_boundingbox_volume(self) -> None:
        """BoundingBox.volume_mm3 should calculate volume."""
        box = BoundingBox(
            width=Dimension(value=10),
            depth=Dimension(value=20),
            height=Dimension(value=5),
        )
        assert box.volume_mm3 == 1000

    def test_boundingbox_to_tuple_mm(self) -> None:
        """BoundingBox.to_tuple_mm should return (w, d, h) tuple."""
        box = BoundingBox(
            width=Dimension(value=100),
            depth=Dimension(value=80),
            height=Dimension(value=40),
        )
        assert box.to_tuple_mm() == (100, 80, 40)

    def test_boundingbox_str_representation(self) -> None:
        """BoundingBox __str__ should return readable format."""
        box = BoundingBox(
            width=Dimension(value=100),
            depth=Dimension(value=80),
            height=Dimension(value=40),
        )
        assert "100" in str(box)
        assert "80" in str(box)
        assert "40" in str(box)

    def test_boundingbox_with_mixed_units(self) -> None:
        """BoundingBox should handle mixed units correctly."""
        box = BoundingBox(
            width=Dimension(value=1, unit=Unit.INCHES),  # 25.4mm
            depth=Dimension(value=50),  # 50mm
            height=Dimension(value=25),  # 25mm
        )
        assert box.width_mm == pytest.approx(25.4)
        assert box.depth_mm == 50
        assert box.height_mm == 25


class TestTolerance:
    """Tests for Tolerance schema."""

    def test_tolerance_symmetric(self) -> None:
        """Tolerance.symmetric should create equal plus/minus."""
        tol = Tolerance.symmetric(0.2)
        assert tol.plus.mm == 0.2
        assert tol.minus.mm == 0.2

    def test_tolerance_fit_3d_print(self) -> None:
        """Tolerance.fit_3d_print should return ±0.2mm."""
        tol = Tolerance.fit_3d_print()
        assert tol.plus.mm == 0.2
        assert tol.minus.mm == 0.2

    def test_tolerance_fit_tight(self) -> None:
        """Tolerance.fit_tight should return ±0.1mm."""
        tol = Tolerance.fit_tight()
        assert tol.plus.mm == 0.1
        assert tol.minus.mm == 0.1

    def test_tolerance_fit_loose(self) -> None:
        """Tolerance.fit_loose should return ±0.5mm."""
        tol = Tolerance.fit_loose()
        assert tol.plus.mm == 0.5
        assert tol.minus.mm == 0.5


class TestAxis:
    """Tests for Axis enum."""

    def test_axis_values(self) -> None:
        """Axis enum should have x, y, z values."""
        assert Axis.X.value == "x"
        assert Axis.Y.value == "y"
        assert Axis.Z.value == "z"
