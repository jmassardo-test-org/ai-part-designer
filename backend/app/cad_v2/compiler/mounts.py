"""Mounting geometry compiler for CAD v2.

Compiles mounting features like screw bosses, standoffs, and mounting tabs.
These features are used to secure the lid and mount components.
"""

from typing import Any

from app.cad_v2.schemas.components import (
    ComponentMount,
    MountingHole,
    MountingType,
    StandoffSpec,
    StandoffType,
)
from app.cad_v2.schemas.enclosure import (
    EnclosureSpec,
    LidType,
    ScrewSpec,
)

# Import Build123d conditionally
try:
    from build123d import (
        Align,
        Axis,
        Box,
        BuildPart,
        Cylinder,
        Location,
        Locations,
        Mode,
        Part,
        RegularPolygon,
        add,
        extrude,
    )

    BUILD123D_AVAILABLE = True
except ImportError:
    BUILD123D_AVAILABLE = False
    Part = Any  # type: ignore[assignment, misc]


class MountCompiler:
    """Compiles mounting features into Build123d geometry."""

    def __init__(self, spec: EnclosureSpec) -> None:
        """Initialize mount compiler.

        Args:
            spec: The enclosure specification for context.
        """
        self.spec = spec

    def add_screw_bosses(self, body: Part) -> Part:
        """Add screw bosses for screw-on lid attachment.

        Screw bosses are cylindrical posts at corners of the enclosure
        with holes for screws that secure the lid.

        Args:
            body: Current enclosure body.

        Returns:
            Modified body with screw bosses added.
        """
        if not BUILD123D_AVAILABLE:
            return body

        lid = self.spec.lid
        if lid is None or lid.type != LidType.SCREW_ON:
            return body

        screws = lid.screws
        if screws is None:
            screws = ScrewSpec.m3()

        ext = self.spec.exterior
        wall = self.spec.walls.thickness.mm

        # Calculate boss positions (corners, inset from walls)
        boss_d = screws.boss_diameter.mm
        hole_d = screws.hole_diameter.mm
        inset = wall + boss_d / 2  # Center of boss

        # 4 corner positions
        positions = [
            (-ext.width.mm / 2 + inset, -ext.depth.mm / 2 + inset),  # Front-left
            (ext.width.mm / 2 - inset, -ext.depth.mm / 2 + inset),  # Front-right
            (-ext.width.mm / 2 + inset, ext.depth.mm / 2 - inset),  # Back-left
            (ext.width.mm / 2 - inset, ext.depth.mm / 2 - inset),  # Back-right
        ]

        # Boss height from bottom wall to just below top
        boss_height = ext.height.mm - wall - 0.5  # Leave small gap for lid

        with BuildPart() as result:
            add(body)

            # Add each boss
            for x, y in positions:
                # Add cylindrical boss
                with Locations([Location((x, y, wall))]):
                    Cylinder(
                        radius=boss_d / 2,
                        height=boss_height,
                        align=(Align.CENTER, Align.CENTER, Align.MIN),
                    )

                # Subtract screw hole
                with BuildPart(mode=Mode.SUBTRACT):
                    with Locations([Location((x, y, wall))]):
                        Cylinder(
                            radius=hole_d / 2,
                            height=boss_height + 1,  # Through
                            align=(Align.CENTER, Align.CENTER, Align.MIN),
                        )

        return result.part  # type: ignore[no-any-return]

    def add_lid_screw_holes(self, lid: Part) -> Part:
        """Add countersunk screw holes to the lid.

        The holes match the boss positions in the body.

        Args:
            lid: Current lid part.

        Returns:
            Modified lid with screw holes.
        """
        if not BUILD123D_AVAILABLE:
            return lid

        lid_spec = self.spec.lid
        if lid_spec is None or lid_spec.type != LidType.SCREW_ON:
            return lid

        screws = lid_spec.screws
        if screws is None:
            screws = ScrewSpec.m3()

        ext = self.spec.exterior
        wall = self.spec.walls.thickness.mm

        # Same positions as bosses
        boss_d = screws.boss_diameter.mm
        inset = wall + boss_d / 2

        positions = [
            (-ext.width.mm / 2 + inset, -ext.depth.mm / 2 + inset),
            (ext.width.mm / 2 - inset, -ext.depth.mm / 2 + inset),
            (-ext.width.mm / 2 + inset, ext.depth.mm / 2 - inset),
            (ext.width.mm / 2 - inset, ext.depth.mm / 2 - inset),
        ]

        hole_d = screws.hole_diameter.mm
        head_d = screws.head_diameter.mm
        head_depth = screws.head_depth.mm

        with BuildPart() as result:
            add(lid)

            for x, y in positions:
                # Through hole for screw shaft
                with BuildPart(mode=Mode.SUBTRACT):
                    with Locations([Location((x, y, 0))]):
                        Cylinder(
                            radius=hole_d / 2,
                            height=wall + 1,
                            align=(Align.CENTER, Align.CENTER, Align.MIN),
                        )

                # Countersink for screw head (from top)
                with BuildPart(mode=Mode.SUBTRACT):
                    with Locations([Location((x, y, wall - head_depth))]):
                        Cylinder(
                            radius=head_d / 2,
                            height=head_depth + 1,
                            align=(Align.CENTER, Align.CENTER, Align.MIN),
                        )

        return result.part  # type: ignore[no-any-return]

    def add_standoffs(
        self,
        body: Part,
        positions: list[tuple[float, float]],
        standoff: StandoffSpec,
    ) -> Part:
        """Add standoffs for component mounting.

        Standoffs are posts that raise a component (like a PCB)
        off the enclosure floor. They have screw holes for securing.

        Args:
            body: Current enclosure body.
            positions: List of (x, y) positions for standoffs.
            standoff: Standoff specification.

        Returns:
            Modified body with standoffs added.
        """
        if not BUILD123D_AVAILABLE:
            return body

        if not positions:
            return body

        wall = self.spec.walls.thickness.mm
        height = standoff.height.mm
        outer_d = standoff.outer_diameter.mm
        hole_d = standoff.hole_diameter.mm

        with BuildPart() as result:
            add(body)

            for x, y in positions:
                if standoff.type == StandoffType.CYLINDRICAL:
                    # Cylindrical standoff
                    with Locations([Location((x, y, wall))]):
                        Cylinder(
                            radius=outer_d / 2,
                            height=height,
                            align=(Align.CENTER, Align.CENTER, Align.MIN),
                        )
                elif standoff.type == StandoffType.HEXAGONAL:
                    # Hexagonal standoff - use cylinder with 6 sides
                    # Build123d doesn't have direct hex prism, use cylinder
                    with Locations([Location((x, y, wall))]):
                        Cylinder(
                            radius=outer_d / 2,
                            height=height,
                            align=(Align.CENTER, Align.CENTER, Align.MIN),
                        )
                elif standoff.type == StandoffType.SQUARE:
                    # Square standoff
                    with Locations([Location((x, y, wall))]):
                        Box(
                            outer_d,
                            outer_d,
                            height,
                            align=(Align.CENTER, Align.CENTER, Align.MIN),
                        )

                # Subtract screw hole
                with BuildPart(mode=Mode.SUBTRACT):
                    with Locations([Location((x, y, wall))]):
                        Cylinder(
                            radius=hole_d / 2,
                            height=height + 1,
                            align=(Align.CENTER, Align.CENTER, Align.MIN),
                        )

        return result.part  # type: ignore[no-any-return]

    def add_component_standoffs(
        self,
        body: Part,
        mount: ComponentMount,
        mounting_holes: list[MountingHole],
    ) -> Part:
        """Add standoffs for a component mount.

        Uses the component's mounting hole pattern from the library
        plus the mount position to place standoffs.

        Args:
            body: Current enclosure body.
            mount: Component mount specification.
            mounting_holes: Mounting holes from component definition.

        Returns:
            Modified body with component standoffs.
        """
        if not BUILD123D_AVAILABLE:
            return body

        if mount.mounting_type != MountingType.STANDOFF:
            return body

        standoff = mount.standoffs
        if standoff is None:
            standoff = StandoffSpec()

        # Calculate standoff positions relative to enclosure
        positions: list[tuple[float, float]] = []
        for hole in mounting_holes:
            x = mount.position.x + hole.x
            y = mount.position.y + hole.y
            positions.append((x, y))

        return self.add_standoffs(body, positions, standoff)
