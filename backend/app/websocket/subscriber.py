"""
Redis pub/sub listener for WebSocket message relay.

Listens to Redis channels for messages from Celery workers
and forwards them to connected WebSocket clients.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging

from app.websocket.manager import manager

logger = logging.getLogger(__name__)


class RedisSubscriber:
    """
    Subscribes to Redis channels and relays messages to WebSocket clients.

    This bridges the gap between synchronous Celery workers and
    the async WebSocket server.
    """

    def __init__(self) -> None:
        self._task: asyncio.Task[None] | None = None
        self._running = False
        self._redis = None
        self._pubsub = None

    async def start(self) -> None:
        """Start the Redis subscriber background task."""
        if self._task is not None:
            logger.warning("Redis subscriber already running")
            return

        try:
            from app.core.cache import redis_client

            # Get async Redis client
            # Note: This requires redis.asyncio or aioredis
            self._redis = redis_client.client
            self._running = True

            self._task = asyncio.create_task(self._run())
            logger.info("Redis subscriber started")
        except ImportError:
            logger.warning("Redis client not available, subscriber disabled")
        except Exception as e:
            logger.error(f"Failed to start Redis subscriber: {e}")

    async def stop(self) -> None:
        """Stop the Redis subscriber."""
        self._running = False

        if self._pubsub:
            try:
                await self._pubsub.unsubscribe()
                await self._pubsub.close()
            except Exception:
                pass

        if self._task:
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task
            self._task = None

        logger.info("Redis subscriber stopped")

    async def _run(self) -> None:
        """Main subscriber loop."""
        try:
            import redis.asyncio as aioredis
        except ImportError:
            logger.warning("aioredis not available, using polling fallback")
            await self._run_polling_fallback()
            return

        try:
            # Connect to Redis for pub/sub
            from app.core.config import get_settings

            settings = get_settings()
            redis_url = settings.REDIS_URL
            self._redis = await aioredis.from_url(redis_url)  # type: ignore[assignment]
            self._pubsub = self._redis.pubsub()  # type: ignore[attr-defined]

            # Subscribe to patterns for user and room messages
            await self._pubsub.psubscribe("ws:user:*", "ws:room:*")  # type: ignore[attr-defined]

            logger.info("Subscribed to Redis channels ws:user:* and ws:room:*")

            # Listen for messages
            async for message in self._pubsub.listen():  # type: ignore[attr-defined]
                if not self._running:
                    break

                if message["type"] != "pmessage":
                    continue

                try:
                    await self._handle_message(
                        message["channel"].decode("utf-8"),
                        message["data"],
                    )
                except Exception as e:
                    logger.error(f"Error handling Redis message: {e}")

        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.error(f"Redis subscriber error: {e}")
            # Retry after delay
            if self._running:
                await asyncio.sleep(5)
                self._task = asyncio.create_task(self._run())

    async def _run_polling_fallback(self) -> None:
        """Polling fallback if async Redis is not available."""
        # This fallback uses the async Redis client with polling
        # instead of pattern subscription
        logger.info("Using polling fallback for Redis pub/sub")

        try:
            from app.core.cache import redis_client

            # Use async pubsub from the existing client
            pubsub = redis_client.client.pubsub()
            await pubsub.psubscribe("ws:user:*", "ws:room:*")

            while self._running:
                # Use async get_message
                message = await pubsub.get_message(timeout=0.1)
                if message and message.get("type") == "pmessage":
                    try:
                        channel = message.get("channel", "")
                        data = message.get("data", "")

                        # Decode bytes if necessary
                        if isinstance(channel, bytes):
                            channel = channel.decode("utf-8")

                        await self._handle_message(channel, data)
                    except Exception as e:
                        logger.error(f"Error handling Redis message: {e}")

                await asyncio.sleep(0.01)

        except Exception as e:
            logger.error(f"Polling fallback error: {e}")
            if self._running:
                await asyncio.sleep(5)
                self._task = asyncio.create_task(self._run_polling_fallback())

    async def _handle_message(self, channel: str, data: bytes | str) -> None:
        """Handle a message from Redis."""
        if isinstance(data, bytes):
            data = data.decode("utf-8")

        try:
            message = json.loads(data)
        except json.JSONDecodeError:
            logger.warning(f"Invalid JSON in Redis message: {data}")
            return

        # Parse channel
        parts = channel.split(":")

        if len(parts) >= 3 and parts[0] == "ws":
            channel_type = parts[1]  # "user" or "room"
            channel_id = ":".join(parts[2:])  # ID (may contain colons)

            if channel_type == "user":
                # Send to specific user
                sent = await manager.send_to_user(channel_id, message)
                logger.debug(f"Relayed message to user {channel_id}: {sent} connections")

            elif channel_type == "room":
                # Send to room
                exclude_user = message.pop("_exclude_user", None)
                sent = await manager.send_to_room(channel_id, message, exclude_user)
                logger.debug(f"Relayed message to room {channel_id}: {sent} connections")


# Singleton instance
redis_subscriber = RedisSubscriber()


async def start_redis_subscriber() -> None:
    """Start the Redis subscriber (called on app startup)."""
    await redis_subscriber.start()


async def stop_redis_subscriber() -> None:
    """Stop the Redis subscriber (called on app shutdown)."""
    await redis_subscriber.stop()
