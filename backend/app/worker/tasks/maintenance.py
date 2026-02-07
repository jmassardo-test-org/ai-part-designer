"""
Maintenance and housekeeping tasks.
"""

import logging
from datetime import UTC, datetime, timedelta
from typing import Any, Literal, cast

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(  # type: ignore[untyped-decorator]
    name="app.worker.tasks.maintenance.purge_expired_trash",
)
def purge_expired_trash() -> dict[str, Any]:
    """
    Permanently delete items that have exceeded their trash retention period.

    This task:
    1. Finds all soft-deleted items past their retention period
    2. Permanently deletes the database records
    3. Cleans up associated storage files
    4. Returns summary of deleted items

    Runs daily via Celery beat.
    """
    import asyncio

    from sqlalchemy import select

    from app.core.database import async_session_maker
    from app.core.storage import StorageBucket, storage_client
    from app.models import Design, File, Project

    async def run() -> dict[str, Any]:
        deleted_summary: dict[str, Any] = {
            "designs": 0,
            "projects": 0,
            "files": 0,
            "storage_files_removed": 0,
            "errors": [],
        }

        async with async_session_maker() as session:
            # Get all users with their trash settings
            from app.models import User

            users_result = await session.execute(select(User))
            users = users_result.scalars().all()

            for user in users:
                # Get user's retention setting (default 30 days)
                user_settings = (user.extra_data or {}).get("trash_settings", {})
                retention_days = user_settings.get("retention_days", 30)
                auto_empty = user_settings.get("auto_empty", True)

                if not auto_empty:
                    continue

                cutoff = datetime.now(tz=UTC) - timedelta(days=retention_days)

                try:
                    # Find and delete expired designs
                    designs_result = await session.execute(
                        select(Design)
                        .where(Design.user_id == user.id)
                        .where(Design.deleted_at.isnot(None))
                        .where(Design.deleted_at < cutoff)
                    )
                    expired_designs = designs_result.scalars().all()

                    for design in expired_designs:
                        # Clean up storage files
                        file_url = getattr(design, "file_url", None) or design.extra_data.get(
                            "file_url"
                        )
                        if file_url:
                            try:
                                await storage_client.delete_files(StorageBucket.DESIGNS, [file_url])
                                deleted_summary["storage_files_removed"] += 1
                            except Exception as e:
                                deleted_summary["errors"].append(
                                    f"Failed to delete storage file for design {design.id}: {e}"
                                )

                        await session.delete(design)
                        deleted_summary["designs"] += 1

                    # Find and delete expired projects
                    projects_result = await session.execute(
                        select(Project)
                        .where(Project.user_id == user.id)
                        .where(Project.deleted_at.isnot(None))
                        .where(Project.deleted_at < cutoff)
                    )
                    expired_projects = projects_result.scalars().all()

                    for project in expired_projects:
                        await session.delete(project)
                        deleted_summary["projects"] += 1

                    # Find and delete expired files
                    files_result = await session.execute(
                        select(File)
                        .where(File.user_id == user.id)
                        .where(File.deleted_at.isnot(None))
                        .where(File.deleted_at < cutoff)
                    )
                    expired_files = files_result.scalars().all()

                    for file in expired_files:
                        storage_key = getattr(file, "storage_key", None) or getattr(
                            file, "storage_bucket", None
                        )
                        if storage_key:
                            try:
                                await storage_client.delete_files(
                                    StorageBucket.DESIGNS, [storage_key]
                                )
                                deleted_summary["storage_files_removed"] += 1
                            except Exception as e:
                                deleted_summary["errors"].append(
                                    f"Failed to delete storage file for file {file.id}: {e}"
                                )

                        await session.delete(file)
                        deleted_summary["files"] += 1

                except Exception as e:
                    deleted_summary["errors"].append(f"Error processing user {user.id}: {e}")

            await session.commit()

        total_deleted = (
            deleted_summary["designs"] + deleted_summary["projects"] + deleted_summary["files"]
        )

        if total_deleted > 0:
            logger.info(
                f"Purged {total_deleted} expired trash items: "
                f"{deleted_summary['designs']} designs, "
                f"{deleted_summary['projects']} projects, "
                f"{deleted_summary['files']} files"
            )

        if deleted_summary["errors"]:
            logger.warning(f"Trash purge completed with {len(deleted_summary['errors'])} errors")

        return deleted_summary

    return asyncio.run(run())


