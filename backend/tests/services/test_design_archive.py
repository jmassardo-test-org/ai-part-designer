"""
Tests for DesignArchiveService.

Tests archiving, restoring, deleting, and listing archived designs
with mocked storage dependencies.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from sqlalchemy import select
from tests.factories import Counter, DesignFactory, ProjectFactory, UserFactory

from app.models.design import Design
from app.services.design_archive import DesignArchiveService

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


@pytest.fixture(autouse=True)
def reset_counters():
    """Reset factory counters before each test."""
    Counter.reset()


@pytest.mark.asyncio
class TestDesignArchiveService:
    """Tests for the DesignArchiveService."""

    async def test_archive_design_copies_files_to_archives_bucket(
        self, db_session: AsyncSession
    ) -> None:
        """Test that archiving a design copies files to ARCHIVES bucket."""
        design = await DesignFactory.create(db_session, status="ready")

        with patch("app.services.design_archive.storage_client") as mock_storage:
            mock_storage.list_files = AsyncMock(
                return_value=[
                    {"key": f"{design.id}/model.stl", "size": 1024},
                ]
            )
            mock_storage.copy_file = AsyncMock()
            mock_storage.upload_file = AsyncMock()

            service = DesignArchiveService(db_session)
            await service.archive_design(design)

            # Verify copy_file was called to copy from DESIGNS to ARCHIVES
            from app.core.storage import StorageBucket

            mock_storage.copy_file.assert_called_once()
            call_kwargs = mock_storage.copy_file.call_args[1]
            assert call_kwargs["source_bucket"] == StorageBucket.DESIGNS
            assert call_kwargs["dest_bucket"] == StorageBucket.ARCHIVES

    async def test_archive_design_sets_status_and_timestamps(
        self, db_session: AsyncSession
    ) -> None:
        """Test that archiving sets status to 'archived' and sets archived_at."""
        design = await DesignFactory.create(db_session, status="ready")

        with patch("app.services.design_archive.storage_client") as mock_storage:
            mock_storage.list_files = AsyncMock(return_value=[])
            mock_storage.upload_file = AsyncMock()

            service = DesignArchiveService(db_session)
            location = await service.archive_design(design)

            assert design.status == "archived"
            assert design.archived_at is not None
            assert design.archive_location == location

    async def test_archive_design_creates_metadata_json(self, db_session: AsyncSession) -> None:
        """Test that archiving creates a gzipped metadata JSON in storage."""
        design = await DesignFactory.create(db_session, status="ready")

        with patch("app.services.design_archive.storage_client") as mock_storage:
            mock_storage.list_files = AsyncMock(return_value=[])
            mock_storage.upload_file = AsyncMock()

            service = DesignArchiveService(db_session)
            await service.archive_design(design)

            # Verify upload_file was called with gzip content type
            mock_storage.upload_file.assert_called_once()
            call_kwargs = mock_storage.upload_file.call_args[1]
            assert call_kwargs["content_type"] == "application/gzip"
            assert "metadata.json.gz" in call_kwargs["key"]

    async def test_archive_design_with_no_files_handles_gracefully(
        self, db_session: AsyncSession
    ) -> None:
        """Test that archiving design with no files doesn't raise errors."""
        design = await DesignFactory.create(db_session, status="ready")

        with patch("app.services.design_archive.storage_client") as mock_storage:
            mock_storage.list_files = AsyncMock(return_value=[])
            mock_storage.upload_file = AsyncMock()

            service = DesignArchiveService(db_session)
            location = await service.archive_design(design)

            assert location is not None
            assert design.status == "archived"
            # copy_file should not have been called
            mock_storage.copy_file.assert_not_called()

    async def test_restore_design_copies_files_back(self, db_session: AsyncSession) -> None:
        """Test that restoring copies files from ARCHIVES back to DESIGNS."""
        design = await DesignFactory.create(
            db_session,
            status="archived",
            archived_at=datetime.now(tz=UTC),
            archive_location="designs/test/20260224_100000",
        )

        with patch("app.services.design_archive.storage_client") as mock_storage:
            mock_storage.list_files = AsyncMock(
                return_value=[
                    {"key": "designs/test/20260224_100000/files/model.stl", "size": 1024},
                ]
            )
            mock_storage.copy_file = AsyncMock()

            service = DesignArchiveService(db_session)
            restored = await service.restore_design(design.id)

            from app.core.storage import StorageBucket

            mock_storage.copy_file.assert_called_once()
            call_kwargs = mock_storage.copy_file.call_args[1]
            assert call_kwargs["source_bucket"] == StorageBucket.ARCHIVES
            assert call_kwargs["dest_bucket"] == StorageBucket.DESIGNS
            assert restored.status == "ready"

    async def test_restore_design_clears_archive_fields(self, db_session: AsyncSession) -> None:
        """Test that restoring clears archived_at and archive_location."""
        design = await DesignFactory.create(
            db_session,
            status="archived",
            archived_at=datetime.now(tz=UTC),
            archive_location="designs/test/20260224_100000",
        )

        with patch("app.services.design_archive.storage_client") as mock_storage:
            mock_storage.list_files = AsyncMock(return_value=[])
            mock_storage.copy_file = AsyncMock()

            service = DesignArchiveService(db_session)
            restored = await service.restore_design(design.id)

            assert restored.archived_at is None
            assert restored.archive_location is None
            assert restored.status == "ready"

    async def test_restore_design_not_found_raises_error(self, db_session: AsyncSession) -> None:
        """Test that restoring a non-existent design raises ValueError."""
        service = DesignArchiveService(db_session)

        with pytest.raises(ValueError, match="not found"):
            await service.restore_design(uuid4())

    async def test_restore_non_archived_design_raises_error(self, db_session: AsyncSession) -> None:
        """Test that restoring a non-archived design raises ValueError."""
        design = await DesignFactory.create(db_session, status="ready")

        service = DesignArchiveService(db_session)

        with pytest.raises(ValueError, match="is not archived"):
            await service.restore_design(design.id)

    async def test_delete_archived_design_removes_files_and_record(
        self, db_session: AsyncSession
    ) -> None:
        """Test that deleting an archived design removes storage files and DB record."""
        design = await DesignFactory.create(
            db_session,
            status="archived",
            archived_at=datetime.now(tz=UTC),
            archive_location="designs/test/20260224_100000",
        )
        design_id = design.id

        with patch("app.services.design_archive.storage_client") as mock_storage:
            mock_storage.list_files = AsyncMock(
                return_value=[
                    {"key": "designs/test/20260224_100000/metadata.json.gz", "size": 512},
                ]
            )
            mock_storage.delete_files = AsyncMock(return_value=1)

            service = DesignArchiveService(db_session)
            await service.delete_archived_design(design_id)

            # Verify DB record is gone
            result = await db_session.execute(select(Design).where(Design.id == design_id))
            assert result.scalar_one_or_none() is None

            # Verify storage files were deleted
            mock_storage.delete_files.assert_called_once()

    async def test_delete_non_archived_design_raises_error(self, db_session: AsyncSession) -> None:
        """Test that deleting a non-archived design raises ValueError."""
        design = await DesignFactory.create(db_session, status="ready")

        service = DesignArchiveService(db_session)

        with pytest.raises(ValueError, match="is not archived"):
            await service.delete_archived_design(design.id)

    async def test_list_archived_designs_with_pagination(self, db_session: AsyncSession) -> None:
        """Test that listing archived designs returns paginated results."""
        user = await UserFactory.create(db_session)
        project = await ProjectFactory.create(db_session, user=user)

        # Create 5 archived designs
        for i in range(5):
            await DesignFactory.create(
                db_session,
                user=user,
                project=project,
                status="archived",
                archived_at=datetime.now(tz=UTC) - timedelta(hours=i),
                archive_location=f"designs/test/{i}",
            )

        service = DesignArchiveService(db_session)
        designs, total = await service.list_archived_designs(page=1, per_page=3)

        assert total == 5
        assert len(designs) == 3

        # Get page 2
        designs_p2, total_p2 = await service.list_archived_designs(page=2, per_page=3)
        assert total_p2 == 5
        assert len(designs_p2) == 2

    async def test_find_archivable_designs_respects_age_threshold(
        self, db_session: AsyncSession
    ) -> None:
        """Test that only designs older than threshold are returned."""
        user = await UserFactory.create(db_session)
        project = await ProjectFactory.create(db_session, user=user)

        # Old design (should be found)
        old_design = await DesignFactory.create(
            db_session, user=user, project=project, status="ready"
        )
        # Manually set updated_at to 400 days ago
        old_design.updated_at = datetime.now(tz=UTC) - timedelta(days=400)
        await db_session.commit()

        service = DesignArchiveService(db_session)
        designs = await service.find_archivable_designs(days_inactive=365)

        assert len(designs) == 1
        assert designs[0].id == old_design.id

    async def test_find_archivable_designs_excludes_recently_updated(
        self, db_session: AsyncSession
    ) -> None:
        """Test that recently updated designs are not returned."""
        user = await UserFactory.create(db_session)
        project = await ProjectFactory.create(db_session, user=user)

        # Recent design (should NOT be found)
        await DesignFactory.create(db_session, user=user, project=project, status="ready")

        service = DesignArchiveService(db_session)
        designs = await service.find_archivable_designs(days_inactive=365)

        assert len(designs) == 0

    async def test_find_archivable_designs_excludes_already_archived(
        self, db_session: AsyncSession
    ) -> None:
        """Test that already-archived designs are excluded."""
        user = await UserFactory.create(db_session)
        project = await ProjectFactory.create(db_session, user=user)

        # Already archived design
        archived = await DesignFactory.create(
            db_session,
            user=user,
            project=project,
            status="archived",
            archived_at=datetime.now(tz=UTC),
            archive_location="designs/test/old",
        )
        archived.updated_at = datetime.now(tz=UTC) - timedelta(days=400)
        await db_session.commit()

        service = DesignArchiveService(db_session)
        designs = await service.find_archivable_designs(days_inactive=365)

        assert len(designs) == 0
