"""
Seed data for templates.

This script populates the database with initial templates
for the AI Part Designer platform.

Usage:
    python -m app.seeds.templates

Or via Makefile:
    make seed-templates
"""

import asyncio
from uuid import uuid4

# Template seed data organized by category
TEMPLATE_SEEDS = [
    # =============================================
    # ENCLOSURES
    # =============================================
    {
        "id": uuid4(),
        "name": "Rounded Box Enclosure",
        "slug": "rounded-box-enclosure",
        "description": "A customizable rectangular enclosure with rounded edges, perfect for electronics projects. Includes options for wall thickness, fillet radius, and mounting tabs.",
        "category": "enclosures",
        "subcategory": "electronics",
        "min_tier": "free",
        "is_featured": True,
        "tags": ["electronics", "box", "enclosure", "3d-printable"],
        "parameters": {
            "length": {
                "type": "number",
                "label": "Length",
                "unit": "mm",
                "min": 20,
                "max": 300,
                "step": 1,
            },
            "width": {
                "type": "number",
                "label": "Width",
                "unit": "mm",
                "min": 20,
                "max": 200,
                "step": 1,
            },
            "height": {
                "type": "number",
                "label": "Height",
                "unit": "mm",
                "min": 10,
                "max": 150,
                "step": 1,
            },
            "wall_thickness": {
                "type": "number",
                "label": "Wall Thickness",
                "unit": "mm",
                "min": 1,
                "max": 5,
                "step": 0.5,
            },
            "fillet_radius": {
                "type": "number",
                "label": "Corner Radius",
                "unit": "mm",
                "min": 0,
                "max": 10,
                "step": 0.5,
            },
            "include_lid": {
                "type": "boolean",
                "label": "Include Lid",
            },
            "mounting_tabs": {
                "type": "select",
                "label": "Mounting Tabs",
                "options": ["none", "corners", "sides"],
            },
        },
        "default_values": {
            "length": 100,
            "width": 60,
            "height": 30,
            "wall_thickness": 2,
            "fillet_radius": 3,
            "include_lid": True,
            "mounting_tabs": "none",
        },
        "cadquery_script": '''
from build123d import BuildPart, Box, Cylinder, Location, Mode, Align, fillet, Axis

def create_enclosure(length, width, height, wall_thickness, fillet_radius, include_lid, mounting_tabs):
    """Generate a rounded box enclosure using Build123d."""
    
    with BuildPart() as builder:
        # Outer shell
        Box(length, width, height, align=(Align.CENTER, Align.CENTER, Align.CENTER))
        
        # Apply fillet to vertical edges
        try:
            vertical_edges = builder.edges().filter_by(Axis.Z)
            if vertical_edges:
                fillet(vertical_edges, fillet_radius)
        except Exception:
            pass
        
        # Inner cavity (subtract)
        Box(
            length - 2 * wall_thickness,
            width - 2 * wall_thickness,
            height - wall_thickness,
            align=(Align.CENTER, Align.CENTER, Align.CENTER),
            mode=Mode.SUBTRACT
        ).locate(Location((0, 0, wall_thickness / 2)))
    
    box = builder.part
    
    # Add mounting tabs if requested
    if mounting_tabs == "corners":
        for x, y in [(1, 1), (1, -1), (-1, 1), (-1, -1)]:
            pos_x = x * (length / 2 + 5)
            pos_y = y * (width / 2 + 5)
            with BuildPart() as tab_builder:
                Box(10, 10, wall_thickness, align=(Align.CENTER, Align.CENTER, Align.CENTER))
                Cylinder(1.5, wall_thickness, align=(Align.CENTER, Align.CENTER, Align.CENTER), mode=Mode.SUBTRACT)
            tab = tab_builder.part.moved(Location((pos_x, pos_y, -height / 2 + wall_thickness / 2)))
            box = box.fuse(tab)
    
    result = {"body": box}
    
    # Create lid if requested
    if include_lid:
        with BuildPart() as lid_builder:
            Box(length, width, wall_thickness, align=(Align.CENTER, Align.CENTER, Align.CENTER))
            try:
                vertical_edges = lid_builder.edges().filter_by(Axis.Z)
                if vertical_edges:
                    fillet(vertical_edges, fillet_radius)
            except Exception:
                pass
        result["lid"] = lid_builder.part
    
    return result

# Execute with provided parameters
result = create_enclosure(
    length=params["length"],
    width=params["width"],
    height=params["height"],
    wall_thickness=params["wall_thickness"],
    fillet_radius=params["fillet_radius"],
    include_lid=params["include_lid"],
    mounting_tabs=params["mounting_tabs"],
)
''',
    },
    {
        "id": uuid4(),
        "name": "Raspberry Pi Case",
        "slug": "raspberry-pi-case",
        "description": "Enclosure designed specifically for Raspberry Pi boards. Supports Pi 3B, 3B+, 4B, and 5 with customizable ventilation and GPIO access.",
        "category": "enclosures",
        "subcategory": "electronics",
        "min_tier": "free",
        "is_featured": True,
        "tags": ["raspberry-pi", "electronics", "case", "3d-printable"],
        "parameters": {
            "pi_model": {
                "type": "select",
                "label": "Pi Model",
                "options": ["3B", "3B+", "4B", "5"],
            },
            "vent_style": {
                "type": "select",
                "label": "Ventilation Style",
                "options": ["none", "slots", "hexagon", "mesh"],
            },
            "include_fan_mount": {
                "type": "boolean",
                "label": "Include Fan Mount",
            },
            "gpio_access": {
                "type": "boolean",
                "label": "GPIO Access Slot",
            },
            "wall_thickness": {
                "type": "number",
                "label": "Wall Thickness",
                "unit": "mm",
                "min": 1.5,
                "max": 3,
                "step": 0.5,
            },
        },
        "default_values": {
            "pi_model": "4B",
            "vent_style": "hexagon",
            "include_fan_mount": True,
            "gpio_access": True,
            "wall_thickness": 2,
        },
        "cadquery_script": "# Raspberry Pi case script placeholder",
    },
    
    # =============================================
    # MECHANICAL PARTS
    # =============================================
    {
        "id": uuid4(),
        "name": "Parametric Gear",
        "slug": "parametric-gear",
        "description": "Involute spur gear with customizable module, tooth count, pressure angle, and bore. Suitable for 3D printing or machining.",
        "category": "mechanical",
        "subcategory": "gears",
        "min_tier": "pro",
        "is_featured": True,
        "tags": ["gear", "mechanical", "involute", "power-transmission"],
        "parameters": {
            "module": {
                "type": "number",
                "label": "Module",
                "unit": "mm",
                "min": 0.5,
                "max": 5,
                "step": 0.1,
            },
            "teeth": {
                "type": "number",
                "label": "Number of Teeth",
                "min": 8,
                "max": 100,
                "step": 1,
            },
            "pressure_angle": {
                "type": "number",
                "label": "Pressure Angle",
                "unit": "degrees",
                "min": 14.5,
                "max": 25,
                "step": 0.5,
            },
            "face_width": {
                "type": "number",
                "label": "Face Width",
                "unit": "mm",
                "min": 5,
                "max": 50,
                "step": 1,
            },
            "bore_diameter": {
                "type": "number",
                "label": "Bore Diameter",
                "unit": "mm",
                "min": 3,
                "max": 30,
                "step": 0.5,
            },
            "include_keyway": {
                "type": "boolean",
                "label": "Include Keyway",
            },
        },
        "default_values": {
            "module": 2,
            "teeth": 20,
            "pressure_angle": 20,
            "face_width": 10,
            "bore_diameter": 8,
            "include_keyway": False,
        },
        "cadquery_script": "# Parametric gear script placeholder",
    },
    {
        "id": uuid4(),
        "name": "Shaft Coupler",
        "slug": "shaft-coupler",
        "description": "Flexible shaft coupling for connecting two rotating shafts. Supports rigid, flexible, and jaw-type configurations.",
        "category": "mechanical",
        "subcategory": "couplings",
        "min_tier": "hobby",
        "is_featured": False,
        "tags": ["coupling", "shaft", "mechanical", "motor"],
        "parameters": {
            "shaft_diameter_1": {
                "type": "number",
                "label": "Shaft 1 Diameter",
                "unit": "mm",
                "min": 3,
                "max": 20,
                "step": 0.5,
            },
            "shaft_diameter_2": {
                "type": "number",
                "label": "Shaft 2 Diameter",
                "unit": "mm",
                "min": 3,
                "max": 20,
                "step": 0.5,
            },
            "coupler_type": {
                "type": "select",
                "label": "Coupler Type",
                "options": ["rigid", "flexible", "jaw"],
            },
            "length": {
                "type": "number",
                "label": "Overall Length",
                "unit": "mm",
                "min": 15,
                "max": 60,
                "step": 1,
            },
        },
        "default_values": {
            "shaft_diameter_1": 5,
            "shaft_diameter_2": 8,
            "coupler_type": "flexible",
            "length": 25,
        },
        "cadquery_script": "# Shaft coupler script placeholder",
    },
    
    # =============================================
    # BRACKETS & MOUNTS
    # =============================================
    {
        "id": uuid4(),
        "name": "L-Bracket",
        "slug": "l-bracket",
        "description": "Universal L-shaped mounting bracket with customizable dimensions and hole patterns. Perfect for structural connections.",
        "category": "brackets",
        "subcategory": "structural",
        "min_tier": "free",
        "is_featured": False,
        "tags": ["bracket", "mount", "structural", "hardware"],
        "parameters": {
            "arm_length_1": {
                "type": "number",
                "label": "Arm 1 Length",
                "unit": "mm",
                "min": 20,
                "max": 150,
                "step": 5,
            },
            "arm_length_2": {
                "type": "number",
                "label": "Arm 2 Length",
                "unit": "mm",
                "min": 20,
                "max": 150,
                "step": 5,
            },
            "width": {
                "type": "number",
                "label": "Width",
                "unit": "mm",
                "min": 15,
                "max": 60,
                "step": 5,
            },
            "thickness": {
                "type": "number",
                "label": "Material Thickness",
                "unit": "mm",
                "min": 2,
                "max": 8,
                "step": 0.5,
            },
            "hole_diameter": {
                "type": "number",
                "label": "Hole Diameter",
                "unit": "mm",
                "min": 3,
                "max": 10,
                "step": 0.5,
            },
            "holes_per_arm": {
                "type": "number",
                "label": "Holes per Arm",
                "min": 1,
                "max": 4,
                "step": 1,
            },
        },
        "default_values": {
            "arm_length_1": 50,
            "arm_length_2": 50,
            "width": 25,
            "thickness": 3,
            "hole_diameter": 5,
            "holes_per_arm": 2,
        },
        "cadquery_script": "# L-bracket script placeholder",
    },
    {
        "id": uuid4(),
        "name": "Phone/Tablet Stand",
        "slug": "phone-tablet-stand",
        "description": "Adjustable stand for phones and tablets with customizable angle and device width. Includes cable routing option.",
        "category": "brackets",
        "subcategory": "consumer",
        "min_tier": "free",
        "is_featured": True,
        "tags": ["stand", "phone", "tablet", "desk", "3d-printable"],
        "parameters": {
            "device_width": {
                "type": "number",
                "label": "Device Width",
                "unit": "mm",
                "min": 60,
                "max": 250,
                "step": 5,
            },
            "viewing_angle": {
                "type": "number",
                "label": "Viewing Angle",
                "unit": "degrees",
                "min": 30,
                "max": 75,
                "step": 5,
            },
            "cable_slot": {
                "type": "boolean",
                "label": "Include Cable Slot",
            },
            "base_style": {
                "type": "select",
                "label": "Base Style",
                "options": ["solid", "hollow", "weighted"],
            },
        },
        "default_values": {
            "device_width": 80,
            "viewing_angle": 60,
            "cable_slot": True,
            "base_style": "solid",
        },
        "cadquery_script": "# Phone/tablet stand script placeholder",
    },
    
    # =============================================
    # FASTENERS
    # =============================================
    {
        "id": uuid4(),
        "name": "Custom Spacer",
        "slug": "custom-spacer",
        "description": "Cylindrical or hexagonal spacer/standoff with customizable height and thread options.",
        "category": "fasteners",
        "subcategory": "spacers",
        "min_tier": "free",
        "is_featured": False,
        "tags": ["spacer", "standoff", "fastener", "hardware"],
        "parameters": {
            "outer_diameter": {
                "type": "number",
                "label": "Outer Diameter",
                "unit": "mm",
                "min": 4,
                "max": 20,
                "step": 0.5,
            },
            "inner_diameter": {
                "type": "number",
                "label": "Inner Diameter",
                "unit": "mm",
                "min": 2,
                "max": 15,
                "step": 0.5,
            },
            "height": {
                "type": "number",
                "label": "Height",
                "unit": "mm",
                "min": 3,
                "max": 50,
                "step": 1,
            },
            "shape": {
                "type": "select",
                "label": "Shape",
                "options": ["round", "hex"],
            },
            "threaded": {
                "type": "boolean",
                "label": "Include Threads",
            },
        },
        "default_values": {
            "outer_diameter": 8,
            "inner_diameter": 3.2,
            "height": 10,
            "shape": "round",
            "threaded": False,
        },
        "cadquery_script": "# Custom spacer script placeholder",
    },
    
    # =============================================
    # CONTAINERS
    # =============================================
    {
        "id": uuid4(),
        "name": "Stackable Storage Bin",
        "slug": "stackable-storage-bin",
        "description": "Modular stackable storage container with optional dividers and label area.",
        "category": "containers",
        "subcategory": "storage",
        "min_tier": "hobby",
        "is_featured": True,
        "tags": ["storage", "bin", "organizer", "stackable", "3d-printable"],
        "parameters": {
            "length": {
                "type": "number",
                "label": "Length",
                "unit": "mm",
                "min": 50,
                "max": 200,
                "step": 10,
            },
            "width": {
                "type": "number",
                "label": "Width",
                "unit": "mm",
                "min": 50,
                "max": 150,
                "step": 10,
            },
            "height": {
                "type": "number",
                "label": "Height",
                "unit": "mm",
                "min": 30,
                "max": 100,
                "step": 10,
            },
            "dividers": {
                "type": "number",
                "label": "Number of Dividers",
                "min": 0,
                "max": 4,
                "step": 1,
            },
            "label_slot": {
                "type": "boolean",
                "label": "Include Label Slot",
            },
        },
        "default_values": {
            "length": 100,
            "width": 80,
            "height": 50,
            "dividers": 1,
            "label_slot": True,
        },
        "cadquery_script": "# Stackable storage bin script placeholder",
    },
    
    # =============================================
    # CONNECTORS
    # =============================================
    {
        "id": uuid4(),
        "name": "Pipe Connector",
        "slug": "pipe-connector",
        "description": "Parametric pipe connector supporting various configurations: straight, elbow, tee, and cross.",
        "category": "connectors",
        "subcategory": "plumbing",
        "min_tier": "hobby",
        "is_featured": False,
        "tags": ["pipe", "connector", "plumbing", "fitting"],
        "parameters": {
            "pipe_od": {
                "type": "number",
                "label": "Pipe Outer Diameter",
                "unit": "mm",
                "min": 10,
                "max": 50,
                "step": 1,
            },
            "connector_type": {
                "type": "select",
                "label": "Connector Type",
                "options": ["straight", "elbow_90", "elbow_45", "tee", "cross"],
            },
            "wall_thickness": {
                "type": "number",
                "label": "Wall Thickness",
                "unit": "mm",
                "min": 2,
                "max": 5,
                "step": 0.5,
            },
            "socket_depth": {
                "type": "number",
                "label": "Socket Depth",
                "unit": "mm",
                "min": 10,
                "max": 30,
                "step": 1,
            },
        },
        "default_values": {
            "pipe_od": 25,
            "connector_type": "elbow_90",
            "wall_thickness": 3,
            "socket_depth": 15,
        },
        "cadquery_script": "# Pipe connector script placeholder",
    },
]


