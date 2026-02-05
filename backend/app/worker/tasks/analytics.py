"""
Analytics and event processing tasks.
"""

import logging
from datetime import UTC, datetime, timedelta

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(
    name="app.worker.tasks.analytics.process_pending_events",
)
def process_pending_events() -> dict:
    """
    Process pending analytics events from Redis queue.

    This task runs periodically to batch-process events
    for downstream analytics pipelines.
    """
    import asyncio

    from app.core.events import event_tracker

    async def run():
        events = await event_tracker.consume_batch(batch_size=500)

        if not events:
            return {"processed": 0}

        # Process events - in production, this would:
        # 1. Transform events for the data warehouse
        # 2. Send to analytics service (Segment, Amplitude, etc.)
        # 3. Store in data lake for batch analysis

        # Group by event type for logging
        event_counts = {}
        for event in events:
            event_name = event.get("event_name", "unknown")
            event_counts[event_name] = event_counts.get(event_name, 0) + 1

        logger.info(f"Processed {len(events)} analytics events: {event_counts}")

        return {
            "processed": len(events),
            "event_counts": event_counts,
        }

    return asyncio.run(run())


@shared_task(
    name="app.worker.tasks.analytics.generate_daily_report",
)
def generate_daily_report(date: str | None = None) -> dict:
    """
    Generate daily analytics report.

    Aggregates key metrics for the specified date (or yesterday).
    """
    import asyncio

    from sqlalchemy import func, select

    from app.core.database import async_session_maker
    from app.models import Design, Job, User

    if date:
        report_date = datetime.fromisoformat(date).date()
    else:
        report_date = (datetime.now(UTC) - timedelta(days=1)).date()

    start = datetime.combine(report_date, datetime.min.time())
    end = datetime.combine(report_date, datetime.max.time())

    async def run():
        async with async_session_maker() as session:
            # New users
            new_users = await session.execute(
                select(func.count(User.id)).where(User.created_at.between(start, end))
            )

            # New designs
            new_designs = await session.execute(
                select(func.count(Design.id)).where(Design.created_at.between(start, end))
            )

            # Job stats
            job_stats = await session.execute(
                select(
                    Job.status,
                    func.count(Job.id),
                    func.avg(Job.execution_time_ms),
                )
                .where(Job.created_at.between(start, end))
                .group_by(Job.status)
            )

            jobs_by_status = {
                row[0]: {"count": row[1], "avg_time_ms": float(row[2]) if row[2] else None}
                for row in job_stats.all()
            }

            report = {
                "date": report_date.isoformat(),
                "metrics": {
                    "new_users": new_users.scalar() or 0,
                    "new_designs": new_designs.scalar() or 0,
                    "jobs": jobs_by_status,
                    "total_jobs": sum(v["count"] for v in jobs_by_status.values()),
                },
                "generated_at": datetime.now(UTC).isoformat(),
            }

            logger.info(f"Generated daily report for {report_date}")
            return report

    return asyncio.run(run())


@shared_task(
    name="app.worker.tasks.analytics.calculate_user_metrics",
)
def calculate_user_metrics(user_id: str) -> dict:
    """
    Calculate metrics for a specific user.

    Used for user dashboards and engagement tracking.
    """
    import asyncio
    from uuid import UUID

    from app.core.database import async_session_maker
    from app.repositories import (
        DesignRepository,
        JobRepository,
        ProjectRepository,
    )

    async def run():
        user_uuid = UUID(user_id)

        async with async_session_maker() as session:
            project_repo = ProjectRepository(session)
            DesignRepository(session)
            job_repo = JobRepository(session)

            # Count projects
            project_count = await project_repo.count(filters={"user_id": user_uuid})

            # Get recent jobs
            job_stats = await job_repo.get_job_stats(since=datetime.now(UTC) - timedelta(days=30))

            return {
                "user_id": user_id,
                "total_projects": project_count,
                "last_30_days": {
                    "jobs": job_stats,
                },
                "calculated_at": datetime.now(UTC).isoformat(),
            }

    return asyncio.run(run())


@shared_task(
    name="app.worker.tasks.analytics.export_to_warehouse",
)
def export_to_warehouse(
    table: str,
    start_date: str,
    end_date: str,
) -> dict:
    """
    Export data to data warehouse for analytics.

    Extracts, transforms, and loads data to analytics platform.
    """
    import asyncio

    from app.core.backup import data_exporter

    async def run():
        start = datetime.fromisoformat(start_date)
        end = datetime.fromisoformat(end_date)

        export_path = await data_exporter.export_analytics_snapshot(start, end)

        # TODO: Upload to data warehouse (BigQuery, Redshift, Snowflake, etc.)

        return {
            "table": table,
            "period": {"start": start_date, "end": end_date},
            "export_path": str(export_path),
            "status": "completed",
        }

    return asyncio.run(run())
