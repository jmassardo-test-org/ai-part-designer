"""
Large-scale seed data generator for admin panel testing.

Creates a realistic dataset for testing admin panel functionality:
- Multiple users across different tiers
- Organizations with varying team sizes
- Projects and designs with realistic distribution
- Subscriptions, notifications, and audit logs

Usage:
    python -m app.seeds.large_scale --users 1000 --orgs 50
    python -m app.seeds.large_scale --scale small   # 500 users, 25 orgs
    python -m app.seeds.large_scale --scale medium  # 2000 users, 100 orgs
    python -m app.seeds.large_scale --scale large   # 10000 users, 500 orgs

Or via Makefile:
    make seed-large SCALE=medium
"""

import argparse
import asyncio
import logging
import random
import string
from datetime import datetime, timedelta
from typing import Any
from uuid import uuid4

from faker import Faker
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session_maker
from app.core.security import hash_password
from app.models.user import User, Subscription, UserSettings
from app.models.project import Project
from app.models.design import Design
from app.models.organization import Organization, OrganizationMember
from app.models.notification import Notification
from app.models.audit import AuditLog
from app.models.subscription import SubscriptionTier

logger = logging.getLogger(__name__)
fake = Faker()

# =============================================================================
# Scale Presets
# =============================================================================

SCALE_PRESETS = {
    "small": {
        "users": 500,
        "orgs": 25,
        "projects_per_user": (1, 5),
        "designs_per_project": (1, 10),
    },
    "medium": {
        "users": 2000,
        "orgs": 100,
        "projects_per_user": (2, 8),
        "designs_per_project": (2, 15),
    },
    "large": {
        "users": 10000,
        "orgs": 500,
        "projects_per_user": (3, 10),
        "designs_per_project": (3, 20),
    },
}

# Tier distribution (percentages)
TIER_DISTRIBUTION = {
    "free": 0.70,      # 70%
    "starter": 0.15,   # 15%
    "pro": 0.10,       # 10%
    "enterprise": 0.05 # 5%
}

# Status distribution for projects
PROJECT_STATUS_DISTRIBUTION = {
    "active": 0.70,
    "archived": 0.20,
    "suspended": 0.05,
    "draft": 0.05,
}

# Design source types
DESIGN_SOURCES = ["template", "ai_generated", "imported", "manual"]


# =============================================================================
# Batch Insert Helper
# =============================================================================

async def batch_insert(
    session: AsyncSession,
    objects: list[Any],
    batch_size: int = 500,
    label: str = "objects",
) -> int:
    """Insert objects in batches for better performance."""
    total = len(objects)
    inserted = 0
    
    for i in range(0, total, batch_size):
        batch = objects[i:i + batch_size]
        session.add_all(batch)
        await session.flush()
        inserted += len(batch)
        logger.info(f"  Inserted {inserted}/{total} {label}")
    
    return inserted


# =============================================================================
# Data Generators
# =============================================================================

def generate_user(tier_slug: str, hashed_pwd: str, index: int) -> User:
    """Generate a random user.
    
    Args:
        tier_slug: The subscription tier for this user.
        hashed_pwd: Pre-hashed password for efficiency.
        index: User index for unique email generation.
        
    Returns:
        A new User model instance.
    """
    created_at = fake.date_time_between(start_date="-2y", end_date="now")
    last_login = fake.date_time_between(start_date=created_at, end_date="now") if random.random() > 0.1 else None
    
    # Use seed_ prefix for easy identification of seeded users
    unique_suffix = f"{index}_{fake.uuid4()[:8]}"
    email = f"seed_{unique_suffix}@{fake.domain_name()}"
    
    # Determine status
    status = "active"
    if random.random() < 0.02:  # 2% suspended
        status = "suspended"
    elif random.random() < 0.05:  # 5% pending verification
        status = "pending_verification"
    
    return User(
        id=uuid4(),
        email=email,
        password_hash=hashed_pwd,
        display_name=fake.name(),
        role="user",
        status=status,
        email_verified_at=created_at if status == "active" else None,
        created_at=created_at,
        last_login_at=last_login,
    )


def generate_organization(owner_id: str) -> Organization:
    """Generate a random organization."""
    return Organization(
        id=uuid4(),
        name=fake.company(),
        slug=fake.unique.slug(),
        owner_id=owner_id,
        created_at=fake.date_time_between(start_date="-2y", end_date="now"),
    )


