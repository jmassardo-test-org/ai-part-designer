"""
Tests for EncryptedStorageClient.

Tests automatic encryption/decryption for file storage operations.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from app.core.encrypted_storage import EncryptedStorageClient
from app.core.storage import StorageBucket


class TestEncryptedStorageClient:
    """Tests for EncryptedStorageClient class."""

    @pytest.fixture
    def mock_s3_client(self):
        """Create a mock S3 client."""
        return AsyncMock()

    @pytest.fixture
    def encrypted_storage_client(self):
        """Create an encrypted storage client instance."""
        with patch("app.core.storage.settings") as mock_settings:
            mock_settings.storage_endpoint = "http://localhost:9000"
            mock_settings.storage_access_key = "minioadmin"
            mock_settings.storage_secret_key = "minioadmin"
            mock_settings.storage_region = "us-east-1"
            mock_settings.ENVIRONMENT = "test"
            return EncryptedStorageClient()

    @pytest.mark.asyncio
    async def test_upload_file_with_encryption_enabled(
        self, encrypted_storage_client, mock_s3_client
    ):
        """Test uploading file with encryption enabled."""
        file_content = b"test file content"

        with patch.object(encrypted_storage_client, "_get_client") as mock_get_client:
            mock_client_ctx = AsyncMock()
            mock_client_ctx.__aenter__.return_value = mock_s3_client
            mock_get_client.return_value = mock_client_ctx

            await encrypted_storage_client.upload_file(
                bucket=StorageBucket.UPLOADS,
                key="test/file.txt",
                file=file_content,
                encrypt=True,
            )

            # Verify upload was called
            mock_s3_client.put_object.assert_called_once()
            call_kwargs = mock_s3_client.put_object.call_args.kwargs

            # Verify metadata includes encryption marker
            assert "Metadata" in call_kwargs
            assert call_kwargs["Metadata"]["encrypted"] == "true"

            # Verify file content was encrypted (should be different from original)
            uploaded_content = call_kwargs["Body"]
            assert uploaded_content != file_content
            assert len(uploaded_content) > len(file_content)

    @pytest.mark.asyncio
    async def test_upload_file_with_encryption_disabled(
        self, encrypted_storage_client, mock_s3_client
    ):
        """Test uploading file with encryption disabled."""
        file_content = b"test file content"

        with patch.object(encrypted_storage_client, "_get_client") as mock_get_client:
            mock_client_ctx = AsyncMock()
            mock_client_ctx.__aenter__.return_value = mock_s3_client
            mock_get_client.return_value = mock_client_ctx

            await encrypted_storage_client.upload_file(
                bucket=StorageBucket.UPLOADS,
                key="test/file.txt",
                file=file_content,
                encrypt=False,
            )

            # Verify upload was called
            mock_s3_client.put_object.assert_called_once()
            call_kwargs = mock_s3_client.put_object.call_args.kwargs

            # Verify metadata does not include encryption marker
            assert "encrypted" not in call_kwargs.get("Metadata", {})

            # Verify file content was not encrypted
            uploaded_content = call_kwargs["Body"]
            assert uploaded_content == file_content

    @pytest.mark.asyncio
    async def test_upload_file_with_custom_metadata(
        self, encrypted_storage_client, mock_s3_client
    ):
        """Test uploading file with custom metadata preserved."""
        file_content = b"test file content"
        custom_metadata = {"author": "test", "version": "1.0"}

        with patch.object(encrypted_storage_client, "_get_client") as mock_get_client:
            mock_client_ctx = AsyncMock()
            mock_client_ctx.__aenter__.return_value = mock_s3_client
            mock_get_client.return_value = mock_client_ctx

            await encrypted_storage_client.upload_file(
                bucket=StorageBucket.UPLOADS,
                key="test/file.txt",
                file=file_content,
                metadata=custom_metadata,
                encrypt=True,
            )

            # Verify custom metadata is preserved along with encryption marker
            call_kwargs = mock_s3_client.put_object.call_args.kwargs
            metadata = call_kwargs["Metadata"]
            assert metadata["author"] == "test"
            assert metadata["version"] == "1.0"
            assert metadata["encrypted"] == "true"

    @pytest.mark.asyncio
    async def test_download_file_with_auto_decrypt(self, encrypted_storage_client, mock_s3_client):
        """Test downloading and auto-decrypting an encrypted file."""
        original_content = b"test file content"

        # Encrypt the content
        from app.core.security import encryption_service

        encrypted_content = await encryption_service.encrypt_file(original_content)

        with patch.object(encrypted_storage_client, "_get_client") as mock_get_client:
            mock_client_ctx = AsyncMock()
            mock_client_ctx.__aenter__.return_value = mock_s3_client
            mock_get_client.return_value = mock_client_ctx

            # Mock head_object to return encrypted metadata
            mock_s3_client.head_object.return_value = {"Metadata": {"encrypted": "true"}}

            # Mock get_object to return encrypted content
            mock_response = {"Body": AsyncMock()}
            mock_response["Body"].read.return_value = encrypted_content
            mock_s3_client.get_object.return_value = mock_response

            # Download with auto-decrypt
            result = await encrypted_storage_client.download_file(
                bucket=StorageBucket.UPLOADS,
                key="test/file.txt",
                auto_decrypt=True,
            )

            # Verify decrypted content matches original
            assert result == original_content

    @pytest.mark.asyncio
    async def test_download_file_without_auto_decrypt(
        self, encrypted_storage_client, mock_s3_client
    ):
        """Test downloading encrypted file without decryption."""
        original_content = b"test file content"

        # Encrypt the content
        from app.core.security import encryption_service

        encrypted_content = await encryption_service.encrypt_file(original_content)

        with patch.object(encrypted_storage_client, "_get_client") as mock_get_client:
            mock_client_ctx = AsyncMock()
            mock_client_ctx.__aenter__.return_value = mock_s3_client
            mock_get_client.return_value = mock_client_ctx

            # Mock head_object to return encrypted metadata
            mock_s3_client.head_object.return_value = {"Metadata": {"encrypted": "true"}}

            # Mock get_object to return encrypted content
            mock_response = {"Body": AsyncMock()}
            mock_response["Body"].read.return_value = encrypted_content
            mock_s3_client.get_object.return_value = mock_response

            # Download without auto-decrypt
            result = await encrypted_storage_client.download_file(
                bucket=StorageBucket.UPLOADS,
                key="test/file.txt",
                auto_decrypt=False,
            )

            # Verify content is still encrypted
            assert result == encrypted_content
            assert result != original_content

    @pytest.mark.asyncio
    async def test_download_file_not_encrypted(self, encrypted_storage_client, mock_s3_client):
        """Test downloading a non-encrypted file."""
        file_content = b"test file content"

        with patch.object(encrypted_storage_client, "_get_client") as mock_get_client:
            mock_client_ctx = AsyncMock()
            mock_client_ctx.__aenter__.return_value = mock_s3_client
            mock_get_client.return_value = mock_client_ctx

            # Mock head_object to return no encryption metadata
            mock_s3_client.head_object.return_value = {"Metadata": {}}

            # Mock get_object to return plain content
            mock_response = {"Body": AsyncMock()}
            mock_response["Body"].read.return_value = file_content
            mock_s3_client.get_object.return_value = mock_response

            # Download with auto-decrypt
            result = await encrypted_storage_client.download_file(
                bucket=StorageBucket.UPLOADS,
                key="test/file.txt",
                auto_decrypt=True,
            )

            # Verify content is returned as-is
            assert result == file_content

    @pytest.mark.asyncio
    async def test_download_file_handles_metadata_error_gracefully(
        self, encrypted_storage_client, mock_s3_client
    ):
        """Test that download handles metadata errors gracefully."""
        file_content = b"test file content"

        with patch.object(encrypted_storage_client, "_get_client") as mock_get_client:
            mock_client_ctx = AsyncMock()
            mock_client_ctx.__aenter__.return_value = mock_s3_client
            mock_get_client.return_value = mock_client_ctx

            # Mock head_object to raise an error
            mock_s3_client.head_object.side_effect = Exception("Metadata error")

            # Mock get_object to return plain content
            mock_response = {"Body": AsyncMock()}
            mock_response["Body"].read.return_value = file_content
            mock_s3_client.get_object.return_value = mock_response

            # Download should handle metadata error and treat as unencrypted
            result = await encrypted_storage_client.download_file(
                bucket=StorageBucket.UPLOADS,
                key="test/file.txt",
                auto_decrypt=True,
            )

            # Verify content is returned as-is
            assert result == file_content

    @pytest.mark.asyncio
    async def test_get_metadata_returns_file_metadata(
        self, encrypted_storage_client, mock_s3_client
    ):
        """Test getting file metadata."""
        expected_metadata = {"encrypted": "true", "author": "test"}

        with patch.object(encrypted_storage_client, "_get_client") as mock_get_client:
            mock_client_ctx = AsyncMock()
            mock_client_ctx.__aenter__.return_value = mock_s3_client
            mock_get_client.return_value = mock_client_ctx

            # Mock head_object
            mock_s3_client.head_object.return_value = {"Metadata": expected_metadata}

            # Get metadata
            result = await encrypted_storage_client.get_metadata(
                bucket=StorageBucket.UPLOADS,
                key="test/file.txt",
            )

            # Verify metadata matches
            assert result == expected_metadata
            mock_s3_client.head_object.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_metadata_handles_missing_metadata(
        self, encrypted_storage_client, mock_s3_client
    ):
        """Test getting metadata when it doesn't exist."""
        with patch.object(encrypted_storage_client, "_get_client") as mock_get_client:
            mock_client_ctx = AsyncMock()
            mock_client_ctx.__aenter__.return_value = mock_s3_client
            mock_get_client.return_value = mock_client_ctx

            # Mock head_object without Metadata key
            mock_s3_client.head_object.return_value = {}

            # Get metadata
            result = await encrypted_storage_client.get_metadata(
                bucket=StorageBucket.UPLOADS,
                key="test/file.txt",
            )

            # Verify empty dict is returned
            assert result == {}

    @pytest.mark.asyncio
    async def test_upload_file_with_file_like_object(
        self, encrypted_storage_client, mock_s3_client
    ):
        """Test uploading file-like object with encryption."""
        from io import BytesIO

        file_content = b"test file content"
        file_obj = BytesIO(file_content)

        with patch.object(encrypted_storage_client, "_get_client") as mock_get_client:
            mock_client_ctx = AsyncMock()
            mock_client_ctx.__aenter__.return_value = mock_s3_client
            mock_get_client.return_value = mock_client_ctx

            await encrypted_storage_client.upload_file(
                bucket=StorageBucket.UPLOADS,
                key="test/file.txt",
                file=file_obj,
                encrypt=True,
            )

            # Verify upload was called
            mock_s3_client.put_object.assert_called_once()
            call_kwargs = mock_s3_client.put_object.call_args.kwargs

            # Verify file was encrypted
            uploaded_content = call_kwargs["Body"]
            assert uploaded_content != file_content
            assert call_kwargs["Metadata"]["encrypted"] == "true"

    @pytest.mark.asyncio
    async def test_encryption_roundtrip_through_storage(
        self, encrypted_storage_client, mock_s3_client
    ):
        """Test full roundtrip: upload encrypted, download decrypted."""
        original_content = b"test file content for roundtrip"
        stored_content = None

        with patch.object(encrypted_storage_client, "_get_client") as mock_get_client:
            mock_client_ctx = AsyncMock()
            mock_client_ctx.__aenter__.return_value = mock_s3_client
            mock_get_client.return_value = mock_client_ctx

            # Upload
            def store_content(**kwargs):
                nonlocal stored_content
                stored_content = kwargs["Body"]
                stored_metadata = kwargs.get("Metadata", {})
                # Store metadata for later retrieval
                mock_s3_client.head_object.return_value = {"Metadata": stored_metadata}

            mock_s3_client.put_object.side_effect = store_content

            await encrypted_storage_client.upload_file(
                bucket=StorageBucket.UPLOADS,
                key="test/roundtrip.txt",
                file=original_content,
                encrypt=True,
            )

            # Download
            mock_response = {"Body": AsyncMock()}
            mock_response["Body"].read.return_value = stored_content
            mock_s3_client.get_object.return_value = mock_response

            result = await encrypted_storage_client.download_file(
                bucket=StorageBucket.UPLOADS,
                key="test/roundtrip.txt",
                auto_decrypt=True,
            )

            # Verify roundtrip integrity
            assert result == original_content
