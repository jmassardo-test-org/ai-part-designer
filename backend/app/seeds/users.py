"""
Seed data for users and sample content.

Creates development users across all tiers with sample projects and designs.

Usage:
    python -m app.seeds.users

Or via Makefile:
    make seed-users
"""

import asyncio
import logging
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session_maker
from app.core.security import hash_password
from app.models.design import Design, DesignVersion
from app.models.project import Project
from app.models.user import Subscription, User, UserSettings

logger = logging.getLogger(__name__)

# =============================================================================
# Seed Data Definitions
# =============================================================================

# Platform admin
PLATFORM_ADMIN = {
    "email": "admin@assemblematicai.com",
    "password": "admin123!",
    "display_name": "Platform Admin",
    "role": "admin",
    "tier": "enterprise",
}

# Free tier users
FREE_USERS = [
    {
        "email": "demo@example.com",
        "password": "demo123",
        "display_name": "Demo User",
    },
    {
        "email": "alex.maker@gmail.com",
        "password": "maker123",
        "display_name": "Alex Maker",
    },
    {
        "email": "sam.hobbyist@outlook.com",
        "password": "hobby123",
        "display_name": "Sam Hobbyist",
    },
]

# Pro tier users
PRO_USERS = [
    {
        "email": "pro@example.com",
        "password": "pro123",
        "display_name": "Pro User",
    },
    {
        "email": "jordan.engineer@techcorp.com",
        "password": "engineer123",
        "display_name": "Jordan Engineer",
    },
    {
        "email": "taylor.designer@studio.io",
        "password": "design123",
        "display_name": "Taylor Designer",
    },
]

# Enterprise organizations with users
ENTERPRISE_ORGS = [
    {
        "org_name": "Acme Robotics",
        "domain": "acmerobotics.com",
        "admin": {
            "email": "admin@acmerobotics.com",
            "password": "acmeadmin123",
            "display_name": "Acme Admin",
            "role": "admin",  # Org admin
        },
        "users": [
            {
                "email": "engineer1@acmerobotics.com",
                "password": "acme123",
                "display_name": "Morgan Chen",
            },
            {
                "email": "engineer2@acmerobotics.com",
                "password": "acme123",
                "display_name": "Casey Williams",
            },
            {
                "email": "designer@acmerobotics.com",
                "password": "acme123",
                "display_name": "Riley Johnson",
            },
            {
                "email": "intern@acmerobotics.com",
                "password": "acme123",
                "display_name": "Jamie Park",
            },
        ],
    },
    {
        "org_name": "IoT Solutions Inc",
        "domain": "iotsolutions.io",
        "admin": {
            "email": "admin@iotsolutions.io",
            "password": "iotadmin123",
            "display_name": "IoT Admin",
            "role": "admin",
        },
        "users": [
            {
                "email": "hardware@iotsolutions.io",
                "password": "iot123",
                "display_name": "Avery Martinez",
            },
            {
                "email": "firmware@iotsolutions.io",
                "password": "iot123",
                "display_name": "Quinn Thompson",
            },
            {
                "email": "product@iotsolutions.io",
                "password": "iot123",
                "display_name": "Blake Anderson",
            },
        ],
    },
]

