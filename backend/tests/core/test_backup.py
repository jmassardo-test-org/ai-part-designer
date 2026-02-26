"""
Tests for DatabaseBackup core backup and recovery utilities.

Tests pg_dump invocation, compression, storage upload, restore,
cleanup retention, and backup listing.
"""

from __future__ import annotations

import gzip
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.backup import DatabaseBackup


def _make_pg_dump_side_effect(
    mock_process: AsyncMock,
) -> Any:
    """Create a side_effect for create_subprocess_exec that writes the -f file.

    pg_dump uses ``-f <filepath>`` to write output. Since we mock the
    subprocess, the file is never actually created. This helper inspects the
    arguments passed to ``create_subprocess_exec`` and creates the target
    file so that subsequent ``stat()`` / ``open()`` calls succeed.
    """

    async def side_effect(*args: Any, **kwargs: Any) -> AsyncMock:
        arg_list = list(args)
        for i, arg in enumerate(arg_list):
            if arg == "-f" and i + 1 < len(arg_list):
                Path(arg_list[i + 1]).write_text("-- pg_dump output")
        return mock_process

    return side_effect


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
def db_backup(tmp_backup_dir: Path) -> DatabaseBackup:
    """Create a DatabaseBackup instance with temporary directory."""
    return DatabaseBackup(backup_dir=str(tmp_backup_dir), retention_days=30)


@pytest.fixture
def mock_settings() -> MagicMock:
    """Create mock settings for database connection."""
    settings = MagicMock()
    settings.POSTGRES_HOST = "localhost"
    settings.POSTGRES_PORT = 5432
    settings.POSTGRES_USER = "testuser"
    settings.POSTGRES_PASSWORD = "testpass"
    settings.POSTGRES_DB = "testdb"
    return settings


# =============================================================================
# create_backup Tests
# =============================================================================


class TestCreateBackup:
    """Tests for DatabaseBackup.create_backup."""

    @pytest.mark.asyncio
    async def test_create_backup_full_runs_pg_dump(
        self, db_backup: DatabaseBackup, mock_settings: MagicMock
    ) -> None:
        """Test that a full backup invokes pg_dump subprocess."""
        mock_process = AsyncMock()
        mock_process.returncode = 0
        mock_process.communicate = AsyncMock(return_value=(b"", b""))

        with (
            patch("app.core.backup.settings", mock_settings),
            patch(
                "asyncio.create_subprocess_exec",
                side_effect=_make_pg_dump_side_effect(mock_process),
            ) as mock_exec,
            patch("app.core.backup.storage_client") as mock_storage,
        ):
            mock_storage.upload_file = AsyncMock(return_value="s3://bucket/key")

            result = await db_backup.create_backup(
                backup_type="full", compress=False, upload_to_storage=False
            )

            mock_exec.assert_called_once()
            cmd_args = mock_exec.call_args[0]
            assert cmd_args[0] == "pg_dump"
            assert result["backup_type"] == "full"

    @pytest.mark.asyncio
    async def test_create_backup_schema_only(
        self, db_backup: DatabaseBackup, mock_settings: MagicMock
    ) -> None:
        """Test that schema backup passes --schema-only flag to pg_dump."""
        mock_process = AsyncMock()
        mock_process.returncode = 0
        mock_process.communicate = AsyncMock(return_value=(b"", b""))

        with (
            patch("app.core.backup.settings", mock_settings),
            patch(
                "asyncio.create_subprocess_exec",
                side_effect=_make_pg_dump_side_effect(mock_process),
            ) as mock_exec,
        ):
            result = await db_backup.create_backup(
                backup_type="schema", compress=False, upload_to_storage=False
            )

            cmd_args = mock_exec.call_args[0]
            assert "--schema-only" in cmd_args
            assert result["backup_type"] == "schema"

    @pytest.mark.asyncio
    async def test_create_backup_data_only(
        self, db_backup: DatabaseBackup, mock_settings: MagicMock
    ) -> None:
        """Test that data backup passes --data-only flag to pg_dump."""
        mock_process = AsyncMock()
        mock_process.returncode = 0
        mock_process.communicate = AsyncMock(return_value=(b"", b""))

        with (
            patch("app.core.backup.settings", mock_settings),
            patch(
                "asyncio.create_subprocess_exec",
                side_effect=_make_pg_dump_side_effect(mock_process),
            ) as mock_exec,
        ):
            result = await db_backup.create_backup(
                backup_type="data", compress=False, upload_to_storage=False
            )

            cmd_args = mock_exec.call_args[0]
            assert "--data-only" in cmd_args
            assert result["backup_type"] == "data"

    @pytest.mark.asyncio
    async def test_create_backup_with_compression(
        self, db_backup: DatabaseBackup, mock_settings: MagicMock
    ) -> None:
        """Test that compressed backup creates .sql.gz file."""
        mock_process = AsyncMock()
        mock_process.returncode = 0
        mock_process.communicate = AsyncMock(return_value=(b"", b""))

        with (
            patch("app.core.backup.settings", mock_settings),
            patch(
                "asyncio.create_subprocess_exec",
                side_effect=_make_pg_dump_side_effect(mock_process),
            ),
        ):
            result = await db_backup.create_backup(
                backup_type="full", compress=True, upload_to_storage=False
            )

            assert result["compressed"] is True
            assert result["filename"].endswith(".sql.gz")

    @pytest.mark.asyncio
    async def test_create_backup_uploads_to_storage(
        self, db_backup: DatabaseBackup, mock_settings: MagicMock
    ) -> None:
        """Test that backup uploads to storage when enabled."""
        mock_process = AsyncMock()
        mock_process.returncode = 0
        mock_process.communicate = AsyncMock(return_value=(b"", b""))

        with (
            patch("app.core.backup.settings", mock_settings),
            patch(
                "asyncio.create_subprocess_exec",
                side_effect=_make_pg_dump_side_effect(mock_process),
            ),
            patch("app.core.backup.storage_client") as mock_storage,
        ):
            mock_storage.upload_file = AsyncMock(return_value="s3://bucket/backup.sql.gz")

            result = await db_backup.create_backup(
                backup_type="full", compress=False, upload_to_storage=True
            )

            mock_storage.upload_file.assert_called_once()
            assert result["storage_url"] is not None


