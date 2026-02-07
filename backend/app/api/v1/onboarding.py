"""
Onboarding API endpoints.

Provides endpoints for tracking and managing user onboarding progress.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.core.auth import get_current_user
from app.core.database import get_db
from app.models import User

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/onboarding", tags=["onboarding"])


# =============================================================================
# Constants
# =============================================================================

# Total number of onboarding steps
TOTAL_ONBOARDING_STEPS = 5

# Onboarding step descriptions
ONBOARDING_STEPS = {
    0: "Not started",
    1: "Welcome & profile setup",
    2: "First project creation",
    3: "Explore templates",
    4: "First generation",
    5: "Review & complete",
}


# =============================================================================
# Request/Response Models
# =============================================================================


class OnboardingStatusResponse(BaseModel):
    """Onboarding status response."""

    completed: bool
    completed_at: datetime | None = None
    current_step: int
    total_steps: int
    step_name: str


class OnboardingStepRequest(BaseModel):
    """Request to update onboarding step."""

    step_data: dict[str, Any] = Field(
        default_factory=dict, description="Optional data about the completed step"
    )


class OnboardingStepResponse(BaseModel):
    """Response after updating onboarding step."""

    current_step: int
    total_steps: int
    step_name: str
    completed: bool
    message: str


class MessageResponse(BaseModel):
    """Simple message response."""

    message: str


# =============================================================================
# Endpoints
# =============================================================================


@router.get(
    "/status",
    response_model=OnboardingStatusResponse,
    summary="Get onboarding status",
    description="Get current user's onboarding progress.",
)
async def get_onboarding_status(
    current_user: User = Depends(get_current_user),
) -> OnboardingStatusResponse:
    """Get the current user's onboarding status."""
    step_name = ONBOARDING_STEPS.get(current_user.onboarding_step, "Unknown")

    return OnboardingStatusResponse(
        completed=current_user.onboarding_completed,
        completed_at=current_user.onboarding_completed_at,
        current_step=current_user.onboarding_step,
        total_steps=TOTAL_ONBOARDING_STEPS,
        step_name=step_name,
    )


@router.post(
    "/step/{step}",
    response_model=OnboardingStepResponse,
    summary="Complete onboarding step",
    description="Mark an onboarding step as complete.",
)
async def complete_onboarding_step(
    step: int,
    request: OnboardingStepRequest | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> OnboardingStepResponse:
    """
    Complete an onboarding step.

    Steps can only advance forward (can't go back to lower steps).
    Completing step 5 marks onboarding as complete.
    """
    if step < 1 or step > TOTAL_ONBOARDING_STEPS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid step. Must be between 1 and {TOTAL_ONBOARDING_STEPS}",
        )

    # Only advance if moving forward
    if step > current_user.onboarding_step:
        current_user.onboarding_step = step

        # Check if onboarding is complete
        if step >= TOTAL_ONBOARDING_STEPS:
            current_user.onboarding_completed = True
            current_user.onboarding_completed_at = datetime.now(tz=UTC)

        # Store step data if provided
        if request and request.step_data:
            onboarding_data = current_user.extra_data.get("onboarding", {})
            onboarding_data[f"step_{step}"] = request.step_data
            current_user.extra_data = {
                **current_user.extra_data,
                "onboarding": onboarding_data,
            }

        await db.commit()
        await db.refresh(current_user)

    step_name = ONBOARDING_STEPS.get(current_user.onboarding_step, "Unknown")

    return OnboardingStepResponse(
        current_step=current_user.onboarding_step,
        total_steps=TOTAL_ONBOARDING_STEPS,
        step_name=step_name,
        completed=current_user.onboarding_completed,
        message=(
            "Onboarding complete! Welcome to AI Part Designer."
            if current_user.onboarding_completed
            else f"Step {step} completed"
        ),
    )


