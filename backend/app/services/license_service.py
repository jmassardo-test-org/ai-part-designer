"""License service for marketplace licensing operations (Epic 13).

Provides business logic for license validation, remix checks,
attribution generation, violation reporting, and admin takedown.
"""

import math
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.licenses import (
    LicenseType,
    get_license_metadata,
    get_share_alike_compatible_licenses,
    is_valid_license_type,
)
from app.core.licenses import (
    allows_remix as license_allows_remix,
)
from app.models.audit import AuditActions, AuditLog
from app.models.design import Design
from app.models.rating import (
    ContentReport,
    LicenseViolationType,
    ReportStatus,
    ReportTargetType,
)
from app.models.user import User
from app.schemas.license import (
    LicenseDetailResponse,
    LicenseViolationReportResponse,
    PaginatedPublishedLicensesResponse,
    PaginatedRemixedLicensesResponse,
    PublishedLicenseItem,
    RemixedLicenseItem,
    TakedownResponse,
)


class LicenseService:
    """Service for managing design licenses in the marketplace.

    Handles license validation, remix permission checks, attribution
    generation, violation reporting, and admin takedown operations.
    """

    def __init__(self, db: AsyncSession) -> None:
        """Initialize the service.

        Args:
            db: Async database session.
        """
        self.db = db

    async def validate_license_for_publish(
        self,
        design: Design,
        license_type: str | None,
        custom_license_text: str | None,
        custom_allows_remix: bool,  # noqa: ARG002 — accepted for future validation
    ) -> None:
        """Validate license parameters before publishing a design.

        Checks that the license type is valid, custom license text is provided
        when needed, and share-alike constraints from parent designs are satisfied.

        Args:
            design: The design being published.
            license_type: SPDX-like license identifier or None.
            custom_license_text: Custom license terms (for CUSTOM type).
            custom_allows_remix: Whether custom license allows remixing.

        Raises:
            ValueError: If license validation fails.
        """
        if license_type is None:
            return

        if not is_valid_license_type(license_type):
            raise ValueError(f"Invalid license type: {license_type}")

        if license_type == LicenseType.CUSTOM:
            if not custom_license_text or not custom_license_text.strip():
                raise ValueError(
                    "Custom license text is required when license_type is CUSTOM"
                )
            if len(custom_license_text) > 5000:
                raise ValueError(
                    "Custom license text must be 5000 characters or fewer"
                )

        # Check share-alike constraints from parent design
        if design.remixed_from_id is not None:
            parent = await self.db.get(Design, design.remixed_from_id)
            if parent and parent.license_type:
                compatible = get_share_alike_compatible_licenses(parent.license_type)
                if compatible and license_type not in compatible:
                    parent_info = get_license_metadata(parent.license_type)
                    parent_name = parent_info.name if parent_info else parent.license_type

                    # Log share-alike enforcement before raising
                    audit = AuditLog.log(
                        action=AuditActions.LICENSE_SHARE_ALIKE_ENFORCED,
                        resource_type="design",
                        resource_id=design.id,
                        user_id=design.user_id,
                        context={
                            "parent_design_id": str(parent.id),
                            "parent_license": parent.license_type,
                            "attempted_license": license_type,
                        },
                    )
                    self.db.add(audit)

                    raise ValueError(
                        f"Share-alike license '{parent_name}' requires derivatives "
                        f"to use license '{parent.license_type}'"
                    )

    async def check_remix_allowed(
        self,
        design: Design,
        user: User,
    ) -> tuple[bool, str | None]:
        """Check whether a design can be remixed by a user.

        Evaluates the design's license to determine if remixing is permitted.
        Designs without a license default to allowing remixes.

        Args:
            design: The design to check.
            user: The user attempting to remix.

        Returns:
            A tuple of (allowed, reason). If not allowed, reason explains why.
        """
        # Own designs can always be remixed
        if design.user_id == user.id:
            return True, None

        # No license set — default to allowing remix
        if not design.license_type:
            return True, None

        can_remix = license_allows_remix(
            design.license_type,
            custom_allows_remix=design.custom_allows_remix,
        )

        if not can_remix:
            info = get_license_metadata(design.license_type)
            license_name = info.name if info else design.license_type
            reason = f"License '{license_name}' does not allow remixing"

            # Log blocked remix attempt
            audit = AuditLog.log(
                action=AuditActions.LICENSE_REMIX_BLOCKED,
                resource_type="design",
                resource_id=design.id,
                user_id=user.id,
                context={
                    "license_type": design.license_type,
                    "design_owner_id": str(design.user_id),
                },
            )
            self.db.add(audit)
            await self.db.flush()

            return False, reason

        return True, None

    async def build_attribution(
        self,
        parent_design: Design,
        parent_author: User,
    ) -> dict[str, Any]:
        """Build an attribution dict for a remix.

        Generates attribution metadata suitable for display in the UI
        and for embedding in exported files.

        Args:
            parent_design: The original design being remixed.
            parent_author: The author of the original design.

        Returns:
            Dictionary containing attribution details.
        """
        info = get_license_metadata(parent_design.license_type or "")
        license_name = info.name if info else None
        license_url = info.url if info else None
        requires_attribution = info.requires_attribution if info else False

        attribution: dict[str, Any] = {
            "parent_design_id": str(parent_design.id),
            "parent_design_name": parent_design.name,
            "parent_author_id": str(parent_author.id),
            "parent_author_name": parent_author.display_name or parent_author.email,
            "license_type": parent_design.license_type,
            "license_name": license_name,
            "license_url": license_url,
            "requires_attribution": requires_attribution,
        }

        # Log attribution generation
        audit = AuditLog.log(
            action=AuditActions.LICENSE_ATTRIBUTION_GENERATED,
            resource_type="design",
            resource_id=parent_design.id,
            context={
                "parent_design_id": str(parent_design.id),
                "parent_author_id": str(parent_author.id),
            },
        )
        self.db.add(audit)
        await self.db.flush()

        return attribution

    async def report_violation(
        self,
        design_id: UUID,
        reporter: User,
        violation_type: str,
        description: str,
        evidence_url: str | None = None,
    ) -> LicenseViolationReportResponse:
        """File a license violation report against a design.

        Creates a ContentReport with target_type of LICENSE_VIOLATION.

        Args:
            design_id: The design being reported.
            reporter: The user filing the report.
            violation_type: Type of violation from LicenseViolationType.
            description: Description of the violation.
            evidence_url: Optional URL to evidence.

        Returns:
            The created report as a response model.

        Raises:
            ValueError: If design not found, already reported, or invalid violation type.
        """
        # Validate design exists
        design = await self.db.get(Design, design_id)
        if not design or design.deleted_at is not None:
            raise ValueError("Design not found")

        # Validate violation type
        try:
            LicenseViolationType(violation_type)
        except ValueError:
            raise ValueError(f"Invalid violation type: {violation_type}")

        # Check for duplicate report
        stmt = select(ContentReport).where(
            ContentReport.reporter_id == reporter.id,
            ContentReport.target_type == ReportTargetType.LICENSE_VIOLATION,
            ContentReport.target_id == design_id,
        )
        result = await self.db.execute(stmt)
        if result.scalar_one_or_none():
            raise ValueError("You have already reported a license violation for this design")

        report = ContentReport(
            reporter_id=reporter.id,
            target_type=ReportTargetType.LICENSE_VIOLATION,
            target_id=design_id,
            reason=violation_type,
            description=description,
            evidence_url=evidence_url,
            status=ReportStatus.PENDING,
        )
        self.db.add(report)

        # Audit log
        audit = AuditLog.log(
            action=AuditActions.LICENSE_VIOLATION_REPORT,
            resource_type="design",
            resource_id=design_id,
            user_id=reporter.id,
            context={
                "violation_type": violation_type,
                "has_evidence": evidence_url is not None,
            },
        )
        self.db.add(audit)

        await self.db.commit()
        await self.db.refresh(report)

        return LicenseViolationReportResponse(
            id=report.id,
            design_id=design_id,
            violation_type=violation_type,
            status=report.status
            if isinstance(report.status, str)
            else report.status.value,
            created_at=report.created_at,
        )

    async def admin_takedown(
        self,
        design_id: UUID,
        admin_user: User,
        reason: str,
        violation_report_id: UUID | None = None,
    ) -> TakedownResponse:
        """Admin takedown of a design for licensing violations.

        Unpublishes the design and records the action in the audit log.

        Args:
            design_id: The design to take down.
            admin_user: The admin performing the takedown.
            reason: Reason for the takedown.
            violation_report_id: Optional linked violation report ID.

        Returns:
            TakedownResponse with details of the action.

        Raises:
            ValueError: If design not found or not published.
            PermissionError: If user is not an admin.
        """
        if admin_user.role != "admin":
            raise PermissionError("Only admins can perform takedowns")

        design = await self.db.get(Design, design_id)
        if not design or design.deleted_at is not None:
            raise ValueError("Design not found")

        if not design.is_public or design.published_at is None:
            raise ValueError("Design is not currently published")

        now = datetime.now(UTC)

        # Unpublish the design
        design.is_public = False
        design.published_at = None

        # If a violation report was referenced, mark it resolved
        if violation_report_id:
            report = await self.db.get(ContentReport, violation_report_id)
            if report:
                report.status = ReportStatus.RESOLVED.value
                report.resolved_by_id = admin_user.id
                report.resolved_at = now
                report.resolution_notes = reason
                report.action_taken = "takedown"

        # Audit log
        audit = AuditLog.log(
            action=AuditActions.LICENSE_TAKEDOWN,
            resource_type="design",
            resource_id=design_id,
            user_id=admin_user.id,
            context={
                "reason": reason,
                "violation_report_id": str(violation_report_id)
                if violation_report_id
                else None,
                "previous_license": design.license_type,
            },
        )
        self.db.add(audit)

        await self.db.commit()

        return TakedownResponse(
            design_id=design_id,
            unpublished_at=now,
            reason=reason,
            admin_id=admin_user.id,
        )

    async def get_user_published_licenses(
        self,
        user: User,
        license_type_filter: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> PaginatedPublishedLicensesResponse:
        """Get a paginated list of published designs with license info for a user.

        Args:
            user: The user whose published designs to retrieve.
            license_type_filter: Optional filter by license type.
            page: Page number (1-indexed).
            page_size: Number of items per page.

        Returns:
            Paginated response of published designs with license info.
        """
        base_query = select(Design).where(
            Design.user_id == user.id,
            Design.is_public.is_(True),
            Design.published_at.is_not(None),
            Design.deleted_at.is_(None),
        )
        count_query = select(func.count()).select_from(
            base_query.subquery()
        )

        if license_type_filter:
            base_query = base_query.where(Design.license_type == license_type_filter)
            count_query = select(func.count()).select_from(
                base_query.subquery()
            )

        total_result = await self.db.execute(count_query)
        total = total_result.scalar() or 0
        total_pages = max(1, math.ceil(total / page_size))

        offset = (page - 1) * page_size
        items_query = (
            base_query.order_by(Design.published_at.desc())
            .offset(offset)
            .limit(page_size)
        )
        result = await self.db.execute(items_query)
        designs = result.scalars().all()

        items = []
        for d in designs:
            info = get_license_metadata(d.license_type or "")
            items.append(
                PublishedLicenseItem(
                    design_id=d.id,
                    design_name=d.name,
                    license_type=d.license_type,
                    license_name=info.name if info else None,
                    published_at=d.published_at,
                    remix_count=d.remix_count,
                )
            )

        return PaginatedPublishedLicensesResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
            has_next=page < total_pages,
            has_prev=page > 1,
        )

    async def get_user_remixed_licenses(
        self,
        user: User,
        license_type_filter: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> PaginatedRemixedLicensesResponse:
        """Get a paginated list of remixed designs for a user.

        Args:
            user: The user whose remixed designs to retrieve.
            license_type_filter: Optional filter by parent license type.
            page: Page number (1-indexed).
            page_size: Number of items per page.

        Returns:
            Paginated response of remixed designs with parent license info.
        """
        # Alias for parent design
        ParentDesign = Design.__table__.alias("parent_design")

        base_query = select(Design).where(
            Design.user_id == user.id,
            Design.remixed_from_id.is_not(None),
            Design.deleted_at.is_(None),
        )

        if license_type_filter:
            # Filter by parent's license type by joining
            base_query = base_query.join(
                ParentDesign,
                Design.remixed_from_id == ParentDesign.c.id,
            ).where(ParentDesign.c.license_type == license_type_filter)

        count_query = select(func.count()).select_from(base_query.subquery())
        total_result = await self.db.execute(count_query)
        total = total_result.scalar() or 0
        total_pages = max(1, math.ceil(total / page_size))

        offset = (page - 1) * page_size
        items_query = (
            base_query.order_by(Design.created_at.desc())
            .offset(offset)
            .limit(page_size)
        )
        result = await self.db.execute(items_query)
        designs = result.scalars().all()

        items = []
        for d in designs:
            parent = await self.db.get(Design, d.remixed_from_id) if d.remixed_from_id else None
            parent_info = get_license_metadata(parent.license_type or "") if parent else None

            items.append(
                RemixedLicenseItem(
                    design_id=d.id,
                    design_name=d.name,
                    license_type=d.license_type,
                    parent_design_id=d.remixed_from_id,
                    parent_design_name=parent.name if parent else None,
                    parent_license_type=parent.license_type if parent else None,
                    requires_attribution=parent_info.requires_attribution if parent_info else False,
                    created_at=d.created_at,
                )
            )

        return PaginatedRemixedLicensesResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
            has_next=page < total_pages,
            has_prev=page > 1,
        )

    def get_license_detail(self, design: Design) -> LicenseDetailResponse:
        """Build a LicenseDetailResponse for a design.

        Resolves the license metadata from the catalog and includes
        custom license text when applicable.

        Args:
            design: The design to get license detail for.

        Returns:
            LicenseDetailResponse with resolved license metadata.
        """
        if not design.license_type:
            return LicenseDetailResponse(license_type=None)

        info = get_license_metadata(design.license_type)
        if info is None:
            return LicenseDetailResponse(license_type=design.license_type)

        effective_allows_remix = (
            design.custom_allows_remix
            if design.license_type == LicenseType.CUSTOM
            else info.allows_remix
        )

        return LicenseDetailResponse(
            license_type=design.license_type,
            license_name=info.name,
            license_url=info.url,
            allows_remix=effective_allows_remix,
            requires_attribution=info.requires_attribution,
            allows_commercial=info.allows_commercial,
            requires_share_alike=info.requires_share_alike,
            custom_license_text=(
                design.custom_license_text
                if design.license_type == LicenseType.CUSTOM
                else None
            ),
            icon=info.icon,
        )
