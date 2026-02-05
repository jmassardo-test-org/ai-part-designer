"""
Service layer for rating and community features.

Handles template ratings, feedback, comments, reports, and moderation.
"""

from collections.abc import Sequence
from datetime import datetime, timedelta
from uuid import UUID

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.rating import (
    ContentReport,
    FeedbackType,
    ReportStatus,
    TemplateComment,
    TemplateFeedback,
    TemplateRating,
    UserBan,
)
from app.models.template import Template
from app.schemas.rating import (
    BanCreate,
    CommentCreate,
    CommentUpdate,
    ModerationStats,
    ReportCreate,
    ReportResolve,
    TemplateFeedbackCreate,
    TemplateFeedbackSummary,
    TemplateRatingCreate,
    TemplateRatingSummary,
)


class RatingService:
    """Service for template ratings."""

    def __init__(self, db: AsyncSession):
        """Initialize rating service.

        Args:
            db: Async database session.
        """
        self.db = db

    async def rate_template(
        self,
        template_id: UUID,
        user_id: UUID,
        data: TemplateRatingCreate,
    ) -> TemplateRating:
        """Create or update a template rating.

        Args:
            template_id: Template to rate.
            user_id: User rating the template.
            data: Rating data.

        Returns:
            Created or updated rating.
        """
        # Check for existing rating
        stmt = select(TemplateRating).where(
            and_(
                TemplateRating.template_id == template_id,
                TemplateRating.user_id == user_id,
            )
        )
        result = await self.db.execute(stmt)
        existing = result.scalar_one_or_none()

        if existing:
            # Update existing rating
            existing.rating = data.rating
            existing.review = data.review
            rating = existing
        else:
            # Create new rating
            rating = TemplateRating(
                template_id=template_id,
                user_id=user_id,
                rating=data.rating,
                review=data.review,
            )
            self.db.add(rating)

        await self.db.flush()

        # Update template average rating
        await self._update_template_avg_rating(template_id)

        return rating

    async def get_user_rating(
        self,
        template_id: UUID,
        user_id: UUID,
    ) -> TemplateRating | None:
        """Get user's rating for a template.

        Args:
            template_id: Template ID.
            user_id: User ID.

        Returns:
            Rating or None if not rated.
        """
        stmt = select(TemplateRating).where(
            and_(
                TemplateRating.template_id == template_id,
                TemplateRating.user_id == user_id,
            )
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_template_ratings(
        self,
        template_id: UUID,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[Sequence[TemplateRating], int]:
        """Get ratings for a template with pagination.

        Args:
            template_id: Template ID.
            limit: Maximum results.
            offset: Offset for pagination.

        Returns:
            Tuple of (ratings, total_count).
        """
        # Get ratings with user info
        stmt = (
            select(TemplateRating)
            .where(TemplateRating.template_id == template_id)
            .options(selectinload(TemplateRating.user))
            .order_by(TemplateRating.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self.db.execute(stmt)
        ratings = result.scalars().all()

        # Get total count
        count_stmt = (
            select(func.count())
            .select_from(TemplateRating)
            .where(TemplateRating.template_id == template_id)
        )
        count_result = await self.db.execute(count_stmt)
        total = count_result.scalar() or 0

        return ratings, total

    async def get_rating_summary(self, template_id: UUID) -> TemplateRatingSummary:
        """Get rating summary for a template.

        Args:
            template_id: Template ID.

        Returns:
            Rating summary with distribution.
        """
        # Get average and count
        stmt = select(
            func.avg(TemplateRating.rating).label("avg"),
            func.count().label("total"),
        ).where(TemplateRating.template_id == template_id)
        result = await self.db.execute(stmt)
        row = result.one()

        avg_rating = float(row.avg) if row.avg else 0.0
        total = row.total or 0

        # Get distribution
        dist_stmt = (
            select(
                TemplateRating.rating,
                func.count().label("count"),
            )
            .where(TemplateRating.template_id == template_id)
            .group_by(TemplateRating.rating)
        )
        dist_result = await self.db.execute(dist_stmt)
        distribution = dict.fromkeys(range(1, 6), 0)
        for row in dist_result:
            distribution[row.rating] = row.count

        return TemplateRatingSummary(
            template_id=template_id,
            average_rating=round(avg_rating, 2),
            total_ratings=total,
            rating_distribution=distribution,
        )

    async def delete_rating(self, template_id: UUID, user_id: UUID) -> bool:
        """Delete a user's rating.

        Args:
            template_id: Template ID.
            user_id: User ID.

        Returns:
            True if deleted, False if not found.
        """
        stmt = select(TemplateRating).where(
            and_(
                TemplateRating.template_id == template_id,
                TemplateRating.user_id == user_id,
            )
        )
        result = await self.db.execute(stmt)
        rating = result.scalar_one_or_none()

        if not rating:
            return False

        await self.db.delete(rating)
        await self._update_template_avg_rating(template_id)
        return True

    async def _update_template_avg_rating(self, template_id: UUID) -> None:
        """Update template's cached average rating.

        Args:
            template_id: Template ID.
        """
        stmt = select(func.avg(TemplateRating.rating)).where(
            TemplateRating.template_id == template_id
        )
        result = await self.db.execute(stmt)
        avg = result.scalar()

        # Update template
        template_stmt = select(Template).where(Template.id == template_id)
        template_result = await self.db.execute(template_stmt)
        template = template_result.scalar_one_or_none()

        if template:
            template.avg_rating = float(avg) if avg else None


class FeedbackService:
    """Service for template feedback (thumbs up/down)."""

    def __init__(self, db: AsyncSession):
        """Initialize feedback service.

        Args:
            db: Async database session.
        """
        self.db = db

    async def set_feedback(
        self,
        template_id: UUID,
        user_id: UUID,
        data: TemplateFeedbackCreate,
    ) -> TemplateFeedback:
        """Set feedback for a template.

        Args:
            template_id: Template ID.
            user_id: User ID.
            data: Feedback data.

        Returns:
            Created or updated feedback.
        """
        stmt = select(TemplateFeedback).where(
            and_(
                TemplateFeedback.template_id == template_id,
                TemplateFeedback.user_id == user_id,
            )
        )
        result = await self.db.execute(stmt)
        existing = result.scalar_one_or_none()

        if existing:
            existing.feedback_type = data.feedback_type
            feedback = existing
        else:
            feedback = TemplateFeedback(
                template_id=template_id,
                user_id=user_id,
                feedback_type=data.feedback_type,
            )
            self.db.add(feedback)

        await self.db.flush()
        return feedback

    async def remove_feedback(self, template_id: UUID, user_id: UUID) -> bool:
        """Remove user's feedback for a template.

        Args:
            template_id: Template ID.
            user_id: User ID.

        Returns:
            True if removed, False if not found.
        """
        stmt = select(TemplateFeedback).where(
            and_(
                TemplateFeedback.template_id == template_id,
                TemplateFeedback.user_id == user_id,
            )
        )
        result = await self.db.execute(stmt)
        feedback = result.scalar_one_or_none()

        if not feedback:
            return False

        await self.db.delete(feedback)
        return True

    async def get_feedback_summary(
        self,
        template_id: UUID,
        user_id: UUID | None = None,
    ) -> TemplateFeedbackSummary:
        """Get feedback summary for a template.

        Args:
            template_id: Template ID.
            user_id: Optional user ID to include their feedback.

        Returns:
            Feedback summary.
        """
        # Count thumbs up
        up_stmt = (
            select(func.count())
            .select_from(TemplateFeedback)
            .where(
                and_(
                    TemplateFeedback.template_id == template_id,
                    TemplateFeedback.feedback_type == FeedbackType.THUMBS_UP.value,
                )
            )
        )
        up_result = await self.db.execute(up_stmt)
        thumbs_up = up_result.scalar() or 0

        # Count thumbs down
        down_stmt = (
            select(func.count())
            .select_from(TemplateFeedback)
            .where(
                and_(
                    TemplateFeedback.template_id == template_id,
                    TemplateFeedback.feedback_type == FeedbackType.THUMBS_DOWN.value,
                )
            )
        )
        down_result = await self.db.execute(down_stmt)
        thumbs_down = down_result.scalar() or 0

        # Get user's feedback if requested
        user_feedback = None
        if user_id:
            user_stmt = select(TemplateFeedback.feedback_type).where(
                and_(
                    TemplateFeedback.template_id == template_id,
                    TemplateFeedback.user_id == user_id,
                )
            )
            user_result = await self.db.execute(user_stmt)
            user_feedback = user_result.scalar_one_or_none()

        return TemplateFeedbackSummary(
            template_id=template_id,
            thumbs_up=thumbs_up,
            thumbs_down=thumbs_down,
            user_feedback=user_feedback,
        )


class CommentService:
    """Service for template comments."""

    def __init__(self, db: AsyncSession):
        """Initialize comment service.

        Args:
            db: Async database session.
        """
        self.db = db

    async def create_comment(
        self,
        template_id: UUID,
        user_id: UUID,
        data: CommentCreate,
    ) -> TemplateComment:
        """Create a new comment.

        Args:
            template_id: Template ID.
            user_id: User ID.
            data: Comment data.

        Returns:
            Created comment.
        """
        comment = TemplateComment(
            template_id=template_id,
            user_id=user_id,
            content=data.content,
            parent_id=data.parent_id,
        )
        self.db.add(comment)
        await self.db.flush()
        return comment

    async def update_comment(
        self,
        comment_id: UUID,
        user_id: UUID,
        data: CommentUpdate,
    ) -> TemplateComment | None:
        """Update a comment.

        Args:
            comment_id: Comment ID.
            user_id: User ID (must match comment author).
            data: Update data.

        Returns:
            Updated comment or None if not found/unauthorized.
        """
        stmt = select(TemplateComment).where(
            and_(
                TemplateComment.id == comment_id,
                TemplateComment.user_id == user_id,
            )
        )
        result = await self.db.execute(stmt)
        comment = result.scalar_one_or_none()

        if not comment:
            return None

        comment.content = data.content
        comment.is_edited = True
        comment.edited_at = datetime.utcnow()

        await self.db.flush()
        return comment

    async def delete_comment(
        self,
        comment_id: UUID,
        user_id: UUID,
        is_admin: bool = False,
    ) -> bool:
        """Delete a comment.

        Args:
            comment_id: Comment ID.
            user_id: User ID.
            is_admin: Whether user is an admin (can delete any comment).

        Returns:
            True if deleted, False if not found/unauthorized.
        """
        if is_admin:
            stmt = select(TemplateComment).where(TemplateComment.id == comment_id)
        else:
            stmt = select(TemplateComment).where(
                and_(
                    TemplateComment.id == comment_id,
                    TemplateComment.user_id == user_id,
                )
            )

        result = await self.db.execute(stmt)
        comment = result.scalar_one_or_none()

        if not comment:
            return False

        await self.db.delete(comment)
        return True

    async def get_template_comments(
        self,
        template_id: UUID,
        include_hidden: bool = False,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[Sequence[TemplateComment], int]:
        """Get comments for a template.

        Args:
            template_id: Template ID.
            include_hidden: Include hidden comments (for admins).
            limit: Maximum results.
            offset: Offset for pagination.

        Returns:
            Tuple of (comments, total_count).
        """
        # Build query
        conditions = [
            TemplateComment.template_id == template_id,
            TemplateComment.parent_id.is_(None),  # Only top-level comments
        ]
        if not include_hidden:
            conditions.append(not TemplateComment.is_hidden)

        stmt = (
            select(TemplateComment)
            .where(and_(*conditions))
            .options(selectinload(TemplateComment.user))
            .order_by(TemplateComment.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self.db.execute(stmt)
        comments = result.scalars().all()

        # Get total count
        count_stmt = select(func.count()).select_from(TemplateComment).where(and_(*conditions))
        count_result = await self.db.execute(count_stmt)
        total = count_result.scalar() or 0

        return comments, total

    async def get_comment_replies(
        self,
        comment_id: UUID,
        include_hidden: bool = False,
    ) -> Sequence[TemplateComment]:
        """Get replies to a comment.

        Args:
            comment_id: Parent comment ID.
            include_hidden: Include hidden replies.

        Returns:
            List of reply comments.
        """
        conditions = [TemplateComment.parent_id == comment_id]
        if not include_hidden:
            conditions.append(not TemplateComment.is_hidden)

        stmt = (
            select(TemplateComment)
            .where(and_(*conditions))
            .options(selectinload(TemplateComment.user))
            .order_by(TemplateComment.created_at.asc())
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def hide_comment(
        self,
        comment_id: UUID,
        moderator_id: UUID,
        reason: str | None = None,
    ) -> TemplateComment | None:
        """Hide a comment (moderation).

        Args:
            comment_id: Comment ID.
            moderator_id: Moderator user ID.
            reason: Reason for hiding.

        Returns:
            Updated comment or None if not found.
        """
        stmt = select(TemplateComment).where(TemplateComment.id == comment_id)
        result = await self.db.execute(stmt)
        comment = result.scalar_one_or_none()

        if not comment:
            return None

        comment.is_hidden = True
        comment.hidden_by_id = moderator_id
        comment.hidden_at = datetime.utcnow()
        comment.hidden_reason = reason

        await self.db.flush()
        return comment

    async def unhide_comment(self, comment_id: UUID) -> TemplateComment | None:
        """Unhide a comment.

        Args:
            comment_id: Comment ID.

        Returns:
            Updated comment or None if not found.
        """
        stmt = select(TemplateComment).where(TemplateComment.id == comment_id)
        result = await self.db.execute(stmt)
        comment = result.scalar_one_or_none()

        if not comment:
            return None

        comment.is_hidden = False
        comment.hidden_by_id = None
        comment.hidden_at = None
        comment.hidden_reason = None

        await self.db.flush()
        return comment

    async def get_reply_count(self, comment_id: UUID) -> int:
        """Get number of replies to a comment.

        Args:
            comment_id: Parent comment ID.

        Returns:
            Number of visible replies.
        """
        stmt = (
            select(func.count())
            .select_from(TemplateComment)
            .where(
                and_(
                    TemplateComment.parent_id == comment_id,
                    not TemplateComment.is_hidden,
                )
            )
        )
        result = await self.db.execute(stmt)
        return result.scalar() or 0


class ReportService:
    """Service for content reports."""

    def __init__(self, db: AsyncSession):
        """Initialize report service.

        Args:
            db: Async database session.
        """
        self.db = db

    async def create_report(
        self,
        reporter_id: UUID,
        data: ReportCreate,
    ) -> ContentReport:
        """Create a content report.

        Args:
            reporter_id: User filing the report.
            data: Report data.

        Returns:
            Created report.
        """
        report = ContentReport(
            reporter_id=reporter_id,
            target_type=data.target_type,
            target_id=data.target_id,
            reason=data.reason,
            description=data.description,
            status=ReportStatus.PENDING.value,
        )
        self.db.add(report)
        await self.db.flush()
        return report

    async def get_report(self, report_id: UUID) -> ContentReport | None:
        """Get a report by ID.

        Args:
            report_id: Report ID.

        Returns:
            Report or None.
        """
        stmt = select(ContentReport).where(ContentReport.id == report_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_pending_reports(
        self,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[Sequence[ContentReport], int]:
        """Get pending reports for moderation queue.

        Args:
            limit: Maximum results.
            offset: Offset for pagination.

        Returns:
            Tuple of (reports, total_count).
        """
        stmt = (
            select(ContentReport)
            .where(ContentReport.status == ReportStatus.PENDING.value)
            .options(selectinload(ContentReport.reporter))
            .order_by(ContentReport.created_at.asc())
            .limit(limit)
            .offset(offset)
        )
        result = await self.db.execute(stmt)
        reports = result.scalars().all()

        count_stmt = (
            select(func.count())
            .select_from(ContentReport)
            .where(ContentReport.status == ReportStatus.PENDING.value)
        )
        count_result = await self.db.execute(count_stmt)
        total = count_result.scalar() or 0

        return reports, total

    async def resolve_report(
        self,
        report_id: UUID,
        moderator_id: UUID,
        data: ReportResolve,
    ) -> ContentReport | None:
        """Resolve a report.

        Args:
            report_id: Report ID.
            moderator_id: Moderator resolving the report.
            data: Resolution data.

        Returns:
            Updated report or None if not found.
        """
        report = await self.get_report(report_id)
        if not report:
            return None

        report.status = ReportStatus.RESOLVED.value
        report.resolved_by_id = moderator_id
        report.resolved_at = datetime.utcnow()
        report.resolution_notes = data.resolution_notes
        report.action_taken = data.action

        await self.db.flush()
        return report

    async def dismiss_report(
        self,
        report_id: UUID,
        moderator_id: UUID,
        notes: str | None = None,
    ) -> ContentReport | None:
        """Dismiss a report.

        Args:
            report_id: Report ID.
            moderator_id: Moderator dismissing the report.
            notes: Optional notes.

        Returns:
            Updated report or None if not found.
        """
        report = await self.get_report(report_id)
        if not report:
            return None

        report.status = ReportStatus.DISMISSED.value
        report.resolved_by_id = moderator_id
        report.resolved_at = datetime.utcnow()
        report.resolution_notes = notes
        report.action_taken = "dismiss"

        await self.db.flush()
        return report

    async def get_user_report_count(self, user_id: UUID) -> int:
        """Get number of reports filed by a user.

        Args:
            user_id: User ID.

        Returns:
            Number of reports.
        """
        stmt = (
            select(func.count())
            .select_from(ContentReport)
            .where(ContentReport.reporter_id == user_id)
        )
        result = await self.db.execute(stmt)
        return result.scalar() or 0


class BanService:
    """Service for user bans."""

    def __init__(self, db: AsyncSession):
        """Initialize ban service.

        Args:
            db: Async database session.
        """
        self.db = db

    async def ban_user(
        self,
        admin_id: UUID,
        data: BanCreate,
    ) -> UserBan:
        """Ban a user.

        Args:
            admin_id: Admin performing the ban.
            data: Ban data.

        Returns:
            Created ban.
        """
        expires_at = None
        if not data.is_permanent and data.duration_days:
            expires_at = datetime.utcnow() + timedelta(days=data.duration_days)

        ban = UserBan(
            user_id=data.user_id,
            reason=data.reason,
            banned_by_id=admin_id,
            is_permanent=data.is_permanent,
            expires_at=expires_at,
            is_active=True,
            related_report_id=data.related_report_id,
        )
        self.db.add(ban)
        await self.db.flush()
        return ban

    async def unban_user(
        self,
        ban_id: UUID,
        admin_id: UUID,
        reason: str,
    ) -> UserBan | None:
        """Unban a user.

        Args:
            ban_id: Ban ID.
            admin_id: Admin performing the unban.
            reason: Reason for unbanning.

        Returns:
            Updated ban or None if not found.
        """
        stmt = select(UserBan).where(UserBan.id == ban_id)
        result = await self.db.execute(stmt)
        ban = result.scalar_one_or_none()

        if not ban:
            return None

        ban.is_active = False
        ban.unbanned_by_id = admin_id
        ban.unbanned_at = datetime.utcnow()
        ban.unban_reason = reason

        await self.db.flush()
        return ban

    async def get_active_ban(self, user_id: UUID) -> UserBan | None:
        """Get active ban for a user.

        Args:
            user_id: User ID.

        Returns:
            Active ban or None.
        """
        stmt = (
            select(UserBan)
            .where(
                and_(
                    UserBan.user_id == user_id,
                    UserBan.is_active,
                )
            )
            .order_by(UserBan.created_at.desc())
        )
        result = await self.db.execute(stmt)
        ban = result.scalar_one_or_none()

        # Check if expired
        if ban and not ban.is_permanent and ban.expires_at:
            if datetime.utcnow() > ban.expires_at:
                # Auto-expire the ban
                ban.is_active = False
                await self.db.flush()
                return None

        return ban

    async def is_user_banned(self, user_id: UUID) -> bool:
        """Check if a user is currently banned.

        Args:
            user_id: User ID.

        Returns:
            True if banned, False otherwise.
        """
        ban = await self.get_active_ban(user_id)
        return ban is not None

    async def get_active_bans(
        self,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[Sequence[UserBan], int]:
        """Get all active bans.

        Args:
            limit: Maximum results.
            offset: Offset for pagination.

        Returns:
            Tuple of (bans, total_count).
        """
        stmt = (
            select(UserBan)
            .where(UserBan.is_active)
            .options(selectinload(UserBan.user))
            .order_by(UserBan.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self.db.execute(stmt)
        bans = result.scalars().all()

        count_stmt = select(func.count()).select_from(UserBan).where(UserBan.is_active)
        count_result = await self.db.execute(count_stmt)
        total = count_result.scalar() or 0

        return bans, total

    async def get_user_ban_history(self, user_id: UUID) -> Sequence[UserBan]:
        """Get ban history for a user.

        Args:
            user_id: User ID.

        Returns:
            List of bans.
        """
        stmt = select(UserBan).where(UserBan.user_id == user_id).order_by(UserBan.created_at.desc())
        result = await self.db.execute(stmt)
        return result.scalars().all()


class ModerationService:
    """Service for moderation dashboard and stats."""

    def __init__(self, db: AsyncSession):
        """Initialize moderation service.

        Args:
            db: Async database session.
        """
        self.db = db
        self.report_service = ReportService(db)
        self.ban_service = BanService(db)
        self.comment_service = CommentService(db)

    async def get_moderation_stats(self) -> ModerationStats:
        """Get moderation dashboard statistics.

        Returns:
            Moderation stats.
        """
        # Pending reports
        pending_stmt = (
            select(func.count())
            .select_from(ContentReport)
            .where(ContentReport.status == ReportStatus.PENDING.value)
        )
        pending_result = await self.db.execute(pending_stmt)
        pending_reports = pending_result.scalar() or 0

        # Reports today
        today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        today_stmt = (
            select(func.count()).select_from(ContentReport).where(ContentReport.created_at >= today)
        )
        today_result = await self.db.execute(today_stmt)
        reports_today = today_result.scalar() or 0

        # Reports this week
        week_ago = today - timedelta(days=7)
        week_stmt = (
            select(func.count())
            .select_from(ContentReport)
            .where(ContentReport.created_at >= week_ago)
        )
        week_result = await self.db.execute(week_stmt)
        reports_this_week = week_result.scalar() or 0

        # Active bans
        bans_stmt = select(func.count()).select_from(UserBan).where(UserBan.is_active)
        bans_result = await self.db.execute(bans_stmt)
        active_bans = bans_result.scalar() or 0

        # Hidden comments
        hidden_stmt = (
            select(func.count()).select_from(TemplateComment).where(TemplateComment.is_hidden)
        )
        hidden_result = await self.db.execute(hidden_stmt)
        hidden_comments = hidden_result.scalar() or 0

        return ModerationStats(
            pending_reports=pending_reports,
            reports_today=reports_today,
            reports_this_week=reports_this_week,
            active_bans=active_bans,
            hidden_comments=hidden_comments,
        )
