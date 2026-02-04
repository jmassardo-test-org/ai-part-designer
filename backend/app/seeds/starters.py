"""
Seed data for starter designs.

This script populates the database with starter designs
that users can browse and remix from the marketplace.

Usage:
    python -m app.seeds.starters

Or via Makefile:
    make db-seed-starters
"""

import asyncio
import logging
from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session_maker
from app.models.design import Design
from app.models.project import Project
from app.models.user import User

logger = logging.getLogger(__name__)


# =============================================================================
# Starter Design Definitions
# =============================================================================

# Well-known UUID for system/vendor account
VENDOR_USER_ID = UUID("00000000-0000-0000-0000-000000000001")
STARTERS_PROJECT_ID = UUID("00000000-0000-0000-0000-000000000100")

STARTER_DESIGNS = [
    # Raspberry Pi enclosures
    {
        "id": UUID("10000000-0000-0000-0000-000000000001"),
        "name": "Raspberry Pi 5 Basic Case",
        "description": (
            "A minimal enclosure for the Raspberry Pi 5. Features ventilation slots, "
            "access to all ports (USB, Ethernet, HDMI, USB-C power), and GPIO header access."
        ),
        "category": "raspberry-pi",
        "tags": ["raspberry-pi-5", "enclosure", "ventilation", "beginner"],
        "is_starter": True,
        "is_public": True,
        "enclosure_spec": {
            "exterior": {
                "width": {"value": 95, "unit": "mm"},
                "depth": {"value": 66, "unit": "mm"},
                "height": {"value": 30, "unit": "mm"},
            },
            "walls": {"thickness": {"value": 2.5, "unit": "mm"}},
            "lid": {"type": "snap_fit"},
            "components": [
                {
                    "ref": {"id": "raspberry-pi-5"},
                    "position": {"x": 0, "y": 0, "z": 5},
                }
            ],
            "features": [
                {"type": "port_cutout", "wall": "back", "port_name": "usb-a"},
                {"type": "port_cutout", "wall": "back", "port_name": "ethernet"},
                {"type": "port_cutout", "wall": "left", "port_name": "hdmi"},
                {"type": "port_cutout", "wall": "left", "port_name": "usb-c-power"},
                {"type": "port_cutout", "wall": "right", "port_name": "sd-card"},
            ],
            "ventilation": {
                "enabled": True,
                "pattern": "grid",
                "location": "top",
            },
        },
    },
    {
        "id": UUID("10000000-0000-0000-0000-000000000002"),
        "name": "Raspberry Pi 4 Desktop Case",
        "description": (
            "A desktop-style enclosure for Raspberry Pi 4 with integrated fan mount "
            "and room for a small HAT. Designed for continuous operation."
        ),
        "category": "raspberry-pi",
        "tags": ["raspberry-pi-4", "enclosure", "fan", "desktop", "hat"],
        "is_starter": True,
        "is_public": True,
        "enclosure_spec": {
            "exterior": {
                "width": {"value": 100, "unit": "mm"},
                "depth": {"value": 70, "unit": "mm"},
                "height": {"value": 45, "unit": "mm"},
            },
            "walls": {"thickness": {"value": 2.5, "unit": "mm"}},
            "lid": {"type": "screw"},
            "components": [
                {
                    "ref": {"id": "raspberry-pi-4"},
                    "position": {"x": 0, "y": 0, "z": 5},
                }
            ],
            "features": [
                {"type": "port_cutout", "wall": "back", "port_name": "usb-a"},
                {"type": "port_cutout", "wall": "back", "port_name": "ethernet"},
                {"type": "port_cutout", "wall": "left", "port_name": "hdmi"},
                {"type": "fan_mount", "wall": "top", "diameter": 30},
            ],
            "ventilation": {"enabled": True, "pattern": "slots", "location": "sides"},
        },
    },
    # Arduino enclosures
    {
        "id": UUID("10000000-0000-0000-0000-000000000003"),
        "name": "Arduino Uno Project Box",
        "description": (
            "A compact enclosure for Arduino Uno with USB and power jack access. "
            "Includes a prototyping area for small circuits."
        ),
        "category": "arduino",
        "tags": ["arduino-uno", "enclosure", "prototyping", "beginner"],
        "is_starter": True,
        "is_public": True,
        "enclosure_spec": {
            "exterior": {
                "width": {"value": 80, "unit": "mm"},
                "depth": {"value": 60, "unit": "mm"},
                "height": {"value": 30, "unit": "mm"},
            },
            "walls": {"thickness": {"value": 2, "unit": "mm"}},
            "lid": {"type": "snap_fit"},
            "components": [
                {
                    "ref": {"id": "arduino-uno"},
                    "position": {"x": 0, "y": 0, "z": 3},
                }
            ],
            "features": [
                {"type": "port_cutout", "wall": "back", "port_name": "usb-b"},
                {"type": "port_cutout", "wall": "back", "port_name": "barrel-jack"},
            ],
        },
    },
    {
        "id": UUID("10000000-0000-0000-0000-000000000004"),
        "name": "Arduino Nano Sensor Hub",
        "description": (
            "A small enclosure for Arduino Nano with mounting for common sensors. "
            "Perfect for IoT and environmental monitoring projects."
        ),
        "category": "arduino",
        "tags": ["arduino-nano", "enclosure", "sensors", "iot"],
        "is_starter": True,
        "is_public": True,
        "enclosure_spec": {
            "exterior": {
                "width": {"value": 55, "unit": "mm"},
                "depth": {"value": 40, "unit": "mm"},
                "height": {"value": 25, "unit": "mm"},
            },
            "walls": {"thickness": {"value": 2, "unit": "mm"}},
            "lid": {"type": "press_fit"},
            "components": [
                {
                    "ref": {"id": "arduino-nano"},
                    "position": {"x": 0, "y": 0, "z": 3},
                }
            ],
            "features": [
                {"type": "port_cutout", "wall": "front", "port_name": "mini-usb"},
                {"type": "vent_pattern", "wall": "top", "pattern": "grid"},
            ],
        },
    },
    # ESP32 enclosures
    {
        "id": UUID("10000000-0000-0000-0000-000000000005"),
        "name": "ESP32 WiFi Controller Case",
        "description": (
            "A compact case for ESP32 DevKit with antenna clearance and "
            "USB-C access. Ideal for home automation controllers."
        ),
        "category": "esp32",
        "tags": ["esp32", "enclosure", "wifi", "home-automation", "iot"],
        "is_starter": True,
        "is_public": True,
        "enclosure_spec": {
            "exterior": {
                "width": {"value": 60, "unit": "mm"},
                "depth": {"value": 35, "unit": "mm"},
                "height": {"value": 20, "unit": "mm"},
            },
            "walls": {"thickness": {"value": 1.5, "unit": "mm"}},
            "lid": {"type": "snap_fit"},
            "components": [
                {
                    "ref": {"id": "esp32-devkit"},
                    "position": {"x": 0, "y": 0, "z": 2},
                }
            ],
            "features": [
                {"type": "port_cutout", "wall": "front", "port_name": "usb-c"},
            ],
        },
    },
    # Display cases
    {
        "id": UUID("10000000-0000-0000-0000-000000000006"),
        "name": "3.5\" LCD Display Stand",
        "description": (
            "A display stand for 3.5 inch LCD screens with adjustable viewing angle. "
            "Compatible with Raspberry Pi displays and similar."
        ),
        "category": "display",
        "tags": ["display", "lcd", "stand", "raspberry-pi"],
        "is_starter": True,
        "is_public": True,
        "enclosure_spec": {
            "exterior": {
                "width": {"value": 95, "unit": "mm"},
                "depth": {"value": 65, "unit": "mm"},
                "height": {"value": 25, "unit": "mm"},
            },
            "walls": {"thickness": {"value": 2, "unit": "mm"}},
            "lid": {"type": "none"},
            "features": [
                {
                    "type": "display_cutout",
                    "wall": "top",
                    "width": 76,
                    "height": 64,
                    "display_type": "lcd",
                },
            ],
        },
    },
    # Power supply enclosures
    {
        "id": UUID("10000000-0000-0000-0000-000000000007"),
        "name": "5V Power Supply Enclosure",
        "description": (
            "A safety enclosure for 5V power supplies with proper ventilation "
            "and cable management. Includes mounting flanges."
        ),
        "category": "power-supply",
        "tags": ["power-supply", "enclosure", "5v", "safety"],
        "is_starter": True,
        "is_public": True,
        "enclosure_spec": {
            "exterior": {
                "width": {"value": 90, "unit": "mm"},
                "depth": {"value": 55, "unit": "mm"},
                "height": {"value": 35, "unit": "mm"},
            },
            "walls": {"thickness": {"value": 2.5, "unit": "mm"}},
            "lid": {"type": "screw"},
            "features": [
                {"type": "cable_grommet", "wall": "back", "diameter": 8},
                {"type": "cable_grommet", "wall": "front", "diameter": 5},
                {"type": "mounting_flange", "corners": True},
            ],
            "ventilation": {"enabled": True, "pattern": "slots", "location": "all"},
        },
    },
    # Sensor housings
    {
        "id": UUID("10000000-0000-0000-0000-000000000008"),
        "name": "Environmental Sensor Housing",
        "description": (
            "A weatherproof housing for environmental sensors (temperature, humidity, etc). "
            "Features ventilation that protects against water ingress."
        ),
        "category": "sensors",
        "tags": ["sensor", "enclosure", "weatherproof", "iot", "outdoor"],
        "is_starter": True,
        "is_public": True,
        "enclosure_spec": {
            "exterior": {
                "width": {"value": 60, "unit": "mm"},
                "depth": {"value": 40, "unit": "mm"},
                "height": {"value": 30, "unit": "mm"},
            },
            "walls": {"thickness": {"value": 2, "unit": "mm"}},
            "lid": {"type": "screw"},
            "features": [
                {"type": "louvered_vent", "wall": "bottom"},
                {"type": "cable_grommet", "wall": "bottom", "diameter": 5},
            ],
            "mounting": {"type": "wall", "keyhole_slots": True},
        },
    },
]


