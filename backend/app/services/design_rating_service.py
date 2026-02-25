"""Design rating service for marketplace rating operations.

Provides business logic for creating, updating, and querying design ratings.
"""

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.design import Design
from app.models.rating import DesignRating
from app.models.user import User
from app.schemas.rating import (
    DesignRatingCreate,
    DesignRatingResponse,
    DesignRatingSummary,
    DesignRatingWithUser,
)


class DesignRatingService:
    """Service for managing design ratings.

    Handles creation, updates, deletion, and aggregation of design ratings.
    Maintains denormalized avg_rating and total_ratings on the Design model.
    """

    def __init__(self, db: AsyncSession) -> None:
        """Initialize the service.

        Args:
            db: Async database session.
        """
        self.db = db

    async def create_or_update_rating(
        self,
        design_id: UUID,
        user: User,
        data: DesignRatingCreate,
    ) -> DesignRatingResponse:
        """Create or update a rating for a design.

        If the user has already rated this design, updates the existing rating.
        Recalculates denormalized averages on the design.

        Args:
            design_id: The design to rate.
            user: The authenticated user.
            data: Rating data (1-5 stars + optional review).

        Returns:
            The created or updated rating.

        Raises:
            ValueError: If design not found or user is the design owner.
        """
        # Validate design exists and is public
        design = await self.db.get(Design, design_id)
        if not design or not design.is_public or design.deleted_at is not None:
            raise ValueError("Design not found or not public")

        # Prevent rating own design
        if design.user_id == user.id:
            raise ValueError("Cannot rate your own design")

        # Check existing rating
        stmt = select(DesignRating).where(
            DesignRating.design_id == design_id,
            DesignRating.user_id == user.id,
        )
        result = await self.db.execute(stmt)
        existing = result.scalar_one_or_none()

        if existing:
            existing.rating = data.rating
            existing.review = data.review
            existing.updated_at = datetime.now(timezone.utc)
            rating_obj = existing
        else:
            rating_obj = DesignRating(
                design_id=design_id,
                user_id=user.id,
                rating=data.rating,
                review=data.review,
            )
            self.db.add(rating_obj)

        await self.db.flush()
        await self._update_design_aggregates(design_id)
        await self.db.commit()
        await self.db.refresh(rating_obj)

        return DesignRatingResponse.model_validate(rating_obj)

    async def delete_rating(self, design_id: UUID, user: User) -> None:
        """Delete a user's rating for a design.

        Args:
            design_id: The design to unrate.
            user: The authenticated user.

        Raises:
            ValueError: If no rating found.
        """
        stmt = delete(DesignRating).where(
            DesignRating.design_id == design_id,
            DesignRating.user_id == user.id,
        )
        result = await self.db.execute(stmt)
        if result.rowcount == 0:
            raise ValueError("Rating not found")

        await self._update_design_aggregates(design_id)
        await self.db.commit()

    async def get_user_rating(
        self, design_id: UUID, user_id: UUID
    ) -> DesignRatingResponse | None:
        """Get a specific user's rating for a design.

        Args:
            design_id: The design ID.
            user_id: The user ID.

        Returns:
            The rating if found, None otherwise.
        """
        stmt = select(DesignRating).where(
            DesignRating.design_id == design_id,
            DesignRating.user_id == user_id,
        )
        result = await self.db.execute(stmt)
        rating = result.scalar_one_or_none()
        if not rating:
            return None
        return DesignRatingResponse.model_validate(rating)

    async def get_design_ratings(
        self,
        design_id: UUID,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[DesignRatingWithUser], int]:
        """Get paginated ratings for a design with user info.

        Args:
            design_id: The design to get ratings for.
            page: Page number (1-based).
            page_size: Items per page.

        Returns:
            Tuple of (ratings list, total count).
        """
        # Count
        count_stmt = (
            select(func.count())
            .select_from(DesignRating)
            .where(DesignRating.design_id == design_id)
        )
        total = (await self.db.execute(count_stmt)).scalar() or 0

        # Fetch with user name
        stmt = (
            select(DesignRating, User.display_name)
            .join(User, DesignRating.user_id == User.id)
            .where(DesignRating.design_id == design_id)
            .order_by(DesignRating.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await self.db.execute(stmt)
        rows = result.all()

        ratings = []
        for rating, user_name in rows:
            rating_dict = {
                "id": rating.id,
                "design_id": rating.design_id,
                "user_id": rating.user_id,
                "rating": rating.rating,
                "review": rating.review,
                "created_at": rating.created_at,
                "updated_at": rating.updated_at,
                "user_name": user_name or "Anonymous",
            }
            ratings.append(DesignRatingWithUser(**rating_dict))

        return ratings, total

    async def get_rating_summary(self, design_id: UUID) -> DesignRatingSummary:
        """Get aggregate rating summary for a design.

        Args:
            design_id: The design ID.

        Returns:
            Rating summary with average, count, and distribution.
        """
        # Average and count
        stmt = select(
            func.avg(DesignRating.rating),
            func.count(DesignRating.id),
        ).where(DesignRating.design_id == design_id)
        result = await self.db.execute(stmt)
        row = result.one()
        avg_rating = float(row[0]) if row[0] else 0.0
        total = row[1] or 0

        # Distribution
        dist_stmt = (
            select(DesignRating.rating, func.count())
            .where(DesignRating.design_id == design_id)
            .group_by(DesignRating.rating)
        )
        dist_result = await self.db.execute(dist_stmt)
        distribution = {i: 0 for i in range(1, 6)}
        for rating_val, count in dist_result.all():
            distribution[rating_val] = count

        return DesignRatingSummary(
            design_id=design_id,
            average_rating=round(avg_rating, 2),
            total_ratings=total,
            rating_distribution=distribution,
        )

    async def _update_design_aggregates(self, design_id: UUID) -> None:
        """Recalculate and update denormalized rating aggregates on design.

        Args:
            design_id: The design to update.
        """
        stmt = select(
            func.avg(DesignRating.rating),
            func.count(DesignRating.id),
        ).where(DesignRating.design_id == design_id)
        result = await self.db.execute(stmt)
        row = result.one()
        avg = round(float(row[0]), 2) if row[0] else None
        total = row[1] or 0

        await self.db.execute(
            update(Design)
            .where(Design.id == design_id)
            .values(avg_rating=avg, total_ratings=total)
        )
