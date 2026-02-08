"""
Key rotation service for encryption key management.

Provides key versioning, rotation procedures, and re-encryption
of data encrypted with old keys. Supports both EncryptionService
(Fernet-based) and KMS-based envelope encryption.
"""

from __future__ import annotations

import base64
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from app.core.config import settings
from app.core.file_encryption import (
    ENCRYPTED_MARKER_SUFFIX,
    is_file_encrypted,
)

if TYPE_CHECKING:
    from datetime import datetime

logger = logging.getLogger(__name__)


class KeyRotationError(Exception):
    """Error during key rotation."""


@dataclass
class KeyVersion:
    """Represents a versioned encryption key.

    Attributes:
        version: Sequential version number.
        key: The secret key string.
        created_at: When this key version was created.
        is_active: Whether this is the currently active key.
    """

    version: int
    key: str
    created_at: datetime
    is_active: bool = False


@dataclass
class RotationResult:
    """Result of a key rotation or re-encryption operation.

    Attributes:
        files_processed: Number of files processed.
        files_re_encrypted: Number of files successfully re-encrypted.
        files_skipped: Number of files skipped (not encrypted or already current).
        files_failed: Number of files that failed re-encryption.
        errors: List of error details.
        duration_seconds: Time taken for the operation.
    """

    files_processed: int = 0
    files_re_encrypted: int = 0
    files_skipped: int = 0
    files_failed: int = 0
    errors: list[str] = field(default_factory=list)
    duration_seconds: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization.

        Returns:
            Dictionary representation of the result.
        """
        return {
            "files_processed": self.files_processed,
            "files_re_encrypted": self.files_re_encrypted,
            "files_skipped": self.files_skipped,
            "files_failed": self.files_failed,
            "errors": self.errors[:50],  # Limit error details
            "duration_seconds": round(self.duration_seconds, 2),
        }


def _derive_fernet_key(secret_key: str) -> bytes:
    """Derive a Fernet-compatible key from a secret string.

    Uses PBKDF2 with SHA256 to derive a 32-byte key, then
    base64-encodes it for Fernet compatibility.

    Args:
        secret_key: The secret key string.

    Returns:
        Base64-encoded derived key bytes.
    """
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=b"ai-part-designer-salt",
        iterations=100000,
    )
    return base64.urlsafe_b64encode(kdf.derive(secret_key.encode()))


class KeyRotationService:
    """Service for managing encryption key rotation.

    Supports decrypting data with old keys and re-encrypting with the
    current key. Key versions are managed through configuration.
    """

    def __init__(
        self,
        current_key: str | None = None,
        previous_keys: list[str] | None = None,
    ) -> None:
        """Initialize key rotation service.

        Args:
            current_key: The current encryption key. Defaults to SECRET_KEY.
            previous_keys: List of previous keys for decryption during rotation.
        """
        self._current_key = current_key or settings.SECRET_KEY
        self._previous_keys = previous_keys or []

        # Build Fernet instances for all known keys
        self._current_fernet = Fernet(_derive_fernet_key(self._current_key))
        self._previous_fernets = [Fernet(_derive_fernet_key(key)) for key in self._previous_keys]

    def decrypt_with_any_key(self, encrypted_data: bytes) -> bytes:
        """Attempt to decrypt data with current key, falling back to previous keys.

        Args:
            encrypted_data: The encrypted bytes.

        Returns:
            Decrypted bytes.

        Raises:
            KeyRotationError: If no key can decrypt the data.
        """
        # Try current key first
        try:
            return self._current_fernet.decrypt(encrypted_data)
        except InvalidToken:
            pass

        # Try previous keys
        for i, fernet in enumerate(self._previous_fernets):
            try:
                result = fernet.decrypt(encrypted_data)
                logger.info(f"Decrypted with previous key version {i}")
                return result
            except InvalidToken:
                continue

        raise KeyRotationError(
            "Unable to decrypt data with any known key. "
            "Data may be corrupted or encrypted with an unknown key."
        )

    def re_encrypt(self, encrypted_data: bytes) -> bytes:
        """Decrypt with any known key and re-encrypt with the current key.

        Args:
            encrypted_data: Data encrypted with any known key version.

        Returns:
            Data re-encrypted with the current key.

        Raises:
            KeyRotationError: If decryption fails with all known keys.
        """
        plaintext = self.decrypt_with_any_key(encrypted_data)
        return self._current_fernet.encrypt(plaintext)

    async def rotate_file(self, file_path: Path) -> bool:
        """Re-encrypt a single file with the current key.

        Reads the file, decrypts with any known key, and re-encrypts
        with the current key.

        Args:
            file_path: Path to the encrypted file.

        Returns:
            True if the file was re-encrypted, False if skipped.

        Raises:
            KeyRotationError: If decryption fails.
            FileNotFoundError: If the file does not exist.
        """
        import aiofiles

        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        if not is_file_encrypted(file_path):
            return False  # Not encrypted, skip

        # Read encrypted data
        async with aiofiles.open(file_path, "rb") as f:
            encrypted_data = await f.read()

        # Try to decrypt with current key first — if it works, no rotation needed
        try:
            self._current_fernet.decrypt(encrypted_data)
            return False  # Already encrypted with current key
        except InvalidToken:
            pass

        # Re-encrypt with current key
        re_encrypted = self.re_encrypt(encrypted_data)

        async with aiofiles.open(file_path, "wb") as f:
            await f.write(re_encrypted)

        logger.info(f"Re-encrypted file: {file_path}")
        return True

    async def rotate_directory(self, directory: Path, pattern: str = "*") -> RotationResult:
        """Re-encrypt all encrypted files in a directory.

        Args:
            directory: Directory to scan.
            pattern: Glob pattern for files to process.

        Returns:
            RotationResult with statistics.
        """
        result = RotationResult()
        start_time = time.monotonic()

        if not directory.exists():
            logger.warning(f"Directory not found: {directory}")
            result.duration_seconds = time.monotonic() - start_time
            return result

        for file_path in directory.rglob(pattern):
            if file_path.is_dir():
                continue
            if file_path.suffix == ENCRYPTED_MARKER_SUFFIX:
                continue  # Skip marker files

            result.files_processed += 1

            try:
                if await self.rotate_file(file_path):
                    result.files_re_encrypted += 1
                else:
                    result.files_skipped += 1
            except Exception as e:
                result.files_failed += 1
                result.errors.append(f"{file_path}: {e}")
                logger.error(f"Failed to re-encrypt {file_path}: {e}")

        result.duration_seconds = time.monotonic() - start_time
        return result

    async def rotate_all_cad_files(self) -> dict[str, Any]:
        """Re-encrypt all CAD files across all storage directories.

        Scans component files, CAD exports, and uploads.

        Returns:
            Dictionary with rotation results per directory.
        """
        results: dict[str, Any] = {}
        directories = [
            ("components", Path(settings.UPLOAD_DIR) / "components"),
            ("cad_exports", Path(settings.UPLOAD_DIR) / "cad_exports"),
            ("uploads", Path(settings.UPLOAD_DIR)),
        ]

        for name, directory in directories:
            if directory.exists():
                rotation_result = await self.rotate_directory(directory)
                results[name] = rotation_result.to_dict()
                logger.info(
                    f"Key rotation for {name}: "
                    f"processed={rotation_result.files_processed}, "
                    f"re-encrypted={rotation_result.files_re_encrypted}, "
                    f"failed={rotation_result.files_failed}"
                )
            else:
                results[name] = {"skipped": True, "reason": "directory not found"}

        return results


def get_key_rotation_service(
    previous_keys: list[str] | None = None,
) -> KeyRotationService:
    """Create a KeyRotationService with the current and previous keys.

    Args:
        previous_keys: List of previous SECRET_KEY values for rotation.

    Returns:
        Configured KeyRotationService instance.
    """
    return KeyRotationService(previous_keys=previous_keys)
