"""
Event tracking and analytics infrastructure.

Provides event collection, batching, and publishing for analytics
and business intelligence pipelines.
"""

import json
import logging
from datetime import datetime
from enum import StrEnum
from typing import Any, ClassVar
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from app.core.cache import redis_client

logger = logging.getLogger(__name__)


class EventCategory(StrEnum):
    """Event categories for analytics."""

    USER = "user"
    DESIGN = "design"
    TEMPLATE = "template"
    JOB = "job"
    BILLING = "billing"
    SYSTEM = "system"


class AnalyticsEvent(BaseModel):
    """
    Analytics event schema.

    All events follow this structure for consistent processing
    in downstream analytics pipelines.
    """

    # Event identification
    event_id: UUID = Field(default_factory=uuid4)
    event_name: str
    event_category: EventCategory

    # Timestamp
    timestamp: datetime = Field(default_factory=lambda: datetime.now(tz=datetime.UTC))

    # Context
    user_id: UUID | None = None
    session_id: str | None = None

    # Event properties
    properties: dict[str, Any] = Field(default_factory=dict)

    # Request context
    ip_address: str | None = None
    user_agent: str | None = None
    referrer: str | None = None

    # Environment
    environment: str = "production"
    app_version: str | None = None

    class Config:
        json_encoders: ClassVar[dict[type, Any]] = {
            UUID: str,
            datetime: lambda v: v.isoformat(),
        }


class EventTracker:
    """
    Analytics event tracker.

    Collects events and batches them for efficient processing.
    Events are stored in Redis and can be consumed by
    downstream analytics systems.
    """

    EVENTS_KEY = "analytics:events"
    EVENTS_BACKUP_KEY = "analytics:events:backup"
    BATCH_SIZE = 100
    MAX_QUEUE_SIZE = 10000

    def __init__(self) -> None:
        self._buffer: list[AnalyticsEvent] = []

    async def track(
        self,
        event_name: str,
        category: EventCategory,
        *,
        user_id: UUID | None = None,
        session_id: str | None = None,
        properties: dict[str, Any] | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> None:
        """
        Track an analytics event.

        Events are buffered and flushed to Redis in batches.
        """
        event = AnalyticsEvent(
            event_name=event_name,
            event_category=category,
            user_id=user_id,
            session_id=session_id,
            properties=properties or {},
            ip_address=ip_address,
            user_agent=user_agent,
        )

        self._buffer.append(event)

        # Auto-flush when buffer reaches batch size
        if len(self._buffer) >= self.BATCH_SIZE:
            await self.flush()

    async def flush(self) -> int:
        """
        Flush buffered events to Redis.

        Returns number of events flushed.
        """
        if not self._buffer:
            return 0

        events_to_flush = self._buffer[:]
        self._buffer.clear()

        try:
            # Serialize events
            serialized = [event.model_dump_json() for event in events_to_flush]

            # Push to Redis list
            await redis_client.client.lpush(self.EVENTS_KEY, *serialized)

            # Trim to prevent unbounded growth
            await redis_client.client.ltrim(self.EVENTS_KEY, 0, self.MAX_QUEUE_SIZE - 1)

            logger.debug(f"Flushed {len(serialized)} analytics events")
            return len(serialized)

        except Exception as e:
            logger.error(f"Failed to flush events: {e}")
            # Put events back in buffer for retry
            self._buffer = events_to_flush + self._buffer
            return 0

    async def get_pending_count(self) -> int:
        """Get count of pending events in queue."""
        return await redis_client.llen(self.EVENTS_KEY)

    async def consume_batch(self, batch_size: int = 100) -> list[dict[str, Any]]:
        """
        Consume a batch of events from the queue.

        Used by analytics workers to process events.
        """
        events = []

        for _ in range(batch_size):
            event_json = await redis_client.rpop(self.EVENTS_KEY)
            if not event_json:
                break

            try:
                events.append(json.loads(event_json))
            except json.JSONDecodeError:
                logger.warning(f"Invalid event JSON: {event_json}")

        return events

    # =========================================================================
    # Convenience Methods for Common Events
    # =========================================================================

    async def track_user_signup(
        self,
        user_id: UUID,
        *,
        signup_method: str = "email",
        referral_source: str | None = None,
        **kwargs: Any,
    ) -> None:
        """Track user signup event."""
        await self.track(
            "user_signup",
            EventCategory.USER,
            user_id=user_id,
            properties={
                "signup_method": signup_method,
                "referral_source": referral_source,
            },
            **kwargs,
        )

    async def track_user_login(
        self,
        user_id: UUID,
        *,
        login_method: str = "email",
        **kwargs: Any,
    ) -> None:
        """Track user login event."""
        await self.track(
            "user_login",
            EventCategory.USER,
            user_id=user_id,
            properties={"login_method": login_method},
            **kwargs,
        )

    async def track_design_created(
        self,
        user_id: UUID,
        design_id: UUID,
        *,
        source_type: str,
        template_id: UUID | None = None,
        **kwargs: Any,
    ) -> None:
        """Track design creation event."""
        await self.track(
            "design_created",
            EventCategory.DESIGN,
            user_id=user_id,
            properties={
                "design_id": str(design_id),
                "source_type": source_type,
                "template_id": str(template_id) if template_id else None,
            },
            **kwargs,
        )

    async def track_design_exported(
        self,
        user_id: UUID,
        design_id: UUID,
        *,
        export_format: str,
        **kwargs: Any,
    ) -> None:
        """Track design export event."""
        await self.track(
            "design_exported",
            EventCategory.DESIGN,
            user_id=user_id,
            properties={
                "design_id": str(design_id),
                "export_format": export_format,
            },
            **kwargs,
        )

    async def track_template_used(
        self,
        user_id: UUID,
        template_id: UUID,
        *,
        template_slug: str | None = None,
        **kwargs: Any,
    ) -> None:
        """Track template usage event."""
        await self.track(
            "template_used",
            EventCategory.TEMPLATE,
            user_id=user_id,
            properties={
                "template_id": str(template_id),
                "template_slug": template_slug,
            },
            **kwargs,
        )

    async def track_job_completed(
        self,
        user_id: UUID,
        job_id: UUID,
        *,
        job_type: str,
        duration_ms: int,
        success: bool,
        **kwargs: Any,
    ) -> None:
        """Track job completion event."""
        await self.track(
            "job_completed",
            EventCategory.JOB,
            user_id=user_id,
            properties={
                "job_id": str(job_id),
                "job_type": job_type,
                "duration_ms": duration_ms,
                "success": success,
            },
            **kwargs,
        )

    async def track_subscription_changed(
        self,
        user_id: UUID,
        *,
        from_tier: str | None,
        to_tier: str,
        change_type: str,  # upgrade, downgrade, new, cancel
        **kwargs: Any,
    ) -> None:
        """Track subscription change event."""
        await self.track(
            "subscription_changed",
            EventCategory.BILLING,
            user_id=user_id,
            properties={
                "from_tier": from_tier,
                "to_tier": to_tier,
                "change_type": change_type,
            },
            **kwargs,
        )


# Global event tracker instance
event_tracker = EventTracker()


async def get_event_tracker() -> EventTracker:
    """Dependency for getting event tracker."""
    return event_tracker
