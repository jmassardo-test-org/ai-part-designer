"""
Object storage abstraction layer.

Provides a cloud-agnostic interface for S3-compatible object storage,
supporting AWS S3, GCS, Azure Blob, and MinIO.
"""

import hashlib
import logging
import mimetypes
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any, BinaryIO
from uuid import UUID

import aioboto3
from botocore.exceptions import ClientError

from app.core.config import settings

logger = logging.getLogger(__name__)


class StorageBucket(StrEnum):
    """Available storage buckets."""

    DESIGNS = "designs"
    EXPORTS = "exports"
    THUMBNAILS = "thumbnails"
    UPLOADS = "uploads"
    TEMP = "temp"
    ARCHIVES = "archives"


class StorageClient:
    """
    Async S3-compatible storage client.

    Provides a unified interface for object storage operations
    across different cloud providers.
    """

    def __init__(self) -> None:
        self._session = aioboto3.Session()
        self._config = {
            "endpoint_url": settings.storage_endpoint,
            "aws_access_key_id": settings.storage_access_key,
            "aws_secret_access_key": settings.storage_secret_key,
            "region_name": settings.storage_region,
        }
        self._bucket_prefix = f"ai-part-designer-{settings.ENVIRONMENT}"

    def _get_bucket_name(self, bucket: StorageBucket) -> str:
        """Get full bucket name with environment prefix."""
        return f"{self._bucket_prefix}-{bucket.value}"

    def _get_client(self) -> Any:
        """Get async S3 client context manager."""
        return self._session.client("s3", **self._config)

    # =========================================================================
    # Core Operations
    # =========================================================================

    async def upload_file(
        self,
        bucket: StorageBucket,
        key: str,
        file: BinaryIO | bytes,
        *,
        content_type: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """
        Upload a file to storage.

        Args:
            bucket: Target bucket
            key: Object key (path)
            file: File-like object or bytes
            content_type: MIME type
            metadata: Custom metadata

        Returns:
            Object URL
        """
        bucket_name = self._get_bucket_name(bucket)

        extra_args: dict[str, Any] = {}
        if content_type:
            extra_args["ContentType"] = content_type
        if metadata:
            extra_args["Metadata"] = metadata

        async with self._get_client() as client:
            if isinstance(file, bytes):
                await client.put_object(
                    Bucket=bucket_name,
                    Key=key,
                    Body=file,
                    **extra_args,
                )
            else:
                await client.upload_fileobj(
                    file,
                    bucket_name,
                    key,
                    ExtraArgs=extra_args or None,
                )

        logger.debug(f"Uploaded {key} to {bucket_name}")
        return self._build_url(bucket_name, key)

    async def download_file(
        self,
        bucket: StorageBucket,
        key: str,
    ) -> bytes:
        """
        Download a file from storage.

        Returns:
            File contents as bytes
        """
        bucket_name = self._get_bucket_name(bucket)

        async with self._get_client() as client:
            response = await client.get_object(Bucket=bucket_name, Key=key)
            body_bytes: bytes = await response["Body"].read()
            return body_bytes

    async def delete_file(
        self,
        bucket: StorageBucket,
        key: str,
    ) -> bool:
        """
        Delete a file from storage.

        Returns:
            True if deleted, False if not found
        """
        bucket_name = self._get_bucket_name(bucket)

        try:
            async with self._get_client() as client:
                await client.delete_object(Bucket=bucket_name, Key=key)
            logger.debug(f"Deleted {key} from {bucket_name}")
            return True
        except ClientError as e:
            if e.response["Error"]["Code"] == "404":
                return False
            raise

    async def file_exists(
        self,
        bucket: StorageBucket,
        key: str,
    ) -> bool:
        """Check if a file exists."""
        bucket_name = self._get_bucket_name(bucket)

        try:
            async with self._get_client() as client:
                await client.head_object(Bucket=bucket_name, Key=key)
            return True
        except ClientError:
            return False

    async def get_file_info(
        self,
        bucket: StorageBucket,
        key: str,
    ) -> dict[str, Any] | None:
        """Get file metadata."""
        bucket_name = self._get_bucket_name(bucket)

        try:
            async with self._get_client() as client:
                response = await client.head_object(Bucket=bucket_name, Key=key)
            result: dict[str, Any] = {
                "size": response["ContentLength"],
                "content_type": response.get("ContentType"),
                "last_modified": response["LastModified"],
                "etag": response["ETag"],
                "metadata": response.get("Metadata", {}),
            }
            return result
        except ClientError:
            return None

    # =========================================================================
    # Presigned URLs
    # =========================================================================

    async def generate_presigned_upload_url(
        self,
        bucket: StorageBucket,
        key: str,
        *,
        expires_in: int = 3600,
        content_type: str | None = None,
    ) -> dict[str, Any]:
        """
        Generate a presigned URL for direct upload.

        Returns:
            Dict with url and required fields for upload
        """
        bucket_name = self._get_bucket_name(bucket)

        conditions = []
        fields = {}

        if content_type:
            conditions.append({"Content-Type": content_type})
            fields["Content-Type"] = content_type

        async with self._get_client() as client:
            result: dict[str, Any] = await client.generate_presigned_post(
                Bucket=bucket_name,
                Key=key,
                Fields=fields,
                Conditions=conditions,
                ExpiresIn=expires_in,
            )
            return result

    async def generate_presigned_download_url(
        self,
        bucket: StorageBucket,
        key: str,
        *,
        expires_in: int = 3600,
        filename: str | None = None,
    ) -> str:
        """
        Generate a presigned URL for download.

        Args:
            bucket: Source bucket
            key: Object key
            expires_in: URL expiration in seconds
            filename: Optional filename for Content-Disposition

        Returns:
            Presigned download URL
        """
        bucket_name = self._get_bucket_name(bucket)

        params = {
            "Bucket": bucket_name,
            "Key": key,
        }

        if filename:
            params["ResponseContentDisposition"] = f'attachment; filename="{filename}"'

        async with self._get_client() as client:
            url: str = await client.generate_presigned_url(
                "get_object",
                Params=params,
                ExpiresIn=expires_in,
            )
            return url

    # =========================================================================
    # Listing and Batch Operations
    # =========================================================================

    async def list_files(
        self,
        bucket: StorageBucket,
        prefix: str = "",
        *,
        max_keys: int = 1000,
    ) -> list[dict[str, Any]]:
        """List files in a bucket with optional prefix."""
        bucket_name = self._get_bucket_name(bucket)

        files = []
        async with self._get_client() as client:
            paginator = client.get_paginator("list_objects_v2")

            async for page in paginator.paginate(
                Bucket=bucket_name,
                Prefix=prefix,
                PaginationConfig={"MaxItems": max_keys},
            ):
                for obj in page.get("Contents", []):
                    files.append(
                        {
                            "key": obj["Key"],
                            "size": obj["Size"],
                            "last_modified": obj["LastModified"],
                            "etag": obj["ETag"],
                        }
                    )

        return files

    async def delete_files(
        self,
        bucket: StorageBucket,
        keys: list[str],
    ) -> int:
        """
        Delete multiple files.

        Returns:
            Number of files deleted
        """
        if not keys:
            return 0

        bucket_name = self._get_bucket_name(bucket)

        # S3 delete_objects has a limit of 1000 objects per request
        deleted_count = 0

        for i in range(0, len(keys), 1000):
            batch = keys[i : i + 1000]
            objects = [{"Key": key} for key in batch]

            async with self._get_client() as client:
                response = await client.delete_objects(
                    Bucket=bucket_name,
                    Delete={"Objects": objects},
                )
                deleted_count += len(response.get("Deleted", []))

        logger.info(f"Deleted {deleted_count} files from {bucket_name}")
        return deleted_count

    async def copy_file(
        self,
        source_bucket: StorageBucket,
        source_key: str,
        dest_bucket: StorageBucket,
        dest_key: str,
    ) -> str:
        """
        Copy a file between buckets or keys.

        Returns:
            Destination URL
        """
        source_bucket_name = self._get_bucket_name(source_bucket)
        dest_bucket_name = self._get_bucket_name(dest_bucket)

        async with self._get_client() as client:
            await client.copy_object(
                CopySource={"Bucket": source_bucket_name, "Key": source_key},
                Bucket=dest_bucket_name,
                Key=dest_key,
            )

        return self._build_url(dest_bucket_name, dest_key)

    # =========================================================================
    # Helper Methods
    # =========================================================================

    def _build_url(self, bucket_name: str, key: str) -> str:
        """Build object URL."""
        if settings.STORAGE_ENDPOINT:
            return f"{settings.STORAGE_ENDPOINT}/{bucket_name}/{key}"
        return f"https://{bucket_name}.s3.{settings.STORAGE_REGION}.amazonaws.com/{key}"

    @staticmethod
    def generate_key(
        prefix: str,
        filename: str,
        *,
        include_timestamp: bool = True,
        unique_id: str | UUID | None = None,
    ) -> str:
        """
        Generate a storage key for a file.

        Args:
            prefix: Key prefix (e.g., "designs/user-123")
            filename: Original filename
            include_timestamp: Include timestamp in key
            unique_id: Optional unique identifier

        Returns:
            Generated key path
        """
        # Sanitize filename
        safe_filename = Path(filename).name

        parts = [prefix.strip("/")]

        if include_timestamp:
            parts.append(datetime.now(tz=UTC).strftime("%Y/%m/%d"))

        if unique_id:
            parts.append(str(unique_id))

        parts.append(safe_filename)

        return "/".join(parts)

    @staticmethod
    def get_content_type(filename: str) -> str:
        """Guess content type from filename."""
        content_type, _ = mimetypes.guess_type(filename)
        return content_type or "application/octet-stream"

    @staticmethod
    def calculate_checksum(data: bytes) -> str:
        """Calculate MD5 checksum of data."""
        return hashlib.md5(data).hexdigest()


# Global storage client instance
storage_client = StorageClient()


async def get_storage() -> StorageClient:
    """Dependency for getting storage client."""
    return storage_client
