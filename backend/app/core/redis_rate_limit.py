"""
Redis-Backed Rate Limiting

Production-ready distributed rate limiting using Redis.
Supports sliding window, token bucket, and fixed window algorithms.
Falls back to in-memory if Redis unavailable.
"""

import asyncio
import hashlib
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import StrEnum

from app.core.config import settings

# =============================================================================
# Configuration
# =============================================================================


class RateLimitAlgorithm(StrEnum):
    """Rate limiting algorithms."""

    FIXED_WINDOW = "fixed_window"
    SLIDING_WINDOW = "sliding_window"
    TOKEN_BUCKET = "token_bucket"


@dataclass
class RateLimitResult:
    """Result of a rate limit check."""

    allowed: bool
    limit: int
    remaining: int
    reset_at: int  # Unix timestamp
    retry_after: int | None = None  # Seconds until retry

    def to_headers(self) -> dict[str, str]:
        """Convert to HTTP headers."""
        headers = {
            "X-RateLimit-Limit": str(self.limit),
            "X-RateLimit-Remaining": str(self.remaining),
            "X-RateLimit-Reset": str(self.reset_at),
        }
        if self.retry_after:
            headers["Retry-After"] = str(self.retry_after)
        return headers


# =============================================================================
# Abstract Rate Limiter
# =============================================================================


class RateLimiter(ABC):
    """Abstract base for rate limiters."""

    @abstractmethod
    async def check(
        self,
        key: str,
        limit: int,
        window_seconds: int,
    ) -> RateLimitResult:
        """Check if request is allowed and record it."""

    @abstractmethod
    async def get_remaining(
        self,
        key: str,
        limit: int,
        window_seconds: int,
    ) -> int:
        """Get remaining requests without consuming."""

    @abstractmethod
    async def reset(self, key: str) -> bool:
        """Reset a rate limit key."""


# =============================================================================
# Redis Rate Limiter
# =============================================================================


class RedisRateLimiter(RateLimiter):
    """
    Redis-backed rate limiter using sliding window algorithm.

    Uses sorted sets for precise sliding window rate limiting.
    """

    def __init__(
        self,
        redis_url: str | None = None,
        key_prefix: str = "ratelimit:",
    ):
        self.redis_url = redis_url or settings.REDIS_URL
        self.key_prefix = key_prefix
        self._redis = None
        self._connected = False

    async def _get_redis(self) -> Any:
        """Get Redis connection, creating if needed."""
        if self._redis is None:
            try:
                import redis.asyncio as redis

                self._redis = redis.from_url(
                    self.redis_url,
                    encoding="utf-8",
                    decode_responses=True,
                )
                await self._redis.ping()
                self._connected = True
            except Exception as e:
                print(f"Redis connection failed: {e}")
                self._connected = False
                return None
        return self._redis

    def _make_key(self, key: str) -> str:
        """Create Redis key with prefix."""
        return f"{self.key_prefix}{key}"

    async def check(
        self,
        key: str,
        limit: int,
        window_seconds: int,
    ) -> RateLimitResult:
        """
        Check rate limit using sliding window log algorithm.

        Uses Redis sorted set where:
        - Score = timestamp
        - Member = unique request ID
        """
        redis = await self._get_redis()
        if not redis:
            # Fallback: allow but don't track
            return RateLimitResult(
                allowed=True,
                limit=limit,
                remaining=limit - 1,
                reset_at=int(time.time()) + window_seconds,
            )

        redis_key = self._make_key(key)
        now = time.time()
        window_start = now - window_seconds

        pipe = redis.pipeline()

        # Remove old entries outside window
        pipe.zremrangebyscore(redis_key, 0, window_start)

        # Count current entries
        pipe.zcard(redis_key)

        # Add new entry (will execute only if under limit)
        request_id = f"{now}:{hashlib.md5(str(now).encode()).hexdigest()[:8]}"

        results = await pipe.execute()
        current_count = results[1]

        if current_count >= limit:
            # Over limit - find when oldest entry expires
            oldest = await redis.zrange(redis_key, 0, 0, withscores=True)
            retry_after = int(oldest[0][1] + window_seconds - now) + 1 if oldest else window_seconds

            return RateLimitResult(
                allowed=False,
                limit=limit,
                remaining=0,
                reset_at=int(now + retry_after),
                retry_after=max(1, retry_after),
            )

        # Under limit - add the request
        await redis.zadd(redis_key, {request_id: now})
        await redis.expire(redis_key, window_seconds + 60)  # Extra buffer

        return RateLimitResult(
            allowed=True,
            limit=limit,
            remaining=limit - current_count - 1,
            reset_at=int(now + window_seconds),
        )

    async def get_remaining(
        self,
        key: str,
        limit: int,
        window_seconds: int,
    ) -> int:
        """Get remaining requests without consuming."""
        redis = await self._get_redis()
        if not redis:
            return limit

        redis_key = self._make_key(key)
        now = time.time()
        window_start = now - window_seconds

        # Remove old entries and count
        await redis.zremrangebyscore(redis_key, 0, window_start)
        current_count: int = await redis.zcard(redis_key)

        return max(0, limit - current_count)

    async def reset(self, key: str) -> bool:
        """Reset a rate limit key."""
        redis = await self._get_redis()
        if not redis:
            return False

        redis_key = self._make_key(key)
        await redis.delete(redis_key)
        return True

    async def close(self) -> None:
        """Close Redis connection."""
        if self._redis:
            await self._redis.close()
            self._redis = None
            self._connected = False


