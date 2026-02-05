"""
Worker utilities for WebSocket integration.

Provides helper functions for Celery workers to send
real-time updates via WebSocket.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)


def get_redis_client():
    """Get Redis client for pub/sub."""
    try:
        from app.core.cache import redis_client

        return redis_client.client
    except Exception as e:
        logger.warning(f"Failed to get Redis client: {e}")
        return None


def publish_ws_message(user_id: str, message: dict) -> bool:
    """
    Publish a WebSocket message via Redis for async delivery.

    The WebSocket server subscribes to these channels and
    forwards messages to connected clients.

    Args:
        user_id: Target user ID
        message: Message to send

    Returns:
        True if message was published successfully
    """
    redis = get_redis_client()
    if not redis:
        return False

    try:
        channel = f"ws:user:{user_id}"
        # Add timestamp if not present
        if "timestamp" not in message:
            message["timestamp"] = datetime.now(tz=datetime.UTC).isoformat()

        redis.publish(channel, json.dumps(message))
        return True
    except Exception as e:
        logger.warning(f"Failed to publish WS message to {user_id}: {e}")
        return False


def publish_room_message(room: str, message: dict) -> bool:
    """
    Publish a message to a WebSocket room via Redis.

    Args:
        room: Room name (e.g., "project:123")
        message: Message to send

    Returns:
        True if message was published successfully
    """
    redis = get_redis_client()
    if not redis:
        return False

    try:
        channel = f"ws:room:{room}"
        if "timestamp" not in message:
            message["timestamp"] = datetime.now(tz=datetime.UTC).isoformat()

        redis.publish(channel, json.dumps(message))
        return True
    except Exception as e:
        logger.warning(f"Failed to publish WS room message to {room}: {e}")
        return False


def send_job_progress(
    user_id: str,
    job_id: str,
    progress: int,
    status: str = "running",
    message: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> None:
    """
    Send job progress update to user.

    Args:
        user_id: User ID
        job_id: Job ID
        progress: Progress percentage (0-100)
        status: Current status (running, etc.)
        message: Human-readable status message
        metadata: Additional metadata
    """
    payload = {
        "type": "job_progress",
        "job_id": job_id,
        "progress": progress,
        "status": status,
        "message": message,
    }
    if metadata:
        payload["metadata"] = metadata

    publish_ws_message(user_id, payload)


def send_job_complete(
    user_id: str,
    job_id: str,
    result: dict[str, Any] | None = None,
) -> None:
    """
    Send job completion notification to user.

    Args:
        user_id: User ID
        job_id: Job ID
        result: Job result data
    """
    publish_ws_message(
        user_id,
        {
            "type": "job_complete",
            "job_id": job_id,
            "status": "completed",
            "progress": 100,
            "result": result,
        },
    )


def send_job_failed(
    user_id: str,
    job_id: str,
    error: str,
    error_type: str | None = None,
) -> None:
    """
    Send job failure notification to user.

    Args:
        user_id: User ID
        job_id: Job ID
        error: Error message
        error_type: Error type/class name
    """
    publish_ws_message(
        user_id,
        {
            "type": "job_failed",
            "job_id": job_id,
            "status": "failed",
            "error": error,
            "error_type": error_type,
        },
    )


def send_job_started(user_id: str, job_id: str, job_type: str) -> None:
    """
    Send job started notification to user.

    Args:
        user_id: User ID
        job_id: Job ID
        job_type: Type of job (e.g., "cad_generation")
    """
    publish_ws_message(
        user_id,
        {
            "type": "job_started",
            "job_id": job_id,
            "job_type": job_type,
            "status": "running",
            "progress": 0,
        },
    )


def send_project_update(
    project_id: str,
    event_type: str,
    data: dict[str, Any],
    exclude_user: str | None = None,
) -> None:
    """
    Send project update to all users subscribed to project room.

    Args:
        project_id: Project ID
        event_type: Type of event (e.g., "design_updated")
        data: Event data
        exclude_user: User ID to exclude (e.g., the user who made the change)
    """
    message = {
        "type": "project_update",
        "event": event_type,
        "project_id": project_id,
        "data": data,
    }
    if exclude_user:
        message["_exclude_user"] = exclude_user

    publish_room_message(f"project:{project_id}", message)


def send_notification(
    user_id: str,
    title: str,
    message: str,
    notification_type: str = "info",
    link: str | None = None,
) -> None:
    """
    Send a push notification to user.

    Args:
        user_id: User ID
        title: Notification title
        message: Notification message
        notification_type: Type (info, success, warning, error)
        link: Optional link to navigate to
    """
    payload = {
        "type": "notification",
        "notification_type": notification_type,
        "title": title,
        "message": message,
    }
    if link:
        payload["link"] = link

    publish_ws_message(user_id, payload)