@shared_task(  # type: ignore[untyped-decorator]
    name="app.worker.tasks.maintenance.send_trash_deletion_warnings",
)
def send_trash_deletion_warnings() -> dict[str, Any]:
    """
    Send email notifications to users with items expiring soon in trash.

    Sends warnings at:
    - 7 days before deletion
    - 3 days before deletion
    - 1 day before deletion

    Tracks sent notifications to avoid duplicates.
    Runs daily via Celery beat.
    """
    import asyncio

    from sqlalchemy import and_, select

    from app.core.config import settings
    from app.core.database import async_session_maker
    from app.models import Design, Project, User
    from app.services.email import get_email_service

    # Warning thresholds in days
    WARNING_DAYS = [7, 3, 1]

    async def run() -> dict[str, Any]:
        notification_summary: dict[str, Any] = {
            "users_notified": 0,
            "emails_sent": 0,
            "items_warned": 0,
            "errors": [],
        }

        email_service = get_email_service()

        async with async_session_maker() as session:
            # Get all users with email notifications enabled
            users_result = await session.execute(
                select(User).where(and_(User.status == "active", User.deleted_at.is_(None)))
            )
            users = users_result.scalars().all()

            for user in users:
                # Check if user has email notifications enabled
                user_settings = user.extra_data or {}
                email_notifications = user_settings.get("email_notifications", True)
                trash_notifications = user_settings.get("trash_notifications", True)

                if not email_notifications or not trash_notifications:
                    continue

                # Get user's retention setting
                trash_settings = user_settings.get("trash_settings", {})
                retention_days = trash_settings.get("retention_days", 30)

                # Track notifications already sent (stored in user's extra_data)
                sent_notifications = user_settings.get("trash_notifications_sent", {})

                # Find items expiring at each warning threshold
                items_to_warn = []
                now = datetime.now(tz=UTC)

                for warning_day in WARNING_DAYS:
                    # Calculate cutoff: items deleted X days ago where X = retention - warning
                    days_since_deletion = retention_days - warning_day
                    if days_since_deletion < 0:
                        continue

                    cutoff_start = now - timedelta(days=days_since_deletion + 1)
                    cutoff_end = now - timedelta(days=days_since_deletion)

                    # Find designs in this window
                    designs_result = await session.execute(
                        select(Design)
                        .where(Design.user_id == user.id)
                        .where(Design.deleted_at.isnot(None))
                        .where(
                            and_(Design.deleted_at >= cutoff_start, Design.deleted_at < cutoff_end)
                        )
                    )
                    designs = designs_result.scalars().all()

                    for design in designs:
                        notification_key = f"design_{design.id}_{warning_day}"
                        if notification_key not in sent_notifications:
                            # deleted_at is guaranteed non-None by query filter
                            assert design.deleted_at is not None
                            items_to_warn.append(
                                {
                                    "name": design.name,
                                    "type": "Design",
                                    "deleted_at": design.deleted_at.strftime("%Y-%m-%d"),
                                    "days_until_deletion": warning_day,
                                    "notification_key": notification_key,
                                }
                            )

                    # Find projects in this window
                    projects_result = await session.execute(
                        select(Project)
                        .where(Project.user_id == user.id)
                        .where(Project.deleted_at.isnot(None))
                        .where(
                            and_(
                                Project.deleted_at >= cutoff_start, Project.deleted_at < cutoff_end
                            )
                        )
                    )
                    projects = projects_result.scalars().all()

                    for project in projects:
                        notification_key = f"project_{project.id}_{warning_day}"
                        if notification_key not in sent_notifications:
                            # deleted_at is guaranteed non-None by query filter
                            assert project.deleted_at is not None
                            items_to_warn.append(
                                {
                                    "name": project.name,
                                    "type": "Project",
                                    "deleted_at": project.deleted_at.strftime("%Y-%m-%d"),
                                    "days_until_deletion": warning_day,
                                    "notification_key": notification_key,
                                }
                            )

                if items_to_warn:
                    try:
                        # Group by days until deletion
                        min_days = min(
                            cast("int", item["days_until_deletion"]) for item in items_to_warn
                        )

                        # Build URLs
                        base_url = settings.FRONTEND_URL or "https://assemblematic.ai"
                        trash_url = f"{base_url}/trash"
                        settings_url = f"{base_url}/settings/trash"

                        # Send email
                        success = await email_service.send_trash_deletion_warning(
                            email=user.email,
                            display_name=user.display_name or user.email.split("@")[0],
                            days_until_deletion=min_days,
                            items=[
                                {
                                    "name": item["name"],
                                    "type": item["type"],
                                    "deleted_at": item["deleted_at"],
                                }
                                for item in items_to_warn
                            ],
                            trash_url=trash_url,
                            settings_url=settings_url,
                        )

                        if success:
                            notification_summary["emails_sent"] += 1
                            notification_summary["users_notified"] += 1
                            notification_summary["items_warned"] += len(items_to_warn)

                            # Mark notifications as sent
                            for item in items_to_warn:
                                sent_notifications[item["notification_key"]] = now.isoformat()

                            # Update user's extra_data with sent notifications
                            user.extra_data = {
                                **(user.extra_data or {}),
                                "trash_notifications_sent": sent_notifications,
                            }

                    except Exception as e:
                        notification_summary["errors"].append(
                            f"Failed to notify user {user.id}: {e}"
                        )

            await session.commit()

        if notification_summary["emails_sent"] > 0:
            logger.info(
                f"Sent {notification_summary['emails_sent']} trash deletion warnings "
                f"to {notification_summary['users_notified']} users"
            )

        if notification_summary["errors"]:
            logger.warning(
                f"Trash notifications completed with {len(notification_summary['errors'])} errors"
            )

        return notification_summary

    return asyncio.run(run())


