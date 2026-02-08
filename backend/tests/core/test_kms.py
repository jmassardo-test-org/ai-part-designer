"""
Tests for KMS (Key Management Service) providers.

Tests the KMS abstraction layer and individual provider implementations.
"""

from __future__ import annotations

import base64
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest

from app.core.kms import (
    AWSKMSProvider,
    DEKCache,
    GCPKMSProvider,
    KMSDecryptionError,
    KMSEncryptionError,
    KMSError,
    LocalKMSProvider,
    get_kms_provider,
)

if TYPE_CHECKING:
    pass


class TestLocalKMSProvider:
    """Tests for local KMS provider (development mode)."""

    def test_local_kms_provider_initialization(self):
        """Test that local KMS provider initializes correctly."""
        provider = LocalKMSProvider()
        assert provider is not None

    def test_generate_dek_returns_32_bytes(self):
        """Test that DEK generation returns 32 bytes."""
        provider = LocalKMSProvider()
        dek = provider.generate_dek()

        assert isinstance(dek, bytes)
        assert len(dek) == 32

    def test_encrypt_dek_returns_valid_structure(self):
        """Test that DEK encryption returns expected structure."""
        provider = LocalKMSProvider()
        plaintext_dek = provider.generate_dek()

        encrypted = provider.encrypt_dek(plaintext_dek)

        assert isinstance(encrypted, dict)
        assert "ciphertext" in encrypted
        assert "key_id" in encrypted
        assert "algorithm" in encrypted
        assert encrypted["key_id"] == "local"
        assert encrypted["algorithm"] == "fernet"

    def test_decrypt_dek_returns_original_plaintext(self):
        """Test that DEK decryption returns original plaintext."""
        provider = LocalKMSProvider()
        plaintext_dek = provider.generate_dek()

        encrypted = provider.encrypt_dek(plaintext_dek)
        decrypted = provider.decrypt_dek(encrypted)

        assert decrypted == plaintext_dek

    def test_encrypt_decrypt_round_trip(self):
        """Test full encryption/decryption round trip."""
        provider = LocalKMSProvider()
        original_dek = b"0" * 32  # Use fixed DEK for reproducibility

        # Encrypt
        encrypted = provider.encrypt_dek(original_dek)

        # Decrypt
        decrypted = provider.decrypt_dek(encrypted)

        assert decrypted == original_dek

    def test_decrypt_with_invalid_ciphertext_raises_error(self):
        """Test that decryption with invalid ciphertext raises error."""
        provider = LocalKMSProvider()

        invalid_encrypted = {
            "ciphertext": base64.b64encode(b"invalid").decode("utf-8"),
            "key_id": "local",
            "algorithm": "fernet",
        }

        with pytest.raises(KMSDecryptionError):
            provider.decrypt_dek(invalid_encrypted)


