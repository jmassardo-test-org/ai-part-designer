"""
Redis caching layer.

Provides async Redis client with caching utilities,
rate limiting support, and distributed locking.
"""

import json
from datetime import timedelta
from typing import Any, Callable, TypeVar
from functools import wraps
import hashlib

import redis.asyncio as redis
from redis.asyncio.lock import Lock

from app.core.config import settings

T = TypeVar("T")


class RedisClient:
    """
    Async Redis client wrapper with caching utilities.
    
    Provides:
    - Key-value caching with TTL
    - JSON serialization
    - Rate limiting
    - Distributed locks
    - Pub/sub support
    """

    def __init__(self, url: str | None = None):
        self.url = url or settings.REDIS_URL
        self._client: redis.Redis | None = None

    async def connect(self) -> None:
        """Initialize Redis connection pool."""
        self._client = redis.from_url(
            self.url,
            encoding="utf-8",
            decode_responses=True,
        )

    async def disconnect(self) -> None:
        """Close Redis connections."""
        if self._client:
            await self._client.close()
            self._client = None

    @property
    def client(self) -> redis.Redis:
        """Get the Redis client, ensuring connection."""
        if not self._client:
            raise RuntimeError("Redis client not connected. Call connect() first.")
        return self._client

    # =========================================================================
    # Basic Key-Value Operations
    # =========================================================================

    async def get(self, key: str) -> str | None:
        """Get a string value."""
        return await self.client.get(key)

    async def set(
        self,
        key: str,
        value: str,
        *,
        ttl: int | timedelta | None = None,
    ) -> None:
        """Set a string value with optional TTL."""
        if isinstance(ttl, timedelta):
            ttl = int(ttl.total_seconds())
        await self.client.set(key, value, ex=ttl)

    async def delete(self, *keys: str) -> int:
        """Delete one or more keys."""
        return await self.client.delete(*keys)

    async def exists(self, key: str) -> bool:
        """Check if a key exists."""
        return await self.client.exists(key) > 0

    async def expire(self, key: str, ttl: int | timedelta) -> bool:
        """Set TTL on an existing key."""
        if isinstance(ttl, timedelta):
            ttl = int(ttl.total_seconds())
        return await self.client.expire(key, ttl)

    async def ttl(self, key: str) -> int:
        """Get remaining TTL for a key (-1 if no TTL, -2 if doesn't exist)."""
        return await self.client.ttl(key)

    # =========================================================================
    # JSON Operations
    # =========================================================================

    async def get_json(self, key: str) -> Any | None:
        """Get and deserialize JSON value."""
        value = await self.get(key)
        if value:
            return json.loads(value)
        return None

    async def set_json(
        self,
        key: str,
        value: Any,
        *,
        ttl: int | timedelta | None = None,
    ) -> None:
        """Serialize and set JSON value."""
        await self.set(key, json.dumps(value, default=str), ttl=ttl)

    # =========================================================================
    # Cache Decorators
    # =========================================================================

    def cached(
        self,
        key_prefix: str,
        ttl: int | timedelta = 300,
        key_builder: Callable[..., str] | None = None,
    ):
        """
        Decorator for caching function results.
        
        Args:
            key_prefix: Prefix for cache keys
            ttl: Time-to-live in seconds or timedelta
            key_builder: Custom function to build cache key from args
            
        Example:
            @redis_client.cached("user", ttl=300)
            async def get_user(user_id: str) -> User:
                ...
        """
        def decorator(func: Callable[..., T]) -> Callable[..., T]:
            @wraps(func)
            async def wrapper(*args, **kwargs) -> T:
                # Build cache key
                if key_builder:
                    cache_key = f"{key_prefix}:{key_builder(*args, **kwargs)}"
                else:
                    key_parts = [str(a) for a in args] + [f"{k}={v}" for k, v in sorted(kwargs.items())]
                    key_hash = hashlib.md5(":".join(key_parts).encode()).hexdigest()[:12]
                    cache_key = f"{key_prefix}:{key_hash}"
                
                # Try cache
                cached_value = await self.get_json(cache_key)
                if cached_value is not None:
                    return cached_value
                
                # Execute function
                result = await func(*args, **kwargs)
                
                # Cache result
                if result is not None:
                    await self.set_json(cache_key, result, ttl=ttl)
                
                return result
            
            return wrapper
        return decorator

    async def invalidate_pattern(self, pattern: str) -> int:
        """Delete all keys matching a pattern."""
        keys = []
        async for key in self.client.scan_iter(match=pattern):
            keys.append(key)
        
        if keys:
            return await self.delete(*keys)
        return 0

    # =========================================================================
    # Rate Limiting
    # =========================================================================

    async def check_rate_limit(
        self,
        key: str,
        max_requests: int,
        window_seconds: int,
    ) -> tuple[bool, int]:
        """
        Check and increment rate limit counter.
        
        Returns:
            Tuple of (is_allowed, remaining_requests)
        """
        pipe = self.client.pipeline()
        
        pipe.incr(key)
        pipe.ttl(key)
        
        results = await pipe.execute()
        current_count = results[0]
        current_ttl = results[1]
        
        # Set TTL if this is a new key
        if current_ttl == -1:
            await self.expire(key, window_seconds)
        
        remaining = max(0, max_requests - current_count)
        is_allowed = current_count <= max_requests
        
        return is_allowed, remaining

    async def get_rate_limit_status(
        self,
        key: str,
        max_requests: int,
    ) -> dict:
        """Get current rate limit status."""
        current = await self.get(key)
        ttl = await self.ttl(key)
        
        current_count = int(current) if current else 0
        remaining = max(0, max_requests - current_count)
        
        return {
            "limit": max_requests,
            "remaining": remaining,
            "reset_in": max(0, ttl),
            "is_limited": current_count >= max_requests,
        }

    # =========================================================================
    # Distributed Locks
    # =========================================================================

    def lock(
        self,
        name: str,
        timeout: float = 30.0,
        blocking: bool = True,
        blocking_timeout: float | None = None,
    ) -> Lock:
        """
        Get a distributed lock.
        
        Example:
            async with redis_client.lock("resource:123"):
                # Do exclusive work
                pass
        """
        return Lock(
            self.client,
            name=f"lock:{name}",
            timeout=timeout,
            blocking=blocking,
            blocking_timeout=blocking_timeout,
        )

    # =========================================================================
    # Pub/Sub
    # =========================================================================

    async def publish(self, channel: str, message: Any) -> int:
        """Publish a message to a channel."""
        if not isinstance(message, str):
            message = json.dumps(message, default=str)
        return await self.client.publish(channel, message)

    def pubsub(self):
        """Get a pub/sub client."""
        return self.client.pubsub()

    # =========================================================================
    # Counter Operations
    # =========================================================================

    async def incr(self, key: str, amount: int = 1) -> int:
        """Increment a counter."""
        return await self.client.incrby(key, amount)

    async def decr(self, key: str, amount: int = 1) -> int:
        """Decrement a counter."""
        return await self.client.decrby(key, amount)

    # =========================================================================
    # Hash Operations
    # =========================================================================

    async def hget(self, name: str, key: str) -> str | None:
        """Get a hash field."""
        return await self.client.hget(name, key)

    async def hset(self, name: str, key: str, value: str) -> int:
        """Set a hash field."""
        return await self.client.hset(name, key, value)

    async def hgetall(self, name: str) -> dict:
        """Get all hash fields."""
        return await self.client.hgetall(name)

    async def hdel(self, name: str, *keys: str) -> int:
        """Delete hash fields."""
        return await self.client.hdel(name, *keys)

    # =========================================================================
    # List Operations (for simple queues)
    # =========================================================================

    async def lpush(self, key: str, *values: str) -> int:
        """Push values to the left of a list."""
        return await self.client.lpush(key, *values)

    async def rpop(self, key: str) -> str | None:
        """Pop from the right of a list."""
        return await self.client.rpop(key)

    async def llen(self, key: str) -> int:
        """Get list length."""
        return await self.client.llen(key)


# Global Redis client instance
redis_client = RedisClient()


async def get_redis() -> RedisClient:
    """Dependency for getting Redis client."""
    return redis_client
