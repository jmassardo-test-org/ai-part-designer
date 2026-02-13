"""
Tests for KMS-based encryption service.

Tests envelope encryption with KMS integration.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from app.core.security import KMSEncryptionService


class TestKMSEncryptionService:
    """Tests for KMS-based encryption service."""

    @patch("app.core.kms.get_kms_provider")
    @patch("app.core.kms.get_dek_cache")
    def test_kms_encryption_service_initialization(self, mock_get_cache, mock_get_provider):
        """Test that KMS encryption service initializes correctly."""
        mock_provider = MagicMock()
        mock_cache = MagicMock()
        mock_get_provider.return_value = mock_provider
        mock_get_cache.return_value = mock_cache

        service = KMSEncryptionService()

        assert service._kms_provider == mock_provider
        assert service._dek_cache == mock_cache

    @patch("app.core.kms.get_kms_provider")
    @patch("app.core.kms.get_dek_cache")
    def test_encrypt_string_returns_valid_structure(self, mock_get_cache, mock_get_provider):
        """Test that string encryption returns expected structure."""
        # Mock KMS provider
        mock_provider = MagicMock()
        mock_provider.generate_dek.return_value = b"0" * 32
        mock_provider.encrypt_dek.return_value = {
            "ciphertext": "encrypted_dek",
            "key_id": "test-key",
            "algorithm": "local",
        }
        mock_get_provider.return_value = mock_provider

        # Mock DEK cache
        mock_cache = MagicMock()
        mock_get_cache.return_value = mock_cache

        service = KMSEncryptionService()
        plaintext = "test data"

        result = service.encrypt(plaintext)

        assert isinstance(result, dict)
        assert "ciphertext" in result
        assert "encrypted_dek" in result
        assert isinstance(result["encrypted_dek"], dict)

    @patch("app.core.kms.get_kms_provider")
    @patch("app.core.kms.get_dek_cache")
    def test_encrypt_decrypt_round_trip(self, mock_get_cache, mock_get_provider):
        """Test full encryption/decryption round trip."""
        # Mock KMS provider
        test_dek = b"0" * 32
        mock_provider = MagicMock()
        mock_provider.generate_dek.return_value = test_dek
        mock_provider.encrypt_dek.return_value = {
            "ciphertext": "encrypted_dek",
            "key_id": "test-key",
            "algorithm": "local",
        }
        mock_provider.decrypt_dek.return_value = test_dek
        mock_get_provider.return_value = mock_provider

        # Mock DEK cache (cache miss scenario)
        mock_cache = MagicMock()
        mock_cache.get.return_value = None
        mock_get_cache.return_value = mock_cache

        service = KMSEncryptionService()
        original = "test data with special chars: 😀🔒"

        # Encrypt
        encrypted = service.encrypt(original)

        # Decrypt
        decrypted = service.decrypt(encrypted)

        assert decrypted == original

    @patch("app.core.kms.get_kms_provider")
    @patch("app.core.kms.get_dek_cache")
    def test_decrypt_uses_cache(self, mock_get_cache, mock_get_provider):
        """Test that decryption uses cached DEKs."""
        # Mock KMS provider
        test_dek = b"0" * 32
        mock_provider = MagicMock()
        mock_provider.generate_dek.return_value = test_dek
        mock_provider.encrypt_dek.return_value = {
            "ciphertext": "encrypted_dek",
            "key_id": "test-key",
            "algorithm": "local",
        }
        mock_get_provider.return_value = mock_provider

        # Mock DEK cache (cache hit scenario)
        mock_cache = MagicMock()
        mock_cache.get.return_value = test_dek  # DEK is in cache
        mock_get_cache.return_value = mock_cache

        service = KMSEncryptionService()

        # Encrypt first
        encrypted = service.encrypt("test data")

        # Reset mock to verify decrypt behavior
        mock_provider.decrypt_dek.reset_mock()

        # Decrypt - should use cache
        service.decrypt(encrypted)

        # Verify KMS provider decrypt was NOT called (used cache instead)
        mock_provider.decrypt_dek.assert_not_called()

    @patch("app.core.kms.get_kms_provider")
    @patch("app.core.kms.get_dek_cache")
    def test_decrypt_calls_kms_on_cache_miss(self, mock_get_cache, mock_get_provider):
        """Test that decryption calls KMS on cache miss."""
        # Mock KMS provider
        test_dek = b"0" * 32
        mock_provider = MagicMock()
        mock_provider.generate_dek.return_value = test_dek
        mock_provider.encrypt_dek.return_value = {
            "ciphertext": "encrypted_dek",
            "key_id": "test-key",
            "algorithm": "local",
        }
        mock_provider.decrypt_dek.return_value = test_dek
        mock_get_provider.return_value = mock_provider

        # Mock DEK cache (cache miss scenario)
        mock_cache = MagicMock()
        mock_cache.get.return_value = None  # Not in cache
        mock_get_cache.return_value = mock_cache

        service = KMSEncryptionService()

        # Encrypt first
        encrypted = service.encrypt("test data")

        # Decrypt - should call KMS
        service.decrypt(encrypted)

        # Verify KMS provider decrypt was called
        mock_provider.decrypt_dek.assert_called_once()
        # Verify result was cached
        mock_cache.set.assert_called()

    @patch("app.core.kms.get_kms_provider")
    @patch("app.core.kms.get_dek_cache")
    def test_encrypt_dict_round_trip(self, mock_get_cache, mock_get_provider):
        """Test dictionary encryption/decryption."""
        # Mock KMS provider
        test_dek = b"0" * 32
        mock_provider = MagicMock()
        mock_provider.generate_dek.return_value = test_dek
        mock_provider.encrypt_dek.return_value = {
            "ciphertext": "encrypted_dek",
            "key_id": "test-key",
            "algorithm": "local",
        }
        mock_provider.decrypt_dek.return_value = test_dek
        mock_get_provider.return_value = mock_provider

        # Mock DEK cache
        mock_cache = MagicMock()
        mock_cache.get.return_value = None
        mock_get_cache.return_value = mock_cache

        service = KMSEncryptionService()
        original_dict = {"key1": "value1", "key2": 42, "key3": [1, 2, 3]}

        # Encrypt
        encrypted = service.encrypt_dict(original_dict)

        # Decrypt
        decrypted = service.decrypt_dict(encrypted)

        assert decrypted == original_dict

    @patch("app.core.kms.get_kms_provider")
    @patch("app.core.kms.get_dek_cache")
    def test_encrypt_bytes_round_trip(self, mock_get_cache, mock_get_provider):
        """Test bytes encryption/decryption."""
        # Mock KMS provider
        test_dek = b"0" * 32
        mock_provider = MagicMock()
        mock_provider.generate_dek.return_value = test_dek
        mock_provider.encrypt_dek.return_value = {
            "ciphertext": "encrypted_dek",
            "key_id": "test-key",
            "algorithm": "local",
        }
        mock_provider.decrypt_dek.return_value = test_dek
        mock_get_provider.return_value = mock_provider

        # Mock DEK cache
        mock_cache = MagicMock()
        mock_cache.get.return_value = None
        mock_get_cache.return_value = mock_cache

        service = KMSEncryptionService()
        original_bytes = b"binary data \x00\x01\x02\xff"

        # Encrypt
        encrypted = service.encrypt_bytes(original_bytes)

        # Decrypt
        decrypted = service.decrypt_bytes(encrypted)

        assert decrypted == original_bytes

    @patch("app.core.kms.get_kms_provider")
    @patch("app.core.kms.get_dek_cache")
    def test_encrypted_data_is_different_from_plaintext(self, mock_get_cache, mock_get_provider):
        """Test that encrypted data is different from plaintext."""
        # Mock KMS provider
        test_dek = b"0" * 32
        mock_provider = MagicMock()
        mock_provider.generate_dek.return_value = test_dek
        mock_provider.encrypt_dek.return_value = {
            "ciphertext": "encrypted_dek",
            "key_id": "test-key",
            "algorithm": "local",
        }
        mock_get_provider.return_value = mock_provider

        # Mock DEK cache
        mock_cache = MagicMock()
        mock_get_cache.return_value = mock_cache

        service = KMSEncryptionService()
        plaintext = "secret data"

        encrypted = service.encrypt(plaintext)

        # Encrypted ciphertext should not contain plaintext
        assert plaintext not in encrypted["ciphertext"]

    @patch("app.core.kms.get_kms_provider")
    @patch("app.core.kms.get_dek_cache")
    def test_each_encryption_generates_new_dek(self, mock_get_cache, mock_get_provider):
        """Test that each encryption operation generates a new DEK."""
        # Mock KMS provider
        mock_provider = MagicMock()
        # Generate different DEKs each time
        mock_provider.generate_dek.side_effect = [b"0" * 32, b"1" * 32]
        mock_provider.encrypt_dek.side_effect = [
            {"ciphertext": "encrypted_dek_1", "key_id": "test-key", "algorithm": "local"},
            {"ciphertext": "encrypted_dek_2", "key_id": "test-key", "algorithm": "local"},
        ]
        mock_get_provider.return_value = mock_provider

        # Mock DEK cache
        mock_cache = MagicMock()
        mock_get_cache.return_value = mock_cache

        service = KMSEncryptionService()
        plaintext = "test data"

        # Encrypt twice
        encrypted1 = service.encrypt(plaintext)
        encrypted2 = service.encrypt(plaintext)

        # Should have different encrypted DEKs
        assert encrypted1["encrypted_dek"] != encrypted2["encrypted_dek"]

        # Verify generate_dek was called twice
        assert mock_provider.generate_dek.call_count == 2


class TestKMSEncryptionServiceIntegration:
    """Integration tests using local KMS provider."""

    def test_real_local_kms_encrypt_decrypt(self):
        """Test encryption/decryption with real local KMS provider."""
        from unittest.mock import patch

        # Use local KMS provider
        with patch("app.core.kms.settings") as mock_settings:
            mock_settings.KMS_PROVIDER = "local"
            mock_settings.SECRET_KEY = "test-secret-key-for-encryption"
            mock_settings.KMS_DEK_CACHE_TTL_SECONDS = 300
            mock_settings.KMS_DEK_CACHE_MAX_SIZE = 100

            service = KMSEncryptionService()
            plaintext = "sensitive data 🔒"

            # Encrypt
            encrypted = service.encrypt(plaintext)

            # Verify structure
            assert "ciphertext" in encrypted
            assert "encrypted_dek" in encrypted

            # Decrypt
            decrypted = service.decrypt(encrypted)

            assert decrypted == plaintext

    def test_real_local_kms_large_data(self):
        """Test encryption of larger data."""
        from unittest.mock import patch

        with patch("app.core.kms.settings") as mock_settings:
            mock_settings.KMS_PROVIDER = "local"
            mock_settings.SECRET_KEY = "test-secret-key-for-encryption"
            mock_settings.KMS_DEK_CACHE_TTL_SECONDS = 300
            mock_settings.KMS_DEK_CACHE_MAX_SIZE = 100

            service = KMSEncryptionService()
            # Generate 1MB of data
            plaintext = "A" * (1024 * 1024)

            # Encrypt
            encrypted = service.encrypt(plaintext)

            # Decrypt
            decrypted = service.decrypt(encrypted)

            assert decrypted == plaintext
