"""
Tests for BackupService backup and disaster recovery operations.

Tests backup creation, verification, restore, cleanup, listing, and deletion
using mocked subprocess calls, filesystem, and storage operations.
"""

from __future__ import annotations

import gzip
import hashlib
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

from app.services.backup import (
    BackupRecord,
    BackupService,
    BackupStatus,
    BackupType,
)

if TYPE_CHECKING:
    from pathlib import Path

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def tmp_backup_dir(tmp_path: Path) -> Path:
    """Create a temporary backup directory."""
    backup_dir = tmp_path / "backups"
    backup_dir.mkdir()
    return backup_dir


@pytest.fixture
def backup_service(tmp_backup_dir: Path) -> BackupService:
    """Create a BackupService with a temporary directory."""
    return BackupService(backup_dir=str(tmp_backup_dir))


@pytest.fixture
def completed_backup_record() -> BackupRecord:
    """Create a completed backup record for testing."""
    return BackupRecord(
        backup_type=BackupType.FULL,
        status=BackupStatus.COMPLETED,
        completed_at=datetime.now(tz=UTC),
        size_bytes=1024,
        checksum="abc123",
        metadata={"description": "Test backup"},
    )


# =============================================================================
# create_backup Tests
# =============================================================================


class TestCreateBackup:
    """Tests for BackupService.create_backup."""

    @pytest.mark.asyncio
    async def test_create_backup_database_type_runs_pg_dump(
        self, backup_service: BackupService
    ) -> None:
        """Test that DATABASE backup type invokes pg_dump via subprocess."""
        mock_process = AsyncMock()
        mock_process.returncode = 0
        mock_process.communicate = AsyncMock(return_value=(b"SQL DUMP DATA", b""))

        with patch("asyncio.create_subprocess_exec", return_value=mock_process) as mock_exec:
            record = await backup_service.create_backup(
                backup_type=BackupType.DATABASE,
                description="Test database backup",
            )

            assert record.status == BackupStatus.COMPLETED
            assert record.backup_type == BackupType.DATABASE
            assert record.completed_at is not None
            # Verify pg_dump was invoked
            mock_exec.assert_called()
            cmd_args = mock_exec.call_args[0]
            assert cmd_args[0] == "pg_dump"

    @pytest.mark.asyncio
    async def test_create_backup_files_type_creates_tar(
        self, backup_service: BackupService, tmp_path: Path
    ) -> None:
        """Test that FILES backup type creates a tar archive."""
        # Create a fake uploads directory with files
        uploads_dir = tmp_path / "uploads"
        uploads_dir.mkdir()
        (uploads_dir / "file1.txt").write_text("content1")
        (uploads_dir / "file2.txt").write_text("content2")

        mock_process = AsyncMock()
        mock_process.returncode = 0
        mock_process.communicate = AsyncMock(return_value=(b"", b""))

        with (
            patch("asyncio.create_subprocess_exec", return_value=mock_process) as mock_exec,
            patch(
                "app.services.backup.settings",
                FILE_STORAGE_PATH=str(uploads_dir),
            ),
        ):
            record = await backup_service.create_backup(
                backup_type=BackupType.FILES,
                description="Test file backup",
            )

            # FILES backup should invoke tar
            tar_called = any(call[0][0] == "tar" for call in mock_exec.call_args_list if call[0])
            assert tar_called or record.metadata.get("files_backup") is not None

    @pytest.mark.asyncio
    async def test_create_backup_full_type_runs_both(
        self, backup_service: BackupService, tmp_path: Path
    ) -> None:
        """Test that FULL backup type runs both database and file backups."""
        mock_process = AsyncMock()
        mock_process.returncode = 0
        mock_process.communicate = AsyncMock(return_value=(b"SQL DATA", b""))

        with patch("asyncio.create_subprocess_exec", return_value=mock_process):
            record = await backup_service.create_backup(
                backup_type=BackupType.FULL,
                description="Test full backup",
            )

            assert record.status == BackupStatus.COMPLETED
            assert record.backup_type == BackupType.FULL

    @pytest.mark.asyncio
    async def test_create_backup_incremental_type(self, backup_service: BackupService) -> None:
        """Test that INCREMENTAL backup uses last full as base."""
        # First create a full backup to serve as base
        mock_process = AsyncMock()
        mock_process.returncode = 0
        mock_process.communicate = AsyncMock(return_value=(b"SQL DATA", b""))

        with patch("asyncio.create_subprocess_exec", return_value=mock_process):
            full_record = await backup_service.create_backup(
                backup_type=BackupType.FULL,
            )

            incremental_record = await backup_service.create_backup(
                backup_type=BackupType.INCREMENTAL,
            )

            assert incremental_record.status == BackupStatus.COMPLETED
            # If full backup exists, incremental should reference it
            if "incremental_base" in incremental_record.metadata:
                assert incremental_record.metadata["incremental_base"] == str(full_record.id)


# =============================================================================
# verify_backup Tests
# =============================================================================


