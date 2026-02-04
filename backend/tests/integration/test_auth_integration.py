"""
Integration tests for authentication workflows.

Tests user registration, login, token handling, and session management.
"""

from __future__ import annotations

import pytest
from uuid import uuid4
from datetime import datetime, timezone


# =============================================================================
# User Registration Integration Tests
# =============================================================================

class TestUserRegistrationIntegration:
    """Integration tests for user registration flow."""
    
    @pytest.mark.asyncio
    async def test_create_user_in_database(self, db_session):
        """Test creating a user record in database."""
        from app.models import User
        from app.core.security import hash_password
        from app.repositories import UserRepository
        
        user_id = uuid4()
        user = User(
            id=user_id,
            email=f"integration_test_{uuid4().hex[:8]}@example.com",
            password_hash=hash_password("TestPassword123!"),
            display_name="Integration Test User",
            status="active",
        )
        db_session.add(user)
        await db_session.commit()
        
        user_repo = UserRepository(db_session)
        fetched_user = await user_repo.get_by_id(user_id)
        
        assert fetched_user is not None
        assert fetched_user.status == "active"
    
    @pytest.mark.asyncio
    async def test_user_email_uniqueness(self, db_session):
        """Test that duplicate emails are rejected."""
        from app.models import User
        from app.core.security import hash_password
        from sqlalchemy.exc import IntegrityError
        
        email = f"unique_test_{uuid4().hex[:8]}@example.com"
        
        # Create first user
        user1 = User(
            id=uuid4(),
            email=email,
            password_hash=hash_password("TestPassword123!"),
            display_name="User 1",
        )
        db_session.add(user1)
        await db_session.commit()
        
        # Try to create second user with same email
        user2 = User(
            id=uuid4(),
            email=email,
            password_hash=hash_password("TestPassword456!"),
            display_name="User 2",
        )
        db_session.add(user2)
        
        with pytest.raises(IntegrityError):
            await db_session.commit()
        
        await db_session.rollback()


# =============================================================================
# Password Verification Integration Tests
# =============================================================================

class TestPasswordVerificationIntegration:
    """Integration tests for password handling."""
    
    def test_password_hashing_and_verification(self):
        """Test that password hashing and verification works."""
        from app.core.security import hash_password, verify_password
        
        password = "SecurePassword123!"
        hashed = hash_password(password)
        
        # Hash should be different from password
        assert hashed != password
        
        # Should verify correctly
        assert verify_password(password, hashed) is True
        
        # Wrong password should fail
        assert verify_password("WrongPassword", hashed) is False
    
    def test_password_hash_is_unique(self):
        """Test that same password produces different hashes (salted)."""
        from app.core.security import hash_password
        
        password = "TestPassword123!"
        hash1 = hash_password(password)
        hash2 = hash_password(password)
        
        # Hashes should be different due to salting
        assert hash1 != hash2


# =============================================================================
# JWT Token Integration Tests
# =============================================================================

class TestJWTTokenIntegration:
    """Integration tests for JWT token handling."""
    
    def test_create_access_token(self):
        """Test creating JWT access token."""
        from app.core.security import create_access_token
        
        user_id = uuid4()
        token = create_access_token(
            user_id=user_id,
            email="test@example.com",
            role="user",
            tier="free",
        )
        
        assert token is not None
        assert len(token) > 0
        assert "." in token  # JWT format
    
    def test_token_structure(self):
        """Test JWT token has correct structure."""
        from app.core.security import create_access_token
        
        user_id = uuid4()
        token = create_access_token(
            user_id=user_id,
            email="test@example.com",
        )
        
        # JWT has 3 parts
        parts = token.split(".")
        assert len(parts) == 3


# =============================================================================
# User Repository Integration Tests
# =============================================================================

class TestUserRepositoryIntegration:
    """Integration tests for user repository operations."""
    
    @pytest.mark.asyncio
    async def test_get_user_by_email(self, db_session):
        """Test finding user by email."""
        from app.models import User
        from app.core.security import hash_password
        from app.repositories import UserRepository
        
        email = f"email_test_{uuid4().hex[:8]}@example.com"
        user = User(
            id=uuid4(),
            email=email,
            password_hash=hash_password("TestPassword123!"),
            display_name="Email Test User",
        )
        db_session.add(user)
        await db_session.commit()
        
        user_repo = UserRepository(db_session)
        found_user = await user_repo.get_by_email(email)
        
        assert found_user is not None
        assert found_user.email == email
    
    @pytest.mark.asyncio
    async def test_user_not_found_returns_none(self, db_session):
        """Test that non-existent user returns None."""
        from app.repositories import UserRepository
        
        user_repo = UserRepository(db_session)
        found_user = await user_repo.get_by_email("nonexistent@example.com")
        
        assert found_user is None