def generate_project(user_id: str, org_id: str | None = None) -> Project:
    """Generate a random project."""
    status_choices = list(PROJECT_STATUS_DISTRIBUTION.keys())
    status_weights = list(PROJECT_STATUS_DISTRIBUTION.values())
    
    return Project(
        id=uuid4(),
        name=f"{fake.catch_phrase()} {fake.word().capitalize()}",
        description=fake.paragraph(nb_sentences=2) if random.random() > 0.3 else None,
        user_id=user_id,
        organization_id=org_id,
        status=random.choices(status_choices, weights=status_weights)[0],
        created_at=fake.date_time_between(start_date="-1y", end_date="now"),
    )


def generate_design(project_id: str, user_id: str) -> Design:
    """Generate a random design.
    
    Args:
        project_id: The project this design belongs to.
        user_id: The owner of the design.
    """
    created_at = fake.date_time_between(start_date="-1y", end_date="now")
    
    return Design(
        id=uuid4(),
        name=f"{fake.word().capitalize()} Design {random.randint(1, 100)}",
        description=fake.sentence() if random.random() > 0.5 else None,
        project_id=project_id,
        user_id=user_id,
        source_type=random.choice(DESIGN_SOURCES),
        is_public=random.random() < 0.1,  # 10% public
        status=random.choice(["draft", "ready", "processing"]),
        created_at=created_at,
    )


def generate_subscription(user_id: str, tier_slug: str) -> Subscription:
    """Generate a subscription for a user."""
    start_date = fake.date_time_between(start_date="-1y", end_date="now")
    end_date = start_date + timedelta(days=30)
    
    return Subscription(
        id=uuid4(),
        user_id=user_id,
        tier=tier_slug,
        status=random.choices(
            ["active", "cancelled", "past_due"],
            weights=[0.85, 0.10, 0.05]
        )[0],
        current_period_start=start_date,
        current_period_end=end_date,
        cancel_at_period_end=random.random() < 0.05,
        created_at=start_date,
    )


def generate_notification(user_id: str) -> Notification:
    """Generate a notification for a user."""
    from app.models.notification import NotificationType
    
    type_choices = [
        NotificationType.SYSTEM_ANNOUNCEMENT,
        NotificationType.JOB_COMPLETED,
        NotificationType.JOB_FAILED,
    ]
    notif_type = random.choice(type_choices)
    
    titles = {
        NotificationType.SYSTEM_ANNOUNCEMENT: "System Maintenance Notice",
        NotificationType.JOB_COMPLETED: "Your design generation is complete",
        NotificationType.JOB_FAILED: "Design generation failed",
    }
    
    return Notification(
        id=uuid4(),
        user_id=user_id,
        type=notif_type,
        title=titles[notif_type],
        message=fake.paragraph(nb_sentences=1),
        is_read=random.random() < 0.6,  # 60% read
        created_at=fake.date_time_between(start_date="-30d", end_date="now"),
    )


def generate_audit_log(user_id: str | None = None) -> AuditLog:
    """Generate an audit log entry."""
    actions = ["create", "update", "delete", "login", "logout", "view", "export"]
    resources = ["user", "project", "design", "template", "organization"]
    
    return AuditLog(
        id=uuid4(),
        user_id=user_id,
        actor_type="user" if user_id else "system",
        action=random.choice(actions),
        resource_type=random.choice(resources),
        resource_id=str(uuid4()),
        ip_address=fake.ipv4() if random.random() > 0.2 else None,
        created_at=fake.date_time_between(start_date="-30d", end_date="now"),
    )


# =============================================================================
# Main Seeder
# =============================================================================

