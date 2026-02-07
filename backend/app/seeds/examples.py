"""
Seed data for example projects.

This script populates the database with example projects
that users can explore during onboarding or copy to their library.

Usage:
    python -m app.seeds.examples

Or via Makefile:
    make seed-examples
"""

import asyncio
import logging
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session_maker
from app.models import Design, Project, User

logger = logging.getLogger(__name__)


# =============================================================================
# Example Projects Data
# =============================================================================

EXAMPLE_PROJECTS = [
    {
        "id": "11111111-1111-1111-1111-111111111111",
        "name": "Raspberry Pi 4 Enclosure",
        "description": (
            "A custom enclosure designed for the Raspberry Pi 4. "
            "Features ventilation slots, access to all ports, and mounting options."
        ),
        "is_example": True,
        "tags": ["raspberry-pi", "enclosure", "electronics", "3d-printable"],
        "designs": [
            {
                "name": "Main Enclosure Body",
                "description": "The main body of the Raspberry Pi enclosure with ventilation.",
                "prompt": "Create a Raspberry Pi 4 enclosure body with ventilation slots on top, "
                "access holes for USB, Ethernet, HDMI, and power ports on the sides, "
                "and mounting holes for M2.5 screws.",
                "parameters": {
                    "length": 90,
                    "width": 60,
                    "height": 25,
                    "wall_thickness": 2,
                    "ventilation": True,
                },
            },
            {
                "name": "Enclosure Lid",
                "description": "Snap-fit lid for the Raspberry Pi enclosure.",
                "prompt": "Create a snap-fit lid for a Raspberry Pi 4 enclosure with logo embossing area.",
                "parameters": {
                    "length": 90,
                    "width": 60,
                    "thickness": 2,
                    "snap_fit": True,
                },
            },
        ],
    },
    {
        "id": "22222222-2222-2222-2222-222222222222",
        "name": "Desk Cable Organizer",
        "description": (
            "A modular cable management system for your desk. "
            "Includes cable clips, cord channels, and a hub mount."
        ),
        "is_example": True,
        "tags": ["desk-accessories", "cable-management", "organization", "modular"],
        "designs": [
            {
                "name": "Cable Clip - Small",
                "description": "Adhesive-backed cable clip for thin cables (up to 3mm diameter).",
                "prompt": "Create an adhesive-backed cable clip for cables up to 3mm diameter "
                "with a snap-in mechanism.",
                "parameters": {
                    "cable_diameter": 3,
                    "clip_count": 1,
                    "mount_type": "adhesive",
                },
            },
            {
                "name": "Cable Clip - Multi",
                "description": "Multi-cable clip holding up to 5 cables.",
                "prompt": "Create a multi-cable organizer clip that can hold 5 cables "
                "with adjustable dividers.",
                "parameters": {
                    "cable_count": 5,
                    "cable_diameter": 5,
                    "mount_type": "screw",
                },
            },
            {
                "name": "Under-Desk Cable Tray",
                "description": "Cable tray that mounts under the desk.",
                "prompt": "Create an under-desk cable tray with mounting brackets "
                "and cable pass-through holes.",
                "parameters": {
                    "length": 400,
                    "width": 100,
                    "depth": 60,
                },
            },
        ],
    },
    {
        "id": "33333333-3333-3333-3333-333333333333",
        "name": "Custom Phone Stand",
        "description": (
            "An adjustable phone stand with multiple viewing angles. "
            "Works with phones of various sizes and cases."
        ),
        "is_example": True,
        "tags": ["phone-stand", "desk-accessories", "adjustable", "universal"],
        "designs": [
            {
                "name": "Phone Stand Base",
                "description": "Weighted base with anti-slip pad.",
                "prompt": "Create a weighted phone stand base with anti-slip rubber pad area "
                "and hinge mount point.",
                "parameters": {
                    "base_width": 80,
                    "base_depth": 100,
                    "base_height": 10,
                },
            },
            {
                "name": "Adjustable Arm",
                "description": "Articulating arm with angle adjustment.",
                "prompt": "Create an adjustable phone stand arm with multiple angle settings "
                "from 15 to 75 degrees.",
                "parameters": {
                    "arm_length": 120,
                    "angle_min": 15,
                    "angle_max": 75,
                    "angle_steps": 4,
                },
            },
            {
                "name": "Phone Cradle",
                "description": "Universal phone cradle with cable routing.",
                "prompt": "Create a universal phone cradle that fits phones up to 80mm wide "
                "with a cutout for charging cables.",
                "parameters": {
                    "max_phone_width": 80,
                    "cradle_depth": 25,
                    "cable_routing": True,
                },
            },
        ],
    },
    {
        "id": "44444444-4444-4444-4444-444444444444",
        "name": "Sensor Mounting Brackets",
        "description": (
            "A collection of mounting brackets for common sensors used in IoT "
            "and automation projects."
        ),
        "is_example": True,
        "tags": ["sensors", "iot", "mounting", "brackets", "automation"],
        "designs": [
            {
                "name": "PIR Sensor Mount",
                "description": "Corner-mount bracket for PIR motion sensors.",
                "prompt": "Create a corner-mount bracket for a PIR motion sensor with "
                "adjustable tilt angle.",
                "parameters": {
                    "sensor_diameter": 25,
                    "tilt_range": 45,
                    "mount_type": "corner",
                },
            },
            {
                "name": "Temperature Sensor Housing",
                "description": "Ventilated housing for temperature/humidity sensors.",
                "prompt": "Create a ventilated housing for a DHT22 temperature sensor "
                "with wall mount option.",
                "parameters": {
                    "sensor_type": "DHT22",
                    "ventilation": True,
                    "mount_type": "wall",
                },
            },
            {
                "name": "Ultrasonic Sensor Bracket",
                "description": "Adjustable bracket for HC-SR04 ultrasonic sensors.",
                "prompt": "Create an adjustable mounting bracket for HC-SR04 ultrasonic "
                "sensor with pan and tilt adjustment.",
                "parameters": {
                    "sensor_type": "HC-SR04",
                    "pan_range": 180,
                    "tilt_range": 90,
                },
            },
        ],
    },
]


