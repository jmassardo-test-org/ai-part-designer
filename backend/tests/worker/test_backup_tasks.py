"""
Tests for backup-related Celery tasks.

Tests backup_database and weekly_full_backup task execution,
return values, and error handling with mocked dependencies.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# =============================================================================
# backup_database Task Tests
# =============================================================================


class TestBackupDatabaseTask:
    """Tests for the backup_database Celery task."""

    def test_backup_database_task_calls_service(self) -> None:
        """Test that backup_database task invokes db_backup.create_backup."""
        mock_backup_info: dict[str, Any] = {
            "filename": "backup_full_20250224.sql.gz",
            "filepath": "/tmp/backups/backup_full_20250224.sql.gz",
            "backup_type": "full",
            "size_bytes": 1024,
            "compressed": True,
            "storage_url": "s3://bucket/backup.gz",
            "created_at": "20250224_030000",
        }

        with (
            patch(
                "app.worker.tasks.maintenance.BACKUP_OPERATIONS_TOTAL", None
            ),
            patch(
                "app.worker.tasks.maintenance.BACKUP_DURATION_SECONDS", None
            ),
            patch("app.core.backup.db_backup") as mock_db_backup,
        ):
            mock_db_backup.create_backup = AsyncMock(return_value=mock_backup_info)
            mock_db_backup.cleanup_old_backups = AsyncMock(return_value=2)

            from app.worker.tasks.maintenance import backup_database

            result = backup_database("full")

            mock_db_backup.create_backup.assert_called_once_with(
                backup_type="full",
                compress=True,
                upload_to_storage=True,
            )
            mock_db_backup.cleanup_old_backups.assert_called_once()

    def test_backup_database_task_returns_metadata(self) -> None:
        """Test that backup_database task returns backup metadata dict."""
        mock_backup_info: dict[str, Any] = {
            "filename": "backup_full_20250224.sql.gz",
            "filepath": "/tmp/backups/backup_full_20250224.sql.gz",
            "backup_type": "full",
            "size_bytes": 2048,
            "compressed": True,
            "storage_url": "s3://bucket/backup.gz",
            "created_at": "20250224_030000",
        }

        with (
            patch(
                "app.worker.tasks.maintenance.BACKUP_OPERATIONS_TOTAL", None
            ),
            patch(
                "app.worker.tasks.maintenance.BACKUP_DURATION_SECONDS", None
            ),
            patch("app.core.backup.db_backup") as mock_db_backup,
        ):
            mock_db_backup.create_backup = AsyncMock(return_value=mock_backup_info)
            mock_db_backup.cleanup_old_backups = AsyncMock(return_value=0)

            from app.worker.tasks.maintenance import backup_database

            result = backup_database("full")

            assert isinstance(result, dict)
            assert result["filename"] == "backup_full_20250224.sql.gz"
            assert result["backup_type"] == "full"
            assert result["old_backups_removed"] == 0

    def test_backup_database_task_handles_failure(self) -> None:
        """Test that backup_database task propagates exceptions."""
        with (
            patch(
                "app.worker.tasks.maintenance.BACKUP_OPERATIONS_TOTAL", None
            ),
            patch(
                "app.worker.tasks.maintenance.BACKUP_DURATION_SECONDS", None
            ),
            patch("app.core.backup.db_backup") as mock_db_backup,
        ):
            mock_db_backup.create_backup = AsyncMock(
                side_effect=RuntimeError("pg_dump failed: connection refused")
            )

            from app.worker.tasks.maintenance import backup_database

            with pytest.raises(RuntimeError, match="pg_dump failed"):
                backup_database("full")


# =============================================================================
# weekly_full_backup Task Tests
# =============================================================================


class TestWeeklyFullBackupTask:
    """Tests for the weekly_full_backup Celery task."""

    def test_weekly_full_backup_task_calls_service(self) -> None:
        """Test that weekly_full_backup task invokes BackupService.create_backup."""
        mock_record = MagicMock()
        mock_record.to_dict.return_value = {
            "id": "test-uuid",
            "backup_type": "full",
            "status": "completed",
            "created_at": "2025-02-24T03:00:00+00:00",
            "completed_at": "2025-02-24T03:15:00+00:00",
            "size_bytes": 4096,
        }

        with (
            patch(
                "app.worker.tasks.maintenance.BACKUP_OPERATIONS_TOTAL", None
            ),
            patch(
                "app.worker.tasks.maintenance.BACKUP_DURATION_SECONDS", None
            ),
            patch(
                "app.services.backup.BackupService"
            ) as MockBackupService,
        ):
            mock_service_instance = MagicMock()
            mock_service_instance.create_backup = AsyncMock(return_value=mock_record)
            MockBackupService.return_value = mock_service_instance

            from app.worker.tasks.maintenance import weekly_full_backup

            result = weekly_full_backup()

            mock_service_instance.create_backup.assert_called_once()
            call_kwargs = mock_service_instance.create_backup.call_args
            # Verify BackupType.FULL and description
            assert call_kwargs.kwargs.get("description") == "Weekly full backup"

    def test_weekly_full_backup_task_returns_metadata(self) -> None:
        """Test that weekly_full_backup task returns serialized backup record."""
        expected_result = {
            "id": "test-uuid-123",
            "backup_type": "full",
            "status": "completed",
            "created_at": "2025-02-24T03:00:00+00:00",
            "completed_at": "2025-02-24T03:15:00+00:00",
            "size_bytes": 8192,
            "file_count": 100,
        }

        mock_record = MagicMock()
        mock_record.to_dict.return_value = expected_result

        with (
            patch(
                "app.worker.tasks.maintenance.BACKUP_OPERATIONS_TOTAL", None
            ),
            patch(
                "app.worker.tasks.maintenance.BACKUP_DURATION_SECONDS", None
            ),
            patch(
                "app.services.backup.BackupService"
            ) as MockBackupService,
        ):
            mock_service_instance = MagicMock()
            mock_service_instance.create_backup = AsyncMock(return_value=mock_record)
            MockBackupService.return_value = mock_service_instance

            from app.worker.tasks.maintenance import weekly_full_backup

            result = weekly_full_backup()

            assert isinstance(result, dict)
            assert result["id"] == "test-uuid-123"
            assert result["backup_type"] == "full"
            assert result["status"] == "completed"

    def test_weekly_full_backup_task_handles_failure(self) -> None:
        """Test that weekly_full_backup task propagates exceptions on failure."""
        with (
            patch(
                "app.worker.tasks.maintenance.BACKUP_OPERATIONS_TOTAL", None
            ),
            patch(
                "app.worker.tasks.maintenance.BACKUP_DURATION_SECONDS", None
            ),
            patch(
                "app.services.backup.BackupService"
            ) as MockBackupService,
        ):
            mock_service_instance = MagicMock()
            mock_service_instance.create_backup = AsyncMock(
                side_effect=OSError("Disk full")
            )
            MockBackupService.return_value = mock_service_instance

            from app.worker.tasks.maintenance import weekly_full_backup

            with pytest.raises(OSError, match="Disk full"):
                weekly_full_backup()