async def ensure_vendor_user(db: AsyncSession) -> User:
    """Ensure the vendor/system user exists for starter designs.
    
    Args:
        db: Async database session.
        
    Returns:
        The vendor user.
    """
    existing = await db.execute(
        select(User).where(User.id == VENDOR_USER_ID)
    )
    user = existing.scalar_one_or_none()
    
    if not user:
        user = User(
            id=VENDOR_USER_ID,
            email="vendor@assemblematic.ai",
            display_name="AssemblematicAI",
            role="system",
            status="active",
            password_hash="!",  # Cannot login - invalid hash
            email_verified_at=datetime.utcnow(),
        )
        db.add(user)
        await db.flush()
        logger.info("Created vendor user")
    
    return user


async def ensure_starters_project(db: AsyncSession, user: User) -> Project:
    """Ensure the starters project exists.
    
    Args:
        db: Async database session.
        user: The vendor user.
        
    Returns:
        The starters project.
    """
    existing = await db.execute(
        select(Project).where(Project.id == STARTERS_PROJECT_ID)
    )
    project = existing.scalar_one_or_none()
    
    if not project:
        project = Project(
            id=STARTERS_PROJECT_ID,
            name="Starter Designs",
            description="Official starter designs for the AssemblematicAI marketplace",
            user_id=user.id,
            status="active",
        )
        db.add(project)
        await db.flush()
        logger.info("Created starters project")
    
    return project


