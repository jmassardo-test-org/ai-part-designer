"""
Seed data for marketplace and file components.

This script populates the database with:
- Sample design lists for marketplace organization
- Sample saved designs for popularity metrics
- Sample file records for uploaded CAD files

Usage:
    python -m app.seeds.marketplace

Or via Makefile:
    make db-seed-marketplace
"""

import asyncio
import logging
from datetime import datetime, timedelta
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session_maker
from app.models.design import Design
from app.models.file import File
from app.models.marketplace import DesignList, DesignListItem, DesignSave
from app.models.user import User

logger = logging.getLogger(__name__)


# =============================================================================
# Seed Data Definitions
# =============================================================================

# Well-known UUIDs for seeding (matching users.py and starters.py)
VENDOR_USER_ID = UUID("00000000-0000-0000-0000-000000000001")

# Sample design lists that will be created for users
SAMPLE_DESIGN_LISTS = [
    {
        "name": "Favorites",
        "description": "My favorite designs from the marketplace",
        "icon": "heart",
        "color": "#ef4444",
        "is_public": False,
    },
    {
        "name": "Electronics Projects",
        "description": "Enclosures and mounts for electronics",
        "icon": "cpu",
        "color": "#3b82f6",
        "is_public": True,
    },
    {
        "name": "To Print Later",
        "description": "Designs I want to 3D print when I have time",
        "icon": "printer",
        "color": "#10b981",
        "is_public": False,
    },
    {
        "name": "Inspiration",
        "description": "Cool designs for reference",
        "icon": "lightbulb",
        "color": "#f59e0b",
        "is_public": False,
    },
]

# File types and formats for sample files
SAMPLE_FILES = [
    {
        "filename": "raspberry_pi_case_v1.step",
        "original_filename": "Raspberry Pi Case v1.STEP",
        "mime_type": "application/step",
        "size_bytes": 245760,  # ~240 KB
        "file_type": "cad",
        "cad_format": "step",
        "status": "ready",
        "geometry_info": {
            "bounding_box": {"x": 95, "y": 66, "z": 30},
            "volume": 85000,
            "surface_area": 23000,
            "unit": "mm",
        },
    },
    {
        "filename": "arduino_enclosure.stl",
        "original_filename": "Arduino Enclosure.stl",
        "mime_type": "model/stl",
        "size_bytes": 524288,  # ~512 KB
        "file_type": "cad",
        "cad_format": "stl",
        "status": "ready",
        "geometry_info": {
            "bounding_box": {"x": 80, "y": 60, "z": 30},
            "volume": 72000,
            "surface_area": 19200,
            "unit": "mm",
            "triangles": 12480,
        },
    },
    {
        "filename": "sensor_housing.step",
        "original_filename": "Sensor Housing.STEP",
        "mime_type": "application/step",
        "size_bytes": 163840,  # ~160 KB
        "file_type": "cad",
        "cad_format": "step",
        "status": "ready",
        "geometry_info": {
            "bounding_box": {"x": 60, "y": 40, "z": 30},
            "volume": 32000,
            "surface_area": 10800,
            "unit": "mm",
        },
    },
    {
        "filename": "project_render.png",
        "original_filename": "Project Render.png",
        "mime_type": "image/png",
        "size_bytes": 2097152,  # ~2 MB
        "file_type": "image",
        "cad_format": None,
        "status": "ready",
        "geometry_info": None,
    },
]


# =============================================================================
# Seeding Functions
# =============================================================================


async def seed_design_lists_for_user(
    db: AsyncSession,
    user: User,
    public_designs: list[Design],
) -> tuple[int, int]:
    """Create sample design lists for a user.
    
    Args:
        db: Async database session.
        user: The user to create lists for.
        public_designs: List of public designs to potentially add to lists.
        
    Returns:
        Tuple of (lists_created, items_created).
    """
    lists_created = 0
    items_created = 0
    
    for idx, list_data in enumerate(SAMPLE_DESIGN_LISTS):
        # Check if list already exists for this user
        existing = await db.execute(
            select(DesignList).where(
                DesignList.user_id == user.id,
                DesignList.name == list_data["name"],
            )
        )
        if existing.scalar_one_or_none():
            continue
        
        # Create the design list
        design_list = DesignList(
            id=uuid4(),
            user_id=user.id,
            name=list_data["name"],
            description=list_data["description"],
            icon=list_data["icon"],
            color=list_data["color"],
            is_public=list_data["is_public"],
            position=idx,
        )
        db.add(design_list)
        await db.flush()
        lists_created += 1
        
        # Add some designs to Favorites list
        if list_data["name"] == "Favorites" and public_designs:
            # Add up to 3 random designs
            designs_to_add = public_designs[:min(3, len(public_designs))]
            for pos, design in enumerate(designs_to_add):
                item = DesignListItem(
                    id=uuid4(),
                    list_id=design_list.id,
                    design_id=design.id,
                    position=pos,
                )
                db.add(item)
                items_created += 1
        
        # Add some to Electronics Projects list
        elif list_data["name"] == "Electronics Projects" and public_designs:
            # Filter for electronics-related designs
            electronics_designs = [
                d for d in public_designs 
                if d.category and "raspberry" in d.category.lower()
                or d.category and "arduino" in d.category.lower()
                or d.category and "esp" in d.category.lower()
            ][:2]
            for pos, design in enumerate(electronics_designs):
                item = DesignListItem(
                    id=uuid4(),
                    list_id=design_list.id,
                    design_id=design.id,
                    position=pos,
                    note="Great for prototyping" if pos == 0 else None,
                )
                db.add(item)
                items_created += 1
    
    return lists_created, items_created


