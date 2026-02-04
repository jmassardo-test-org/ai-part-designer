"""Tests for CAD v2 pattern schemas."""

import pytest
from pydantic import ValidationError

from app.cad_v2.schemas.base import Dimension, Point2D
from app.cad_v2.schemas.patterns import (
    CircularPattern,
    CustomPattern,
    GridPattern,
    LinearPattern,
    PatternPresets,
)


class TestLinearPattern:
    """Tests for LinearPattern schema."""

    def test_linear_pattern_horizontal(self) -> None:
        """LinearPattern should create horizontal pattern."""
        pattern = LinearPattern(
            direction="horizontal",
            count=5,
            spacing=Dimension(value=10),
        )
        assert pattern.type == "linear"
        assert pattern.direction == "horizontal"
        assert pattern.count == 5
        assert pattern.spacing.mm == 10

    def test_linear_pattern_vertical(self) -> None:
        """LinearPattern should create vertical pattern."""
        pattern = LinearPattern(
            direction="vertical",
            count=3,
            spacing=Dimension(value=15),
        )
        assert pattern.direction == "vertical"
        assert pattern.count == 3

    def test_linear_pattern_total_length(self) -> None:
        """LinearPattern.total_length should calculate total span."""
        pattern = LinearPattern(
            direction="horizontal",
            count=5,
            spacing=Dimension(value=10),
        )
        # 5 items with 10mm spacing = 4 gaps = 40mm total
        assert pattern.total_length == 40

    def test_linear_pattern_centering(self) -> None:
        """LinearPattern should support center option."""
        pattern = LinearPattern(
            count=3,
            spacing=Dimension(value=10),
            center=False,
        )
        assert pattern.center is False

    def test_linear_pattern_count_limits(self) -> None:
        """LinearPattern should validate count range."""
        # Valid
        LinearPattern(count=1, spacing=Dimension(value=10))
        LinearPattern(count=100, spacing=Dimension(value=10))

        # Invalid
        with pytest.raises(ValidationError):
            LinearPattern(count=0, spacing=Dimension(value=10))
        with pytest.raises(ValidationError):
            LinearPattern(count=101, spacing=Dimension(value=10))


class TestGridPattern:
    """Tests for GridPattern schema."""

    def test_grid_pattern_creation(self) -> None:
        """GridPattern should accept rows and columns."""
        pattern = GridPattern(
            rows=3,
            columns=4,
            row_spacing=Dimension(value=10),
            column_spacing=Dimension(value=12),
        )
        assert pattern.type == "grid"
        assert pattern.rows == 3
        assert pattern.columns == 4
        assert pattern.row_spacing.mm == 10
        assert pattern.column_spacing.mm == 12

    def test_grid_pattern_dimensions(self) -> None:
        """GridPattern should calculate total dimensions."""
        pattern = GridPattern(
            rows=3,
            columns=4,
            row_spacing=Dimension(value=10),
            column_spacing=Dimension(value=12),
        )
        # 3 rows, 2 gaps = 20mm height
        # 4 cols, 3 gaps = 36mm width
        assert pattern.total_height == 20
        assert pattern.total_width == 36

    def test_grid_pattern_stagger(self) -> None:
        """GridPattern should support stagger option."""
        pattern = GridPattern(
            rows=5,
            columns=7,
            row_spacing=Dimension(value=10),
            column_spacing=Dimension(value=10),
            stagger=True,
        )
        assert pattern.stagger is True
        # Stagger offset should be auto-calculated
        assert pattern.stagger_offset is not None
        assert pattern.stagger_offset.mm == 5.0  # Half of column_spacing

    def test_grid_pattern_custom_stagger_offset(self) -> None:
        """GridPattern should accept custom stagger offset."""
        pattern = GridPattern(
            rows=5,
            columns=7,
            row_spacing=Dimension(value=10),
            column_spacing=Dimension(value=10),
            stagger=True,
            stagger_offset=Dimension(value=3),
        )
        assert pattern.stagger_offset is not None
        assert pattern.stagger_offset.mm == 3.0


