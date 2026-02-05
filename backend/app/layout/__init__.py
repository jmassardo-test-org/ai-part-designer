"""
Auto-Layout Algorithm

Algorithms for automatically arranging components within an enclosure.
Supports multiple strategies: packed, grid, thermal-aware.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

logger = logging.getLogger(__name__)


# =============================================================================
# Data Structures
# =============================================================================


class LayoutAlgorithm(StrEnum):
    """Available layout algorithms."""

    PACKED = "packed"  # Minimize enclosure size
    GRID = "grid"  # Align to grid
    THERMAL = "thermal"  # Spread heat sources
    CONNECTOR = "connector"  # Prioritize connector access


@dataclass
class ComponentBox:
    """Axis-aligned bounding box for a component."""

    id: str
    name: str
    width: float  # X dimension
    depth: float  # Y dimension
    height: float  # Z dimension

    # Thermal properties
    power_dissipation: float = 0  # Watts

    # Connector info
    connector_faces: list[str] = field(default_factory=list)  # ["front", "back", etc.]

    # Rotation state
    rotation: int = 0  # 0, 90, 180, 270

    @property
    def rotated_width(self) -> float:
        """Width after rotation."""
        if self.rotation in (90, 270):
            return self.depth
        return self.width

    @property
    def rotated_depth(self) -> float:
        """Depth after rotation."""
        if self.rotation in (90, 270):
            return self.width
        return self.depth

    @property
    def footprint_area(self) -> float:
        """XY footprint area."""
        return self.width * self.depth


@dataclass
class Placement:
    """A component placement result."""

    component: ComponentBox
    x: float
    y: float
    z: float = 0
    rotation: int = 0
    face_direction: str = "front"

    @property
    def max_x(self) -> float:
        return self.x + self.component.rotated_width

    @property
    def max_y(self) -> float:
        return self.y + self.component.rotated_depth

    @property
    def max_z(self) -> float:
        return self.z + self.component.height

    def intersects(self, other: Placement, margin: float = 0) -> bool:
        """Check if this placement overlaps with another."""
        # Check X overlap
        if self.x + self.component.rotated_width + margin <= other.x:
            return False
        if other.x + other.component.rotated_width + margin <= self.x:
            return False

        # Check Y overlap
        if self.y + self.component.rotated_depth + margin <= other.y:
            return False
        if other.y + other.component.rotated_depth + margin <= self.y:
            return False

        # Check Z overlap
        if self.z + self.component.height + margin <= other.z:
            return False
        return not other.z + other.component.height + margin <= self.z


@dataclass
class LayoutResult:
    """Result of auto-layout algorithm."""

    placements: list[Placement]
    enclosure_width: float
    enclosure_depth: float
    enclosure_height: float
    algorithm_used: str
    success: bool = True
    message: str = ""

    @property
    def total_footprint(self) -> float:
        """Total enclosure footprint area."""
        return self.enclosure_width * self.enclosure_depth

    @property
    def utilization(self) -> float:
        """Component area / enclosure area."""
        component_area = sum(p.component.footprint_area for p in self.placements)
        return component_area / self.total_footprint if self.total_footprint > 0 else 0


# =============================================================================
# Layout Algorithms
# =============================================================================


class AutoLayoutEngine:
    """
    Engine for automatic component layout.

    Supports multiple algorithms with configurable parameters.
    """

    def __init__(
        self,
        clearance: float = 5.0,
        wall_margin: float = 2.0,
        grid_size: float = 5.0,
    ):
        self.clearance = clearance  # Between components
        self.wall_margin = wall_margin  # From enclosure walls
        self.grid_size = grid_size  # For grid snapping

    def layout(
        self,
        components: list[ComponentBox],
        algorithm: LayoutAlgorithm = LayoutAlgorithm.PACKED,
        max_width: float | None = None,
        max_depth: float | None = None,
        prioritize_connectors: bool = True,
    ) -> LayoutResult:
        """
        Arrange components using specified algorithm.

        Args:
            components: List of components to arrange
            algorithm: Layout algorithm to use
            max_width: Maximum enclosure width (optional constraint)
            max_depth: Maximum enclosure depth (optional constraint)
            prioritize_connectors: Align connectors to edges

        Returns:
            LayoutResult with placements and enclosure dimensions
        """
        if not components:
            return LayoutResult(
                placements=[],
                enclosure_width=0,
                enclosure_depth=0,
                enclosure_height=0,
                algorithm_used=algorithm.value,
                success=True,
                message="No components to layout",
            )

        if algorithm == LayoutAlgorithm.PACKED:
            return self._packed_layout(components, max_width, max_depth, prioritize_connectors)
        if algorithm == LayoutAlgorithm.GRID:
            return self._grid_layout(components, max_width, max_depth)
        if algorithm == LayoutAlgorithm.THERMAL:
            return self._thermal_layout(components, max_width, max_depth)
        if algorithm == LayoutAlgorithm.CONNECTOR:
            return self._connector_layout(components, max_width, max_depth)
        return self._packed_layout(components, max_width, max_depth, prioritize_connectors)

    def _packed_layout(
        self,
        components: list[ComponentBox],
        max_width: float | None,
        max_depth: float | None,
        prioritize_connectors: bool,
    ) -> LayoutResult:
        """
        Pack components efficiently using shelf algorithm.

        Sorts by height, then places in rows (shelves).
        """
        # Sort by footprint area (largest first) for better packing
        sorted_components = sorted(
            components,
            key=lambda c: c.footprint_area,
            reverse=True,
        )

        # Determine rotation for connector access
        if prioritize_connectors:
            for comp in sorted_components:
                if "front" in comp.connector_faces or "back" in comp.connector_faces:
                    # Keep default rotation
                    pass
                elif "left" in comp.connector_faces or "right" in comp.connector_faces:
                    # Rotate 90° to bring connectors to front/back
                    comp.rotation = 90

        # Simple shelf algorithm
        placements = []
        current_x = self.wall_margin
        current_y = self.wall_margin
        shelf_height = 0  # Track row (shelf) depth
        max_used_x = 0
        max_height_z = 0

        # Estimate width if not constrained
        if max_width is None:
            total_width = sum(c.rotated_width for c in sorted_components)
            max_width = max(
                total_width / 2 + self.clearance * len(sorted_components),
                sorted_components[0].rotated_width + self.wall_margin * 2,
            )

        for comp in sorted_components:
            comp_width = comp.rotated_width
            comp_depth = comp.rotated_depth

            # Check if fits in current row
            if current_x + comp_width + self.wall_margin > max_width:
                # Start new row
                current_x = self.wall_margin
                current_y += shelf_height + self.clearance
                shelf_height = 0

            # Place component
            placement = Placement(
                component=comp,
                x=current_x,
                y=current_y,
                z=0,
                rotation=comp.rotation,
                face_direction="front",
            )
            placements.append(placement)

            # Update tracking
            current_x += comp_width + self.clearance
            shelf_height = max(shelf_height, comp_depth)
            max_used_x = max(max_used_x, current_x)
            max_height_z = max(max_height_z, comp.height)

        # Calculate enclosure dimensions
        enclosure_width = max_used_x + self.wall_margin - self.clearance
        enclosure_depth = current_y + shelf_height + self.wall_margin
        enclosure_height = max_height_z + 10  # Add headroom

        return LayoutResult(
            placements=placements,
            enclosure_width=enclosure_width,
            enclosure_depth=enclosure_depth,
            enclosure_height=enclosure_height,
            algorithm_used="packed",
            success=True,
        )

    def _grid_layout(
        self,
        components: list[ComponentBox],
        max_width: float | None,
        max_depth: float | None,
    ) -> LayoutResult:
        """
        Arrange components on a regular grid.

        Good for uniform component sizes.
        """
        if not components:
            return LayoutResult(
                placements=[],
                enclosure_width=0,
                enclosure_depth=0,
                enclosure_height=0,
                algorithm_used="grid",
            )

        # Find largest component dimensions for grid cell size
        max_comp_width = max(c.rotated_width for c in components)
        max_comp_depth = max(c.rotated_depth for c in components)

        # Snap to grid
        cell_width = self._snap_to_grid(max_comp_width + self.clearance)
        cell_depth = self._snap_to_grid(max_comp_depth + self.clearance)

        # Calculate grid dimensions
        n = len(components)
        cols = int((n**0.5) + 0.5)  # Roughly square
        rows = (n + cols - 1) // cols

        placements = []
        max_height_z = 0

        for i, comp in enumerate(components):
            col = i % cols
            row = i // cols

            x = self.wall_margin + col * cell_width
            y = self.wall_margin + row * cell_depth

            # Center component in cell
            x += (cell_width - comp.rotated_width - self.clearance) / 2
            y += (cell_depth - comp.rotated_depth - self.clearance) / 2

            placement = Placement(
                component=comp,
                x=x,
                y=y,
                z=0,
                rotation=comp.rotation,
            )
            placements.append(placement)
            max_height_z = max(max_height_z, comp.height)

        enclosure_width = self.wall_margin * 2 + cols * cell_width - self.clearance
        enclosure_depth = self.wall_margin * 2 + rows * cell_depth - self.clearance
        enclosure_height = max_height_z + 10

        return LayoutResult(
            placements=placements,
            enclosure_width=enclosure_width,
            enclosure_depth=enclosure_depth,
            enclosure_height=enclosure_height,
            algorithm_used="grid",
            success=True,
        )

    def _thermal_layout(
        self,
        components: list[ComponentBox],
        max_width: float | None,
        max_depth: float | None,
    ) -> LayoutResult:
        """
        Spread heat-generating components apart.

        High-power components get placed first with maximum spacing.
        """
        # Sort by power dissipation (highest first)
        sorted_components = sorted(
            components,
            key=lambda c: c.power_dissipation,
            reverse=True,
        )

        # Count high-power components
        high_power = [c for c in sorted_components if c.power_dissipation > 0.5]

        if len(high_power) <= 1:
            # Not enough heat sources to worry about, use packed
            return self._packed_layout(components, max_width, max_depth, prioritize_connectors=True)

        # Place high-power components in corners/edges first
        placements = []

        # Estimate enclosure size
        total_area = sum(c.footprint_area for c in components)
        target_side = (total_area * 2) ** 0.5  # Roughly square with 50% utilization

        if max_width:
            target_side = min(target_side, max_width)

        # Corner positions for heat sources
        corners = [
            (self.wall_margin, self.wall_margin),
            (target_side - self.wall_margin, self.wall_margin),
            (self.wall_margin, target_side - self.wall_margin),
            (target_side - self.wall_margin, target_side - self.wall_margin),
        ]

        placed = []
        max_height_z = 0

        # Place high-power components at corners
        for i, comp in enumerate(high_power[:4]):
            corner = corners[i % 4]
            x, y = corner

            # Adjust for component size if at right/bottom edges
            if i % 2 == 1:  # Right side
                x -= comp.rotated_width
            if i >= 2:  # Bottom side
                y -= comp.rotated_depth

            placement = Placement(component=comp, x=x, y=y, z=0)
            placements.append(placement)
            placed.append(comp)
            max_height_z = max(max_height_z, comp.height)

        # Place remaining components using packed algorithm
        remaining = [c for c in sorted_components if c not in placed]

        if remaining:
            # Simple row placement for remaining
            current_x = self.wall_margin
            current_y = target_side / 3  # Start in middle area
            row_height = 0

            for comp in remaining:
                if current_x + comp.rotated_width + self.wall_margin > target_side:
                    current_x = self.wall_margin
                    current_y += row_height + self.clearance
                    row_height = 0

                # Check for collisions with existing placements
                test_placement = Placement(component=comp, x=current_x, y=current_y, z=0)

                collision = any(test_placement.intersects(p, self.clearance) for p in placements)

                if collision:
                    # Skip to next row
                    current_x = self.wall_margin
                    current_y += row_height + self.clearance + comp.rotated_depth
                    row_height = 0
                    test_placement = Placement(component=comp, x=current_x, y=current_y, z=0)

                placements.append(test_placement)
                current_x += comp.rotated_width + self.clearance
                row_height = max(row_height, comp.rotated_depth)
                max_height_z = max(max_height_z, comp.height)

        # Calculate actual bounds
        max_x = max(p.max_x for p in placements)
        max_y = max(p.max_y for p in placements)

        return LayoutResult(
            placements=placements,
            enclosure_width=max_x + self.wall_margin,
            enclosure_depth=max_y + self.wall_margin,
            enclosure_height=max_height_z + 10,
            algorithm_used="thermal",
            success=True,
        )

    def _connector_layout(
        self,
        components: list[ComponentBox],
        max_width: float | None,
        max_depth: float | None,
    ) -> LayoutResult:
        """
        Prioritize connector accessibility.

        Components with connectors are placed at edges.
        """
        # Separate components by connector presence
        has_front_connectors = []
        has_back_connectors = []
        has_side_connectors = []
        no_connectors = []

        for comp in components:
            if "front" in comp.connector_faces:
                has_front_connectors.append(comp)
            elif "back" in comp.connector_faces:
                has_back_connectors.append(comp)
            elif "left" in comp.connector_faces or "right" in comp.connector_faces:
                has_side_connectors.append(comp)
            else:
                no_connectors.append(comp)

        placements = []
        max_height_z = 0

        # Estimate width
        if max_width is None:
            max_comp_width = max(c.rotated_width for c in components) if components else 100
            max_width = (
                max(
                    max_comp_width * 3,
                    sum(c.rotated_width for c in has_front_connectors)
                    + self.clearance * len(has_front_connectors),
                )
                + self.wall_margin * 2
            )

        # Place front-connector components at front (y = margin)
        current_x = self.wall_margin
        for comp in has_front_connectors:
            placement = Placement(
                component=comp,
                x=current_x,
                y=self.wall_margin,
                z=0,
                face_direction="front",
            )
            placements.append(placement)
            current_x += comp.rotated_width + self.clearance
            max_height_z = max(max_height_z, comp.height)

        front_row_depth = max(
            (c.rotated_depth for c in has_front_connectors),
            default=0,
        )

        # Place back-connector components at back
        current_x = self.wall_margin
        back_y = (
            self.wall_margin
            + front_row_depth
            + self.clearance * 2
            + max(
                (c.rotated_depth for c in no_connectors + has_side_connectors),
                default=50,
            )
        )

        for comp in has_back_connectors:
            placement = Placement(
                component=comp,
                x=current_x,
                y=back_y,
                z=0,
                face_direction="back",
            )
            placements.append(placement)
            current_x += comp.rotated_width + self.clearance
            max_height_z = max(max_height_z, comp.height)

        # Place remaining components in middle
        middle_y = self.wall_margin + front_row_depth + self.clearance
        current_x = self.wall_margin
        row_depth = 0

        for comp in no_connectors + has_side_connectors:
            if current_x + comp.rotated_width + self.wall_margin > max_width:
                current_x = self.wall_margin
                middle_y += row_depth + self.clearance
                row_depth = 0

            placement = Placement(
                component=comp,
                x=current_x,
                y=middle_y,
                z=0,
            )
            placements.append(placement)
            current_x += comp.rotated_width + self.clearance
            row_depth = max(row_depth, comp.rotated_depth)
            max_height_z = max(max_height_z, comp.height)

        # Calculate bounds
        max_x = max((p.max_x for p in placements), default=0)
        max_y = max((p.max_y for p in placements), default=0)

        return LayoutResult(
            placements=placements,
            enclosure_width=max_x + self.wall_margin,
            enclosure_depth=max_y + self.wall_margin,
            enclosure_height=max_height_z + 10,
            algorithm_used="connector",
            success=True,
        )

    def _snap_to_grid(self, value: float) -> float:
        """Snap a value to the nearest grid point."""
        return round(value / self.grid_size) * self.grid_size

    def validate_layout(
        self,
        result: LayoutResult,
        max_width: float | None = None,
        max_depth: float | None = None,
        max_height: float | None = None,
    ) -> tuple[bool, list[str]]:
        """
        Validate a layout result.

        Returns:
            Tuple of (is_valid, list of error messages)
        """
        errors = []

        # Check dimension constraints
        if max_width and result.enclosure_width > max_width:
            errors.append(f"Layout exceeds max width: {result.enclosure_width:.1f} > {max_width}")
        if max_depth and result.enclosure_depth > max_depth:
            errors.append(f"Layout exceeds max depth: {result.enclosure_depth:.1f} > {max_depth}")
        if max_height and result.enclosure_height > max_height:
            errors.append(
                f"Layout exceeds max height: {result.enclosure_height:.1f} > {max_height}"
            )

        # Check for collisions
        placements = result.placements
        for i, p1 in enumerate(placements):
            for p2 in placements[i + 1 :]:
                if p1.intersects(p2, margin=0):
                    errors.append(f"Collision between {p1.component.name} and {p2.component.name}")

        # Check boundary violations
        for p in placements:
            if p.x < 0 or p.y < 0 or p.z < 0:
                errors.append(f"Component {p.component.name} has negative position")

        return len(errors) == 0, errors


# =============================================================================
# Convenience Functions
# =============================================================================


def auto_layout(
    components: list[dict[str, Any]],
    algorithm: str = "packed",
    clearance: float = 5.0,
    max_width: float | None = None,
    max_depth: float | None = None,
) -> dict[str, Any]:
    """
    Convenience function for auto-layout.

    Args:
        components: List of component dicts with id, name, width, depth, height
        algorithm: Algorithm name (packed, grid, thermal, connector)
        clearance: Minimum clearance between components
        max_width: Maximum enclosure width
        max_depth: Maximum enclosure depth

    Returns:
        Dict with placements and enclosure dimensions
    """
    # Convert dicts to ComponentBox objects
    boxes = []
    for c in components:
        box = ComponentBox(
            id=c.get("id", ""),
            name=c.get("name", "Component"),
            width=c.get("width", 50),
            depth=c.get("depth", 50),
            height=c.get("height", 20),
            power_dissipation=c.get("power_dissipation", 0),
            connector_faces=c.get("connector_faces", []),
        )
        boxes.append(box)

    # Run layout
    engine = AutoLayoutEngine(clearance=clearance)
    result = engine.layout(
        boxes,
        algorithm=LayoutAlgorithm(algorithm),
        max_width=max_width,
        max_depth=max_depth,
    )

    # Convert result to dict
    return {
        "success": result.success,
        "message": result.message,
        "algorithm": result.algorithm_used,
        "enclosure": {
            "width": result.enclosure_width,
            "depth": result.enclosure_depth,
            "height": result.enclosure_height,
        },
        "utilization": result.utilization,
        "placements": [
            {
                "component_id": p.component.id,
                "component_name": p.component.name,
                "x": p.x,
                "y": p.y,
                "z": p.z,
                "rotation": p.rotation,
                "face_direction": p.face_direction,
                "width": p.component.rotated_width,
                "depth": p.component.rotated_depth,
                "height": p.component.height,
            }
            for p in result.placements
        ],
    }
