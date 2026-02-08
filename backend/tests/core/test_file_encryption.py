"""
Tests for file encryption utilities.

Tests the core file encryption/decryption functions used across
all CAD export, component storage, and download paths.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from app.core.file_encryption import (
    ENCRYPTED_MARKER_SUFFIX,
    cleanup_encryption_marker,
    decrypt_bytes_from_storage,
    decrypt_file_from_disk,
    encrypt_and_write,
    encrypt_bytes_for_storage,
    encrypt_file_on_disk,
    is_encryption_enabled,
    is_file_encrypted,
    migrate_file_to_encrypted,
)


class TestIsEncryptionEnabled:
    """Tests for is_encryption_enabled function."""

    def test_encryption_enabled_by_default(self) -> None:
        """Test that encryption is enabled by default."""
        with patch("app.core.file_encryption.settings") as mock_settings:
            mock_settings.FILE_ENCRYPTION_ENABLED = True
            assert is_encryption_enabled() is True

    def test_encryption_disabled_when_setting_false(self) -> None:
        """Test that encryption can be disabled via settings."""
        with patch("app.core.file_encryption.settings") as mock_settings:
            mock_settings.FILE_ENCRYPTION_ENABLED = False
            assert is_encryption_enabled() is False


class TestEncryptFileOnDisk:
    """Tests for encrypt_file_on_disk function."""

    @pytest.mark.asyncio
    async def test_encrypt_file_on_disk_creates_marker(self, tmp_path: Path) -> None:
        """Test that encrypting a file creates an .enc marker."""
        file_path = tmp_path / "test.step"
        file_path.write_bytes(b"test cad content")

        await encrypt_file_on_disk(file_path)

        marker_path = Path(str(file_path) + ENCRYPTED_MARKER_SUFFIX)
        assert marker_path.exists()

    @pytest.mark.asyncio
    async def test_encrypt_file_on_disk_changes_content(self, tmp_path: Path) -> None:
        """Test that encrypting a file modifies its on-disk content."""
        file_path = tmp_path / "test.step"
        original_content = b"test cad content"
        file_path.write_bytes(original_content)

        await encrypt_file_on_disk(file_path)

        encrypted_content = file_path.read_bytes()
        assert encrypted_content != original_content
        assert len(encrypted_content) > len(original_content)

    @pytest.mark.asyncio
    async def test_encrypt_file_on_disk_skips_already_encrypted(self, tmp_path: Path) -> None:
        """Test that already-encrypted files are not re-encrypted."""
        file_path = tmp_path / "test.step"
        file_path.write_bytes(b"encrypted content")

        # Create marker to simulate already-encrypted
        marker_path = Path(str(file_path) + ENCRYPTED_MARKER_SUFFIX)
        marker_path.write_text("1")

        # Record content before call
        content_before = file_path.read_bytes()

        await encrypt_file_on_disk(file_path)

        # Content should not change
        assert file_path.read_bytes() == content_before

    @pytest.mark.asyncio
    async def test_encrypt_file_on_disk_raises_on_missing_file(self, tmp_path: Path) -> None:
        """Test that encrypting a non-existent file raises FileNotFoundError."""
        file_path = tmp_path / "nonexistent.step"

        with pytest.raises(FileNotFoundError):
            await encrypt_file_on_disk(file_path)

    @pytest.mark.asyncio
    async def test_encrypt_file_on_disk_noop_when_disabled(self, tmp_path: Path) -> None:
        """Test that encryption is a no-op when disabled."""
        file_path = tmp_path / "test.step"
        original_content = b"test cad content"
        file_path.write_bytes(original_content)

        with patch("app.core.file_encryption.is_encryption_enabled", return_value=False):
            await encrypt_file_on_disk(file_path)

        # Content should not change
        assert file_path.read_bytes() == original_content
        marker_path = Path(str(file_path) + ENCRYPTED_MARKER_SUFFIX)
        assert not marker_path.exists()


class TestDecryptFileFromDisk:
    """Tests for decrypt_file_from_disk function."""

    @pytest.mark.asyncio
    async def test_decrypt_file_returns_original_content(self, tmp_path: Path) -> None:
        """Test that decrypting returns the original plaintext content."""
        file_path = tmp_path / "test.step"
        original_content = b"test cad content"
        file_path.write_bytes(original_content)

        # Encrypt first
        await encrypt_file_on_disk(file_path)

        # Decrypt
        result = await decrypt_file_from_disk(file_path)
        assert result == original_content

    @pytest.mark.asyncio
    async def test_decrypt_file_returns_raw_when_not_encrypted(self, tmp_path: Path) -> None:
        """Test that non-encrypted files are returned as-is."""
        file_path = tmp_path / "test.step"
        content = b"plaintext cad content"
        file_path.write_bytes(content)

        result = await decrypt_file_from_disk(file_path)
        assert result == content

    @pytest.mark.asyncio
    async def test_decrypt_file_raises_on_missing_file(self, tmp_path: Path) -> None:
        """Test that decrypting a non-existent file raises FileNotFoundError."""
        file_path = tmp_path / "nonexistent.step"

        with pytest.raises(FileNotFoundError):
            await decrypt_file_from_disk(file_path)

    @pytest.mark.asyncio
    async def test_encrypt_decrypt_roundtrip_preserves_binary_data(
        self, tmp_path: Path
    ) -> None:
        """Test full roundtrip with binary data preserves content."""
        file_path = tmp_path / "binary.stl"
        # Use binary data with all byte values
        original_content = bytes(range(256)) * 100
        file_path.write_bytes(original_content)

        await encrypt_file_on_disk(file_path)
        result = await decrypt_file_from_disk(file_path)

        assert result == original_content

    @pytest.mark.asyncio
    async def test_encrypt_decrypt_roundtrip_large_file(self, tmp_path: Path) -> None:
        """Test roundtrip with a larger file (5MB)."""
        file_path = tmp_path / "large.step"
        original_content = b"x" * (5 * 1024 * 1024)
        file_path.write_bytes(original_content)

        await encrypt_file_on_disk(file_path)
        result = await decrypt_file_from_disk(file_path)

        assert result == original_content


class TestEncryptAndWrite:
    """Tests for encrypt_and_write function."""

    @pytest.mark.asyncio
    async def test_encrypt_and_write_creates_encrypted_file(self, tmp_path: Path) -> None:
        """Test that encrypt_and_write creates an encrypted file with marker."""
        file_path = tmp_path / "subdir" / "output.step"
        content = b"new cad content"

        await encrypt_and_write(file_path, content)

        assert file_path.exists()
        assert file_path.read_bytes() != content  # Encrypted
        marker_path = Path(str(file_path) + ENCRYPTED_MARKER_SUFFIX)
        assert marker_path.exists()

    @pytest.mark.asyncio
    async def test_encrypt_and_write_creates_parent_directories(self, tmp_path: Path) -> None:
        """Test that encrypt_and_write creates parent dirs if needed."""
        file_path = tmp_path / "a" / "b" / "c" / "output.step"

        await encrypt_and_write(file_path, b"content")

        assert file_path.exists()

    @pytest.mark.asyncio
    async def test_encrypt_and_write_plain_when_disabled(self, tmp_path: Path) -> None:
        """Test that encrypt_and_write writes plaintext when encryption is disabled."""
        file_path = tmp_path / "output.step"
        content = b"plaintext content"

        with patch("app.core.file_encryption.is_encryption_enabled", return_value=False):
            await encrypt_and_write(file_path, content)

        assert file_path.read_bytes() == content
        marker_path = Path(str(file_path) + ENCRYPTED_MARKER_SUFFIX)
        assert not marker_path.exists()

    @pytest.mark.asyncio
    async def test_encrypt_and_write_roundtrip(self, tmp_path: Path) -> None:
        """Test that data written with encrypt_and_write can be read back."""
        file_path = tmp_path / "roundtrip.step"
        content = b"roundtrip test content"

        await encrypt_and_write(file_path, content)
        result = await decrypt_file_from_disk(file_path)

        assert result == content


class TestEncryptDecryptBytes:
    """Tests for bytes encryption/decryption for storage."""

    @pytest.mark.asyncio
    async def test_encrypt_bytes_for_storage_changes_data(self) -> None:
        """Test that encrypting bytes changes the content."""
        data = b"sensitive cad data"
        encrypted = await encrypt_bytes_for_storage(data)

        assert encrypted != data
        assert len(encrypted) > len(data)

    @pytest.mark.asyncio
    async def test_decrypt_bytes_from_storage_restores_data(self) -> None:
        """Test full bytes roundtrip."""
        data = b"sensitive cad data"
        encrypted = await encrypt_bytes_for_storage(data)
        decrypted = await decrypt_bytes_from_storage(encrypted, is_encrypted=True)

        assert decrypted == data

    @pytest.mark.asyncio
    async def test_decrypt_bytes_noop_when_not_encrypted(self) -> None:
        """Test that non-encrypted data is returned as-is."""
        data = b"plaintext data"
        result = await decrypt_bytes_from_storage(data, is_encrypted=False)

        assert result == data

    @pytest.mark.asyncio
    async def test_encrypt_bytes_noop_when_disabled(self) -> None:
        """Test that encryption is skipped when disabled."""
        data = b"test data"

        with patch("app.core.file_encryption.is_encryption_enabled", return_value=False):
            result = await encrypt_bytes_for_storage(data)

        assert result == data


class TestMigrateFileToEncrypted:
    """Tests for migrate_file_to_encrypted function."""

    @pytest.mark.asyncio
    async def test_migrate_encrypts_unencrypted_file(self, tmp_path: Path) -> None:
        """Test migration of an unencrypted file."""
        file_path = tmp_path / "old_file.step"
        original_content = b"old unencrypted content"
        file_path.write_bytes(original_content)

        result = await migrate_file_to_encrypted(file_path)

        assert result is True
        assert is_file_encrypted(file_path)
        # Verify decryption works
        decrypted = await decrypt_file_from_disk(file_path)
        assert decrypted == original_content

    @pytest.mark.asyncio
    async def test_migrate_skips_already_encrypted_file(self, tmp_path: Path) -> None:
        """Test migration skips already-encrypted files."""
        file_path = tmp_path / "encrypted_file.step"
        file_path.write_bytes(b"content")
        marker_path = Path(str(file_path) + ENCRYPTED_MARKER_SUFFIX)
        marker_path.write_text("1")

        result = await migrate_file_to_encrypted(file_path)

        assert result is False

    @pytest.mark.asyncio
    async def test_migrate_returns_false_for_missing_file(self, tmp_path: Path) -> None:
        """Test migration returns False for non-existent files."""
        result = await migrate_file_to_encrypted(tmp_path / "missing.step")

        assert result is False


class TestIsFileEncrypted:
    """Tests for is_file_encrypted function."""

    def test_returns_true_when_marker_exists(self, tmp_path: Path) -> None:
        """Test detection of encrypted files via marker."""
        file_path = tmp_path / "test.step"
        file_path.write_bytes(b"data")
        marker_path = Path(str(file_path) + ENCRYPTED_MARKER_SUFFIX)
        marker_path.write_text("1")

        assert is_file_encrypted(file_path) is True

    def test_returns_false_when_no_marker(self, tmp_path: Path) -> None:
        """Test detection of unencrypted files."""
        file_path = tmp_path / "test.step"
        file_path.write_bytes(b"data")

        assert is_file_encrypted(file_path) is False


class TestCleanupEncryptionMarker:
    """Tests for cleanup_encryption_marker function."""

    def test_removes_existing_marker(self, tmp_path: Path) -> None:
        """Test that cleanup removes the .enc marker."""
        file_path = tmp_path / "test.step"
        file_path.write_bytes(b"data")
        marker_path = Path(str(file_path) + ENCRYPTED_MARKER_SUFFIX)
        marker_path.write_text("1")

        cleanup_encryption_marker(file_path)

        assert not marker_path.exists()

    def test_no_error_when_no_marker(self, tmp_path: Path) -> None:
        """Test cleanup is a no-op when no marker exists."""
        file_path = tmp_path / "test.step"
        file_path.write_bytes(b"data")

        # Should not raise
        cleanup_encryption_marker(file_path)