class TestAWSKMSProvider:
    """Tests for AWS KMS provider."""

    def test_aws_kms_requires_key_id(self):
        """Test that AWS KMS requires AWS_KMS_KEY_ID to be set."""
        with patch("app.core.kms.settings") as mock_settings:
            mock_settings.AWS_KMS_KEY_ID = None

            with pytest.raises(KMSError, match="AWS_KMS_KEY_ID must be set"):
                AWSKMSProvider()

    @patch("boto3.client")
    def test_aws_kms_provider_initialization(self, mock_boto3_client):
        """Test that AWS KMS provider initializes with correct settings."""
        with patch("app.core.kms.settings") as mock_settings:
            mock_settings.AWS_KMS_KEY_ID = "test-key-id"
            mock_settings.AWS_KMS_REGION = "us-west-2"
            mock_settings.AWS_REGION = "us-east-1"

            provider = AWSKMSProvider()

            # Verify boto3 client was created with correct region
            mock_boto3_client.assert_called_once_with("kms", region_name="us-west-2")
            assert provider._key_id == "test-key-id"

    @patch("boto3.client")
    def test_aws_kms_encrypt_dek(self, mock_boto3_client):
        """Test AWS KMS DEK encryption."""
        with patch("app.core.kms.settings") as mock_settings:
            mock_settings.AWS_KMS_KEY_ID = "test-key-id"
            mock_settings.AWS_KMS_REGION = "us-west-2"
            mock_settings.AWS_REGION = "us-east-1"

            # Mock KMS client response
            mock_kms_client = MagicMock()
            mock_boto3_client.return_value = mock_kms_client
            mock_kms_client.encrypt.return_value = {
                "CiphertextBlob": b"encrypted_dek_data",
                "KeyId": "arn:aws:kms:us-west-2:123456789012:key/test-key-id",
            }

            provider = AWSKMSProvider()
            plaintext_dek = b"0" * 32

            encrypted = provider.encrypt_dek(plaintext_dek)

            assert isinstance(encrypted, dict)
            assert "ciphertext" in encrypted
            assert "key_id" in encrypted
            assert "algorithm" in encrypted
            assert encrypted["algorithm"] == "AWS_KMS"

            # Verify KMS client was called
            mock_kms_client.encrypt.assert_called_once_with(KeyId="test-key-id", Plaintext=plaintext_dek)

    @patch("boto3.client")
    def test_aws_kms_decrypt_dek(self, mock_boto3_client):
        """Test AWS KMS DEK decryption."""
        with patch("app.core.kms.settings") as mock_settings:
            mock_settings.AWS_KMS_KEY_ID = "test-key-id"
            mock_settings.AWS_KMS_REGION = "us-west-2"
            mock_settings.AWS_REGION = "us-east-1"

            # Mock KMS client response
            mock_kms_client = MagicMock()
            mock_boto3_client.return_value = mock_kms_client
            expected_plaintext = b"0" * 32
            mock_kms_client.decrypt.return_value = {"Plaintext": expected_plaintext}

            provider = AWSKMSProvider()
            encrypted_dek = {
                "ciphertext": base64.b64encode(b"encrypted_dek_data").decode("utf-8"),
                "key_id": "test-key-id",
                "algorithm": "AWS_KMS",
            }

            decrypted = provider.decrypt_dek(encrypted_dek)

            assert decrypted == expected_plaintext
            mock_kms_client.decrypt.assert_called_once()

    @patch("boto3.client")
    def test_aws_kms_encrypt_failure_raises_error(self, mock_boto3_client):
        """Test that AWS KMS encryption failure raises error."""
        with patch("app.core.kms.settings") as mock_settings:
            mock_settings.AWS_KMS_KEY_ID = "test-key-id"
            mock_settings.AWS_KMS_REGION = "us-west-2"
            mock_settings.AWS_REGION = "us-east-1"

            # Mock KMS client to raise exception
            mock_kms_client = MagicMock()
            mock_boto3_client.return_value = mock_kms_client
            mock_kms_client.encrypt.side_effect = Exception("KMS error")

            provider = AWSKMSProvider()
            plaintext_dek = b"0" * 32

            with pytest.raises(KMSEncryptionError, match="AWS KMS encryption failed"):
                provider.encrypt_dek(plaintext_dek)


