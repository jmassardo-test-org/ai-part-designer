"""
API routes for template ratings and feedback.

Handles star ratings and thumbs up/down feedback for templates.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.rating import (
    TemplateFeedbackCreate,
    TemplateFeedbackResponse,
    TemplateFeedbackSummary,
    TemplateRatingCreate,
    TemplateRatingResponse,
    TemplateRatingSummary,
)
from app.services.rating_service import FeedbackService, RatingService

router = APIRouter(prefix="/templates/{template_id}", tags=["ratings"])


# =============================================================================
# Template Ratings
# =============================================================================


@router.post(
    "/ratings",
    response_model=TemplateRatingResponse,
    status_code=status.HTTP_201_CREATED,
)
async def rate_template(
    template_id: UUID,
    data: TemplateRatingCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TemplateRatingResponse:
    """Create or update a rating for a template.

    Users can rate templates 1-5 stars with an optional review.
    Each user can only have one rating per template.
    """
    service = RatingService(db)
    rating = await service.rate_template(template_id, current_user.id, data)
    await db.commit()

    return TemplateRatingResponse.model_validate(rating)


@router.get(
    "/ratings",
    response_model=list[TemplateRatingResponse],
)
async def get_template_ratings(
    template_id: UUID,
    limit: int = 20,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
) -> list[TemplateRatingResponse]:
    """Get ratings for a template with pagination."""
    service = RatingService(db)
    ratings, _ = await service.get_template_ratings(template_id, limit, offset)

    return [TemplateRatingResponse.model_validate(r) for r in ratings]


@router.get(
    "/ratings/summary",
    response_model=TemplateRatingSummary,
)
async def get_rating_summary(
    template_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> TemplateRatingSummary:
    """Get rating summary for a template.

    Returns average rating, total count, and distribution.
    """
    service = RatingService(db)
    return await service.get_rating_summary(template_id)


@router.get(
    "/ratings/me",
    response_model=TemplateRatingResponse | None,
)
async def get_my_rating(
    template_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TemplateRatingResponse | None:
    """Get current user's rating for a template."""
    service = RatingService(db)
    rating = await service.get_user_rating(template_id, current_user.id)

    if not rating:
        return None

    return TemplateRatingResponse.model_validate(rating)


@router.delete(
    "/ratings",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_my_rating(
    template_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    """Delete current user's rating for a template."""
    service = RatingService(db)
    deleted = await service.delete_rating(template_id, current_user.id)

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Rating not found",
        )

    await db.commit()


# =============================================================================
# Template Feedback (Thumbs Up/Down)
# =============================================================================


@router.post(
    "/feedback",
    response_model=TemplateFeedbackResponse,
    status_code=status.HTTP_201_CREATED,
)
async def set_template_feedback(
    template_id: UUID,
    data: TemplateFeedbackCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TemplateFeedbackResponse:
    """Set thumbs up/down feedback for a template.

    Each user can only have one feedback per template.
    Calling again with different value updates the feedback.
    """
    service = FeedbackService(db)
    feedback = await service.set_feedback(template_id, current_user.id, data)
    await db.commit()

    return TemplateFeedbackResponse.model_validate(feedback)


@router.get(
    "/feedback",
    response_model=TemplateFeedbackSummary,
)
async def get_feedback_summary(
    template_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User | None = Depends(get_current_user),
) -> TemplateFeedbackSummary:
    """Get feedback summary for a template.

    Includes current user's feedback if authenticated.
    """
    service = FeedbackService(db)
    user_id = current_user.id if current_user else None
    return await service.get_feedback_summary(template_id, user_id)


@router.delete(
    "/feedback",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def remove_feedback(
    template_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    """Remove current user's feedback for a template."""
    service = FeedbackService(db)
    removed = await service.remove_feedback(template_id, current_user.id)

    if not removed:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Feedback not found",
        )

    await db.commit()