async def seed_large_scale(
    num_users: int = 1000,
    num_orgs: int = 50,
    projects_range: tuple[int, int] = (1, 5),
    designs_range: tuple[int, int] = (1, 10),
) -> dict[str, int]:
    """
    Generate large-scale seed data.
    
    Args:
        num_users: Number of users to generate
        num_orgs: Number of organizations to generate
        projects_range: (min, max) projects per user
        designs_range: (min, max) designs per project
    
    Returns:
        Dictionary with counts of created entities
    """
    logger.info(f"Starting large-scale seed: {num_users} users, {num_orgs} orgs")
    
    async with async_session_maker() as session:
        # Get subscription tiers
        from sqlalchemy import select
        result = await session.execute(select(SubscriptionTier))
        tiers = {t.slug: t.id for t in result.scalars().all()}
        
        if not tiers:
            logger.error("No subscription tiers found! Run regular seeds first.")
            raise RuntimeError("No subscription tiers found. Run regular seeds first.")
        
        # Pre-hash a common password for speed
        common_password = hash_password("seed123!")
        
        # Calculate tier distribution
        tier_counts = {
            tier: int(num_users * pct) 
            for tier, pct in TIER_DISTRIBUTION.items()
        }
        # Adjust to match total
        diff = num_users - sum(tier_counts.values())
        tier_counts["free"] += diff
        
        logger.info(f"Tier distribution: {tier_counts}")
        
        # =================================================================
        # Generate Users
        # =================================================================
        logger.info("Generating users...")
        users = []
        user_tiers = []
        user_index = 0
        
        # First, create the seed marker user
        marker_user = User(
            id=uuid4(),
            email=SEED_MARKER_EMAIL,
            password_hash=common_password,
            display_name="Seed Marker (Do Not Delete)",
            role="user",
            status="suspended",
            email_verified_at=None,
            created_at=datetime.utcnow(),
        )
        users.append(marker_user)
        user_tiers.append((marker_user.id, "free"))
        
        for tier, count in tier_counts.items():
            tier_id = tiers.get(tier)
            if not tier_id:
                logger.warning(f"Tier '{tier}' not found, using 'free'")
                tier = "free"
            
            for _ in range(count):
                user = generate_user(tier, common_password, user_index)
                users.append(user)
                user_tiers.append((user.id, tier))
                user_index += 1
        
        await batch_insert(session, users, label="users")
        
        # =================================================================
        # Generate Subscriptions
        # =================================================================
        logger.info("Generating subscriptions...")
        subscriptions = [
            generate_subscription(str(user_id), tier_slug)
            for user_id, tier_slug in user_tiers
        ]
        await batch_insert(session, subscriptions, label="subscriptions")
        
        # =================================================================
        # Generate Organizations
        # =================================================================
        logger.info("Generating organizations...")
        # Pick random enterprise users as org owners
        enterprise_users = [u for u, (_, tier_slug) in zip(users, user_tiers) if tier_slug == "enterprise"]
        org_owners = random.sample(enterprise_users, min(num_orgs, len(enterprise_users)))
        
        organizations = []
        for owner in org_owners:
            org = generate_organization(str(owner.id))
            organizations.append(org)
        
        await batch_insert(session, organizations, label="organizations")
        
        # =================================================================
        # Generate Organization Members
        # =================================================================
        logger.info("Generating organization memberships...")
        memberships = []
        for org in organizations:
            # Add owner as admin
            memberships.append(OrganizationMember(
                id=uuid4(),
                organization_id=org.id,
                user_id=org.owner_id,
                role="admin",
            ))
            
            # Add random members (5-50 per org)
            num_members = random.randint(5, min(50, len(users) // num_orgs))
            member_users = random.sample(users, num_members)
            for user in member_users:
                if str(user.id) != str(org.owner_id):
                    memberships.append(OrganizationMember(
                        id=uuid4(),
                        organization_id=org.id,
                        user_id=user.id,
                        role=random.choice(["member", "member", "admin"]),  # 33% admins
                    ))
        
        await batch_insert(session, memberships, label="memberships")
        
        # =================================================================
        # Generate Projects
        # =================================================================
        logger.info("Generating projects...")
        projects = []
        user_org_map = {}  # Map users to their orgs
        for m in memberships:
            if str(m.user_id) not in user_org_map:
                user_org_map[str(m.user_id)] = []
            user_org_map[str(m.user_id)].append(str(m.organization_id))
        
        for user in users:
            num_projects = random.randint(*projects_range)
            for _ in range(num_projects):
                # 30% of projects are org projects
                org_id = None
                if random.random() < 0.3 and str(user.id) in user_org_map:
                    org_id = random.choice(user_org_map[str(user.id)])
                
                project = generate_project(str(user.id), org_id)
                projects.append(project)
        
        await batch_insert(session, projects, label="projects")
        
        # =================================================================
        # Generate Designs
        # =================================================================
        logger.info("Generating designs...")
        designs = []
        for project in projects:
            num_designs = random.randint(*designs_range)
            for _ in range(num_designs):
                design = generate_design(str(project.id), str(project.user_id))
                designs.append(design)
        
        await batch_insert(session, designs, batch_size=1000, label="designs")
        
        # =================================================================
        # Generate Notifications
        # =================================================================
        logger.info("Generating notifications...")
        notifications = []
        for user in random.sample(users, min(500, len(users))):
            num_notifs = random.randint(1, 10)
            for _ in range(num_notifs):
                notifications.append(generate_notification(str(user.id)))
        
        await batch_insert(session, notifications, label="notifications")
        
        # =================================================================
        # Generate Audit Logs
        # =================================================================
        logger.info("Generating audit logs...")
        audit_logs = []
        for _ in range(min(2000, num_users)):
            user = random.choice(users) if random.random() > 0.1 else None
            audit_logs.append(generate_audit_log(str(user.id) if user else None))
        
        await batch_insert(session, audit_logs, label="audit_logs")
        
        # =================================================================
        # Commit
        # =================================================================
        await session.commit()
        logger.info("All data committed successfully!")
        
        return {
            "users": len(users),
            "subscriptions": len(subscriptions),
            "organizations": len(organizations),
            "memberships": len(memberships),
            "projects": len(projects),
            "designs": len(designs),
            "notifications": len(notifications),
            "audit_logs": len(audit_logs),
        }


# =============================================================================
# Idempotency & Incremental Support
# =============================================================================

SEED_MARKER_EMAIL = "seed_marker@assemblematic.ai"


async def check_if_seeded(session: AsyncSession) -> bool:
    """Check if the database has already been seeded.
    
    Looks for the seed marker user to determine if seeding has occurred.
    
    Args:
        session: Database session.
        
    Returns:
        True if already seeded, False otherwise.
    """
    from sqlalchemy import select
    result = await session.execute(
        select(User).where(User.email == SEED_MARKER_EMAIL)
    )
    return result.scalar_one_or_none() is not None


async def get_existing_seed_counts(session: AsyncSession) -> dict[str, int]:
    """Get counts of existing seeded entities.
    
    Args:
        session: Database session.
        
    Returns:
        Dictionary with entity names and their counts.
    """
    from sqlalchemy import func, select
    
    counts = {}
    
    # Count users with common seed password pattern (email contains seed_)
    result = await session.execute(
        select(func.count(User.id)).where(User.email.like("seed_%"))
    )
    counts["users"] = result.scalar_one()
    
    result = await session.execute(select(func.count(Organization.id)))
    counts["organizations"] = result.scalar_one()
    
    result = await session.execute(select(func.count(Project.id)))
    counts["projects"] = result.scalar_one()
    
    result = await session.execute(select(func.count(Design.id)))
    counts["designs"] = result.scalar_one()
    
    return counts


async def clean_seed_data(session: AsyncSession) -> dict[str, int]:
    """Remove all seeded data from the database.
    
    This removes data in dependency order to avoid foreign key constraints.
    
    Args:
        session: Database session.
        
    Returns:
        Dictionary with entity names and counts of deleted records.
    """
    from sqlalchemy import delete
    
    deleted: dict[str, int] = {}
    
    logger.info("Cleaning seed data...")
    
    # Delete in reverse dependency order
    # 1. Audit logs (no dependencies)
    result = await session.execute(delete(AuditLog))
    count = result.rowcount or 0
    deleted["audit_logs"] = count
    logger.info(f"  Deleted {count} audit logs")
    
    # 2. Notifications
    result = await session.execute(delete(Notification))
    count = result.rowcount or 0
    deleted["notifications"] = count
    logger.info(f"  Deleted {count} notifications")
    
    # 3. Designs (depend on projects)
    result = await session.execute(delete(Design))
    count = result.rowcount or 0
    deleted["designs"] = count
    logger.info(f"  Deleted {count} designs")
    
    # 4. Projects (depend on users/orgs)
    result = await session.execute(delete(Project))
    count = result.rowcount or 0
    deleted["projects"] = count
    logger.info(f"  Deleted {count} projects")
    
    # 5. Organization members
    result = await session.execute(delete(OrganizationMember))
    count = result.rowcount or 0
    deleted["memberships"] = count
    logger.info(f"  Deleted {count} memberships")
    
    # 6. Organizations
    result = await session.execute(delete(Organization))
    count = result.rowcount or 0
    deleted["organizations"] = count
    logger.info(f"  Deleted {count} organizations")
    
    # 7. Subscriptions
    result = await session.execute(delete(Subscription))
    count = result.rowcount or 0
    deleted["subscriptions"] = count
    logger.info(f"  Deleted {count} subscriptions")
    
    # 8. Users (seeded users only - based on email pattern)
    result = await session.execute(
        delete(User).where(User.email.like("seed_%"))
    )
    count = result.rowcount or 0
    deleted["users"] = count
    logger.info(f"  Deleted {count} seeded users")
    
    await session.commit()
    logger.info("Seed data cleanup complete!")
    
    return deleted


# =============================================================================
# CLI Entry Point
# =============================================================================

async def async_main(args) -> int:
    """Async main entry point - all DB operations happen here."""
    
    # Handle --check flag: just check and exit
    if args.check:
        async with async_session_maker() as session:
            is_seeded = await check_if_seeded(session)
            if is_seeded:
                counts = await get_existing_seed_counts(session)
                print("Database is already seeded.")
                print(f"  Users: {counts.get('users', 0):,}")
                print(f"  Organizations: {counts.get('organizations', 0):,}")
                print(f"  Projects: {counts.get('projects', 0):,}")
                print(f"  Designs: {counts.get('designs', 0):,}")
                return 0
            else:
                print("Database is NOT seeded.")
                return 1
    
    # Handle --clean flag: remove existing data
    if args.clean:
        print("=" * 60)
        print("Cleaning existing seed data...")
        print("=" * 60)
        print()
        
        async with async_session_maker() as session:
            deleted = await clean_seed_data(session)
        
        print()
        print("Deleted entities:")
        for entity, count in deleted.items():
            print(f"  {entity}: {count:,}")
        print()
        
        if not (args.scale or args.users > 0):
            # Just cleaning, no seeding
            print("Clean complete. Use additional flags to seed new data.")
            return 0
    
    # Check if already seeded (unless --force or --incremental)
    if not args.force and not args.incremental and not args.clean:
        async with async_session_maker() as session:
            if await check_if_seeded(session):
                print("=" * 60)
                print("ERROR: Database is already seeded!")
                print("=" * 60)
                print()
                print("Options:")
                print("  --incremental  Add more data to existing seed")
                print("  --clean        Remove existing seed data first")
                print("  --force        Force seed (may cause duplicates)")
                print()
                return 1
    
    # Get configuration
    if args.scale:
        config = SCALE_PRESETS[args.scale]
        num_users = config["users"]
        num_orgs = config["orgs"]
        projects_range = config["projects_per_user"]
        designs_range = config["designs_per_project"]
    else:
        num_users = args.users
        num_orgs = args.orgs
        projects_range = (1, 5)
        designs_range = (1, 10)
    
    mode_label = "INCREMENTAL" if args.incremental else "FRESH"
    
    print("=" * 60)
    print(f"AssemblematicAI - Large-Scale Seeding ({mode_label})")
    print("=" * 60)
    print()
    print(f"Configuration:")
    print(f"  Users: {num_users}")
    print(f"  Organizations: {num_orgs}")
    print(f"  Projects per user: {projects_range[0]}-{projects_range[1]}")
    print(f"  Designs per project: {designs_range[0]}-{designs_range[1]}")
    print()
    print("Estimated entities:")
    avg_projects = num_users * sum(projects_range) / 2
    avg_designs = avg_projects * sum(designs_range) / 2
    print(f"  Projects: ~{int(avg_projects):,}")
    print(f"  Designs: ~{int(avg_designs):,}")
    print()
    print("=" * 60)
    print()
    
    # Skip confirmation if --yes flag is set
    if not args.yes:
        import sys
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, lambda: input("Press Enter to start seeding (Ctrl+C to cancel)..."))
        print()
    
    # Run seeder
    result = await seed_large_scale(
        num_users=num_users,
        num_orgs=num_orgs,
        projects_range=projects_range,
        designs_range=designs_range,
    )
    
    print()
    print("=" * 60)
    print("Seeding Complete!")
    print("=" * 60)
    print()
    print("Created entities:")
    for entity, count in result.items():
        print(f"  {entity}: {count:,}")
    print()
    print("Common password for all seeded users: seed123!")
    print()
    return 0


def main():
    """CLI entry point for large-scale seeding."""
    parser = argparse.ArgumentParser(
        description="Generate large-scale seed data for admin panel testing"
    )
    parser.add_argument(
        "--scale",
        choices=["small", "medium", "large"],
        help="Use a preset scale configuration",
    )
    parser.add_argument(
        "--users",
        type=int,
        default=1000,
        help="Number of users to generate (default: 1000)",
    )
    parser.add_argument(
        "--orgs",
        type=int,
        default=50,
        help="Number of organizations to generate (default: 50)",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Check if database is already seeded (exit 0 if yes, 1 if no)",
    )
    parser.add_argument(
        "--incremental",
        action="store_true",
        help="Add to existing seed data instead of failing if already seeded",
    )
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Remove existing seed data before seeding",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force seeding even if already seeded (use with caution)",
    )
    parser.add_argument(
        "--yes", "-y",
        action="store_true",
        help="Skip confirmation prompt (for non-interactive use)",
    )
    
    args = parser.parse_args()
    
    # Setup logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(levelname)s - %(message)s",
    )
    
    # Run everything in a single async context
    import sys
    sys.exit(asyncio.run(async_main(args)))


if __name__ == "__main__":
    main()

