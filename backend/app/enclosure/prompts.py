"""
Enclosure Generation Prompts

AI prompts for generating enclosure CadQuery code based on
component specifications and layout.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field

from app.enclosure.schemas import (
    EnclosureOptions,
    EnclosureStyle,
    LidClosureType,
    SpatialLayout,
    VentilationPattern,
)
from app.schemas.component_specs import (
    ClearanceZone,
    Connector,
    Dimensions,
    MountingHole,
    Position3D,
    ThermalProperties,
)

# =============================================================================
# System Prompts
# =============================================================================

ENCLOSURE_SYSTEM_PROMPT = """You are an expert CAD engineer specializing in enclosure design for electronic components.
Your task is to generate CadQuery Python code that creates custom enclosures.

Key responsibilities:
1. Create an enclosure that fits all components with proper clearance
2. Generate mounting standoffs at correct positions for each component's mounting holes
3. Create cutouts for all connectors on the appropriate faces
4. Add ventilation features when thermal requirements indicate
5. Generate a removable lid with appropriate closure mechanism

Code requirements:
- Use CadQuery (import as `cq`)
- All dimensions in millimeters
- Origin at center-bottom of enclosure
- Create separate bodies for base and lid
- Use proper fillets for printability
- Include comments explaining each section

Output format:
Return ONLY valid Python code that:
1. Defines a function `generate_enclosure()` that returns a tuple of (base, lid)
2. Uses proper CadQuery operations
3. Is syntactically correct and runnable

Do NOT include:
- Import statements (they will be added)
- Markdown code blocks
- Explanatory text outside comments
- Print statements"""


ENCLOSURE_USER_TEMPLATE = """Generate a CadQuery enclosure with the following specifications:

## Enclosure Style: {style_name}
- Wall thickness: {wall_thickness}mm
- Floor thickness: {floor_thickness}mm
- Lid thickness: {lid_thickness}mm
- Corner radius: {corner_radius}mm
- Lid closure: {lid_closure}

## Internal Dimensions
- Length (X): {internal_length}mm
- Width (Y): {internal_width}mm
- Height (Z): {internal_height}mm

## Components and Positions
{components_json}

## Mounting Standoffs Required
{standoffs_json}

## Connector Cutouts Required
{cutouts_json}

## Ventilation
{ventilation_spec}

## Additional Requirements
{additional_requirements}

Generate the CadQuery code for this enclosure."""


# =============================================================================
# Few-Shot Examples
# =============================================================================

ENCLOSURE_EXAMPLE_INPUT = """Generate a CadQuery enclosure with the following specifications:

## Enclosure Style: minimal
- Wall thickness: 2.0mm
- Floor thickness: 2.0mm
- Lid thickness: 2.0mm
- Corner radius: 3.0mm
- Lid closure: snap_fit

## Internal Dimensions
- Length (X): 90mm
- Width (Y): 60mm
- Height (Z): 25mm

## Components and Positions
[{"name": "Raspberry Pi 4", "position": {"x": 5, "y": 5, "z": 5}}]

## Mounting Standoffs Required
[
  {"x": 8.5, "y": 8.5, "height": 5, "outer_diameter": 6, "inner_diameter": 2.5},
  {"x": 66.5, "y": 8.5, "height": 5, "outer_diameter": 6, "inner_diameter": 2.5},
  {"x": 8.5, "y": 56.5, "height": 5, "outer_diameter": 6, "inner_diameter": 2.5},
  {"x": 66.5, "y": 56.5, "height": 5, "outer_diameter": 6, "inner_diameter": 2.5}
]

## Connector Cutouts Required
[
  {"face": "left", "center_x": 10, "center_y": 8, "width": 9, "height": 3.5, "name": "USB-C Power"},
  {"face": "left", "center_x": 30, "center_y": 8, "width": 15, "height": 5.5, "name": "HDMI"},
  {"face": "right", "center_x": 15, "center_y": 10, "width": 16, "height": 13.5, "name": "Ethernet"}
]

## Ventilation
Pattern: parallel_slots on top, slot_width: 2mm, slot_spacing: 3mm

