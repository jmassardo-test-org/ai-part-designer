"""
Mounting generators for various mounting types.

Generates mounting features including:
- Snap-fit clips
- DIN rail mounts (35mm standard)
- Wall mount brackets with keyhole patterns
- PCB standoffs

Migrated from CadQuery to Build123d.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from build123d import (
    Align,
    Axis,
    Box,
    BuildSketch,
    Cylinder,
    Location,
    Part,
    RegularPolygon,
    extrude,
    fillet,
)

logger = logging.getLogger(__name__)


# =============================================================================
# Enums
# =============================================================================


class MountingType(StrEnum):
    """Supported mounting types."""

    SNAP_FIT = "snap_fit"
    DIN_RAIL = "din_rail"
    WALL_MOUNT = "wall_mount"
    PCB_STANDOFF = "pcb_standoff"


class SnapFitStyle(StrEnum):
    """Snap-fit clip styles."""

    CANTILEVER = "cantilever"  # Simple cantilever beam
    ANNULAR = "annular"  # Ring/circular snap
    TORSIONAL = "torsional"  # Twist-lock


class DINRailSize(StrEnum):
    """Standard DIN rail sizes."""

    TS35 = "ts35"  # 35mm top-hat (most common)
    TS32 = "ts32"  # 32mm top-hat
    G32 = "g32"  # 32mm G-type


# =============================================================================
# Snap-Fit Configuration
# =============================================================================


@dataclass
class SnapFitConfig:
    """Configuration for snap-fit clips."""

    # Clip dimensions
    length: float = 15.0  # Length of cantilever beam
    width: float = 8.0  # Width of clip
    thickness: float = 2.0  # Base thickness

    # Hook dimensions
    hook_height: float = 2.5  # Height of retaining hook
    hook_angle: float = 30.0  # Entry angle in degrees
    hook_undercut: float = 1.0  # Undercut depth

    # Cantilever properties
    taper: float = 0.8  # Taper ratio (tip/base)
    deflection: float = 2.0  # Required deflection in mm

    # Material (affects flexibility)
    material: str = "ABS"

    # Style
    style: SnapFitStyle = SnapFitStyle.CANTILEVER


@dataclass
class SnapFitResult:
    """Result of snap-fit generation."""

    clip: Part
    receptacle: Part | None = None  # Matching receptacle if applicable

    # Engineering data
    estimated_retention_force: float = 0.0  # Newtons
    max_deflection: float = 0.0  # mm

    metadata: dict[str, Any] = field(default_factory=dict)


# =============================================================================
# DIN Rail Configuration
# =============================================================================


@dataclass
class DINRailConfig:
    """Configuration for DIN rail mounting."""

    # Rail type
    rail_size: DINRailSize = DINRailSize.TS35

    # Mount dimensions (device attachment area)
    mount_width: float = 50.0  # Width of mounting plate
    mount_height: float = 30.0  # Height of mounting plate
    mount_thickness: float = 3.0  # Plate thickness

    # Clip configuration
    clip_spring_tension: float = 2.0  # Spring deflection in mm
    clip_style: str = "spring"  # "spring" or "latch"

    # Corner radius
    corner_radius: float = 2.0


@dataclass
class DINRailResult:
    """Result of DIN rail mount generation."""

    mount: Part

    # Fits standard 35mm TS rail
    rail_compatibility: str = "TS35"

    metadata: dict[str, Any] = field(default_factory=dict)


# =============================================================================
# Wall Mount Configuration
# =============================================================================


@dataclass
class WallMountConfig:
    """Configuration for wall mounting brackets."""

    # Bracket dimensions
    bracket_width: float = 40.0
    bracket_height: float = 25.0
    bracket_depth: float = 20.0  # How far it projects from wall
    bracket_thickness: float = 3.0

    # Keyhole pattern
    keyhole_count: int = 2
    keyhole_spacing: float = 30.0  # Center-to-center
    keyhole_large_dia: float = 8.0  # Screw head diameter
    keyhole_small_dia: float = 4.5  # Screw shaft diameter
    keyhole_slot_length: float = 6.0  # Slot length

    # Mounting screw
    screw_size: str = "M4"

    # Support/stiffener ribs
    add_ribs: bool = True
    rib_count: int = 2
    rib_thickness: float = 2.0


@dataclass
class WallMountResult:
    """Result of wall mount generation."""

    bracket: Part

    # Hardware requirements
    recommended_screws: str = "M4x25 pan head"
    recommended_anchors: str = "Wall anchors for M4"

    metadata: dict[str, Any] = field(default_factory=dict)


# =============================================================================
# PCB Standoff Configuration
# =============================================================================


@dataclass
class PCBStandoffConfig:
    """Configuration for PCB standoffs."""

    # Standoff dimensions
    height: float = 10.0  # Height above surface
    outer_diameter: float = 6.0
    inner_diameter: float = 3.2  # For M3 screw

    # Base
    base_diameter: float = 8.0
    base_height: float = 2.0

    # Thread type
    screw_size: str = "M3"
    threaded: bool = True  # False for through-hole

    # Style
    hex_outer: bool = False  # Hex instead of round


@dataclass
class PCBStandoffResult:
    """Result of PCB standoff generation."""

    standoff: Part

    # For arrays of standoffs
    positions: list[tuple[float, float]] = field(default_factory=list)

    metadata: dict[str, Any] = field(default_factory=dict)


# =============================================================================
# Snap-Fit Generator
# =============================================================================


class SnapFitGenerator:
    """
    Generates snap-fit clips and receptacles.

    Creates cantilever-style snap fits with proper hook geometry
    for reliable engagement and disengagement.
    """

    def __init__(self, config: SnapFitConfig):
        self.config = config

    def generate(self) -> SnapFitResult:
        """Generate snap-fit clip."""
        cfg = self.config

        if cfg.style == SnapFitStyle.CANTILEVER:
            clip = self._generate_cantilever()
        else:
            # Default to cantilever
            clip = self._generate_cantilever()

        # Calculate retention force (simplified engineering estimate)
        # F = (3 * E * I * delta) / L^3
        # Using approximate values for ABS: E ≈ 2.3 GPa
        e_modulus = 2300  # MPa for ABS
        moment_inertia = (cfg.width * cfg.thickness**3) / 12
        retention = (3 * e_modulus * moment_inertia * cfg.hook_undercut) / (cfg.length**3)

        return SnapFitResult(
            clip=clip,
            estimated_retention_force=retention / 1000,  # Convert to reasonable N
            max_deflection=cfg.deflection,
            metadata={
                "style": cfg.style.value,
                "material": cfg.material,
            },
        )

    def _generate_cantilever(self) -> Part:
        """Generate cantilever snap-fit clip."""
        cfg = self.config

        # Base attachment block
        result = Box(
            cfg.width,
            cfg.thickness * 2,
            cfg.thickness * 3,
            align=(Align.CENTER, Align.CENTER, Align.CENTER),
        )

        # Cantilever beam extending in X direction
        # Simple box for beam body
        tip_thickness = cfg.thickness * cfg.taper
        beam_height = (cfg.thickness + tip_thickness) / 2

        beam = Box(
            cfg.length, cfg.width, beam_height, align=(Align.MIN, Align.CENTER, Align.CENTER)
        ).moved(Location((cfg.thickness, 0, cfg.thickness)))
        result = result.fuse(beam)

        # Hook at end - simplified as block with angle
        hook = Box(
            cfg.hook_undercut + 2,
            cfg.width,
            cfg.hook_height,
            align=(Align.CENTER, Align.CENTER, Align.MIN),
        ).moved(Location((cfg.length + cfg.thickness, 0, cfg.thickness + beam_height / 2)))
        result = result.fuse(hook)

        # Add hook undercut by cutting
        undercut = Box(
            cfg.hook_undercut,
            cfg.width * 0.8,
            cfg.hook_height * 0.7,
            align=(Align.MAX, Align.CENTER, Align.MIN),
        ).moved(Location((cfg.length + cfg.thickness, 0, cfg.thickness + beam_height / 2)))
        result = result.cut(undercut)

        # Apply fillets for stress relief
        try:
            edges = result.edges()
            if edges:
                result = fillet(edges, 0.3)
        except Exception:
            pass

        return result

    def generate_receptacle(self, clearance: float = 0.3) -> Part:
        """Generate matching receptacle for the clip."""
        cfg = self.config

        # Simple rectangular pocket with hook entry
        pocket_width = cfg.width + 2 * clearance
        pocket_depth = cfg.thickness + cfg.hook_undercut + clearance
        pocket_length = cfg.hook_height + clearance * 2

        # Outer block
        result = Box(
            pocket_width + 4,
            pocket_length + 4,
            pocket_depth + 2,
            align=(Align.CENTER, Align.CENTER, Align.CENTER),
        )

        # Cut pocket from top
        pocket = Box(
            pocket_width, pocket_length, pocket_depth, align=(Align.CENTER, Align.CENTER, Align.MAX)
        ).moved(Location((0, 0, (pocket_depth + 2) / 2)))
        return result.cut(pocket)


# =============================================================================
# DIN Rail Generator
# =============================================================================


class DINRailGenerator:
    """
    Generates DIN rail mounting adapters.

    Creates mounts compatible with standard 35mm TS (top-hat) DIN rails
    commonly used in industrial control panels.
    """

    # Standard TS35 rail dimensions
    RAIL_WIDTH = 35.0
    RAIL_LIP_HEIGHT = 7.5
    RAIL_LIP_DEPTH = 1.0
    RAIL_THICKNESS = 1.0

    def __init__(self, config: DINRailConfig):
        self.config = config

    def generate(self) -> DINRailResult:
        """Generate DIN rail mount."""
        cfg = self.config

        # Main mounting plate
        base = Box(
            cfg.mount_width,
            cfg.mount_height,
            cfg.mount_thickness,
            align=(Align.CENTER, Align.CENTER, Align.CENTER),
        )

        # Apply corner radius
        if cfg.corner_radius > 0:
            try:
                vertical_edges = base.edges().filter_by(Axis.Z)
                if vertical_edges:
                    base = fillet(vertical_edges, cfg.corner_radius)
            except Exception:
                pass

        # Add rail clips
        mount = self._add_rail_clips(base)

        return DINRailResult(
            mount=mount,
            rail_compatibility="TS35 (35mm top-hat)",
            metadata={
                "mount_width": cfg.mount_width,
                "mount_height": cfg.mount_height,
            },
        )

    def _add_rail_clips(self, base: Part) -> Part:
        """Add DIN rail clips to the base."""
        cfg = self.config

        # Create clips
        top_clip = self._create_fixed_clip()
        bottom_clip = self._create_spring_clip()

        # Position clips
        top_y = self.RAIL_WIDTH / 2 - self.RAIL_LIP_HEIGHT / 2
        bottom_y = -self.RAIL_WIDTH / 2 + self.RAIL_LIP_HEIGHT / 2
        clip_z = -cfg.mount_thickness / 2 - 2

        # Combine
        top_positioned = top_clip.moved(Location((0, top_y, clip_z)))
        bottom_positioned = bottom_clip.moved(Location((0, bottom_y, clip_z)))

        return base.fuse(top_positioned).fuse(bottom_positioned)

    def _create_fixed_clip(self) -> Part:
        """Create fixed top clip that hooks over rail lip."""
        cfg = self.config

        clip_width = cfg.mount_width * 0.8
        clip_height = self.RAIL_LIP_HEIGHT
        lip_depth = self.RAIL_LIP_DEPTH + 1.5

        # L-shaped hook profile - vertical arm
        result = Box(clip_width, 2, clip_height, align=(Align.CENTER, Align.CENTER, Align.MIN))

        # Horizontal hook
        hook = Box(clip_width, lip_depth, 2, align=(Align.CENTER, Align.MIN, Align.MAX)).moved(
            Location((0, -1, clip_height))
        )
        return result.fuse(hook)

    def _create_spring_clip(self) -> Part:
        """Create spring-loaded bottom clip."""
        cfg = self.config

        clip_width = cfg.mount_width * 0.3
        clip_height = self.RAIL_LIP_HEIGHT
        lip_depth = self.RAIL_LIP_DEPTH + 1.5

        # Vertical arm going down
        result = Box(clip_width, 2, clip_height, align=(Align.CENTER, Align.CENTER, Align.MAX))

        # Hook at bottom
        hook = Box(clip_width, lip_depth, 2, align=(Align.CENTER, Align.MIN, Align.MIN)).moved(
            Location((0, -1, -clip_height))
        )
        return result.fuse(hook)


# =============================================================================
# Wall Mount Generator
# =============================================================================


class WallMountGenerator:
    """
    Generates wall mounting brackets with keyhole patterns.

    Creates L-brackets or flat plates with keyhole slots
    for easy installation on wall screws.
    """

    def __init__(self, config: WallMountConfig):
        self.config = config

    def generate(self) -> WallMountResult:
        """Generate wall mount bracket."""
        cfg = self.config

        # Create L-bracket profile
        bracket = self._create_l_bracket()

        # Add keyhole pattern
        bracket = self._add_keyholes(bracket)

        # Add stiffener ribs
        if cfg.add_ribs:
            bracket = self._add_ribs(bracket)

        return WallMountResult(
            bracket=bracket,
            recommended_screws=f"{cfg.screw_size}x25 pan head",
            recommended_anchors=f"Wall anchors for {cfg.screw_size}",
            metadata={
                "keyhole_count": cfg.keyhole_count,
                "keyhole_spacing": cfg.keyhole_spacing,
            },
        )

    def _create_l_bracket(self) -> Part:
        """Create L-shaped bracket profile."""
        cfg = self.config

        # Wall plate (in XZ plane, extends in +Y for shelf)
        result = Box(
            cfg.bracket_width,
            cfg.bracket_thickness,
            cfg.bracket_height,
            align=(Align.CENTER, Align.MIN, Align.CENTER),
        )

        # Shelf plate (horizontal, extending in +Y)
        shelf = Box(
            cfg.bracket_width,
            cfg.bracket_depth,
            cfg.bracket_thickness,
            align=(Align.CENTER, Align.MIN, Align.MAX),
        ).moved(Location((0, 0, -cfg.bracket_height / 2)))
        return result.fuse(shelf)

    def _add_keyholes(self, bracket: Part) -> Part:
        """Add keyhole pattern to wall plate."""
        cfg = self.config

        # Calculate keyhole positions
        if cfg.keyhole_count == 1:
            positions = [0.0]
        else:
            start_x = -cfg.keyhole_spacing * (cfg.keyhole_count - 1) / 2
            positions = [start_x + i * cfg.keyhole_spacing for i in range(cfg.keyhole_count)]

        result = bracket

        for x in positions:
            # Cut large hole for screw head
            hole = (
                Cylinder(
                    cfg.keyhole_large_dia / 2,
                    cfg.bracket_thickness * 2,
                    align=(Align.CENTER, Align.CENTER, Align.CENTER),
                )
                .moved(Location((x, cfg.bracket_thickness / 2, 0)))
                .rotate(Axis.X, 90)
            )
            result = result.cut(hole)

            # Cut slot extending downward
            slot = (
                Box(
                    cfg.keyhole_small_dia,
                    cfg.bracket_thickness * 2,
                    cfg.keyhole_slot_length,
                    align=(Align.CENTER, Align.CENTER, Align.MAX),
                )
                .moved(Location((x, cfg.bracket_thickness / 2, 0)))
                .rotate(Axis.X, 90)
            )
            result = result.cut(slot)

        return result

    def _add_ribs(self, bracket: Part) -> Part:
        """Add triangular stiffener ribs."""
        cfg = self.config

        rib_height = cfg.bracket_height * 0.4
        rib_depth = cfg.bracket_depth * 0.6

        # Calculate rib positions
        if cfg.rib_count == 1:
            positions = [0.0]
        else:
            spacing = (cfg.bracket_width - cfg.rib_thickness * 2) / (cfg.rib_count + 1)
            positions = [
                -cfg.bracket_width / 2 + cfg.rib_thickness + spacing * (i + 1)
                for i in range(cfg.rib_count)
            ]

        result = bracket

        for x_pos in positions:
            # Create triangular rib as a box (simplified)
            # In practice, would use a triangular sketch
            rib = Box(
                cfg.rib_thickness,
                rib_depth * 0.7,
                rib_height * 0.7,
                align=(Align.CENTER, Align.MIN, Align.MIN),
            ).moved(
                Location(
                    (x_pos, cfg.bracket_thickness, -cfg.bracket_height / 2 + cfg.bracket_thickness)
                )
            )
            result = result.fuse(rib)

        return result


# =============================================================================
# PCB Standoff Generator
# =============================================================================


class PCBStandoffGenerator:
    """
    Generates PCB standoffs for mounting circuit boards.

    Creates cylindrical or hex standoffs with threaded or
    through-hole mounting options.
    """

    def __init__(self, config: PCBStandoffConfig):
        self.config = config

    def generate(self) -> PCBStandoffResult:
        """Generate a single PCB standoff."""
        cfg = self.config

        standoff = self._create_hex_standoff() if cfg.hex_outer else self._create_round_standoff()

        return PCBStandoffResult(
            standoff=standoff,
            metadata={
                "height": cfg.height,
                "screw_size": cfg.screw_size,
                "threaded": cfg.threaded,
            },
        )

    def _create_round_standoff(self) -> Part:
        """Create cylindrical standoff."""
        cfg = self.config

        # Base
        result = Cylinder(
            cfg.base_diameter / 2, cfg.base_height, align=(Align.CENTER, Align.CENTER, Align.MIN)
        )

        # Main column on top of base
        column = Cylinder(
            cfg.outer_diameter / 2, cfg.height, align=(Align.CENTER, Align.CENTER, Align.MIN)
        ).moved(Location((0, 0, cfg.base_height)))
        result = result.fuse(column)

        # Center hole through entire part
        total_height = cfg.base_height + cfg.height
        hole = Cylinder(
            cfg.inner_diameter / 2, total_height, align=(Align.CENTER, Align.CENTER, Align.MIN)
        )
        return result.cut(hole)

    def _create_hex_standoff(self) -> Part:
        """Create hexagonal standoff."""
        cfg = self.config

        # Base (round)
        result = Cylinder(
            cfg.base_diameter / 2, cfg.base_height, align=(Align.CENTER, Align.CENTER, Align.MIN)
        )

        # Hex column - use RegularPolygon for hexagon
        # Create hex sketch and extrude
        with BuildSketch() as hex_sketch:
            RegularPolygon(cfg.outer_diameter / 2, 6)
        hex_column = extrude(hex_sketch.sketch, amount=cfg.height)
        hex_column = hex_column.moved(Location((0, 0, cfg.base_height)))
        result = result.fuse(hex_column)

        # Center hole through entire part
        total_height = cfg.base_height + cfg.height
        hole = Cylinder(
            cfg.inner_diameter / 2, total_height, align=(Align.CENTER, Align.CENTER, Align.MIN)
        )
        return result.cut(hole)

    def generate_array(
        self,
        positions: list[tuple[float, float]],
    ) -> list[Part]:
        """Generate array of standoffs at specified positions."""
        standoffs = []
        single = self.generate().standoff

        for x, y in positions:
            positioned = single.moved(Location((x, y, 0)))
            standoffs.append(positioned)

        return standoffs


# =============================================================================
# Factory Functions
# =============================================================================


def create_snap_fit(
    length: float = 15.0,
    width: float = 8.0,
    thickness: float = 2.0,
    hook_height: float = 2.5,
    style: SnapFitStyle = SnapFitStyle.CANTILEVER,
) -> SnapFitResult:
    """
    Create a snap-fit clip.

    Args:
        length: Cantilever beam length in mm
        width: Clip width in mm
        thickness: Base thickness in mm
        hook_height: Retaining hook height in mm
        style: Snap-fit style

    Returns:
        SnapFitResult with generated clip
    """
    config = SnapFitConfig(
        length=length,
        width=width,
        thickness=thickness,
        hook_height=hook_height,
        style=style,
    )
    return SnapFitGenerator(config).generate()


def create_din_rail_mount(
    mount_width: float = 50.0,
    mount_height: float = 30.0,
    mount_thickness: float = 3.0,
    rail_size: DINRailSize = DINRailSize.TS35,
) -> DINRailResult:
    """
    Create a DIN rail mounting adapter.

    Args:
        mount_width: Width of mounting plate in mm
        mount_height: Height of mounting plate in mm
        mount_thickness: Plate thickness in mm
        rail_size: DIN rail standard size

    Returns:
        DINRailResult with generated mount
    """
    config = DINRailConfig(
        mount_width=mount_width,
        mount_height=mount_height,
        mount_thickness=mount_thickness,
        rail_size=rail_size,
    )
    return DINRailGenerator(config).generate()


def create_wall_mount(
    bracket_width: float = 40.0,
    bracket_height: float = 25.0,
    bracket_depth: float = 20.0,
    keyhole_count: int = 2,
    keyhole_spacing: float = 30.0,
    add_ribs: bool = True,
) -> WallMountResult:
    """
    Create a wall mounting bracket with keyholes.

    Args:
        bracket_width: Width of bracket in mm
        bracket_height: Height of wall plate in mm
        bracket_depth: Depth of shelf projection in mm
        keyhole_count: Number of keyhole slots
        keyhole_spacing: Center-to-center spacing in mm
        add_ribs: Whether to add stiffener ribs

    Returns:
        WallMountResult with generated bracket
    """
    config = WallMountConfig(
        bracket_width=bracket_width,
        bracket_height=bracket_height,
        bracket_depth=bracket_depth,
        keyhole_count=keyhole_count,
        keyhole_spacing=keyhole_spacing,
        add_ribs=add_ribs,
    )
    return WallMountGenerator(config).generate()


def create_pcb_standoff(
    height: float = 10.0,
    screw_size: str = "M3",
    hex_outer: bool = False,
) -> PCBStandoffResult:
    """
    Create a PCB standoff.

    Args:
        height: Standoff height above surface in mm
        screw_size: Metric screw size
        hex_outer: Use hex shape instead of round

    Returns:
        PCBStandoffResult with generated standoff
    """
    # Map screw size to dimensions
    screw_dims = {
        "M2": (4.0, 2.2),
        "M2.5": (5.0, 2.7),
        "M3": (6.0, 3.2),
        "M4": (8.0, 4.2),
    }
    outer, inner = screw_dims.get(screw_size, (6.0, 3.2))

    config = PCBStandoffConfig(
        height=height,
        outer_diameter=outer,
        inner_diameter=inner,
        base_diameter=outer + 2,
        screw_size=screw_size,
        hex_outer=hex_outer,
    )
    return PCBStandoffGenerator(config).generate()
