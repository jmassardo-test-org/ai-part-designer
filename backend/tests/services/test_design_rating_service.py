"""
Tests for DesignRatingService.

Tests rating creation, updates, deletion, pagination, and aggregate calculations
for marketplace designs.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import uuid4

import pytest
import pytest_asyncio
from tests.factories import DesignFactory, ProjectFactory, UserFactory

from app.schemas.rating import DesignRatingCreate
from app.services.design_rating_service import DesignRatingService

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.models.design import Design
    from app.models.user import User


# =============================================================================
# Fixtures
# =============================================================================


@pytest_asyncio.fixture
async def owner(db_session: AsyncSession) -> User:
    """Create a design owner user."""
    return await UserFactory.create(db_session, email="owner@test.com", display_name="Owner")


@pytest_asyncio.fixture
async def rater(db_session: AsyncSession) -> User:
    """Create a user who rates designs."""
    return await UserFactory.create(db_session, email="rater@test.com", display_name="Rater")


@pytest_asyncio.fixture
async def rater_2(db_session: AsyncSession) -> User:
    """Create a second rater for multi-rating tests."""
    return await UserFactory.create(db_session, email="rater2@test.com", display_name="Rater 2")


@pytest_asyncio.fixture
async def public_design(db_session: AsyncSession, owner: User) -> Design:
    """Create a public marketplace design."""
    project = await ProjectFactory.create(db_session, user=owner)
    return await DesignFactory.create(
        db_session,
        project=project,
        user=owner,
        is_public=True,
        name="Public Design",
    )


@pytest_asyncio.fixture
async def private_design(db_session: AsyncSession, owner: User) -> Design:
    """Create a private (non-published) design."""
    project = await ProjectFactory.create(db_session, user=owner)
    return await DesignFactory.create(
        db_session,
        project=project,
        user=owner,
        is_public=False,
        name="Private Design",
    )


@pytest_asyncio.fixture
def rating_service(db_session: AsyncSession) -> DesignRatingService:
    """Create a DesignRatingService instance."""
    return DesignRatingService(db_session)


# =============================================================================
# create_or_update_rating Tests
# =============================================================================


class TestCreateOrUpdateRating:
    """Tests for the create_or_update_rating method."""

    @pytest.mark.asyncio
    async def test_create_rating_with_valid_data_returns_rating(
        self,
        rating_service: DesignRatingService,
        public_design: Design,
        rater: User,
    ) -> None:
        """Creating a rating with valid data returns a properly formed response."""
        data = DesignRatingCreate(rating=5, review="Excellent design!")

        result = await rating_service.create_or_update_rating(
            design_id=public_design.id, user=rater, data=data
        )

        assert result.design_id == public_design.id
        assert result.user_id == rater.id
        assert result.rating == 5
        assert result.review == "Excellent design!"
        assert result.id is not None
        assert result.created_at is not None

    @pytest.mark.asyncio
    async def test_create_rating_without_review_returns_rating(
        self,
        rating_service: DesignRatingService,
        public_design: Design,
        rater: User,
    ) -> None:
        """Rating can be created without a review text."""
        data = DesignRatingCreate(rating=4)

        result = await rating_service.create_or_update_rating(
            design_id=public_design.id, user=rater, data=data
        )

        assert result.rating == 4
        assert result.review is None

    @pytest.mark.asyncio
    async def test_create_rating_on_own_design_raises_error(
        self,
        rating_service: DesignRatingService,
        public_design: Design,
        owner: User,
    ) -> None:
        """Rating your own design raises ValueError."""
        data = DesignRatingCreate(rating=5)

        with pytest.raises(ValueError, match="Cannot rate your own design"):
            await rating_service.create_or_update_rating(
                design_id=public_design.id, user=owner, data=data
            )

    @pytest.mark.asyncio
    async def test_create_rating_on_nonexistent_design_raises_error(
        self,
        rating_service: DesignRatingService,
        rater: User,
    ) -> None:
        """Rating a non-existent design raises ValueError."""
        data = DesignRatingCreate(rating=3)

        with pytest.raises(ValueError, match="Design not found or not public"):
            await rating_service.create_or_update_rating(design_id=uuid4(), user=rater, data=data)

    @pytest.mark.asyncio
    async def test_create_rating_on_private_design_raises_error(
        self,
        rating_service: DesignRatingService,
        private_design: Design,
        rater: User,
    ) -> None:
        """Rating a private design raises ValueError."""
        data = DesignRatingCreate(rating=4)

        with pytest.raises(ValueError, match="Design not found or not public"):
            await rating_service.create_or_update_rating(
                design_id=private_design.id, user=rater, data=data
            )

    @pytest.mark.asyncio
    async def test_update_existing_rating_updates_values(
        self,
        rating_service: DesignRatingService,
        public_design: Design,
        rater: User,
    ) -> None:
        """Re-rating a design updates the existing rating instead of creating a new one."""
        # Arrange: create initial rating
        initial = DesignRatingCreate(rating=3, review="Decent")
        first = await rating_service.create_or_update_rating(
            design_id=public_design.id, user=rater, data=initial
        )

        # Act: update rating
        updated_data = DesignRatingCreate(rating=5, review="Actually amazing!")
        second = await rating_service.create_or_update_rating(
            design_id=public_design.id, user=rater, data=updated_data
        )

        # Assert: same ID, updated values
        assert second.id == first.id
        assert second.rating == 5
        assert second.review == "Actually amazing!"

    @pytest.mark.asyncio
    async def test_rating_updates_design_aggregates(
        self,
        rating_service: DesignRatingService,
        public_design: Design,
        rater: User,
        rater_2: User,
        db_session: AsyncSession,
    ) -> None:
        """Creating ratings updates the denormalized avg_rating and total_ratings on the design."""
        # First rating: 4 stars
        await rating_service.create_or_update_rating(
            design_id=public_design.id,
            user=rater,
            data=DesignRatingCreate(rating=4),
        )

        await db_session.refresh(public_design)
        assert public_design.avg_rating == 4.0
        assert public_design.total_ratings == 1

        # Second rating: 2 stars → average = 3.0
        await rating_service.create_or_update_rating(
            design_id=public_design.id,
            user=rater_2,
            data=DesignRatingCreate(rating=2),
        )

        await db_session.refresh(public_design)
        assert public_design.avg_rating == 3.0
        assert public_design.total_ratings == 2


# =============================================================================
# delete_rating Tests
# =============================================================================


class TestDeleteRating:
    """Tests for the delete_rating method."""

    @pytest.mark.asyncio
    async def test_delete_rating_removes_rating(
        self,
        rating_service: DesignRatingService,
        public_design: Design,
        rater: User,
        db_session: AsyncSession,
    ) -> None:
        """Deleting a rating removes it and updates aggregates."""
        # Arrange
        await rating_service.create_or_update_rating(
            design_id=public_design.id,
            user=rater,
            data=DesignRatingCreate(rating=5),
        )

        # Act
        await rating_service.delete_rating(design_id=public_design.id, user=rater)

        # Assert: rating is gone
        result = await rating_service.get_user_rating(public_design.id, rater.id)
        assert result is None

        # Assert: aggregates are zeroed
        await db_session.refresh(public_design)
        assert public_design.total_ratings == 0

    @pytest.mark.asyncio
    async def test_delete_nonexistent_rating_raises_error(
        self,
        rating_service: DesignRatingService,
        public_design: Design,
        rater: User,
    ) -> None:
        """Deleting a non-existent rating raises ValueError."""
        with pytest.raises(ValueError, match="Rating not found"):
            await rating_service.delete_rating(design_id=public_design.id, user=rater)


# =============================================================================
# get_user_rating Tests
# =============================================================================


class TestGetUserRating:
    """Tests for the get_user_rating method."""

    @pytest.mark.asyncio
    async def test_get_user_rating_returns_rating(
        self,
        rating_service: DesignRatingService,
        public_design: Design,
        rater: User,
    ) -> None:
        """Retrieves an existing rating for a user/design pair."""
        await rating_service.create_or_update_rating(
            design_id=public_design.id,
            user=rater,
            data=DesignRatingCreate(rating=4, review="Nice!"),
        )

        result = await rating_service.get_user_rating(public_design.id, rater.id)

        assert result is not None
        assert result.rating == 4
        assert result.review == "Nice!"

    @pytest.mark.asyncio
    async def test_get_user_rating_when_none_returns_none(
        self,
        rating_service: DesignRatingService,
        public_design: Design,
        rater: User,
    ) -> None:
        """Returns None when the user hasn't rated the design."""
        result = await rating_service.get_user_rating(public_design.id, rater.id)
        assert result is None


