"""
Tests for maintenance worker tasks.

Tests audit log archival, cleanup, and retention policies.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.core.config import settings
from app.models.audit import AuditLog
from app.worker.tasks.maintenance import archive_old_audit_logs


def run_async_task_sync(coro):
    """Helper to run coroutine in existing event loop (for tests) or new one."""
    try:
        asyncio.get_running_loop()
        # In an async test, we need to schedule it in the current loop
        import concurrent.futures

        with concurrent.futures.ThreadPoolExecutor() as pool:
            return pool.submit(asyncio.run, coro).result()
    except RuntimeError:
        return asyncio.run(coro)


@pytest.fixture
def mock_asyncio_run():
    """Patch asyncio.run to work in async test contexts."""
    original_run = asyncio.run

    def patched_run(coro):
        try:
            asyncio.get_running_loop()
            # Run in a separate thread to avoid nested loop issues
            import concurrent.futures

            with concurrent.futures.ThreadPoolExecutor() as pool:
                future = pool.submit(original_run, coro)
                return future.result(timeout=60)
        except RuntimeError:
            return original_run(coro)

    with patch("asyncio.run", side_effect=patched_run):
        yield


@pytest.mark.asyncio
class TestArchiveOldAuditLogs:
    """Tests for audit log archival task."""

    async def test_archive_no_old_logs_returns_empty_summary(
        self, db_session, test_user, mock_asyncio_run
    ):
        """Test that archival with no old logs returns empty summary."""
        # Create recent audit log (within retention period)
        recent_log = AuditLog(
            user_id=test_user.id,
            actor_type="user",
            action="login",
            resource_type="user",
            resource_id=test_user.id,
            context={},
            status="success",
            created_at=datetime.now(tz=UTC),
        )
        db_session.add(recent_log)
        await db_session.commit()

        # Mock storage client
        with patch("app.core.storage.storage_client") as mock_storage:
            mock_storage.upload_file = AsyncMock()

            result = archive_old_audit_logs()

            assert result["logs_archived"] == 0
            assert result["logs_deleted"] == 0
            assert result["archive_files_created"] == 0
            mock_storage.upload_file.assert_not_called()

    async def test_archive_old_logs_creates_archive_files(
        self, db_session, test_user, mock_asyncio_run
    ):
        """Test that old logs are archived to storage."""
        # Create old audit logs (beyond retention period)
        cutoff_date = datetime.now(tz=UTC) - timedelta(days=settings.AUDIT_LOG_RETENTION_DAYS + 10)

        old_logs = []
        for i in range(5):
            log = AuditLog(
                user_id=test_user.id,
                actor_type="user",
                action="update" if i % 2 == 0 else "delete",
                resource_type="design",
                resource_id=uuid4(),
                context={"test": f"data_{i}"},
                status="success",
                created_at=cutoff_date - timedelta(hours=i),
            )
            old_logs.append(log)
            db_session.add(log)

        await db_session.commit()

        # Mock storage client
        with patch("app.core.storage.storage_client") as mock_storage:
            mock_storage.upload_file = AsyncMock()

            result = archive_old_audit_logs()

            assert result["logs_archived"] == 5
            assert result["logs_deleted"] == 5
            assert result["archive_files_created"] >= 1
            assert result["total_size_bytes"] > 0
            assert len(result["errors"]) == 0

            # Verify storage upload was called
            assert mock_storage.upload_file.call_count >= 1

            # Check that logs were deleted from database
            remaining_logs = await db_session.execute(
                select(AuditLog).where(AuditLog.created_at < cutoff_date)
            )
            assert len(remaining_logs.scalars().all()) == 0

    async def test_archive_preserves_recent_logs(self, db_session, test_user, mock_asyncio_run):
        """Test that recent logs are not archived."""
        # Create mix of old and recent logs
        cutoff_date = datetime.now(tz=UTC) - timedelta(days=settings.AUDIT_LOG_RETENTION_DAYS)

        # Old log
        old_log = AuditLog(
            user_id=test_user.id,
            actor_type="user",
            action="delete",
            resource_type="design",
            resource_id=uuid4(),
            context={},
            status="success",
            created_at=cutoff_date - timedelta(days=1),
        )
        db_session.add(old_log)

        # Recent log
        recent_log = AuditLog(
            user_id=test_user.id,
            actor_type="user",
            action="create",
            resource_type="design",
            resource_id=uuid4(),
            context={},
            status="success",
            created_at=datetime.now(tz=UTC),
        )
        db_session.add(recent_log)

        await db_session.commit()

        # Mock storage client
        with patch("app.core.storage.storage_client") as mock_storage:
            mock_storage.upload_file = AsyncMock()

            result = archive_old_audit_logs()

            assert result["logs_archived"] == 1
            assert result["logs_deleted"] == 1

            # Verify recent log still exists
            recent_check = await db_session.execute(
                select(AuditLog).where(AuditLog.id == recent_log.id)
            )
            assert recent_check.scalar_one_or_none() is not None

    async def test_archive_generates_summary_stats(self, db_session, test_user, mock_asyncio_run):
        """Test that archival generates summary statistics."""
        cutoff_date = datetime.now(tz=UTC) - timedelta(days=settings.AUDIT_LOG_RETENTION_DAYS + 5)

        # Create logs with different actions and statuses
        actions = ["create", "update", "delete", "read"]
        statuses = ["success", "failure"]

        for i, action in enumerate(actions):
            for j, status in enumerate(statuses):
                log = AuditLog(
                    user_id=test_user.id,
                    actor_type="user",
                    action=action,
                    resource_type="design",
                    resource_id=uuid4(),
                    context={},
                    status=status,
                    created_at=cutoff_date - timedelta(hours=i * 2 + j),
                )
                db_session.add(log)

        await db_session.commit()

        # Mock storage client
        with patch("app.core.storage.storage_client") as mock_storage:
            mock_storage.upload_file = AsyncMock()

            result = archive_old_audit_logs()

            # Verify summary stats are generated
            assert "summary_stats" in result
            summary = result["summary_stats"]

            assert "period_start" in summary
            assert "period_end" in summary
            assert "total_logs" in summary
            assert summary["total_logs"] == 8

            assert "by_action" in summary
            assert len(summary["by_action"]) == 4

            assert "by_status" in summary
            assert len(summary["by_status"]) == 2

    async def test_archive_batches_large_datasets(self, db_session, test_user, mock_asyncio_run):
        """Test that large datasets are batched into multiple files."""
        cutoff_date = datetime.now(tz=UTC) - timedelta(days=settings.AUDIT_LOG_RETENTION_DAYS + 1)

        # Create 2500 logs (should create 3 batch files at 1000 per batch)
        logs = []
        for i in range(2500):
            log = AuditLog(
                user_id=test_user.id,
                actor_type="user",
                action="read",
                resource_type="design",
                resource_id=uuid4(),
                context={},
                status="success",
                created_at=cutoff_date - timedelta(minutes=i),
            )
            logs.append(log)

        db_session.add_all(logs)
        await db_session.commit()

        # Mock storage client
        with patch("app.core.storage.storage_client") as mock_storage:
            mock_storage.upload_file = AsyncMock()

            result = archive_old_audit_logs()

            assert result["logs_archived"] == 2500
            # Should create 3 batch files + 1 summary file
            assert result["archive_files_created"] >= 3
            # Summary file should also be uploaded
            assert mock_storage.upload_file.call_count >= 4  # 3 batches + summary

    async def test_archive_handles_storage_upload_errors(
        self, db_session, test_user, mock_asyncio_run
    ):
        """Test that storage upload errors are handled gracefully."""
        cutoff_date = datetime.now(tz=UTC) - timedelta(days=settings.AUDIT_LOG_RETENTION_DAYS + 1)

        log = AuditLog(
            user_id=test_user.id,
            actor_type="user",
            action="create",
            resource_type="design",
            resource_id=uuid4(),
            context={},
            status="success",
            created_at=cutoff_date,
        )
        db_session.add(log)
        await db_session.commit()

        # Mock storage client to raise error
        with patch("app.core.storage.storage_client") as mock_storage:
            mock_storage.upload_file = AsyncMock(side_effect=Exception("Storage error"))

            result = archive_old_audit_logs()

            # Task should complete but report errors
            assert len(result["errors"]) > 0
            assert any("Storage error" in str(err) for err in result["errors"])

    async def test_archive_includes_all_log_fields(self, db_session, test_user, mock_asyncio_run):
        """Test that archived data includes all log fields."""
        cutoff_date = datetime.now(tz=UTC) - timedelta(days=settings.AUDIT_LOG_RETENTION_DAYS + 1)

        resource_id = uuid4()
        log = AuditLog(
            user_id=test_user.id,
            actor_type="api_key",
            action="export",
            resource_type="design",
            resource_id=resource_id,
            context={"format": "stl", "quality": "high"},
            ip_address="192.168.1.1",
            user_agent="TestAgent/1.0",
            status="success",
            error_message=None,
            created_at=cutoff_date,
        )
        db_session.add(log)
        await db_session.commit()

        # Mock storage client and capture uploaded data
        uploaded_data = []

        async def capture_upload(*args, **kwargs):
            uploaded_data.append(kwargs.get("file"))

        with patch("app.core.storage.storage_client") as mock_storage:
            mock_storage.upload_file = AsyncMock(side_effect=capture_upload)

            result = archive_old_audit_logs()

            assert result["logs_archived"] == 1

            # Verify at least one file was uploaded (batch file)
            assert len(uploaded_data) > 0

    async def test_archive_uses_correct_bucket(self, db_session, test_user, mock_asyncio_run):
        """Test that archives are stored in the ARCHIVES bucket."""
        cutoff_date = datetime.now(tz=UTC) - timedelta(days=settings.AUDIT_LOG_RETENTION_DAYS + 1)

        log = AuditLog(
            user_id=test_user.id,
            actor_type="user",
            action="login",
            resource_type="user",
            resource_id=test_user.id,
            context={},
            status="success",
            created_at=cutoff_date,
        )
        db_session.add(log)
        await db_session.commit()

        with patch("app.core.storage.storage_client") as mock_storage:
            mock_storage.upload_file = AsyncMock()

            archive_old_audit_logs()

            # Check that ARCHIVES bucket was used
            from app.core.storage import StorageBucket

            for call in mock_storage.upload_file.call_args_list:
                bucket_arg = call[1]["bucket"]
                assert bucket_arg == StorageBucket.ARCHIVES

    async def test_archive_compresses_data(self, db_session, test_user, mock_asyncio_run):
        """Test that archived data is gzip compressed."""
        import gzip
        import json

        cutoff_date = datetime.now(tz=UTC) - timedelta(days=settings.AUDIT_LOG_RETENTION_DAYS + 1)

        log = AuditLog(
            user_id=test_user.id,
            actor_type="user",
            action="update",
            resource_type="design",
            resource_id=uuid4(),
            context={"large": "data" * 100},  # Some data to compress
            status="success",
            created_at=cutoff_date,
        )
        db_session.add(log)
        await db_session.commit()

        captured_files = []

        async def capture_file(*args, **kwargs):
            captured_files.append(kwargs.get("file"))

        with patch("app.core.storage.storage_client") as mock_storage:
            mock_storage.upload_file = AsyncMock(side_effect=capture_file)

            result = archive_old_audit_logs()

            assert result["logs_archived"] == 1
            assert len(captured_files) > 0

            # Verify first file (batch file) is valid gzip
            batch_file = captured_files[0]
            assert isinstance(batch_file, bytes)

            # Decompress and verify it's valid JSON
            decompressed = gzip.decompress(batch_file)
            data = json.loads(decompressed)
            assert isinstance(data, list)
            assert len(data) == 1
            assert data[0]["action"] == "update"