@shared_task(  # type: ignore[untyped-decorator]
    name="app.worker.tasks.maintenance.cleanup_old_jobs",
)
def cleanup_old_jobs(days: int = 30) -> dict[str, Any]:
    """
    Clean up old completed/failed jobs.

    Removes job records older than specified days to prevent
    database bloat while preserving recent history.
    """
    import asyncio

    from sqlalchemy import delete

    from app.core.database import async_session_maker
    from app.models import Job

    cutoff = datetime.now(tz=UTC) - timedelta(days=days)

    async def run() -> dict[str, Any]:
        async with async_session_maker() as session:
            result = await session.execute(
                delete(Job)
                .where(Job.status.in_(["completed", "failed", "cancelled"]))
                .where(Job.created_at < cutoff)
            )

            deleted_count = result.rowcount  # type: ignore[attr-defined]
            await session.commit()

            logger.info(f"Cleaned up {deleted_count} old jobs")
            return {"deleted": deleted_count, "cutoff_date": cutoff.isoformat()}

    return asyncio.run(run())


@shared_task(  # type: ignore[untyped-decorator]
    name="app.worker.tasks.maintenance.check_stale_jobs",
)
def check_stale_jobs(stale_after_minutes: int = 30) -> dict[str, Any]:
    """
    Check for stale running jobs and mark them as failed.

    Jobs that have been running longer than expected are likely
    stuck and should be failed for retry.
    """
    import asyncio

    from app.core.database import async_session_maker
    from app.repositories import JobRepository

    async def run() -> dict[str, Any]:
        async with async_session_maker() as session:
            job_repo = JobRepository(session)
            stale_jobs = await job_repo.get_stale_jobs(stale_after_minutes)

            failed_count = 0
            for job in stale_jobs:
                job.status = "failed"
                job.completed_at = datetime.now(tz=UTC)
                job.error_message = f"Job timed out after {stale_after_minutes} minutes"
                job.error = {
                    "type": "timeout",
                    "message": job.error_message,
                    "started_at": job.started_at.isoformat() if job.started_at else None,
                }
                failed_count += 1

            await session.commit()

            if failed_count > 0:
                logger.warning(f"Marked {failed_count} stale jobs as failed")

            return {"stale_jobs_failed": failed_count}

    return asyncio.run(run())


