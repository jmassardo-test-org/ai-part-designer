"""
Pydantic schemas for rating and community features.

Includes schemas for ratings, feedback, comments, reports, and moderation.
"""

from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


# =============================================================================
# Template Rating Schemas
# =============================================================================


class TemplateRatingCreate(BaseModel):
    """Schema for creating/updating a template rating."""
    
    rating: Annotated[int, Field(ge=1, le=5, description="Rating from 1-5 stars")]
    review: Annotated[str | None, Field(max_length=2000, default=None)]


class TemplateRatingResponse(BaseModel):
    """Schema for template rating response."""
    
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    template_id: UUID
    user_id: UUID
    rating: int
    review: str | None
    created_at: datetime
    updated_at: datetime


class TemplateRatingWithUser(TemplateRatingResponse):
    """Rating with user information."""
    
    user_name: str


class TemplateRatingSummary(BaseModel):
    """Aggregate rating summary for a template."""
    
    template_id: UUID
    average_rating: float
    total_ratings: int
    rating_distribution: dict[int, int]  # {1: count, 2: count, ...}


# =============================================================================
# Template Feedback Schemas (Thumbs Up/Down)
# =============================================================================


class TemplateFeedbackCreate(BaseModel):
    """Schema for creating/updating template feedback."""
    
    feedback_type: Annotated[str, Field(pattern="^(thumbs_up|thumbs_down)$")]


class TemplateFeedbackResponse(BaseModel):
    """Schema for template feedback response."""
    
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    template_id: UUID
    user_id: UUID
    feedback_type: str
    created_at: datetime


class TemplateFeedbackSummary(BaseModel):
    """Aggregate feedback summary for a template."""
    
    template_id: UUID
    thumbs_up: int
    thumbs_down: int
    user_feedback: str | None = None  # Current user's feedback if any


# =============================================================================
# Template Comment Schemas
# =============================================================================


class CommentCreate(BaseModel):
    """Schema for creating a new comment."""
    
    content: Annotated[str, Field(min_length=1, max_length=5000)]
    parent_id: UUID | None = None


class CommentUpdate(BaseModel):
    """Schema for updating a comment."""
    
    content: Annotated[str, Field(min_length=1, max_length=5000)]


class CommentUserInfo(BaseModel):
    """Basic user info for comments."""
    
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    display_name: str


class CommentResponse(BaseModel):
    """Schema for comment response."""
    
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    template_id: UUID
    user_id: UUID
    parent_id: UUID | None
    content: str
    is_hidden: bool
    is_edited: bool
    edited_at: datetime | None
    created_at: datetime
    updated_at: datetime
    user: CommentUserInfo | None = None
    reply_count: int = 0


class CommentThread(CommentResponse):
    """Comment with nested replies."""
    
    replies: list["CommentThread"] = []


class CommentModerationAction(BaseModel):
    """Schema for moderating a comment."""
    
    action: Annotated[str, Field(pattern="^(hide|unhide|delete)$")]
    reason: Annotated[str | None, Field(max_length=255, default=None)]


# =============================================================================
# Content Report Schemas
# =============================================================================


class ReportCreate(BaseModel):
    """Schema for creating a content report."""
    
    target_type: Annotated[
        str, Field(pattern="^(template|comment|design|user)$")
    ]
    target_id: UUID
    reason: Annotated[
        str,
        Field(
            pattern="^(spam|inappropriate|copyright|misleading|offensive|other)$"
        ),
    ]
    description: Annotated[str | None, Field(max_length=1000, default=None)]


class ReportResponse(BaseModel):
    """Schema for report response."""
    
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    reporter_id: UUID
    target_type: str
    target_id: UUID
    reason: str
    description: str | None
    status: str
    created_at: datetime


class ReportDetailResponse(ReportResponse):
    """Report with resolution details."""
    
    resolved_by_id: UUID | None
    resolved_at: datetime | None
    resolution_notes: str | None
    action_taken: str | None
    reporter_name: str | None = None


class ReportResolve(BaseModel):
    """Schema for resolving a report."""
    
    action: Annotated[
        str,
        Field(
            pattern="^(dismiss|warn|hide_content|remove_content|ban_user)$"
        ),
    ]
    resolution_notes: Annotated[str | None, Field(max_length=1000, default=None)]


class ReportListResponse(BaseModel):
    """Paginated list of reports."""
    
    items: list[ReportDetailResponse]
    total: int
    page: int
    per_page: int
    pages: int


# =============================================================================
# User Ban Schemas
# =============================================================================


class BanCreate(BaseModel):
    """Schema for creating a user ban."""
    
    user_id: UUID
    reason: Annotated[str, Field(min_length=10, max_length=2000)]
    is_permanent: bool = False
    duration_days: Annotated[int | None, Field(ge=1, le=365, default=None)]
    related_report_id: UUID | None = None


class BanResponse(BaseModel):
    """Schema for ban response."""
    
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    user_id: UUID
    reason: str
    banned_by_id: UUID | None
    is_permanent: bool
    expires_at: datetime | None
    is_active: bool
    created_at: datetime


class BanDetailResponse(BanResponse):
    """Ban with additional details."""
    
    user_email: str | None = None
    user_name: str | None = None
    banned_by_name: str | None = None
    unbanned_by_id: UUID | None = None
    unbanned_at: datetime | None = None
    unban_reason: str | None = None


class UnbanRequest(BaseModel):
    """Schema for unbanning a user."""
    
    reason: Annotated[str, Field(min_length=5, max_length=1000)]


class BanListResponse(BaseModel):
    """Paginated list of bans."""
    
    items: list[BanDetailResponse]
    total: int
    page: int
    per_page: int
    pages: int


# =============================================================================
# Moderation Dashboard Schemas
# =============================================================================


class ModerationStats(BaseModel):
    """Moderation dashboard statistics."""
    
    pending_reports: int
    reports_today: int
    reports_this_week: int
    active_bans: int
    hidden_comments: int


class ModerationQueueItem(BaseModel):
    """Item in the moderation queue."""
    
    report: ReportDetailResponse
    target_preview: str | None = None  # Preview of reported content
    reporter_history: int = 0  # Number of previous reports by this user


class ModerationQueue(BaseModel):
    """Moderation queue response."""
    
    items: list[ModerationQueueItem]
    total: int
    page: int
    per_page: int