# =============================================================================
# In-Memory Rate Limiter (Fallback)
# =============================================================================


class InMemoryRateLimiter(RateLimiter):
    """
    In-memory rate limiter for development/testing.

    Note: Not suitable for production with multiple workers.
    """

    def __init__(self) -> None:
        self._requests: dict[str, list[float]] = {}
        self._lock = asyncio.Lock()

    async def check(
        self,
        key: str,
        limit: int,
        window_seconds: int,
    ) -> RateLimitResult:
        """Check rate limit using sliding window."""
        async with self._lock:
            now = time.time()
            window_start = now - window_seconds

            # Get and filter requests
            if key not in self._requests:
                self._requests[key] = []

            self._requests[key] = [t for t in self._requests[key] if t > window_start]

            current_count = len(self._requests[key])

            if current_count >= limit:
                # Calculate retry after
                if self._requests[key]:
                    oldest = min(self._requests[key])
                    retry_after = int(oldest + window_seconds - now) + 1
                else:
                    retry_after = window_seconds

                return RateLimitResult(
                    allowed=False,
                    limit=limit,
                    remaining=0,
                    reset_at=int(now + retry_after),
                    retry_after=max(1, retry_after),
                )

            # Record request
            self._requests[key].append(now)

            return RateLimitResult(
                allowed=True,
                limit=limit,
                remaining=limit - current_count - 1,
                reset_at=int(now + window_seconds),
            )

    async def get_remaining(
        self,
        key: str,
        limit: int,
        window_seconds: int,
    ) -> int:
        """Get remaining without consuming."""
        now = time.time()
        window_start = now - window_seconds

        if key not in self._requests:
            return limit

        current_count = len([t for t in self._requests[key] if t > window_start])

        return max(0, limit - current_count)

    async def reset(self, key: str) -> bool:
        """Reset a rate limit key."""
        if key in self._requests:
            del self._requests[key]
            return True
        return False

    def cleanup(self, max_age_seconds: int = 3600) -> None:
        """Remove old entries to prevent memory growth."""
        now = time.time()
        cutoff = now - max_age_seconds

        keys_to_delete = []
        for key, timestamps in self._requests.items():
            self._requests[key] = [t for t in timestamps if t > cutoff]
            if not self._requests[key]:
                keys_to_delete.append(key)

        for key in keys_to_delete:
            del self._requests[key]


# =============================================================================
# Token Bucket Rate Limiter
# =============================================================================


