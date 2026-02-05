"""
Tests for authentication endpoints.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING
from uuid import uuid4

import pytest

from app.core.security import create_refresh_token, hash_password
from app.models import User

if TYPE_CHECKING:
    from httpx import AsyncClient

# =============================================================================
# Registration Tests
# =============================================================================


class TestRegistration:
    """Tests for POST /api/v1/auth/register endpoint."""

    @pytest.mark.asyncio
    async def test_register_success(self, client: AsyncClient, db_session):
        """Test successful user registration."""
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "newuser@example.com",
                "password": "SecurePass123!",
                "display_name": "New User",
                "accepted_terms": True,
            },
        )

        assert response.status_code == 201
        data = response.json()

        assert data["email"] == "newuser@example.com"
        assert data["display_name"] == "New User"
        assert data["role"] == "user"
        assert "id" in data

    @pytest.mark.asyncio
    async def test_register_duplicate_email(self, client: AsyncClient, test_user):
        """Test registration with existing email fails."""
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": test_user.email,  # Already exists
                "password": "SecurePass123!",
                "display_name": "Another User",
                "accepted_terms": True,
            },
        )

        assert response.status_code == 409
        assert "already exists" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_register_weak_password(self, client: AsyncClient):
        """Test registration with weak password fails."""
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "test@example.com",
                "password": "weak",  # Too short, no special chars
                "display_name": "Test User",
                "accepted_terms": True,
            },
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_register_invalid_email(self, client: AsyncClient):
        """Test registration with invalid email fails."""
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "not-an-email",
                "password": "SecurePass123!",
                "display_name": "Test User",
                "accepted_terms": True,
            },
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_register_terms_not_accepted(self, client: AsyncClient):
        """Test registration without accepting terms fails."""
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "test@example.com",
                "password": "SecurePass123!",
                "display_name": "Test User",
                "accepted_terms": False,
            },
        )

        assert response.status_code == 422


# =============================================================================
# Login Tests
# =============================================================================


class TestLogin:
    """Tests for POST /api/v1/auth/login endpoint."""

    @pytest.mark.asyncio
    async def test_login_success(self, client: AsyncClient, db_session):
        """Test successful login."""
        # Create active user
        user = User(
            email="active@example.com",
            password_hash=hash_password("SecurePass123!"),
            display_name="Active User",
            role="user",
            status="active",
            email_verified_at=datetime.now(tz=datetime.UTC),
        )
        db_session.add(user)
        await db_session.commit()

        response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "active@example.com",
                "password": "SecurePass123!",
            },
        )

        assert response.status_code == 200
        data = response.json()

        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
        assert data["expires_in"] > 0

    @pytest.mark.asyncio
    async def test_login_wrong_password(self, client: AsyncClient, db_session):
        """Test login with wrong password fails."""
        user = User(
            email="test@example.com",
            password_hash=hash_password("CorrectPass123!"),
            display_name="Test User",
            status="active",
            email_verified_at=datetime.now(tz=datetime.UTC),
        )
        db_session.add(user)
        await db_session.commit()

        response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "test@example.com",
                "password": "WrongPass123!",
            },
        )

        assert response.status_code == 401
        assert "invalid" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_login_nonexistent_user(self, client: AsyncClient):
        """Test login with nonexistent email fails."""
        response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "nonexistent@example.com",
                "password": "SomePass123!",
            },
        )

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_login_unverified_user(self, client: AsyncClient, db_session):
        """Test login with unverified email fails."""
        user = User(
            email="unverified@example.com",
            password_hash=hash_password("SecurePass123!"),
            display_name="Unverified User",
            status="pending_verification",
        )
        db_session.add(user)
        await db_session.commit()

        response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "unverified@example.com",
                "password": "SecurePass123!",
            },
        )

        assert response.status_code == 403
        assert "verify" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_login_suspended_user(self, client: AsyncClient, db_session):
        """Test login with suspended account fails."""
        user = User(
            email="suspended@example.com",
            password_hash=hash_password("SecurePass123!"),
            display_name="Suspended User",
            status="suspended",
        )
        db_session.add(user)
        await db_session.commit()

        response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "suspended@example.com",
                "password": "SecurePass123!",
            },
        )

        assert response.status_code == 403
        assert "suspended" in response.json()["detail"].lower()


# =============================================================================
# Token Refresh Tests
# =============================================================================


class TestTokenRefresh:
    """Tests for POST /api/v1/auth/refresh endpoint."""

    @pytest.mark.asyncio
    async def test_refresh_success(self, client: AsyncClient, db_session):
        """Test successful token refresh."""
        # Create active user
        user = User(
            id=uuid4(),
            email="refresh@example.com",
            password_hash=hash_password("SecurePass123!"),
            display_name="Refresh User",
            status="active",
        )
        db_session.add(user)
        await db_session.commit()

        # Generate refresh token
        refresh_token, _ = create_refresh_token(user.id)

        response = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token},
        )

        assert response.status_code == 200
        data = response.json()

        assert "access_token" in data
        assert "refresh_token" in data

    @pytest.mark.asyncio
    async def test_refresh_invalid_token(self, client: AsyncClient):
        """Test refresh with invalid token fails."""
        response = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": "invalid.token.here"},
        )

        assert response.status_code == 401


# =============================================================================
# Current User Tests
# =============================================================================


class TestGetMe:
    """Tests for GET /api/v1/auth/me endpoint."""

    @pytest.mark.asyncio
    async def test_get_me_authenticated(self, client: AsyncClient, test_user, auth_headers):
        """Test getting current user when authenticated."""
        response = await client.get(
            "/api/v1/auth/me",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()

        assert data["email"] == test_user.email
        assert data["display_name"] == test_user.display_name

    @pytest.mark.asyncio
    async def test_get_me_unauthenticated(self, client: AsyncClient):
        """Test getting current user without auth fails."""
        response = await client.get("/api/v1/auth/me")

        assert response.status_code == 401


# =============================================================================
# Password Reset Tests
# =============================================================================


class TestPasswordReset:
    """Tests for password reset endpoints."""

    @pytest.mark.asyncio
    async def test_forgot_password_existing_user(self, client: AsyncClient, test_user):
        """Test forgot password for existing user."""
        response = await client.post(
            "/api/v1/auth/forgot-password",
            json={"email": test_user.email},
        )

        # Always returns 200 to prevent email enumeration
        assert response.status_code == 200
        assert "email has been sent" in response.json()["message"].lower()

    @pytest.mark.asyncio
    async def test_forgot_password_nonexistent_user(self, client: AsyncClient):
        """Test forgot password for nonexistent user (should not reveal)."""
        response = await client.post(
            "/api/v1/auth/forgot-password",
            json={"email": "nonexistent@example.com"},
        )

        # Same response to prevent enumeration
        assert response.status_code == 200


# =============================================================================
# Logout Tests
# =============================================================================


class TestLogout:
    """Tests for POST /api/v1/auth/logout endpoint."""

    @pytest.mark.asyncio
    async def test_logout_success(self, client: AsyncClient, auth_headers):
        """Test successful logout."""
        response = await client.post(
            "/api/v1/auth/logout",
            headers=auth_headers,
        )

        assert response.status_code == 200
        assert "logged out" in response.json()["message"].lower()
