"""
Tests for rating and community models.

Tests TemplateRating, TemplateFeedback, TemplateComment, ContentReport, and UserBan.
"""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from app.models.rating import (
    ContentReport,
    FeedbackType,
    ReportReason,
    ReportStatus,
    ReportTargetType,
    TemplateComment,
    TemplateFeedback,
    TemplateRating,
    UserBan,
)


class TestTemplateRating:
    """Tests for TemplateRating model."""

    def test_create_rating_with_required_fields(self) -> None:
        """Test creating a rating with required fields."""
        template_id = uuid4()
        user_id = uuid4()

        rating = TemplateRating(
            template_id=template_id,
            user_id=user_id,
            rating=5,
        )

        assert rating.template_id == template_id
        assert rating.user_id == user_id
        assert rating.rating == 5
        assert rating.review is None

    def test_create_rating_with_review(self) -> None:
        """Test creating a rating with optional review."""
        rating = TemplateRating(
            template_id=uuid4(),
            user_id=uuid4(),
            rating=4,
            review="Great template!",
        )

        assert rating.rating == 4
        assert rating.review == "Great template!"

    def test_rating_repr(self) -> None:
        """Test rating string representation."""
        template_id = uuid4()
        user_id = uuid4()

        rating = TemplateRating(
            template_id=template_id,
            user_id=user_id,
            rating=3,
        )

        repr_str = repr(rating)
        assert "TemplateRating" in repr_str
        assert str(template_id) in repr_str


class TestTemplateFeedback:
    """Tests for TemplateFeedback model."""

    def test_create_thumbs_up_feedback(self) -> None:
        """Test creating thumbs up feedback."""
        feedback = TemplateFeedback(
            template_id=uuid4(),
            user_id=uuid4(),
            feedback_type=FeedbackType.THUMBS_UP.value,
        )

        assert feedback.feedback_type == "thumbs_up"

    def test_create_thumbs_down_feedback(self) -> None:
        """Test creating thumbs down feedback."""
        feedback = TemplateFeedback(
            template_id=uuid4(),
            user_id=uuid4(),
            feedback_type=FeedbackType.THUMBS_DOWN.value,
        )

        assert feedback.feedback_type == "thumbs_down"

    def test_feedback_repr(self) -> None:
        """Test feedback string representation."""
        feedback = TemplateFeedback(
            template_id=uuid4(),
            user_id=uuid4(),
            feedback_type=FeedbackType.THUMBS_UP.value,
        )

        assert "TemplateFeedback" in repr(feedback)


class TestTemplateComment:
    """Tests for TemplateComment model."""

    def test_create_top_level_comment(self) -> None:
        """Test creating a top-level comment."""
        comment = TemplateComment(
            template_id=uuid4(),
            user_id=uuid4(),
            content="This is a great template!",
            is_hidden=False,
            is_edited=False,
        )

        assert comment.content == "This is a great template!"
        assert comment.parent_id is None
        assert comment.is_hidden is False
        assert comment.is_edited is False

    def test_create_reply_comment(self) -> None:
        """Test creating a reply comment."""
        parent_id = uuid4()

        comment = TemplateComment(
            template_id=uuid4(),
            user_id=uuid4(),
            content="I agree!",
            parent_id=parent_id,
        )

        assert comment.parent_id == parent_id

    def test_comment_with_moderation_fields(self) -> None:
        """Test comment with moderation status."""
        moderator_id = uuid4()
        hidden_at = datetime.now(tz=UTC)

        comment = TemplateComment(
            template_id=uuid4(),
            user_id=uuid4(),
            content="Hidden comment",
            is_hidden=True,
            hidden_by_id=moderator_id,
            hidden_at=hidden_at,
            hidden_reason="Spam content",
        )

        assert comment.is_hidden is True
        assert comment.hidden_by_id == moderator_id
        assert comment.hidden_reason == "Spam content"

    def test_edited_comment(self) -> None:
        """Test edited comment fields."""
        edited_at = datetime.now(tz=UTC)

        comment = TemplateComment(
            template_id=uuid4(),
            user_id=uuid4(),
            content="Updated content",
            is_edited=True,
            edited_at=edited_at,
        )

        assert comment.is_edited is True
        assert comment.edited_at == edited_at

    def test_comment_repr(self) -> None:
        """Test comment string representation."""
        comment = TemplateComment(
            template_id=uuid4(),
            user_id=uuid4(),
            content="Test",
        )

        assert "TemplateComment" in repr(comment)