# Sample project templates per user type
SAMPLE_PROJECTS = {
    "free": [
        {
            "name": "My First Enclosure",
            "description": "Learning how to create enclosures with AssemblematicAI",
            "designs": [
                {
                    "name": "Simple Box",
                    "description": "A basic box enclosure for testing",
                    "source_type": "template",
                    "status": "ready",
                },
            ],
        },
    ],
    "pro": [
        {
            "name": "Raspberry Pi Projects",
            "description": "Custom enclosures for Raspberry Pi builds",
            "designs": [
                {
                    "name": "Pi 5 Desktop Case",
                    "description": "Ventilated desktop enclosure for Raspberry Pi 5",
                    "source_type": "ai_generated",
                    "status": "ready",
                },
                {
                    "name": "Pi Zero W IoT Hub",
                    "description": "Wall-mounted IoT hub enclosure",
                    "source_type": "ai_generated",
                    "status": "ready",
                },
            ],
        },
        {
            "name": "Custom Electronics",
            "description": "Various electronics project enclosures",
            "designs": [
                {
                    "name": "Arduino Controller Box",
                    "description": "Industrial controller enclosure with DIN rail",
                    "source_type": "template",
                    "status": "ready",
                },
            ],
        },
    ],
    "enterprise": [
        {
            "name": "Product Line A - Sensors",
            "description": "Production sensor enclosures for Product Line A",
            "designs": [
                {
                    "name": "Temperature Sensor Housing",
                    "description": "IP65 rated outdoor sensor enclosure",
                    "source_type": "ai_generated",
                    "status": "ready",
                },
                {
                    "name": "Humidity Sensor Module",
                    "description": "Compact sensor housing with vents",
                    "source_type": "ai_generated",
                    "status": "ready",
                },
                {
                    "name": "Multi-Sensor Hub",
                    "description": "Central hub for sensor network",
                    "source_type": "template",
                    "status": "ready",
                },
            ],
        },
        {
            "name": "Product Line B - Controllers",
            "description": "Industrial controller enclosures",
            "designs": [
                {
                    "name": "Main Controller Unit",
                    "description": "Primary industrial controller enclosure",
                    "source_type": "ai_generated",
                    "status": "ready",
                },
                {
                    "name": "Remote I/O Module",
                    "description": "DIN rail mounted I/O module",
                    "source_type": "template",
                    "status": "ready",
                },
            ],
        },
        {
            "name": "R&D Prototypes",
            "description": "Experimental designs in development",
            "designs": [
                {
                    "name": "Next-Gen Sensor (Draft)",
                    "description": "Prototype enclosure for new sensor design",
                    "source_type": "ai_generated",
                    "status": "draft",
                },
            ],
        },
    ],
}


# =============================================================================
# Seeding Functions
# =============================================================================


async def create_user(
    session: AsyncSession,
    email: str,
    password: str,
    display_name: str,
    role: str = "user",
    tier: str = "free",
    org_name: str | None = None,
) -> User | None:
    """Create a user with subscription and settings."""

    # Check if user already exists
    from sqlalchemy import select

    existing = await session.execute(select(User).where(User.email == email))
    if existing.scalar_one_or_none():
        logger.info(f"User {email} already exists, skipping")
        return None

    # Create user
    user = User(
        id=uuid4(),
        email=email,
        password_hash=hash_password(password),
        display_name=display_name,
        role=role,
        status="active",
        email_verified_at=datetime.now(UTC),
        last_login_at=datetime.now(UTC) - timedelta(days=1),
        extra_data={
            "org_name": org_name,
            "seeded": True,
            "seeded_at": datetime.now(UTC).isoformat(),
        },
    )
    session.add(user)
    await session.flush()

    # Create subscription
    subscription = Subscription(
        id=uuid4(),
        user_id=user.id,
        tier=tier,
        status="active",
        current_period_start=datetime.now(UTC) - timedelta(days=15),
        current_period_end=datetime.now(UTC) + timedelta(days=15),
    )
    session.add(subscription)

    # Create user settings
    settings = UserSettings(
        id=uuid4(),
        user_id=user.id,
        preferences={
            "defaultUnits": "mm",
            "defaultExportFormat": "stl",
            "theme": "system",
            "language": "en",
        },
        notifications={
            "email": {
                "jobComplete": True,
                "weeklyDigest": True,
                "marketing": False,
            },
            "push": {
                "jobComplete": True,
            },
        },
    )
    session.add(settings)

    logger.info(f"Created user: {email} ({tier} tier, {role} role)")
    return user


async def create_sample_data(
    session: AsyncSession,
    user: User,
    tier: str,
) -> None:
    """Create sample projects and designs for a user."""

    projects_data = SAMPLE_PROJECTS.get(tier, SAMPLE_PROJECTS["free"])

    for project_data in projects_data:
        # Create project
        project = Project(
            id=uuid4(),
            user_id=user.id,
            name=project_data["name"],
            description=project_data["description"],
        )
        session.add(project)
        await session.flush()

        # Create designs
        for design_data in project_data.get("designs", []):
            design = Design(
                id=uuid4(),
                project_id=project.id,
                user_id=user.id,
                name=design_data["name"],
                description=design_data["description"],
                source_type=design_data["source_type"],
                status=design_data["status"],
                extra_data={
                    "seeded": True,
                    "parameters": {
                        "length": 100,
                        "width": 60,
                        "height": 40,
                        "wall_thickness": 2,
                    },
                },
            )
            session.add(design)
            await session.flush()

            # Create initial version
            version = DesignVersion(
                id=uuid4(),
                design_id=design.id,
                version_number=1,
                file_url="s3://designs/sample/version_1.step",
                file_formats={"step": "s3://designs/sample/version_1.step"},
                change_description="Initial design",
                parameters={
                    "length": 100,
                    "width": 60,
                    "height": 40,
                    "wall_thickness": 2,
                },
                geometry_info={
                    "boundingBox": {"x": 100, "y": 60, "z": 40},
                    "volume": 240000,
                    "unit": "mm",
                },
            )
            session.add(version)

            # Update design with current version
            design.current_version_id = version.id

        logger.info(
            f"  Created project: {project_data['name']} with {len(project_data.get('designs', []))} designs"
        )


