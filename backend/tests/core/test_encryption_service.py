"""
Tests for EncryptionService file encryption functionality.

Tests file encryption, decryption, streaming, and path-based operations.
"""

from __future__ import annotations

import tempfile
from io import BytesIO
from pathlib import Path

import pytest

from app.core.security import EncryptionService


class TestEncryptionServiceFileOperations:
    """Tests for EncryptionService file encryption methods."""

    @pytest.fixture
    def encryption_service(self):
        """Create an encryption service instance."""
        return EncryptionService()

    def test_encrypt_bytes_returns_encrypted_bytes(self, encryption_service):
        """Test encrypting raw bytes returns encrypted data."""
        data = b"test file content"
        encrypted = encryption_service.encrypt_bytes(data)

        assert isinstance(encrypted, bytes)
        assert encrypted != data
        assert len(encrypted) > len(data)  # Encrypted data is larger

    def test_decrypt_bytes_returns_original_data(self, encryption_service):
        """Test decrypting bytes returns original data."""
        data = b"test file content"
        encrypted = encryption_service.encrypt_bytes(data)
        decrypted = encryption_service.decrypt_bytes(encrypted)

        assert decrypted == data

    def test_encrypt_decrypt_bytes_roundtrip_with_binary_data(self, encryption_service):
        """Test encryption/decryption roundtrip with binary data."""
        # Use binary data with non-ASCII bytes
        data = bytes(range(256))
        encrypted = encryption_service.encrypt_bytes(data)
        decrypted = encryption_service.decrypt_bytes(encrypted)

        assert decrypted == data

    @pytest.mark.asyncio
    async def test_encrypt_file_encrypts_file_content(self, encryption_service):
        """Test encrypting file content."""
        file_data = b"test file content"
        encrypted = await encryption_service.encrypt_file(file_data)

        assert isinstance(encrypted, bytes)
        assert encrypted != file_data

    @pytest.mark.asyncio
    async def test_decrypt_file_decrypts_file_content(self, encryption_service):
        """Test decrypting file content."""
        file_data = b"test file content"
        encrypted = await encryption_service.encrypt_file(file_data)
        decrypted = await encryption_service.decrypt_file(encrypted)

        assert decrypted == file_data

    @pytest.mark.asyncio
    async def test_encrypt_file_path_creates_encrypted_file(self, encryption_service):
        """Test encrypting a file from path to path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            input_path = Path(tmpdir) / "input.txt"
            output_path = Path(tmpdir) / "output.enc"

            # Create input file
            test_data = b"test file content"
            input_path.write_bytes(test_data)

            # Encrypt
            await encryption_service.encrypt_file_path(str(input_path), str(output_path))

            # Verify output exists and is different
            assert output_path.exists()
            encrypted_data = output_path.read_bytes()
            assert encrypted_data != test_data
            assert len(encrypted_data) > len(test_data)

    @pytest.mark.asyncio
    async def test_decrypt_file_path_creates_decrypted_file(self, encryption_service):
        """Test decrypting a file from path to path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            input_path = Path(tmpdir) / "input.txt"
            encrypted_path = Path(tmpdir) / "encrypted.enc"
            decrypted_path = Path(tmpdir) / "decrypted.txt"

            # Create and encrypt file
            test_data = b"test file content"
            input_path.write_bytes(test_data)
            await encryption_service.encrypt_file_path(str(input_path), str(encrypted_path))

            # Decrypt
            await encryption_service.decrypt_file_path(str(encrypted_path), str(decrypted_path))

            # Verify decrypted matches original
            assert decrypted_path.exists()
            decrypted_data = decrypted_path.read_bytes()
            assert decrypted_data == test_data

    @pytest.mark.asyncio
    async def test_encrypt_file_path_creates_parent_directories(self, encryption_service):
        """Test that parent directories are created if they don't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            input_path = Path(tmpdir) / "input.txt"
            output_path = Path(tmpdir) / "nested" / "dir" / "output.enc"

            # Create input file
            input_path.write_bytes(b"test")

            # Encrypt to nested path
            await encryption_service.encrypt_file_path(str(input_path), str(output_path))

            # Verify nested directories were created
            assert output_path.exists()
            assert output_path.parent.exists()

    @pytest.mark.asyncio
    async def test_encrypt_file_path_raises_error_for_missing_input(self, encryption_service):
        """Test that encrypting a non-existent file raises FileNotFoundError."""
        with tempfile.TemporaryDirectory() as tmpdir:
            input_path = Path(tmpdir) / "nonexistent.txt"
            output_path = Path(tmpdir) / "output.enc"

            with pytest.raises(FileNotFoundError, match="Input file not found"):
                await encryption_service.encrypt_file_path(str(input_path), str(output_path))

    @pytest.mark.asyncio
    async def test_decrypt_file_path_raises_error_for_missing_input(self, encryption_service):
        """Test that decrypting a non-existent file raises FileNotFoundError."""
        with tempfile.TemporaryDirectory() as tmpdir:
            input_path = Path(tmpdir) / "nonexistent.enc"
            output_path = Path(tmpdir) / "output.txt"

            with pytest.raises(FileNotFoundError, match="Input file not found"):
                await encryption_service.decrypt_file_path(str(input_path), str(output_path))

    @pytest.mark.asyncio
    async def test_encrypt_stream_with_bytes_input(self, encryption_service):
        """Test streaming encryption with bytes input."""
        data = b"test streaming content"
        encrypted = await encryption_service.encrypt_stream(data)

        assert isinstance(encrypted, bytes)
        assert encrypted != data

    @pytest.mark.asyncio
    async def test_encrypt_stream_with_file_like_object(self, encryption_service):
        """Test streaming encryption with file-like object."""
        data = b"test streaming content"
        file_obj = BytesIO(data)

        encrypted = await encryption_service.encrypt_stream(file_obj)

        assert isinstance(encrypted, bytes)
        assert encrypted != data

    @pytest.mark.asyncio
    async def test_decrypt_stream_with_bytes_input(self, encryption_service):
        """Test streaming decryption with bytes input."""
        data = b"test streaming content"
        encrypted = await encryption_service.encrypt_stream(data)
        decrypted = await encryption_service.decrypt_stream(encrypted)

        assert decrypted == data

    @pytest.mark.asyncio
    async def test_decrypt_stream_with_file_like_object(self, encryption_service):
        """Test streaming decryption with file-like object."""
        data = b"test streaming content"
        encrypted = await encryption_service.encrypt_stream(data)
        file_obj = BytesIO(encrypted)

        decrypted = await encryption_service.decrypt_stream(file_obj)

        assert decrypted == data

    @pytest.mark.asyncio
    async def test_encrypt_stream_with_large_data(self, encryption_service):
        """Test streaming encryption with large data."""
        # Create 5MB of data
        data = b"x" * (5 * 1024 * 1024)
        encrypted = await encryption_service.encrypt_stream(data, chunk_size=1024 * 1024)

        assert isinstance(encrypted, bytes)
        assert len(encrypted) > len(data)

    @pytest.mark.asyncio
    async def test_decrypt_stream_with_large_data(self, encryption_service):
        """Test streaming decryption with large data."""
        # Create 5MB of data
        data = b"x" * (5 * 1024 * 1024)
        encrypted = await encryption_service.encrypt_stream(data, chunk_size=1024 * 1024)
        decrypted = await encryption_service.decrypt_stream(encrypted, chunk_size=1024 * 1024)

        assert decrypted == data

    @pytest.mark.asyncio
    async def test_encrypt_stream_raises_error_for_invalid_input(self, encryption_service):
        """Test that encrypting invalid input raises TypeError."""
        with pytest.raises(TypeError, match="Input must be bytes or file-like object"):
            await encryption_service.encrypt_stream("invalid")  # type: ignore[arg-type]

    @pytest.mark.asyncio
    async def test_decrypt_stream_raises_error_for_invalid_input(self, encryption_service):
        """Test that decrypting invalid input raises TypeError."""
        with pytest.raises(TypeError, match="Input must be bytes or file-like object"):
            await encryption_service.decrypt_stream("invalid")  # type: ignore[arg-type]

    @pytest.mark.asyncio
    async def test_encrypt_file_path_with_large_file(self, encryption_service):
        """Test encrypting a large file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            input_path = Path(tmpdir) / "large.bin"
            output_path = Path(tmpdir) / "large.enc"

            # Create 10MB file
            large_data = b"x" * (10 * 1024 * 1024)
            input_path.write_bytes(large_data)

            # Encrypt
            await encryption_service.encrypt_file_path(str(input_path), str(output_path))

            # Verify
            assert output_path.exists()
            encrypted_size = output_path.stat().st_size
            assert encrypted_size > len(large_data)

    @pytest.mark.asyncio
    async def test_file_encryption_roundtrip_preserves_binary_data(self, encryption_service):
        """Test that encryption/decryption preserves binary data integrity."""
        with tempfile.TemporaryDirectory() as tmpdir:
            input_path = Path(tmpdir) / "binary.bin"
            encrypted_path = Path(tmpdir) / "binary.enc"
            decrypted_path = Path(tmpdir) / "binary_out.bin"

            # Create file with all byte values
            binary_data = bytes(range(256)) * 1000  # 256KB of various bytes
            input_path.write_bytes(binary_data)

            # Encrypt and decrypt
            await encryption_service.encrypt_file_path(str(input_path), str(encrypted_path))
            await encryption_service.decrypt_file_path(str(encrypted_path), str(decrypted_path))

            # Verify exact match
            decrypted_data = decrypted_path.read_bytes()
            assert decrypted_data == binary_data

    def test_different_instances_same_key_can_decrypt(self):
        """Test that different instances with same key can decrypt each other's data."""
        service1 = EncryptionService()
        service2 = EncryptionService()

        data = b"test data"
        encrypted = service1.encrypt_bytes(data)
        decrypted = service2.decrypt_bytes(encrypted)

        assert decrypted == data
