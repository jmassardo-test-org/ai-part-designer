"""
Tests for design rating, comment, and report Pydantic schemas.

Validates schema constraints including rating ranges, content length limits,
and report reason validation.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.schemas.rating import (
    DesignCommentCreate,
    DesignCommentUpdate,
    DesignRatingCreate,
    DesignReportCreate,
)

# =============================================================================
# DesignRatingCreate Tests
# =============================================================================


class TestDesignRatingCreate:
    """Tests for rating creation schema validation."""

    def test_rating_create_valid(self) -> None:
        """Valid rating with review is accepted."""
        schema = DesignRatingCreate(rating=5, review="Amazing design!")
        assert schema.rating == 5
        assert schema.review == "Amazing design!"

    def test_rating_create_valid_without_review(self) -> None:
        """Valid rating without review text is accepted."""
        schema = DesignRatingCreate(rating=3)
        assert schema.rating == 3
        assert schema.review is None

    def test_rating_create_minimum_boundary(self) -> None:
        """Rating of 1 (minimum) is valid."""
        schema = DesignRatingCreate(rating=1)
        assert schema.rating == 1

    def test_rating_create_maximum_boundary(self) -> None:
        """Rating of 5 (maximum) is valid."""
        schema = DesignRatingCreate(rating=5)
        assert schema.rating == 5

    def test_rating_create_below_range_fails(self) -> None:
        """Rating below 1 is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            DesignRatingCreate(rating=0)
        assert "greater than or equal to 1" in str(exc_info.value).lower() or "ge" in str(
            exc_info.value
        )

    def test_rating_create_above_range_fails(self) -> None:
        """Rating above 5 is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            DesignRatingCreate(rating=6)
        assert "less than or equal to 5" in str(exc_info.value).lower() or "le" in str(
            exc_info.value
        )

    def test_rating_create_negative_fails(self) -> None:
        """Negative ratings are rejected."""
        with pytest.raises(ValidationError):
            DesignRatingCreate(rating=-1)

    def test_rating_create_review_too_long_fails(self) -> None:
        """Review text exceeding 2000 characters is rejected."""
        with pytest.raises(ValidationError):
            DesignRatingCreate(rating=4, review="x" * 2001)

    def test_rating_create_review_at_max_length(self) -> None:
        """Review text at exactly 2000 characters is accepted."""
        schema = DesignRatingCreate(rating=4, review="x" * 2000)
        assert len(schema.review) == 2000

    def test_rating_create_empty_review_is_allowed(self) -> None:
        """An empty string review is not the same as None — depends on schema."""
        # The schema allows None, but an empty string may be valid depending on config
        schema = DesignRatingCreate(rating=3, review="")
        assert schema.review == ""


# =============================================================================
# DesignCommentCreate Tests
# =============================================================================


class TestDesignCommentCreate:
    """Tests for comment creation schema validation."""

    def test_comment_create_valid(self) -> None:
        """Valid comment content is accepted."""
        schema = DesignCommentCreate(content="This is a great design!")
        assert schema.content == "This is a great design!"
        assert schema.parent_id is None

    def test_comment_create_with_parent_id(self) -> None:
        """Comment with valid parent_id for threading is accepted."""
        from uuid import uuid4

        parent_id = uuid4()
        schema = DesignCommentCreate(content="Reply!", parent_id=parent_id)
        assert schema.parent_id == parent_id

    def test_comment_create_empty_content_fails(self) -> None:
        """Empty comment content is rejected (min_length=1)."""
        with pytest.raises(ValidationError):
            DesignCommentCreate(content="")

    def test_comment_create_content_too_long_fails(self) -> None:
        """Comment content exceeding 5000 characters is rejected."""
        with pytest.raises(ValidationError):
            DesignCommentCreate(content="x" * 5001)

    def test_comment_create_content_at_max_length(self) -> None:
        """Comment content at exactly 5000 characters is accepted."""
        schema = DesignCommentCreate(content="x" * 5000)
        assert len(schema.content) == 5000

    def test_comment_create_whitespace_only_single_char(self) -> None:
        """A single space character meets min_length=1."""
        schema = DesignCommentCreate(content=" ")
        assert schema.content == " "


# =============================================================================
# DesignCommentUpdate Tests
# =============================================================================


class TestDesignCommentUpdate:
    """Tests for comment update schema validation."""

    def test_comment_update_valid(self) -> None:
        """Valid updated content is accepted."""
        schema = DesignCommentUpdate(content="Updated comment text")
        assert schema.content == "Updated comment text"

    def test_comment_update_empty_content_fails(self) -> None:
        """Empty updated content is rejected."""
        with pytest.raises(ValidationError):
            DesignCommentUpdate(content="")

    def test_comment_update_content_too_long_fails(self) -> None:
        """Updated content exceeding 5000 characters is rejected."""
        with pytest.raises(ValidationError):
            DesignCommentUpdate(content="y" * 5001)


# =============================================================================
# DesignReportCreate Tests
# =============================================================================


class TestDesignReportCreate:
    """Tests for report creation schema validation."""

    def test_report_create_valid(self) -> None:
        """Valid report with all fields is accepted."""
        schema = DesignReportCreate(reason="spam", description="Clearly spam content")
        assert schema.reason == "spam"
        assert schema.description == "Clearly spam content"

    def test_report_create_valid_without_description(self) -> None:
        """Report without description is accepted."""
        schema = DesignReportCreate(reason="copyright")
        assert schema.reason == "copyright"
        assert schema.description is None

    @pytest.mark.parametrize(
        "reason",
        ["spam", "inappropriate", "copyright", "misleading", "offensive", "other"],
    )
    def test_report_create_all_valid_reasons(self, reason: str) -> None:
        """All defined report reasons are accepted."""
        schema = DesignReportCreate(reason=reason)
        assert schema.reason == reason

    def test_report_create_invalid_reason_fails(self) -> None:
        """An unrecognized reason string is rejected by the pattern validator."""
        with pytest.raises(ValidationError):
            DesignReportCreate(reason="not_a_reason")

    def test_report_create_empty_reason_fails(self) -> None:
        """Empty string reason is rejected."""
        with pytest.raises(ValidationError):
            DesignReportCreate(reason="")

    def test_report_create_description_too_long_fails(self) -> None:
        """Report description exceeding 1000 characters is rejected."""
        with pytest.raises(ValidationError):
            DesignReportCreate(reason="spam", description="z" * 1001)

    def test_report_create_description_at_max_length(self) -> None:
        """Report description at exactly 1000 characters is accepted."""
        schema = DesignReportCreate(reason="other", description="z" * 1000)
        assert len(schema.description) == 1000
