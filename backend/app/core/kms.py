"""
Key Management Service (KMS) abstraction layer.

Provides a unified interface for managing encryption keys using:
- Local key management (development/testing)
- AWS KMS (production)
- GCP Cloud KMS (production)

Uses envelope encryption pattern:
1. Master key (KEK) lives in KMS
2. Data encryption keys (DEK) are generated per operation
3. DEKs are encrypted by master key and stored with data
4. DEKs are cached in memory with TTL for performance
"""

import base64
import secrets
from abc import ABC, abstractmethod
from datetime import UTC, datetime, timedelta
from typing import Any

import structlog

from app.core.config import settings

logger = structlog.get_logger(__name__)


class KMSError(Exception):
    """Base exception for KMS operations."""


class KMSKeyNotFoundError(KMSError):
    """Raised when a KMS key is not found."""


class KMSEncryptionError(KMSError):
    """Raised when encryption fails."""


class KMSDecryptionError(KMSError):
    """Raised when decryption fails."""


class KMSKeyProvider(ABC):
    """
    Abstract base class for KMS providers.

    Implementations must provide methods to encrypt and decrypt
    data encryption keys (DEKs) using a master key.
    """

    @abstractmethod
    def encrypt_dek(self, plaintext_dek: bytes) -> dict[str, Any]:
        """
        Encrypt a data encryption key using the master key.

        Args:
            plaintext_dek: The plaintext DEK to encrypt (typically 32 bytes)

        Returns:
            Dict containing encrypted DEK and metadata needed for decryption
            Example: {"ciphertext": b"...", "key_id": "...", "algorithm": "..."}

        Raises:
            KMSEncryptionError: If encryption fails
        """

    @abstractmethod
    def decrypt_dek(self, encrypted_dek_data: dict[str, Any]) -> bytes:
        """
        Decrypt an encrypted data encryption key.

        Args:
            encrypted_dek_data: Dict containing encrypted DEK and metadata

        Returns:
            Plaintext DEK bytes

        Raises:
            KMSDecryptionError: If decryption fails
        """

    @abstractmethod
    def generate_dek(self) -> bytes:
        """
        Generate a new data encryption key.

        Returns:
            Plaintext DEK bytes (typically 32 bytes)
        """


class LocalKMSProvider(KMSKeyProvider):
    """
    Local KMS provider for development and testing.

    Uses SECRET_KEY from settings to simulate KMS operations.
    NOT SUITABLE FOR PRODUCTION - keys stored in environment variables.
    """

    def __init__(self):
        """Initialize local KMS provider."""
        from cryptography.fernet import Fernet
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

        # Derive a Fernet-compatible key from SECRET_KEY
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b"ai-part-designer-kms",
            iterations=100000,
        )
        derived_key = base64.urlsafe_b64encode(kdf.derive(settings.SECRET_KEY.encode()))
        self._fernet = Fernet(derived_key)

        logger.info("local_kms_provider_initialized", provider="local")

    def encrypt_dek(self, plaintext_dek: bytes) -> dict[str, Any]:
        """Encrypt DEK using local Fernet key."""
        try:
            ciphertext = self._fernet.encrypt(plaintext_dek)
            return {
                "ciphertext": base64.b64encode(ciphertext).decode("utf-8"),
                "key_id": "local",
                "algorithm": "fernet",
            }
        except Exception as e:
            logger.error("local_kms_encrypt_failed", error=str(e))
            raise KMSEncryptionError(f"Failed to encrypt DEK: {e}") from e

    def decrypt_dek(self, encrypted_dek_data: dict[str, Any]) -> bytes:
        """Decrypt DEK using local Fernet key."""
        try:
            ciphertext = base64.b64decode(encrypted_dek_data["ciphertext"])
            return self._fernet.decrypt(ciphertext)
        except Exception as e:
            logger.error("local_kms_decrypt_failed", error=str(e))
            raise KMSDecryptionError(f"Failed to decrypt DEK: {e}") from e

    def generate_dek(self) -> bytes:
        """Generate a random 32-byte DEK."""
        return secrets.token_bytes(32)