# =============================================================================
# get_design_ratings Tests
# =============================================================================


class TestGetDesignRatings:
    """Tests for the get_design_ratings method."""

    @pytest.mark.asyncio
    async def test_get_design_ratings_returns_paginated(
        self,
        rating_service: DesignRatingService,
        public_design: Design,
        rater: User,
        rater_2: User,
    ) -> None:
        """Returns paginated ratings with user info for a design."""
        # Arrange: create multiple ratings
        await rating_service.create_or_update_rating(
            design_id=public_design.id,
            user=rater,
            data=DesignRatingCreate(rating=5, review="Great!"),
        )
        await rating_service.create_or_update_rating(
            design_id=public_design.id,
            user=rater_2,
            data=DesignRatingCreate(rating=3, review="OK"),
        )

        # Act
        ratings, total = await rating_service.get_design_ratings(
            public_design.id, page=1, page_size=10
        )

        # Assert
        assert total == 2
        assert len(ratings) == 2
        assert all(hasattr(r, "user_name") for r in ratings)

    @pytest.mark.asyncio
    async def test_get_design_ratings_pagination_limits(
        self,
        rating_service: DesignRatingService,
        public_design: Design,
        db_session: AsyncSession,
    ) -> None:
        """Pagination properly limits results and returns correct total."""
        # Create 3 users and ratings
        users = []
        for i in range(3):
            u = await UserFactory.create(db_session, email=f"paginate{i}@test.com")
            users.append(u)
            await rating_service.create_or_update_rating(
                design_id=public_design.id,
                user=u,
                data=DesignRatingCreate(rating=3 + (i % 3)),
            )

        # Request page_size=2
        ratings, total = await rating_service.get_design_ratings(
            public_design.id, page=1, page_size=2
        )

        assert total == 3
        assert len(ratings) == 2

    @pytest.mark.asyncio
    async def test_get_design_ratings_empty_design_returns_empty(
        self,
        rating_service: DesignRatingService,
        public_design: Design,
    ) -> None:
        """Returns empty list for a design with no ratings."""
        ratings, total = await rating_service.get_design_ratings(public_design.id)
        assert total == 0
        assert ratings == []


