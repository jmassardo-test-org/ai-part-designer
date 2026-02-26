"""
Integration tests for Model Licensing (Epic 13) API endpoints.

Tests license catalog, publish with license, remix license enforcement,
browse license filters, violation reporting, and admin takedown.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING
from uuid import uuid4

import pytest
import pytest_asyncio

from app.models.design import Design
from app.models.project import Project

if TYPE_CHECKING:
    from httpx import AsyncClient
    from sqlalchemy.ext.asyncio import AsyncSession


# =============================================================================
# Fixtures
# =============================================================================


@pytest_asyncio.fixture
async def license_project(db_session: AsyncSession, test_user) -> Project:
    """Create a test project for license tests (owned by test_user)."""
    project = Project(
        user_id=test_user.id,
        name="License Test Project",
        description="Project for license integration tests",
    )
    db_session.add(project)
    await db_session.commit()
    await db_session.refresh(project)
    return project


@pytest_asyncio.fixture
async def other_user_project(db_session: AsyncSession, test_user_2) -> Project:
    """Create a project owned by a DIFFERENT user (test_user_2).

    Designs in this project won't trigger the owner-bypass in license checks
    when auth_client (test_user) tries to remix them.
    """
    project = Project(
        user_id=test_user_2.id,
        name="Other User Project",
        description="Project owned by test_user_2 for remix tests",
    )
    db_session.add(project)
    await db_session.commit()
    await db_session.refresh(project)
    return project


@pytest_asyncio.fixture
async def unpublished_design(
    db_session: AsyncSession, license_project: Project
) -> Design:
    """Create a private design ready to be published."""
    design = Design(
        project_id=license_project.id,
        user_id=license_project.user_id,
        name="Unpublished Widget",
        description="A widget that will be published with a license",
        is_public=False,
        source_type="v2_generated",
        status="ready",
    )
    db_session.add(design)
    await db_session.commit()
    await db_session.refresh(design)
    return design


@pytest_asyncio.fixture
async def cc_by_design(
    db_session: AsyncSession, other_user_project: Project
) -> Design:
    """Create a public CC-BY licensed design owned by OTHER user."""
    design = Design(
        project_id=other_user_project.id,
        user_id=other_user_project.user_id,
        name="CC-BY Open Widget",
        description="An open-source widget under CC-BY",
        is_public=True,
        published_at=datetime.now(UTC) - timedelta(days=3),
        license_type="CC-BY-4.0",
        category="electronics",
        tags=["open-source", "widget"],
        source_type="v2_generated",
        status="ready",
    )
    db_session.add(design)
    await db_session.commit()
    await db_session.refresh(design)
    return design


@pytest_asyncio.fixture
async def cc_by_nd_design(
    db_session: AsyncSession, other_user_project: Project
) -> Design:
    """Create a public CC-BY-ND (no derivatives) design owned by OTHER user."""
    design = Design(
        project_id=other_user_project.id,
        user_id=other_user_project.user_id,
        name="No-Derivatives Case",
        description="A design that does not allow remixing",
        is_public=True,
        published_at=datetime.now(UTC) - timedelta(days=2),
        license_type="CC-BY-ND-4.0",
        category="arduino",
        tags=["no-remix"],
        source_type="v2_generated",
        status="ready",
    )
    db_session.add(design)
    await db_session.commit()
    await db_session.refresh(design)
    return design


@pytest_asyncio.fixture
async def all_rights_design(
    db_session: AsyncSession, other_user_project: Project
) -> Design:
    """Create a public ALL-RIGHTS-RESERVED design owned by OTHER user."""
    design = Design(
        project_id=other_user_project.id,
        user_id=other_user_project.user_id,
        name="Proprietary Gadget",
        description="All rights reserved — no remixing or commercial use",
        is_public=True,
        published_at=datetime.now(UTC) - timedelta(days=1),
        license_type="ALL-RIGHTS-RESERVED",
        category="electronics",
        tags=["proprietary"],
        source_type="v2_generated",
        status="ready",
    )
    db_session.add(design)
    await db_session.commit()
    await db_session.refresh(design)
    return design


@pytest_asyncio.fixture
async def cc_by_nc_design(
    db_session: AsyncSession, other_user_project: Project
) -> Design:
    """Create a public CC-BY-NC (non-commercial) design owned by OTHER user."""
    design = Design(
        project_id=other_user_project.id,
        user_id=other_user_project.user_id,
        name="Non-commercial Part",
        description="CC-BY-NC: remix ok but no commercial use",
        is_public=True,
        published_at=datetime.now(UTC) - timedelta(days=1),
        license_type="CC-BY-NC-4.0",
        category="raspberry-pi",
        tags=["non-commercial"],
        source_type="v2_generated",
        status="ready",
    )
    db_session.add(design)
    await db_session.commit()
    await db_session.refresh(design)
    return design


# =============================================================================
# License Catalog Tests
# =============================================================================


class TestLicenseCatalog:
    """Tests for the GET /licenses/types endpoint."""

    @pytest.mark.asyncio
    async def test_list_license_types_returns_all_types(
        self, auth_client: AsyncClient
    ):
        """Test that the license catalog returns all supported types."""
        response = await auth_client.get("/api/v2/licenses/types")

        assert response.status_code == 200
        data = response.json()

        # Should have 9 types (7 CC variants + ALL-RIGHTS-RESERVED + CUSTOM)
        assert len(data) == 9

        spdx_ids = {item["spdx_id"] for item in data}
        assert "CC0-1.0" in spdx_ids
        assert "CC-BY-4.0" in spdx_ids
        assert "CC-BY-SA-4.0" in spdx_ids
        assert "CC-BY-NC-4.0" in spdx_ids
        assert "CC-BY-NC-SA-4.0" in spdx_ids
        assert "CC-BY-ND-4.0" in spdx_ids
        assert "CC-BY-NC-ND-4.0" in spdx_ids
        assert "ALL-RIGHTS-RESERVED" in spdx_ids
        assert "CUSTOM" in spdx_ids

    @pytest.mark.asyncio
    async def test_license_types_have_required_fields(
        self, auth_client: AsyncClient
    ):
        """Test each license type has all required fields."""
        response = await auth_client.get("/api/v2/licenses/types")

        assert response.status_code == 200
        data = response.json()

        for item in data:
            assert "spdx_id" in item
            assert "name" in item
            assert "allows_remix" in item
            assert "requires_attribution" in item
            assert "allows_commercial" in item
            assert "requires_share_alike" in item
            assert "icon" in item

    @pytest.mark.asyncio
    async def test_cc_by_allows_remix_and_commercial(
        self, auth_client: AsyncClient
    ):
        """Test CC-BY-4.0 metadata is correct."""
        response = await auth_client.get("/api/v2/licenses/types")
        data = response.json()

        cc_by = next(item for item in data if item["spdx_id"] == "CC-BY-4.0")
        assert cc_by["allows_remix"] is True
        assert cc_by["allows_commercial"] is True
        assert cc_by["requires_attribution"] is True
        assert cc_by["requires_share_alike"] is False


# =============================================================================
# Publish with License Tests
# =============================================================================


class TestPublishWithLicense:
    """Tests for publishing designs with license information."""

    @pytest.mark.asyncio
    async def test_publish_with_cc_by_license(
        self, auth_client: AsyncClient, unpublished_design: Design
    ):
        """Test publishing a design with a CC-BY license."""
        response = await auth_client.post(
            f"/api/v2/marketplace/designs/{unpublished_design.id}/publish",
            json={
                "category": "electronics",
                "tags": ["test", "licensed"],
                "license_type": "CC-BY-4.0",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["license_type"] == "CC-BY-4.0"
        assert data["published_at"] is not None

    @pytest.mark.asyncio
    async def test_publish_with_all_rights_reserved(
        self,
        auth_client: AsyncClient,
        db_session: AsyncSession,
        license_project: Project,
    ):
        """Test publishing with ALL-RIGHTS-RESERVED license."""
        design = Design(
            project_id=license_project.id,
            user_id=license_project.user_id,
            name="Proprietary Publish Test",
            description="Publishing with all rights reserved",
            is_public=False,
            source_type="v2_generated",
            status="ready",
        )
        db_session.add(design)
        await db_session.commit()
        await db_session.refresh(design)

        response = await auth_client.post(
            f"/api/v2/marketplace/designs/{design.id}/publish",
            json={
                "category": "electronics",
                "license_type": "ALL-RIGHTS-RESERVED",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["license_type"] == "ALL-RIGHTS-RESERVED"

    @pytest.mark.asyncio
    async def test_publish_without_license_succeeds(
        self,
        auth_client: AsyncClient,
        db_session: AsyncSession,
        license_project: Project,
    ):
        """Test that publishing without a license still succeeds (backwards compat)."""
        design = Design(
            project_id=license_project.id,
            user_id=license_project.user_id,
            name="No License Design",
            description="No license specified",
            is_public=False,
            source_type="v2_generated",
            status="ready",
        )
        db_session.add(design)
        await db_session.commit()
        await db_session.refresh(design)

        response = await auth_client.post(
            f"/api/v2/marketplace/designs/{design.id}/publish",
            json={"category": "electronics"},
        )

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_publish_with_invalid_license_returns_400(
        self,
        auth_client: AsyncClient,
        db_session: AsyncSession,
        license_project: Project,
    ):
        """Test that an invalid license type returns 400."""
        design = Design(
            project_id=license_project.id,
            user_id=license_project.user_id,
            name="Invalid License Design",
            description="This will fail",
            is_public=False,
            source_type="v2_generated",
            status="ready",
        )
        db_session.add(design)
        await db_session.commit()
        await db_session.refresh(design)

        response = await auth_client.post(
            f"/api/v2/marketplace/designs/{design.id}/publish",
            json={
                "category": "electronics",
                "license_type": "INVALID-LICENSE-TYPE",
            },
        )

        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_publish_custom_license_requires_text(
        self,
        auth_client: AsyncClient,
        db_session: AsyncSession,
        license_project: Project,
    ):
        """Test that CUSTOM license requires custom_license_text."""
        design = Design(
            project_id=license_project.id,
            user_id=license_project.user_id,
            name="Custom No Text",
            description="Custom license without text",
            is_public=False,
            source_type="v2_generated",
            status="ready",
        )
        db_session.add(design)
        await db_session.commit()
        await db_session.refresh(design)

        response = await auth_client.post(
            f"/api/v2/marketplace/designs/{design.id}/publish",
            json={
                "category": "electronics",
                "license_type": "CUSTOM",
                # custom_license_text intentionally omitted
            },
        )

        assert response.status_code == 422  # Pydantic model_validator catches this


class TestRemixLicenseEnforcement:
    """Tests for license enforcement during remix."""

    @pytest.mark.asyncio
    async def test_remix_cc_by_design_succeeds(
        self,
        auth_client: AsyncClient,
        cc_by_design: Design,
    ):
        """Test remixing a CC-BY design succeeds."""
        response = await auth_client.post(
            f"/api/v2/marketplace/designs/{cc_by_design.id}/remix",
            json={"name": "My CC-BY Remix"},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["remixed_from_id"] == str(cc_by_design.id)
        assert "Remix" in data["name"] or data["name"] == "My CC-BY Remix"

    @pytest.mark.asyncio
    async def test_remix_cc_by_nd_design_blocked(
        self,
        auth_client: AsyncClient,
        cc_by_nd_design: Design,
    ):
        """Test that remixing a CC-BY-ND (no derivatives) design is blocked."""
        response = await auth_client.post(
            f"/api/v2/marketplace/designs/{cc_by_nd_design.id}/remix",
            json={"name": "Blocked Remix"},
        )

        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_remix_all_rights_reserved_blocked(
        self,
        auth_client: AsyncClient,
        all_rights_design: Design,
    ):
        """Test that remixing an ALL-RIGHTS-RESERVED design is blocked."""
        response = await auth_client.post(
            f"/api/v2/marketplace/designs/{all_rights_design.id}/remix",
            json={"name": "Blocked Remix"},
        )

        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_remix_design_without_license_succeeds(
        self,
        auth_client: AsyncClient,
        db_session: AsyncSession,
        other_user_project: Project,
    ):
        """Test that legacy designs (no license) can still be remixed."""
        legacy = Design(
            project_id=other_user_project.id,
            user_id=other_user_project.user_id,
            name="Legacy No-License Design",
            description="Created before licensing was added",
            is_public=True,
            published_at=datetime.now(UTC) - timedelta(days=10),
            license_type=None,
            category="electronics",
            source_type="v2_generated",
            status="ready",
        )
        db_session.add(legacy)
        await db_session.commit()
        await db_session.refresh(legacy)

        response = await auth_client.post(
            f"/api/v2/marketplace/designs/{legacy.id}/remix",
            json={"name": "Legacy Remix"},
        )

        assert response.status_code == 201


# =============================================================================
# Browse with License Filters Tests
# =============================================================================


class TestBrowseLicenseFilters:
    """Tests for browsing marketplace with license filter parameters."""

    @pytest.mark.asyncio
    async def test_filter_by_license_type(
        self,
        auth_client: AsyncClient,
        cc_by_design: Design,
        cc_by_nd_design: Design,
        all_rights_design: Design,
    ):
        """Test filtering by exact license type."""
        response = await auth_client.get(
            "/api/v2/marketplace/designs",
            params={"license_type": "CC-BY-4.0"},
        )

        assert response.status_code == 200
        data = response.json()

        # Should only return CC-BY designs
        for item in data["items"]:
            assert item.get("license_type") == "CC-BY-4.0"

    @pytest.mark.asyncio
    async def test_filter_allows_remix(
        self,
        auth_client: AsyncClient,
        cc_by_design: Design,
        cc_by_nd_design: Design,
        all_rights_design: Design,
    ):
        """Test filtering for designs that allow remixing."""
        response = await auth_client.get(
            "/api/v2/marketplace/designs",
            params={"allows_remix": True},
        )

        assert response.status_code == 200
        data = response.json()

        # CC-BY allows remix, CC-BY-ND and ALL-RIGHTS-RESERVED do not
        names = [item["name"] for item in data["items"]]
        assert "CC-BY Open Widget" in names
        assert "No-Derivatives Case" not in names
        assert "Proprietary Gadget" not in names

    @pytest.mark.asyncio
    async def test_filter_invalid_license_type_returns_400(
        self,
        auth_client: AsyncClient,
    ):
        """Test that invalid license_type filter returns 400."""
        response = await auth_client.get(
            "/api/v2/marketplace/designs",
            params={"license_type": "NOT-A-REAL-LICENSE"},
        )

        assert response.status_code == 400


# =============================================================================
# Design Detail License Info Tests
# =============================================================================


class TestDesignDetailLicenseInfo:
    """Tests for license info in the design detail response."""

    @pytest.mark.asyncio
    async def test_design_detail_includes_license_info(
        self,
        auth_client: AsyncClient,
        cc_by_design: Design,
    ):
        """Test that design detail includes license_type and license_info."""
        response = await auth_client.get(
            f"/api/v2/marketplace/designs/{cc_by_design.id}"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["license_type"] == "CC-BY-4.0"
        assert data["license_info"] is not None
        assert data["license_info"]["allows_remix"] is True
        assert data["license_info"]["requires_attribution"] is True

    @pytest.mark.asyncio
    async def test_design_detail_no_license_returns_null(
        self,
        auth_client: AsyncClient,
        db_session: AsyncSession,
        other_user_project: Project,
    ):
        """Test that a design without a license returns null license_info."""
        legacy = Design(
            project_id=other_user_project.id,
            user_id=other_user_project.user_id,
            name="Legacy Detail Design",
            description="No license set",
            is_public=True,
            published_at=datetime.now(UTC) - timedelta(days=5),
            license_type=None,
            category="electronics",
            source_type="v2_generated",
            status="ready",
        )
        db_session.add(legacy)
        await db_session.commit()
        await db_session.refresh(legacy)

        response = await auth_client.get(
            f"/api/v2/marketplace/designs/{legacy.id}"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["license_type"] is None
        assert data["license_info"] is None


# =============================================================================
# License Violation Report Tests
# =============================================================================


class TestViolationReport:
    """Tests for the license violation reporting endpoint."""

    @pytest.mark.asyncio
    async def test_report_violation_success(
        self,
        auth_client: AsyncClient,
        cc_by_design: Design,
    ):
        """Test filing a license violation report."""
        response = await auth_client.post(
            f"/api/v2/marketplace/designs/{cc_by_design.id}/report-violation",
            json={
                "violation_type": "missing_attribution",
                "description": "This design uses my work without proper attribution as required by CC-BY.",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["design_id"] == str(cc_by_design.id)
        assert data["violation_type"] == "missing_attribution"
        assert data["status"] == "pending"

    @pytest.mark.asyncio
    async def test_report_violation_with_evidence_url(
        self,
        auth_client: AsyncClient,
        cc_by_nd_design: Design,
    ):
        """Test filing a report with an evidence URL."""
        response = await auth_client.post(
            f"/api/v2/marketplace/designs/{cc_by_nd_design.id}/report-violation",
            json={
                "violation_type": "unauthorized_remix",
                "description": "This design was remixed without permission, violating CC-BY-ND license.",
                "evidence_url": "https://example.com/evidence/screenshot.png",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["violation_type"] == "unauthorized_remix"

    @pytest.mark.asyncio
    async def test_report_violation_invalid_type_returns_400(
        self,
        auth_client: AsyncClient,
        cc_by_design: Design,
    ):
        """Test that an invalid violation type returns 400."""
        response = await auth_client.post(
            f"/api/v2/marketplace/designs/{cc_by_design.id}/report-violation",
            json={
                "violation_type": "not_a_real_type",
                "description": "This should fail validation.",
            },
        )

        assert response.status_code == 422  # Pydantic validation error (regex pattern)

    @pytest.mark.asyncio
    async def test_report_violation_nonexistent_design_returns_400(
        self,
        auth_client: AsyncClient,
    ):
        """Test reporting a nonexistent design returns 400."""
        fake_id = uuid4()
        response = await auth_client.post(
            f"/api/v2/marketplace/designs/{fake_id}/report-violation",
            json={
                "violation_type": "missing_attribution",
                "description": "Reporting a design that doesn't exist.",
            },
        )

        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_report_violation_duplicate_returns_400(
        self,
        auth_client: AsyncClient,
        all_rights_design: Design,
    ):
        """Test that reporting the same design twice returns 400."""
        # First report
        response1 = await auth_client.post(
            f"/api/v2/marketplace/designs/{all_rights_design.id}/report-violation",
            json={
                "violation_type": "commercial_misuse",
                "description": "First report on this design for commercial misuse.",
            },
        )
        assert response1.status_code == 201

        # Duplicate report
        response2 = await auth_client.post(
            f"/api/v2/marketplace/designs/{all_rights_design.id}/report-violation",
            json={
                "violation_type": "commercial_misuse",
                "description": "Second report should be rejected as duplicate.",
            },
        )
        assert response2.status_code == 400


# =============================================================================
# Admin Takedown Tests
# =============================================================================


class TestAdminTakedown:
    """Tests for admin takedown of designs with license violations."""

    @pytest.mark.asyncio
    async def test_admin_takedown_success(
        self,
        admin_client: AsyncClient,
        cc_by_design: Design,
    ):
        """Test admin can take down a published design."""
        response = await admin_client.post(
            f"/api/v2/admin/designs/{cc_by_design.id}/takedown",
            json={
                "reason": "This design was confirmed to violate the original author's license terms.",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["design_id"] == str(cc_by_design.id)
        assert data["reason"] is not None
        assert data["unpublished_at"] is not None

    @pytest.mark.asyncio
    async def test_non_admin_takedown_returns_401_or_403(
        self,
        auth_client: AsyncClient,
        cc_by_design: Design,
    ):
        """Test that non-admin users cannot perform takedowns."""
        response = await auth_client.post(
            f"/api/v2/admin/designs/{cc_by_design.id}/takedown",
            json={
                "reason": "Non-admin should not be able to do this.",
            },
        )

        # Should be either 401 (not authenticated as admin) or 403 (forbidden)
        assert response.status_code in (401, 403)

    @pytest.mark.asyncio
    async def test_takedown_nonexistent_design_returns_404(
        self,
        admin_client: AsyncClient,
    ):
        """Test that taking down a nonexistent design returns 404."""
        fake_id = uuid4()
        response = await admin_client.post(
            f"/api/v2/admin/designs/{fake_id}/takedown",
            json={
                "reason": "Design does not exist, should return 404.",
            },
        )

        assert response.status_code == 404


# =============================================================================
# Admin Violation Listing Tests
# =============================================================================


class TestAdminViolationListing:
    """Tests for admin license violation report listing."""

    @pytest.mark.asyncio
    async def test_admin_list_violations_empty(
        self,
        admin_client: AsyncClient,
    ):
        """Test listing violations when none exist."""
        response = await admin_client.get("/api/v2/admin/license-violations")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["items"] == []

    @pytest.mark.asyncio
    async def test_admin_list_violations_after_report(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        admin_headers: dict[str, str],
        cc_by_design: Design,
    ):
        """Test that admin sees filed violation reports.

        Uses raw client with explicit headers per-request because
        auth_client and admin_client share the same underlying client
        and cannot be used together.
        """
        # File a report first (as a regular user)
        report_resp = await client.post(
            f"/api/v2/marketplace/designs/{cc_by_design.id}/report-violation",
            json={
                "violation_type": "missing_attribution",
                "description": "Filed a report so admin can see it in the listing.",
            },
            headers=auth_headers,
        )
        assert report_resp.status_code == 201

        # Now list as admin
        response = await client.get(
            "/api/v2/admin/license-violations",
            headers=admin_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1

        # Find our report
        report_ids = [item["design_id"] for item in data["items"]]
        assert str(cc_by_design.id) in report_ids

    @pytest.mark.asyncio
    async def test_admin_list_violations_filter_by_status(
        self,
        admin_client: AsyncClient,
    ):
        """Test filtering violations by status."""
        response = await admin_client.get(
            "/api/v2/admin/license-violations",
            params={"report_status": "pending"},
        )

        assert response.status_code == 200
        data = response.json()
        # All returned items should have pending status
        for item in data["items"]:
            assert item["status"] == "pending"

    @pytest.mark.asyncio
    async def test_admin_list_violations_invalid_status_returns_400(
        self,
        admin_client: AsyncClient,
    ):
        """Test that invalid status filter returns 400."""
        response = await admin_client.get(
            "/api/v2/admin/license-violations",
            params={"report_status": "not_a_real_status"},
        )

        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_non_admin_list_violations_returns_401_or_403(
        self,
        auth_client: AsyncClient,
    ):
        """Test that non-admin users cannot list violations."""
        response = await auth_client.get("/api/v2/admin/license-violations")

        assert response.status_code in (401, 403)
