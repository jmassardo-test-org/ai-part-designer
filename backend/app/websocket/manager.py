"""
WebSocket connection manager.

Manages WebSocket connections for real-time updates.
Supports user-specific messaging, room subscriptions,
and broadcasting.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from fastapi import WebSocket

logger = logging.getLogger(__name__)


# =============================================================================
# Data Structures
# =============================================================================


@dataclass(eq=False)
class Connection:
    """Represents a single WebSocket connection."""

    websocket: WebSocket
    user_id: str
    connected_at: datetime = field(default_factory=datetime.utcnow)
    subscriptions: set[str] = field(default_factory=set)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __hash__(self) -> int:
        """Use object identity for hashing."""
        return id(self)

    def __eq__(self, other: object) -> bool:
        """Use object identity for equality."""
        return self is other

    async def send(self, message: dict) -> bool:
        """Send a message to this connection."""
        try:
            await self.websocket.send_json(message)
            return True
        except Exception as e:
            logger.debug(f"Failed to send to {self.user_id}: {e}")
            return False


# =============================================================================
# Connection Manager
# =============================================================================


class ConnectionManager:
    """
    Manages WebSocket connections for the application.

    Features:
    - Track connections by user ID (supports multiple connections per user)
    - Room/topic subscriptions for targeted messaging
    - Broadcast to all, to user, or to room
    - Graceful disconnection handling
    """

    def __init__(self):
        # user_id -> set of Connection objects
        self._connections: dict[str, set[Connection]] = {}
        # room_name -> set of Connection objects
        self._rooms: dict[str, set[Connection]] = {}
        # Connection tracking for metrics
        self._total_connections: int = 0
        self._peak_connections: int = 0

    @property
    def connection_count(self) -> int:
        """Get current number of active connections."""
        return sum(len(conns) for conns in self._connections.values())

    @property
    def user_count(self) -> int:
        """Get number of unique connected users."""
        return len(self._connections)

    async def connect(
        self,
        websocket: WebSocket,
        user_id: str,
        metadata: dict[str, Any] | None = None,
    ) -> Connection:
        """
        Accept a new WebSocket connection.

        Args:
            websocket: The WebSocket to accept
            user_id: User ID for this connection
            metadata: Optional metadata to store with connection

        Returns:
            Connection object for this connection
        """
        await websocket.accept()

        connection = Connection(
            websocket=websocket,
            user_id=user_id,
            metadata=metadata or {},
        )

        if user_id not in self._connections:
            self._connections[user_id] = set()
        self._connections[user_id].add(connection)

        self._total_connections += 1
        current_count = self.connection_count
        if current_count > self._peak_connections:
            self._peak_connections = current_count

        logger.info(
            f"WebSocket connected: user={user_id}, "
            f"total={current_count}, peak={self._peak_connections}"
        )

        return connection

    def disconnect(self, connection: Connection) -> None:
        """
        Remove a WebSocket connection.

        Args:
            connection: The connection to remove
        """
        user_id = connection.user_id

        # Remove from user connections
        if user_id in self._connections:
            self._connections[user_id].discard(connection)
            if not self._connections[user_id]:
                del self._connections[user_id]

        # Remove from all rooms
        for room_connections in self._rooms.values():
            room_connections.discard(connection)

        # Clean up empty rooms
        empty_rooms = [room for room, conns in self._rooms.items() if not conns]
        for room in empty_rooms:
            del self._rooms[room]

        logger.info(f"WebSocket disconnected: user={user_id}, remaining={self.connection_count}")

    async def send_to_user(
        self,
        user_id: str,
        message: dict,
    ) -> int:
        """
        Send a message to all connections for a user.

        Args:
            user_id: User ID to send to
            message: Message to send

        Returns:
            Number of connections that received the message
        """
        if user_id not in self._connections:
            return 0

        sent_count = 0
        failed_connections = []

        for connection in self._connections[user_id]:
            if await connection.send(message):
                sent_count += 1
            else:
                failed_connections.append(connection)

        # Clean up failed connections
        for connection in failed_connections:
            self.disconnect(connection)

        return sent_count

    async def send_to_room(
        self,
        room: str,
        message: dict,
        exclude_user: str | None = None,
    ) -> int:
        """
        Send a message to all connections in a room.

        Args:
            room: Room name
            message: Message to send
            exclude_user: Optional user ID to exclude

        Returns:
            Number of connections that received the message
        """
        if room not in self._rooms:
            return 0

        sent_count = 0
        failed_connections = []

        for connection in self._rooms[room]:
            if exclude_user and connection.user_id == exclude_user:
                continue

            if await connection.send(message):
                sent_count += 1
            else:
                failed_connections.append(connection)

        # Clean up failed connections
        for connection in failed_connections:
            self.disconnect(connection)

        return sent_count

    async def broadcast(
        self,
        message: dict,
        exclude_users: set[str] | None = None,
    ) -> int:
        """
        Broadcast a message to all connected users.

        Args:
            message: Message to send
            exclude_users: Set of user IDs to exclude

        Returns:
            Number of connections that received the message
        """
        exclude_users = exclude_users or set()
        sent_count = 0
        failed_connections = []

        for user_id, connections in self._connections.items():
            if user_id in exclude_users:
                continue

            for connection in connections:
                if await connection.send(message):
                    sent_count += 1
                else:
                    failed_connections.append(connection)

        # Clean up failed connections
        for connection in failed_connections:
            self.disconnect(connection)

        return sent_count

    def subscribe(self, connection: Connection, room: str) -> None:
        """
        Subscribe a connection to a room.

        Args:
            connection: The connection to subscribe
            room: Room name to subscribe to
        """
        if room not in self._rooms:
            self._rooms[room] = set()
        self._rooms[room].add(connection)
        connection.subscriptions.add(room)

        logger.debug(f"User {connection.user_id} subscribed to {room}")

    def unsubscribe(self, connection: Connection, room: str) -> None:
        """
        Unsubscribe a connection from a room.

        Args:
            connection: The connection to unsubscribe
            room: Room name to unsubscribe from
        """
        if room in self._rooms:
            self._rooms[room].discard(connection)
            if not self._rooms[room]:
                del self._rooms[room]

        connection.subscriptions.discard(room)
        logger.debug(f"User {connection.user_id} unsubscribed from {room}")

    def get_room_members(self, room: str) -> set[str]:
        """Get set of user IDs in a room."""
        if room not in self._rooms:
            return set()
        return {conn.user_id for conn in self._rooms[room]}

    def is_user_connected(self, user_id: str) -> bool:
        """Check if a user has any active connections."""
        return user_id in self._connections and len(self._connections[user_id]) > 0

    def get_stats(self) -> dict:
        """Get connection statistics."""
        return {
            "current_connections": self.connection_count,
            "current_users": self.user_count,
            "total_connections": self._total_connections,
            "peak_connections": self._peak_connections,
            "rooms": len(self._rooms),
        }


# =============================================================================
# Helper Functions for Celery Workers
# =============================================================================


def send_ws_message_sync(user_id: str, message: dict) -> None:
    """
    Send WebSocket message from synchronous context (e.g., Celery worker).

    This uses Redis pub/sub to communicate with the WebSocket process.
    The actual sending happens in the async WebSocket server.
    """
    from app.core.cache import redis_client

    try:
        # Publish to Redis channel for WebSocket server to pick up
        channel = f"ws:user:{user_id}"
        redis_client.client.publish(channel, json.dumps(message))
    except Exception as e:
        logger.warning(f"Failed to publish WS message: {e}")


async def send_job_progress(
    user_id: str,
    job_id: str,
    progress: int,
    status: str,
    message: str | None = None,
) -> None:
    """
    Send job progress update to user.

    Args:
        user_id: User ID
        job_id: Job ID
        progress: Progress percentage (0-100)
        status: Current status
        message: Optional status message
    """
    await manager.send_to_user(
        user_id,
        {
            "type": "job_progress",
            "job_id": job_id,
            "progress": progress,
            "status": status,
            "message": message,
            "timestamp": datetime.now(UTC).isoformat(),
        },
    )


async def send_job_complete(
    user_id: str,
    job_id: str,
    result: dict | None = None,
) -> None:
    """Send job completion notification."""
    await manager.send_to_user(
        user_id,
        {
            "type": "job_complete",
            "job_id": job_id,
            "result": result,
            "timestamp": datetime.now(UTC).isoformat(),
        },
    )


async def send_job_failed(
    user_id: str,
    job_id: str,
    error: str,
) -> None:
    """Send job failure notification."""
    await manager.send_to_user(
        user_id,
        {
            "type": "job_failed",
            "job_id": job_id,
            "error": error,
            "timestamp": datetime.now(UTC).isoformat(),
        },
    )


# =============================================================================
# Singleton Instance
# =============================================================================

manager = ConnectionManager()
