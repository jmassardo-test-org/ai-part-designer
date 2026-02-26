"""
Tests for DesignReportService.

Tests report creation, duplicate prevention, and status checking for
marketplace design content moderation.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
import pytest_asyncio
from tests.factories import DesignFactory, ProjectFactory, UserFactory

from app.schemas.rating import DesignReportCreate
from app.services.design_report_service import DesignReportService

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
async def reporter(db_session: AsyncSession) -> User:
    """Create a user who reports designs."""
    return await UserFactory.create(db_session, email="reporter@test.com", display_name="Reporter")


@pytest_asyncio.fixture
async def reporter_2(db_session: AsyncSession) -> User:
    """Create a second reporter for multi-report tests."""
    return await UserFactory.create(
        db_session, email="reporter2@test.com", display_name="Reporter 2"
    )


@pytest_asyncio.fixture
async def public_design(db_session: AsyncSession, owner: User) -> Design:
    """Create a public marketplace design."""
    project = await ProjectFactory.create(db_session, user=owner)
    return await DesignFactory.create(
        db_session,
        project=project,
        user=owner,
        is_public=True,
        name="Reported Design",
    )


@pytest_asyncio.fixture
def report_service(db_session: AsyncSession) -> DesignReportService:
    """Create a DesignReportService instance."""
    return DesignReportService(db_session)


# =============================================================================
# create_report Tests
# =============================================================================


class TestCreateReport:
    """Tests for the create_report method."""

    @pytest.mark.asyncio
    async def test_create_report_returns_report(
        self,
        report_service: DesignReportService,
        public_design: Design,
        reporter: User,
    ) -> None:
        """Creating a report with valid data returns a response with pending status."""
        data = DesignReportCreate(reason="spam", description="This is spam content")

        result = await report_service.create_report(
            design_id=public_design.id, user=reporter, data=data
        )

        assert result.id is not None
        assert result.status == "pending"
        assert result.created_at is not None

    @pytest.mark.asyncio
    async def test_create_report_without_description(
        self,
        report_service: DesignReportService,
        public_design: Design,
        reporter: User,
    ) -> None:
        """Report can be created with just a reason, no description."""
        data = DesignReportCreate(reason="inappropriate")

        result = await report_service.create_report(
            design_id=public_design.id, user=reporter, data=data
        )

        assert result.id is not None
        assert result.status == "pending"

    @pytest.mark.asyncio
    async def test_create_duplicate_report_raises_error(
        self,
        report_service: DesignReportService,
        public_design: Design,
        reporter: User,
    ) -> None:
        """Reporting the same design twice by the same user raises ValueError."""
        data = DesignReportCreate(reason="copyright")
        await report_service.create_report(design_id=public_design.id, user=reporter, data=data)

        with pytest.raises(ValueError, match="already reported"):
            await report_service.create_report(design_id=public_design.id, user=reporter, data=data)

    @pytest.mark.asyncio
    async def test_different_users_can_report_same_design(
        self,
        report_service: DesignReportService,
        public_design: Design,
        reporter: User,
        reporter_2: User,
    ) -> None:
        """Different users can independently report the same design."""
        data = DesignReportCreate(reason="offensive")

        result_1 = await report_service.create_report(
            design_id=public_design.id, user=reporter, data=data
        )
        result_2 = await report_service.create_report(
            design_id=public_design.id, user=reporter_2, data=data
        )

        assert result_1.id != result_2.id
        assert result_1.status == "pending"
        assert result_2.status == "pending"


# =============================================================================
# check_report_status Tests
# =============================================================================


class TestCheckReportStatus:
    """Tests for the check_report_status method."""

    @pytest.mark.asyncio
    async def test_check_report_status_not_reported(
        self,
        report_service: DesignReportService,
        public_design: Design,
        reporter: User,
    ) -> None:
        """Status check for an unreported design returns already_reported=False."""
        status = await report_service.check_report_status(
            design_id=public_design.id, user_id=reporter.id
        )
        assert status.already_reported is False

    @pytest.mark.asyncio
    async def test_check_report_status_already_reported(
        self,
        report_service: DesignReportService,
        public_design: Design,
        reporter: User,
    ) -> None:
        """Status check after reporting returns already_reported=True."""
        await report_service.create_report(
            design_id=public_design.id,
            user=reporter,
            data=DesignReportCreate(reason="misleading"),
        )

        status = await report_service.check_report_status(
            design_id=public_design.id, user_id=reporter.id
        )
        assert status.already_reported is True

    @pytest.mark.asyncio
    async def test_check_report_status_other_user_not_affected(
        self,
        report_service: DesignReportService,
        public_design: Design,
        reporter: User,
        reporter_2: User,
    ) -> None:
        """User A's report doesn't affect User B's report status."""
        await report_service.create_report(
            design_id=public_design.id,
            user=reporter,
            data=DesignReportCreate(reason="spam"),
        )

        status = await report_service.check_report_status(
            design_id=public_design.id, user_id=reporter_2.id
        )
        assert status.already_reported is False
