"""
Enclosure generator for multi-part box assemblies.

Generates box + lid enclosures with:
- Configurable wall thickness
- Mounting flanges with holes
- Gasket grooves
- Threaded insert bosses

Migrated from CadQuery to Build123d.
"""

from __future__ import annotations

import contextlib
import logging
import tempfile
import uuid
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any

from build123d import (
    Align,
    Axis,
    Box,
    BuildPart,
    Cylinder,
    Location,
    Mode,
    Part,
    export_step,
    export_stl,
    fillet,
)

from app.cad.hardware import (
    BillOfMaterials,
    get_clearance_hole,
    get_insert_hole,
    get_screw_spec,
    get_threaded_insert_spec,
    recommend_screw_length,
)

logger = logging.getLogger(__name__)


class EnclosureStyle(StrEnum):
    """Enclosure lid styles."""

    TOP_LID = "top_lid"  # Lid on top
    CLAMSHELL = "clamshell"  # Two halves
    SLIDE_LID = "slide_lid"  # Sliding lid


@dataclass
class EnclosureConfig:
    """Configuration for enclosure generation."""

    # External dimensions
    length: float = 100.0  # X dimension
    width: float = 80.0  # Y dimension
    height: float = 50.0  # Z dimension (total, including lid)

    # Wall and structure
    wall_thickness: float = 2.5
    lid_height_ratio: float = 0.25  # Lid is 25% of total height

    # Flange configuration
    flange_width: float = 8.0
    flange_thickness: float = 3.0

    # Mounting holes
    screw_size: str = "M3"
    num_screws_per_side: int = 2  # Screws per long side
    screw_inset: float = 6.0  # Distance from corner to hole center

    # Gasket
    gasket_groove: bool = True
    gasket_width: float = 2.0
    gasket_depth: float = 1.5

    # Threaded inserts
    use_threaded_inserts: bool = True

    # Corner radius
    corner_radius: float = 3.0

    # Style
    style: EnclosureStyle = EnclosureStyle.TOP_LID

    @property
    def lid_height(self) -> float:
        """Calculate lid height."""
        return self.height * self.lid_height_ratio

    @property
    def box_height(self) -> float:
        """Calculate box (base) height."""
        return self.height * (1 - self.lid_height_ratio)

    @property
    def internal_length(self) -> float:
        return self.length - 2 * self.wall_thickness

    @property
    def internal_width(self) -> float:
        return self.width - 2 * self.wall_thickness


@dataclass
class GeneratedPart:
    """A single generated CAD part."""

    name: str
    description: str
    shape: Part
    step_data: bytes | None = None
    stl_data: bytes | None = None
    step_path: Path | None = None
    stl_path: Path | None = None

    # Part metadata
    material: str = "ABS Plastic"
    color: str = "#3b82f6"

    def export(
        self,
        output_dir: Path,
        job_id: str,
    ) -> None:
        """Export part to STEP and STL.

        Files are encrypted at rest if FILE_ENCRYPTION_ENABLED is set.
        """
        from app.core.file_encryption import (
            ENCRYPTED_MARKER_SUFFIX,
            is_encryption_enabled,
        )
        from app.core.security import encryption_service

        base_name = f"{self.name.lower().replace(' ', '_')}_{job_id[:8]}"

        # Export STEP
        self.step_path = output_dir / f"{base_name}.step"
        export_step(self.shape, str(self.step_path))
        self.step_data = self.step_path.read_bytes()

        # Export STL
        self.stl_path = output_dir / f"{base_name}.stl"
        export_stl(self.shape, str(self.stl_path))
        self.stl_data = self.stl_path.read_bytes()

        # Encrypt files at rest
        if is_encryption_enabled():
            encrypted_step = encryption_service.encrypt_bytes(self.step_data)
            self.step_path.write_bytes(encrypted_step)
            Path(str(self.step_path) + ENCRYPTED_MARKER_SUFFIX).write_text("1")

            encrypted_stl = encryption_service.encrypt_bytes(self.stl_data)
            self.stl_path.write_bytes(encrypted_stl)
            Path(str(self.stl_path) + ENCRYPTED_MARKER_SUFFIX).write_text("1")