async def seed_design_saves(
    db: AsyncSession,
    users: list[User],
    public_designs: list[Design],
) -> int:
    """Create sample design saves for popularity metrics.
    
    Args:
        db: Async database session.
        users: List of users to create saves for.
        public_designs: List of public designs that can be saved.
        
    Returns:
        Number of saves created.
    """
    saves_created = 0
    
    for design in public_designs[:5]:  # Only process first 5 designs
        # Simulate saves from multiple users
        users_to_save = users[:min(3, len(users))]
        
        for user in users_to_save:
            # Don't let users save their own designs (check via project)
            if hasattr(design, 'project') and design.project and design.project.user_id == user.id:
                continue
            
            # Check if save already exists
            existing = await db.execute(
                select(DesignSave).where(
                    DesignSave.user_id == user.id,
                    DesignSave.design_id == design.id,
                )
            )
            if existing.scalar_one_or_none():
                continue
            
            save = DesignSave(
                id=uuid4(),
                user_id=user.id,
                design_id=design.id,
            )
            db.add(save)
            
            # Increment the design's save count
            design.save_count = (design.save_count or 0) + 1
            
            saves_created += 1
    
    return saves_created


async def seed_files_for_user(
    db: AsyncSession,
    user: User,
) -> int:
    """Create sample file records for a user.
    
    Args:
        db: Async database session.
        user: The user to create files for.
        
    Returns:
        Number of files created.
    """
    files_created = 0
    
    for file_data in SAMPLE_FILES:
        # Check if file already exists for this user
        existing = await db.execute(
            select(File).where(
                File.user_id == user.id,
                File.filename == file_data["filename"],
            )
        )
        if existing.scalar_one_or_none():
            continue
        
        # Create a unique storage path
        storage_path = f"users/{user.id}/uploads/{file_data['filename']}"
        
        file = File(
            id=uuid4(),
            user_id=user.id,
            filename=file_data["filename"],
            original_filename=file_data["original_filename"],
            mime_type=file_data["mime_type"],
            size_bytes=file_data["size_bytes"],
            storage_bucket="uploads",
            storage_path=storage_path,
            file_type=file_data["file_type"],
            cad_format=file_data["cad_format"],
            status=file_data["status"],
            geometry_info=file_data["geometry_info"],
            checksum_sha256="seeded_" + file_data["filename"],  # Fake checksum
            scan_status="clean",
        )
        db.add(file)
        files_created += 1
    
    return files_created


async def seed_marketplace(db: AsyncSession) -> dict[str, int]:
    """Seed marketplace data including lists, saves, and files.
    
    Args:
        db: Async database session.
        
    Returns:
        Dictionary with counts of created records.
    """
    results = {
        "lists_created": 0,
        "items_created": 0,
        "saves_created": 0,
        "files_created": 0,
    }
    
    # Get existing users (excluding vendor/system user)
    users_result = await db.execute(
        select(User).where(
            User.status == "active",
            User.id != VENDOR_USER_ID,
        ).limit(10)
    )
    users = list(users_result.scalars())
    
    if not users:
        logger.warning("No users found to seed marketplace data for")
        return results
    
    # Get public designs for saving/listing
    designs_result = await db.execute(
        select(Design).where(
            Design.is_public == True,
            Design.deleted_at == None,
        ).limit(10)
    )
    public_designs = list(designs_result.scalars())
    
    logger.info(f"Found {len(users)} users and {len(public_designs)} public designs")
    
    # Seed design lists for first 3 users
    for user in users[:3]:
        lists_count, items_count = await seed_design_lists_for_user(
            db, user, public_designs
        )
        results["lists_created"] += lists_count
        results["items_created"] += items_count
        logger.debug(f"Created {lists_count} lists with {items_count} items for {user.email}")
    
    # Seed design saves
    if public_designs:
        results["saves_created"] = await seed_design_saves(db, users, public_designs)
        logger.debug(f"Created {results['saves_created']} design saves")
    
    # Seed files for first 2 users
    for user in users[:2]:
        files_count = await seed_files_for_user(db, user)
        results["files_created"] += files_count
        logger.debug(f"Created {files_count} files for {user.email}")
    
    await db.commit()
    return results


async def main() -> None:
    """Run marketplace seeding."""
    logging.basicConfig(level=logging.INFO)
    logger.info("Seeding marketplace data...")
    
    async with async_session_maker() as db:
        results = await seed_marketplace(db)
        logger.info(
            f"Marketplace seeding complete: "
            f"{results['lists_created']} lists, "
            f"{results['items_created']} list items, "
            f"{results['saves_created']} saves, "
            f"{results['files_created']} files"
        )


if __name__ == "__main__":
    asyncio.run(main())