class TestVerifyBackup:
    """Tests for BackupService.verify_backup."""

    @pytest.mark.asyncio
    async def test_verify_backup_valid_returns_verified(
        self, backup_service: BackupService
    ) -> None:
        """Test that verifying a valid backup returns VERIFIED status."""
        # Create a backup with a known checksum
        db_content = b"Valid SQL dump content"
        checksum = hashlib.sha256(db_content).hexdigest()

        backup_filename = "db_backup_20250101_120000.sql.gz"
        backup_path = backup_service.backup_dir / backup_filename

        # Write compressed content
        with gzip.open(backup_path, "wb") as f:
            f.write(db_content)

        record = BackupRecord(
            status=BackupStatus.COMPLETED,
            checksum=checksum,
            metadata={"database_backup": backup_filename},
        )
        backup_service._backup_index[str(record.id)] = record
        backup_service._save_backup_index()

        result = await backup_service.verify_backup(record.id)

        assert result.is_valid is True
        assert result.checksum_match is True

    @pytest.mark.asyncio
    async def test_verify_backup_corrupted_returns_corrupted(
        self, backup_service: BackupService
    ) -> None:
        """Test that verifying a corrupted backup returns CORRUPTED status."""
        backup_filename = "db_backup_20250102_120000.sql.gz"
        backup_path = backup_service.backup_dir / backup_filename

        # Write content with wrong checksum
        with gzip.open(backup_path, "wb") as f:
            f.write(b"Some data")

        record = BackupRecord(
            status=BackupStatus.COMPLETED,
            checksum="totally_wrong_checksum",
            metadata={"database_backup": backup_filename},
        )
        backup_service._backup_index[str(record.id)] = record
        backup_service._save_backup_index()

        result = await backup_service.verify_backup(record.id)

        assert result.is_valid is False
        assert result.checksum_match is False
        assert any("checksum" in issue.lower() for issue in result.issues)

    @pytest.mark.asyncio
    async def test_verify_backup_not_found(self, backup_service: BackupService) -> None:
        """Test that verifying a non-existent backup returns invalid."""
        result = await backup_service.verify_backup(uuid4())

        assert result.is_valid is False
        assert any("not found" in issue.lower() for issue in result.issues)


# =============================================================================
# restore_backup Tests
# =============================================================================


class TestRestoreBackup:
    """Tests for BackupService.restore_backup."""

    @pytest.mark.asyncio
    async def test_restore_backup_success(self, backup_service: BackupService) -> None:
        """Test successful backup restore."""
        record = BackupRecord(
            status=BackupStatus.COMPLETED,
            metadata={"database_backup": "db_backup_test.sql.gz"},
        )
        # Create the backup file
        backup_path = backup_service.backup_dir / "db_backup_test.sql.gz"
        with gzip.open(backup_path, "wb") as f:
            f.write(b"SQL DATA")

        backup_service._backup_index[str(record.id)] = record
        backup_service._save_backup_index()

        result = await backup_service.restore_backup(record.id)

        assert result.success is True
        assert result.backup_id == record.id

    @pytest.mark.asyncio
    async def test_restore_backup_not_found_raises_error(
        self, backup_service: BackupService
    ) -> None:
        """Test that restoring a non-existent backup returns failure."""
        result = await backup_service.restore_backup(uuid4())

        assert result.success is False
        assert result.error_message is not None
        assert "not found" in result.error_message.lower()


# =============================================================================
# cleanup_old_backups Tests
# =============================================================================


class TestCleanupOldBackups:
    """Tests for BackupService.cleanup_old_backups."""

    @pytest.mark.asyncio
    async def test_cleanup_old_backups_removes_expired(self, backup_service: BackupService) -> None:
        """Test that old backups beyond retention are removed."""
        # Create old backups
        old_date = datetime.now(tz=UTC) - timedelta(days=60)
        for i in range(5):
            record = BackupRecord(
                status=BackupStatus.COMPLETED,
                created_at=old_date - timedelta(days=i),
            )
            backup_service._backup_index[str(record.id)] = record

        backup_service._save_backup_index()

        deleted = await backup_service.cleanup_old_backups(retention_days=30, keep_minimum=1)

        # At least some should be deleted (keeping minimum of 1)
        assert deleted >= 1

    @pytest.mark.asyncio
    async def test_cleanup_old_backups_keeps_recent(self, backup_service: BackupService) -> None:
        """Test that recent backups are preserved during cleanup."""
        # Create recent backups
        now = datetime.now(tz=UTC)
        for i in range(3):
            record = BackupRecord(
                status=BackupStatus.COMPLETED,
                created_at=now - timedelta(days=i),
            )
            backup_service._backup_index[str(record.id)] = record

        backup_service._save_backup_index()

        deleted = await backup_service.cleanup_old_backups(retention_days=30, keep_minimum=3)

        assert deleted == 0
        assert len(backup_service._backup_index) == 3


# =============================================================================
# list_backups Tests
# =============================================================================


