"""
Design management service.

Handles design operations including copy, move, delete with undo,
and lifecycle management.
"""

import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.design import Design, DesignVersion
from app.models.project import Project
from app.models.user import User
from app.services.storage_service import StorageService, get_storage_service

logger = logging.getLogger(__name__)


# =============================================================================
# Exceptions
# =============================================================================


class DesignServiceError(Exception):
    """Base exception for design service errors."""


class DesignNotFoundError(DesignServiceError):
    """Design not found."""


class DesignPermissionError(DesignServiceError):
    """User does not have permission for this operation."""


class DesignCopyError(DesignServiceError):
    """Error during copy operation."""


class ProjectNotFoundError(DesignServiceError):
    """Target project not found."""


class UndoTokenExpiredError(DesignServiceError):
    """Undo token has expired."""


# =============================================================================
# Data Classes
# =============================================================================


@dataclass
class CopyResult:
    """Result of a copy operation."""

    design: Design
    versions_copied: int
    files_copied: int


@dataclass
class DeleteResult:
    """Result of a delete operation with undo support."""

    design_id: UUID
    undo_token: str
    expires_at: datetime


# =============================================================================
# Design Service
# =============================================================================


class DesignService:
    """
    Service for managing design lifecycle operations.

    Provides high-level operations for:
    - Copying designs (with or without version history)
    - Moving designs between projects
    - Deleting designs with undo support
    - Managing design versions
    """

    UNDO_TTL_SECONDS = 30  # Time window for undo operations

    def __init__(
        self,
        db: AsyncSession,
        storage: StorageService | None = None,
    ):
        """
        Initialize the design service.

        Args:
            db: Database session
            storage: Storage service for file operations (optional)
        """
        self.db = db
        self.storage = storage or get_storage_service()

    # =========================================================================
    # Copy Operations
    # =========================================================================

    async def copy_design(
        self,
        design_id: UUID,
        user: User,
        name: str,
        target_project_id: UUID | None = None,
        include_versions: bool = False,
    ) -> CopyResult:
        """
        Create a copy of a design.

        Args:
            design_id: Source design ID
            user: User performing the copy
            name: Name for the new design
            target_project_id: Target project (default: same project)
            include_versions: Copy all versions or just current

        Returns:
            CopyResult with new design and stats

        Raises:
            DesignNotFoundError: Source design not found
            DesignPermissionError: User cannot access source
            ProjectNotFoundError: Target project not found
            DesignCopyError: Copy operation failed
        """
        # Load source design with ownership check
        source = await self._get_design_with_access(design_id, user)

        # Validate target project
        project_id = target_project_id or source.project_id
        target_project = await self._validate_project_access(project_id, user)

        logger.info(f"Copying design {design_id} to project {target_project.id} for user {user.id}")

        try:
            # Create new design record
            new_design = Design(
                id=uuid4(),
                project_id=target_project.id,
                user_id=user.id,
                name=name,
                description=source.description,
                source_type="copied",
                status=source.status if source.status == "ready" else "draft",
                extra_data=source.extra_data.copy() if source.extra_data else {},
                tags=source.tags.copy() if source.tags else [],
                copied_from_id=source.id,
                enclosure_spec=source.enclosure_spec,
                is_public=False,  # Copies are always private
            )

            self.db.add(new_design)
            await self.db.flush()

            # Copy files and versions
            files_copied = 0
            versions_copied = 0

            if include_versions:
                # Copy all versions
                versions = await self._get_all_versions(source.id)
                for version in versions:
                    new_version = await self._copy_version(version, new_design.id, user.id)
                    versions_copied += 1
                    files_copied += len(version.file_formats) if version.file_formats else 0

                    # Set current version if this was the source's current
                    if source.current_version_id and version.id == source.current_version_id:
                        new_design.current_version_id = new_version.id
            else:
                # Copy only current version
                if source.current_version_id:
                    current = await self._get_version(source.current_version_id)
                    if current:
                        new_version = await self._copy_version(
                            current, new_design.id, user.id, version_number=1
                        )
                        new_design.current_version_id = new_version.id
                        versions_copied = 1
                        files_copied = len(current.file_formats) if current.file_formats else 0

            await self.db.commit()
            await self.db.refresh(new_design)

            logger.info(
                f"Design copied successfully: {new_design.id} "
                f"({versions_copied} versions, {files_copied} files)"
            )

            return CopyResult(
                design=new_design,
                versions_copied=versions_copied,
                files_copied=files_copied,
            )

        except Exception as e:
            logger.error(f"Failed to copy design {design_id}: {e}")
            await self.db.rollback()
            raise DesignCopyError(f"Failed to copy design: {e}") from e

    async def _copy_version(
        self,
        source: DesignVersion,
        new_design_id: UUID,
        user_id: UUID,
        version_number: int | None = None,
    ) -> DesignVersion:
        """Copy a version including its files."""
        new_file_formats = {}
        new_file_url = source.file_url
        new_thumbnail_url = source.thumbnail_url

        # Copy files in storage (if storage service available and files exist)
        if source.file_formats:
            for format_name, url in source.file_formats.items():
                if url:
                    try:
                        new_url = await self.storage.copy_file(
                            source_url=url,
                            target_prefix=f"users/{user_id}/designs/{new_design_id}",
                        )
                        new_file_formats[format_name] = new_url
                        if format_name in ("step", "stl") and not new_file_url:
                            new_file_url = new_url
                    except Exception as e:
                        logger.warning(f"Failed to copy file {url}: {e}")
                        new_file_formats[format_name] = url  # Keep original URL

        # Copy thumbnail
        if source.thumbnail_url:
            try:
                new_thumbnail_url = await self.storage.copy_file(
                    source_url=source.thumbnail_url,
                    target_prefix=f"users/{user_id}/designs/{new_design_id}",
                )
            except Exception as e:
                logger.warning(f"Failed to copy thumbnail: {e}")
                new_thumbnail_url = source.thumbnail_url  # Keep original

        # Create new version record
        new_version = DesignVersion(
            id=uuid4(),
            design_id=new_design_id,
            version_number=version_number or source.version_number,
            file_url=new_file_url or "",
            thumbnail_url=new_thumbnail_url,
            file_formats=new_file_formats or source.file_formats or {},
            parameters=source.parameters.copy() if source.parameters else {},
            geometry_info=source.geometry_info.copy() if source.geometry_info else {},
            change_description="Copied from original",
            created_by=user_id,
        )

        self.db.add(new_version)
        return new_version

    # =========================================================================
    # Move Operations
    # =========================================================================

    async def move_design(
        self,
        design_id: UUID,
        target_project_id: UUID,
        user: User,
    ) -> Design:
        """
        Move a design to a different project.

        Args:
            design_id: Design to move
            target_project_id: Target project ID
            user: User performing the move

        Returns:
            Updated design

        Raises:
            DesignNotFoundError: Design not found
            DesignPermissionError: User cannot access design or project
            ProjectNotFoundError: Target project not found
        """
        design = await self._get_design_with_access(design_id, user)
        target_project = await self._validate_project_access(target_project_id, user)

        old_project_id = design.project_id
        design.project_id = target_project.id
        design.updated_at = datetime.now(UTC)

        await self.db.commit()
        await self.db.refresh(design)

        logger.info(
            f"Design {design_id} moved from project {old_project_id} "
            f"to {target_project_id} by user {user.id}"
        )

        return design

    # =========================================================================
    # Delete Operations with Undo
    # =========================================================================

    async def delete_design(
        self,
        design_id: UUID,
        user: User,
    ) -> DeleteResult:
        """
        Soft delete a design with undo support.

        The design is marked as deleted but can be restored within
        UNDO_TTL_SECONDS by using the returned undo token.

        Args:
            design_id: Design to delete
            user: User performing the delete

        Returns:
            DeleteResult with undo token

        Raises:
            DesignNotFoundError: Design not found
            DesignPermissionError: User cannot delete this design
        """
        from app.core.undo_tokens import store_undo_token, store_undo_token_fallback

        design = await self._get_design_with_access(design_id, user)

        # Soft delete
        design.deleted_at = datetime.now(UTC)
        await self.db.commit()

        # Store undo token in Redis (with fallback to in-memory)
        try:
            undo_data = await store_undo_token(
                design_id=design_id,
                user_id=user.id,
                operation="delete",
                ttl_seconds=self.UNDO_TTL_SECONDS,
                metadata={"design_name": design.name},
            )
        except Exception as e:
            logger.warning(f"Redis unavailable, using fallback: {e}")
            undo_data = await store_undo_token_fallback(
                design_id=design_id,
                user_id=user.id,
                operation="delete",
                ttl_seconds=self.UNDO_TTL_SECONDS,
                metadata={"design_name": design.name},
            )

        logger.info(f"Design {design_id} soft deleted by user {user.id}")

        return DeleteResult(
            design_id=design_id,
            undo_token=undo_data.token,
            expires_at=undo_data.expires_at,
        )

    async def undo_delete(
        self,
        undo_token: str,
        user: User,
    ) -> Design:
        """
        Restore a recently deleted design.

        Args:
            undo_token: Token from delete operation
            user: User performing the undo

        Returns:
            Restored design

        Raises:
            UndoTokenExpiredError: Token expired or invalid
            DesignPermissionError: User doesn't own this undo token
        """
        from app.core.undo_tokens import (
            get_undo_token_fallback,
            invalidate_undo_token,
            validate_undo_token,
        )

        # Try Redis first, then fallback
        token_data = await validate_undo_token(undo_token, user.id)

        if not token_data:
            # Try fallback storage
            fallback_data = get_undo_token_fallback(undo_token)
            if fallback_data and fallback_data.user_id == user.id:
                token_data = fallback_data
            else:
                raise UndoTokenExpiredError("Invalid or expired undo token")

        design_id = token_data.design_id

        # Find the deleted design (including soft-deleted)
        # SECURITY: Also verify user_id matches to prevent IDOR even with valid token
        query = (
            select(Design)
            .where(Design.id == design_id)
            .where(Design.user_id == user.id)  # Ownership check
        )
        result = await self.db.execute(query)
        design = result.scalar_one_or_none()

        if not design:
            # Use generic message to prevent information disclosure
            raise UndoTokenExpiredError("Invalid or expired undo token")

        # Restore
        design.deleted_at = None
        design.updated_at = datetime.now(UTC)
        await self.db.commit()
        await self.db.refresh(design)

        # Invalidate the token
        await invalidate_undo_token(undo_token)

        logger.info(f"Design {design_id} restored by user {user.id}")

        return design

    # =========================================================================
    # Version Operations
    # =========================================================================

    async def list_versions(
        self,
        design_id: UUID,
        user: User,
        page: int = 1,
        per_page: int = 20,
    ) -> tuple[list[DesignVersion], int]:
        """
        List versions for a design.

        Args:
            design_id: Design ID
            user: User requesting versions
            page: Page number (1-indexed)
            per_page: Items per page

        Returns:
            Tuple of (versions list, total count)
        """
        # Verify access
        await self._get_design_with_access(design_id, user)

        # Count total
        count_query = select(func.count()).where(DesignVersion.design_id == design_id)
        total = (await self.db.execute(count_query)).scalar() or 0

        # Fetch page
        query = (
            select(DesignVersion)
            .where(DesignVersion.design_id == design_id)
            .order_by(DesignVersion.version_number.desc())
            .offset((page - 1) * per_page)
            .limit(per_page)
        )
        result = await self.db.execute(query)
        versions = list(result.scalars().all())

        return versions, total

    async def create_version(
        self,
        design_id: UUID,
        user: User,
        change_description: str | None = None,
    ) -> DesignVersion:
        """
        Create a new version snapshot of a design.

        Args:
            design_id: Design ID
            user: User creating the version
            change_description: Description of changes

        Returns:
            New version
        """
        design = await self._get_design_with_access(design_id, user)

        # Get current version to copy from
        current = None
        if design.current_version_id:
            current = await self._get_version(design.current_version_id)

        # Determine next version number
        next_number = await self._get_next_version_number(design_id)

        # Create new version
        new_version = DesignVersion(
            id=uuid4(),
            design_id=design_id,
            version_number=next_number,
            file_url=current.file_url if current else "",
            thumbnail_url=current.thumbnail_url if current else None,
            file_formats=current.file_formats.copy() if current and current.file_formats else {},
            parameters=design.extra_data.get("parameters", {}) if design.extra_data else {},
            geometry_info=current.geometry_info.copy() if current and current.geometry_info else {},
            change_description=change_description or "Manual snapshot",
            created_by=user.id,
        )

        self.db.add(new_version)

        # Update design's current version
        design.current_version_id = new_version.id
        design.updated_at = datetime.now(UTC)

        await self.db.commit()
        await self.db.refresh(new_version)

        logger.info(f"Created version {next_number} for design {design_id}")

        return new_version

    async def restore_version(
        self,
        design_id: UUID,
        version_id: UUID,
        user: User,
    ) -> Design:
        """
        Restore a design to a previous version.

        Creates a new version with the restored state (preserves history).

        Args:
            design_id: Design ID
            version_id: Version ID to restore
            user: User performing restore

        Returns:
            Updated design
        """
        design = await self._get_design_with_access(design_id, user)
        target_version = await self._get_version(version_id)

        if not target_version or target_version.design_id != design_id:
            raise DesignNotFoundError("Version not found for this design")

        # Create new version from target state
        next_number = await self._get_next_version_number(design_id)

        restored_version = DesignVersion(
            id=uuid4(),
            design_id=design_id,
            version_number=next_number,
            file_url=target_version.file_url,
            thumbnail_url=target_version.thumbnail_url,
            file_formats=target_version.file_formats.copy() if target_version.file_formats else {},
            parameters=target_version.parameters.copy() if target_version.parameters else {},
            geometry_info=target_version.geometry_info.copy()
            if target_version.geometry_info
            else {},
            change_description=f"Restored from v{target_version.version_number}",
            created_by=user.id,
        )

        self.db.add(restored_version)

        # Update design state
        design.current_version_id = restored_version.id
        if target_version.parameters:
            if design.extra_data is None:
                design.extra_data = {}
            design.extra_data["parameters"] = target_version.parameters.copy()
        design.updated_at = datetime.now(UTC)

        await self.db.commit()
        await self.db.refresh(design)

        logger.info(
            f"Design {design_id} restored to version {target_version.version_number} "
            f"by user {user.id}"
        )

        return design

    # =========================================================================
    # Edit / Save-as-Version Operations
    # =========================================================================

    async def save_edit_as_version(
        self,
        design_id: UUID,
        user: User,
        job_id: str,
        change_description: str,
        parameters: dict[str, Any] | None = None,
        file_url: str | None = None,
    ) -> DesignVersion:
        """
        Save an edited design as a new version.

        Creates a new version from externally-provided data (e.g. after
        re-compiling an enclosure with modified dimensions).

        Args:
            design_id: ID of the design being edited.
            user: User performing the edit.
            job_id: Compile job ID that produced the new geometry.
            change_description: Human-readable description of changes.
            parameters: Optional parameter dict for the new version.
            file_url: Optional explicit file URL.  Falls back to job-based URL.

        Returns:
            Newly created DesignVersion.

        Raises:
            DesignNotFoundError: Design not found or deleted.
            DesignPermissionError: User cannot access design.
        """
        design = await self._get_design_with_access(design_id, user)

        # Determine next version number
        next_number = await self._get_next_version_number(design_id)

        resolved_file_url = file_url or f"/api/v2/generate/download/{job_id}/enclosure.stl"

        new_version = DesignVersion(
            id=uuid4(),
            design_id=design_id,
            version_number=next_number,
            file_url=resolved_file_url,
            file_formats={
                "stl": f"/api/v2/generate/download/{job_id}/enclosure.stl",
                "step": f"/api/v2/generate/download/{job_id}/enclosure.step",
            },
            parameters=parameters or {},
            geometry_info={},
            change_description=change_description or "Edited via part editor",
            created_by=user.id,
        )

        self.db.add(new_version)

        # Update design's current version and extra_data
        design.current_version_id = new_version.id
        if design.extra_data is None:
            design.extra_data = {}
        design.extra_data["job_id"] = job_id
        if parameters:
            design.extra_data["parameters"] = parameters
        design.updated_at = datetime.now(UTC)

        await self.db.commit()
        await self.db.refresh(new_version)

        logger.info(
            f"Created edit version {next_number} for design {design_id} "
            f"(job {job_id}) by user {user.id}"
        )

        return new_version

    # =========================================================================
    # Helper Methods
    # =========================================================================

    async def _get_design_with_access(
        self,
        design_id: UUID,
        user: User,
    ) -> Design:
        """Get a design and verify user has access."""
        query = select(Design).where(Design.id == design_id).where(Design.deleted_at.is_(None))
        result = await self.db.execute(query)
        design = result.scalar_one_or_none()

        if not design:
            raise DesignNotFoundError(f"Design {design_id} not found")

        # Check ownership (or admin)
        if design.user_id != user.id and user.role not in ("admin", "super_admin"):
            # TODO: Check share permissions
            raise DesignPermissionError("Access denied to this design")

        return design

    async def _validate_project_access(
        self,
        project_id: UUID,
        user: User,
    ) -> Project:
        """Validate user has access to a project."""
        query = select(Project).where(Project.id == project_id).where(Project.deleted_at.is_(None))
        result = await self.db.execute(query)
        project = result.scalar_one_or_none()

        if not project:
            raise ProjectNotFoundError(f"Project {project_id} not found")

        if project.user_id != user.id and user.role not in ("admin", "super_admin"):
            raise DesignPermissionError("Access denied to this project")

        return project

    async def _get_version(self, version_id: UUID) -> DesignVersion | None:
        """Get a version by ID."""
        query = select(DesignVersion).where(DesignVersion.id == version_id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def _get_all_versions(self, design_id: UUID) -> list[DesignVersion]:
        """Get all versions for a design."""
        query = (
            select(DesignVersion)
            .where(DesignVersion.design_id == design_id)
            .order_by(DesignVersion.version_number.asc())
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def _get_next_version_number(self, design_id: UUID) -> int:
        """Get the next version number for a design."""
        query = select(func.max(DesignVersion.version_number)).where(
            DesignVersion.design_id == design_id
        )
        result = await self.db.execute(query)
        max_version = result.scalar() or 0
        return max_version + 1
