"""
Conversation Message Moderation Service.

Thin service layer that integrates content moderation with abuse detection
for the conversational Q&A endpoint. Ensures that prompt injection, off-topic
abuse, weapon content, and other violations are caught and recorded before
messages reach the AI reasoning engine.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.abuse_detection import (
    AbuseDecision,
    AbuseDetectionService,
    ViolationEvent,
    ViolationType,
)
from app.services.content_moderation import (
    ModerationResult,
    ProhibitedCategory,
    content_moderation,
)

logger = logging.getLogger(__name__)

# =============================================================================
# Category → ViolationType Mapping
# =============================================================================

CATEGORY_TO_VIOLATION: dict[ProhibitedCategory, ViolationType] = {
    ProhibitedCategory.FIREARM: ViolationType.WEAPON_CONTENT,
    ProhibitedCategory.FIREARM_COMPONENT: ViolationType.WEAPON_CONTENT,
    ProhibitedCategory.WEAPON: ViolationType.WEAPON_CONTENT,
    ProhibitedCategory.EXPLOSIVE: ViolationType.WEAPON_CONTENT,
    ProhibitedCategory.ILLEGAL_DRUG: ViolationType.ILLEGAL_CONTENT,
    ProhibitedCategory.CONTROLLED_SUBSTANCE: ViolationType.ILLEGAL_CONTENT,
    ProhibitedCategory.PROMPT_INJECTION: ViolationType.PROMPT_INJECTION,
    ProhibitedCategory.API_ABUSE: ViolationType.API_PROXY_ABUSE,
    ProhibitedCategory.OFF_TOPIC: ViolationType.OFF_TOPIC_ABUSE,
}

DEFAULT_VIOLATION_TYPE = ViolationType.TOS_VIOLATION


def map_category_to_violation(category: ProhibitedCategory) -> ViolationType:
    """Map a content moderation ProhibitedCategory to an abuse ViolationType.

    Args:
        category: The prohibited content category from moderation.

    Returns:
        The corresponding ViolationType for abuse tracking.
    """
    return CATEGORY_TO_VIOLATION.get(category, DEFAULT_VIOLATION_TYPE)


# =============================================================================
# Result Dataclass
# =============================================================================


@dataclass
class MessageModerationResult:
    """Result of moderating a conversation message.

    Attributes:
        allowed: Whether the message is allowed through.
        rejection_message: User-facing rejection text, if rejected.
        abuse_decision: The abuse detection decision, if a violation was recorded.
        moderation_result: The raw ModerationResult from content moderation.
    """

    allowed: bool
    rejection_message: str | None
    abuse_decision: AbuseDecision | None
    moderation_result: ModerationResult


# =============================================================================
# Public API
# =============================================================================


async def moderate_conversation_message(
    message: str,
    user_id: UUID,
    ip_address: str,
    db: AsyncSession,
) -> MessageModerationResult:
    """Moderate a user message in a conversation before AI processing.

    Runs fast pattern-based content moderation (no AI call) and, if the
    message is flagged, records the violation through the abuse detection
    service for escalating enforcement.

    Args:
        message: The raw user message text.
        user_id: The authenticated user's ID.
        ip_address: The request source IP address.
        db: Async database session for abuse recording.

    Returns:
        MessageModerationResult indicating whether the message is allowed
        and, if not, the rejection details.
    """
    # Fast pattern-only moderation (use_ai=False for low latency)
    moderation_result: ModerationResult = await content_moderation.check_prompt(
        prompt=message,
        _user_id=user_id,
        use_ai=False,
    )

    # If the message passes moderation, allow it through immediately
    if not moderation_result.is_rejected:
        return MessageModerationResult(
            allowed=True,
            rejection_message=None,
            abuse_decision=None,
            moderation_result=moderation_result,
        )

    # --- Message was rejected — record the violation ---

    # Determine the primary violation type from the highest-severity flag
    violation_type = _resolve_violation_type(moderation_result)
    severity = _resolve_severity(moderation_result)

    violation = ViolationEvent(
        violation_type=violation_type,
        severity=severity,
        description=f"Conversation message flagged: {violation_type.value}",
        evidence={
            "message_preview": message[:200],
            "flags": [
                {
                    "category": f.category.value,
                    "severity": f.severity,
                    "pattern_matched": f.pattern_matched,
                    "confidence": f.confidence,
                }
                for f in moderation_result.flags
            ],
            "decision": moderation_result.decision.value,
            "source": "conversation_message",
        },
        user_id=user_id,
        ip_address=ip_address,
    )

    abuse_service = AbuseDetectionService(db)
    abuse_decision = await abuse_service.record_violation(violation)

    rejection_message = content_moderation.get_rejection_message(moderation_result)

    logger.warning(
        "Conversation message moderated",
        extra={
            "user_id": str(user_id),
            "ip_address": ip_address,
            "violation_type": violation_type.value,
            "severity": severity,
            "abuse_action": abuse_decision.action,
            "decision": moderation_result.decision.value,
            "flag_count": len(moderation_result.flags),
        },
    )

    return MessageModerationResult(
        allowed=False,
        rejection_message=rejection_message,
        abuse_decision=abuse_decision,
        moderation_result=moderation_result,
    )


# =============================================================================
# Internal Helpers
# =============================================================================


def _resolve_violation_type(result: ModerationResult) -> ViolationType:
    """Pick the most severe violation type from moderation flags.

    Args:
        result: The moderation result containing flags.

    Returns:
        The most relevant ViolationType.
    """
    severity_order = ["critical", "high", "medium", "low"]

    for sev in severity_order:
        for flag in result.flags:
            if flag.severity == sev:
                return map_category_to_violation(flag.category)

    return DEFAULT_VIOLATION_TYPE


def _resolve_severity(result: ModerationResult) -> str:
    """Determine the overall severity string from moderation flags.

    Args:
        result: The moderation result containing flags.

    Returns:
        The highest severity level found, or "medium" as default.
    """
    severity_order = ["critical", "high", "medium", "low"]

    for sev in severity_order:
        if any(f.severity == sev for f in result.flags):
            return sev

    return "medium"