@shared_task(  # type: ignore[untyped-decorator]
    name="app.worker.tasks.maintenance.cleanup_temp_files",
)
def cleanup_temp_files(max_age_hours: int = 24) -> dict[str, Any]:
    """
    Clean up temporary files in storage.

    Removes temp files older than specified hours.
    """
    import asyncio

    from app.core.storage import StorageBucket, storage_client

    cutoff = datetime.now(tz=UTC) - timedelta(hours=max_age_hours)

    async def run() -> dict[str, Any]:
        # List temp files
        temp_files = await storage_client.list_files(
            StorageBucket.TEMP,
            prefix="",
        )

        # Find old files
        old_files = [f["key"] for f in temp_files if f["last_modified"] < cutoff]

        if old_files:
            deleted_count = await storage_client.delete_files(
                StorageBucket.TEMP,
                old_files,
            )
            logger.info(f"Cleaned up {deleted_count} temp files")
            return {"deleted": deleted_count}

        return {"deleted": 0}

    return asyncio.run(run())


@shared_task(  # type: ignore[untyped-decorator]
    name="app.worker.tasks.maintenance.backup_database",
)
def backup_database(backup_type: Literal["full", "schema", "data"] = "full") -> dict[str, Any]:
    """
    Create database backup and upload to storage.

    Runs daily to ensure data durability.
    """
    import asyncio

    from app.core.backup import db_backup

    async def run() -> dict[str, Any]:
        backup_info = await db_backup.create_backup(
            backup_type=backup_type,
            compress=True,
            upload_to_storage=True,
        )

        # Clean up old backups
        removed = await db_backup.cleanup_old_backups()

        backup_info["old_backups_removed"] = removed

        logger.info(f"Database backup completed: {backup_info['filename']}")
        return backup_info

    return asyncio.run(run())


@shared_task(  # type: ignore[untyped-decorator]
    name="app.worker.tasks.maintenance.vacuum_database",
)
def vacuum_database() -> dict[str, Any]:
    """
    Run PostgreSQL VACUUM ANALYZE to reclaim space and update statistics.

    Should be run during low-traffic periods.
    """
    import asyncio

    from sqlalchemy import text

    from app.core.database import async_session_maker

    async def run() -> dict[str, Any]:
        async with async_session_maker() as session:
            # Run VACUUM ANALYZE (note: can't run in transaction)
            await session.execute(text("ANALYZE"))
            await session.commit()

            logger.info("Database ANALYZE completed")
            return {"status": "completed", "operation": "ANALYZE"}

    return asyncio.run(run())


@shared_task(  # type: ignore[untyped-decorator]
    name="app.worker.tasks.maintenance.update_search_vectors",
)
def update_search_vectors() -> dict[str, Any]:
    """
    Update full-text search vectors for designs.

    Ensures search vectors are up-to-date for newly modified designs.
    """
    import asyncio

    from sqlalchemy import text

    from app.core.database import async_session_maker

    async def run() -> dict[str, Any]:
        async with async_session_maker() as session:
            # Update search vectors for designs without them
            result = await session.execute(
                text("""
                    UPDATE designs
                    SET search_vector = to_tsvector('english',
                        coalesce(name, '') || ' ' || coalesce(description, '')
                    )
                    WHERE search_vector IS NULL
                    AND deleted_at IS NULL
                """)
            )

            updated_count = result.rowcount  # type: ignore[attr-defined]
            await session.commit()

            logger.info(f"Updated {updated_count} search vectors")
            return {"updated": updated_count}

    return asyncio.run(run())


@shared_task(  # type: ignore[untyped-decorator]
    name="app.worker.tasks.maintenance.generate_missing_thumbnails",
)
def generate_missing_thumbnails() -> dict[str, Any]:
    """
    Generate thumbnails for designs that are missing them.
    """
    import asyncio

    from sqlalchemy import select

    from app.core.database import async_session_maker
    from app.models import DesignVersion
    from app.worker.tasks.cad import generate_thumbnail

    async def run() -> dict[str, Any]:
        async with async_session_maker() as session:
            # Find versions without thumbnails
            result = await session.execute(
                select(DesignVersion).where(DesignVersion.thumbnail_url.is_(None)).limit(100)
            )
            versions = result.scalars().all()

            queued = 0
            for version in versions:
                if version.file_url:
                    # Queue thumbnail generation
                    generate_thumbnail.delay(version.file_url)
                    queued += 1

            logger.info(f"Queued {queued} thumbnail generation tasks")
            return {"queued": queued}

    return asyncio.run(run())