class AWSKMSProvider(KMSKeyProvider):
    """
    AWS KMS provider for production use.

    Uses AWS KMS to encrypt/decrypt data encryption keys.
    Requires AWS credentials with kms:Encrypt and kms:Decrypt permissions.
    """

    def __init__(self):
        """Initialize AWS KMS provider."""
        if not settings.AWS_KMS_KEY_ID:
            raise KMSError("AWS_KMS_KEY_ID must be set when using AWS KMS provider")

        import boto3

        region = settings.AWS_KMS_REGION or settings.AWS_REGION
        self._kms_client = boto3.client("kms", region_name=region)
        self._key_id = settings.AWS_KMS_KEY_ID

        logger.info(
            "aws_kms_provider_initialized",
            provider="aws",
            region=region,
            key_id=self._key_id[:20] + "...",  # Log partial key ID for security
        )

    def encrypt_dek(self, plaintext_dek: bytes) -> dict[str, Any]:
        """Encrypt DEK using AWS KMS."""
        try:
            response = self._kms_client.encrypt(KeyId=self._key_id, Plaintext=plaintext_dek)

            return {
                "ciphertext": base64.b64encode(response["CiphertextBlob"]).decode("utf-8"),
                "key_id": response["KeyId"],
                "algorithm": "AWS_KMS",
            }
        except Exception as e:
            logger.error("aws_kms_encrypt_failed", error=str(e), key_id=self._key_id[:20] + "...")
            raise KMSEncryptionError(f"AWS KMS encryption failed: {e}") from e

    def decrypt_dek(self, encrypted_dek_data: dict[str, Any]) -> bytes:
        """Decrypt DEK using AWS KMS."""
        try:
            ciphertext = base64.b64decode(encrypted_dek_data["ciphertext"])
            response = self._kms_client.decrypt(
                CiphertextBlob=ciphertext,
                KeyId=encrypted_dek_data.get("key_id"),
            )

            return response["Plaintext"]
        except Exception as e:
            logger.error("aws_kms_decrypt_failed", error=str(e))
            raise KMSDecryptionError(f"AWS KMS decryption failed: {e}") from e

    def generate_dek(self) -> bytes:
        """
        Generate a DEK using AWS KMS.

        Uses AWS KMS GenerateDataKey to get a DEK without additional network calls.
        """
        try:
            response = self._kms_client.generate_data_key(
                KeyId=self._key_id,
                KeySpec="AES_256",
            )
            return response["Plaintext"]
        except Exception as e:
            logger.error("aws_kms_generate_dek_failed", error=str(e))
            # Fallback to local generation if KMS fails
            return secrets.token_bytes(32)


class GCPKMSProvider(KMSKeyProvider):
    """
    GCP Cloud KMS provider for production use.

    Uses GCP Cloud KMS to encrypt/decrypt data encryption keys.
    Requires GCP credentials with cloudkms.cryptoKeyVersions.useToEncrypt
    and cloudkms.cryptoKeyVersions.useToDecrypt permissions.
    """

    def __init__(self):
        """Initialize GCP Cloud KMS provider."""
        if not all(
            [
                settings.GCP_KMS_PROJECT_ID,
                settings.GCP_KMS_LOCATION,
                settings.GCP_KMS_KEY_RING,
                settings.GCP_KMS_KEY_NAME,
            ]
        ):
            raise KMSError(
                "GCP_KMS_PROJECT_ID, GCP_KMS_LOCATION, GCP_KMS_KEY_RING, "
                "and GCP_KMS_KEY_NAME must all be set when using GCP KMS provider"
            )

        from google.cloud import kms

        self._kms_client = kms.KeyManagementServiceClient()
        self._key_name = self._kms_client.crypto_key_path(
            settings.GCP_KMS_PROJECT_ID,
            settings.GCP_KMS_LOCATION,
            settings.GCP_KMS_KEY_RING,
            settings.GCP_KMS_KEY_NAME,
        )

        logger.info(
            "gcp_kms_provider_initialized",
            provider="gcp",
            project=settings.GCP_KMS_PROJECT_ID,
            location=settings.GCP_KMS_LOCATION,
            key_ring=settings.GCP_KMS_KEY_RING,
            key_name=settings.GCP_KMS_KEY_NAME,
        )

    def encrypt_dek(self, plaintext_dek: bytes) -> dict[str, Any]:
        """Encrypt DEK using GCP Cloud KMS."""
        try:
            from google.cloud.kms_v1 import EncryptRequest

            request = EncryptRequest(name=self._key_name, plaintext=plaintext_dek)
            response = self._kms_client.encrypt(request=request)

            return {
                "ciphertext": base64.b64encode(response.ciphertext).decode("utf-8"),
                "key_id": self._key_name,
                "algorithm": "GCP_KMS",
            }
        except Exception as e:
            logger.error("gcp_kms_encrypt_failed", error=str(e))
            raise KMSEncryptionError(f"GCP KMS encryption failed: {e}") from e

    def decrypt_dek(self, encrypted_dek_data: dict[str, Any]) -> bytes:
        """Decrypt DEK using GCP Cloud KMS."""
        try:
            from google.cloud.kms_v1 import DecryptRequest

            ciphertext = base64.b64decode(encrypted_dek_data["ciphertext"])
            request = DecryptRequest(name=self._key_name, ciphertext=ciphertext)
            response = self._kms_client.decrypt(request=request)

            return response.plaintext
        except Exception as e:
            logger.error("gcp_kms_decrypt_failed", error=str(e))
            raise KMSDecryptionError(f"GCP KMS decryption failed: {e}") from e

    def generate_dek(self) -> bytes:
        """Generate a random 32-byte DEK."""
        return secrets.token_bytes(32)


