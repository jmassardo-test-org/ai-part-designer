"""
Tests for StorageService.

Tests S3/MinIO storage operations: copy, delete, list, and presigned URLs.
"""

from __future__ import annotations

from unittest.mock import ANY, MagicMock, patch

import pytest

from app.services.storage_service import StorageService

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_s3_client():
    """Create a mock S3 client."""
    client = MagicMock()
    client.copy_object = MagicMock()
    client.delete_object = MagicMock()
    client.list_objects_v2 = MagicMock()
    client.generate_presigned_url = MagicMock(return_value="https://presigned.url")
    return client


@pytest.fixture
def storage_service(mock_s3_client):
    """Create a StorageService with mocked S3 client."""
    with patch("app.services.storage_service.boto3") as mock_boto3:
        mock_boto3.client.return_value = mock_s3_client
        service = StorageService()
        # Override the client with our mock
        service.s3_client = mock_s3_client
        return service


# =============================================================================
# Copy File Tests
# =============================================================================


class TestCopyFile:
    """Tests for the copy_file method."""

    def test_copy_file_same_bucket(self, storage_service, mock_s3_client):
        """Test copying a file within the same bucket."""
        storage_service.copy_file(
            source_key="source/file.stl",
            destination_key="dest/file.stl",
        )

        mock_s3_client.copy_object.assert_called_once()
        call_args = mock_s3_client.copy_object.call_args
        assert call_args.kwargs["Key"] == "dest/file.stl"
        assert "source/file.stl" in call_args.kwargs["CopySource"]

    def test_copy_file_different_bucket(self, storage_service, mock_s3_client):
        """Test copying a file to a different bucket."""
        storage_service.copy_file(
            source_key="source/file.stl",
            destination_key="dest/file.stl",
            source_bucket="source-bucket",
            destination_bucket="dest-bucket",
        )

        mock_s3_client.copy_object.assert_called_once()
        call_args = mock_s3_client.copy_object.call_args
        assert call_args.kwargs["Bucket"] == "dest-bucket"
        assert "source-bucket" in call_args.kwargs["CopySource"]

    def test_copy_file_handles_error(self, storage_service, mock_s3_client):
        """Test that copy_file raises on S3 error."""
        from botocore.exceptions import ClientError

        mock_s3_client.copy_object.side_effect = ClientError(
            {"Error": {"Code": "NoSuchKey", "Message": "Key not found"}},
            "CopyObject",
        )

        with pytest.raises(ClientError):
            storage_service.copy_file(
                source_key="nonexistent/file.stl",
                destination_key="dest/file.stl",
            )


# =============================================================================
# Delete File Tests
# =============================================================================


class TestDeleteFile:
    """Tests for the delete_file method."""

    def test_delete_file(self, storage_service, mock_s3_client):
        """Test deleting a single file."""
        storage_service.delete_file("path/to/file.stl")

        mock_s3_client.delete_object.assert_called_once()
        call_args = mock_s3_client.delete_object.call_args
        assert call_args.kwargs["Key"] == "path/to/file.stl"

    def test_delete_file_custom_bucket(self, storage_service, mock_s3_client):
        """Test deleting from a custom bucket."""
        storage_service.delete_file("path/to/file.stl", bucket="custom-bucket")

        call_args = mock_s3_client.delete_object.call_args
        assert call_args.kwargs["Bucket"] == "custom-bucket"


# =============================================================================
# List Files Tests
# =============================================================================


class TestListFiles:
    """Tests for the list_files method."""

    def test_list_files_empty(self, storage_service, mock_s3_client):
        """Test listing files when prefix has no matches."""
        mock_s3_client.list_objects_v2.return_value = {}

        result = storage_service.list_files("empty/prefix/")

        assert result == []

    def test_list_files_with_contents(self, storage_service, mock_s3_client):
        """Test listing files with results."""
        mock_s3_client.list_objects_v2.return_value = {
            "Contents": [
                {"Key": "prefix/file1.stl", "Size": 1000},
                {"Key": "prefix/file2.step", "Size": 2000},
            ]
        }

        result = storage_service.list_files("prefix/")

        assert len(result) == 2
        assert result[0]["Key"] == "prefix/file1.stl"
        assert result[1]["Size"] == 2000


