"""
Seed data for thread standards.

Syncs the in-memory thread registry with the ``reference_components``
table so that thread data is discoverable through the standard component
search API as well as the dedicated thread endpoints.

Usage:
    python -m app.seeds.threads

Or via Makefile:
    make db-seed
"""

import asyncio
import logging
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.cad.threads import (
    THREAD_FAMILY_INFO,
    THREAD_REGISTRY,
)
from app.core.database import async_session_maker
from app.models.reference_component import ReferenceComponent

logger = logging.getLogger(__name__)


async def seed_thread_standards(
    db: AsyncSession | None = None,
) -> int:
    """Seed thread standard data into the reference_components table.

    Follows the same upsert pattern as ``components_v2.py``.
    Seeds all entries from ``THREAD_REGISTRY`` into
    ``ReferenceComponent`` rows with ``category='thread_standard'``
    and ``subcategory=family.value``.

    Args:
        db: Optional async session.  When *None* a new session is
            created from the default session maker.

    Returns:
        Number of records upserted (created + updated).
    """
    own_session = db is None
    if own_session:  # noqa: SIM108
        session = async_session_maker()
    else:
        session = db  # type: ignore[assignment]

    try:
        upserted = await _do_seed(session)
        await session.commit()
        return upserted
    except Exception:
        await session.rollback()
        raise
    finally:
        if own_session:
            await session.close()


async def _do_seed(db: AsyncSession) -> int:
    """Insert or update all thread standard rows.

    Args:
        db: Active async database session.

    Returns:
        Total number of upserted rows.
    """
    upserted = 0

    for family, specs in THREAD_REGISTRY.items():
        info = THREAD_FAMILY_INFO.get(family, {})
        family_name = info.get("name", family.value)
        info.get("standard_ref", "")

        for size, spec in specs.items():
            slug = f"{family.value}:{size}"

            existing = await db.execute(
                select(ReferenceComponent).where(
                    ReferenceComponent.source_type == "library",
                    ReferenceComponent.category == "thread_standard",
                    ReferenceComponent.notes == slug,
                )
            )
            row = existing.scalar_one_or_none()

            dimensions = {
                "major_diameter": spec.major_diameter,
                "pitch_mm": spec.pitch_mm,
                "minor_diameter_ext": spec.minor_diameter_ext,
                "unit": "mm",
            }
            tags = [family.value, size]
            if spec.pitch_series:
                tags.append(spec.pitch_series.value)

            if row is not None:
                row.name = f"{family_name} {size}"  # type: ignore[assignment]
                row.description = (  # type: ignore[assignment]
                    f"{family_name} thread, size {size}, pitch {spec.pitch_mm} mm"
                )
                row.subcategory = family.value  # type: ignore[assignment]
                row.dimensions = dimensions  # type: ignore[assignment]
                row.tags = tags  # type: ignore[assignment]
            else:
                db.add(
                    ReferenceComponent(
                        id=uuid4(),
                        name=f"{family_name} {size}",
                        description=(
                            f"{family_name} thread, size {size}, pitch {spec.pitch_mm} mm"
                        ),
                        category="thread_standard",
                        subcategory=family.value,
                        dimensions=dimensions,
                        tags=tags,
                        notes=slug,
                        source_type="library",
                        extraction_status="complete",
                        is_verified=True,
                        user_id=None,
                    )
                )

            upserted += 1

    logger.info(
        "Thread standards seed complete: %d records upserted",
        upserted,
    )
    return upserted


async def main() -> None:
    """Run thread standards seeding."""
    logging.basicConfig(level=logging.INFO)
    logger.info("Seeding thread standards from registry...")

    async with async_session_maker() as db:
        count = await seed_thread_standards(db)
        logger.info("Thread standards seeding complete: %d records", count)


if __name__ == "__main__":
    asyncio.run(main())