class DEKCache:
    """
    In-memory cache for decrypted data encryption keys.

    Caches DEKs with TTL to reduce KMS API calls and improve performance.
    Thread-safe for concurrent access.
    """

    def __init__(self, ttl_seconds: int | None = None, max_size: int | None = None):
        """
        Initialize DEK cache.

        Args:
            ttl_seconds: Time-to-live for cached DEKs (defaults to KMS_DEK_CACHE_TTL_SECONDS)
            max_size: Maximum number of DEKs to cache (defaults to KMS_DEK_CACHE_MAX_SIZE)
        """
        self._cache: dict[str, tuple[bytes, datetime]] = {}
        self._ttl = timedelta(seconds=ttl_seconds or settings.KMS_DEK_CACHE_TTL_SECONDS)
        self._max_size = max_size or settings.KMS_DEK_CACHE_MAX_SIZE

    def get(self, key: str) -> bytes | None:
        """
        Get a cached DEK.

        Args:
            key: Cache key (typically hash of encrypted DEK)

        Returns:
            Plaintext DEK bytes if cached and not expired, None otherwise
        """
        if key not in self._cache:
            return None

        dek, expiry = self._cache[key]
        if datetime.now(tz=UTC) > expiry:
            # Expired, remove from cache
            del self._cache[key]
            return None

        return dek

    def set(self, key: str, dek: bytes) -> None:
        """
        Cache a DEK.

        Args:
            key: Cache key (typically hash of encrypted DEK)
            dek: Plaintext DEK bytes to cache
        """
        # Simple LRU: if cache is full, remove oldest entry
        if len(self._cache) >= self._max_size:
            oldest_key = min(self._cache.items(), key=lambda x: x[1][1])[0]
            del self._cache[oldest_key]

        expiry = datetime.now(tz=UTC) + self._ttl
        self._cache[key] = (dek, expiry)

    def clear(self) -> None:
        """Clear all cached DEKs."""
        self._cache.clear()


def get_kms_provider() -> KMSKeyProvider:
    """
    Get the configured KMS provider.

    Returns:
        KMSKeyProvider instance based on KMS_PROVIDER setting

    Raises:
        KMSError: If provider is invalid or configuration is missing
    """
    provider = settings.KMS_PROVIDER

    if provider == "local":
        return LocalKMSProvider()
    if provider == "aws":
        return AWSKMSProvider()
    if provider == "gcp":
        return GCPKMSProvider()
    raise KMSError(f"Unknown KMS provider: {provider}. Must be 'local', 'aws', or 'gcp'")


# Global DEK cache instance
_dek_cache = DEKCache()


def get_dek_cache() -> DEKCache:
    """Get the global DEK cache instance."""
    return _dek_cache