async def seed_templates(db_session) -> int:
    """
    Seed templates into the database.
    
    Args:
        db_session: AsyncSession database session
        
    Returns:
        Number of templates created
    """
    from app.models import Template
    from sqlalchemy import select
    
    created_count = 0
    
    for template_data in TEMPLATE_SEEDS:
        # Check if template already exists by slug
        result = await db_session.execute(
            select(Template).where(Template.slug == template_data["slug"])
        )
        existing = result.scalar_one_or_none()
        
        if existing:
            print(f"Template '{template_data['slug']}' already exists, skipping...")
            continue
        
        template = Template(
            id=template_data.get("id"),
            name=template_data["name"],
            slug=template_data["slug"],
            description=template_data.get("description"),
            category=template_data["category"],
            subcategory=template_data.get("subcategory"),
            parameters=template_data["parameters"],
            default_values=template_data.get("default_values", {}),
            cadquery_script=template_data["cadquery_script"],
            tags=template_data.get("tags", []),
            min_tier=template_data.get("min_tier", "free"),
            is_featured=template_data.get("is_featured", False),
            is_active=True,
        )
        
        db_session.add(template)
        created_count += 1
        print(f"Created template: {template.name}")
    
    await db_session.commit()
    return created_count


async def main():
    """Run template seeding."""
    from app.core.database import async_session_maker
    
    async with async_session_maker() as session:
        count = await seed_templates(session)
        print(f"\nSeeded {count} templates successfully!")


if __name__ == "__main__":
    asyncio.run(main())