@dataclass
class AssemblyResult:
    """Result of multi-part assembly generation."""

    name: str
    description: str
    parts: list[GeneratedPart] = field(default_factory=list)
    bom: BillOfMaterials = field(default_factory=BillOfMaterials)

    # Metadata
    job_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    config: dict[str, Any] = field(default_factory=dict)

    # Timing
    generate_time_ms: float = 0.0
    export_time_ms: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        """Convert to API response format."""
        return {
            "job_id": self.job_id,
            "name": self.name,
            "description": self.description,
            "parts": [
                {
                    "name": part.name,
                    "description": part.description,
                    "material": part.material,
                    "downloads": {
                        "step": f"/api/v1/generate/{self.job_id}/download/step/{part.name.lower().replace(' ', '_')}",
                        "stl": f"/api/v1/generate/{self.job_id}/download/stl/{part.name.lower().replace(' ', '_')}",
                    },
                }
                for part in self.parts
            ],
            "bom": self.bom.to_dict(),
            "config": self.config,
        }


class EnclosureGenerator:
    """
    Generates enclosure assemblies with box + lid.

    Creates properly mating parts with mounting holes,
    gasket grooves, and hardware specifications.
    """

    def __init__(self, config: EnclosureConfig):
        self.config = config
        self.bom = BillOfMaterials()

    def generate(self) -> AssemblyResult:
        """Generate the complete enclosure assembly."""
        import time

        start = time.monotonic()

        parts = []

        # Generate base box
        box = self._generate_box()
        parts.append(
            GeneratedPart(
                name="Enclosure Base",
                description="Bottom part of the enclosure with threaded insert bosses",
                shape=box,
                material="ABS Plastic",
                color="#3b82f6",
            )
        )

        # Generate lid
        lid = self._generate_lid()
        parts.append(
            GeneratedPart(
                name="Enclosure Lid",
                description="Top lid with clearance holes for screws",
                shape=lid,
                material="ABS Plastic",
                color="#60a5fa",
            )
        )

        # Add hardware to BOM
        self._add_hardware_to_bom()

        generate_time = (time.monotonic() - start) * 1000

        return AssemblyResult(
            name="Two-Part Enclosure",
            description=f"Enclosure {self.config.length}x{self.config.width}x{self.config.height}mm with flanged lid",
            parts=parts,
            bom=self.bom,
            config={
                "length": self.config.length,
                "width": self.config.width,
                "height": self.config.height,
                "wall_thickness": self.config.wall_thickness,
                "screw_size": self.config.screw_size,
            },
            generate_time_ms=generate_time,
        )

    def _generate_box(self) -> Part:
        """Generate the base box with flanges and insert bosses."""
        cfg = self.config

        with BuildPart() as builder:
            # Start with outer shell
            Box(
                cfg.length,
                cfg.width,
                cfg.box_height,
                align=(Align.CENTER, Align.CENTER, Align.CENTER),
            )

            # Fillet vertical edges
            fillet_r = min(cfg.corner_radius, cfg.length / 10, cfg.width / 10)
            if fillet_r > 0:
                vertical_edges = builder.edges().filter_by(Axis.Z)
                if vertical_edges:
                    with contextlib.suppress(Exception):
                        fillet(vertical_edges, fillet_r)

            # Hollow out the inside
            Box(
                cfg.internal_length,
                cfg.internal_width,
                cfg.box_height - cfg.wall_thickness,
                align=(Align.CENTER, Align.CENTER, Align.MAX),
                mode=Mode.SUBTRACT,
            ).locate(Location((0, 0, cfg.box_height / 2)))

            # Add flanges around the top edge
            Box(
                cfg.length + 2 * cfg.flange_width,
                cfg.width + 2 * cfg.flange_width,
                cfg.flange_thickness,
                align=(Align.CENTER, Align.CENTER, Align.MIN),
            ).locate(Location((0, 0, cfg.box_height / 2)))

            # Cut out center of flange
            Box(
                cfg.length - 2 * cfg.wall_thickness,
                cfg.width - 2 * cfg.wall_thickness,
                cfg.flange_thickness,
                align=(Align.CENTER, Align.CENTER, Align.MIN),
                mode=Mode.SUBTRACT,
            ).locate(Location((0, 0, cfg.box_height / 2)))

            # Add mounting holes for threaded inserts
            hole_positions = self._get_mounting_hole_positions()
            insert_hole_dia = get_insert_hole(cfg.screw_size)
            insert_spec = get_threaded_insert_spec(cfg.screw_size)
            insert_depth = insert_spec.get_dimension("length") + 1.0

            for x, y in hole_positions:
                Cylinder(
                    insert_hole_dia / 2,
                    insert_depth,
                    align=(Align.CENTER, Align.CENTER, Align.MAX),
                    mode=Mode.SUBTRACT,
                ).locate(Location((x, y, cfg.box_height / 2 + cfg.flange_thickness)))

            # Add gasket groove on top face of flange
            if cfg.gasket_groove:
                gasket_offset = cfg.wall_thickness + cfg.gasket_width

                # Outer groove boundary
                outer_l = cfg.length - 2 * gasket_offset
                outer_w = cfg.width - 2 * gasket_offset
                inner_l = outer_l - 2 * cfg.gasket_width
                inner_w = outer_w - 2 * cfg.gasket_width

                # Outer box for groove
                Box(
                    outer_l,
                    outer_w,
                    cfg.gasket_depth,
                    align=(Align.CENTER, Align.CENTER, Align.MAX),
                    mode=Mode.SUBTRACT,
                ).locate(Location((0, 0, cfg.box_height / 2 + cfg.flange_thickness)))

                # Fill back inner part (leaving groove)
                Box(
                    inner_l,
                    inner_w,
                    cfg.gasket_depth,
                    align=(Align.CENTER, Align.CENTER, Align.MAX),
                ).locate(Location((0, 0, cfg.box_height / 2 + cfg.flange_thickness)))

        return builder.part

    def _generate_lid(self) -> Part:
        """Generate the lid with clearance holes."""
        cfg = self.config

        with BuildPart() as builder:
            # Lid outer dimensions match flange
            Box(
                cfg.length + 2 * cfg.flange_width,
                cfg.width + 2 * cfg.flange_width,
                cfg.lid_height,
                align=(Align.CENTER, Align.CENTER, Align.CENTER),
            )

            # Fillet vertical edges
            fillet_r = min(
                cfg.corner_radius + cfg.flange_width / 2, (cfg.length + 2 * cfg.flange_width) / 10
            )
            if fillet_r > 0:
                vertical_edges = builder.edges().filter_by(Axis.Z)
                if vertical_edges:
                    with contextlib.suppress(Exception):
                        fillet(vertical_edges, fillet_r)

            # Hollow out
            Box(
                cfg.internal_length,
                cfg.internal_width,
                cfg.lid_height - cfg.wall_thickness,
                align=(Align.CENTER, Align.CENTER, Align.MIN),
                mode=Mode.SUBTRACT,
            ).locate(Location((0, 0, -cfg.lid_height / 2)))

            # Add lip that fits inside the box
            lip_height = cfg.flange_thickness
            Box(
                cfg.length - 0.5,  # Slight clearance
                cfg.width - 0.5,
                lip_height,
                align=(Align.CENTER, Align.CENTER, Align.MAX),
            ).locate(Location((0, 0, -cfg.lid_height / 2)))

            # Hollow the lip
            Box(
                cfg.internal_length,
                cfg.internal_width,
                lip_height,
                align=(Align.CENTER, Align.CENTER, Align.MAX),
                mode=Mode.SUBTRACT,
            ).locate(Location((0, 0, -cfg.lid_height / 2)))

            # Add clearance holes for screws (with counterbore)
            hole_positions = self._get_mounting_hole_positions()
            clearance_dia = get_clearance_hole(cfg.screw_size)

            # Counterbore for screw heads
            screw_spec = get_screw_spec(cfg.screw_size, 12)
            head_dia = screw_spec.get_dimension("head_diameter") + 0.5
            head_depth = screw_spec.get_dimension("head_height") + 0.5

            for x, y in hole_positions:
                # Through hole
                Cylinder(
                    clearance_dia / 2,
                    cfg.lid_height,
                    align=(Align.CENTER, Align.CENTER, Align.CENTER),
                    mode=Mode.SUBTRACT,
                ).locate(Location((x, y, 0)))

                # Counterbore
                Cylinder(
                    head_dia / 2,
                    head_depth,
                    align=(Align.CENTER, Align.CENTER, Align.MAX),
                    mode=Mode.SUBTRACT,
                ).locate(Location((x, y, cfg.lid_height / 2)))

        return builder.part

    def _get_mounting_hole_positions(self) -> list[tuple[float, float]]:
        """Calculate mounting hole positions on the flange."""
        cfg = self.config
        positions = []

        # Corner holes
        x_offset = cfg.length / 2 + cfg.flange_width / 2
        y_offset = cfg.width / 2 + cfg.flange_width / 2

        positions.extend(
            [
                (x_offset, y_offset),
                (-x_offset, y_offset),
                (x_offset, -y_offset),
                (-x_offset, -y_offset),
            ]
        )

        # Additional holes along long sides if specified
        if cfg.num_screws_per_side > 1:
            spacing = cfg.length / (cfg.num_screws_per_side + 1)
            for i in range(1, cfg.num_screws_per_side):
                x = -cfg.length / 2 + spacing * (i + 0.5)
                positions.append((x, y_offset))
                positions.append((x, -y_offset))

        return positions

    def _add_hardware_to_bom(self) -> None:
        """Add required hardware to bill of materials."""
        cfg = self.config
        num_holes = len(self._get_mounting_hole_positions())

        # Threaded inserts
        insert_spec = get_threaded_insert_spec(cfg.screw_size)
        self.bom.add(insert_spec, num_holes)

        # Screws - calculate appropriate length
        screw_length = recommend_screw_length(
            material_thickness=cfg.lid_height,
            insert_length=insert_spec.get_dimension("length"),
        )
        screw_spec = get_screw_spec(cfg.screw_size, screw_length)
        self.bom.add(screw_spec, num_holes)

        # Gasket (if applicable)
        if cfg.gasket_groove:
            from app.cad.hardware import HardwareSpec, HardwareType

            # Calculate gasket length (perimeter)
            gasket_length = 2 * (cfg.length + cfg.width - 4 * cfg.wall_thickness)

            gasket = HardwareSpec(
                type=HardwareType.GASKET,
                name=f"{cfg.gasket_width}mm Rubber Gasket",
                description=f"Silicone rubber gasket, {cfg.gasket_width}mm wide x {cfg.gasket_depth}mm thick",
                dimensions={
                    "width": cfg.gasket_width,
                    "thickness": cfg.gasket_depth,
                    "length": gasket_length,
                },
                mcmaster_pn="1120N12",  # Generic silicone cord
                material="Silicone Rubber",
            )
            self.bom.add(gasket, 1)


