"""
Undo token service using Redis for distributed storage.

Provides secure, distributed undo token management for
operations like delete with time-limited recovery.
"""

import logging
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any, TypedDict
from uuid import UUID

from app.core.cache import redis_client

logger = logging.getLogger(__name__)


# =============================================================================
# Types
# =============================================================================


class UndoTokenData(TypedDict):
    """Data stored with an undo token."""

    design_id: str
    user_id: str
    operation: str
    created_at: str
    expires_at: str
    metadata: dict[str, Any]


@dataclass
class UndoToken:
    """Undo token with associated data."""

    token: str
    design_id: UUID
    user_id: UUID
    operation: str
    expires_at: datetime
    metadata: dict[str, Any]


# =============================================================================
# Constants
# =============================================================================

UNDO_TOKEN_PREFIX = "undo_token"
DEFAULT_TTL_SECONDS = 30


# =============================================================================
# Token Operations
# =============================================================================


def generate_undo_token() -> str:
    """Generate a cryptographically secure undo token."""
    return secrets.token_urlsafe(32)


async def store_undo_token(
    design_id: UUID,
    user_id: UUID,
    operation: str = "delete",
    ttl_seconds: int = DEFAULT_TTL_SECONDS,
    metadata: dict[str, Any] | None = None,
) -> UndoToken:
    """
    Store an undo token in Redis with expiration.

    Args:
        design_id: ID of the design being operated on
        user_id: ID of the user who performed the operation
        operation: Type of operation (e.g., "delete", "move")
        ttl_seconds: Time-to-live in seconds
        metadata: Additional data to store

    Returns:
        UndoToken with the generated token and data
    """
    token = generate_undo_token()
    expires_at = datetime.now(UTC) + timedelta(seconds=ttl_seconds)

    data: UndoTokenData = {
        "design_id": str(design_id),
        "user_id": str(user_id),
        "operation": operation,
        "created_at": datetime.now(UTC).isoformat(),
        "expires_at": expires_at.isoformat(),
        "metadata": metadata or {},
    }

    key = f"{UNDO_TOKEN_PREFIX}:{token}"

    try:
        await redis_client.set_json(key, data, ttl=ttl_seconds)
        logger.debug(f"Stored undo token: {token[:8]}... for design {design_id}")
    except Exception as e:
        logger.error(f"Failed to store undo token in Redis: {e}")
        raise

    return UndoToken(
        token=token,
        design_id=design_id,
        user_id=user_id,
        operation=operation,
        expires_at=expires_at,
        metadata=metadata or {},
    )


async def get_undo_token(token: str) -> UndoToken | None:
    """
    Retrieve an undo token from Redis.

    Args:
        token: The undo token string

    Returns:
        UndoToken if valid and not expired, None otherwise
    """
    key = f"{UNDO_TOKEN_PREFIX}:{token}"

    try:
        data: UndoTokenData | None = await redis_client.get_json(key)

        if not data:
            logger.debug(f"Undo token not found or expired: {token[:8]}...")
            return None

        return UndoToken(
            token=token,
            design_id=UUID(data["design_id"]),
            user_id=UUID(data["user_id"]),
            operation=data["operation"],
            expires_at=datetime.fromisoformat(data["expires_at"]),
            metadata=data.get("metadata", {}),
        )
    except Exception as e:
        logger.error(f"Failed to retrieve undo token from Redis: {e}")
        return None


async def invalidate_undo_token(token: str) -> bool:
    """
    Invalidate (delete) an undo token.

    Args:
        token: The undo token to invalidate

    Returns:
        True if token was deleted, False if it didn't exist
    """
    key = f"{UNDO_TOKEN_PREFIX}:{token}"

    try:
        deleted = await redis_client.delete(key)
        if deleted:
            logger.debug(f"Invalidated undo token: {token[:8]}...")
        return deleted > 0
    except Exception as e:
        logger.error(f"Failed to invalidate undo token: {e}")
        return False


async def validate_undo_token(token: str, user_id: UUID) -> UndoToken | None:
    """
    Validate an undo token for a specific user.

    Args:
        token: The undo token to validate
        user_id: Expected user ID (must match token's user_id)

    Returns:
        UndoToken if valid and owned by user, None otherwise
    """
    undo_token = await get_undo_token(token)

    if not undo_token:
        return None

    if undo_token.user_id != user_id:
        # Log potential security issue but don't reveal to caller
        logger.warning(f"Undo token user mismatch: expected {user_id}, got {undo_token.user_id}")
        return None

    return undo_token


# =============================================================================
# Fallback (in-memory) for when Redis is unavailable
# =============================================================================

_fallback_tokens: dict[str, UndoTokenData] = {}


async def store_undo_token_fallback(
    design_id: UUID,
    user_id: UUID,
    operation: str = "delete",
    ttl_seconds: int = DEFAULT_TTL_SECONDS,
    metadata: dict[str, Any] | None = None,
) -> UndoToken:
    """
    Fallback in-memory storage when Redis is unavailable.

    WARNING: This is NOT suitable for production multi-instance deployments.
    """
    logger.warning("Using in-memory fallback for undo token storage")

    token = generate_undo_token()
    expires_at = datetime.now(UTC) + timedelta(seconds=ttl_seconds)

    data: UndoTokenData = {
        "design_id": str(design_id),
        "user_id": str(user_id),
        "operation": operation,
        "created_at": datetime.now(UTC).isoformat(),
        "expires_at": expires_at.isoformat(),
        "metadata": metadata or {},
    }

    _fallback_tokens[token] = data

    return UndoToken(
        token=token,
        design_id=design_id,
        user_id=user_id,
        operation=operation,
        expires_at=expires_at,
        metadata=metadata or {},
    )


def get_undo_token_fallback(token: str) -> UndoToken | None:
    """Fallback retrieval from in-memory storage."""
    data = _fallback_tokens.get(token)

    if not data:
        return None

    expires_at = datetime.fromisoformat(data["expires_at"])
    if datetime.now(UTC) > expires_at:
        del _fallback_tokens[token]
        return None

    return UndoToken(
        token=token,
        design_id=UUID(data["design_id"]),
        user_id=UUID(data["user_id"]),
        operation=data["operation"],
        expires_at=expires_at,
        metadata=data.get("metadata", {}),
    )
