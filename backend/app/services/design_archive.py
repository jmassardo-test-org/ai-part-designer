"""
Design Archive Service.

Handles archiving inactive designs to cold storage, restoring
archived designs, and managing archived design lifecycle.
"""

import gzip
import json
import logging
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.storage import StorageBucket, storage_client
from app.models.design import Design

logger = logging.getLogger(__name__)


class DesignArchiveService:
    """Service for archiving inactive designs to cold storage."""

    def __init__(self, db: AsyncSession) -> None:
        """Initialize the archive service.

        Args:
            db: Async database session for queries and mutations.
        """
        self.db = db

    async def find_archivable_designs(
        self,
        days_inactive: int = 365,
        limit: int = 100,
    ) -> list[Design]:
        """Find designs that haven't been updated in `days_inactive` days.

        Only considers designs that are not already archived, not deleted,
        and whose last update is older than the threshold.

        Args:
            days_inactive: Number of days of inactivity before eligible.
            limit: Maximum number of designs to return.

        Returns:
            List of designs eligible for archival.
        """
        cutoff = datetime.now(tz=UTC) - timedelta(days=days_inactive)

        result = await self.db.execute(
            select(Design)
            .where(
                Design.updated_at < cutoff,
                Design.archived_at.is_(None),
                Design.deleted_at.is_(None),
                Design.status != "archived",
            )
            .order_by(Design.updated_at.asc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def archive_design(self, design: Design) -> str:
        """Archive a design's files to cold storage.

        Copies design files from DESIGNS bucket to ARCHIVES bucket,
        serializes metadata to compressed JSON, and updates the
        design status.

        Args:
            design: The design to archive.

        Returns:
            The archive location key in storage.

        Raises:
            ValueError: If design is already archived.
        """
        if design.archived_at is not None:
            raise ValueError(f"Design {design.id} is already archived")

        archive_timestamp = datetime.now(tz=UTC).strftime("%Y%m%d_%H%M%S")
        archive_prefix = f"designs/{design.id}/{archive_timestamp}"

        # 1. Copy design files from DESIGNS bucket to ARCHIVES bucket
        try:
            files = await storage_client.list_files(
                StorageBucket.DESIGNS,
                prefix=str(design.id),
            )
            for file_info in files:
                source_key = file_info["key"]
                dest_key = f"{archive_prefix}/files/{source_key}"
                await storage_client.copy_file(
                    source_bucket=StorageBucket.DESIGNS,
                    source_key=source_key,
                    dest_bucket=StorageBucket.ARCHIVES,
                    dest_key=dest_key,
                )
        except Exception as e:
            logger.warning(f"Could not copy files for design {design.id}: {e}")

        # 2. Serialize design metadata to JSON, gzip, upload to ARCHIVES
        metadata = {
            "id": str(design.id),
            "name": design.name,
            "description": design.description,
            "status": design.status,
            "source_type": design.source_type,
            "user_id": str(design.user_id),
            "project_id": str(design.project_id),
            "extra_data": design.extra_data,
            "tags": design.tags,
            "created_at": design.created_at.isoformat() if design.created_at else None,
            "updated_at": design.updated_at.isoformat() if design.updated_at else None,
            "archived_at": datetime.now(tz=UTC).isoformat(),
        }

        json_data = json.dumps(metadata, indent=2, default=str)
        compressed = gzip.compress(json_data.encode("utf-8"))

        metadata_key = f"{archive_prefix}/metadata.json.gz"
        await storage_client.upload_file(
            bucket=StorageBucket.ARCHIVES,
            key=metadata_key,
            file=compressed,
            content_type="application/gzip",
            metadata={
                "design_id": str(design.id),
                "design_name": design.name,
                "archived_at": archive_timestamp,
            },
        )

        # 3. Update design record
        design.status = "archived"
        design.archived_at = datetime.now(tz=UTC)
        design.archive_location = archive_prefix

        # 4. Commit
        await self.db.commit()
        await self.db.refresh(design)

        logger.info(
            f"Archived design {design.id} to {archive_prefix}",
            extra={
                "design_id": str(design.id),
                "archive_location": archive_prefix,
            },
        )

        return archive_prefix

    async def restore_design(self, design_id: UUID) -> Design:
        """Restore an archived design from cold storage.

        Copies files back from ARCHIVES to DESIGNS bucket and
        resets the design status to 'ready'.

        Args:
            design_id: ID of the design to restore.

        Returns:
            The restored design.

        Raises:
            ValueError: If design not found or not archived.
        """
        result = await self.db.execute(select(Design).where(Design.id == design_id))
        design = result.scalar_one_or_none()

        if design is None:
            raise ValueError(f"Design {design_id} not found")

        if design.archived_at is None or design.status != "archived":
            raise ValueError(f"Design {design_id} is not archived")

        archive_prefix = design.archive_location

        # 1. Copy files back from ARCHIVES to DESIGNS bucket
        if archive_prefix:
            try:
                files = await storage_client.list_files(
                    StorageBucket.ARCHIVES,
                    prefix=f"{archive_prefix}/files/",
                )
                for file_info in files:
                    source_key = file_info["key"]
                    # Strip the archive prefix/files/ to get original key
                    original_key = source_key.replace(f"{archive_prefix}/files/", "", 1)
                    await storage_client.copy_file(
                        source_bucket=StorageBucket.ARCHIVES,
                        source_key=source_key,
                        dest_bucket=StorageBucket.DESIGNS,
                        dest_key=original_key,
                    )
            except Exception as e:
                logger.warning(f"Could not restore files for design {design_id}: {e}")

        # 2. Update design record
        design.status = "ready"
        design.archived_at = None
        design.archive_location = None

        await self.db.commit()
        await self.db.refresh(design)

        logger.info(
            f"Restored design {design_id} from archive",
            extra={"design_id": str(design_id)},
        )

        return design

    async def delete_archived_design(self, design_id: UUID) -> None:
        """Permanently delete an archived design and its storage files.

        Removes both the archive files in storage and the database record.

        Args:
            design_id: ID of the archived design to delete.

        Raises:
            ValueError: If design not found or not archived.
        """
        result = await self.db.execute(select(Design).where(Design.id == design_id))
        design = result.scalar_one_or_none()

        if design is None:
            raise ValueError(f"Design {design_id} not found")

        if design.archived_at is None or design.status != "archived":
            raise ValueError(f"Design {design_id} is not archived")

        # Delete archive files from storage
        archive_prefix = design.archive_location
        if archive_prefix:
            try:
                files = await storage_client.list_files(
                    StorageBucket.ARCHIVES,
                    prefix=archive_prefix,
                )
                if files:
                    keys = [f["key"] for f in files]
                    await storage_client.delete_files(StorageBucket.ARCHIVES, keys)
            except Exception as e:
                logger.warning(f"Could not delete archive files for design {design_id}: {e}")

        # Delete the database record
        await self.db.delete(design)
        await self.db.commit()

        logger.info(
            f"Permanently deleted archived design {design_id}",
            extra={"design_id": str(design_id)},
        )

    async def list_archived_designs(
        self,
        page: int = 1,
        per_page: int = 20,
    ) -> tuple[list[Design], int]:
        """List archived designs with pagination.

        Args:
            page: Page number (1-indexed).
            per_page: Number of results per page.

        Returns:
            Tuple of (list of archived designs, total count).
        """
        # Get total count
        count_result = await self.db.execute(
            select(func.count(Design.id)).where(
                Design.archived_at.isnot(None),
                Design.status == "archived",
            )
        )
        total = count_result.scalar() or 0

        # Get paginated results
        offset = (page - 1) * per_page
        result = await self.db.execute(
            select(Design)
            .where(
                Design.archived_at.isnot(None),
                Design.status == "archived",
            )
            .order_by(Design.archived_at.desc())
            .offset(offset)
            .limit(per_page)
        )
        designs = list(result.scalars().all())

        return designs, total
