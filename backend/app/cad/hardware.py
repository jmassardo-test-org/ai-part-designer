"""
Standard hardware catalog for CAD assemblies.

Provides dimensions and supplier references for common fasteners,
threaded inserts, and other hardware.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class HardwareType(StrEnum):
    """Types of hardware components."""

    SCREW = "screw"
    NUT = "nut"
    WASHER = "washer"
    THREADED_INSERT = "threaded_insert"
    STANDOFF = "standoff"
    GASKET = "gasket"


class ScrewHead(StrEnum):
    """Screw head styles."""

    SOCKET_HEAD = "socket_head"
    BUTTON_HEAD = "button_head"
    FLAT_HEAD = "flat_head"
    PAN_HEAD = "pan_head"
    HEX_HEAD = "hex_head"


class ScrewDrive(StrEnum):
    """Screw drive types."""

    HEX = "hex"
    PHILLIPS = "phillips"
    TORX = "torx"
    SLOTTED = "slotted"


@dataclass
class HardwareSpec:
    """
    Specification for a hardware component.

    Includes dimensions for CAD modeling and supplier references.
    """

    type: HardwareType
    name: str
    description: str

    # Key dimensions in mm
    dimensions: dict[str, float] = field(default_factory=dict)

    # Supplier information
    mcmaster_pn: str | None = None
    supplier_url: str | None = None

    # Material
    material: str = "Steel"
    finish: str = "Black Oxide"

    # Additional properties
    properties: dict[str, Any] = field(default_factory=dict)

    def get_dimension(self, name: str, default: float = 0.0) -> float:
        """Get a dimension value."""
        return self.dimensions.get(name, default)


# =============================================================================
# Metric Screw Dimensions (ISO 4762 Socket Head Cap Screws)
# =============================================================================

METRIC_SOCKET_HEAD_SCREWS = {
    # (thread_diameter, head_diameter, head_height, hex_size)
    "M2": (2.0, 3.8, 2.0, 1.5),
    "M2.5": (2.5, 4.5, 2.5, 2.0),
    "M3": (3.0, 5.5, 3.0, 2.5),
    "M4": (4.0, 7.0, 4.0, 3.0),
    "M5": (5.0, 8.5, 5.0, 4.0),
    "M6": (6.0, 10.0, 6.0, 5.0),
    "M8": (8.0, 13.0, 8.0, 6.0),
    "M10": (10.0, 16.0, 10.0, 8.0),
}

# Common screw lengths in mm
COMMON_SCREW_LENGTHS = [6, 8, 10, 12, 16, 20, 25, 30, 35, 40, 50]


# =============================================================================
# Heat-Set Threaded Inserts (for 3D printing / plastic)
# =============================================================================

THREADED_INSERTS = {
    # (outer_diameter, length, hole_diameter_for_install)
    "M2": (3.2, 3.0, 2.8),
    "M2.5": (4.0, 4.0, 3.5),
    "M3": (4.6, 5.7, 4.0),
    "M4": (5.6, 6.4, 5.0),
    "M5": (6.4, 7.1, 5.6),
    "M6": (8.0, 9.5, 7.0),
}

# McMaster-Carr part numbers for heat-set inserts
MCMASTER_THREADED_INSERTS = {
    "M2": "94180A307",
    "M2.5": "94180A312",
    "M3": "94180A331",
    "M4": "94180A351",
    "M5": "94180A361",
    "M6": "94180A371",
}


# =============================================================================
# Clearance and Tap Hole Sizes
# =============================================================================

CLEARANCE_HOLES = {
    # Close fit clearance holes
    "M2": 2.2,
    "M2.5": 2.7,
    "M3": 3.2,
    "M4": 4.3,
    "M5": 5.3,
    "M6": 6.4,
    "M8": 8.4,
    "M10": 10.5,
}

TAP_DRILL_SIZES = {
    # For cutting threads in metal
    "M2": 1.6,
    "M2.5": 2.05,
    "M3": 2.5,
    "M4": 3.3,
    "M5": 4.2,
    "M6": 5.0,
    "M8": 6.8,
    "M10": 8.5,
}


# =============================================================================
# Hardware Catalog Functions
# =============================================================================


def get_screw_spec(
    size: str,
    length: float,
    head: ScrewHead = ScrewHead.SOCKET_HEAD,
    material: str = "Steel",
) -> HardwareSpec:
    """
    Get specification for a metric screw.

    Args:
        size: Metric size (e.g., "M3", "M4")
        length: Screw length in mm
        head: Head style
        material: Material type

    Returns:
        HardwareSpec for the screw
    """
    if size not in METRIC_SOCKET_HEAD_SCREWS:
        raise ValueError(f"Unknown screw size: {size}")

    thread_dia, head_dia, head_height, hex_size = METRIC_SOCKET_HEAD_SCREWS[size]

    # McMaster part number pattern for socket head cap screws
    # This is simplified - real lookup would need a database
    mcmaster_pn = f"91290A{size[1:]}"  # Approximate pattern

    return HardwareSpec(
        type=HardwareType.SCREW,
        name=f"{size} x {length}mm Socket Head Cap Screw",
        description=f"ISO 4762 {size} x {length}mm socket head cap screw",
        dimensions={
            "thread_diameter": thread_dia,
            "head_diameter": head_dia,
            "head_height": head_height,
            "hex_size": hex_size,
            "length": length,
            "thread_pitch": thread_dia * 0.175,  # Coarse pitch approximation
        },
        mcmaster_pn=mcmaster_pn,
        supplier_url=f"https://www.mcmaster.com/{mcmaster_pn}",
        material=material,
        properties={
            "head_type": head.value,
            "drive": ScrewDrive.HEX.value,
        },
    )


def get_threaded_insert_spec(size: str) -> HardwareSpec:
    """
    Get specification for a heat-set threaded insert.

    Args:
        size: Metric thread size (e.g., "M3", "M4")

    Returns:
        HardwareSpec for the insert
    """
    if size not in THREADED_INSERTS:
        raise ValueError(f"Unknown insert size: {size}")

    outer_dia, length, hole_dia = THREADED_INSERTS[size]
    mcmaster_pn = MCMASTER_THREADED_INSERTS.get(size)

    return HardwareSpec(
        type=HardwareType.THREADED_INSERT,
        name=f"{size} Heat-Set Threaded Insert",
        description=f"Brass heat-set insert for {size} thread in plastic",
        dimensions={
            "outer_diameter": outer_dia,
            "length": length,
            "install_hole_diameter": hole_dia,
            "thread_size": float(size[1:]),  # Extract number from "M3" -> 3.0
        },
        mcmaster_pn=mcmaster_pn,
        supplier_url=f"https://www.mcmaster.com/{mcmaster_pn}" if mcmaster_pn else None,
        material="Brass",
        finish="Plain",
    )


def get_clearance_hole(size: str) -> float:
    """Get clearance hole diameter for a screw size."""
    if size not in CLEARANCE_HOLES:
        raise ValueError(f"Unknown size: {size}")
    return CLEARANCE_HOLES[size]


def get_insert_hole(size: str) -> float:
    """Get hole diameter for installing a heat-set insert."""
    if size not in THREADED_INSERTS:
        raise ValueError(f"Unknown size: {size}")
    return THREADED_INSERTS[size][2]


def recommend_screw_length(
    material_thickness: float,
    insert_length: float,
    head_clearance: float = 0.5,
) -> float:
    """
    Recommend screw length for going through material into insert.

    Args:
        material_thickness: Thickness of top material (lid)
        insert_length: Length of threaded insert
        head_clearance: Extra clearance for head seating

    Returns:
        Recommended screw length (rounded to standard size)
    """
    ideal = material_thickness + insert_length * 0.8 + head_clearance

    # Round to nearest standard length
    for length in COMMON_SCREW_LENGTHS:
        if length >= ideal:
            return float(length)

    return float(COMMON_SCREW_LENGTHS[-1])


@dataclass
class BillOfMaterials:
    """Bill of materials for an assembly."""

    items: list[tuple[HardwareSpec, int]] = field(default_factory=list)

    def add(self, spec: HardwareSpec, quantity: int = 1) -> None:
        """Add hardware to the BOM."""
        # Check if already exists
        for i, (existing, qty) in enumerate(self.items):
            if existing.name == spec.name:
                self.items[i] = (existing, qty + quantity)
                return
        self.items.append((spec, quantity))

    def to_dict(self) -> list[dict]:
        """Convert to dict format."""
        return [
            {
                "name": spec.name,
                "type": spec.type.value,
                "quantity": qty,
                "mcmaster_pn": spec.mcmaster_pn,
                "supplier_url": spec.supplier_url,
                "material": spec.material,
            }
            for spec, qty in self.items
        ]
