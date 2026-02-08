"""
File encryption utilities for transparent at-rest encryption.

Provides helper functions for encrypting/decrypting files on disk.
Used by all CAD export, component storage, and download paths to ensure
files are encrypted at rest and decrypted transparently on access.

Encryption is controlled by the FILE_ENCRYPTION_ENABLED setting,
allowing it to be disabled in development or testing if needed.
"""

from __future__ import annotations

import logging
from pathlib import Path

import aiofiles

from app.core.config import settings
from app.core.security import encryption_service

logger = logging.getLogger(__name__)

# Metadata marker suffix for encrypted files
ENCRYPTED_MARKER_SUFFIX = ".enc"


def is_encryption_enabled() -> bool:
    """Check if file encryption at rest is enabled.

    Returns:
        True if file encryption is enabled.
    """
    return getattr(settings, "FILE_ENCRYPTION_ENABLED", True)


async def encrypt_file_on_disk(file_path: Path) -> Path:
    """Encrypt a file in-place on disk.

    Reads the file, encrypts its contents, and writes it back.
    Creates a .enc marker file to indicate the file is encrypted.

    Args:
        file_path: Path to the file to encrypt.

    Returns:
        The same file path (file is encrypted in-place).

    Raises:
        FileNotFoundError: If the file does not exist.
        IOError: If unable to read/write the file.
    """
    if not is_encryption_enabled():
        return file_path

    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    marker_path = Path(str(file_path) + ENCRYPTED_MARKER_SUFFIX)
    if marker_path.exists():
        logger.debug(f"File already encrypted: {file_path}")
        return file_path

    # Read, encrypt, write back
    async with aiofiles.open(file_path, "rb") as f:
        plaintext = await f.read()

    ciphertext = await encryption_service.encrypt_file(plaintext)

    async with aiofiles.open(file_path, "wb") as f:
        await f.write(ciphertext)

    # Write marker so we know this file is encrypted
    marker_path.write_text("1")

    logger.debug(f"Encrypted file on disk: {file_path}")
    return file_path


async def decrypt_file_from_disk(file_path: Path) -> bytes:
    """Read and decrypt a file from disk.

    If the file has an encryption marker, decrypts its contents.
    If not, returns the raw bytes (backwards compatible with unencrypted files).

    Args:
        file_path: Path to the file to read.

    Returns:
        Decrypted file contents as bytes.

    Raises:
        FileNotFoundError: If the file does not exist.
        IOError: If unable to read the file.
    """
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    async with aiofiles.open(file_path, "rb") as f:
        data = await f.read()

    marker_path = Path(str(file_path) + ENCRYPTED_MARKER_SUFFIX)
    if marker_path.exists() and is_encryption_enabled():
        data = await encryption_service.decrypt_file(data)
        logger.debug(f"Decrypted file from disk: {file_path}")

    return data


async def encrypt_bytes_for_storage(data: bytes) -> bytes:
    """Encrypt bytes before writing to storage.

    Args:
        data: Raw bytes to encrypt.

    Returns:
        Encrypted bytes, or original bytes if encryption is disabled.
    """
    if not is_encryption_enabled():
        return data
    return await encryption_service.encrypt_file(data)


async def decrypt_bytes_from_storage(data: bytes, is_encrypted: bool = True) -> bytes:
    """Decrypt bytes read from storage.

    Args:
        data: Bytes to decrypt.
        is_encrypted: Whether the data is encrypted.

    Returns:
        Decrypted bytes, or original bytes if not encrypted.
    """
    if not is_encrypted or not is_encryption_enabled():
        return data
    return await encryption_service.decrypt_file(data)


async def encrypt_and_write(file_path: Path, content: bytes) -> None:
    """Encrypt content and write to disk in one step.

    Args:
        file_path: Path to write the encrypted file.
        content: Raw bytes to encrypt and write.
    """
    file_path.parent.mkdir(parents=True, exist_ok=True)

    if is_encryption_enabled():
        ciphertext = await encryption_service.encrypt_file(content)
        async with aiofiles.open(file_path, "wb") as f:
            await f.write(ciphertext)

        # Write marker
        marker_path = Path(str(file_path) + ENCRYPTED_MARKER_SUFFIX)
        marker_path.write_text("1")
        logger.debug(f"Encrypted and wrote file: {file_path}")
    else:
        async with aiofiles.open(file_path, "wb") as f:
            await f.write(content)


async def migrate_file_to_encrypted(file_path: Path) -> bool:
    """Migrate an existing unencrypted file to encrypted format.

    Checks if the file is already encrypted (has marker). If not,
    encrypts it in-place.

    Args:
        file_path: Path to the file to migrate.

    Returns:
        True if the file was encrypted, False if already encrypted or skipped.
    """
    if not file_path.exists():
        return False

    marker_path = Path(str(file_path) + ENCRYPTED_MARKER_SUFFIX)
    if marker_path.exists():
        return False  # Already encrypted

    await encrypt_file_on_disk(file_path)
    return True


def is_file_encrypted(file_path: Path) -> bool:
    """Check if a file has been encrypted (has a .enc marker).

    Args:
        file_path: Path to check.

    Returns:
        True if the file has an encryption marker.
    """
    marker_path = Path(str(file_path) + ENCRYPTED_MARKER_SUFFIX)
    return marker_path.exists()


def cleanup_encryption_marker(file_path: Path) -> None:
    """Remove the encryption marker for a file.

    Used when deleting encrypted files.

    Args:
        file_path: Path whose marker should be removed.
    """
    marker_path = Path(str(file_path) + ENCRYPTED_MARKER_SUFFIX)
    if marker_path.exists():
        marker_path.unlink()
