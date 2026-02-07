"""
Database backup and recovery utilities.

Provides backup automation, point-in-time recovery,
and data export capabilities.
"""

import asyncio
import gzip
import logging
import shutil
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Literal

from app.core.config import settings
from app.core.storage import StorageBucket, storage_client

logger = logging.getLogger(__name__)


class DatabaseBackup:
    """
    Database backup and recovery utilities.

    Supports:
    - Full database dumps (pg_dump)
    - Compressed backups
    - Upload to object storage
    - Backup rotation/retention
    - Point-in-time restore
    """

    def __init__(
        self,
        backup_dir: str = "/tmp/backups",
        retention_days: int = 30,
    ):
        self.backup_dir = Path(backup_dir)
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        self.retention_days = retention_days

    def _get_connection_args(self) -> list[str]:
        """Get pg_dump connection arguments."""
        return [
            "-h",
            settings.POSTGRES_HOST,
            "-p",
            str(settings.POSTGRES_PORT),
            "-U",
            settings.POSTGRES_USER,
            "-d",
            settings.POSTGRES_DB,
        ]

    async def create_backup(
        self,
        backup_type: Literal["full", "schema", "data"] = "full",
        *,
        compress: bool = True,
        upload_to_storage: bool = True,
    ) -> dict[str, str | int | bool | None]:
        """
        Create a database backup.

        Args:
            backup_type: Type of backup (full, schema only, or data only)
            compress: Gzip compress the backup
            upload_to_storage: Upload to object storage

        Returns:
            Backup metadata dict
        """
        timestamp = datetime.now(tz=UTC).strftime("%Y%m%d_%H%M%S")
        filename = f"backup_{backup_type}_{timestamp}.sql"
        filepath = self.backup_dir / filename

        # Build pg_dump command
        cmd = ["pg_dump", *self._get_connection_args()]

        if backup_type == "schema":
            cmd.append("--schema-only")
        elif backup_type == "data":
            cmd.append("--data-only")

        cmd.extend(
            [
                "--format=plain",
                "--no-owner",
                "--no-privileges",
                "-f",
                str(filepath),
            ]
        )

        # Set password in environment
        env = {"PGPASSWORD": settings.POSTGRES_PASSWORD}

        logger.info(f"Creating {backup_type} backup: {filename}")

        try:
            # Run pg_dump
            process = await asyncio.create_subprocess_exec(
                *cmd,
                env=env,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            _stdout, stderr = await process.communicate()

            if process.returncode != 0:
                raise RuntimeError(f"pg_dump failed: {stderr.decode()}")

            # Get file size
            file_size = filepath.stat().st_size

            # Compress if requested
            if compress:
                compressed_path = filepath.with_suffix(".sql.gz")
                with filepath.open("rb") as f_in:
                    with gzip.open(compressed_path, "wb") as f_out:
                        shutil.copyfileobj(f_in, f_out)

                # Remove uncompressed file
                filepath.unlink()
                filepath = compressed_path
                filename = compressed_path.name
                file_size = compressed_path.stat().st_size

            # Upload to storage
            storage_url = None
            if upload_to_storage:
                storage_key = f"backups/{timestamp[:8]}/{filename}"
                with filepath.open("rb") as f:
                    storage_url = await storage_client.upload_file(
                        StorageBucket.TEMP,
                        storage_key,
                        f,
                        content_type="application/gzip" if compress else "text/plain",
                        metadata={
                            "backup_type": backup_type,
                            "database": settings.POSTGRES_DB,
                            "created_at": timestamp,
                        },
                    )
                logger.info(f"Uploaded backup to storage: {storage_key}")

            backup_info: dict[str, Any] = {
                "filename": filename,
                "filepath": str(filepath),
                "backup_type": backup_type,
                "size_bytes": file_size,
                "compressed": compress,
                "storage_url": storage_url,
                "created_at": timestamp,
            }

            logger.info(f"Backup created successfully: {file_size / 1024 / 1024:.2f} MB")
            return backup_info

        except Exception as e:
            logger.error(f"Backup failed: {e}")
            raise

    async def restore_backup(
        self,
        backup_path: str | Path,
        *,
        drop_existing: bool = False,
    ) -> bool:
        """
        Restore database from backup.

        Args:
            backup_path: Path to backup file (local or storage URL)
            drop_existing: Drop existing tables before restore

        Returns:
            True if successful
        """
        backup_path = Path(backup_path)

        # Decompress if needed
        if backup_path.suffix == ".gz":
            decompressed_path = backup_path.with_suffix("")
            with gzip.open(backup_path, "rb") as f_in:
                with decompressed_path.open("wb") as f_out:
                    shutil.copyfileobj(f_in, f_out)
            backup_path = decompressed_path

        # Build psql command
        cmd = ["psql", *self._get_connection_args()]

        if drop_existing:
            # First, drop all tables
            drop_cmd = [*cmd, "-c", "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"]
            env = {"PGPASSWORD": settings.POSTGRES_PASSWORD}

            process = await asyncio.create_subprocess_exec(
                *drop_cmd,
                env=env,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await process.communicate()

        # Restore
        cmd.extend(["-f", str(backup_path)])
        env = {"PGPASSWORD": settings.POSTGRES_PASSWORD}

        logger.info(f"Restoring from backup: {backup_path}")

        process = await asyncio.create_subprocess_exec(
            *cmd,
            env=env,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _stdout, stderr = await process.communicate()

        if process.returncode != 0:
            logger.error(f"Restore failed: {stderr.decode()}")
            return False

        logger.info("Restore completed successfully")
        return True

    async def cleanup_old_backups(self) -> int:
        """
        Remove backups older than retention period.

        Returns:
            Number of backups removed
        """
        cutoff = datetime.now(tz=UTC) - timedelta(days=self.retention_days)
        removed_count = 0

        # Clean local backups
        for filepath in self.backup_dir.glob("backup_*.sql*"):
            if filepath.stat().st_mtime < cutoff.timestamp():
                filepath.unlink()
                removed_count += 1
                logger.debug(f"Removed old backup: {filepath.name}")

        # Clean storage backups
        old_backups = await storage_client.list_files(
            StorageBucket.TEMP,
            prefix="backups/",
        )

        keys_to_delete = []
        for backup in old_backups:
            if backup["last_modified"] < cutoff:
                keys_to_delete.append(backup["key"])

        if keys_to_delete:
            await storage_client.delete_files(StorageBucket.TEMP, keys_to_delete)
            removed_count += len(keys_to_delete)

        logger.info(f"Cleaned up {removed_count} old backups")
        return removed_count

    async def list_backups(self) -> list[dict[str, str]]:
        """List available backups from storage."""
        backups = await storage_client.list_files(
            StorageBucket.TEMP,
            prefix="backups/",
        )

        return sorted(
            backups,
            key=lambda x: x["last_modified"],
            reverse=True,
        )


class DataExporter:
    """
    Data export utilities for analytics and compliance.

    Supports exporting data in various formats for:
    - Analytics/BI pipelines
    - GDPR data portability requests
    - Audit and compliance
    """

    def __init__(self, export_dir: str = "/tmp/exports"):
        self.export_dir = Path(export_dir)
        self.export_dir.mkdir(parents=True, exist_ok=True)

    async def export_user_data(
        self,
        user_id: str,
        *,
        _format: Literal["json", "csv"] = "json",
    ) -> Path:
        """
        Export all data for a specific user (GDPR compliance).

        This exports:
        - User profile
        - Projects and designs
        - Job history
        - Audit logs

        Returns:
            Path to export archive
        """
        import json
        from uuid import UUID

        from app.core.database import async_session_maker
        from app.repositories import (
            AuditLogRepository,
            DesignRepository,
            JobRepository,
            ProjectRepository,
            UserRepository,
        )

        user_uuid = UUID(user_id)
        timestamp = datetime.now(tz=UTC).strftime("%Y%m%d_%H%M%S")
        export_subdir = self.export_dir / f"user_export_{user_id}_{timestamp}"
        export_subdir.mkdir(parents=True, exist_ok=True)

        async with async_session_maker() as session:
            # User profile
            user_repo = UserRepository(session)
            user = await user_repo.get_with_settings(user_uuid)

            if user:
                user_data = {
                    "id": str(user.id),
                    "email": user.email,
                    "full_name": user.display_name,
                    "tier": user.tier,
                    "created_at": user.created_at.isoformat(),
                    "settings": {
                        "default_units": user.settings.preferences.get("defaultUnits") if user.settings else None,
                        "theme": user.settings.preferences.get("theme") if user.settings else None,
                    }
                    if user.settings
                    else None,
                }

                with (export_subdir / "profile.json").open("w") as f:
                    json.dump(user_data, f, indent=2, default=str)

            # Projects
            project_repo = ProjectRepository(session)
            projects = await project_repo.get_user_projects(user_uuid, include_archived=True)

            projects_data = [
                {
                    "id": str(p.id),
                    "name": p.name,
                    "description": p.description,
                    "created_at": p.created_at.isoformat(),
                }
                for p in projects
            ]

            with (export_subdir / "projects.json").open("w") as f:
                json.dump(projects_data, f, indent=2, default=str)

            # Designs
            design_repo = DesignRepository(session)
            all_designs = []
            for project in projects:
                designs = await design_repo.get_project_designs(project.id)
                for d in designs:
                    all_designs.append(
                        {
                            "id": str(d.id),
                            "project_id": str(d.project_id),
                            "name": d.name,
                            "source_type": d.source_type,
                            "status": d.status,
                            "created_at": d.created_at.isoformat(),
                        }
                    )

            with (export_subdir / "designs.json").open("w") as f:
                json.dump(all_designs, f, indent=2, default=str)

            # Job history
            job_repo = JobRepository(session)
            jobs = await job_repo.get_user_jobs(user_uuid, limit=1000)

            jobs_data = [
                {
                    "id": str(j.id),
                    "job_type": j.job_type,
                    "status": j.status,
                    "created_at": j.created_at.isoformat(),
                    "completed_at": j.completed_at.isoformat() if j.completed_at else None,
                }
                for j in jobs
            ]

            with (export_subdir / "jobs.json").open("w") as f:
                json.dump(jobs_data, f, indent=2, default=str)

            # Audit logs
            audit_repo = AuditLogRepository(session)
            audit_logs = await audit_repo.get_user_activity(user_uuid, limit=1000)

            audit_data = [
                {
                    "action": a.action,
                    "resource_type": a.resource_type,
                    "created_at": a.created_at.isoformat(),
                    "status": a.status,
                }
                for a in audit_logs
            ]

            with (export_subdir / "activity.json").open("w") as f:
                json.dump(audit_data, f, indent=2, default=str)

        # Create archive
        archive_path = shutil.make_archive(
            str(export_subdir),
            "zip",
            export_subdir,
        )

        # Clean up temp directory
        shutil.rmtree(export_subdir)

        logger.info(f"User data exported: {archive_path}")
        return Path(archive_path)

    async def export_analytics_snapshot(
        self,
        start_date: datetime,
        end_date: datetime,
    ) -> Path:
        """
        Export analytics data snapshot for BI/data warehouse.

        Exports aggregated, anonymized data for analytics pipelines.
        """
        import json

        from sqlalchemy import func, select

        from app.core.database import async_session_maker
        from app.models import Design, Job, Template, User
        from app.models.user import Subscription

        timestamp = datetime.now(tz=UTC).strftime("%Y%m%d_%H%M%S")
        export_path = self.export_dir / f"analytics_snapshot_{timestamp}.json"

        async with async_session_maker() as session:
            # User metrics
            user_count = await session.execute(
                select(func.count(User.id)).where(User.created_at.between(start_date, end_date))
            )

            users_by_tier = await session.execute(
                select(Subscription.tier, func.count(Subscription.id))
                .where(Subscription.created_at.between(start_date, end_date))
                .group_by(Subscription.tier)
            )

            # Design metrics
            design_count = await session.execute(
                select(func.count(Design.id)).where(Design.created_at.between(start_date, end_date))
            )

            designs_by_source = await session.execute(
                select(Design.source_type, func.count(Design.id))
                .where(Design.created_at.between(start_date, end_date))
                .group_by(Design.source_type)
            )

            # Job metrics
            job_stats = await session.execute(
                select(
                    Job.job_type,
                    Job.status,
                    func.count(Job.id),
                    func.avg(Job.execution_time_ms),
                )
                .where(Job.created_at.between(start_date, end_date))
                .group_by(Job.job_type, Job.status)
            )

            # Template usage
            template_usage = await session.execute(
                select(
                    Template.slug,
                    Template.category,
                    Template.use_count,
                )
                .order_by(Template.use_count.desc())
                .limit(20)
            )

            snapshot = {
                "period": {
                    "start": start_date.isoformat(),
                    "end": end_date.isoformat(),
                },
                "users": {
                    "total_new": user_count.scalar() or 0,
                    "by_tier": {row[0]: row[1] for row in users_by_tier.all()},
                },
                "designs": {
                    "total_new": design_count.scalar() or 0,
                    "by_source": {row[0]: row[1] for row in designs_by_source.all()},
                },
                "jobs": [
                    {
                        "type": row[0],
                        "status": row[1],
                        "count": row[2],
                        "avg_duration_ms": float(row[3]) if row[3] else None,
                    }
                    for row in job_stats.all()
                ],
                "top_templates": [
                    {
                        "slug": row[0],
                        "category": row[1],
                        "use_count": row[2],
                    }
                    for row in template_usage.all()
                ],
                "exported_at": datetime.now(tz=UTC).isoformat(),
            }

            with export_path.open("w") as f:
                json.dump(snapshot, f, indent=2, default=str)

        logger.info(f"Analytics snapshot exported: {export_path}")
        return export_path


# Global instances
db_backup = DatabaseBackup()
data_exporter = DataExporter()