class TestContentReport:
    """Tests for ContentReport model."""

    def test_create_template_report(self) -> None:
        """Test creating a template report."""
        report = ContentReport(
            reporter_id=uuid4(),
            target_type=ReportTargetType.TEMPLATE.value,
            target_id=uuid4(),
            reason=ReportReason.SPAM.value,
            status=ReportStatus.PENDING.value,  # Set explicitly since DB default
        )

        assert report.target_type == "template"
        assert report.reason == "spam"
        assert report.status == ReportStatus.PENDING.value
        assert report.description is None

    def test_create_comment_report_with_description(self) -> None:
        """Test creating a comment report with description."""
        report = ContentReport(
            reporter_id=uuid4(),
            target_type=ReportTargetType.COMMENT.value,
            target_id=uuid4(),
            reason=ReportReason.OFFENSIVE.value,
            description="Contains offensive language",
        )

        assert report.target_type == "comment"
        assert report.reason == "offensive"
        assert report.description == "Contains offensive language"

    def test_resolved_report(self) -> None:
        """Test report with resolution details."""
        moderator_id = uuid4()
        resolved_at = datetime.now(tz=UTC)

        report = ContentReport(
            reporter_id=uuid4(),
            target_type=ReportTargetType.USER.value,
            target_id=uuid4(),
            reason=ReportReason.INAPPROPRIATE.value,
            status=ReportStatus.RESOLVED.value,
            resolved_by_id=moderator_id,
            resolved_at=resolved_at,
            resolution_notes="Content removed",
            action_taken="remove_content",
        )

        assert report.status == "resolved"
        assert report.resolved_by_id == moderator_id
        assert report.action_taken == "remove_content"

    def test_report_reasons(self) -> None:
        """Test all report reason values."""
        assert ReportReason.SPAM.value == "spam"
        assert ReportReason.INAPPROPRIATE.value == "inappropriate"
        assert ReportReason.COPYRIGHT.value == "copyright"
        assert ReportReason.MISLEADING.value == "misleading"
        assert ReportReason.OFFENSIVE.value == "offensive"
        assert ReportReason.OTHER.value == "other"

    def test_report_statuses(self) -> None:
        """Test all report status values."""
        assert ReportStatus.PENDING.value == "pending"
        assert ReportStatus.REVIEWING.value == "reviewing"
        assert ReportStatus.RESOLVED.value == "resolved"
        assert ReportStatus.DISMISSED.value == "dismissed"

    def test_report_repr(self) -> None:
        """Test report string representation."""
        report = ContentReport(
            reporter_id=uuid4(),
            target_type="template",
            target_id=uuid4(),
            reason="spam",
        )

        assert "ContentReport" in repr(report)


class TestUserBan:
    """Tests for UserBan model."""

    def test_create_temporary_ban(self) -> None:
        """Test creating a temporary ban."""
        expires_at = datetime.now(tz=UTC) + timedelta(days=7)

        ban = UserBan(
            user_id=uuid4(),
            reason="Repeated spam violations",
            banned_by_id=uuid4(),
            is_permanent=False,
            expires_at=expires_at,
            is_active=True,  # Set explicitly since DB default
        )

        assert ban.is_permanent is False
        assert ban.expires_at == expires_at
        assert ban.is_active is True

    def test_create_permanent_ban(self) -> None:
        """Test creating a permanent ban."""
        ban = UserBan(
            user_id=uuid4(),
            reason="Severe policy violations",
            banned_by_id=uuid4(),
            is_permanent=True,
        )

        assert ban.is_permanent is True
        assert ban.expires_at is None

    def test_ban_with_related_report(self) -> None:
        """Test ban linked to a report."""
        report_id = uuid4()

        ban = UserBan(
            user_id=uuid4(),
            reason="Based on user report",
            banned_by_id=uuid4(),
            related_report_id=report_id,
        )

        assert ban.related_report_id == report_id

    def test_unbanned_user(self) -> None:
        """Test unban fields."""
        unbanned_by = uuid4()
        unbanned_at = datetime.now(tz=UTC)

        ban = UserBan(
            user_id=uuid4(),
            reason="Original reason",
            banned_by_id=uuid4(),
            is_active=False,
            unbanned_by_id=unbanned_by,
            unbanned_at=unbanned_at,
            unban_reason="Appeal accepted",
        )

        assert ban.is_active is False
        assert ban.unbanned_by_id == unbanned_by
        assert ban.unban_reason == "Appeal accepted"

    def test_is_expired_permanent_ban(self) -> None:
        """Test is_expired for permanent ban."""
        ban = UserBan(
            user_id=uuid4(),
            reason="Permanent ban",
            is_permanent=True,
        )

        assert ban.is_expired is False

    def test_is_expired_active_ban(self) -> None:
        """Test is_expired for active temporary ban."""
        ban = UserBan(
            user_id=uuid4(),
            reason="Temporary ban",
            is_permanent=False,
            expires_at=datetime.now(tz=UTC) + timedelta(days=7),
        )

        assert ban.is_expired is False

    def test_is_expired_expired_ban(self) -> None:
        """Test is_expired for expired ban."""
        ban = UserBan(
            user_id=uuid4(),
            reason="Expired ban",
            is_permanent=False,
            expires_at=datetime.now(tz=UTC) - timedelta(days=1),
        )

        assert ban.is_expired is True

    def test_ban_repr(self) -> None:
        """Test ban string representation."""
        user_id = uuid4()

        ban = UserBan(
            user_id=user_id,
            reason="Test ban",
        )

        repr_str = repr(ban)
        assert "UserBan" in repr_str
        assert str(user_id) in repr_str


class TestFeedbackType:
    """Tests for FeedbackType enum."""

    def test_feedback_type_values(self) -> None:
        """Test feedback type enum values."""
        assert FeedbackType.THUMBS_UP.value == "thumbs_up"
        assert FeedbackType.THUMBS_DOWN.value == "thumbs_down"


class TestReportTargetType:
    """Tests for ReportTargetType enum."""

    def test_target_type_values(self) -> None:
        """Test report target type enum values."""
        assert ReportTargetType.TEMPLATE.value == "template"
        assert ReportTargetType.COMMENT.value == "comment"
        assert ReportTargetType.DESIGN.value == "design"
        assert ReportTargetType.USER.value == "user"
