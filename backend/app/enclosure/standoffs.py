"""
Mounting Standoff Generator

Generates mounting standoffs for PCB/component mounting
based on hole specifications.

Migrated from CadQuery to Build123d.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from build123d import (
    Align,
    Axis,
    Box,
    BuildPart,
    Cylinder,
    Location,
    Mode,
    Part,
    chamfer,
    fillet,
)

from app.enclosure.schemas import (
    BossStyle,
    Standoff,
    StandoffOptions,
    StandoffType,
)
from app.schemas.component_specs import (
    MountingHole,
    Position3D,
    ThreadSize,
)

if TYPE_CHECKING:
    from uuid import UUID

# =============================================================================
# Thread/Hole Size Mappings
# =============================================================================

# Standard screw/insert dimensions (outer diameter, pilot hole)
THREAD_DIMENSIONS: dict[ThreadSize, tuple[float, float]] = {
    ThreadSize.M2: (2.0, 1.6),
    ThreadSize.M2_5: (2.5, 2.0),
    ThreadSize.M3: (3.0, 2.5),
    ThreadSize.M4: (4.0, 3.3),
    ThreadSize.M5: (5.0, 4.2),
    ThreadSize.INCH_4_40: (2.84, 2.26),
    ThreadSize.INCH_6_32: (3.51, 2.69),
    ThreadSize.INCH_8_32: (4.17, 3.25),
}

# Heat-set insert dimensions (insert OD, pilot hole, boss OD)
HEAT_SET_INSERT_DIMS: dict[ThreadSize, tuple[float, float, float]] = {
    ThreadSize.M2: (3.2, 3.0, 5.0),
    ThreadSize.M2_5: (4.0, 3.8, 6.0),
    ThreadSize.M3: (4.6, 4.4, 7.0),
    ThreadSize.M4: (5.6, 5.4, 8.5),
    ThreadSize.M5: (6.4, 6.2, 10.0),
}


# Default outer diameters based on hole diameter
def get_default_outer_diameter(hole_diameter: float) -> float:
    """Calculate default outer diameter for a given hole."""
    # Rule of thumb: outer diameter = hole * 2.5, minimum 5mm
    return max(hole_diameter * 2.5, 5.0)


# =============================================================================
# Standoff Generator
# =============================================================================


class StandoffGenerator:
    """
    Generates mounting standoffs for components.

    Supports various standoff types:
    - Solid posts
    - Hollow for self-tapping screws
    - Heat-set insert bosses
    - Threaded inserts
    """

    def calculate_standoff(
        self,
        hole: MountingHole,
        component_position: Position3D,
        standoff_height: float,
        component_id: UUID | None = None,
        options: StandoffOptions | None = None,
    ) -> Standoff:
        """
        Calculate standoff specification for a mounting hole.

        Args:
            hole: Mounting hole specification
            component_position: Position of component in enclosure
            standoff_height: Height of standoff (floor to PCB bottom)
            component_id: Optional component reference
            options: Optional standoff options

        Returns:
            Standoff specification
        """
        if options is None:
            options = StandoffOptions()

        # Calculate position in enclosure coordinates
        x = component_position.x + hole.x
        y = component_position.y + hole.y

        # Determine dimensions based on type
        if options.type == StandoffType.HEAT_SET_INSERT:
            outer_d, inner_d = self._heat_set_dimensions(hole, options)
        elif options.type == StandoffType.THREADED:
            outer_d, inner_d = self._threaded_dimensions(hole, options)
        else:
            outer_d, inner_d = self._standard_dimensions(hole, options)

        return Standoff(
            x=round(x, 2),
            y=round(y, 2),
            height=standoff_height,
            outer_diameter=round(outer_d, 2),
            inner_diameter=round(inner_d, 2),
            type=options.type,
            thread_size=hole.thread_size,
            boss_style=options.boss_style,
            component_id=component_id,
            hole_label=hole.label,
        )

    def _standard_dimensions(
        self,
        hole: MountingHole,
        options: StandoffOptions,
    ) -> tuple[float, float]:
        """Calculate dimensions for standard hollow/solid standoffs."""
        # Outer diameter
        outer_d = options.outer_diameter or get_default_outer_diameter(hole.diameter)

        # Inner diameter
        if options.type == StandoffType.SOLID:
            inner_d = 0.0
        elif options.inner_diameter:
            inner_d = options.inner_diameter
        else:
            # For hollow, inner = hole diameter - 0.5mm for self-tap
            inner_d = max(hole.diameter - 0.5, hole.diameter * 0.7)

        return outer_d, inner_d

    def _heat_set_dimensions(
        self,
        hole: MountingHole,
        options: StandoffOptions,
    ) -> tuple[float, float]:
        """Calculate dimensions for heat-set insert bosses."""
        thread = hole.thread_size or ThreadSize.M3

        if thread in HEAT_SET_INSERT_DIMS:
            _, pilot, boss = HEAT_SET_INSERT_DIMS[thread]
            return (
                options.outer_diameter or boss,
                options.inner_diameter or pilot,
            )
        # Fallback calculation
        return (
            options.outer_diameter or hole.diameter * 2.0,
            options.inner_diameter or hole.diameter * 1.1,
        )

    def _threaded_dimensions(
        self,
        hole: MountingHole,
        options: StandoffOptions,
    ) -> tuple[float, float]:
        """Calculate dimensions for threaded standoffs."""
        thread = hole.thread_size or options.thread_size

        if thread and thread in THREAD_DIMENSIONS:
            _, tap_drill = THREAD_DIMENSIONS[thread]
            outer_d = options.outer_diameter or get_default_outer_diameter(hole.diameter)
            return outer_d, tap_drill
        # Fallback
        return (
            options.outer_diameter or hole.diameter * 2.5,
            options.inner_diameter or hole.diameter * 0.85,
        )

    def generate_standoff_geometry(
        self,
        standoff: Standoff,
        floor_offset: float = 0.0,
    ) -> Part:
        """
        Generate Build123d geometry for a single standoff.

        Args:
            standoff: Standoff specification
            floor_offset: Z offset from origin (floor thickness)

        Returns:
            Build123d Part with standoff geometry
        """
        with BuildPart() as builder:
            # Create outer shape based on boss style
            if standoff.boss_style == BossStyle.SQUARE:
                Box(
                    standoff.outer_diameter,
                    standoff.outer_diameter,
                    standoff.height,
                    align=(Align.CENTER, Align.CENTER, Align.MIN),
                ).locate(Location((standoff.x, standoff.y, floor_offset)))

                # Add fillets on vertical edges
                try:
                    vertical_edges = builder.edges().filter_by(Axis.Z)
                    if vertical_edges:
                        fillet(vertical_edges, standoff.outer_diameter * 0.1)
                except Exception:
                    pass
            else:
                # Cylindrical (default)
                Cylinder(
                    standoff.outer_diameter / 2,
                    standoff.height,
                    align=(Align.CENTER, Align.CENTER, Align.MIN),
                ).locate(Location((standoff.x, standoff.y, floor_offset)))

            # Add fillet at base
            try:
                bottom_edges = builder.edges().filter_by(lambda e: floor_offset + 1 > e.center().Z)
                if bottom_edges:
                    fillet(bottom_edges, 0.5)
            except Exception:
                pass

            # Create inner hole if not solid
            if standoff.inner_diameter > 0:
                Cylinder(
                    standoff.inner_diameter / 2,
                    standoff.height,
                    align=(Align.CENTER, Align.CENTER, Align.MIN),
                    mode=Mode.SUBTRACT,
                ).locate(Location((standoff.x, standoff.y, floor_offset)))

        return builder.part  # type: ignore[no-any-return]

    def generate_all_standoffs(
        self,
        standoffs: list[Standoff],
        floor_offset: float = 0.0,
    ) -> Part | None:
        """
        Generate geometry for all standoffs combined.

        Args:
            standoffs: List of standoff specifications
            floor_offset: Z offset from origin

        Returns:
            Combined Build123d Part with all standoffs, or None if empty
        """
        if not standoffs:
            return None

        # Generate first standoff
        result = self.generate_standoff_geometry(standoffs[0], floor_offset)

        # Fuse with remaining standoffs
        for standoff in standoffs[1:]:
            new_standoff = self.generate_standoff_geometry(standoff, floor_offset)
            result = result.fuse(new_standoff)

        return result

    def generate_heat_set_insert_boss(
        self,
        hole: MountingHole,
        position: Position3D,
        boss_height: float = 8.0,
        floor_offset: float = 0.0,
    ) -> Part:
        """
        Generate a boss specifically designed for heat-set inserts.

        Heat-set insert bosses have:
        - Slightly larger pilot hole for insert insertion
        - Chamfer at top for insert alignment
        - Ribbed or gusseted base for strength

        Args:
            hole: Mounting hole specification
            position: Position in enclosure
            boss_height: Total boss height
            floor_offset: Z offset from origin

        Returns:
            Build123d Part with boss geometry
        """
        thread = hole.thread_size or ThreadSize.M3

        if thread in HEAT_SET_INSERT_DIMS:
            _insert_od, pilot, boss_od = HEAT_SET_INSERT_DIMS[thread]
        else:
            # Fallback dimensions
            hole.diameter * 1.1
            pilot = hole.diameter * 1.0
            boss_od = hole.diameter * 2.0

        x = position.x + hole.x
        y = position.y + hole.y

        with BuildPart() as builder:
            # Create main boss cylinder
            Cylinder(
                boss_od / 2, boss_height, align=(Align.CENTER, Align.CENTER, Align.MIN)
            ).locate(Location((x, y, floor_offset)))

            # Add base fillet
            try:
                bottom_edges = builder.edges().filter_by(lambda e: floor_offset + 1 > e.center().Z)
                if bottom_edges:
                    fillet(bottom_edges, 1.0)
            except Exception:
                pass

            # Create pilot hole
            Cylinder(
                pilot / 2,
                boss_height,
                align=(Align.CENTER, Align.CENTER, Align.MIN),
                mode=Mode.SUBTRACT,
            ).locate(Location((x, y, floor_offset)))

            # Add chamfer at top for insert alignment
            try:
                top_edges = builder.edges().filter_by(
                    lambda e: floor_offset + boss_height - 1 < e.center().Z
                )
                if top_edges:
                    chamfer(top_edges, 0.5)
            except Exception:
                pass

        return builder.part  # type: ignore[no-any-return]