## Additional Requirements
Add snap-fit clips on lid, 4 rubber feet mounting points"""


ENCLOSURE_EXAMPLE_OUTPUT = '''def generate_enclosure():
    """Generate enclosure base and lid."""

    # Parameters
    wall = 2.0
    floor = 2.0
    lid_thick = 2.0
    corner_r = 3.0

    # External dimensions
    ext_length = 90 + 2 * wall  # 94mm
    ext_width = 60 + 2 * wall   # 64mm
    ext_height = 25 + floor     # 27mm (base height without lid)

    # =========================================================================
    # BASE
    # =========================================================================

    # Create outer shell
    base = (
        cq.Workplane("XY")
        .box(ext_length, ext_width, ext_height, centered=(True, True, False))
        .edges("|Z")
        .fillet(corner_r)
    )

    # Hollow out interior
    base = (
        base
        .faces(">Z")
        .workplane()
        .rect(ext_length - 2 * wall, ext_width - 2 * wall)
        .cutBlind(-(ext_height - floor))
    )

    # Add internal fillets
    base = base.edges("<Z").edges("not(<Z or >Z)").fillet(1.0)

    # -------------------------------------------------------------------------
    # Mounting Standoffs
    # -------------------------------------------------------------------------
    standoffs = [
        (8.5, 8.5), (66.5, 8.5),
        (8.5, 56.5), (66.5, 56.5)
    ]
    standoff_h = 5.0
    standoff_od = 6.0
    standoff_id = 2.5

    for sx, sy in standoffs:
        # Convert from internal coords to enclosure coords
        px = sx - 45 + wall  # Center offset
        py = sy - 30 + wall

        # Add standoff
        standoff = (
            cq.Workplane("XY")
            .workplane(offset=floor)
            .center(px, py)
            .circle(standoff_od / 2)
            .extrude(standoff_h)
        )
        # Add hole
        standoff = (
            standoff
            .faces(">Z")
            .workplane()
            .hole(standoff_id)
        )
        base = base.union(standoff)

    # -------------------------------------------------------------------------
    # Connector Cutouts
    # -------------------------------------------------------------------------

    # USB-C on left face
    base = (
        base
        .faces("<X")
        .workplane(centerOption="CenterOfMass")
        .center(10 - 30, 8 - ext_height/2 + floor)
        .rect(9, 3.5)
        .cutThruAll()
    )

    # HDMI on left face
    base = (
        base
        .faces("<X")
        .workplane(centerOption="CenterOfMass")
        .center(30 - 30, 8 - ext_height/2 + floor)
        .rect(15, 5.5)
        .cutThruAll()
    )

    # Ethernet on right face
    base = (
        base
        .faces(">X")
        .workplane(centerOption="CenterOfMass")
        .center(15 - 30, 10 - ext_height/2 + floor)
        .rect(16, 13.5)
        .cutThruAll()
    )

    # -------------------------------------------------------------------------
    # Lid Snap-Fit Clips (on base)
    # -------------------------------------------------------------------------
    clip_positions = [
        (0, ext_width/2 - 1),   # Front center
        (0, -ext_width/2 + 1),  # Back center
        (ext_length/2 - 1, 0),  # Right center
        (-ext_length/2 + 1, 0), # Left center
    ]

    for cx, cy in clip_positions:
        # Add clip receiver notch
        base = (
            base
            .faces(">Z")
            .workplane()
            .center(cx, cy)
            .rect(4, 2)
            .cutBlind(-3)
        )

    # -------------------------------------------------------------------------
    # Rubber Feet Mounting Points
    # -------------------------------------------------------------------------
    feet_inset = 8.0
    feet_diameter = 8.0
    feet_positions = [
        (-ext_length/2 + feet_inset, -ext_width/2 + feet_inset),
        (ext_length/2 - feet_inset, -ext_width/2 + feet_inset),
        (-ext_length/2 + feet_inset, ext_width/2 - feet_inset),
        (ext_length/2 - feet_inset, ext_width/2 - feet_inset),
    ]

    for fx, fy in feet_positions:
        base = (
            base
            .faces("<Z")
            .workplane()
            .center(fx, fy)
            .hole(feet_diameter, 2)  # Recess for rubber foot
        )

    # =========================================================================
    # LID
    # =========================================================================

    lid_height = lid_thick + 3  # Extra for overlap

    lid = (
        cq.Workplane("XY")
        .box(ext_length, ext_width, lid_height, centered=(True, True, False))
        .edges("|Z")
        .fillet(corner_r)
    )

    # Create lip that fits inside base
    lip_clearance = 0.3
    lid = (
        lid
        .faces("<Z")
        .workplane()
        .rect(
            ext_length - 2 * wall - lip_clearance,
            ext_width - 2 * wall - lip_clearance
        )
        .extrude(-3, combine=False)
        .union(lid)
    )

    # -------------------------------------------------------------------------
    # Ventilation Slots
    # -------------------------------------------------------------------------
    slot_width = 2.0
    slot_spacing = 3.0
    slot_length = ext_length * 0.6

    # Create slot pattern
    num_slots = int((ext_width * 0.6) / (slot_width + slot_spacing))
    start_y = -num_slots * (slot_width + slot_spacing) / 2

    for i in range(num_slots):
        slot_y = start_y + i * (slot_width + slot_spacing)
        lid = (
            lid
            .faces(">Z")
            .workplane()
            .center(0, slot_y)
            .rect(slot_length, slot_width)
            .cutThruAll()
        )

    # -------------------------------------------------------------------------
    # Snap-Fit Clips (on lid)
    # -------------------------------------------------------------------------
    for cx, cy in clip_positions:
        clip = (
            cq.Workplane("XY")
            .workplane(offset=-3)
            .center(cx, cy)
            .rect(3.5, 1.5)
            .extrude(-2)
        )
        # Add angled catch
        clip = clip.faces("<Z").edges(">Y" if cy > 0 else "<Y").chamfer(1)
        lid = lid.union(clip)

    return base, lid
'''


# =============================================================================
# Prompt Builder
# =============================================================================


@dataclass
class ComponentData:
    """Component data for prompt building."""

    id: str
    name: str
    dimensions: Dimensions
    mounting_holes: list[MountingHole] = field(default_factory=list)
    connectors: list[Connector] = field(default_factory=list)
    clearance_zones: list[ClearanceZone] = field(default_factory=list)
    thermal_properties: ThermalProperties | None = None
    position: Position3D | None = None


@dataclass
class EnclosurePromptBuilder:
    """Builds prompts for enclosure generation."""

    components: list[ComponentData]
    style: EnclosureStyle
    options: EnclosureOptions
    layout: SpatialLayout | None = None

    def build_system_prompt(self) -> str:
        """Get the system prompt."""
        return ENCLOSURE_SYSTEM_PROMPT

    def build_user_prompt(self) -> str:
        """Build the complete user prompt."""
        # Calculate internal dimensions
        internal_dims = self._calculate_internal_dimensions()

        # Build component JSON
        components_json = self._build_components_json()

        # Build standoffs JSON
        standoffs_json = self._build_standoffs_json()

        # Build cutouts JSON
        cutouts_json = self._build_cutouts_json()

        # Build ventilation spec
        ventilation_spec = self._build_ventilation_spec()

        # Build additional requirements
        additional = self._build_additional_requirements()

        return ENCLOSURE_USER_TEMPLATE.format(
            style_name=self.style.style_type.value,
            wall_thickness=self.style.wall_thickness,
            floor_thickness=self.style.floor_thickness,
            lid_thickness=self.style.lid_thickness,
            corner_radius=self.style.corner_radius,
            lid_closure=self.style.lid_closure.value,
            internal_length=internal_dims.length,
            internal_width=internal_dims.width,
            internal_height=internal_dims.height,
            components_json=components_json,
            standoffs_json=standoffs_json,
            cutouts_json=cutouts_json,
            ventilation_spec=ventilation_spec,
            additional_requirements=additional,
        )

    def build_messages(self) -> list[dict[str, str]]:
        """Build complete message list for API call."""
        return [
            {"role": "system", "content": self.build_system_prompt()},
            # Few-shot example
            {"role": "user", "content": ENCLOSURE_EXAMPLE_INPUT},
            {"role": "assistant", "content": ENCLOSURE_EXAMPLE_OUTPUT},
            # Actual request
            {"role": "user", "content": self.build_user_prompt()},
        ]

    def _calculate_internal_dimensions(self) -> Dimensions:
        """Calculate required internal dimensions from components."""
        if self.layout and self.layout.internal_dimensions:
            return self.layout.internal_dimensions

        # Calculate from component bounding boxes
        max_x = 0.0
        max_y = 0.0
        max_z = 0.0

        clearance = self.options.component_clearance
        standoff_height = self.options.pcb_standoff_height
        lid_clearance = self.options.lid_clearance

        for comp in self.components:
            dims = comp.dimensions.to_mm()
            pos = comp.position or Position3D(x=0, y=0, z=standoff_height)

            # Component extends to
            comp_max_x = pos.x + dims.length + clearance
            comp_max_y = pos.y + dims.width + clearance
            comp_max_z = pos.z + dims.height + lid_clearance

            # Check clearance zones
            for zone in comp.clearance_zones:
                zone_z = zone.bounds.max_z + zone.minimum_clearance
                comp_max_z = max(comp_max_z, zone_z + lid_clearance)

            max_x = max(max_x, comp_max_x)
            max_y = max(max_y, comp_max_y)
            max_z = max(max_z, comp_max_z)

        # Add clearance on minimum side too
        max_x += clearance
        max_y += clearance

        return Dimensions(
            length=max_x,
            width=max_y,
            height=max_z,
        )

    def _build_components_json(self) -> str:
        """Build JSON representation of components."""
        components_data = []
        standoff_height = self.options.pcb_standoff_height

        for _i, comp in enumerate(self.components):
            pos = comp.position
            if not pos and self.layout:
                # Find in layout
                for lpos in self.layout.components:
                    if str(lpos.component_id) == comp.id:
                        pos = lpos.position
                        break

            if not pos:
                pos = Position3D(x=0, y=0, z=standoff_height)

            components_data.append(
                {
                    "name": comp.name,
                    "dimensions": {
                        "length": comp.dimensions.length,
                        "width": comp.dimensions.width,
                        "height": comp.dimensions.height,
                    },
                    "position": {
                        "x": pos.x,
                        "y": pos.y,
                        "z": pos.z,
                    },
                }
            )

        return json.dumps(components_data, indent=2)

    def _build_standoffs_json(self) -> str:
        """Build JSON for all required standoffs."""
        standoffs = []
        standoff_height = self.options.pcb_standoff_height

        for comp in self.components:
            pos = comp.position or Position3D(x=0, y=0, z=standoff_height)

            for hole in comp.mounting_holes:
                # Calculate standoff dimensions based on hole
                outer_d = max(hole.diameter * 2.5, 5.0)
                inner_d = hole.diameter if hole.diameter < 3.5 else hole.diameter - 0.5

                standoffs.append(
                    {
                        "x": pos.x + hole.x,
                        "y": pos.y + hole.y,
                        "height": standoff_height,
                        "outer_diameter": round(outer_d, 1),
                        "inner_diameter": round(inner_d, 1),
                        "component": comp.name,
                        "label": hole.label,
                    }
                )

        return json.dumps(standoffs, indent=2)

    def _build_cutouts_json(self) -> str:
        """Build JSON for all required cutouts."""
        if not self.options.auto_cutouts:
            return "[]"

        cutouts = []
        tolerance = self.options.cutout_tolerance

        for comp in self.components:
            pos = comp.position or Position3D(x=0, y=0, z=0)

            for conn in comp.connectors:
                cutouts.append(
                    {
                        "face": conn.face.value,
                        "center_x": pos.x + conn.position.x,
                        "center_y": pos.z + conn.position.z,  # Y on face = Z in enclosure
                        "width": conn.cutout_width + tolerance,
                        "height": conn.cutout_height + tolerance,
                        "name": conn.name,
                        "type": conn.type.value,
                    }
                )

        return json.dumps(cutouts, indent=2)

    def _build_ventilation_spec(self) -> str:
        """Build ventilation specification string."""
        if not self.options.auto_ventilation:
            return f"Pattern: {self.style.ventilation.value}"

        # Check if any component needs ventilation
        needs_vent = False
        for comp in self.components:
            if comp.thermal_properties and getattr(comp.thermal_properties, "requires_venting", False):
                needs_vent = True
                break
            for zone in comp.clearance_zones:
                if zone.requires_venting:
                    needs_vent = True
                    break

        if needs_vent or self.style.ventilation != VentilationPattern.NONE:
            pattern = self.style.ventilation
            if pattern == VentilationPattern.NONE and needs_vent:
                pattern = VentilationPattern.PARALLEL_SLOTS

            return (
                f"Pattern: {pattern.value} on top, "
                f"slot_width: {self.style.vent_slot_width}mm, "
                f"slot_spacing: {self.style.vent_slot_spacing}mm"
            )

        return "No ventilation required"

    def _build_additional_requirements(self) -> str:
        """Build additional requirements string."""
        requirements = []

        # Lid closure
        if self.style.lid_closure == LidClosureType.SNAP_FIT:
            requirements.append("Add snap-fit clips on lid and matching receivers on base")
        elif self.style.lid_closure == LidClosureType.SCREW:
            requirements.append("Add screw bosses in corners (M3)")

        # Feet
        if self.style.add_feet:
            requirements.append(
                f"Add {4} rubber feet mounting points "
                f"(diameter: {self.style.feet_diameter}mm, "
                f"inset: {self.style.feet_inset}mm)"
            )

        # Assembly guides
        if self.options.add_assembly_guides:
            requirements.append("Add alignment pins/slots for lid positioning")

        # Separate lid
        if self.options.generate_lid_separately:
            requirements.append("Generate lid as a separate body")

        return "\n".join(f"- {req}" for req in requirements) if requirements else "None"


def build_enclosure_prompt(
    components: list[ComponentData],
    style: EnclosureStyle,
    options: EnclosureOptions,
    layout: SpatialLayout | None = None,
) -> list[dict[str, str]]:
    """
    Build a complete prompt for enclosure generation.

    Args:
        components: List of components with specifications
        style: Enclosure style parameters
        options: Generation options
        layout: Optional spatial layout

    Returns:
        List of message dicts for API call
    """
    builder = EnclosurePromptBuilder(
        components=components,
        style=style,
        options=options,
        layout=layout,
    )
    return builder.build_messages()