async def seed_users() -> dict:
    """
    Seed all users and sample data.

    Returns:
        Summary of seeded data
    """
    summary = {
        "users_created": 0,
        "projects_created": 0,
        "designs_created": 0,
        "errors": [],
    }

    async with async_session_maker() as session:
        try:
            # 1. Create platform admin
            logger.info("Creating platform admin...")
            admin = await create_user(
                session,
                email=PLATFORM_ADMIN["email"],
                password=PLATFORM_ADMIN["password"],
                display_name=PLATFORM_ADMIN["display_name"],
                role="admin",
                tier="enterprise",
            )
            if admin:
                summary["users_created"] += 1
                await create_sample_data(session, admin, "enterprise")

            # 2. Create free tier users
            logger.info("Creating free tier users...")
            for user_data in FREE_USERS:
                user = await create_user(
                    session,
                    email=user_data["email"],
                    password=user_data["password"],
                    display_name=user_data["display_name"],
                    tier="free",
                )
                if user:
                    summary["users_created"] += 1
                    await create_sample_data(session, user, "free")

            # 3. Create pro tier users
            logger.info("Creating pro tier users...")
            for user_data in PRO_USERS:
                user = await create_user(
                    session,
                    email=user_data["email"],
                    password=user_data["password"],
                    display_name=user_data["display_name"],
                    tier="pro",
                )
                if user:
                    summary["users_created"] += 1
                    await create_sample_data(session, user, "pro")

            # 4. Create enterprise organizations
            logger.info("Creating enterprise organizations...")
            for org in ENTERPRISE_ORGS:
                logger.info(f"  Organization: {org['org_name']}")

                # Create org admin
                org_admin = await create_user(
                    session,
                    email=org["admin"]["email"],
                    password=org["admin"]["password"],
                    display_name=org["admin"]["display_name"],
                    role=org["admin"].get("role", "user"),
                    tier="enterprise",
                    org_name=org["org_name"],
                )
                if org_admin:
                    summary["users_created"] += 1
                    await create_sample_data(session, org_admin, "enterprise")

                # Create org users
                for user_data in org["users"]:
                    user = await create_user(
                        session,
                        email=user_data["email"],
                        password=user_data["password"],
                        display_name=user_data["display_name"],
                        tier="enterprise",
                        org_name=org["org_name"],
                    )
                    if user:
                        summary["users_created"] += 1
                        await create_sample_data(session, user, "enterprise")

            await session.commit()
            logger.info(f"Seeding complete! Created {summary['users_created']} users")

        except Exception as e:
            await session.rollback()
            logger.error(f"Seeding failed: {e}")
            summary["errors"].append(str(e))
            raise

    return summary


# =============================================================================
# CLI Entry Point
# =============================================================================

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
    )

    print("=" * 60)
    print("AssemblematicAI - User Seeding")
    print("=" * 60)
    print()
    print("This will create the following users:")
    print()
    print("Platform Admin:")
    print(f"  • {PLATFORM_ADMIN['email']} (password: {PLATFORM_ADMIN['password']})")
    print()
    print("Free Tier Users:")
    for u in FREE_USERS:
        print(f"  • {u['email']} (password: {u['password']})")
    print()
    print("Pro Tier Users:")
    for u in PRO_USERS:
        print(f"  • {u['email']} (password: {u['password']})")
    print()
    print("Enterprise Organizations:")
    for org in ENTERPRISE_ORGS:
        print(f"  {org['org_name']}:")
        print(f"    • {org['admin']['email']} (admin, password: {org['admin']['password']})")
        for u in org["users"]:
            print(f"    • {u['email']} (password: {u['password']})")
    print()
    print("=" * 60)

    asyncio.run(seed_users())

    print()
    print("Done! You can now log in with any of the above credentials.")