@shared_task(  # type: ignore[untyped-decorator]
    name="app.worker.tasks.maintenance.check_storage_health",
)
def check_storage_health() -> dict[str, Any]:
    """
    Check storage bucket health and report issues.
    """
    import asyncio

    from app.core.storage import StorageBucket, storage_client

    async def run() -> dict[str, Any]:
        results = {}

        for bucket in StorageBucket:
            try:
                await storage_client.list_files(bucket, max_keys=1)
                results[bucket.value] = {
                    "status": "healthy",
                    "accessible": True,
                }
            except Exception as e:
                results[bucket.value] = {
                    "status": "error",
                    "accessible": False,
                    "error": str(e),
                }
                logger.error(f"Storage bucket {bucket.value} health check failed: {e}")

        all_healthy = all(r["status"] == "healthy" for r in results.values())

        return {
            "overall_status": "healthy" if all_healthy else "degraded",
            "buckets": results,
            "checked_at": datetime.now(tz=UTC).isoformat(),
        }

    return asyncio.run(run())


@shared_task(  # type: ignore[untyped-decorator]
    name="app.worker.tasks.maintenance.check_data_integrity",
)
def check_data_integrity() -> dict[str, Any]:
    """
    Run comprehensive data integrity checks.

    Checks for:
    - Orphaned database records
    - Missing storage files
    - Checksum validation
    - Referential integrity

    Runs weekly via Celery beat. Results are logged and can trigger alerts.
    """
    import asyncio

    from app.core.database import async_session_maker
    from app.services.integrity import DataIntegrityService

    async def run() -> dict[str, Any]:
        async with async_session_maker() as session:
            service = DataIntegrityService(session)
            report = await service.run_full_check()

            # Log summary
            if report.is_healthy:
                logger.info(
                    f"Integrity check passed - {len(report.checks_run)} checks, no critical issues"
                )
            else:
                logger.warning(f"Integrity check found issues: {report.issue_counts}")

                # Log critical issues
                for issue in report.issues:
                    if issue.severity in ("critical", "error"):
                        logger.error(
                            f"Integrity issue: {issue.message} "
                            f"(table={issue.table}, id={issue.record_id})"
                        )

            return report.to_dict()

    return asyncio.run(run())


@shared_task(  # type: ignore[untyped-decorator]
    name="app.worker.tasks.maintenance.verify_backups",
)
def verify_backups() -> dict[str, Any]:
    """
    Verify integrity of recent backups.

    Checks:
    - Backup files exist and are readable
    - Checksums match recorded values
    - Backup can be decompressed
    - Sample data can be read

    Runs weekly via Celery beat. Issues trigger alerts.
    """
    import asyncio

    from app.services.backup import BackupService, BackupStatus

    async def run() -> dict[str, Any]:
        verification_summary: dict[str, Any] = {
            "backups_checked": 0,
            "backups_valid": 0,
            "backups_invalid": 0,
            "issues": [],
            "verified_at": datetime.now(tz=UTC).isoformat(),
        }

        backup_service = BackupService()

        # Get recent backups (last 7 days)
        cutoff = datetime.now(tz=UTC) - timedelta(days=7)
        recent_backups = [
            record
            for record in backup_service._backup_index.values()
            if record.created_at >= cutoff and record.status == BackupStatus.COMPLETED
        ]

        for record in recent_backups:
            verification_summary["backups_checked"] += 1

            try:
                result = await backup_service.verify_backup(record.id)

                if result.is_valid:
                    verification_summary["backups_valid"] += 1

                    # Update backup status to verified
                    record.status = BackupStatus.VERIFIED

                    logger.info(f"Backup {record.id} verified successfully")
                else:
                    verification_summary["backups_invalid"] += 1

                    # Update backup status to corrupted
                    record.status = BackupStatus.CORRUPTED

                    for issue in result.issues:
                        verification_summary["issues"].append(
                            {
                                "backup_id": str(record.id),
                                "created_at": record.created_at.isoformat(),
                                "issue": issue,
                            }
                        )
                        logger.error(f"Backup {record.id} verification failed: {issue}")

            except Exception as e:
                verification_summary["backups_invalid"] += 1
                verification_summary["issues"].append(
                    {
                        "backup_id": str(record.id),
                        "error": str(e),
                    }
                )
                logger.error(f"Error verifying backup {record.id}: {e}")

        # Save updated backup index
        backup_service._save_backup_index()

        # Log summary
        if verification_summary["backups_invalid"] > 0:
            logger.warning(
                f"Backup verification completed with {verification_summary['backups_invalid']} "
                f"invalid backups out of {verification_summary['backups_checked']}"
            )
        else:
            logger.info(
                f"Backup verification passed: {verification_summary['backups_valid']} "
                f"backups verified"
            )

        return verification_summary

    return asyncio.run(run())


