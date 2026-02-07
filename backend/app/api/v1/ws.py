"""
WebSocket API endpoint.

Provides WebSocket connection for real-time updates.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

from app.core.security import decode_token
from app.websocket.manager import manager

logger = logging.getLogger(__name__)

router = APIRouter()


# =============================================================================
# WebSocket Endpoint
# =============================================================================


@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    token: str = Query(..., description="JWT access token"),
) -> None:
    """
    WebSocket endpoint for real-time updates.

    Authentication is done via query parameter token.

    Message Types (client -> server):
    - ping: Keep-alive heartbeat
    - subscribe: Subscribe to a room/topic
    - unsubscribe: Unsubscribe from a room/topic

    Message Types (server -> client):
    - pong: Response to ping
    - job_progress: Job progress update
    - job_complete: Job completion notification
    - job_failed: Job failure notification
    - notification: User notification
    """
    # Authenticate
    try:
        payload = decode_token(token)
        user_id = payload.get("sub")
        if not user_id:
            await websocket.close(code=4001, reason="Invalid token")
            return
    except Exception as e:
        logger.warning(f"WebSocket auth failed: {e}")
        await websocket.close(code=4001, reason="Authentication failed")
        return

    # Connect
    connection = await manager.connect(
        websocket,
        user_id,
        metadata={
            "token_exp": payload.get("exp"),
            "user_agent": websocket.headers.get("user-agent"),
        },
    )

    # Send welcome message
    await connection.send(
        {
            "type": "connected",
            "user_id": user_id,
            "timestamp": datetime.now(tz=UTC).isoformat(),
        }
    )

    try:
        while True:
            # Receive message
            data = await websocket.receive_json()
            message_type = data.get("type")

            if message_type == "ping":
                # Heartbeat
                await connection.send({"type": "pong"})

            elif message_type == "subscribe":
                # Subscribe to a room
                room = data.get("room")
                if room:
                    manager.subscribe(connection, room)
                    await connection.send(
                        {
                            "type": "subscribed",
                            "room": room,
                        }
                    )

            elif message_type == "unsubscribe":
                # Unsubscribe from a room
                room = data.get("room")
                if room:
                    manager.unsubscribe(connection, room)
                    await connection.send(
                        {
                            "type": "unsubscribed",
                            "room": room,
                        }
                    )

            elif message_type == "subscribe_job":
                # Subscribe to a specific job's updates
                job_id = data.get("job_id")
                if job_id:
                    room = f"job:{job_id}"
                    manager.subscribe(connection, room)
                    await connection.send(
                        {
                            "type": "subscribed",
                            "room": room,
                            "job_id": job_id,
                        }
                    )

            elif message_type == "get_stats":
                # Get connection stats (for debugging)
                stats = manager.get_stats()
                await connection.send(
                    {
                        "type": "stats",
                        "data": stats,
                    }
                )

            else:
                # Unknown message type
                await connection.send(
                    {
                        "type": "error",
                        "message": f"Unknown message type: {message_type}",
                    }
                )

    except WebSocketDisconnect:
        manager.disconnect(connection)
    except Exception:
        logger.exception(f"WebSocket error for user {user_id}")
        manager.disconnect(connection)


# =============================================================================
# HTTP Endpoints for WebSocket Status
# =============================================================================


@router.get("/ws/stats")
async def websocket_stats() -> dict[str, Any]:
    """Get WebSocket connection statistics."""
    return manager.get_stats()


@router.get("/ws/health")
async def websocket_health() -> dict[str, Any]:
    """Health check for WebSocket server."""
    return {
        "status": "healthy",
        "connections": manager.connection_count,
        "users": manager.user_count,
    }
