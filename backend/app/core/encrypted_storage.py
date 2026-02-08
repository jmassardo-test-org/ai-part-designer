"""
Encrypted file storage wrapper.

Provides transparent encryption/decryption for files stored in S3-compatible storage.
Files are automatically encrypted when uploaded and decrypted when downloaded.
"""

from typing import Any, BinaryIO

from app.core.security import encryption_service
from app.core.storage import StorageBucket, StorageClient


class EncryptedStorageClient(StorageClient):
    """
    Storage client with automatic file encryption/decryption.

    Wraps the base StorageClient to provide transparent encryption
    for files at rest. Files are encrypted before upload and decrypted
    after download.
    """

    ENCRYPTED_METADATA_KEY = "encrypted"
    ENCRYPTED_METADATA_VALUE = "true"

    async def upload_file(
        self,
        bucket: StorageBucket,
        key: str,
        file: BinaryIO | bytes,
        *,
        content_type: str | None = None,
        metadata: dict[str, Any] | None = None,
        encrypt: bool = True,
    ) -> str:
        """
        Upload a file with optional encryption.

        Args:
            bucket: Target bucket
            key: Object key (path)
            file: File-like object or bytes
            content_type: MIME type
            metadata: Custom metadata
            encrypt: Whether to encrypt the file (default: True)

        Returns:
            Object URL

        Note:
            If file is a file-like object, it will be read completely,
            consuming the stream. The stream position is not reset.
        """
        # Prepare metadata
        meta = metadata or {}
        if encrypt:
            meta[self.ENCRYPTED_METADATA_KEY] = self.ENCRYPTED_METADATA_VALUE

        # Encrypt file if requested
        if encrypt:
            if isinstance(file, bytes):
                file = await encryption_service.encrypt_file(file)
            else:
                # Read from file-like object, encrypt, and convert to bytes
                file_data = file.read()
                file = await encryption_service.encrypt_file(file_data)

        # Upload using parent class
        return await super().upload_file(
            bucket=bucket,
            key=key,
            file=file,
            content_type=content_type,
            metadata=meta,
        )

    async def download_file(
        self,
        bucket: StorageBucket,
        key: str,
        *,
        auto_decrypt: bool = True,
    ) -> bytes:
        """
        Download a file with optional automatic decryption.

        Args:
            bucket: Source bucket
            key: Object key (path)
            auto_decrypt: Whether to automatically decrypt if metadata indicates encryption

        Returns:
            File contents as bytes (decrypted if encrypted)
        """
        # Get file metadata to check if encrypted
        try:
            metadata = await self.get_metadata(bucket, key)
            is_encrypted = (
                metadata.get(self.ENCRYPTED_METADATA_KEY) == self.ENCRYPTED_METADATA_VALUE
            )
        except Exception:
            # If we can't get metadata, assume not encrypted
            is_encrypted = False

        # Download using parent class
        file_data = await super().download_file(bucket, key)

        # Decrypt if needed
        if auto_decrypt and is_encrypted:
            file_data = await encryption_service.decrypt_file(file_data)

        return file_data

    async def get_metadata(
        self,
        bucket: StorageBucket,
        key: str,
    ) -> dict[str, Any]:
        """
        Get file metadata.

        Args:
            bucket: Source bucket
            key: Object key (path)

        Returns:
            File metadata dictionary
        """
        bucket_name = self._get_bucket_name(bucket)

        async with self._get_client() as client:
            response = await client.head_object(Bucket=bucket_name, Key=key)
            metadata: dict[str, Any] = response.get("Metadata", {})
            return metadata


# Global encrypted storage client instance
encrypted_storage_client = EncryptedStorageClient()