class TokenBucketRateLimiter(RateLimiter):
    """
    Token bucket rate limiter using Redis.

    Good for allowing bursts while maintaining average rate.
    """

    def __init__(
        self,
        redis_url: str | None = None,
        key_prefix: str = "tokenbucket:",
    ):
        self.redis_url = redis_url or settings.REDIS_URL
        self.key_prefix = key_prefix
        self._redis = None

    async def _get_redis(self) -> Any:
        """Get Redis connection."""
        if self._redis is None:
            try:
                import redis.asyncio as redis

                self._redis = redis.from_url(
                    self.redis_url,
                    encoding="utf-8",
                    decode_responses=True,
                )
            except Exception:
                return None
        return self._redis

    async def check(
        self,
        key: str,
        limit: int,  # Bucket capacity
        window_seconds: int,  # Time to refill fully
    ) -> RateLimitResult:
        """
        Check token bucket.

        Tokens refill at rate of limit/window_seconds per second.
        """
        redis = await self._get_redis()
        if not redis:
            return RateLimitResult(
                allowed=True,
                limit=limit,
                remaining=limit - 1,
                reset_at=int(time.time()) + window_seconds,
            )

        redis_key = f"{self.key_prefix}{key}"
        now = time.time()
        refill_rate = limit / window_seconds

        # Get current bucket state
        data = await redis.hgetall(redis_key)

        if data:
            tokens = float(data.get("tokens", limit))
            last_update = float(data.get("last_update", now))

            # Calculate tokens to add
            elapsed = now - last_update
            tokens = min(limit, tokens + (elapsed * refill_rate))
        else:
            tokens = limit
            last_update = now

        if tokens < 1:
            # Not enough tokens
            wait_time = (1 - tokens) / refill_rate
            return RateLimitResult(
                allowed=False,
                limit=limit,
                remaining=0,
                reset_at=int(now + wait_time),
                retry_after=int(wait_time) + 1,
            )

        # Consume token
        tokens -= 1

        # Update bucket
        await redis.hset(
            redis_key,
            mapping={
                "tokens": tokens,
                "last_update": now,
            },
        )
        await redis.expire(redis_key, window_seconds * 2)

        return RateLimitResult(
            allowed=True,
            limit=limit,
            remaining=int(tokens),
            reset_at=int(now + (limit - tokens) / refill_rate),
        )

    async def get_remaining(
        self,
        key: str,
        limit: int,
        window_seconds: int,
    ) -> int:
        """Get remaining tokens."""
        redis = await self._get_redis()
        if not redis:
            return limit

        redis_key = f"{self.key_prefix}{key}"
        now = time.time()
        refill_rate = limit / window_seconds

        data = await redis.hgetall(redis_key)
        if not data:
            return limit

        tokens = float(data.get("tokens", limit))
        last_update = float(data.get("last_update", now))

        elapsed = now - last_update
        tokens = min(limit, tokens + (elapsed * refill_rate))

        return int(tokens)

    async def reset(self, key: str) -> bool:
        """Reset bucket to full."""
        redis = await self._get_redis()
        if not redis:
            return False

        redis_key = f"{self.key_prefix}{key}"
        await redis.delete(redis_key)
        return True


# =============================================================================
# Rate Limiter Factory
# =============================================================================

_rate_limiter: RateLimiter | None = None


async def get_rate_limiter() -> RateLimiter:
    """Get the configured rate limiter instance."""
    global _rate_limiter

    if _rate_limiter is None:
        # Try Redis first
        if settings.REDIS_URL:
            redis_limiter = RedisRateLimiter(settings.REDIS_URL)
            redis = await redis_limiter._get_redis()
            if redis:
                _rate_limiter = redis_limiter
            else:
                print("Redis unavailable, using in-memory rate limiter")
                _rate_limiter = InMemoryRateLimiter()
        else:
            _rate_limiter = InMemoryRateLimiter()

    return _rate_limiter


def get_rate_limit_key(
    user_id: str | None,
    ip_address: str,
    endpoint: str,
) -> str:
    """Generate rate limit key."""
    if user_id:
        return f"user:{user_id}:{endpoint}"
    return f"ip:{ip_address}:{endpoint}"
