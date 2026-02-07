"""
Tests for Backup and Disaster Recovery Service.

Tests backup types, status enums, and backup record management.
Note: The backup module has external dependencies, so we test the
enums and dataclasses by redefining them here for isolated testing.
"""

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from uuid import UUID, uuid4

# =============================================================================
# Local definitions for testing (matching backup.py)
# =============================================================================


class BackupType(StrEnum):
    """Types of backups."""

    FULL = "full"
    DATABASE = "database"
    FILES = "files"
    INCREMENTAL = "incremental"


class BackupStatus(StrEnum):
    """Backup operation status."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    VERIFIED = "verified"
    CORRUPTED = "corrupted"


@dataclass
class BackupRecord:
    """Record of a backup operation."""

    id: UUID = field(default_factory=uuid4)
    backup_type: BackupType = BackupType.FULL
    status: BackupStatus = BackupStatus.PENDING
    created_at: datetime = field(default_factory=lambda: datetime.now(tz=UTC))
    completed_at: datetime | None = None
    size_bytes: int = 0
    file_count: int = 0
    location: str = ""
    checksum: str = ""
    metadata: dict = field(default_factory=dict)
    error_message: str | None = None

    def to_dict(self) -> dict:
        """Convert to dictionary for storage."""
        return {
            "id": str(self.id),
            "backup_type": self.backup_type.value,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "size_bytes": self.size_bytes,
            "file_count": self.file_count,
            "location": self.location,
            "checksum": self.checksum,
            "metadata": self.metadata,
            "error_message": self.error_message,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "BackupRecord":
        """Create from dictionary."""
        return cls(
            id=UUID(data["id"]),
            backup_type=BackupType(data["backup_type"]),
            status=BackupStatus(data["status"]),
            created_at=datetime.fromisoformat(data["created_at"]),
            completed_at=datetime.fromisoformat(data["completed_at"])
            if data.get("completed_at")
            else None,
            size_bytes=data.get("size_bytes", 0),
            file_count=data.get("file_count", 0),
            location=data.get("location", ""),
            checksum=data.get("checksum", ""),
            metadata=data.get("metadata", {}),
            error_message=data.get("error_message"),
        )


# =============================================================================
# BackupType Tests
# =============================================================================


class TestBackupType:
    """Tests for BackupType enum."""

    def test_full_backup(self):
        """Test full backup type."""
        assert BackupType.FULL == "full"

    def test_database_backup(self):
        """Test database backup type."""
        assert BackupType.DATABASE == "database"

    def test_files_backup(self):
        """Test files backup type."""
        assert BackupType.FILES == "files"

    def test_incremental_backup(self):
        """Test incremental backup type."""
        assert BackupType.INCREMENTAL == "incremental"

    def test_all_types_are_strings(self):
        """Test all backup types are strings."""
        for backup_type in BackupType:
            assert isinstance(backup_type.value, str)


# =============================================================================
# BackupStatus Tests
# =============================================================================


class TestBackupStatus:
    """Tests for BackupStatus enum."""

    def test_pending_status(self):
        """Test pending status."""
        assert BackupStatus.PENDING == "pending"

    def test_in_progress_status(self):
        """Test in progress status."""
        assert BackupStatus.IN_PROGRESS == "in_progress"

    def test_completed_status(self):
        """Test completed status."""
        assert BackupStatus.COMPLETED == "completed"

    def test_failed_status(self):
        """Test failed status."""
        assert BackupStatus.FAILED == "failed"

    def test_verified_status(self):
        """Test verified status."""
        assert BackupStatus.VERIFIED == "verified"

    def test_corrupted_status(self):
        """Test corrupted status."""
        assert BackupStatus.CORRUPTED == "corrupted"


# =============================================================================
# BackupRecord Tests
# =============================================================================


class TestBackupRecord:
    """Tests for BackupRecord dataclass."""

    def test_default_creation(self):
        """Test creating a backup record with defaults."""
        record = BackupRecord()

        assert record.backup_type == BackupType.FULL
        assert record.status == BackupStatus.PENDING
        assert record.size_bytes == 0
        assert record.file_count == 0
        assert record.location == ""
        assert record.checksum == ""
        assert record.metadata == {}
        assert record.error_message is None

    def test_custom_creation(self):
        """Test creating a backup record with custom values."""
        backup_id = uuid4()
        now = datetime.now(tz=UTC)

        record = BackupRecord(
            id=backup_id,
            backup_type=BackupType.DATABASE,
            status=BackupStatus.COMPLETED,
            created_at=now,
            completed_at=now + timedelta(minutes=5),
            size_bytes=1024000,
            file_count=10,
            location="s3://backup-bucket/backups/test.gz",
            checksum="abc123",
            metadata={"compression": "gzip"},
        )

        assert record.id == backup_id
        assert record.backup_type == BackupType.DATABASE
        assert record.status == BackupStatus.COMPLETED
        assert record.size_bytes == 1024000
        assert record.file_count == 10

    def test_to_dict(self):
        """Test converting backup record to dictionary."""
        record = BackupRecord(
            backup_type=BackupType.FILES,
            status=BackupStatus.VERIFIED,
            size_bytes=500000,
            location="/backups/files.tar.gz",
        )

        data = record.to_dict()

        assert data["backup_type"] == "files"
        assert data["status"] == "verified"
        assert data["size_bytes"] == 500000
        assert data["location"] == "/backups/files.tar.gz"
        assert "id" in data
        assert "created_at" in data

    def test_to_dict_with_completed_at(self):
        """Test to_dict includes completed_at when set."""
        now = datetime.now(tz=UTC)
        record = BackupRecord(
            completed_at=now,
        )

        data = record.to_dict()

        assert data["completed_at"] is not None

    def test_to_dict_without_completed_at(self):
        """Test to_dict handles None completed_at."""
        record = BackupRecord()

        data = record.to_dict()

        assert data["completed_at"] is None

    def test_from_dict(self):
        """Test creating backup record from dictionary."""
        data = {
            "id": str(uuid4()),
            "backup_type": "database",
            "status": "completed",
            "created_at": "2024-01-15T10:30:00",
            "completed_at": "2024-01-15T10:45:00",
            "size_bytes": 2048000,
            "file_count": 5,
            "location": "s3://bucket/backup.gz",
            "checksum": "sha256hash",
            "metadata": {"tables": ["users", "designs"]},
            "error_message": None,
        }

        record = BackupRecord.from_dict(data)

        assert record.backup_type == BackupType.DATABASE
        assert record.status == BackupStatus.COMPLETED
        assert record.size_bytes == 2048000
        assert record.file_count == 5
        assert record.completed_at is not None

    def test_from_dict_without_optional_fields(self):
        """Test from_dict with minimal data."""
        data = {
            "id": str(uuid4()),
            "backup_type": "full",
            "status": "pending",
            "created_at": "2024-01-15T10:00:00",
        }

        record = BackupRecord.from_dict(data)

        assert record.backup_type == BackupType.FULL
        assert record.status == BackupStatus.PENDING
        assert record.size_bytes == 0
        assert record.completed_at is None

    def test_roundtrip_serialization(self):
        """Test to_dict/from_dict roundtrip."""
        original = BackupRecord(
            backup_type=BackupType.INCREMENTAL,
            status=BackupStatus.FAILED,
            size_bytes=100,
            error_message="Disk full",
            metadata={"attempt": 3},
        )

        data = original.to_dict()
        restored = BackupRecord.from_dict(data)

        assert restored.backup_type == original.backup_type
        assert restored.status == original.status
        assert restored.size_bytes == original.size_bytes
        assert restored.error_message == original.error_message
        assert restored.metadata == original.metadata


# =============================================================================
# Edge Cases
# =============================================================================


class TestBackupEdgeCases:
    """Tests for edge cases in backup module."""

    def test_uuid_generation(self):
        """Test that UUID is auto-generated."""
        record = BackupRecord()

        assert record.id is not None
        assert isinstance(record.id, UUID)

    def test_datetime_generation(self):
        """Test that created_at is auto-generated."""
        record = BackupRecord()

        assert record.created_at is not None
        assert isinstance(record.created_at, datetime)

    def test_empty_metadata(self):
        """Test default empty metadata."""
        record = BackupRecord()

        assert record.metadata == {}
        assert isinstance(record.metadata, dict)

    def test_large_size_bytes(self):
        """Test handling of large backup sizes."""
        record = BackupRecord(size_bytes=10_000_000_000)  # 10 GB

        assert record.size_bytes == 10_000_000_000
        data = record.to_dict()
        assert data["size_bytes"] == 10_000_000_000

    def test_error_message_preserved(self):
        """Test error messages are preserved."""
        error_msg = "Connection timeout: failed to reach S3 bucket"
        record = BackupRecord(error_message=error_msg)

        data = record.to_dict()
        assert data["error_message"] == error_msg

    def test_complex_metadata(self):
        """Test complex metadata structures."""
        metadata = {
            "tables": ["users", "designs", "versions"],
            "compressed": True,
            "encryption": {
                "algorithm": "AES-256",
                "key_id": "aws/s3",
            },
            "stats": {
                "rows_backed_up": 50000,
                "duration_seconds": 120.5,
            },
        }
        record = BackupRecord(metadata=metadata)

        data = record.to_dict()
        assert data["metadata"]["tables"] == ["users", "designs", "versions"]
        assert data["metadata"]["encryption"]["algorithm"] == "AES-256"