# =============================================================================
# System User for Example Projects
# =============================================================================

SYSTEM_USER_ID = UUID("00000000-0000-0000-0000-000000000001")
SYSTEM_USER = {
    "id": SYSTEM_USER_ID,
    "email": "system@aipartdesigner.com",
    "password_hash": "not-a-real-password-hash",
    "display_name": "AI Part Designer",
    "role": "admin",
    "status": "active",
}


# =============================================================================
# Seeding Functions
# =============================================================================


async def seed_system_user(session: AsyncSession) -> User:
    """Create or get the system user for example projects."""
    result = await session.execute(select(User).where(User.id == SYSTEM_USER_ID))
    user = result.scalar_one_or_none()

    if not user:
        user = User(**SYSTEM_USER)
        session.add(user)
        await session.flush()
        logger.info(f"Created system user: {user.email}")
    else:
        logger.info(f"System user already exists: {user.email}")

    return user


async def seed_example_projects(session: AsyncSession, user: User) -> int:
    """Seed example projects."""
    count = 0

    for project_data in EXAMPLE_PROJECTS:
        project_id = UUID(str(project_data["id"]))

        # Check if project already exists
        existing = await session.execute(select(Project).where(Project.id == project_id))
        if existing.scalar_one_or_none():
            logger.info(f"Example project already exists: {project_data['name']}")
            continue

        # Create project
        project = Project(
            id=project_id,
            user_id=user.id,
            name=project_data["name"],
            description=project_data["description"],
            status="active",
        )
        session.add(project)
        await session.flush()

        # Create designs for the project
        designs_list: list[dict[str, Any]] = project_data.get("designs", [])  # type: ignore[assignment]
        for design_data in designs_list:
            design = Design(
                project_id=project.id,
                user_id=user.id,
                name=design_data["name"],
                description=design_data.get("description"),
                source_type="template",
                status="ready",
                is_public=True,
                tags=project_data.get("tags", []),
                extra_data={
                    "is_example": True,
                    "ai_prompt": design_data.get("prompt"),
                    "parameters": design_data.get("parameters", {}),
                },
            )
            session.add(design)

        count += 1
        logger.info(f"Created example project: {project_data['name']}")

    return count


async def copy_example_project(
    session: AsyncSession,
    example_project_id: UUID,
    user_id: UUID,
) -> Project | None:
    """
    Copy an example project to a user's library.

    Args:
        session: Database session
        example_project_id: ID of the example project to copy
        user_id: ID of the user to copy to

    Returns:
        The new project copy, or None if example not found
    """
    # Get the example project
    result = await session.execute(select(Project).where(Project.id == example_project_id))
    example = result.scalar_one_or_none()

    if not example:
        return None

    # Create copy
    new_project = Project(
        user_id=user_id,
        name=f"{example.name} (Copy)",
        description=example.description,
        status="active",
    )
    session.add(new_project)
    await session.flush()

    # Copy designs
    designs_result = await session.execute(
        select(Design).where(Design.project_id == example_project_id)
    )
    for design in designs_result.scalars():
        new_design = Design(
            project_id=new_project.id,
            user_id=new_project.user_id,
            name=design.name,
            description=design.description,
            source_type=design.source_type,
            status="draft",
            is_public=False,
            tags=design.tags.copy() if design.tags else [],
            extra_data={
                "copied_from": str(design.id),
                "copied_at": datetime.now(tz=UTC).isoformat(),
                **design.extra_data,
            },
        )
        session.add(new_design)

    await session.commit()
    return new_project


async def run_seeder() -> None:
    """Run the example projects seeder."""
    async with async_session_maker() as session:
        user = await seed_system_user(session)
        count = await seed_example_projects(session, user)
        await session.commit()
        logger.info(f"Seeded {count} example projects")


# =============================================================================
# Main Entry Point
# =============================================================================

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run_seeder())