# =============================================================================
# get_rating_summary Tests
# =============================================================================


class TestGetRatingSummary:
    """Tests for the get_rating_summary method."""

    @pytest.mark.asyncio
    async def test_get_rating_summary_aggregates_correctly(
        self,
        rating_service: DesignRatingService,
        public_design: Design,
        rater: User,
        rater_2: User,
    ) -> None:
        """Rating summary correctly aggregates average, count, and distribution."""
        # Arrange: 5-star + 3-star = avg 4.0
        await rating_service.create_or_update_rating(
            design_id=public_design.id,
            user=rater,
            data=DesignRatingCreate(rating=5),
        )
        await rating_service.create_or_update_rating(
            design_id=public_design.id,
            user=rater_2,
            data=DesignRatingCreate(rating=3),
        )

        # Act
        summary = await rating_service.get_rating_summary(public_design.id)

        # Assert
        assert summary.design_id == public_design.id
        assert summary.average_rating == 4.0
        assert summary.total_ratings == 2
        assert summary.rating_distribution[5] == 1
        assert summary.rating_distribution[3] == 1
        assert summary.rating_distribution[1] == 0
        assert summary.rating_distribution[2] == 0
        assert summary.rating_distribution[4] == 0

    @pytest.mark.asyncio
    async def test_get_rating_summary_no_ratings_returns_zeros(
        self,
        rating_service: DesignRatingService,
        public_design: Design,
    ) -> None:
        """Summary for a design with no ratings returns zero average and empty distribution."""
        summary = await rating_service.get_rating_summary(public_design.id)

        assert summary.average_rating == 0.0
        assert summary.total_ratings == 0
        assert all(v == 0 for v in summary.rating_distribution.values())

    @pytest.mark.asyncio
    async def test_get_rating_summary_single_rating(
        self,
        rating_service: DesignRatingService,
        public_design: Design,
        rater: User,
    ) -> None:
        """Summary for a single rating returns that rating as the average."""
        await rating_service.create_or_update_rating(
            design_id=public_design.id,
            user=rater,
            data=DesignRatingCreate(rating=2),
        )

        summary = await rating_service.get_rating_summary(public_design.id)

        assert summary.average_rating == 2.0
        assert summary.total_ratings == 1
        assert summary.rating_distribution[2] == 1