async def seed_starters(db: AsyncSession) -> tuple[int, int]:
    """Seed starter designs into the database.
    
    Args:
        db: Async database session.
        
    Returns:
        Tuple of (created_count, updated_count).
    """
    # Ensure vendor user and project exist
    vendor_user = await ensure_vendor_user(db)
    starters_project = await ensure_starters_project(db, vendor_user)
    
    created = 0
    updated = 0
    
    for starter_data in STARTER_DESIGNS:
        # Check if design already exists
        existing = await db.execute(
            select(Design).where(Design.id == starter_data["id"])
        )
        design = existing.scalar_one_or_none()
        
        if design:
            # Update existing design
            design.name = starter_data["name"]
            design.description = starter_data["description"]
            design.category = starter_data["category"]
            design.tags = starter_data["tags"]
            design.is_public = starter_data["is_public"]
            design.is_starter = starter_data["is_starter"]
            design.enclosure_spec = starter_data["enclosure_spec"]
            design.user_id = vendor_user.id
            updated += 1
            logger.debug(f"Updated starter: {starter_data['name']}")
        else:
            # Create new design
            design = Design(
                id=starter_data["id"],
                name=starter_data["name"],
                description=starter_data["description"],
                project_id=starters_project.id,
                user_id=vendor_user.id,
                source_type="starter",
                status="ready",
                category=starter_data["category"],
                tags=starter_data["tags"],
                is_public=True,
                is_starter=starter_data["is_starter"],
                enclosure_spec=starter_data["enclosure_spec"],
            )
            db.add(design)
            created += 1
            logger.debug(f"Created starter: {starter_data['name']}")
    
    await db.commit()
    return created, updated


async def main() -> None:
    """Run starter seeding."""
    logging.basicConfig(level=logging.INFO)
    logger.info("Seeding starter designs...")
    
    async with async_session_maker() as db:
        created, updated = await seed_starters(db)
        logger.info(f"Starter seeding complete: {created} created, {updated} updated")
        logger.info(f"Total starters defined: {len(STARTER_DESIGNS)}")


if __name__ == "__main__":
    asyncio.run(main())
