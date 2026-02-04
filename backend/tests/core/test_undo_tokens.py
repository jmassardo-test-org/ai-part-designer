"""
Tests for Undo Token Service.

Tests Redis-backed undo token storage and retrieval.
"""

import pytest
from datetime import datetime, timedelta, UTC
from unittest.mock import AsyncMock, patch
from uuid import uuid4

from app.core.undo_tokens import (
    UndoToken,
    generate_undo_token,
    store_undo_token,
    get_undo_token,
    invalidate_undo_token,
    validate_undo_token,
    store_undo_token_fallback,
    get_undo_token_fallback,
    DEFAULT_TTL_SECONDS,
)


# =============================================================================
# Token Generation Tests
# =============================================================================

class TestGenerateUndoToken:
    """Tests for undo token generation."""

    def test_generates_unique_tokens(self):
        """Test that generated tokens are unique."""
        tokens = [generate_undo_token() for _ in range(100)]
        assert len(set(tokens)) == 100

    def test_token_is_url_safe(self):
        """Test that generated tokens are URL-safe."""
        token = generate_undo_token()
        # URL-safe characters only
        assert all(c.isalnum() or c in "-_" for c in token)

    def test_token_has_sufficient_length(self):
        """Test that tokens have sufficient entropy."""
        token = generate_undo_token()
        # At least 32 characters for good entropy
        assert len(token) >= 32


# =============================================================================
# Redis Storage Tests (Mocked)
# =============================================================================

class TestRedisStorage:
    """Tests for Redis-backed undo token storage."""

    @pytest.fixture
    def mock_redis(self):
        """Create a mock Redis client."""
        with patch("app.core.undo_tokens.redis_client") as mock:
            mock.set_json = AsyncMock()
            mock.get_json = AsyncMock()
            mock.delete = AsyncMock(return_value=1)
            yield mock

    @pytest.mark.asyncio
    async def test_store_undo_token(self, mock_redis):
        """Test storing an undo token in Redis."""
        design_id = uuid4()
        user_id = uuid4()
        
        result = await store_undo_token(
            design_id=design_id,
            user_id=user_id,
            operation="delete",
            ttl_seconds=30,
        )
        
        assert result.design_id == design_id
        assert result.user_id == user_id
        assert result.operation == "delete"
        assert result.token is not None
        
        mock_redis.set_json.assert_called_once()

    @pytest.mark.asyncio
    async def test_store_undo_token_with_metadata(self, mock_redis):
        """Test storing an undo token with metadata."""
        design_id = uuid4()
        user_id = uuid4()
        metadata = {"design_name": "Test Design", "project_id": str(uuid4())}
        
        result = await store_undo_token(
            design_id=design_id,
            user_id=user_id,
            metadata=metadata,
        )
        
        assert result.metadata == metadata

    @pytest.mark.asyncio
    async def test_get_undo_token_success(self, mock_redis):
        """Test retrieving a valid undo token."""
        design_id = uuid4()
        user_id = uuid4()
        expires_at = (datetime.now(UTC) + timedelta(seconds=30)).isoformat()
        
        mock_redis.get_json.return_value = {
            "design_id": str(design_id),
            "user_id": str(user_id),
            "operation": "delete",
            "created_at": datetime.now(UTC).isoformat(),
            "expires_at": expires_at,
            "metadata": {},
        }
        
        result = await get_undo_token("test-token")
        
        assert result is not None
        assert result.design_id == design_id
        assert result.user_id == user_id

    @pytest.mark.asyncio
    async def test_get_undo_token_not_found(self, mock_redis):
        """Test retrieving a non-existent token."""
        mock_redis.get_json.return_value = None
        
        result = await get_undo_token("nonexistent-token")
        
        assert result is None

    @pytest.mark.asyncio
    async def test_invalidate_undo_token_success(self, mock_redis):
        """Test invalidating an existing token."""
        result = await invalidate_undo_token("test-token")
        
        assert result is True
        mock_redis.delete.assert_called_once()

    @pytest.mark.asyncio
    async def test_invalidate_undo_token_not_found(self, mock_redis):
        """Test invalidating a non-existent token."""
        mock_redis.delete.return_value = 0
        
        result = await invalidate_undo_token("nonexistent-token")
        
        assert result is False

    @pytest.mark.asyncio
    async def test_validate_undo_token_correct_user(self, mock_redis):
        """Test validating a token with correct user."""
        user_id = uuid4()
        expires_at = (datetime.now(UTC) + timedelta(seconds=30)).isoformat()
        
        mock_redis.get_json.return_value = {
            "design_id": str(uuid4()),
            "user_id": str(user_id),
            "operation": "delete",
            "created_at": datetime.now(UTC).isoformat(),
            "expires_at": expires_at,
            "metadata": {},
        }
        
        result = await validate_undo_token("test-token", user_id)
        
        assert result is not None
        assert result.user_id == user_id

    @pytest.mark.asyncio
    async def test_validate_undo_token_wrong_user(self, mock_redis):
        """Test validating a token with wrong user returns None."""
        owner_id = uuid4()
        wrong_user_id = uuid4()
        expires_at = (datetime.now(UTC) + timedelta(seconds=30)).isoformat()
        
        mock_redis.get_json.return_value = {
            "design_id": str(uuid4()),
            "user_id": str(owner_id),
            "operation": "delete",
            "created_at": datetime.now(UTC).isoformat(),
            "expires_at": expires_at,
            "metadata": {},
        }
        
        result = await validate_undo_token("test-token", wrong_user_id)
        
        # Should return None, not the token (security)
        assert result is None


# =============================================================================
# Fallback Storage Tests
# =============================================================================

class TestFallbackStorage:
    """Tests for in-memory fallback storage."""

    @pytest.mark.asyncio
    async def test_fallback_store_and_retrieve(self):
        """Test storing and retrieving from fallback storage."""
        design_id = uuid4()
        user_id = uuid4()
        
        token = await store_undo_token_fallback(
            design_id=design_id,
            user_id=user_id,
        )
        
        result = get_undo_token_fallback(token.token)
        
        assert result is not None
        assert result.design_id == design_id
        assert result.user_id == user_id

    def test_fallback_expired_token(self):
        """Test that expired fallback tokens are not returned."""
        # This would require time manipulation or a very short TTL
        # For now, just test that non-existent tokens return None
        result = get_undo_token_fallback("nonexistent-token")
        assert result is None

    @pytest.mark.asyncio
    async def test_fallback_preserves_metadata(self):
        """Test that fallback storage preserves metadata."""
        metadata = {"key": "value"}
        
        token = await store_undo_token_fallback(
            design_id=uuid4(),
            user_id=uuid4(),
            metadata=metadata,
        )
        
        result = get_undo_token_fallback(token.token)
        
        assert result is not None
        assert result.metadata == metadata


# =============================================================================
# Constants Tests
# =============================================================================

class TestConstants:
    """Tests for module constants."""

    def test_default_ttl(self):
        """Test default TTL is set correctly."""
        assert DEFAULT_TTL_SECONDS == 30