@shared_task(  # type: ignore[untyped-decorator]
    name="app.worker.tasks.maintenance.archive_old_audit_logs",
)
def archive_old_audit_logs() -> dict[str, Any]:
    """
    Archive audit logs older than the retention period.

    This task:
    1. Queries audit logs older than configured retention period (default 90 days)
    2. Generates summary statistics for analytics
    3. Compresses and exports logs to cold storage (ARCHIVES bucket)
    4. Deletes archived logs from database to reduce table size

    Runs weekly via Celery beat.
    """
    import asyncio
    import gzip
    import json
    from io import BytesIO

    from sqlalchemy import delete, func, select

    from app.core.config import settings
    from app.core.database import async_session_maker
    from app.core.storage import StorageBucket, storage_client
    from app.models.audit import AuditLog

    async def run() -> dict[str, Any]:
        archive_summary: dict[str, Any] = {
            "logs_archived": 0,
            "logs_deleted": 0,
            "archive_files_created": 0,
            "total_size_bytes": 0,
            "summary_stats": {},
            "errors": [],
        }

        async with async_session_maker() as session:
            # Calculate cutoff date
            cutoff_date = datetime.now(tz=UTC) - timedelta(days=settings.AUDIT_LOG_RETENTION_DAYS)

            # Query old audit logs
            logs_result = await session.execute(
                select(AuditLog)
                .where(AuditLog.created_at < cutoff_date)
                .order_by(AuditLog.created_at)
            )
            old_logs = logs_result.scalars().all()

            if not old_logs:
                logger.info("No audit logs to archive")
                return archive_summary

            logger.info(
                f"Found {len(old_logs)} audit logs older than {settings.AUDIT_LOG_RETENTION_DAYS} days"
            )

            # Generate summary statistics before archiving
            try:
                stats_result = await session.execute(
                    select(
                        AuditLog.action,
                        AuditLog.resource_type,
                        AuditLog.status,
                        func.count(AuditLog.id).label("count"),
                    )
                    .where(AuditLog.created_at < cutoff_date)
                    .group_by(AuditLog.action, AuditLog.resource_type, AuditLog.status)
                )
                stats = stats_result.all()

                summary_stats = {
                    "period_start": min(log.created_at for log in old_logs).isoformat(),
                    "period_end": max(log.created_at for log in old_logs).isoformat(),
                    "total_logs": len(old_logs),
                    "by_action": {},
                    "by_resource_type": {},
                    "by_status": {},
                }

                for stat in stats:
                    action, resource_type, status, count = stat

                    # Count by action
                    if action not in summary_stats["by_action"]:
                        summary_stats["by_action"][action] = 0
                    summary_stats["by_action"][action] += count

                    # Count by resource type
                    if resource_type not in summary_stats["by_resource_type"]:
                        summary_stats["by_resource_type"][resource_type] = 0
                    summary_stats["by_resource_type"][resource_type] += count

                    # Count by status
                    if status not in summary_stats["by_status"]:
                        summary_stats["by_status"][status] = 0
                    summary_stats["by_status"][status] += count

                archive_summary["summary_stats"] = summary_stats
            except Exception as e:
                archive_summary["errors"].append(f"Failed to generate statistics: {e}")
                logger.error(f"Error generating audit log statistics: {e}")

            # Archive logs in batches (1000 logs per file)
            batch_size = 1000
            archive_timestamp = datetime.now(tz=UTC).strftime("%Y%m%d_%H%M%S")

            for batch_num, i in enumerate(range(0, len(old_logs), batch_size)):
                batch = old_logs[i : i + batch_size]

                try:
                    # Serialize logs to JSON
                    logs_data = [
                        {
                            "id": str(log.id),
                            "user_id": str(log.user_id) if log.user_id else None,
                            "actor_type": log.actor_type,
                            "action": log.action,
                            "resource_type": log.resource_type,
                            "resource_id": str(log.resource_id) if log.resource_id else None,
                            "context": log.context,
                            "ip_address": log.ip_address,
                            "user_agent": log.user_agent,
                            "status": log.status,
                            "error_message": log.error_message,
                            "created_at": log.created_at.isoformat(),
                        }
                        for log in batch
                    ]

                    json_data = json.dumps(logs_data, indent=2)

                    # Compress with gzip
                    compressed_buffer = BytesIO()
                    with gzip.GzipFile(fileobj=compressed_buffer, mode="wb") as gz_file:
                        gz_file.write(json_data.encode("utf-8"))

                    compressed_data = compressed_buffer.getvalue()
                    archive_summary["total_size_bytes"] += len(compressed_data)

                    # Upload to cold storage
                    archive_key = f"audit-logs/{archive_timestamp}/batch_{batch_num:04d}.json.gz"
                    await storage_client.upload_file(
                        bucket=StorageBucket.ARCHIVES,
                        key=archive_key,
                        file=compressed_data,
                        content_type="application/gzip",
                        metadata={
                            "original_count": str(len(batch)),
                            "period_start": batch[0].created_at.isoformat(),
                            "period_end": batch[-1].created_at.isoformat(),
                            "archived_at": archive_timestamp,
                        },
                    )

                    archive_summary["archive_files_created"] += 1
                    archive_summary["logs_archived"] += len(batch)

                    logger.info(f"Archived batch {batch_num} ({len(batch)} logs) to {archive_key}")

                except Exception as e:
                    archive_summary["errors"].append(f"Failed to archive batch {batch_num}: {e}")
                    logger.error(f"Error archiving audit log batch {batch_num}: {e}")
                    continue

            # Also save summary statistics file
            try:
                summary_json = json.dumps(archive_summary["summary_stats"], indent=2)
                summary_compressed = BytesIO()
                with gzip.GzipFile(fileobj=summary_compressed, mode="wb") as gz_file:
                    gz_file.write(summary_json.encode("utf-8"))

                summary_key = f"audit-logs/{archive_timestamp}/summary.json.gz"
                await storage_client.upload_file(
                    bucket=StorageBucket.ARCHIVES,
                    key=summary_key,
                    file=summary_compressed.getvalue(),
                    content_type="application/gzip",
                    metadata={"type": "summary", "archived_at": archive_timestamp},
                )
                logger.info(f"Saved summary statistics to {summary_key}")
            except Exception as e:
                archive_summary["errors"].append(f"Failed to save summary: {e}")
                logger.error(f"Error saving audit log summary: {e}")

            # Delete archived logs from database
            try:
                result = await session.execute(
                    delete(AuditLog).where(AuditLog.created_at < cutoff_date)
                )
                archive_summary["logs_deleted"] = result.rowcount or 0
                await session.commit()

                logger.info(f"Deleted {archive_summary['logs_deleted']} archived audit logs")
            except Exception as e:
                archive_summary["errors"].append(f"Failed to delete archived logs: {e}")
                logger.error(f"Error deleting archived audit logs: {e}")
                await session.rollback()

        # Log final summary
        if archive_summary["errors"]:
            logger.warning(
                f"Audit log archival completed with {len(archive_summary['errors'])} errors. "
                f"Archived {archive_summary['logs_archived']} logs in "
                f"{archive_summary['archive_files_created']} files "
                f"({archive_summary['total_size_bytes']} bytes)"
            )
        else:
            logger.info(
                f"Successfully archived {archive_summary['logs_archived']} audit logs "
                f"in {archive_summary['archive_files_created']} files "
                f"({archive_summary['total_size_bytes']} bytes)"
            )

        return archive_summary

    return asyncio.run(run())