def generate_enclosure(
    length: float = 100.0,
    width: float = 80.0,
    height: float = 50.0,
    wall_thickness: float = 2.5,
    screw_size: str = "M3",
    gasket: bool = True,
    output_dir: Path | None = None,
    job_id: str | None = None,
) -> AssemblyResult:
    """
    Generate a two-part enclosure assembly.

    Convenience function for creating enclosures.

    Args:
        length: External length (X) in mm
        width: External width (Y) in mm
        height: Total external height (Z) in mm
        wall_thickness: Wall thickness in mm
        screw_size: Metric screw size (e.g., "M3", "M4")
        gasket: Whether to include gasket groove
        output_dir: Directory for output files
        job_id: Unique job identifier

    Returns:
        AssemblyResult with generated parts and BOM
    """
    import time

    config = EnclosureConfig(
        length=length,
        width=width,
        height=height,
        wall_thickness=wall_thickness,
        screw_size=screw_size,
        gasket_groove=gasket,
    )

    generator = EnclosureGenerator(config)
    result = generator.generate()

    if job_id:
        result.job_id = job_id

    # Export parts
    if output_dir is None:
        output_dir = Path(tempfile.gettempdir()) / "cad_exports"
    output_dir.mkdir(parents=True, exist_ok=True)

    export_start = time.monotonic()
    for part in result.parts:
        part.export(output_dir, result.job_id)
    result.export_time_ms = (time.monotonic() - export_start) * 1000

    return result