class TestGCPKMSProvider:
    """Tests for GCP Cloud KMS provider."""

    def test_gcp_kms_requires_all_settings(self):
        """Test that GCP KMS requires all configuration settings."""
        with patch("app.core.kms.settings") as mock_settings:
            mock_settings.GCP_KMS_PROJECT_ID = None
            mock_settings.GCP_KMS_LOCATION = "us-east1"
            mock_settings.GCP_KMS_KEY_RING = "test-ring"
            mock_settings.GCP_KMS_KEY_NAME = "test-key"

            with pytest.raises(KMSError, match="must all be set"):
                GCPKMSProvider()

    @patch("google.cloud.kms.KeyManagementServiceClient")
    def test_gcp_kms_provider_initialization(self, mock_kms_client_class):
        """Test that GCP KMS provider initializes with correct settings."""
        with patch("app.core.kms.settings") as mock_settings:
            mock_settings.GCP_KMS_PROJECT_ID = "test-project"
            mock_settings.GCP_KMS_LOCATION = "us-east1"
            mock_settings.GCP_KMS_KEY_RING = "test-ring"
            mock_settings.GCP_KMS_KEY_NAME = "test-key"

            # Mock KMS client
            mock_kms_client = MagicMock()
            mock_kms_client_class.return_value = mock_kms_client
            mock_kms_client.crypto_key_path.return_value = (
                "projects/test-project/locations/us-east1/keyRings/test-ring/cryptoKeys/test-key"
            )

            provider = GCPKMSProvider()

            # Verify client was initialized
            mock_kms_client_class.assert_called_once()
            assert provider._key_name == (
                "projects/test-project/locations/us-east1/keyRings/test-ring/cryptoKeys/test-key"
            )

    @patch("google.cloud.kms.KeyManagementServiceClient")
    def test_gcp_kms_encrypt_dek(self, mock_kms_client_class):
        """Test GCP KMS DEK encryption."""
        with patch("app.core.kms.settings") as mock_settings:
            mock_settings.GCP_KMS_PROJECT_ID = "test-project"
            mock_settings.GCP_KMS_LOCATION = "us-east1"
            mock_settings.GCP_KMS_KEY_RING = "test-ring"
            mock_settings.GCP_KMS_KEY_NAME = "test-key"

            # Mock KMS client
            mock_kms_client = MagicMock()
            mock_kms_client_class.return_value = mock_kms_client
            mock_kms_client.crypto_key_path.return_value = "test-key-path"

            # Mock encrypt response
            mock_response = MagicMock()
            mock_response.ciphertext = b"encrypted_dek_data"
            mock_kms_client.encrypt.return_value = mock_response

            provider = GCPKMSProvider()
            plaintext_dek = b"0" * 32

            encrypted = provider.encrypt_dek(plaintext_dek)

            assert isinstance(encrypted, dict)
            assert "ciphertext" in encrypted
            assert "key_id" in encrypted
            assert "algorithm" in encrypted
            assert encrypted["algorithm"] == "GCP_KMS"
            mock_kms_client.encrypt.assert_called_once()

    @patch("google.cloud.kms.KeyManagementServiceClient")
    def test_gcp_kms_decrypt_dek(self, mock_kms_client_class):
        """Test GCP KMS DEK decryption."""
        with patch("app.core.kms.settings") as mock_settings:
            mock_settings.GCP_KMS_PROJECT_ID = "test-project"
            mock_settings.GCP_KMS_LOCATION = "us-east1"
            mock_settings.GCP_KMS_KEY_RING = "test-ring"
            mock_settings.GCP_KMS_KEY_NAME = "test-key"

            # Mock KMS client
            mock_kms_client = MagicMock()
            mock_kms_client_class.return_value = mock_kms_client
            mock_kms_client.crypto_key_path.return_value = "test-key-path"

            # Mock decrypt response
            expected_plaintext = b"0" * 32
            mock_response = MagicMock()
            mock_response.plaintext = expected_plaintext
            mock_kms_client.decrypt.return_value = mock_response

            provider = GCPKMSProvider()
            encrypted_dek = {
                "ciphertext": base64.b64encode(b"encrypted_dek_data").decode("utf-8"),
                "key_id": "test-key-path",
                "algorithm": "GCP_KMS",
            }

            decrypted = provider.decrypt_dek(encrypted_dek)

            assert decrypted == expected_plaintext
            mock_kms_client.decrypt.assert_called_once()


