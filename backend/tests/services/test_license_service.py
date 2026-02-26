"""
Tests for LicenseService.

Tests license validation, remix permission checks, attribution generation,
violation reporting, admin takedown, and paginated license listings.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
import pytest_asyncio
from tests.factories import DesignFactory, ProjectFactory, UserFactory

from app.core.licenses import LicenseType
from app.models.design import Design
from app.models.rating import ContentReport, ReportStatus
from app.models.user import User  # noqa: TC001 — used at runtime by factories
from app.services.license_service import LicenseService

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


# =============================================================================
# Fixtures
# =============================================================================


@pytest_asyncio.fixture
async def owner(db_session: AsyncSession) -> User:
    """Create a design owner user."""
    return await UserFactory.create(
        db_session, email="license_owner@test.com", display_name="License Owner"
    )


@pytest_asyncio.fixture
async def other_user(db_session: AsyncSession) -> User:
    """Create another user for remix/report tests."""
    return await UserFactory.create(
        db_session, email="license_other@test.com", display_name="Other User"
    )


@pytest_asyncio.fixture
async def admin_user(db_session: AsyncSession) -> User:
    """Create an admin user for takedown tests."""
    return await UserFactory.create_admin(
        db_session, email="license_admin@test.com", display_name="Admin"
    )


@pytest_asyncio.fixture
async def public_design(db_session: AsyncSession, owner: User) -> Design:
    """Create a public design with CC-BY-4.0 license."""
    project = await ProjectFactory.create(db_session, user=owner)
    design = await DesignFactory.create(
        db_session,
        project=project,
        user=owner,
        is_public=True,
        name="Licensed Design",
    )
    design.license_type = LicenseType.CC_BY_4_0.value
    design.published_at = datetime.now(UTC)
    await db_session.commit()
    await db_session.refresh(design)
    return design


@pytest_asyncio.fixture
async def nd_design(db_session: AsyncSession, owner: User) -> Design:
    """Create a public design with CC-BY-ND-4.0 (no derivatives) license."""
    project = await ProjectFactory.create(db_session, user=owner)
    design = await DesignFactory.create(
        db_session,
        project=project,
        user=owner,
        is_public=True,
        name="No-Derivatives Design",
    )
    design.license_type = LicenseType.CC_BY_ND_4_0.value
    design.published_at = datetime.now(UTC)
    await db_session.commit()
    await db_session.refresh(design)
    return design


@pytest_asyncio.fixture
async def sa_design(db_session: AsyncSession, owner: User) -> Design:
    """Create a public design with CC-BY-SA-4.0 (share-alike) license."""
    project = await ProjectFactory.create(db_session, user=owner)
    design = await DesignFactory.create(
        db_session,
        project=project,
        user=owner,
        is_public=True,
        name="Share-Alike Design",
    )
    design.license_type = LicenseType.CC_BY_SA_4_0.value
    design.published_at = datetime.now(UTC)
    await db_session.commit()
    await db_session.refresh(design)
    return design


@pytest_asyncio.fixture
async def unlicensed_design(db_session: AsyncSession, owner: User) -> Design:
    """Create a public design with no license set."""
    project = await ProjectFactory.create(db_session, user=owner)
    design = await DesignFactory.create(
        db_session,
        project=project,
        user=owner,
        is_public=True,
        name="Unlicensed Design",
    )
    design.published_at = datetime.now(UTC)
    await db_session.commit()
    await db_session.refresh(design)
    return design


@pytest_asyncio.fixture
def license_service(db_session: AsyncSession) -> LicenseService:
    """Create a LicenseService instance."""
    return LicenseService(db_session)


# =============================================================================
# validate_license_for_publish Tests
# =============================================================================


class TestValidateLicenseForPublish:
    """Tests for the validate_license_for_publish method."""

    @pytest.mark.asyncio
    async def test_validate_none_license_passes(
        self,
        license_service: LicenseService,
        public_design: Design,
    ) -> None:
        """Publishing without a license (None) should pass validation."""
        await license_service.validate_license_for_publish(
            design=public_design,
            license_type=None,
            custom_license_text=None,
            custom_allows_remix=False,
        )
        # No exception raised

    @pytest.mark.asyncio
    async def test_validate_valid_license_passes(
        self,
        license_service: LicenseService,
        public_design: Design,
    ) -> None:
        """Publishing with a valid license type passes validation."""
        await license_service.validate_license_for_publish(
            design=public_design,
            license_type=LicenseType.CC_BY_4_0.value,
            custom_license_text=None,
            custom_allows_remix=False,
        )

    @pytest.mark.asyncio
    async def test_validate_invalid_license_raises_error(
        self,
        license_service: LicenseService,
        public_design: Design,
    ) -> None:
        """Publishing with an invalid license type raises ValueError."""
        with pytest.raises(ValueError, match="Invalid license type"):
            await license_service.validate_license_for_publish(
                design=public_design,
                license_type="DEFINITELY-NOT-A-LICENSE",
                custom_license_text=None,
                custom_allows_remix=False,
            )

    @pytest.mark.asyncio
    async def test_validate_custom_without_text_raises_error(
        self,
        license_service: LicenseService,
        public_design: Design,
    ) -> None:
        """CUSTOM license without custom_license_text raises ValueError."""
        with pytest.raises(ValueError, match="Custom license text is required"):
            await license_service.validate_license_for_publish(
                design=public_design,
                license_type=LicenseType.CUSTOM.value,
                custom_license_text=None,
                custom_allows_remix=False,
            )

    @pytest.mark.asyncio
    async def test_validate_custom_with_empty_text_raises_error(
        self,
        license_service: LicenseService,
        public_design: Design,
    ) -> None:
        """CUSTOM license with blank text raises ValueError."""
        with pytest.raises(ValueError, match="Custom license text is required"):
            await license_service.validate_license_for_publish(
                design=public_design,
                license_type=LicenseType.CUSTOM.value,
                custom_license_text="   ",
                custom_allows_remix=False,
            )

    @pytest.mark.asyncio
    async def test_validate_custom_with_text_passes(
        self,
        license_service: LicenseService,
        public_design: Design,
    ) -> None:
        """CUSTOM license with valid text passes validation."""
        await license_service.validate_license_for_publish(
            design=public_design,
            license_type=LicenseType.CUSTOM.value,
            custom_license_text="My custom terms allow personal use only.",
            custom_allows_remix=False,
        )

    @pytest.mark.asyncio
    async def test_validate_custom_with_overlength_text_raises_error(
        self,
        license_service: LicenseService,
        public_design: Design,
    ) -> None:
        """CUSTOM license with text > 5000 chars raises ValueError."""
        with pytest.raises(ValueError, match="5000 characters"):
            await license_service.validate_license_for_publish(
                design=public_design,
                license_type=LicenseType.CUSTOM.value,
                custom_license_text="x" * 5001,
                custom_allows_remix=False,
            )

    @pytest.mark.asyncio
    async def test_validate_share_alike_remix_with_incompatible_license_raises(
        self,
        license_service: LicenseService,
        sa_design: Design,
        db_session: AsyncSession,
        owner: User,
    ) -> None:
        """Remixed design with incompatible license against share-alike parent raises ValueError."""
        # Create a remix of the share-alike design
        project = await ProjectFactory.create(db_session, user=owner)
        remix = await DesignFactory.create(
            db_session,
            project=project,
            user=owner,
            is_public=False,
            name="My Remix",
        )
        remix.remixed_from_id = sa_design.id
        await db_session.commit()
        await db_session.refresh(remix)

        # Try to publish with a different license (should fail because of share-alike)
        with pytest.raises(ValueError, match="Share-alike"):
            await license_service.validate_license_for_publish(
                design=remix,
                license_type=LicenseType.CC_BY_4_0.value,
                custom_license_text=None,
                custom_allows_remix=False,
            )

    @pytest.mark.asyncio
    async def test_validate_share_alike_remix_with_same_license_passes(
        self,
        license_service: LicenseService,
        sa_design: Design,
        db_session: AsyncSession,
        owner: User,
    ) -> None:
        """Remixed design using the same share-alike license passes validation."""
        project = await ProjectFactory.create(db_session, user=owner)
        remix = await DesignFactory.create(
            db_session,
            project=project,
            user=owner,
            is_public=False,
            name="SA Remix",
        )
        remix.remixed_from_id = sa_design.id
        await db_session.commit()
        await db_session.refresh(remix)

        await license_service.validate_license_for_publish(
            design=remix,
            license_type=LicenseType.CC_BY_SA_4_0.value,
            custom_license_text=None,
            custom_allows_remix=False,
        )


# =============================================================================
# check_remix_allowed Tests
# =============================================================================


class TestCheckRemixAllowed:
    """Tests for the check_remix_allowed method."""

    @pytest.mark.asyncio
    async def test_owner_can_always_remix(
        self,
        license_service: LicenseService,
        nd_design: Design,
        owner: User,
    ) -> None:
        """Design owner can remix even if license disallows it."""
        allowed, reason = await license_service.check_remix_allowed(nd_design, owner)
        assert allowed is True
        assert reason is None

    @pytest.mark.asyncio
    async def test_cc_by_allows_remix(
        self,
        license_service: LicenseService,
        public_design: Design,
        other_user: User,
    ) -> None:
        """CC-BY-4.0 design allows remix by others."""
        allowed, reason = await license_service.check_remix_allowed(public_design, other_user)
        assert allowed is True
        assert reason is None

    @pytest.mark.asyncio
    async def test_nd_license_blocks_remix(
        self,
        license_service: LicenseService,
        nd_design: Design,
        other_user: User,
    ) -> None:
        """CC-BY-ND-4.0 design blocks remix by others."""
        allowed, reason = await license_service.check_remix_allowed(nd_design, other_user)
        assert allowed is False
        assert reason is not None
        assert "remixing" in reason.lower()

    @pytest.mark.asyncio
    async def test_unlicensed_design_allows_remix(
        self,
        license_service: LicenseService,
        unlicensed_design: Design,
        other_user: User,
    ) -> None:
        """Design with no license allows remix by default."""
        allowed, reason = await license_service.check_remix_allowed(unlicensed_design, other_user)
        assert allowed is True
        assert reason is None


# =============================================================================
# build_attribution Tests
# =============================================================================


class TestBuildAttribution:
    """Tests for the build_attribution method."""

    @pytest.mark.asyncio
    async def test_build_attribution_returns_complete_dict(
        self,
        license_service: LicenseService,
        public_design: Design,
        owner: User,
    ) -> None:
        """Attribution dict contains all required keys."""
        attribution = await license_service.build_attribution(public_design, owner)

        assert "parent_design_id" in attribution
        assert "parent_design_name" in attribution
        assert "parent_author_id" in attribution
        assert "parent_author_name" in attribution
        assert "license_type" in attribution
        assert "license_name" in attribution
        assert "license_url" in attribution
        assert "requires_attribution" in attribution

    @pytest.mark.asyncio
    async def test_build_attribution_has_correct_values(
        self,
        license_service: LicenseService,
        public_design: Design,
        owner: User,
    ) -> None:
        """Attribution dict values match the design and author."""
        attribution = await license_service.build_attribution(public_design, owner)

        assert attribution["parent_design_id"] == str(public_design.id)
        assert attribution["parent_design_name"] == public_design.name
        assert attribution["parent_author_id"] == str(owner.id)
        assert attribution["license_type"] == LicenseType.CC_BY_4_0.value
        assert attribution["requires_attribution"] is True

    @pytest.mark.asyncio
    async def test_build_attribution_for_unlicensed_design(
        self,
        license_service: LicenseService,
        unlicensed_design: Design,
        owner: User,
    ) -> None:
        """Attribution for unlicensed design has None for license fields."""
        attribution = await license_service.build_attribution(unlicensed_design, owner)

        assert attribution["license_type"] is None
        assert attribution["license_name"] is None
        assert attribution["requires_attribution"] is False


# =============================================================================
# report_violation Tests
# =============================================================================


class TestReportViolation:
    """Tests for the report_violation method."""

    @pytest.mark.asyncio
    async def test_report_violation_creates_report(
        self,
        license_service: LicenseService,
        public_design: Design,
        other_user: User,
    ) -> None:
        """Filing a violation report creates a ContentReport."""
        result = await license_service.report_violation(
            design_id=public_design.id,
            reporter=other_user,
            violation_type="unauthorized_remix",
            description="This design was remixed without permission from the original author.",
            evidence_url="https://example.com/evidence",
        )

        assert result.id is not None
        assert result.design_id == public_design.id
        assert result.violation_type == "unauthorized_remix"
        assert result.status == "pending"
        assert result.created_at is not None

    @pytest.mark.asyncio
    async def test_report_violation_without_evidence_url(
        self,
        license_service: LicenseService,
        public_design: Design,
        other_user: User,
    ) -> None:
        """Violation report can be created without evidence URL."""
        result = await license_service.report_violation(
            design_id=public_design.id,
            reporter=other_user,
            violation_type="missing_attribution",
            description="This remix does not credit the original author properly.",
        )

        assert result.id is not None
        assert result.status == "pending"

    @pytest.mark.asyncio
    async def test_report_violation_duplicate_raises_error(
        self,
        license_service: LicenseService,
        public_design: Design,
        other_user: User,
    ) -> None:
        """Filing duplicate violation report raises ValueError."""
        await license_service.report_violation(
            design_id=public_design.id,
            reporter=other_user,
            violation_type="commercial_misuse",
            description="This design is being sold in violation of its NC license.",
        )

        with pytest.raises(ValueError, match="already reported"):
            await license_service.report_violation(
                design_id=public_design.id,
                reporter=other_user,
                violation_type="commercial_misuse",
                description="Duplicate report attempt.",
            )

    @pytest.mark.asyncio
    async def test_report_violation_nonexistent_design_raises_error(
        self,
        license_service: LicenseService,
        other_user: User,
    ) -> None:
        """Reporting a non-existent design raises ValueError."""
        with pytest.raises(ValueError, match="Design not found"):
            await license_service.report_violation(
                design_id=uuid4(),
                reporter=other_user,
                violation_type="other",
                description="This should fail.",
            )

    @pytest.mark.asyncio
    async def test_report_violation_invalid_type_raises_error(
        self,
        license_service: LicenseService,
        public_design: Design,
        other_user: User,
    ) -> None:
        """Invalid violation type raises ValueError."""
        with pytest.raises(ValueError, match="Invalid violation type"):
            await license_service.report_violation(
                design_id=public_design.id,
                reporter=other_user,
                violation_type="made_up_type",
                description="Using invalid violation type.",
            )


# =============================================================================
# admin_takedown Tests
# =============================================================================


class TestAdminTakedown:
    """Tests for the admin_takedown method."""

    @pytest.mark.asyncio
    async def test_admin_takedown_unpublishes_design(
        self,
        license_service: LicenseService,
        public_design: Design,
        admin_user: User,
        db_session: AsyncSession,
    ) -> None:
        """Admin takedown unpublishes the design."""
        result = await license_service.admin_takedown(
            design_id=public_design.id,
            admin_user=admin_user,
            reason="License violation confirmed after review.",
        )

        assert result.design_id == public_design.id
        assert result.admin_id == admin_user.id
        assert result.reason == "License violation confirmed after review."
        assert result.unpublished_at is not None

        # Verify design state
        await db_session.refresh(public_design)
        assert public_design.is_public is False

    @pytest.mark.asyncio
    async def test_admin_takedown_by_non_admin_raises_error(
        self,
        license_service: LicenseService,
        public_design: Design,
        other_user: User,
    ) -> None:
        """Non-admin cannot perform takedown."""
        with pytest.raises(PermissionError, match="Only admins"):
            await license_service.admin_takedown(
                design_id=public_design.id,
                admin_user=other_user,
                reason="Should not be allowed.",
            )

    @pytest.mark.asyncio
    async def test_admin_takedown_nonexistent_design_raises_error(
        self,
        license_service: LicenseService,
        admin_user: User,
    ) -> None:
        """Takedown of non-existent design raises ValueError."""
        with pytest.raises(ValueError, match="Design not found"):
            await license_service.admin_takedown(
                design_id=uuid4(),
                admin_user=admin_user,
                reason="Non-existent design.",
            )

    @pytest.mark.asyncio
    async def test_admin_takedown_unpublished_design_raises_error(
        self,
        license_service: LicenseService,
        admin_user: User,
        db_session: AsyncSession,
        owner: User,
    ) -> None:
        """Takedown of an unpublished design raises ValueError."""
        project = await ProjectFactory.create(db_session, user=owner)
        draft = await DesignFactory.create(
            db_session, project=project, user=owner, is_public=False, name="Draft"
        )

        with pytest.raises(ValueError, match="not currently published"):
            await license_service.admin_takedown(
                design_id=draft.id,
                admin_user=admin_user,
                reason="Cannot take down unpublished.",
            )

    @pytest.mark.asyncio
    async def test_admin_takedown_with_violation_report_resolves_report(
        self,
        license_service: LicenseService,
        public_design: Design,
        admin_user: User,
        other_user: User,
        db_session: AsyncSession,
    ) -> None:
        """Takedown with a linked violation report marks the report resolved."""
        # First create a violation report
        report_result = await license_service.report_violation(
            design_id=public_design.id,
            reporter=other_user,
            violation_type="unauthorized_remix",
            description="Unauthorized remix evidence.",
        )

        # Now perform takedown linked to that report
        takedown = await license_service.admin_takedown(
            design_id=public_design.id,
            admin_user=admin_user,
            reason="Confirmed violation.",
            violation_report_id=report_result.id,
        )

        assert takedown.design_id == public_design.id

        # Verify the report was resolved
        report = await db_session.get(ContentReport, report_result.id)
        assert report is not None
        assert report.status == ReportStatus.RESOLVED.value
        assert report.resolved_by_id == admin_user.id
        assert report.action_taken == "takedown"


# =============================================================================
# get_user_published_licenses Tests
# =============================================================================


class TestGetUserPublishedLicenses:
    """Tests for the get_user_published_licenses method."""

    @pytest.mark.asyncio
    async def test_returns_published_designs(
        self,
        license_service: LicenseService,
        public_design: Design,
        owner: User,
    ) -> None:
        """Returns the owner's published designs with license info."""
        result = await license_service.get_user_published_licenses(owner)

        assert result.total >= 1
        assert result.page == 1
        assert any(item.design_id == public_design.id for item in result.items)

    @pytest.mark.asyncio
    async def test_returns_license_name_for_licensed_designs(
        self,
        license_service: LicenseService,
        public_design: Design,
        owner: User,
    ) -> None:
        """Licensed designs include the human-readable license name."""
        result = await license_service.get_user_published_licenses(owner)

        matching = [i for i in result.items if i.design_id == public_design.id]
        assert len(matching) == 1
        assert matching[0].license_type == LicenseType.CC_BY_4_0.value
        assert matching[0].license_name is not None
        assert "Attribution" in matching[0].license_name

    @pytest.mark.asyncio
    async def test_filter_by_license_type(
        self,
        license_service: LicenseService,
        public_design: Design,
        owner: User,
    ) -> None:
        """Filter parameter limits results to specific license type."""
        result = await license_service.get_user_published_licenses(
            owner, license_type_filter=LicenseType.CC_BY_4_0.value
        )
        for item in result.items:
            assert item.license_type == LicenseType.CC_BY_4_0.value

    @pytest.mark.asyncio
    async def test_filter_by_nonexistent_license_type_returns_empty(
        self,
        license_service: LicenseService,
        owner: User,
    ) -> None:
        """Filter for a license type with no designs returns empty list."""
        result = await license_service.get_user_published_licenses(
            owner, license_type_filter=LicenseType.CC0_1_0.value
        )
        assert result.total == 0
        assert len(result.items) == 0

    @pytest.mark.asyncio
    async def test_empty_for_user_with_no_published(
        self,
        license_service: LicenseService,
        other_user: User,
    ) -> None:
        """User with no published designs gets empty result."""
        result = await license_service.get_user_published_licenses(other_user)
        assert result.total == 0
        assert len(result.items) == 0

    @pytest.mark.asyncio
    async def test_pagination_fields(
        self,
        license_service: LicenseService,
        owner: User,
    ) -> None:
        """Pagination metadata is correct."""
        result = await license_service.get_user_published_licenses(owner, page=1, page_size=10)
        assert result.page == 1
        assert result.page_size == 10
        assert result.total_pages >= 1
        assert isinstance(result.has_next, bool)
        assert isinstance(result.has_prev, bool)


