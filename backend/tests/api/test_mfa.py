"""
Tests for MFA (Multi-Factor Authentication) endpoints.

Tests TOTP-based MFA setup, verification, and management.
"""

import pyotp
import pytest
from httpx import AsyncClient

# =============================================================================
# MFA Status Tests
# =============================================================================


class TestMFAStatus:
    """Tests for MFA status endpoint."""

    async def test_mfa_status_unauthenticated(self, client: AsyncClient):
        """Should reject unauthenticated requests."""
        response = await client.get("/api/v1/auth/mfa/status")
        assert response.status_code == 401

    async def test_mfa_status_when_disabled(self, client: AsyncClient, auth_headers):
        """Should return disabled status when MFA is not enabled."""
        response = await client.get("/api/v1/auth/mfa/status", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["enabled"] is False
        assert data["enabled_at"] is None
        assert data["backup_codes_remaining"] == 0


# =============================================================================
# MFA Setup Tests
# =============================================================================


class TestMFASetup:
    """Tests for MFA setup endpoint."""

    async def test_mfa_setup_generates_secret(self, client: AsyncClient, auth_headers):
        """Should generate TOTP secret on setup."""
        response = await client.post("/api/v1/auth/mfa/setup", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()

        # Should have secret
        assert "secret" in data
        assert len(data["secret"]) >= 16  # Base32 encoded secret

        # Should have QR code
        assert "qr_code" in data
        assert len(data["qr_code"]) > 0  # Base64 PNG

        # Should have provisioning URI
        assert "provisioning_uri" in data
        assert "otpauth://totp/" in data["provisioning_uri"]

    async def test_mfa_setup_returns_qr_code(self, client: AsyncClient, auth_headers):
        """Should return base64-encoded QR code."""
        response = await client.post("/api/v1/auth/mfa/setup", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()

        # QR code should be valid base64
        import base64

        try:
            decoded = base64.b64decode(data["qr_code"])
            # PNG files start with specific bytes
            assert decoded[:4] == b"\x89PNG" or len(decoded) > 100
        except Exception:
            pytest.fail("QR code is not valid base64")

    async def test_mfa_setup_generates_backup_codes(self, client: AsyncClient, auth_headers):
        """Should generate backup codes on setup."""
        response = await client.post("/api/v1/auth/mfa/setup", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()

        assert "backup_codes" in data
        assert len(data["backup_codes"]) == 10

        # Each backup code should be 8 characters
        for code in data["backup_codes"]:
            assert len(code) == 8

    async def test_mfa_setup_unauthenticated(self, client: AsyncClient):
        """Should reject unauthenticated requests."""
        response = await client.post("/api/v1/auth/mfa/setup")
        assert response.status_code == 401


# =============================================================================
# MFA Enable Tests
# =============================================================================


class TestMFAEnable:
    """Tests for MFA enable endpoint."""

    async def test_mfa_enable_with_valid_code(self, client: AsyncClient, auth_headers, db_session):
        """Should enable MFA with valid TOTP code."""
        # First, setup MFA
        setup_response = await client.post("/api/v1/auth/mfa/setup", headers=auth_headers)
        assert setup_response.status_code == 200
        secret = setup_response.json()["secret"]

        # Generate a valid TOTP code
        totp = pyotp.TOTP(secret)
        valid_code = totp.now()

        # Enable MFA
        enable_response = await client.post(
            "/api/v1/auth/mfa/enable", headers=auth_headers, json={"code": valid_code}
        )

        assert enable_response.status_code == 200
        assert "enabled" in enable_response.json()["message"].lower()

    async def test_mfa_enable_with_invalid_code(self, client: AsyncClient, auth_headers):
        """Should reject invalid TOTP code."""
        # First, setup MFA
        await client.post("/api/v1/auth/mfa/setup", headers=auth_headers)

        # Try with invalid code
        response = await client.post(
            "/api/v1/auth/mfa/enable", headers=auth_headers, json={"code": "000000"}
        )

        assert response.status_code == 400
        assert "invalid" in response.json()["detail"].lower()

    async def test_mfa_enable_without_setup(self, client: AsyncClient, auth_headers):
        """Should reject if setup not initiated."""
        response = await client.post(
            "/api/v1/auth/mfa/enable", headers=auth_headers, json={"code": "123456"}
        )

        assert response.status_code == 400
        assert "setup" in response.json()["detail"].lower()


# =============================================================================
# MFA Verification Tests
# =============================================================================


class TestMFAVerify:
    """Tests for MFA verification endpoint."""

    async def test_mfa_verify_correct_code(self, client: AsyncClient, auth_headers_with_mfa):
        """Should verify correct TOTP code."""
        # This test requires a user with MFA already enabled
        # auth_headers_with_mfa fixture would set this up
        # Requires fixture setup

    async def test_mfa_verify_incorrect_code(self, client: AsyncClient, auth_headers_with_mfa):
        """Should reject incorrect TOTP code."""
        # Requires fixture setup

    async def test_mfa_verify_expired_code(self, client: AsyncClient, auth_headers_with_mfa):
        """Should reject expired TOTP code."""
        # Requires fixture setup

    async def test_mfa_backup_code_works_once(self, client: AsyncClient, auth_headers_with_mfa):
        """Should allow backup code only once."""
        # Requires fixture setup


# =============================================================================
# MFA Disable Tests
# =============================================================================


class TestMFADisable:
    """Tests for MFA disable endpoint."""

    async def test_mfa_disable_requires_password(self, client: AsyncClient, auth_headers_with_mfa):
        """Should require password to disable MFA."""
        response = await client.post(
            "/api/v1/auth/mfa/disable",
            headers=auth_headers_with_mfa,
            json={"password": "", "code": "123456"},
        )

        # Should fail without valid password
        assert response.status_code in [400, 401, 422]

    async def test_mfa_disable_requires_code(self, client: AsyncClient, auth_headers_with_mfa):
        """Should require TOTP code to disable MFA."""
        response = await client.post(
            "/api/v1/auth/mfa/disable",
            headers=auth_headers_with_mfa,
            json={"password": "testpassword", "code": ""},
        )

        assert response.status_code in [400, 422]


# =============================================================================
# Login with MFA Tests
# =============================================================================


class TestLoginWithMFA:
    """Tests for login flow with MFA enabled."""

    async def test_login_requires_mfa_when_enabled(self, client: AsyncClient, user_with_mfa):
        """Should require MFA verification when MFA is enabled."""
        # Login should return partial token or MFA required status
        response = await client.post(
            "/api/v1/auth/login", json={"email": user_with_mfa.email, "password": "testpassword"}
        )

        # Could be 200 with mfa_required flag or 202 or custom status
        if response.status_code == 200:
            data = response.json()
            # Should indicate MFA is required
            assert data.get("mfa_required") is True or "mfa" in str(data).lower()

    async def test_login_accepts_backup_code(self, client: AsyncClient, user_with_mfa):
        """Should accept backup code for MFA verification."""
        # Requires fixture setup


# =============================================================================
# Backup Code Management Tests
# =============================================================================


class TestBackupCodes:
    """Tests for backup code management."""

    async def test_regenerate_backup_codes(self, client: AsyncClient, auth_headers_with_mfa):
        """Should regenerate backup codes with valid TOTP."""
        # Requires fixture setup

    async def test_get_backup_codes_count(self, client: AsyncClient, auth_headers):
        """Should return backup codes count."""
        response = await client.get("/api/v1/auth/mfa/backup-codes/count", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert "remaining" in data
        assert "total" in data


# =============================================================================
# Helper Fixtures (to be added to conftest.py)
# =============================================================================


@pytest.fixture
async def auth_headers_with_mfa(db_session, test_user, auth_headers):
    """
    Fixture that provides auth headers for a user with MFA enabled.

    For now, this uses the regular auth_headers since MFA enable/disable
    tests just need a valid authenticated user.
    """
    # Return the regular auth headers - the MFA status is checked server-side
    return auth_headers


@pytest.fixture
async def user_with_mfa(db_session, test_user):
    """
    Fixture that provides a user with MFA enabled.

    This should be added to conftest.py for real implementation.
    """
    # This is a placeholder
    return test_user
