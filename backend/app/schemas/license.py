"""
Pydantic schemas for the licensing system (Epic 13).

Includes schemas for license type catalogues, violation reports,
admin takedown, and paginated license-related listings.
"""

from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

# =============================================================================
# License Catalog Schemas
# =============================================================================


class LicenseTypeResponse(BaseModel):
    """Response schema for a single license type in the catalog.

    Returned by GET /licenses/types.
    """

    spdx_id: str
    name: str
    url: str | None
    allows_remix: bool
    requires_attribution: bool
    allows_commercial: bool
    requires_share_alike: bool
    icon: str


class LicenseDetailResponse(BaseModel):
    """License information embedded in a design detail response.

    Provides the resolved license metadata for a specific design,
    including custom license text when applicable.
    """

    model_config = ConfigDict(from_attributes=True)

    license_type: str | None
    license_name: str | None = None
    license_url: str | None = None
    allows_remix: bool = False
    requires_attribution: bool = False
    allows_commercial: bool = False
    requires_share_alike: bool = False
    custom_license_text: str | None = None
    icon: str | None = None


# =============================================================================
# License Violation Report Schemas
# =============================================================================


class LicenseViolationReportCreate(BaseModel):
    """Schema for creating a license violation report.

    Used by POST /designs/{id}/report-violation.
    """

    violation_type: Annotated[
        str,
        Field(
            description="Type of license violation",
            pattern="^(unauthorized_remix|missing_attribution|commercial_misuse|share_alike_violation|other)$",
        ),
    ]
    description: Annotated[str, Field(min_length=10, max_length=2000)]
    evidence_url: Annotated[
        str | None,
        Field(
            max_length=2048,
            default=None,
            description="URL to evidence supporting the report",
        ),
    ]

    @model_validator(mode="after")
    def validate_evidence_url(self) -> "LicenseViolationReportCreate":
        """Validate evidence_url is a plausible URL when provided."""
        if self.evidence_url is not None:
            url = self.evidence_url.strip()
            if not url.startswith(("http://", "https://")):
                msg = "evidence_url must start with http:// or https://"
                raise ValueError(msg)
            self.evidence_url = url
        return self


class LicenseViolationReportResponse(BaseModel):
    """Response after filing a license violation report."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    design_id: UUID
    violation_type: str
    status: str
    created_at: datetime


# =============================================================================
# Admin Takedown Schemas
# =============================================================================


class TakedownRequest(BaseModel):
    """Schema for an admin takedown of a design due to licensing violation."""

    reason: Annotated[str, Field(min_length=10, max_length=2000)]
    violation_report_id: UUID | None = None


class TakedownResponse(BaseModel):
    """Response after an admin takes down a design."""

    model_config = ConfigDict(from_attributes=True)

    design_id: UUID
    unpublished_at: datetime
    reason: str
    admin_id: UUID


# =============================================================================
# User License Listing Schemas
# =============================================================================


class PublishedLicenseItem(BaseModel):
    """Summary of a design's license info for the publisher's dashboard."""

    model_config = ConfigDict(from_attributes=True)

    design_id: UUID
    design_name: str
    license_type: str | None
    license_name: str | None = None
    published_at: datetime | None
    remix_count: int = 0


class PaginatedPublishedLicensesResponse(BaseModel):
    """Paginated list of a user's published designs with license info."""

    items: list[PublishedLicenseItem]
    total: int
    page: int
    page_size: int
    total_pages: int
    has_next: bool
    has_prev: bool


class RemixedLicenseItem(BaseModel):
    """Summary of a remixed design with parent license attribution."""

    model_config = ConfigDict(from_attributes=True)

    design_id: UUID
    design_name: str
    license_type: str | None
    parent_design_id: UUID | None
    parent_design_name: str | None = None
    parent_license_type: str | None = None
    requires_attribution: bool = False
    created_at: datetime


class PaginatedRemixedLicensesResponse(BaseModel):
    """Paginated list of a user's remixed designs with license info."""

    items: list[RemixedLicenseItem]
    total: int
    page: int
    page_size: int
    total_pages: int
    has_next: bool
    has_prev: bool