# =============================================================================
# get_user_remixed_licenses Tests
# =============================================================================


class TestGetUserRemixedLicenses:
    """Tests for the get_user_remixed_licenses method."""

    @pytest.mark.asyncio
    async def test_returns_remixed_designs(
        self,
        license_service: LicenseService,
        public_design: Design,
        other_user: User,
        db_session: AsyncSession,
    ) -> None:
        """Returns designs that are remixes of other designs."""
        project = await ProjectFactory.create(db_session, user=other_user)
        remix = await DesignFactory.create(
            db_session,
            project=project,
            user=other_user,
            is_public=False,
            name="My Remix",
        )
        remix.remixed_from_id = public_design.id
        await db_session.commit()
        await db_session.refresh(remix)

        result = await license_service.get_user_remixed_licenses(other_user)

        assert result.total >= 1
        matching = [i for i in result.items if i.design_id == remix.id]
        assert len(matching) == 1
        assert matching[0].parent_design_id == public_design.id
        assert matching[0].parent_license_type == LicenseType.CC_BY_4_0.value

    @pytest.mark.asyncio
    async def test_empty_for_user_with_no_remixes(
        self,
        license_service: LicenseService,
        other_user: User,
    ) -> None:
        """User with no remixed designs gets empty result."""
        result = await license_service.get_user_remixed_licenses(other_user)
        assert result.total == 0
        assert len(result.items) == 0

    @pytest.mark.asyncio
    async def test_pagination_fields(
        self,
        license_service: LicenseService,
        other_user: User,
    ) -> None:
        """Pagination metadata is correct for empty results."""
        result = await license_service.get_user_remixed_licenses(other_user, page=1, page_size=10)
        assert result.page == 1
        assert result.page_size == 10
        assert result.total_pages >= 1


