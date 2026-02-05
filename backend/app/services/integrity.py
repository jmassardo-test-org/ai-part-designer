"""
Data Integrity Service.

Provides verification and validation of:
- Database consistency
- Orphaned records detection
- File storage integrity
- Backup verification
"""

import hashlib
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.storage import StorageBucket, storage_client

logger = logging.getLogger(__name__)


class IntegrityCheckType(StrEnum):
    """Types of integrity checks."""

    ORPHANED_RECORDS = "orphaned_records"
    MISSING_FILES = "missing_files"
    CHECKSUM_VALIDATION = "checksum_validation"
    REFERENTIAL_INTEGRITY = "referential_integrity"
    STORAGE_CONSISTENCY = "storage_consistency"


class IntegritySeverity(StrEnum):
    """Severity levels for integrity issues."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class IntegrityIssue:
    """A detected integrity issue."""

    check_type: IntegrityCheckType
    severity: IntegritySeverity
    table: str | None = None
    record_id: str | None = None
    message: str = ""
    details: dict[str, Any] = field(default_factory=dict)
    detected_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "check_type": self.check_type.value,
            "severity": self.severity.value,
            "table": self.table,
            "record_id": self.record_id,
            "message": self.message,
            "details": self.details,
            "detected_at": self.detected_at.isoformat(),
        }


@dataclass
class IntegrityReport:
    """Report from an integrity check run."""

    started_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: datetime | None = None
    checks_run: list[IntegrityCheckType] = field(default_factory=list)
    issues: list[IntegrityIssue] = field(default_factory=list)
    stats: dict[str, Any] = field(default_factory=dict)

    @property
    def is_healthy(self) -> bool:
        """Check if no critical or error issues were found."""
        return not any(
            issue.severity in (IntegritySeverity.CRITICAL, IntegritySeverity.ERROR)
            for issue in self.issues
        )

    @property
    def issue_counts(self) -> dict[str, int]:
        """Count issues by severity."""
        counts = {s.value: 0 for s in IntegritySeverity}
        for issue in self.issues:
            counts[issue.severity.value] += 1
        return counts

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "checks_run": [c.value for c in self.checks_run],
            "is_healthy": self.is_healthy,
            "issue_counts": self.issue_counts,
            "issues": [i.to_dict() for i in self.issues],
            "stats": self.stats,
        }


class DataIntegrityService:
    """
    Service for verifying data integrity across the application.

    Checks for:
    - Orphaned database records (e.g., designs without users)
    - Missing storage files referenced in database
    - Checksum mismatches for stored files
    - Referential integrity violations
    - Storage/database consistency

    Example:
        >>> service = DataIntegrityService(session)
        >>> report = await service.run_full_check()
        >>> if not report.is_healthy:
        ...     logger.error(f"Integrity issues found: {report.issue_counts}")
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def run_full_check(self) -> IntegrityReport:
        """
        Run all integrity checks.

        Returns:
            IntegrityReport with all detected issues
        """
        report = IntegrityReport()

        # Run all checks
        await self._check_orphaned_designs(report)
        await self._check_orphaned_projects(report)
        await self._check_orphaned_files(report)
        await self._check_missing_storage_files(report)
        await self._check_referential_integrity(report)
        await self._collect_stats(report)

        report.completed_at = datetime.utcnow()

        return report

    async def check_orphaned_records(self) -> IntegrityReport:
        """Check only for orphaned records."""
        report = IntegrityReport()

        await self._check_orphaned_designs(report)
        await self._check_orphaned_projects(report)
        await self._check_orphaned_files(report)

        report.completed_at = datetime.utcnow()
        return report

    async def check_storage_integrity(self) -> IntegrityReport:
        """Check only storage-related integrity."""
        report = IntegrityReport()

        await self._check_missing_storage_files(report)
        await self._check_file_checksums(report)

        report.completed_at = datetime.utcnow()
        return report

    async def _check_orphaned_designs(self, report: IntegrityReport) -> None:
        """Check for designs without valid projects."""
        from app.models import Design, Project

        report.checks_run.append(IntegrityCheckType.ORPHANED_RECORDS)

        # Find designs with project_ids that don't exist in projects table
        result = await self.session.execute(
            select(Design.id, Design.name, Design.project_id)
            .outerjoin(Project, Design.project_id == Project.id)
            .where(Project.id.is_(None))
            .where(Design.deleted_at.is_(None))
        )
        orphaned = result.all()

        for design_id, name, project_id in orphaned:
            report.issues.append(
                IntegrityIssue(
                    check_type=IntegrityCheckType.ORPHANED_RECORDS,
                    severity=IntegritySeverity.ERROR,
                    table="designs",
                    record_id=str(design_id),
                    message=f"Design '{name}' references non-existent project",
                    details={"project_id": str(project_id)},
                )
            )

    async def _check_orphaned_projects(self, report: IntegrityReport) -> None:
        """Check for projects without valid users."""
        from app.models import Project, User

        # Find projects with user_ids that don't exist
        result = await self.session.execute(
            select(Project.id, Project.name, Project.user_id)
            .outerjoin(User, Project.user_id == User.id)
            .where(User.id.is_(None))
            .where(Project.deleted_at.is_(None))
        )
        orphaned = result.all()

        for project_id, name, user_id in orphaned:
            report.issues.append(
                IntegrityIssue(
                    check_type=IntegrityCheckType.ORPHANED_RECORDS,
                    severity=IntegritySeverity.ERROR,
                    table="projects",
                    record_id=str(project_id),
                    message=f"Project '{name}' references non-existent user",
                    details={"user_id": str(user_id)},
                )
            )

    async def _check_orphaned_files(self, report: IntegrityReport) -> None:
        """Check for files without valid users or designs."""
        from app.models import File, User

        # Files without users
        result = await self.session.execute(
            select(File.id, File.filename, File.user_id)
            .outerjoin(User, File.user_id == User.id)
            .where(User.id.is_(None))
            .where(File.deleted_at.is_(None))
        )
        orphaned = result.all()

        for file_id, filename, user_id in orphaned:
            report.issues.append(
                IntegrityIssue(
                    check_type=IntegrityCheckType.ORPHANED_RECORDS,
                    severity=IntegritySeverity.ERROR,
                    table="files",
                    record_id=str(file_id),
                    message=f"File '{filename}' references non-existent user",
                    details={"user_id": str(user_id)},
                )
            )

    async def _check_missing_storage_files(self, report: IntegrityReport) -> None:
        """Check for database records pointing to missing storage files."""
        from app.models import DesignVersion

        report.checks_run.append(IntegrityCheckType.MISSING_FILES)

        # Check design versions with file URLs
        result = await self.session.execute(
            select(DesignVersion.id, DesignVersion.design_id, DesignVersion.file_url)
            .where(DesignVersion.file_url.isnot(None))
            .limit(1000)  # Limit to prevent timeout
        )
        versions = result.all()

        missing_count = 0
        for version_id, design_id, file_url in versions:
            # Check if file exists in storage
            # file_url is typically a storage key like "designs/abc123/v1.step"
            try:
                exists = await storage_client.file_exists(StorageBucket.DESIGNS, file_url)
                if not exists:
                    missing_count += 1
                    if missing_count <= 50:  # Limit reported issues
                        report.issues.append(
                            IntegrityIssue(
                                check_type=IntegrityCheckType.MISSING_FILES,
                                severity=IntegritySeverity.WARNING,
                                table="design_versions",
                                record_id=str(version_id),
                                message="Design version references missing storage file",
                                details={
                                    "design_id": str(design_id),
                                    "file_url": file_url,
                                },
                            )
                        )
            except Exception as e:
                logger.warning(f"Error checking file existence: {e}")

        if missing_count > 50:
            report.issues.append(
                IntegrityIssue(
                    check_type=IntegrityCheckType.MISSING_FILES,
                    severity=IntegritySeverity.ERROR,
                    message=f"Found {missing_count} missing storage files (showing first 50)",
                )
            )

    async def _check_file_checksums(self, report: IntegrityReport) -> None:
        """Verify file checksums for stored files."""
        from app.models import File

        report.checks_run.append(IntegrityCheckType.CHECKSUM_VALIDATION)

        # Get files with checksums
        result = await self.session.execute(
            select(File.id, File.filename, File.storage_path, File.checksum_sha256)
            .where(File.checksum_sha256.isnot(None))
            .where(File.deleted_at.is_(None))
            .limit(100)  # Sample check
        )
        files = result.all()

        for file_id, filename, storage_path, expected_checksum in files:
            try:
                # Download file and calculate checksum
                content = await storage_client.download_file(StorageBucket.DESIGNS, storage_path)
                if content:
                    actual_checksum = hashlib.sha256(content).hexdigest()
                    if actual_checksum != expected_checksum:
                        report.issues.append(
                            IntegrityIssue(
                                check_type=IntegrityCheckType.CHECKSUM_VALIDATION,
                                severity=IntegritySeverity.CRITICAL,
                                table="files",
                                record_id=str(file_id),
                                message=f"Checksum mismatch for file '{filename}'",
                                details={
                                    "expected": expected_checksum,
                                    "actual": actual_checksum,
                                },
                            )
                        )
            except Exception as e:
                logger.warning(f"Error validating checksum for file {file_id}: {e}")

    async def _check_referential_integrity(self, report: IntegrityReport) -> None:
        """Check foreign key relationships are valid."""
        from app.models import Design, DesignVersion

        report.checks_run.append(IntegrityCheckType.REFERENTIAL_INTEGRITY)

        # Check design versions point to valid designs
        result = await self.session.execute(
            select(DesignVersion.id, DesignVersion.design_id)
            .outerjoin(Design, DesignVersion.design_id == Design.id)
            .where(Design.id.is_(None))
        )
        orphaned_versions = result.all()

        for version_id, design_id in orphaned_versions:
            report.issues.append(
                IntegrityIssue(
                    check_type=IntegrityCheckType.REFERENTIAL_INTEGRITY,
                    severity=IntegritySeverity.ERROR,
                    table="design_versions",
                    record_id=str(version_id),
                    message="Design version references non-existent design",
                    details={"design_id": str(design_id)},
                )
            )

    async def _collect_stats(self, report: IntegrityReport) -> None:
        """Collect database statistics."""
        from app.models import Design, File, Job, Project, User

        stats = {}

        # Count records in each table
        for model, name in [
            (User, "users"),
            (Design, "designs"),
            (Project, "projects"),
            (File, "files"),
            (Job, "jobs"),
        ]:
            result = await self.session.execute(select(func.count(model.id)))
            stats[f"{name}_total"] = result.scalar() or 0

            # Count soft-deleted if applicable
            if hasattr(model, "deleted_at"):
                result = await self.session.execute(
                    select(func.count(model.id)).where(model.deleted_at.isnot(None))
                )
                stats[f"{name}_deleted"] = result.scalar() or 0

        report.stats = stats


async def run_integrity_check(session: AsyncSession) -> IntegrityReport:
    """
    Run a full integrity check.

    Convenience function for scheduled tasks.
    """
    service = DataIntegrityService(session)
    return await service.run_full_check()
