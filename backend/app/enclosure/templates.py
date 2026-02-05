"""
Enclosure Style Templates

Pre-defined enclosure style templates for common use cases.
"""

from typing import Any

from app.enclosure.schemas import (
    EnclosureStyle,
    EnclosureStyleType,
    LidClosureType,
    VentilationPattern,
)

# =============================================================================
# Style Templates
# =============================================================================

MINIMAL_STYLE = EnclosureStyle(
    style_type=EnclosureStyleType.MINIMAL,
    wall_thickness=1.5,
    floor_thickness=1.5,
    lid_thickness=1.5,
    corner_radius=2.0,
    internal_corner_radius=0.5,
    lid_closure=LidClosureType.SNAP_FIT,
    lid_overlap=2.5,
    ventilation=VentilationPattern.NONE,
    add_feet=False,
)
"""
Minimal Style

- Thin walls (1.5mm) for tight fit
- Small corner radius for compact design
- Snap-fit lid for tool-less access
- No ventilation (add if needed)
- No feet

Best for: Small, indoor projects where size matters
"""


RUGGED_STYLE = EnclosureStyle(
    style_type=EnclosureStyleType.RUGGED,
    wall_thickness=3.0,
    floor_thickness=3.0,
    lid_thickness=3.0,
    corner_radius=5.0,
    internal_corner_radius=2.0,
    lid_closure=LidClosureType.SCREW,
    lid_overlap=5.0,
    ventilation=VentilationPattern.NONE,
    add_feet=True,
    feet_diameter=10.0,
    feet_inset=8.0,
)
"""
Rugged Style

- Thick walls (3mm) for durability
- Large corner radius for impact resistance
- Screw-down lid for secure closure
- No default ventilation (add holes for IP rating)
- Rubber feet for stability

Best for: Industrial, outdoor, or high-stress applications
"""


VENTED_STYLE = EnclosureStyle(
    style_type=EnclosureStyleType.VENTED,
    wall_thickness=2.0,
    floor_thickness=2.0,
    lid_thickness=2.0,
    corner_radius=3.0,
    internal_corner_radius=1.0,
    lid_closure=LidClosureType.SNAP_FIT,
    lid_overlap=3.0,
    ventilation=VentilationPattern.PARALLEL_SLOTS,
    vent_slot_width=2.0,
    vent_slot_spacing=3.0,
    add_feet=True,
    feet_diameter=8.0,
    feet_inset=6.0,
)
"""
Vented Style

- Standard walls (2mm)
- Parallel slot ventilation on lid
- Snap-fit lid for easy access
- Feet for airflow underneath

Best for: Projects with heat-generating components (RPi, etc.)
"""


STACKABLE_STYLE = EnclosureStyle(
    style_type=EnclosureStyleType.STACKABLE,
    wall_thickness=2.5,
    floor_thickness=2.0,
    lid_thickness=2.0,
    corner_radius=3.0,
    internal_corner_radius=1.0,
    lid_closure=LidClosureType.FRICTION,
    lid_overlap=4.0,
    ventilation=VentilationPattern.NONE,
    add_feet=False,  # Stacking features instead
)
"""
Stackable Style

- Interlocking edges for stacking
- Friction-fit lid for easy stacking
- No feet (bottom has matching interlock)
- Slightly thicker walls for structural integrity

Best for: Modular systems, rack-mounted, multi-unit projects
"""


DESKTOP_STYLE = EnclosureStyle(
    style_type=EnclosureStyleType.DESKTOP,
    wall_thickness=2.5,
    floor_thickness=2.5,
    lid_thickness=2.5,
    corner_radius=4.0,
    internal_corner_radius=1.5,
    lid_closure=LidClosureType.SNAP_FIT,
    lid_overlap=3.0,
    ventilation=VentilationPattern.GRID,
    vent_slot_width=2.0,
    vent_slot_spacing=4.0,
    add_feet=True,
    feet_diameter=10.0,
    feet_inset=10.0,
)
"""
Desktop Style

- Premium feel with smooth corners
- Grid ventilation pattern
- Angled front option for displays (custom parameter)
- Quality rubber feet
- Display-friendly proportions

Best for: Consumer devices, home automation hubs, NAS boxes
"""


# =============================================================================
# Template Registry
# =============================================================================

ENCLOSURE_STYLE_TEMPLATES: dict[EnclosureStyleType, EnclosureStyle] = {
    EnclosureStyleType.MINIMAL: MINIMAL_STYLE,
    EnclosureStyleType.RUGGED: RUGGED_STYLE,
    EnclosureStyleType.VENTED: VENTED_STYLE,
    EnclosureStyleType.STACKABLE: STACKABLE_STYLE,
    EnclosureStyleType.DESKTOP: DESKTOP_STYLE,
}


def get_style_template(
    style_type: EnclosureStyleType,
) -> EnclosureStyle:
    """
    Get a pre-defined style template.

    Args:
        style_type: Type of style to retrieve

    Returns:
        EnclosureStyle with pre-defined parameters

    Raises:
        ValueError: If style_type is CUSTOM or unknown
    """
    if style_type == EnclosureStyleType.CUSTOM:
        raise ValueError("CUSTOM style requires explicit parameters, use EnclosureStyle() directly")

    if style_type not in ENCLOSURE_STYLE_TEMPLATES:
        raise ValueError(f"Unknown style type: {style_type}")

    # Return a copy to prevent modification
    template = ENCLOSURE_STYLE_TEMPLATES[style_type]
    return template.model_copy()


def get_style_description(
    style_type: EnclosureStyleType,
) -> str:
    """Get human-readable description of a style."""
    descriptions = {
        EnclosureStyleType.MINIMAL: (
            "Thin walls, tight fit, snap-fit lid. "
            "Best for small indoor projects where size matters."
        ),
        EnclosureStyleType.RUGGED: (
            "Thick walls, rounded corners, screw-down lid with rubber feet. "
            "Best for industrial or high-stress applications."
        ),
        EnclosureStyleType.VENTED: (
            "Standard walls with parallel slot ventilation on lid. "
            "Best for projects with heat-generating components."
        ),
        EnclosureStyleType.STACKABLE: (
            "Interlocking edges for stacking multiple units. "
            "Best for modular systems and rack mounting."
        ),
        EnclosureStyleType.DESKTOP: (
            "Premium feel with smooth corners and grid ventilation. "
            "Best for consumer devices and home automation."
        ),
        EnclosureStyleType.CUSTOM: ("Fully customizable parameters."),
    }
    return descriptions.get(style_type, "Unknown style")


def list_available_styles() -> list[dict[str, Any]]:
    """
    List all available style templates with descriptions.

    Returns:
        List of dicts with style info
    """
    return [
        {
            "type": style_type.value,
            "name": style_type.name.title(),
            "description": get_style_description(style_type),
            "wall_thickness": template.wall_thickness,
            "lid_closure": template.lid_closure.value,
            "ventilation": template.ventilation.value,
        }
        for style_type, template in ENCLOSURE_STYLE_TEMPLATES.items()
    ]
