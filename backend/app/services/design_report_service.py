"""Design report service for content moderation.

Provides functionality for users to report marketplace designs
that violate community guidelines.
"""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.rating import ContentReport, ReportStatus, ReportTargetType
from app.models.user import User
from app.schemas.rating import DesignReportCreate, DesignReportResponse, DesignReportStatus


class DesignReportService:
    """Service for managing design reports.

    Wraps the existing ContentReport model for design-specific reporting.
    """

    def __init__(self, db: AsyncSession) -> None:
        """Initialize the service.

        Args:
            db: Async database session.
        """
        self.db = db

    async def create_report(
        self,
        design_id: UUID,
        user: User,
        data: DesignReportCreate,
    ) -> DesignReportResponse:
        """Report a design for content moderation.

        Args:
            design_id: The design being reported.
            user: The reporting user.
            data: Report reason and optional description.

        Returns:
            The created report.

        Raises:
            ValueError: If already reported by this user.
        """
        # Check for duplicate report
        existing = await self._get_existing_report(design_id, user.id)
        if existing:
            raise ValueError("You have already reported this design")

        report = ContentReport(
            reporter_id=user.id,
            target_type=ReportTargetType.DESIGN,
            target_id=design_id,
            reason=data.reason,
            description=data.description,
            status=ReportStatus.PENDING,
        )
        self.db.add(report)
        await self.db.commit()
        await self.db.refresh(report)

        return DesignReportResponse(
            id=report.id,
            status=(
                report.status.value
                if hasattr(report.status, "value")
                else str(report.status)
            ),
            created_at=report.created_at,
        )

    async def check_report_status(
        self, design_id: UUID, user_id: UUID
    ) -> DesignReportStatus:
        """Check if a user has already reported a design.

        Args:
            design_id: The design ID.
            user_id: The user ID.

        Returns:
            Report status indicating if already reported.
        """
        existing = await self._get_existing_report(design_id, user_id)
        return DesignReportStatus(already_reported=existing is not None)

    async def _get_existing_report(
        self, design_id: UUID, user_id: UUID
    ) -> ContentReport | None:
        """Get existing report by user for a design.

        Args:
            design_id: The design ID.
            user_id: The user ID.

        Returns:
            The existing report or None.
        """
        stmt = select(ContentReport).where(
            ContentReport.reporter_id == user_id,
            ContentReport.target_type == ReportTargetType.DESIGN,
            ContentReport.target_id == design_id,
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