class TestCircularPattern:
    """Tests for CircularPattern schema."""

    def test_circular_pattern_full_circle(self) -> None:
        """CircularPattern should create full circle pattern."""
        pattern = CircularPattern(
            count=6,
            radius=Dimension(value=15),
        )
        assert pattern.type == "circular"
        assert pattern.count == 6
        assert pattern.radius.mm == 15
        assert pattern.sweep_angle == 360

    def test_circular_pattern_arc(self) -> None:
        """CircularPattern should support partial arc."""
        pattern = CircularPattern(
            count=5,
            radius=Dimension(value=20),
            start_angle=45,
            sweep_angle=180,
        )
        assert pattern.start_angle == 45
        assert pattern.sweep_angle == 180

    def test_circular_pattern_rotation(self) -> None:
        """CircularPattern should support instance rotation."""
        pattern = CircularPattern(
            count=8,
            radius=Dimension(value=25),
            rotate_instances=False,
        )
        assert pattern.rotate_instances is False

    def test_circular_pattern_angle_validation(self) -> None:
        """CircularPattern should validate angle ranges."""
        # Valid
        CircularPattern(count=6, radius=Dimension(value=10), start_angle=0)
        CircularPattern(count=6, radius=Dimension(value=10), start_angle=359)

        # Invalid
        with pytest.raises(ValidationError):
            CircularPattern(count=6, radius=Dimension(value=10), start_angle=-1)
        with pytest.raises(ValidationError):
            CircularPattern(count=6, radius=Dimension(value=10), start_angle=360)


class TestCustomPattern:
    """Tests for CustomPattern schema."""

    def test_custom_pattern_creation(self) -> None:
        """CustomPattern should accept list of positions."""
        pattern = CustomPattern(
            positions=[
                Point2D(x=0, y=10),
                Point2D(x=-10, y=0),
                Point2D(x=10, y=0),
                Point2D(x=0, y=-10),
                Point2D(x=0, y=0),
            ],
        )
        assert pattern.type == "custom"
        assert len(pattern.positions) == 5

    def test_custom_pattern_with_labels(self) -> None:
        """CustomPattern should accept labels."""
        pattern = CustomPattern(
            positions=[
                Point2D(x=0, y=10),
                Point2D(x=0, y=-10),
                Point2D(x=-10, y=0),
                Point2D(x=10, y=0),
                Point2D(x=0, y=0),
            ],
            labels=["up", "down", "left", "right", "select"],
        )
        assert len(pattern.labels) == 5
        assert pattern.labels[0] == "up"

    def test_custom_pattern_label_count_mismatch(self) -> None:
        """CustomPattern should validate label count matches positions."""
        with pytest.raises(ValidationError) as exc_info:
            CustomPattern(
                positions=[
                    Point2D(x=0, y=10),
                    Point2D(x=0, y=-10),
                ],
                labels=["up"],  # Missing label
            )
        assert "must match" in str(exc_info.value)

    def test_custom_pattern_requires_positions(self) -> None:
        """CustomPattern should require at least one position."""
        with pytest.raises(ValidationError):
            CustomPattern(positions=[])


class TestPatternPresets:
    """Tests for PatternPresets helper class."""

    def test_nav_cluster_dpad(self) -> None:
        """PatternPresets.nav_cluster_dpad should create D-pad pattern."""
        pattern = PatternPresets.nav_cluster_dpad()
        assert isinstance(pattern, CustomPattern)
        assert len(pattern.positions) == 5
        assert len(pattern.labels) == 5
        assert "up" in pattern.labels
        assert "down" in pattern.labels
        assert "select" in pattern.labels

    def test_nav_cluster_linear(self) -> None:
        """PatternPresets.nav_cluster_linear should create linear buttons."""
        pattern = PatternPresets.nav_cluster_linear()
        assert isinstance(pattern, LinearPattern)
        assert pattern.count == 5
        assert pattern.direction == "horizontal"

    def test_vent_slots(self) -> None:
        """PatternPresets.vent_slots should create vent slot pattern."""
        pattern = PatternPresets.vent_slots(width_mm=50, count=8)
        assert isinstance(pattern, LinearPattern)
        assert pattern.count == 8

    def test_honeycomb(self) -> None:
        """PatternPresets.honeycomb should create honeycomb pattern."""
        pattern = PatternPresets.honeycomb(rows=5, cols=7, spacing_mm=5)
        assert isinstance(pattern, GridPattern)
        assert pattern.rows == 5
        assert pattern.columns == 7
        assert pattern.stagger is True

    def test_mounting_corners(self) -> None:
        """PatternPresets.mounting_corners should create corner pattern."""
        pattern = PatternPresets.mounting_corners(width_mm=80, height_mm=60)
        assert isinstance(pattern, CustomPattern)
        assert len(pattern.positions) == 4
        # Check corners are at half dimensions
        xs = [p.x for p in pattern.positions]
        ys = [p.y for p in pattern.positions]
        assert 40 in xs or -40 in xs  # Half of 80
        assert 30 in ys or -30 in ys  # Half of 60
