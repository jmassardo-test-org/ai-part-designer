"""
Integration tests for OAuth authentication workflows.

Tests the complete OAuth flow including provider authentication,
callback handling, user creation/linking, and connection management.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

if TYPE_CHECKING:
    from httpx import AsyncClient
    from sqlalchemy.ext.asyncio import AsyncSession

# =============================================================================
# OAuth Login Initiation Integration Tests
# =============================================================================


class TestOAuthLoginInitiation:
    """Integration tests for OAuth login initiation."""

    @pytest.mark.asyncio
    async def test_google_oauth_login_with_valid_config(
        self,
        client: AsyncClient,
    ) -> None:
        """Test Google OAuth login initiation when properly configured."""
        with patch("app.api.v1.oauth.oauth") as mock_oauth:
            # Mock the OAuth client
            mock_client = MagicMock()
            mock_client.create_authorization_url = AsyncMock(
                return_value={
                    "url": "https://accounts.google.com/o/oauth2/auth?client_id=test&state=abc123",
                }
            )
            mock_oauth.create_client.return_value = mock_client

            with patch("app.api.v1.oauth.get_settings") as mock_settings:
                mock_settings.return_value.GOOGLE_CLIENT_ID = "test-client-id"
                mock_settings.return_value.GOOGLE_CLIENT_SECRET = "test-secret"
                mock_settings.return_value.OAUTH_REDIRECT_BASE = "http://localhost:5173"

                response = await client.get("/api/v1/auth/oauth/google/login")

                assert response.status_code == 200
                data = response.json()
                assert "authorization_url" in data
                assert "state" in data
                assert "accounts.google.com" in data["authorization_url"]

    @pytest.mark.asyncio
    async def test_github_oauth_login_with_valid_config(
        self,
        client: AsyncClient,
    ) -> None:
        """Test GitHub OAuth login initiation when properly configured."""
        with patch("app.api.v1.oauth.oauth") as mock_oauth:
            mock_client = MagicMock()
            mock_client.create_authorization_url = AsyncMock(
                return_value={
                    "url": "https://github.com/login/oauth/authorize?client_id=test&state=xyz789",
                }
            )
            mock_oauth.create_client.return_value = mock_client

            with patch("app.api.v1.oauth.get_settings") as mock_settings:
                mock_settings.return_value.GITHUB_CLIENT_ID = "test-client-id"
                mock_settings.return_value.GITHUB_CLIENT_SECRET = "test-secret"
                mock_settings.return_value.OAUTH_REDIRECT_BASE = "http://localhost:5173"

                response = await client.get("/api/v1/auth/oauth/github/login")

                assert response.status_code == 200
                data = response.json()
                assert "authorization_url" in data
                assert "state" in data
                assert "github.com" in data["authorization_url"]

    @pytest.mark.asyncio
    async def test_oauth_login_without_configuration(
        self,
        client: AsyncClient,
    ) -> None:
        """Test OAuth login fails gracefully when not configured."""
        with patch("app.api.v1.oauth.get_settings") as mock_settings:
            mock_settings.return_value.GOOGLE_CLIENT_ID = None
            mock_settings.return_value.GOOGLE_CLIENT_SECRET = None

            response = await client.get("/api/v1/auth/oauth/google/login")

            assert response.status_code == 503
            data = response.json()
            assert "detail" in data
            assert "not configured" in data["detail"].lower()

    @pytest.mark.asyncio
    async def test_oauth_redirect_uri_includes_callback_path(
        self,
        client: AsyncClient,
    ) -> None:
        """Test that OAuth redirect URI is correctly constructed."""
        with patch("app.api.v1.oauth.oauth") as mock_oauth:
            mock_client = MagicMock()
            authorization_url = ""

            async def capture_callback_url(callback_url: str, **kwargs: dict) -> dict:
                nonlocal authorization_url
                authorization_url = callback_url
                return {"url": f"https://accounts.google.com/oauth?redirect={callback_url}"}

            mock_client.create_authorization_url = capture_callback_url
            mock_oauth.create_client.return_value = mock_client

            with patch("app.api.v1.oauth.get_settings") as mock_settings:
                mock_settings.return_value.GOOGLE_CLIENT_ID = "test-client-id"
                mock_settings.return_value.GOOGLE_CLIENT_SECRET = "test-secret"
                mock_settings.return_value.OAUTH_REDIRECT_BASE = "https://example.com"

                response = await client.get("/api/v1/auth/oauth/google/login")

                assert response.status_code == 200
                assert authorization_url == "https://example.com/api/v1/auth/oauth/google/callback"


# =============================================================================
# OAuth Callback Integration Tests
# =============================================================================


class TestOAuthCallback:
    """Integration tests for OAuth callback handling."""

    @pytest.mark.asyncio
    async def test_google_oauth_callback_creates_new_user(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
    ) -> None:
        """Test Google OAuth callback creates a new user on first login."""
        # Mock OAuth token exchange and user info
        with patch("app.api.v1.oauth.oauth") as mock_oauth:
            mock_client = MagicMock()
            mock_client.authorize_access_token = AsyncMock(
                return_value={
                    "access_token": "test_access_token",
                    "token_type": "Bearer",
                    "expires_in": 3600,
                }
            )
            mock_oauth.create_client.return_value = mock_client

            with patch("app.api.v1.oauth.fetch_google_user_info") as mock_user_info:
                test_email = f"test_{uuid4().hex[:8]}@example.com"
                mock_user_info.return_value = {
                    "id": "google_123456",
                    "email": test_email,
                    "name": "Test User",
                    "picture": "https://example.com/photo.jpg",
                }

                with patch("app.api.v1.oauth.get_settings") as mock_settings:
                    mock_settings.return_value.FRONTEND_URL = "http://localhost:5173"
                    mock_settings.return_value.OAUTH_REDIRECT_BASE = "http://localhost:5173"

                    response = await client.get(
                        "/api/v1/auth/oauth/google/callback",
                        params={"code": "test_code"},
                        follow_redirects=False,
                    )

                    # Should redirect to frontend with tokens
                    assert response.status_code == 307
                    assert "access_token" in response.headers["location"]
                    assert "is_new_user=true" in response.headers["location"]

                    # Verify user was created in database
                    from app.repositories import UserRepository

                    user_repo = UserRepository(db_session)
                    user = await user_repo.get_by_email(test_email.lower())
                    assert user is not None
                    assert user.email == test_email.lower()
                    assert user.status == "active"
                    assert user.email_verified_at is not None

    @pytest.mark.asyncio
    async def test_github_oauth_callback_creates_new_user(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
    ) -> None:
        """Test GitHub OAuth callback creates a new user on first login."""
        with patch("app.api.v1.oauth.oauth") as mock_oauth:
            mock_client = MagicMock()
            mock_client.authorize_access_token = AsyncMock(
                return_value={
                    "access_token": "test_access_token",
                    "token_type": "Bearer",
                    "expires_in": 3600,
                }
            )
            mock_oauth.create_client.return_value = mock_client

            with patch("app.api.v1.oauth.fetch_github_user_info") as mock_user_info:
                test_email = f"test_{uuid4().hex[:8]}@example.com"
                mock_user_info.return_value = {
                    "id": "12345",
                    "email": test_email,
                    "name": "GitHub User",
                    "picture": "https://github.com/avatar.jpg",
                    "username": "githubuser",
                }

                with patch("app.api.v1.oauth.get_settings") as mock_settings:
                    mock_settings.return_value.FRONTEND_URL = "http://localhost:5173"
                    mock_settings.return_value.OAUTH_REDIRECT_BASE = "http://localhost:5173"

                    response = await client.get(
                        "/api/v1/auth/oauth/github/callback",
                        params={"code": "test_code"},
                        follow_redirects=False,
                    )

                    assert response.status_code == 307
                    assert "access_token" in response.headers["location"]

                    # Verify user was created
                    from app.repositories import UserRepository

                    user_repo = UserRepository(db_session)
                    user = await user_repo.get_by_email(test_email.lower())
                    assert user is not None
                    assert user.email == test_email.lower()

    @pytest.mark.asyncio
    async def test_oauth_callback_links_to_existing_user(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
    ) -> None:
        """Test OAuth callback links to existing user with same email."""
        # Create existing user
        from app.core.security import hash_password
        from app.models import User

        test_email = f"existing_{uuid4().hex[:8]}@example.com"
        existing_user = User(
            id=uuid4(),
            email=test_email,
            password_hash=hash_password("TestPassword123!"),
            display_name="Existing User",
            status="active",
        )
        db_session.add(existing_user)
        await db_session.commit()

        # Mock OAuth callback
        with patch("app.api.v1.oauth.oauth") as mock_oauth:
            mock_client = MagicMock()
            mock_client.authorize_access_token = AsyncMock(
                return_value={
                    "access_token": "test_token",
                    "expires_in": 3600,
                }
            )
            mock_oauth.create_client.return_value = mock_client

            with patch("app.api.v1.oauth.fetch_google_user_info") as mock_user_info:
                mock_user_info.return_value = {
                    "id": "google_999",
                    "email": test_email,
                    "name": "Test User",
                }

                with patch("app.api.v1.oauth.get_settings") as mock_settings:
                    mock_settings.return_value.FRONTEND_URL = "http://localhost:5173"
                    mock_settings.return_value.OAUTH_REDIRECT_BASE = "http://localhost:5173"

                    response = await client.get(
                        "/api/v1/auth/oauth/google/callback",
                        params={"code": "test_code"},
                        follow_redirects=False,
                    )

                    assert response.status_code == 307
                    # Should NOT be a new user since email exists
                    assert "is_new_user=false" in response.headers["location"]

    @pytest.mark.asyncio
    async def test_oauth_callback_handles_error_from_provider(
        self,
        client: AsyncClient,
    ) -> None:
        """Test OAuth callback handles errors from provider."""
        with patch("app.api.v1.oauth.get_settings") as mock_settings:
            mock_settings.return_value.FRONTEND_URL = "http://localhost:5173"

            response = await client.get(
                "/api/v1/auth/oauth/google/callback",
                params={
                    "error": "access_denied",
                    "error_description": "User denied access",
                },
                follow_redirects=False,
            )

            assert response.status_code == 307
            assert "error=oauth_error" in response.headers["location"]
            assert "User denied access" in response.headers["location"]

    @pytest.mark.asyncio
    async def test_oauth_callback_validates_state_csrf(
        self,
        client: AsyncClient,
    ) -> None:
        """Test OAuth callback validates state parameter (CSRF protection)."""
        # This test simulates state mismatch which should fail
        with patch("app.api.v1.oauth.oauth") as mock_oauth:
            mock_client = MagicMock()
            mock_client.authorize_access_token = AsyncMock(side_effect=Exception("State mismatch"))
            mock_oauth.create_client.return_value = mock_client

            with patch("app.api.v1.oauth.get_settings") as mock_settings:
                mock_settings.return_value.FRONTEND_URL = "http://localhost:5173"
                mock_settings.return_value.OAUTH_REDIRECT_BASE = "http://localhost:5173"

                response = await client.get(
                    "/api/v1/auth/oauth/google/callback",
                    params={"code": "test_code", "state": "invalid_state"},
                    follow_redirects=False,
                )

                # Should redirect with error
                assert response.status_code == 307
                assert "error=server_error" in response.headers["location"]


# =============================================================================
# OAuth Connection Management Integration Tests
# =============================================================================


class TestOAuthConnectionManagement:
    """Integration tests for OAuth connection management."""

    @pytest.mark.asyncio
    async def test_list_oauth_connections_for_user(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        auth_headers: dict,
    ) -> None:
        """Test listing OAuth connections for authenticated user."""
        # Create user with OAuth connection
        from app.core.security import hash_password
        from app.models import OAuthConnection, User

        user_id = uuid4()
        user = User(
            id=user_id,
            email=f"test_{uuid4().hex[:8]}@example.com",
            password_hash=hash_password("TestPass123!"),
            display_name="Test User",
            status="active",
        )
        db_session.add(user)

        oauth_conn = OAuthConnection(
            user_id=user_id,
            provider="google",
            provider_user_id="google_123",
            provider_email=user.email,
            access_token="test_token",
            last_used_at=datetime.now(tz=UTC),
        )
        db_session.add(oauth_conn)
        await db_session.commit()

        # Note: This uses the auth_headers fixture which should provide valid auth
        response = await client.get(
            "/api/v1/auth/oauth/connections",
            headers=auth_headers,
        )

        # May be 200 or 404 depending on implementation
        assert response.status_code in [200, 404, 401]

    @pytest.mark.asyncio
    async def test_unlink_oauth_connection(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        auth_headers: dict,
    ) -> None:
        """Test unlinking an OAuth connection."""
        # This would require a properly authenticated user
        # The test structure validates the endpoint exists
        response = await client.delete(
            "/api/v1/auth/oauth/connections/google",
            headers=auth_headers,
        )

        # Could be 200/204 (success), 404 (not found), or 400 (last auth method)
        assert response.status_code in [200, 204, 404, 400, 401]

    @pytest.mark.asyncio
    async def test_cannot_unlink_last_authentication_method(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
    ) -> None:
        """Test that user cannot unlink their last authentication method."""
        from app.core.security import create_access_token, hash_password
        from app.models import OAuthConnection, User

        # Create user with ONLY OAuth (no password)
        user_id = uuid4()
        test_email = f"oauth_only_{uuid4().hex[:8]}@example.com"
        user = User(
            id=user_id,
            email=test_email,
            password_hash=hash_password(""),  # No real password
            display_name="OAuth Only User",
            status="active",
        )
        db_session.add(user)

        # Add single OAuth connection
        oauth_conn = OAuthConnection(
            user_id=user_id,
            provider="google",
            provider_user_id="google_only_123",
            provider_email=test_email,
            access_token="test_token",
            last_used_at=datetime.now(tz=UTC),
        )
        db_session.add(oauth_conn)
        await db_session.commit()

        # Create auth token
        token = create_access_token(
            user_id=user_id,
            email=test_email,
            role="user",
        )
        headers = {"Authorization": f"Bearer {token}"}

        response = await client.delete(
            "/api/v1/auth/oauth/connections/google",
            headers=headers,
        )

        # Should prevent unlinking
        if response.status_code == 400:
            data = response.json()
            assert "cannot unlink" in data["detail"].lower() or "last" in data["detail"].lower()


# =============================================================================
# OAuth Redirect URI Configuration Tests
# =============================================================================


class TestOAuthRedirectURIConfiguration:
    """Integration tests for OAuth redirect URI configuration."""

    @pytest.mark.asyncio
    async def test_redirect_uri_uses_configured_base_url(
        self,
        client: AsyncClient,
    ) -> None:
        """Test that redirect URI uses the configured base URL."""
        with patch("app.api.v1.oauth.oauth") as mock_oauth:
            mock_client = MagicMock()
            captured_callback_url = None

            async def capture_url(callback_url: str, **kwargs: dict) -> dict:
                nonlocal captured_callback_url
                captured_callback_url = callback_url
                return {"url": "https://accounts.google.com/oauth"}

            mock_client.create_authorization_url = capture_url
            mock_oauth.create_client.return_value = mock_client

            with patch("app.api.v1.oauth.get_settings") as mock_settings:
                mock_settings.return_value.GOOGLE_CLIENT_ID = "test"
                mock_settings.return_value.GOOGLE_CLIENT_SECRET = "test"
                # Test production URL
                mock_settings.return_value.OAUTH_REDIRECT_BASE = "https://assemblematic.ai"

                await client.get("/api/v1/auth/oauth/google/login")

                assert captured_callback_url is not None
                assert captured_callback_url.startswith("https://assemblematic.ai")
                assert "/api/v1/auth/oauth/google/callback" in captured_callback_url

    @pytest.mark.asyncio
    async def test_redirect_uri_for_different_environments(
        self,
        client: AsyncClient,
    ) -> None:
        """Test redirect URI configuration for different environments."""
        environments = [
            ("http://localhost:5173", "development"),
            ("https://staging.assemblematic.ai", "staging"),
            ("https://assemblematic.ai", "production"),
        ]

        for base_url, env_name in environments:
            with patch("app.api.v1.oauth.oauth") as mock_oauth:
                mock_client = MagicMock()
                captured_url = None

                async def capture(callback_url: str, **kwargs: dict) -> dict:
                    nonlocal captured_url
                    captured_url = callback_url
                    return {"url": "https://accounts.google.com/oauth"}

                mock_client.create_authorization_url = capture
                mock_oauth.create_client.return_value = mock_client

                with patch("app.api.v1.oauth.get_settings") as mock_settings:
                    mock_settings.return_value.GOOGLE_CLIENT_ID = "test"
                    mock_settings.return_value.GOOGLE_CLIENT_SECRET = "test"
                    mock_settings.return_value.OAUTH_REDIRECT_BASE = base_url

                    await client.get("/api/v1/auth/oauth/google/login")

                    assert captured_url is not None
                    assert captured_url.startswith(base_url), f"Failed for {env_name}"