# =============================================================================
# restore_backup Tests
# =============================================================================


class TestRestoreBackup:
    """Tests for DatabaseBackup.restore_backup."""

    @pytest.mark.asyncio
    async def test_restore_backup_runs_psql(
        self, db_backup: DatabaseBackup, mock_settings: MagicMock, tmp_path: Path
    ) -> None:
        """Test that restore invokes psql subprocess."""
        # Create a fake backup file
        backup_file = tmp_path / "restore_test.sql"
        backup_file.write_text("CREATE TABLE test;")

        mock_process = AsyncMock()
        mock_process.returncode = 0
        mock_process.communicate = AsyncMock(return_value=(b"", b""))

        with (
            patch("app.core.backup.settings", mock_settings),
            patch("asyncio.create_subprocess_exec", return_value=mock_process) as mock_exec,
        ):
            result = await db_backup.restore_backup(str(backup_file))

            assert result is True
            mock_exec.assert_called()
            cmd_args = mock_exec.call_args[0]
            assert cmd_args[0] == "psql"

    @pytest.mark.asyncio
    async def test_restore_backup_decompresses_gz(
        self, db_backup: DatabaseBackup, mock_settings: MagicMock, tmp_path: Path
    ) -> None:
        """Test that .gz backup files are decompressed before restore."""
        # Create a compressed backup file
        backup_file = tmp_path / "restore_test.sql.gz"
        with gzip.open(backup_file, "wb") as f:
            f.write(b"CREATE TABLE test;")

        mock_process = AsyncMock()
        mock_process.returncode = 0
        mock_process.communicate = AsyncMock(return_value=(b"", b""))

        with (
            patch("app.core.backup.settings", mock_settings),
            patch("asyncio.create_subprocess_exec", return_value=mock_process),
        ):
            result = await db_backup.restore_backup(str(backup_file))

            assert result is True
            # The decompressed file should exist
            decompressed = tmp_path / "restore_test.sql"
            assert decompressed.exists()


# =============================================================================
# cleanup_old_backups Tests
# =============================================================================


class TestCleanupOldBackups:
    """Tests for DatabaseBackup.cleanup_old_backups."""

    @pytest.mark.asyncio
    async def test_cleanup_old_backups_respects_retention(
        self, db_backup: DatabaseBackup, mock_settings: MagicMock
    ) -> None:
        """Test that cleanup only removes backups past the retention period."""
        import os

        # Create old backup files (modify timestamp to be old)
        old_cutoff = datetime.now(tz=UTC) - timedelta(days=db_backup.retention_days + 5)
        old_timestamp = old_cutoff.timestamp()

        old_file = db_backup.backup_dir / "backup_full_20240101_000000.sql.gz"
        old_file.write_bytes(b"old data")
        os.utime(old_file, (old_timestamp, old_timestamp))

        # Create a recent file
        recent_file = db_backup.backup_dir / "backup_full_20260224_000000.sql.gz"
        recent_file.write_bytes(b"recent data")

        with (
            patch("app.core.backup.settings", mock_settings),
            patch("app.core.backup.storage_client") as mock_storage,
        ):
            mock_storage.list_files = AsyncMock(return_value=[])
            mock_storage.delete_files = AsyncMock(return_value=0)

            removed = await db_backup.cleanup_old_backups()

            # Old file should be removed
            assert not old_file.exists()
            # Recent file should be kept
            assert recent_file.exists()
            assert removed >= 1


# =============================================================================
# list_backups Tests
# =============================================================================


class TestListBackups:
    """Tests for DatabaseBackup.list_backups."""

    @pytest.mark.asyncio
    async def test_list_backups_from_storage(
        self, db_backup: DatabaseBackup, mock_settings: MagicMock
    ) -> None:
        """Test that list_backups retrieves backup list from storage."""
        now = datetime.now(tz=UTC)
        mock_backups = [
            {
                "key": "backups/20250101/backup_full.sql.gz",
                "last_modified": now - timedelta(days=1),
                "size": 1024,
            },
            {
                "key": "backups/20250102/backup_full.sql.gz",
                "last_modified": now,
                "size": 2048,
            },
        ]

        with (
            patch("app.core.backup.settings", mock_settings),
            patch("app.core.backup.storage_client") as mock_storage,
        ):
            mock_storage.list_files = AsyncMock(return_value=mock_backups)

            backups = await db_backup.list_backups()

            mock_storage.list_files.assert_called_once()
            assert len(backups) == 2
            # Should be sorted by last_modified descending
            assert backups[0]["last_modified"] >= backups[1]["last_modified"]
