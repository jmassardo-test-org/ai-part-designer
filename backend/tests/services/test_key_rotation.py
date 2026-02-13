"""
Tests for key rotation service.

Tests key versioning, decryption with multiple keys, re-encryption,
and directory-level rotation operations.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from app.core.file_encryption import ENCRYPTED_MARKER_SUFFIX
from app.core.security import EncryptionService
from app.services.key_rotation import (
    KeyRotationError,
    KeyRotationService,
    RotationResult,
    get_key_rotation_service,
)


class TestKeyRotationService:
    """Tests for KeyRotationService."""

    @pytest.fixture
    def old_key(self) -> str:
        """An old encryption key."""
        return "old-test-key-for-rotation-minimum-32-chars"

    @pytest.fixture
    def new_key(self) -> str:
        """A new encryption key (current)."""
        return "new-test-key-for-rotation-minimum-32-chars"

    @pytest.fixture
    def old_encryption_service(self, old_key: str) -> EncryptionService:
        """Encryption service using the old key."""
        return EncryptionService(key=old_key)

    @pytest.fixture
    def new_encryption_service(self, new_key: str) -> EncryptionService:
        """Encryption service using the new key."""
        return EncryptionService(key=new_key)

    @pytest.fixture
    def rotation_service(self, new_key: str, old_key: str) -> KeyRotationService:
        """Key rotation service with both keys."""
        return KeyRotationService(current_key=new_key, previous_keys=[old_key])

    def test_decrypt_with_current_key(
        self,
        rotation_service: KeyRotationService,
        new_encryption_service: EncryptionService,
    ) -> None:
        """Test decrypting data encrypted with the current key."""
        plaintext = b"test data encrypted with new key"
        encrypted = new_encryption_service.encrypt_bytes(plaintext)

        result = rotation_service.decrypt_with_any_key(encrypted)
        assert result == plaintext

    def test_decrypt_with_previous_key(
        self,
        rotation_service: KeyRotationService,
        old_encryption_service: EncryptionService,
    ) -> None:
        """Test decrypting data encrypted with a previous key."""
        plaintext = b"test data encrypted with old key"
        encrypted = old_encryption_service.encrypt_bytes(plaintext)

        result = rotation_service.decrypt_with_any_key(encrypted)
        assert result == plaintext

    def test_decrypt_with_unknown_key_raises(
        self,
        rotation_service: KeyRotationService,
    ) -> None:
        """Test that decryption fails for an unknown key."""
        unknown_service = EncryptionService(key="unknown-secret-key-not-in-rotation-list")
        encrypted = unknown_service.encrypt_bytes(b"mystery data")

        with pytest.raises(KeyRotationError, match="Unable to decrypt"):
            rotation_service.decrypt_with_any_key(encrypted)

    def test_re_encrypt_with_old_key_data(
        self,
        rotation_service: KeyRotationService,
        old_encryption_service: EncryptionService,
        new_encryption_service: EncryptionService,
    ) -> None:
        """Test re-encrypting data from old key to new key."""
        plaintext = b"data to migrate"
        old_encrypted = old_encryption_service.encrypt_bytes(plaintext)

        re_encrypted = rotation_service.re_encrypt(old_encrypted)

        # Should be decryptable with new key
        result = new_encryption_service.decrypt_bytes(re_encrypted)
        assert result == plaintext

    def test_re_encrypt_with_current_key_data(
        self,
        rotation_service: KeyRotationService,
        new_encryption_service: EncryptionService,
    ) -> None:
        """Test re-encrypting data already encrypted with current key."""
        plaintext = b"already current data"
        current_encrypted = new_encryption_service.encrypt_bytes(plaintext)

        re_encrypted = rotation_service.re_encrypt(current_encrypted)

        # Should still be decryptable
        result = new_encryption_service.decrypt_bytes(re_encrypted)
        assert result == plaintext


class TestKeyRotationServiceFile:
    """Tests for file-level key rotation."""

    @pytest.fixture
    def old_key(self) -> str:
        """An old encryption key."""
        return "old-test-key-for-rotation-minimum-32-chars"

    @pytest.fixture
    def new_key(self) -> str:
        """A new encryption key."""
        return "new-test-key-for-rotation-minimum-32-chars"

    @pytest.fixture
    def rotation_service(self, new_key: str, old_key: str) -> KeyRotationService:
        """Key rotation service with both keys."""
        return KeyRotationService(current_key=new_key, previous_keys=[old_key])

    @pytest.mark.asyncio
    async def test_rotate_file_re_encrypts_with_new_key(
        self,
        tmp_path: Path,
        rotation_service: KeyRotationService,
        old_key: str,
        new_key: str,
    ) -> None:
        """Test rotating a file that was encrypted with the old key."""
        file_path = tmp_path / "test.step"
        original_content = b"test cad file content"
        file_path.write_bytes(original_content)

        # Encrypt with old key
        old_service = EncryptionService(key=old_key)
        encrypted = old_service.encrypt_bytes(original_content)
        file_path.write_bytes(encrypted)
        marker_path = Path(str(file_path) + ENCRYPTED_MARKER_SUFFIX)
        marker_path.write_text("1")

        # Rotate
        result = await rotation_service.rotate_file(file_path)
        assert result is True

        # Verify it's now decryptable with new key
        new_service = EncryptionService(key=new_key)
        decrypted = new_service.decrypt_bytes(file_path.read_bytes())
        assert decrypted == original_content

    @pytest.mark.asyncio
    async def test_rotate_file_skips_unencrypted(
        self,
        tmp_path: Path,
        rotation_service: KeyRotationService,
    ) -> None:
        """Test that rotation skips unencrypted files."""
        file_path = tmp_path / "plain.step"
        file_path.write_bytes(b"plaintext")

        result = await rotation_service.rotate_file(file_path)
        assert result is False

    @pytest.mark.asyncio
    async def test_rotate_file_skips_already_current(
        self,
        tmp_path: Path,
        rotation_service: KeyRotationService,
        new_key: str,
    ) -> None:
        """Test that rotation skips files already encrypted with current key."""
        file_path = tmp_path / "current.step"
        original = b"already current"
        new_service = EncryptionService(key=new_key)
        encrypted = new_service.encrypt_bytes(original)
        file_path.write_bytes(encrypted)
        Path(str(file_path) + ENCRYPTED_MARKER_SUFFIX).write_text("1")

        result = await rotation_service.rotate_file(file_path)
        assert result is False

    @pytest.mark.asyncio
    async def test_rotate_file_raises_on_missing(
        self,
        tmp_path: Path,
        rotation_service: KeyRotationService,
    ) -> None:
        """Test that rotation raises for missing files."""
        with pytest.raises(FileNotFoundError):
            await rotation_service.rotate_file(tmp_path / "missing.step")


class TestRotateDirectory:
    """Tests for directory-level key rotation."""

    @pytest.fixture
    def old_key(self) -> str:
        """An old encryption key."""
        return "old-test-key-for-rotation-minimum-32-chars"

    @pytest.fixture
    def new_key(self) -> str:
        """A new encryption key."""
        return "new-test-key-for-rotation-minimum-32-chars"

    @pytest.fixture
    def rotation_service(self, new_key: str, old_key: str) -> KeyRotationService:
        """Key rotation service."""
        return KeyRotationService(current_key=new_key, previous_keys=[old_key])

    @pytest.mark.asyncio
    async def test_rotate_directory_processes_all_files(
        self,
        tmp_path: Path,
        rotation_service: KeyRotationService,
        old_key: str,
    ) -> None:
        """Test rotation processes all encrypted files in directory."""
        old_service = EncryptionService(key=old_key)

        # Create multiple encrypted files
        for i in range(3):
            file_path = tmp_path / f"file_{i}.step"
            content = f"content {i}".encode()
            encrypted = old_service.encrypt_bytes(content)
            file_path.write_bytes(encrypted)
            Path(str(file_path) + ENCRYPTED_MARKER_SUFFIX).write_text("1")

        result = await rotation_service.rotate_directory(tmp_path, "*.step")

        assert result.files_processed == 3
        assert result.files_re_encrypted == 3
        assert result.files_failed == 0

    @pytest.mark.asyncio
    async def test_rotate_directory_handles_mixed_files(
        self,
        tmp_path: Path,
        rotation_service: KeyRotationService,
    ) -> None:
        """Test rotation with a mix of encrypted and unencrypted files."""
        # Unencrypted file
        plain = tmp_path / "plain.step"
        plain.write_bytes(b"plaintext")

        # Already-current encrypted file
        result = await rotation_service.rotate_directory(tmp_path, "*.step")

        assert result.files_processed == 1
        assert result.files_skipped == 1  # No marker, so skipped
        assert result.files_re_encrypted == 0

    @pytest.mark.asyncio
    async def test_rotate_directory_returns_for_missing_dir(
        self,
        tmp_path: Path,
        rotation_service: KeyRotationService,
    ) -> None:
        """Test rotation handles missing directories gracefully."""
        result = await rotation_service.rotate_directory(tmp_path / "nonexistent", "*.step")

        assert result.files_processed == 0


class TestRotationResult:
    """Tests for RotationResult data class."""

    def test_to_dict_serialization(self) -> None:
        """Test RotationResult serialization."""
        result = RotationResult(
            files_processed=10,
            files_re_encrypted=7,
            files_skipped=2,
            files_failed=1,
            errors=["file.step: some error"],
            duration_seconds=1.234,
        )

        d = result.to_dict()
        assert d["files_processed"] == 10
        assert d["files_re_encrypted"] == 7
        assert d["files_skipped"] == 2
        assert d["files_failed"] == 1
        assert len(d["errors"]) == 1
        assert d["duration_seconds"] == 1.23

    def test_to_dict_truncates_errors(self) -> None:
        """Test that to_dict limits error output to 50 entries."""
        result = RotationResult(
            errors=[f"error {i}" for i in range(100)],
        )

        d = result.to_dict()
        assert len(d["errors"]) == 50


class TestGetKeyRotationService:
    """Tests for the factory function."""

    def test_creates_service_with_defaults(self) -> None:
        """Test creating service with default settings."""
        service = get_key_rotation_service()
        assert service is not None

    def test_creates_service_with_previous_keys(self) -> None:
        """Test creating service with previous keys."""
        service = get_key_rotation_service(
            previous_keys=["old-key-1-minimum-32-characters", "old-key-2-minimum-32-characters"]
        )
        assert service is not None
        assert len(service._previous_fernets) == 2