# =============================================================================
# get_license_detail Tests
# =============================================================================


class TestGetLicenseDetail:
    """Tests for the get_license_detail method."""

    def test_licensed_design_returns_full_detail(
        self,
        license_service: LicenseService,
    ) -> None:
        """Licensed design returns fully populated LicenseDetailResponse."""
        design = MagicMock(spec=Design)
        design.license_type = LicenseType.CC_BY_4_0.value
        design.custom_license_text = None
        design.custom_allows_remix = False

        detail = license_service.get_license_detail(design)

        assert detail.license_type == LicenseType.CC_BY_4_0.value
        assert detail.license_name == "Creative Commons Attribution 4.0"
        assert detail.allows_remix is True
        assert detail.requires_attribution is True
        assert detail.icon == "cc-by"

    def test_unlicensed_design_returns_none_fields(
        self,
        license_service: LicenseService,
    ) -> None:
        """Design with no license returns minimal detail."""
        design = MagicMock(spec=Design)
        design.license_type = None

        detail = license_service.get_license_detail(design)

        assert detail.license_type is None
        assert detail.license_name is None

    def test_custom_license_includes_text(
        self,
        license_service: LicenseService,
    ) -> None:
        """CUSTOM license includes the custom_license_text."""
        design = MagicMock(spec=Design)
        design.license_type = LicenseType.CUSTOM.value
        design.custom_license_text = "My custom terms."
        design.custom_allows_remix = True

        detail = license_service.get_license_detail(design)

        assert detail.license_type == "CUSTOM"
        assert detail.custom_license_text == "My custom terms."
        assert detail.allows_remix is True
        assert detail.icon == "file-text"
