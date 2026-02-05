"""Enclosure compiler for CAD v2.

Compiles EnclosureSpec schemas into Build123d geometry.
"""

from typing import TYPE_CHECKING, Any

from app.cad_v2.schemas.enclosure import EnclosureSpec, LidType, VentilationSpec, WallSide

if TYPE_CHECKING:
    from app.cad_v2.compiler.engine import CompilationResult
    from app.cad_v2.compiler.mounts import MountCompiler

# Import Build123d conditionally to allow testing without it
try:
    from build123d import (
        Align,
        Axis,
        Box,
        BuildPart,
        Location,
        Locations,
        Mode,
        Part,
        add,
        export_step,
        export_stl,
        fillet,
    )

    BUILD123D_AVAILABLE = True
except ImportError:
    BUILD123D_AVAILABLE = False
    # Define placeholder types for type hints
    Part = Any


class EnclosureCompiler:
    """Compiles enclosure specifications into Build123d geometry."""

    def __init__(self) -> None:
        """Initialize enclosure compiler."""
        if not BUILD123D_AVAILABLE:
            # We'll create placeholder geometry for testing
            pass

    def compile(self, spec: EnclosureSpec) -> "CompilationResult":
        """Compile an enclosure specification.

        Args:
            spec: Enclosure specification to compile.

        Returns:
            CompilationResult with body and optionally lid parts.
        """
        from app.cad_v2.compiler.engine import CompilationResult
        from app.cad_v2.compiler.mounts import MountCompiler

        if not BUILD123D_AVAILABLE:
            # Return placeholder result for testing
            return CompilationResult(
                success=True,
                parts={"body": _PlaceholderPart(spec, "body")},
                warnings=["Build123d not available - using placeholder geometry"],
                metadata={
                    "exterior": spec.exterior.to_tuple_mm(),
                    "wall_thickness": spec.walls.thickness.mm,
                },
            )

        warnings: list[str] = []
        parts: dict[str, Part] = {}
        mount_compiler = MountCompiler(spec)

        try:
            # Compile main body
            body = self._compile_body(spec)

            # Add screw bosses if lid type is SCREW_ON
            if spec.lid and spec.lid.type == LidType.SCREW_ON:
                body = mount_compiler.add_screw_bosses(body)

            # Add component mounting (standoffs)
            if spec.components:
                body = self._compile_component_mounts(body, spec, mount_compiler, warnings)

            parts["body"] = body

            # Compile lid if specified
            if spec.lid and spec.lid.separate_part:
                lid = self._compile_lid(spec)

                # Add screw holes if lid type is SCREW_ON
                if spec.lid.type == LidType.SCREW_ON:
                    lid = mount_compiler.add_lid_screw_holes(lid)

                parts["lid"] = lid

            # Apply ventilation
            if spec.ventilation.enabled:
                parts["body"] = self._apply_ventilation(parts["body"], spec)

            return CompilationResult(
                success=True,
                parts=parts,
                warnings=warnings,
                metadata={
                    "exterior": spec.exterior.to_tuple_mm(),
                    "interior": spec.interior.to_tuple_mm(),
                    "wall_thickness": spec.walls.thickness.mm,
                    "part_count": len(parts),
                },
            )

        except Exception as e:
            return CompilationResult(
                success=False,
                errors=[str(e)],
            )

    def _compile_body(self, spec: EnclosureSpec) -> Part:
        """Compile the main enclosure body.

        Creates a hollow box with specified wall thickness.
        The body is aligned with bottom at Z=0.
        """
        ext = spec.exterior
        wall = spec.walls.thickness.mm

        with BuildPart() as body:
            # Create outer box aligned to bottom at Z=0
            Box(
                ext.width.mm,
                ext.depth.mm,
                ext.height.mm,
                align=(Align.CENTER, Align.CENTER, Align.MIN),
            )

            # Apply corner radius if specified (fillet vertical edges)
            if spec.corner_radius and spec.corner_radius.mm > 0:
                radius = spec.corner_radius.mm
                # Filter edges parallel to Z axis (vertical edges)
                vertical_edges = body.edges().filter_by(Axis.Z)
                if vertical_edges:
                    fillet(vertical_edges, radius)

            # Hollow out interior (subtract inner box from top, leave bottom wall)
            inner_width = ext.width.mm - 2 * wall
            inner_depth = ext.depth.mm - 2 * wall
            inner_height = ext.height.mm - wall  # Open top

            with BuildPart(mode=Mode.SUBTRACT):
                # Inner box sits on top of bottom wall
                Box(
                    inner_width,
                    inner_depth,
                    inner_height,
                    align=(Align.CENTER, Align.CENTER, Align.MIN),
                )

        return body.part  # type: ignore[no-any-return]

    def _compile_lid(self, spec: EnclosureSpec) -> Part:
        """Compile the enclosure lid.

        Creates a flat lid plate, optionally with snap-fit lip.
        """
        ext = spec.exterior
        wall = spec.walls.thickness.mm
        lid_spec = spec.lid

        if lid_spec is None:
            raise ValueError("Cannot compile lid without lid specification")

        with BuildPart() as lid:
            # Basic lid is just a flat plate
            Box(
                ext.width.mm,
                ext.depth.mm,
                wall,
                align=(Align.CENTER, Align.CENTER, Align.MIN),
            )

            # Apply corner radius if specified
            if spec.corner_radius and spec.corner_radius.mm > 0:
                radius = spec.corner_radius.mm
                edges = lid.edges().filter_by(Axis.Z)
                if edges:
                    fillet(edges, radius)

            # Add snap-fit lip if specified
            if lid_spec.type == LidType.SNAP_FIT and lid_spec.snap_fit:
                snap = lid_spec.snap_fit
                lip_height = snap.lip_height.mm
                lip_thickness = snap.lip_thickness.mm

                # Create inner lip that fits inside the box
                inner_width = ext.width.mm - 2 * wall - 2 * snap.clearance.mm
                inner_depth = ext.depth.mm - 2 * wall - 2 * snap.clearance.mm

                with Locations([Location((0, 0, -lip_height / 2))]):
                    # Add outer lip
                    Box(inner_width, inner_depth, lip_height)
                    # Subtract inner to make it hollow
                    with BuildPart(mode=Mode.SUBTRACT):
                        Box(
                            inner_width - 2 * lip_thickness,
                            inner_depth - 2 * lip_thickness,
                            lip_height,
                        )

        return lid.part  # type: ignore[no-any-return]

    def _apply_ventilation(self, body: Part, spec: EnclosureSpec) -> Part:
        """Apply ventilation cutouts to the body."""
        vent = spec.ventilation

        if not vent.enabled:
            return body

        with BuildPart() as vented_body:
            add(body)

            # Apply vents to specified sides based on pattern
            for side in vent.sides:
                if vent.pattern == "honeycomb":
                    self._add_honeycomb_vents(vented_body, spec, vent, side)
                else:
                    # Default to slots
                    self._add_vent_slots(vented_body, spec, vent, side)

        return vented_body.part  # type: ignore[no-any-return]

    def _add_honeycomb_vents(
        self,
        body: "BuildPart",
        spec: EnclosureSpec,
        vent: VentilationSpec,
        side: WallSide,
    ) -> None:
        """Add honeycomb ventilation pattern to a wall.

        Creates a grid of hexagonal holes for ventilation.
        Hexagons are arranged in a honeycomb pattern.
        """
        from build123d import Cylinder

        ext = spec.exterior
        wall = spec.walls.thickness.mm
        margin = vent.margin.mm

        # Use slot_width as hole diameter for honeycomb
        hole_diameter = vent.slot_width.mm * 2  # Make honeycomb holes larger
        spacing = vent.slot_spacing.mm + hole_diameter

        width_mm = ext.width.mm
        depth_mm = ext.depth.mm
        height_mm = ext.height.mm

        if side == WallSide.LEFT:
            x_pos = -width_mm / 2
            # Calculate grid
            available_height = height_mm - 2 * margin
            available_depth = depth_mm - 2 * margin
            cols = int(available_depth / spacing)
            rows = int(available_height / spacing)

            for row in range(rows):
                for col in range(cols):
                    # Offset every other row for honeycomb pattern
                    y_offset = (spacing / 2) if row % 2 else 0
                    y = -depth_mm / 2 + margin + spacing / 2 + col * spacing + y_offset
                    z = margin + spacing / 2 + row * spacing

                    if y < depth_mm / 2 - margin and z < height_mm - margin:
                        with BuildPart(mode=Mode.SUBTRACT):
                            with Locations([Location((x_pos, y, z))]):
                                Cylinder(
                                    radius=hole_diameter / 2,
                                    height=wall * 2,
                                )

        elif side == WallSide.RIGHT:
            x_pos = width_mm / 2
            available_height = height_mm - 2 * margin
            available_depth = depth_mm - 2 * margin
            cols = int(available_depth / spacing)
            rows = int(available_height / spacing)

            for row in range(rows):
                for col in range(cols):
                    y_offset = (spacing / 2) if row % 2 else 0
                    y = -depth_mm / 2 + margin + spacing / 2 + col * spacing + y_offset
                    z = margin + spacing / 2 + row * spacing

                    if y < depth_mm / 2 - margin and z < height_mm - margin:
                        with BuildPart(mode=Mode.SUBTRACT):
                            with Locations([Location((x_pos, y, z))]):
                                Cylinder(
                                    radius=hole_diameter / 2,
                                    height=wall * 2,
                                )

        elif side == WallSide.FRONT:
            y_pos = -depth_mm / 2
            available_width = width_mm - 2 * margin
            available_height = height_mm - 2 * margin
            cols = int(available_width / spacing)
            rows = int(available_height / spacing)

            for row in range(rows):
                for col in range(cols):
                    x_offset = (spacing / 2) if row % 2 else 0
                    x = -width_mm / 2 + margin + spacing / 2 + col * spacing + x_offset
                    z = margin + spacing / 2 + row * spacing

                    if x < width_mm / 2 - margin and z < height_mm - margin:
                        with BuildPart(mode=Mode.SUBTRACT):
                            with Locations([Location((x, y_pos, z))]):
                                Cylinder(
                                    radius=hole_diameter / 2,
                                    height=wall * 2,
                                )

        elif side == WallSide.BACK:
            y_pos = depth_mm / 2
            available_width = width_mm - 2 * margin
            available_height = height_mm - 2 * margin
            cols = int(available_width / spacing)
            rows = int(available_height / spacing)

            for row in range(rows):
                for col in range(cols):
                    x_offset = (spacing / 2) if row % 2 else 0
                    x = -width_mm / 2 + margin + spacing / 2 + col * spacing + x_offset
                    z = margin + spacing / 2 + row * spacing

                    if x < width_mm / 2 - margin and z < height_mm - margin:
                        with BuildPart(mode=Mode.SUBTRACT):
                            with Locations([Location((x, y_pos, z))]):
                                Cylinder(
                                    radius=hole_diameter / 2,
                                    height=wall * 2,
                                )

    def _add_vent_slots(
        self,
        body: "BuildPart",
        spec: EnclosureSpec,
        vent: VentilationSpec,
        side: WallSide,
    ) -> None:
        """Add ventilation slots to a wall."""
        ext = spec.exterior
        wall = spec.walls.thickness.mm
        margin = vent.margin.mm
        slot_width = vent.slot_width.mm
        slot_length = vent.slot_length.mm
        spacing = vent.slot_spacing.mm

        width_mm = ext.width.mm
        height_mm = ext.height.mm

        # Calculate slot positions based on wall
        if side == WallSide.LEFT:
            # Left wall: slots run vertically
            x_pos = -width_mm / 2
            available_height = height_mm - 2 * margin
            num_slots = int(available_height / (slot_width + spacing))

            for i in range(num_slots):
                z = margin + slot_width / 2 + i * (slot_width + spacing)
                with BuildPart(mode=Mode.SUBTRACT):
                    with Locations([Location((x_pos, 0, z))]):
                        Box(wall * 2, slot_length, slot_width)

        elif side == WallSide.RIGHT:
            # Right wall: slots run vertically
            x_pos = width_mm / 2
            available_height = height_mm - 2 * margin
            num_slots = int(available_height / (slot_width + spacing))

            for i in range(num_slots):
                z = margin + slot_width / 2 + i * (slot_width + spacing)
                with BuildPart(mode=Mode.SUBTRACT):
                    with Locations([Location((x_pos, 0, z))]):
                        Box(wall * 2, slot_length, slot_width)

    def _compile_component_mounts(
        self,
        body: Part,
        spec: EnclosureSpec,
        mount_compiler: "MountCompiler",
        warnings: list[str],
    ) -> Part:
        """Add component mounting features (standoffs) to the body.

        Looks up each component in the library and adds standoffs
        at the mounting hole positions.

        Args:
            body: Current enclosure body.
            spec: Enclosure specification.
            mount_compiler: MountCompiler instance.
            warnings: List to append warnings to.

        Returns:
            Modified body with component mounts.
        """
        from app.cad_v2.components import get_registry
        from app.cad_v2.schemas.components import MountingType, StandoffSpec

        registry = get_registry()

        for mount in spec.components:
            # Look up component in registry
            component_def = registry.get(mount.component.component_id)

            if component_def is None:
                warnings.append(
                    f"Component '{mount.component.component_id}' not found in library, "
                    "skipping mounting features"
                )
                continue

            # Only add standoffs for STANDOFF mounting type
            if mount.mounting_type != MountingType.STANDOFF:
                continue

            # Get standoff spec (use mount's or default)
            standoff = mount.standoffs
            if standoff is None:
                standoff = StandoffSpec()

            # Add standoffs at component mounting hole positions
            body = mount_compiler.add_component_standoffs(
                body,
                mount,
                component_def.mounting_holes,
            )

        return body


class _PlaceholderPart:
    """Placeholder part for testing without Build123d."""

    def __init__(self, spec: EnclosureSpec, name: str) -> None:
        self.spec = spec
        self.name = name
        self._vertices: list[tuple[float, float, float]] = []
        self._faces: list[list[int]] = []

    def __repr__(self) -> str:
        return f"PlaceholderPart({self.name}, {self.spec.exterior})"


# Import at end to avoid circular import