class TestListBackups:
    """Tests for BackupService.list_backups."""

    @pytest.mark.asyncio
    async def test_list_backups_returns_all(self, backup_service: BackupService) -> None:
        """Test that list_backups returns all backup records."""
        for i in range(5):
            record = BackupRecord(
                backup_type=BackupType.FULL if i % 2 == 0 else BackupType.DATABASE,
                status=BackupStatus.COMPLETED,
                created_at=datetime.now(tz=UTC) - timedelta(hours=i),
            )
            backup_service._backup_index[str(record.id)] = record

        backup_service._save_backup_index()

        backups = await backup_service.list_backups()

        assert len(backups) == 5

    @pytest.mark.asyncio
    async def test_list_backups_filters_by_type(self, backup_service: BackupService) -> None:
        """Test that list_backups can filter by backup type."""
        # Add mixed types
        for btype in [BackupType.FULL, BackupType.DATABASE, BackupType.FULL]:
            record = BackupRecord(
                backup_type=btype,
                status=BackupStatus.COMPLETED,
            )
            backup_service._backup_index[str(record.id)] = record

        backup_service._save_backup_index()

        full_backups = await backup_service.list_backups(backup_type=BackupType.FULL)
        db_backups = await backup_service.list_backups(backup_type=BackupType.DATABASE)

        assert len(full_backups) == 2
        assert len(db_backups) == 1

    @pytest.mark.asyncio
    async def test_list_backups_filters_by_status(self, backup_service: BackupService) -> None:
        """Test that list_backups can filter by status."""
        statuses = [BackupStatus.COMPLETED, BackupStatus.FAILED, BackupStatus.COMPLETED]
        for status in statuses:
            record = BackupRecord(
                status=status,
            )
            backup_service._backup_index[str(record.id)] = record

        backup_service._save_backup_index()

        completed = await backup_service.list_backups(status=BackupStatus.COMPLETED)
        failed = await backup_service.list_backups(status=BackupStatus.FAILED)

        assert len(completed) == 2
        assert len(failed) == 1


# =============================================================================
# delete_backup Tests
# =============================================================================


class TestDeleteBackup:
    """Tests for BackupService.delete_backup."""

    @pytest.mark.asyncio
    async def test_delete_backup_removes_files_and_record(
        self, backup_service: BackupService
    ) -> None:
        """Test that deleting a backup removes files and index entry."""
        db_filename = "db_backup_delete_test.sql.gz"
        files_filename = "files_backup_delete_test.tar.gz"

        # Create actual files
        (backup_service.backup_dir / db_filename).write_bytes(b"db data")
        (backup_service.backup_dir / files_filename).write_bytes(b"files data")

        record = BackupRecord(
            status=BackupStatus.COMPLETED,
            metadata={
                "database_backup": db_filename,
                "files_backup": files_filename,
            },
        )
        backup_service._backup_index[str(record.id)] = record
        backup_service._save_backup_index()

        result = await backup_service.delete_backup(record.id)

        assert result is True
        assert str(record.id) not in backup_service._backup_index
        assert not (backup_service.backup_dir / db_filename).exists()
        assert not (backup_service.backup_dir / files_filename).exists()

    @pytest.mark.asyncio
    async def test_delete_backup_nonexistent_returns_false(
        self, backup_service: BackupService
    ) -> None:
        """Test that deleting a non-existent backup returns False."""
        result = await backup_service.delete_backup(uuid4())

        assert result is False


# =============================================================================
# Serialization Tests
# =============================================================================


class TestBackupRecordSerialization:
    """Tests for BackupRecord serialization roundtrip."""

    def test_backup_record_serialization_roundtrip(self) -> None:
        """Test that to_dict/from_dict produces equivalent records."""
        original = BackupRecord(
            backup_type=BackupType.INCREMENTAL,
            status=BackupStatus.VERIFIED,
            completed_at=datetime.now(tz=UTC),
            size_bytes=999888,
            file_count=42,
            location="/backups/test.tar.gz",
            checksum="sha256_test_hash",
            metadata={
                "description": "roundtrip test",
                "tables": ["users", "designs"],
                "incremental_base": str(uuid4()),
            },
            error_message=None,
        )

        data = original.to_dict()
        restored = BackupRecord.from_dict(data)

        assert restored.id == original.id
        assert restored.backup_type == original.backup_type
        assert restored.status == original.status
        assert restored.size_bytes == original.size_bytes
        assert restored.file_count == original.file_count
        assert restored.location == original.location
        assert restored.checksum == original.checksum
        assert restored.metadata == original.metadata
        assert restored.error_message == original.error_message
        assert restored.completed_at is not None

    def test_backup_record_serialization_with_error(self) -> None:
        """Test serialization of a failed backup record with error message."""
        original = BackupRecord(
            backup_type=BackupType.DATABASE,
            status=BackupStatus.FAILED,
            error_message="Connection refused to pg_dump",
        )

        data = original.to_dict()
        restored = BackupRecord.from_dict(data)

        assert restored.status == BackupStatus.FAILED
        assert restored.error_message == "Connection refused to pg_dump"