# =============================================================================
# Presigned URL Tests
# =============================================================================


class TestPresignedUrl:
    """Tests for the generate_presigned_url method."""

    def test_generate_presigned_url_default_expiry(self, storage_service, mock_s3_client):
        """Test generating presigned URL with default expiry."""
        mock_s3_client.generate_presigned_url.return_value = (
            "https://bucket.s3.amazonaws.com/key?signature=abc"
        )

        result = storage_service.generate_presigned_url("path/to/file.stl")

        assert "s3.amazonaws.com" in result
        mock_s3_client.generate_presigned_url.assert_called_once_with(
            "get_object",
            Params={"Bucket": ANY, "Key": "path/to/file.stl"},
            ExpiresIn=3600,  # Default 1 hour
        )

    def test_generate_presigned_url_custom_expiry(self, storage_service, mock_s3_client):
        """Test generating presigned URL with custom expiry."""
        storage_service.generate_presigned_url(
            "path/to/file.stl",
            expiry_seconds=7200,
        )

        call_args = mock_s3_client.generate_presigned_url.call_args
        assert call_args.kwargs["ExpiresIn"] == 7200


# =============================================================================
# Batch Operations Tests
# =============================================================================


class TestBatchOperations:
    """Tests for batch file operations."""

    def test_copy_multiple_files(self, storage_service, mock_s3_client):
        """Test copying multiple files."""
        files = ["file1.stl", "file2.step", "file3.obj"]
        source_prefix = "source/designs/"
        dest_prefix = "dest/designs/"

        for f in files:
            storage_service.copy_file(
                source_key=f"{source_prefix}{f}",
                destination_key=f"{dest_prefix}{f}",
            )

        assert mock_s3_client.copy_object.call_count == 3

    def test_delete_multiple_files(self, storage_service, mock_s3_client):
        """Test deleting multiple files."""
        keys = ["path/file1.stl", "path/file2.step"]

        for key in keys:
            storage_service.delete_file(key)

        assert mock_s3_client.delete_object.call_count == 2


# =============================================================================
# Configuration Tests
# =============================================================================


class TestConfiguration:
    """Tests for service configuration."""

    def test_default_bucket_from_settings(self):
        """Test that default bucket is read from settings."""
        with patch("app.services.storage_service.get_settings") as mock_settings:
            mock_settings.return_value.S3_BUCKET = "configured-bucket"
            with patch("app.services.storage_service.boto3"):
                service = StorageService()
                assert service.default_bucket == "configured-bucket"

    def test_endpoint_url_for_minio(self):
        """Test that endpoint URL is set for MinIO/local S3."""
        with patch("app.services.storage_service.get_settings") as mock_settings:
            mock_settings.return_value.S3_ENDPOINT_URL = "http://localhost:9000"
            mock_settings.return_value.S3_BUCKET = "test-bucket"
            with patch("app.services.storage_service.boto3") as mock_boto3:
                StorageService()
                mock_boto3.client.assert_called_once()
                call_kwargs = mock_boto3.client.call_args.kwargs
                assert call_kwargs.get("endpoint_url") == "http://localhost:9000"


# =============================================================================
# Error Handling Tests
# =============================================================================


class TestErrorHandling:
    """Tests for error handling in storage operations."""

    def test_copy_nonexistent_source(self, storage_service, mock_s3_client):
        """Test copying from nonexistent source."""
        from botocore.exceptions import ClientError

        error_response = {"Error": {"Code": "404", "Message": "Not Found"}}
        mock_s3_client.copy_object.side_effect = ClientError(error_response, "CopyObject")

        with pytest.raises(ClientError) as exc_info:
            storage_service.copy_file("nonexistent/key", "dest/key")

        assert exc_info.value.response["Error"]["Code"] == "404"

    def test_access_denied_error(self, storage_service, mock_s3_client):
        """Test handling access denied errors."""
        from botocore.exceptions import ClientError

        error_response = {"Error": {"Code": "AccessDenied", "Message": "Access Denied"}}
        mock_s3_client.delete_object.side_effect = ClientError(error_response, "DeleteObject")

        with pytest.raises(ClientError) as exc_info:
            storage_service.delete_file("restricted/file.stl")

        assert exc_info.value.response["Error"]["Code"] == "AccessDenied"