@router.post(
    "/skip",
    response_model=MessageResponse,
    summary="Skip onboarding",
    description="Skip the onboarding flow entirely.",
)
async def skip_onboarding(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MessageResponse:
    """Skip the onboarding flow."""
    if current_user.onboarding_completed:
        return MessageResponse(message="Onboarding already completed")

    current_user.onboarding_completed = True
    current_user.onboarding_completed_at = datetime.now(tz=UTC)
    current_user.onboarding_step = TOTAL_ONBOARDING_STEPS

    # Mark as skipped in extra_data
    current_user.extra_data = {
        **current_user.extra_data,
        "onboarding": {
            **current_user.extra_data.get("onboarding", {}),
            "skipped": True,
            "skipped_at": datetime.now(tz=UTC).isoformat(),
        },
    }

    await db.commit()

    return MessageResponse(message="Onboarding skipped")


@router.post(
    "/reset",
    response_model=MessageResponse,
    summary="Reset onboarding",
    description="Reset onboarding progress (for testing).",
)
async def reset_onboarding(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MessageResponse:
    """Reset onboarding progress (useful for testing)."""
    current_user.onboarding_completed = False
    current_user.onboarding_completed_at = None
    current_user.onboarding_step = 0

    # Clear onboarding data
    extra_data = current_user.extra_data.copy()
    extra_data.pop("onboarding", None)
    current_user.extra_data = extra_data

    await db.commit()

    return MessageResponse(message="Onboarding reset")


@router.get(
    "/steps",
    response_model=dict,
    summary="List onboarding steps",
    description="Get list of all onboarding steps and their names.",
)
async def list_onboarding_steps() -> dict[str, Any]:
    """Get list of all onboarding steps."""
    return {
        "total_steps": TOTAL_ONBOARDING_STEPS,
        "steps": [
            {"step": step, "name": name} for step, name in ONBOARDING_STEPS.items() if step > 0
        ],
    }


# =============================================================================
# Admin Metrics Endpoints
# =============================================================================


class OnboardingMetricsResponse(BaseModel):
    """Onboarding metrics response."""

    total_users: int
    completed_count: int
    skipped_count: int
    in_progress_count: int
    not_started_count: int
    completion_rate: float
    skip_rate: float
    step_distribution: dict[str, int]
    avg_completion_time_hours: float | None


@router.get(
    "/metrics",
    response_model=OnboardingMetricsResponse,
    summary="Get onboarding metrics",
    description="Get aggregated onboarding metrics (admin only).",
)
async def get_onboarding_metrics(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> OnboardingMetricsResponse:
    """
    Get aggregated onboarding metrics.

    Returns:
        - Total users count
        - Completion and skip rates
        - Step distribution (users at each step)
        - Average completion time
    """
    # Check if user has admin role
    if current_user.role not in ("admin", "superadmin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )

    from sqlalchemy import func, select

    # Get total user count
    total_result = await db.execute(select(func.count(User.id)))
    total_users = total_result.scalar() or 0

    # Get completed count
    completed_result = await db.execute(
        select(func.count(User.id)).where(User.onboarding_completed == True)  # noqa: E712
    )
    completed_count = completed_result.scalar() or 0

    # Get skipped count (completed but with skipped flag in extra_data)
    # Note: This is a simplified query - in production you'd want to use JSONB operators
    skipped_result = await db.execute(
        select(func.count(User.id)).where(
            User.onboarding_completed == True,  # noqa: E712
            User.extra_data["onboarding"]["skipped"].astext == "true",
        )
    )
    skipped_count = skipped_result.scalar() or 0

    # Calculate in-progress and not started
    not_started_result = await db.execute(
        select(func.count(User.id)).where(
            User.onboarding_completed == False,  # noqa: E712
            User.onboarding_step == 0,
        )
    )
    not_started_count = not_started_result.scalar() or 0

    in_progress_count = total_users - completed_count - not_started_count

    # Get step distribution
    step_distribution = {}
    for step in range(TOTAL_ONBOARDING_STEPS + 1):
        step_result = await db.execute(
            select(func.count(User.id)).where(User.onboarding_step == step)
        )
        step_distribution[str(step)] = step_result.scalar() or 0

    # Calculate average completion time
    avg_time_result = await db.execute(
        select(
            func.avg(
                func.extract(
                    "epoch",
                    User.onboarding_completed_at - User.created_at,
                )
                / 3600
            )
        ).where(
            User.onboarding_completed == True,  # noqa: E712
            User.onboarding_completed_at.isnot(None),
        )
    )
    avg_completion_time = avg_time_result.scalar()

    # Calculate rates
    completion_rate = (completed_count / total_users * 100) if total_users > 0 else 0
    skip_rate = (skipped_count / completed_count * 100) if completed_count > 0 else 0

    return OnboardingMetricsResponse(
        total_users=total_users,
        completed_count=completed_count,
        skipped_count=skipped_count,
        in_progress_count=in_progress_count,
        not_started_count=not_started_count,
        completion_rate=round(completion_rate, 2),
        skip_rate=round(skip_rate, 2),
        step_distribution=step_distribution,
        avg_completion_time_hours=round(avg_completion_time, 2) if avg_completion_time else None,
    )