class TestDEKCache:
    """Tests for DEK caching."""

    def test_dek_cache_initialization(self):
        """Test that DEK cache initializes correctly."""
        cache = DEKCache(ttl_seconds=300, max_size=50)
        assert cache is not None

    def test_cache_get_returns_none_for_missing_key(self):
        """Test that cache returns None for missing key."""
        cache = DEKCache()
        result = cache.get("nonexistent")
        assert result is None

    def test_cache_set_and_get(self):
        """Test caching and retrieving a DEK."""
        cache = DEKCache(ttl_seconds=300)
        dek = b"test_dek_data"

        cache.set("test_key", dek)
        retrieved = cache.get("test_key")

        assert retrieved == dek

    def test_cache_expiry(self):
        """Test that cached DEKs expire after TTL."""
        cache = DEKCache(ttl_seconds=1)  # 1 second TTL
        dek = b"test_dek_data"

        cache.set("test_key", dek)

        # Verify it's cached initially
        assert cache.get("test_key") == dek

        # Wait for expiration
        import time

        time.sleep(1.1)  # Wait slightly more than TTL
        retrieved = cache.get("test_key")

        assert retrieved is None

    def test_cache_max_size_eviction(self):
        """Test that cache evicts oldest entry when max size reached."""
        cache = DEKCache(ttl_seconds=300, max_size=2)

        cache.set("key1", b"dek1")
        cache.set("key2", b"dek2")
        cache.set("key3", b"dek3")  # Should evict key1

        # key1 should be evicted
        assert cache.get("key1") is None
        assert cache.get("key2") == b"dek2"
        assert cache.get("key3") == b"dek3"

    def test_cache_clear(self):
        """Test that cache clear removes all entries."""
        cache = DEKCache()
        cache.set("key1", b"dek1")
        cache.set("key2", b"dek2")

        cache.clear()

        assert cache.get("key1") is None
        assert cache.get("key2") is None


class TestGetKMSProvider:
    """Tests for KMS provider factory function."""

    def test_get_kms_provider_returns_local_by_default(self):
        """Test that local provider is returned by default."""
        with patch("app.core.kms.settings") as mock_settings:
            mock_settings.KMS_PROVIDER = "local"
            mock_settings.SECRET_KEY = "test-secret-key"

            provider = get_kms_provider()

            assert isinstance(provider, LocalKMSProvider)

    @patch("boto3.client")
    def test_get_kms_provider_returns_aws(self, mock_boto3_client):
        """Test that AWS provider is returned when configured."""
        with patch("app.core.kms.settings") as mock_settings:
            mock_settings.KMS_PROVIDER = "aws"
            mock_settings.AWS_KMS_KEY_ID = "test-key"
            mock_settings.AWS_KMS_REGION = "us-west-2"
            mock_settings.AWS_REGION = "us-east-1"

            provider = get_kms_provider()

            assert isinstance(provider, AWSKMSProvider)

    @patch("google.cloud.kms.KeyManagementServiceClient")
    def test_get_kms_provider_returns_gcp(self, mock_kms_client_class):
        """Test that GCP provider is returned when configured."""
        with patch("app.core.kms.settings") as mock_settings:
            mock_settings.KMS_PROVIDER = "gcp"
            mock_settings.GCP_KMS_PROJECT_ID = "test-project"
            mock_settings.GCP_KMS_LOCATION = "us-east1"
            mock_settings.GCP_KMS_KEY_RING = "test-ring"
            mock_settings.GCP_KMS_KEY_NAME = "test-key"

            # Mock KMS client
            mock_kms_client = MagicMock()
            mock_kms_client_class.return_value = mock_kms_client
            mock_kms_client.crypto_key_path.return_value = "test-key-path"

            provider = get_kms_provider()

            assert isinstance(provider, GCPKMSProvider)

    def test_get_kms_provider_raises_error_for_invalid_provider(self):
        """Test that invalid provider raises error."""
        with patch("app.core.kms.settings") as mock_settings:
            mock_settings.KMS_PROVIDER = "invalid"

            with pytest.raises(KMSError, match="Unknown KMS provider"):
                get_kms_provider()
