# Epic 13: Model Licensing — Technical Architecture & Security Design

**Status:** Draft
**Date:** 2026-02-25
**Authors:** Architecture & Security Agent
**Epic:** #18 — Model Licensing (~13 SP total, Phase 1: 8 SP)

---

## Table of Contents

1. [Architecture Decision Record](#1-architecture-decision-record)
2. [Data Model Specification](#2-data-model-specification)
3. [Migration Strategy](#3-migration-strategy)
4. [Service Layer Architecture](#4-service-layer-architecture)
5. [API Endpoint Specification](#5-api-endpoint-specification)
6. [Error Handling](#6-error-handling)
7. [Security Design](#7-security-design)
8. [Integration Points](#8-integration-points)
9. [Database Indexes & Performance](#9-database-indexes--performance)
10. [File Inventory](#10-file-inventory)

---

## 1. Architecture Decision Record

### ADR: License Catalog as Code Constants (Not DB Table)

**Status:** Accepted

**Context:**
The design spec proposes 9 license types (8 standard CC + CUSTOM) stored as a Python `StrEnum` with a companion `LICENSE_METADATA` dict, rather than a database `license_types` table.

**Decision:** Confirmed — code constants are correct for this use case.

**Rationale:**
- License types are a **closed, slowly-evolving set** — standard CC licenses are versioned by the CC organization, not by platform admins. A new CC major version (e.g., CC-BY-5.0) would require schema review regardless.
- Code constants are **type-checked** by mypy, validated at import time, and require no database round-trip for lookups.
- The existing codebase uses this exact pattern: `FeedbackType(StrEnum)`, `ReportStatus(StrEnum)`, `ReportTargetType(StrEnum)` in `backend/app/models/rating.py`, and `Role(StrEnum)` in `backend/app/core/auth.py`.
- If future Phase 2 requires admin-managed custom license templates, a migration to a DB table is backward-compatible (the `String(30)` column stores the key either way).

**Consequences:**
- Adding a new license type requires a code change + deployment (acceptable given frequency).
- No DB migration needed for catalog changes.
- All metadata lookups are O(1) in-memory.

---

### ADR: New `license_violation_reports` Table vs. Reusing `content_reports`

**Status:** Accepted (modified from strategy spec)

**Context:**
The strategy spec proposes a new `license_violation_reports` table. However, the codebase already has a generic `content_reports` table (`backend/app/models/rating.py` line 464) with `target_type`, `target_id`, `reason`, `description`, `status`, `resolved_by_id`, `resolved_at`, and `resolution_notes`. The existing `DesignReportService` already wraps this table for design-specific reporting.

**Decision:** **Reuse `content_reports`** with a new `ReportTargetType.LICENSE_VIOLATION` enum value and new `ReportReason` values, rather than creating a separate table.

**Rationale:**
- The `content_reports` table already has every required column: `reporter_id`, `target_type`, `target_id`, `reason`, `description`, `status` (with `ReportStatus` enum: `PENDING`, `REVIEWING`, `RESOLVED`, `DISMISSED`), `resolved_by_id`, `resolved_at`, `resolution_notes`, `action_taken`.
- The only field from the strategy spec not present is `evidence_url`. This can be stored in a new nullable column on `content_reports`, or in the description field with a documented convention. **Decision: Add `evidence_url` column** to `content_reports` — it's a generic field useful for any report type.
- Avoids table proliferation for semantically similar data (reports are reports).
- Keeps the admin moderation queue unified — admins review all reports in one place.
- The existing unique constraint `uq_report_user_target` on `(reporter_id, target_type, target_id)` naturally prevents duplicate license violation reports.

**Consequences:**
- One additional migration to add `evidence_url` to `content_reports`.
- New enum values: `ReportTargetType.LICENSE_VIOLATION = "license_violation"` and new reason constants.
- `LicenseViolationReportService` wraps `content_reports` (same pattern as `DesignReportService`).

---

### ADR: License Columns on `designs` Table vs. Separate `design_licenses` Table

**Status:** Accepted

**Context:**
The strategy spec places `license_type` and `custom_license_text` directly on the `designs` table, rather than a join table.

**Decision:** Confirmed — columns on `designs` is correct.

**Rationale:**
- One-to-one relationship: a design has exactly one license at any point in time.
- Avoids JOIN overhead on every marketplace browse query (the `browse_designs` endpoint already selects from `designs` with several filters).
- The `license_type` column will be indexed for filter queries — much more efficient than a join.
- `custom_license_text` is nullable `Text` — only populated for `CUSTOM` licenses. PostgreSQL stores `Text` out-of-line (TOAST) for large values, so it doesn't bloat the main tuple.
- License history is not needed in Phase 1. If Phase 2 requires license change tracking, the existing `AuditLog` captures license changes in JSONB context (old/new values). A formal `design_license_history` table can be added later.

**Consequences:**
- One migration adding two nullable columns to `designs`.
- No change to existing queries that don't reference these columns — they continue to work as-is.

---

### ADR: Attribution Storage in `extra_data` JSONB

**Status:** Accepted

**Context:**
The strategy spec stores attribution metadata in `extra_data.attribution` on the remixed design. The `extra_data` column is already JSONB with a GIN index.

**Decision:** Confirmed — `extra_data.attribution` is the right location.

**Rationale:**
- `extra_data` is already used for design-specific metadata: `parameters`, `dimensions`, `aiPrompt`, `downloads`, etc.
- JSONB storage means the attribution structure can evolve without schema migrations.
- The GIN index on `extra_data` already exists (`idx_designs_extra_data`).
- Attribution is write-once (set at remix time) and read on design detail view — no complex query patterns needed.

---

## 2. Data Model Specification

### 2.1 New Columns on `designs` Table

Add to `Design` class in `backend/app/models/design.py`, after the `search_vector` column (before relationships):

```python
# License information (Epic 13)
license_type: Mapped[str | None] = mapped_column(
    String(30),
    nullable=True,
    index=True,
    doc="SPDX-like license identifier: CC-BY-4.0, CC-BY-SA-4.0, CC-BY-NC-4.0, "
        "CC-BY-NC-SA-4.0, CC-BY-ND-4.0, CC-BY-NC-ND-4.0, CC0-1.0, "
        "ALL-RIGHTS-RESERVED, or CUSTOM",
)
custom_license_text: Mapped[str | None] = mapped_column(
    Text,
    nullable=True,
    doc="Custom license terms when license_type is CUSTOM. Max 5000 chars enforced at schema level.",
)
```

**Column design notes:**
- `String(30)` accommodates the longest key: `CC-BY-NC-ND-4.0` (16 chars) with room for future versions.
- `nullable=True` — existing published designs will have `NULL`, displayed as "No license specified" in the UI.
- `index=True` — enables efficient filtering on `license_type` in browse queries.
- No DB-level `CHECK` constraint on `license_type` values — validation is in the Pydantic schema and service layer, following the existing pattern (e.g., `category` on `designs` is `String(50)` with no DB constraint; validation is in the endpoint).

### 2.2 New Column on `content_reports` Table

Add to `ContentReport` class in `backend/app/models/rating.py`:

```python
evidence_url: Mapped[str | None] = mapped_column(
    String(2048),
    nullable=True,
    doc="URL to evidence supporting the report (screenshot, link, etc.)",
)
```

**Design notes:**
- `String(2048)` — standard maximum URL length per RFC 2616 practical limits.
- Useful for all report types, not just license violations.

### 2.3 New Enum Values

In `backend/app/models/rating.py`, extend existing enums:

```python
class ReportTargetType(StrEnum):
    """Type of content being reported."""
    TEMPLATE = "template"
    COMMENT = "comment"
    DESIGN = "design"
    USER = "user"
    LICENSE_VIOLATION = "license_violation"  # NEW


class LicenseViolationType(StrEnum):
    """Types of license violations that can be reported."""
    UNAUTHORIZED_REMIX = "unauthorized_remix"
    MISSING_ATTRIBUTION = "missing_attribution"
    COMMERCIAL_MISUSE = "commercial_misuse"
    SHARE_ALIKE_VIOLATION = "share_alike_violation"
    OTHER = "other"
```

### 2.4 New File: `backend/app/core/licenses.py`

```python
"""
License type catalog and metadata for the marketplace licensing system.

Defines the closed set of supported license types and their properties.
These are code constants (not DB-managed) because the license catalog
evolves infrequently and benefits from static type checking.
"""

from dataclasses import dataclass
from enum import StrEnum


class LicenseType(StrEnum):
    """Supported license types for marketplace designs.

    Values are SPDX-compatible identifiers where applicable.
    """
    CC_BY_4_0 = "CC-BY-4.0"
    CC_BY_SA_4_0 = "CC-BY-SA-4.0"
    CC_BY_NC_4_0 = "CC-BY-NC-4.0"
    CC_BY_NC_SA_4_0 = "CC-BY-NC-SA-4.0"
    CC_BY_ND_4_0 = "CC-BY-ND-4.0"
    CC_BY_NC_ND_4_0 = "CC-BY-NC-ND-4.0"
    CC0_1_0 = "CC0-1.0"
    ALL_RIGHTS_RESERVED = "ALL-RIGHTS-RESERVED"
    CUSTOM = "CUSTOM"


@dataclass(frozen=True)
class LicenseInfo:
    """Immutable metadata for a license type.

    Attributes:
        spdx_id: SPDX license identifier.
        name: Human-readable license name.
        url: Link to full legal text (None for CUSTOM/ARR).
        allows_remix: Whether derivative works are permitted.
        requires_attribution: Whether attribution is required.
        allows_commercial: Whether commercial use is permitted.
        requires_share_alike: Whether derivatives must use same license.
        icon: Frontend icon identifier for badge display.
    """
    spdx_id: str
    name: str
    url: str | None
    allows_remix: bool
    requires_attribution: bool
    allows_commercial: bool
    requires_share_alike: bool
    icon: str


LICENSE_METADATA: dict[str, LicenseInfo] = {
    LicenseType.CC_BY_4_0: LicenseInfo(
        spdx_id="CC-BY-4.0",
        name="Creative Commons Attribution 4.0 International",
        url="https://creativecommons.org/licenses/by/4.0/",
        allows_remix=True,
        requires_attribution=True,
        allows_commercial=True,
        requires_share_alike=False,
        icon="cc-by",
    ),
    LicenseType.CC_BY_SA_4_0: LicenseInfo(
        spdx_id="CC-BY-SA-4.0",
        name="Creative Commons Attribution-ShareAlike 4.0 International",
        url="https://creativecommons.org/licenses/by-sa/4.0/",
        allows_remix=True,
        requires_attribution=True,
        allows_commercial=True,
        requires_share_alike=True,
        icon="cc-by-sa",
    ),
    LicenseType.CC_BY_NC_4_0: LicenseInfo(
        spdx_id="CC-BY-NC-4.0",
        name="Creative Commons Attribution-NonCommercial 4.0 International",
        url="https://creativecommons.org/licenses/by-nc/4.0/",
        allows_remix=True,
        requires_attribution=True,
        allows_commercial=False,
        requires_share_alike=False,
        icon="cc-by-nc",
    ),
    LicenseType.CC_BY_NC_SA_4_0: LicenseInfo(
        spdx_id="CC-BY-NC-SA-4.0",
        name="Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International",
        url="https://creativecommons.org/licenses/by-nc-sa/4.0/",
        allows_remix=True,
        requires_attribution=True,
        allows_commercial=False,
        requires_share_alike=True,
        icon="cc-by-nc-sa",
    ),
    LicenseType.CC_BY_ND_4_0: LicenseInfo(
        spdx_id="CC-BY-ND-4.0",
        name="Creative Commons Attribution-NoDerivatives 4.0 International",
        url="https://creativecommons.org/licenses/by-nd/4.0/",
        allows_remix=False,
        requires_attribution=True,
        allows_commercial=True,
        requires_share_alike=False,
        icon="cc-by-nd",
    ),
    LicenseType.CC_BY_NC_ND_4_0: LicenseInfo(
        spdx_id="CC-BY-NC-ND-4.0",
        name="Creative Commons Attribution-NonCommercial-NoDerivatives 4.0 International",
        url="https://creativecommons.org/licenses/by-nc-nd/4.0/",
        allows_remix=False,
        requires_attribution=True,
        allows_commercial=False,
        requires_share_alike=False,
        icon="cc-by-nc-nd",
    ),
    LicenseType.CC0_1_0: LicenseInfo(
        spdx_id="CC0-1.0",
        name="CC0 1.0 Universal (Public Domain Dedication)",
        url="https://creativecommons.org/publicdomain/zero/1.0/",
        allows_remix=True,
        requires_attribution=False,
        allows_commercial=True,
        requires_share_alike=False,
        icon="cc-zero",
    ),
    LicenseType.ALL_RIGHTS_RESERVED: LicenseInfo(
        spdx_id="ALL-RIGHTS-RESERVED",
        name="All Rights Reserved",
        url=None,
        allows_remix=False,
        requires_attribution=False,
        allows_commercial=False,
        requires_share_alike=False,
        icon="lock",
    ),
    LicenseType.CUSTOM: LicenseInfo(
        spdx_id="CUSTOM",
        name="Custom License",
        url=None,
        allows_remix=False,  # Default; overridden by custom_allows_remix flag
        requires_attribution=False,
        allows_commercial=False,
        requires_share_alike=False,
        icon="file-text",
    ),
}


def get_license_metadata(license_type: str) -> LicenseInfo | None:
    """Look up metadata for a license type.

    Args:
        license_type: The license type key (e.g., "CC-BY-4.0").

    Returns:
        LicenseInfo if found, None otherwise.
    """
    return LICENSE_METADATA.get(license_type)


def is_valid_license_type(license_type: str) -> bool:
    """Check if a string is a valid license type.

    Args:
        license_type: The license type key to validate.

    Returns:
        True if the key exists in LICENSE_METADATA.
    """
    return license_type in LICENSE_METADATA


def allows_remix(license_type: str, custom_allows_remix: bool = False) -> bool:
    """Check if a license permits derivative works (remixing).

    For CUSTOM licenses, defers to the explicit custom_allows_remix flag
    stored as part of the design's publish configuration.

    Args:
        license_type: The license type key.
        custom_allows_remix: Override for CUSTOM licenses.

    Returns:
        True if remixing is permitted.
    """
    if license_type == LicenseType.CUSTOM:
        return custom_allows_remix
    meta = LICENSE_METADATA.get(license_type)
    return meta.allows_remix if meta else False


def get_share_alike_compatible_licenses(license_type: str) -> list[str]:
    """Return the list of licenses that satisfy share-alike for a given license.

    When a remix's parent is share-alike, the remix must use the same
    or a compatible license.

    Per CC legal code, the only compatible license for CC-BY-SA-4.0 is
    CC-BY-SA-4.0 itself. Same for CC-BY-NC-SA-4.0.

    Args:
        license_type: The parent design's license type.

    Returns:
        List of compatible license type keys. Empty if no restriction.
    """
    meta = LICENSE_METADATA.get(license_type)
    if not meta or not meta.requires_share_alike:
        return []  # No restriction

    # CC share-alike requires the same license
    return [license_type]
```

**Architecture notes:**
- `@dataclass(frozen=True)` makes `LicenseInfo` immutable — matches the semantic that license metadata is static.
- Helper functions (`allows_remix`, `get_share_alike_compatible_licenses`) encapsulate license rule logic in one place, keeping the service layer thin.
- The CUSTOM license's `allows_remix=False` default is overridden at runtime by the `custom_allows_remix` parameter — this is passed from the design's `extra_data` or a dedicated column (see Section 2.5).

### 2.5 Custom License Remix Flag

The CUSTOM license needs a per-design `allows_remix` flag. Two options:

| Option | Storage | Pro | Con |
|--------|---------|-----|-----|
| A: Column on `designs` | `custom_allows_remix: Mapped[bool]` | Explicit, queryable for filters | Yet another column |
| B: Field in `extra_data` JSONB | `extra_data["custom_allows_remix"]` | No migration | Not directly filterable without JSONB index |

**Decision:** Option A — add a `custom_allows_remix` column. Rationale:
- The browse filter `allows_remix=true` needs to work for custom licenses too. A SQL query like `WHERE license_type != 'ALL-RIGHTS-RESERVED' AND (license_type != 'CUSTOM' OR custom_allows_remix = TRUE)` is cleaner and index-friendly.
- Follows the existing pattern of explicit boolean columns (`is_public`, `is_starter`).

```python
# On Design model, alongside license_type and custom_license_text
custom_allows_remix: Mapped[bool] = mapped_column(
    Boolean,
    nullable=False,
    default=False,
    doc="Whether custom-licensed designs allow remixing. Only meaningful when license_type is CUSTOM.",
)
```

### 2.6 Attribution Data Structure (in `extra_data` JSONB)

When a remix is created from a licensed design, the remix's `extra_data.attribution` field is populated:

```json
{
  "attribution": {
    "original_design_id": "uuid-string",
    "original_design_name": "Pi Zero Enclosure",
    "original_author_id": "uuid-string",
    "original_author_name": "alice",
    "license_type": "CC-BY-4.0",
    "license_name": "Creative Commons Attribution 4.0 International",
    "license_url": "https://creativecommons.org/licenses/by/4.0/",
    "attribution_text": "Based on \"Pi Zero Enclosure\" by alice, licensed under CC-BY-4.0",
    "remix_date": "2026-02-25T14:30:00Z",
    "parent_attribution": null
  }
}
```

For remix-of-remix scenarios, `parent_attribution` contains the parent's attribution object, creating a chain:

```json
{
  "attribution": {
    "original_design_id": "uuid-b",
    "original_design_name": "Pi Case (Remix)",
    "original_author_name": "bob",
    "license_type": "CC-BY-SA-4.0",
    "attribution_text": "Based on \"Pi Case (Remix)\" by bob, licensed under CC-BY-SA-4.0",
    "parent_attribution": {
      "original_design_id": "uuid-a",
      "original_design_name": "Pi Zero Enclosure",
      "original_author_name": "alice",
      "license_type": "CC-BY-4.0",
      "attribution_text": "Based on \"Pi Zero Enclosure\" by alice, licensed under CC-BY-4.0"
    }
  }
}
```

### 2.7 New AuditActions Constants

In `backend/app/models/audit.py`, add to the `AuditActions` class:

```python
class AuditActions:
    # ... existing constants ...

    # License (Epic 13)
    LICENSE_SET = "license_set"
    LICENSE_CHANGE = "license_change"
    LICENSE_REMIX_BLOCKED = "license_remix_blocked"
    LICENSE_REMIX_ALLOWED = "license_remix_allowed"
    LICENSE_ATTRIBUTION_GENERATED = "license_attribution_generated"
    LICENSE_VIOLATION_REPORT = "license_violation_report"
    LICENSE_TAKEDOWN = "license_takedown"
    LICENSE_SHARE_ALIKE_ENFORCED = "license_share_alike_enforced"
```

---

## 3. Migration Strategy

### Migration 029: Add License Columns to Designs

**File:** `backend/alembic/versions/029_design_license_columns.py`

```python
"""Add license columns to designs table.

Revision ID: (auto-generated)
Revises: 20260225_184337_merge_heads
"""

def upgrade() -> None:
    op.add_column("designs", sa.Column("license_type", sa.String(30), nullable=True, index=True))
    op.add_column("designs", sa.Column("custom_license_text", sa.Text(), nullable=True))
    op.add_column("designs", sa.Column("custom_allows_remix", sa.Boolean(), nullable=False, server_default="false"))
    op.create_index("idx_designs_license_type", "designs", ["license_type"],
                     postgresql_where="deleted_at IS NULL AND is_public = TRUE")

def downgrade() -> None:
    op.drop_index("idx_designs_license_type", table_name="designs")
    op.drop_column("designs", "custom_allows_remix")
    op.drop_column("designs", "custom_license_text")
    op.drop_column("designs", "license_type")
```

**Notes:**
- `nullable=True` for `license_type` — existing published designs will show "No license specified."
- `server_default="false"` for `custom_allows_remix` avoids NULL issues on existing rows.
- Partial index on `license_type` matches the existing partial index pattern (`idx_designs_public`, `idx_designs_starter`).

### Migration 030: Add Evidence URL to Content Reports

**File:** `backend/alembic/versions/030_content_reports_evidence_url.py`

```python
"""Add evidence_url column to content_reports table.

Revision ID: (auto-generated)
Revises: 029_design_license_columns
"""

def upgrade() -> None:
    op.add_column("content_reports", sa.Column("evidence_url", sa.String(2048), nullable=True))

def downgrade() -> None:
    op.drop_column("content_reports", "evidence_url")
```

**Ordering:** 029 then 030. These are independent but sequential for cleanliness. Neither migration requires data backfill (all new columns are nullable or have server defaults).

---

## 4. Service Layer Architecture

### 4.1 `LicenseService` Class

**File:** `backend/app/services/license_service.py`

```python
class LicenseService:
    """Service for license validation, enforcement, and compliance actions.

    Coordinates with the license catalog (app.core.licenses), the Design model,
    ContentReport model, AuditLog, and NotificationService.

    Args:
        db: Async database session.
    """

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
```

#### Method: `validate_license_for_publish`

```python
async def validate_license_for_publish(
    self,
    design: Design,
    license_type: str,
    custom_license_text: str | None = None,
    custom_allows_remix: bool = False,
) -> None:
    """Validate license selection before publishing.

    Enforces:
    1. license_type must be a valid LicenseType value.
    2. CUSTOM license requires non-empty custom_license_text.
    3. custom_license_text max length: 5000 chars.
    4. Share-alike enforcement: if design is a remix of a share-alike
       licensed parent, the selected license must be compatible.

    Args:
        design: The Design being published.
        license_type: The selected license key.
        custom_license_text: Custom text (required if CUSTOM).
        custom_allows_remix: Whether custom license allows remixing.

    Raises:
        ValueError: If validation fails (caught by endpoint, returned as 400).
    """
```

**Share-alike enforcement logic:**
1. If `design.remixed_from_id` is not None:
   a. Load the parent design.
   b. Check if parent's `license_type` requires share-alike.
   c. If yes, verify `license_type` is in `get_share_alike_compatible_licenses(parent.license_type)`.
   d. If not compatible, raise `ValueError` with message explaining the constraint.
2. Audit log: `LICENSE_SHARE_ALIKE_ENFORCED` if constraint was applied.

#### Method: `check_remix_allowed`

```python
async def check_remix_allowed(
    self,
    design: Design,
    user: User,
) -> tuple[bool, str | None]:
    """Check if a design can be remixed based on its license.

    Rules:
    - Owner can always remix their own designs.
    - Designs without a license (NULL) are remixable (legacy behavior).
    - License metadata determines if remix is allowed.
    - CUSTOM licenses check custom_allows_remix flag.

    Args:
        design: The design to check.
        user: The user attempting to remix.

    Returns:
        Tuple of (allowed: bool, reason: str | None).
        reason is None if allowed, or an explanation if blocked.
    """
```

**Logic:**
1. If `design.user_id == user.id` → `(True, None)` (owner always allowed).
2. If `design.license_type is None` → `(True, None)` (legacy designs, no license).
3. If `design.license_type == LicenseType.CUSTOM` → check `design.custom_allows_remix`.
4. Otherwise → check `LICENSE_METADATA[license_type].allows_remix`.
5. If blocked, return `(False, "This design's license ({license_name}) does not allow remixing.")`.
6. Audit log: `LICENSE_REMIX_BLOCKED` or `LICENSE_REMIX_ALLOWED`.

#### Method: `build_attribution`

```python
async def build_attribution(
    self,
    parent_design: Design,
    parent_author: User,
) -> dict[str, Any]:
    """Build attribution metadata for a remix.

    Called when creating a remix of a licensed design.
    Produces the attribution dict stored in extra_data.attribution.

    Args:
        parent_design: The design being remixed.
        parent_author: The author of the parent design.

    Returns:
        Attribution dict for storage in extra_data.
    """
```

**Logic:**
1. Build attribution from parent design's license info.
2. If parent design has `extra_data.attribution`, capture as `parent_attribution` (chain).
3. Generate `attribution_text`: `Based on "<name>" by <author>, licensed under <license>`.
4. Audit log: `LICENSE_ATTRIBUTION_GENERATED`.

#### Method: `report_violation`

```python
async def report_violation(
    self,
    design_id: UUID,
    reporter: User,
    violation_type: str,
    description: str,
    evidence_url: str | None = None,
) -> ContentReport:
    """Report a license violation on a design.

    Creates a ContentReport with target_type=LICENSE_VIOLATION and an
    AuditLog entry.

    Args:
        design_id: The design being reported.
        reporter: The user filing the report.
        violation_type: One of LicenseViolationType values.
        description: Detailed description (max 2000 chars).
        evidence_url: Optional URL to supporting evidence.

    Returns:
        The created ContentReport.

    Raises:
        ValueError: If user already reported this design for license violation.
        ValueError: If design not found or not public.
    """
```

#### Method: `admin_takedown`

```python
async def admin_takedown(
    self,
    design_id: UUID,
    admin_user: User,
    reason: str,
    violation_report_id: UUID | None = None,
) -> Design:
    """Admin takedown of a design for license violation.

    Unpublishes the design and creates audit trail.
    Optionally resolves an associated violation report.

    Args:
        design_id: Design to take down.
        admin_user: The admin performing the action.
        reason: Reason for takedown (stored in audit context).
        violation_report_id: Optional report to mark as resolved.

    Returns:
        The updated Design.

    Raises:
        ValueError: If design not found.
        PermissionError: If user is not admin.
    """
```

**Logic:**
1. Verify `admin_user.is_admin`.
2. Load design, set `is_public = False`, clear `published_at`.
3. If `violation_report_id`, update report status to `RESOLVED`, set `resolved_by_id`, `resolved_at`, `action_taken = "takedown"`.
4. Create `AuditLog` with `action = LICENSE_TAKEDOWN`, context includes design_id, reason, violation_report_id.
5. Send notification to design owner via `NotificationService` (if available).

#### Method: `get_user_published_licenses`

```python
async def get_user_published_licenses(
    self,
    user: User,
    license_type_filter: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[dict[str, Any]], int]:
    """Get paginated list of user's published designs with license info.

    Args:
        user: The authenticated user.
        license_type_filter: Optional filter by license type.
        page: Page number (1-indexed).
        page_size: Items per page.

    Returns:
        Tuple of (items, total_count).
    """
```

#### Method: `get_user_remixed_licenses`

```python
async def get_user_remixed_licenses(
    self,
    user: User,
    license_type_filter: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[dict[str, Any]], int]:
    """Get paginated list of designs the user has remixed, with license info.

    Args:
        user: The authenticated user.
        license_type_filter: Optional filter by license type.
        page: Page number (1-indexed).
        page_size: Items per page.

    Returns:
        Tuple of (items, total_count).
    """
```

---

## 5. API Endpoint Specification

### 5.1 Updated Endpoints

#### `POST /api/v2/marketplace/designs/{design_id}/publish`

**Changes:**
- Accept `license_type`, `custom_license_text`, `custom_allows_remix` in request body.
- Call `LicenseService.validate_license_for_publish()` before persisting.
- Persist license fields on the Design model.
- Audit log: `LICENSE_SET` on first publish, `LICENSE_CHANGE` on re-publish with different license.

**Updated Request Schema:**

```python
class PublishDesignRequest(BaseModel):
    """Schema for publishing a design to marketplace."""

    category: Annotated[str | None, Field(max_length=50, default=None)]
    tags: list[str] = []
    is_starter: bool = False
    license_type: Annotated[str, Field(
        default="CC-BY-4.0",
        max_length=30,
        description="License type key. Must be a valid LicenseType value.",
    )]
    custom_license_text: Annotated[str | None, Field(
        max_length=5000,
        default=None,
        description="Custom license terms. Required when license_type is CUSTOM.",
    )]
    custom_allows_remix: bool = Field(
        default=False,
        description="Whether custom-licensed designs allow remixing.",
    )

    @model_validator(mode="after")
    def validate_custom_license(self) -> "PublishDesignRequest":
        """Ensure custom_license_text is provided when license_type is CUSTOM."""
        if self.license_type == "CUSTOM" and not self.custom_license_text:
            raise ValueError("custom_license_text is required when license_type is CUSTOM")
        if self.license_type != "CUSTOM" and self.custom_license_text:
            raise ValueError("custom_license_text should only be set when license_type is CUSTOM")
        return self
```

**Updated Response Schema:**

```python
class PublishDesignResponse(BaseModel):
    """Response after publishing a design."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    published_at: datetime
    category: str | None
    is_starter: bool
    license_type: str  # NEW
```

#### `GET /api/v2/marketplace/designs`

**New Query Parameters:**

```python
@router.get("/designs", response_model=PaginatedDesignResponse)
async def browse_designs(
    # ... existing params ...
    license_type: str | None = Query(None, description="Filter by exact license type"),
    allows_remix: bool | None = Query(None, description="Filter: only designs that allow remix"),
    allows_commercial: bool | None = Query(None, description="Filter: only designs that allow commercial use"),
    # ... existing deps ...
) -> PaginatedDesignResponse:
```

**Filter logic:**

```python
# License type filter
if license_type:
    if not is_valid_license_type(license_type):
        raise HTTPException(status_code=400, detail="Invalid license_type filter value")
    query = query.where(Design.license_type == license_type)

# Allows remix filter
if allows_remix is True:
    # Include: all remix-allowing standard licenses + CUSTOM where custom_allows_remix=True + NULL (legacy)
    remix_license_types = [lt for lt, meta in LICENSE_METADATA.items() if meta.allows_remix]
    query = query.where(
        or_(
            Design.license_type.in_(remix_license_types),
            and_(Design.license_type == LicenseType.CUSTOM, Design.custom_allows_remix == True),
            Design.license_type.is_(None),  # Legacy designs
        )
    )

# Allows commercial filter
if allows_commercial is True:
    commercial_license_types = [lt for lt, meta in LICENSE_METADATA.items() if meta.allows_commercial]
    query = query.where(
        or_(
            Design.license_type.in_(commercial_license_types),
            Design.license_type.is_(None),  # Legacy designs
        )
    )
```

#### `GET /api/v2/marketplace/designs/{design_id}`

**Changes:**
- Add `license_type` and `license_info` to response.

**Updated Response:**

```python
class LicenseDetailResponse(BaseModel):
    """Full license detail for design detail page."""
    license_type: str | None
    license_name: str | None
    license_url: str | None
    allows_remix: bool
    requires_attribution: bool
    allows_commercial: bool
    requires_share_alike: bool
    custom_license_text: str | None = None
    icon: str | None = None


class DesignSummaryResponse(BaseModel):
    """Summary of a design for marketplace listings."""
    # ... existing fields ...
    license_type: str | None = None  # NEW


class MarketplaceDesignResponse(DesignSummaryResponse):
    """Full design details for marketplace."""
    # ... existing fields ...
    license_info: LicenseDetailResponse | None = None  # NEW
    attribution: dict[str, Any] | None = None  # NEW — from extra_data.attribution
```

#### `POST /api/v2/marketplace/designs/{design_id}/remix`

**Changes:**
1. Before creating the remix, call `LicenseService.check_remix_allowed()`.
2. If blocked, return 403.
3. If allowed and parent has a license requiring attribution, call `LicenseService.build_attribution()` and store in remix's `extra_data.attribution`.
4. Copy parent's `license_type` to remix as a default (user can change when they publish).

**Error response when blocked:**

```json
{
  "detail": "This design's license does not allow remixing.",
  "license_type": "CC-BY-ND-4.0",
  "license_name": "Creative Commons Attribution-NoDerivatives 4.0 International"
}
```

### 5.2 New Endpoints

#### `GET /api/v2/licenses/types`

**Auth:** Public (no authentication required)
**Rate limit:** `standard_api_limit` (60/min)
**Description:** Returns the full license catalog with metadata.

```python
@router.get("/types", response_model=list[LicenseTypeResponse])
async def list_license_types() -> list[LicenseTypeResponse]:
    """List all supported license types with metadata.

    Returns the static license catalog. This endpoint is cacheable.
    """
```

**Response schema:**

```python
class LicenseTypeResponse(BaseModel):
    """A supported license type with its properties."""
    key: str                      # "CC-BY-4.0"
    name: str                     # "Creative Commons Attribution 4.0 International"
    url: str | None               # "https://creativecommons.org/licenses/by/4.0/"
    allows_remix: bool
    requires_attribution: bool
    allows_commercial: bool
    requires_share_alike: bool
    icon: str                     # "cc-by"
```

**Caching:** Response is static and should include `Cache-Control: public, max-age=86400` header.

#### `GET /api/v2/licenses/my/published`

**Auth:** Required (`get_current_user`)
**Rate limit:** `standard_api_limit` (60/min)

```python
@router.get("/my/published", response_model=PaginatedPublishedLicensesResponse)
async def get_my_published_licenses(
    license_type: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PaginatedPublishedLicensesResponse:
    """Get user's published designs with license information."""
```

**Response schema:**

```python
class PublishedLicenseItem(BaseModel):
    """A published design with its license summary."""
    design_id: UUID
    design_name: str
    license_type: str | None
    license_name: str | None
    published_at: datetime | None
    remix_count: int
    is_public: bool

class PaginatedPublishedLicensesResponse(BaseModel):
    items: list[PublishedLicenseItem]
    total: int
    page: int
    page_size: int
```

#### `GET /api/v2/licenses/my/remixed`

**Auth:** Required (`get_current_user`)
**Rate limit:** `standard_api_limit` (60/min)

```python
@router.get("/my/remixed", response_model=PaginatedRemixedLicensesResponse)
async def get_my_remixed_licenses(
    license_type: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PaginatedRemixedLicensesResponse:
    """Get designs the user has remixed, with original license info."""
```

**Response schema:**

```python
class RemixedLicenseItem(BaseModel):
    """A remixed design with the original's license info."""
    remix_id: UUID
    remix_name: str
    original_design_id: UUID | None
    original_design_name: str | None
    original_author_name: str | None
    license_type: str | None
    license_name: str | None
    remixed_at: datetime

class PaginatedRemixedLicensesResponse(BaseModel):
    items: list[RemixedLicenseItem]
    total: int
    page: int
    page_size: int
```

#### `POST /api/v2/marketplace/designs/{design_id}/report-violation`

**Auth:** Required (`get_current_user`)
**Rate limit:** Custom — **5 requests per user per hour** (abuse prevention)

```python
violation_report_limit = RateLimiter(
    max_requests=5,
    window_seconds=3600,
    key_prefix="rate_limit:violation_report",
)

@router.post(
    "/designs/{design_id}/report-violation",
    response_model=LicenseViolationReportResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(violation_report_limit)],
)
async def report_license_violation(
    design_id: UUID,
    data: LicenseViolationReportCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> LicenseViolationReportResponse:
    """Report a license violation on a marketplace design.

    Each user can only report a design for license violation once.
    Rate limited to 5 reports per hour per user.
    """
```

**Request schema:**

```python
class LicenseViolationReportCreate(BaseModel):
    """Schema for reporting a license violation."""
    violation_type: Annotated[str, Field(
        description="Type: unauthorized_remix, missing_attribution, commercial_misuse, share_alike_violation, other",
    )]
    description: Annotated[str, Field(min_length=10, max_length=2000)]
    evidence_url: Annotated[str | None, Field(max_length=2048, default=None)]

    @field_validator("violation_type")
    @classmethod
    def validate_violation_type(cls, v: str) -> str:
        valid_types = {e.value for e in LicenseViolationType}
        if v not in valid_types:
            raise ValueError(f"Invalid violation_type. Must be one of: {', '.join(valid_types)}")
        return v

    @field_validator("evidence_url")
    @classmethod
    def validate_evidence_url(cls, v: str | None) -> str | None:
        if v is not None:
            if not v.startswith(("https://", "http://")):
                raise ValueError("evidence_url must be a valid HTTP(S) URL")
        return v
```

**Response schema:**

```python
class LicenseViolationReportResponse(BaseModel):
    """Response after filing a license violation report."""
    id: UUID
    status: str
    created_at: datetime
```

**Audit:** `LICENSE_VIOLATION_REPORT` with context containing `design_id`, `violation_type`.

#### `POST /api/v2/admin/designs/{design_id}/takedown`

**Auth:** Admin required (`get_current_admin_user` from `app.api.deps`)
**Rate limit:** `design_operation_limit` (20/min)
**Audit:** `LICENSE_TAKEDOWN`

```python
@router.post(
    "/designs/{design_id}/takedown",
    response_model=TakedownResponse,
    dependencies=[Depends(design_operation_limit)],
)
@audit_log(
    action=AuditActions.LICENSE_TAKEDOWN,
    resource_type="design",
    resource_id_param="design_id",
    context_builder=lambda **kwargs: {"reason": kwargs.get("data", {}).reason},
)
async def admin_takedown_design(
    design_id: UUID,
    data: TakedownRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
) -> TakedownResponse:
    """Take down a design for license violation. Admin only."""
```

**Request schema:**

```python
class TakedownRequest(BaseModel):
    """Admin takedown request."""
    reason: Annotated[str, Field(min_length=10, max_length=1000)]
    violation_report_id: UUID | None = None
```

**Response schema:**

```python
class TakedownResponse(BaseModel):
    """Response after taking down a design."""
    design_id: UUID
    was_public: bool
    taken_down_at: datetime
    reason: str
```

#### `GET /api/v2/admin/license-violations`

**Auth:** Admin required
**Rate limit:** `standard_api_limit`
**Description:** List open license violation reports for admin review queue.

```python
@router.get(
    "/license-violations",
    response_model=PaginatedViolationReportsResponse,
)
async def list_license_violations(
    status_filter: str | None = Query(None, description="Filter by status: pending, reviewing, resolved, dismissed"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
) -> PaginatedViolationReportsResponse:
    """List license violation reports for admin review."""
```

---

## 6. Error Handling

### Error Response Patterns

All errors follow the existing FastAPI pattern of raising `HTTPException`:

| Scenario | Status Code | Detail |
|----------|-------------|--------|
| Invalid license_type value | 400 | `"Invalid license_type. Must be one of: ..."` |
| CUSTOM without text | 400 | `"custom_license_text is required when license_type is CUSTOM"` |
| Custom text with non-CUSTOM license | 400 | `"custom_license_text should only be set when license_type is CUSTOM"` |
| Share-alike violation on publish | 400 | `"The original design requires Share-Alike. Your remix must use license: CC-BY-SA-4.0"` |
| Remix blocked by license | 403 | `"This design's license does not allow remixing."` |
| Duplicate violation report | 400 | `"You have already reported this design for license violation"` |
| Design not found | 404 | `"Design not found"` |
| Not design owner (publish/update) | 403 | `"Design not found or not owned by you"` |
| Not admin (takedown) | 403 | `"Insufficient permissions"` |
| Not authenticated | 401 | `"Not authenticated"` |
| Rate limit exceeded | 429 | `"Rate limit exceeded. Please try again later."` |

### Custom License Text Validation

Beyond Pydantic's `max_length=5000`, the following validations apply:

1. **Strip leading/trailing whitespace**: `custom_license_text.strip()`
2. **Non-empty after strip**: Must have at least 10 characters of actual content.
3. **HTML stripping**: Remove all HTML tags before storage. Use `bleach.clean(text, tags=[], strip=True)` or a lightweight regex strip if bleach is not a dependency. **Decision: use `html.escape()` for display + store raw but validated text.** The frontend renders as plain text (never `dangerouslySetInnerHTML`).
4. **No script injection**: Pydantic string validation + frontend plain-text rendering is sufficient. No need for server-side HTML sanitization since we never render as HTML.

### Evidence URL Validation

- Must start with `https://` or `http://`.
- Max length: 2048 characters (enforced by Pydantic `Field(max_length=2048)`).
- No `javascript:`, `data:`, or other dangerous schemes — validated by prefix check.

---

## 7. Security Design

### 7.1 Authentication Requirements

| Endpoint | Auth | Dependency |
|----------|------|------------|
| `GET /api/v2/licenses/types` | None (public) | — |
| `GET /api/v2/marketplace/designs` | Optional | `get_current_user_optional` |
| `GET /api/v2/marketplace/designs/{id}` | Optional | `get_current_user_optional` |
| `POST /api/v2/marketplace/designs/{id}/publish` | Required | `get_current_user` |
| `POST /api/v2/marketplace/designs/{id}/remix` | Required | `get_current_user` |
| `GET /api/v2/licenses/my/published` | Required | `get_current_user` |
| `GET /api/v2/licenses/my/remixed` | Required | `get_current_user` |
| `POST /api/v2/marketplace/designs/{id}/report-violation` | Required | `get_current_user` |
| `POST /api/v2/admin/designs/{id}/takedown` | Admin | `get_current_admin_user` |
| `GET /api/v2/admin/license-violations` | Admin | `get_current_admin_user` |

### 7.2 Authorization Rules

| Action | Who Can Do It | Enforcement Point |
|--------|---------------|-------------------|
| Set license on design | Design owner only | `publish_design` endpoint: `Design.user_id == current_user.id` |
| Change license on design | Design owner only | Same as above |
| Remix a design | Any authenticated user (if license allows) | `remix_marketplace_design` endpoint + `LicenseService.check_remix_allowed()` |
| Remix own design (any license) | Design owner always | `check_remix_allowed` special case: owner bypass |
| Report license violation | Any authenticated user (not self-report) | `report_violation`: check `design.user_id != reporter.id` |
| Admin takedown | Admin/Super Admin only | `get_current_admin_user` dependency |
| View violation reports | Admin/Super Admin only | `get_current_admin_user` dependency |
| View own published licenses | Self only | `get_current_user` dependency, query filtered by `user_id` |
| View own remixed licenses | Self only | `get_current_user` dependency, query filtered by `user_id` |

### 7.3 Input Validation Rules

| Field | Validation | Layer |
|-------|-----------|-------|
| `license_type` | Must be valid `LicenseType` enum value | Pydantic `@field_validator` |
| `custom_license_text` | Max 5000 chars, min 10 chars when required, stripped | Pydantic `Field` + `@model_validator` |
| `custom_allows_remix` | Boolean, only meaningful with CUSTOM | Service layer |
| `violation_type` | Must be valid `LicenseViolationType` value | Pydantic `@field_validator` |
| `description` (violation) | Min 10, max 2000 chars | Pydantic `Field` |
| `evidence_url` | Max 2048 chars, must be HTTP(S) URL | Pydantic `@field_validator` |
| `reason` (takedown) | Min 10, max 1000 chars | Pydantic `Field` |
| `license_type` filter param | Must be valid or None | Endpoint validation |
| `page`, `page_size` | Standard pagination bounds (ge=1, le=100) | Pydantic `Query` |
| `tags` | List of strings, sanitized | Existing validation |
| `category` | Must be in VALID_CATEGORIES | Existing validation |

### 7.4 Rate Limiting Configuration

| Endpoint | Limiter | Requests | Window | Key |
|----------|---------|----------|--------|-----|
| `GET /api/v2/licenses/types` | `standard_api_limit` | 60 | 60s | user/IP |
| `POST .../publish` | `design_operation_limit` | 20 | 60s | user |
| `POST .../remix` | `expensive_operation_limit` | 10 | 60s | user |
| `POST .../report-violation` | `violation_report_limit` (NEW) | 5 | 3600s | user |
| `POST .../takedown` | `design_operation_limit` | 20 | 60s | user |
| `GET .../license-violations` | `standard_api_limit` | 60 | 60s | user |
| `GET .../my/published` | `standard_api_limit` | 60 | 60s | user |
| `GET .../my/remixed` | `standard_api_limit` | 60 | 60s | user |

**New rate limiter definition** in `backend/app/core/rate_limiter.py`:

```python
# License violation report rate limit (strict to prevent abuse)
violation_report_limit = RateLimiter(
    max_requests=5,
    window_seconds=3600,
    key_prefix="rate_limit:violation_report",
)
```

### 7.5 Audit Logging Events

Every license-related action produces an `AuditLog` entry:

| Action Constant | When | Context JSONB |
|-----------------|------|---------------|
| `LICENSE_SET` | First publish with license | `{license_type, design_id}` |
| `LICENSE_CHANGE` | License changed on re-publish | `{old_license, new_license, design_id}` |
| `LICENSE_REMIX_BLOCKED` | Remix attempt denied by license | `{design_id, license_type, reason}` |
| `LICENSE_REMIX_ALLOWED` | Remix successful with license check | `{design_id, remix_id, license_type}` |
| `LICENSE_ATTRIBUTION_GENERATED` | Attribution data created for remix | `{remix_id, parent_design_id, license_type}` |
| `LICENSE_VIOLATION_REPORT` | User reports license violation | `{design_id, violation_type, reporter_id}` |
| `LICENSE_TAKEDOWN` | Admin takes down design | `{design_id, reason, violation_report_id}` |
| `LICENSE_SHARE_ALIKE_ENFORCED` | Share-alike constraint applied on publish | `{design_id, parent_license, enforced_license}` |

All entries use `resource_type = "license"` for easy filtering in the audit log query indexes.

### 7.6 Data Sanitization

| Data | Sanitization Strategy |
|------|-----------------------|
| `custom_license_text` | Stored as-is (plain text). Frontend renders via `{text}` (React auto-escapes). Never use `dangerouslySetInnerHTML`. Server strips leading/trailing whitespace. |
| `description` (violation report) | Same as above — plain text, frontend escapes. |
| `evidence_url` | Validated as HTTP(S) URL. Rendered as `<a>` with `rel="noopener noreferrer" target="_blank"`. Do not render other URL schemes. |
| `attribution_text` | Generated server-side from trusted data (design name, author name). Stored in JSONB. Frontend renders as plain text. |
| `reason` (takedown) | Admin-only field. Stored as plain text. Only displayed to admins. |

### 7.7 Temporary File Handling

Phase 1 does not involve file generation. If Phase 2 introduces PDF license certificates:
- **Python:** Use `tempfile.NamedTemporaryFile(suffix=".pdf")` — **NEVER** hardcode `/tmp`.
- **Tests:** Use pytest `tmp_path` fixture.
- Generated PDFs should be uploaded to object storage (S3/MinIO) immediately and the temp file deleted in a `finally` block.

---

## 8. Integration Points

### 8.1 Marketplace Service Integration

The `LicenseService` is called from existing marketplace endpoints:

```
marketplace.py::publish_design
    └──> LicenseService.validate_license_for_publish()
    └──> Persist license fields on Design

marketplace.py::remix_marketplace_design
    └──> LicenseService.check_remix_allowed()
    └──> LicenseService.build_attribution()
    └──> Store attribution in remix.extra_data

marketplace.py::browse_designs
    └──> License filter query logic (inline, no service call needed)
```

### 8.2 Notification Service Integration

| Event | Notification | Channel |
|-------|-------------|---------|
| Design taken down | Owner notified: "Your design '{name}' has been taken down for a license violation." | In-app (via existing `NotificationService.create_notification`) |
| License violation reported | No notification to owner (prevents chilling effect; admin reviews first) | — |
| Remix created with attribution | Original author notified (existing remix notification if any) | Existing behavior |

**Integration pattern:**

```python
# In LicenseService.admin_takedown
notification_service = NotificationService(self.db)
await notification_service.create_notification(
    user_id=design.user_id,
    notification_type=NotificationType.DESIGN_UPDATE,  # or a new type if added
    title="Design Taken Down",
    message=f'Your design "{design.name}" has been taken down due to a license violation.',
    entity_type="design",
    entity_id=design.id,
)
```

### 8.3 Audit Service Integration

All `LicenseService` methods create `AuditLog` entries using the existing `AuditLog.log_success()` / `AuditLog.log_failure()` class methods. The `@audit_log` decorator is applied to the API endpoints where applicable (publish, takedown).

### 8.4 Content Report Integration

License violation reports are stored in the existing `content_reports` table with `target_type = "license_violation"`. The admin moderation queue (existing or future) shows license violations alongside other reports.

### 8.5 Existing Report Service Relationship

The existing `DesignReportService` (for general content reports) and the new license violation reporting share the same `content_reports` table but differ by `target_type`. They can coexist without conflict. The unique constraint `uq_report_user_target(reporter_id, target_type, target_id)` means a user can file both a content report (`target_type = "design"`) and a license violation report (`target_type = "license_violation"`) for the same design — this is correct behavior, as they are different types of complaints.

---

## 9. Database Indexes & Performance

### New Indexes

| Index Name | Table | Columns | Type | Condition |
|------------|-------|---------|------|-----------|
| `idx_designs_license_type` | `designs` | `license_type` | B-tree (partial) | `WHERE deleted_at IS NULL AND is_public = TRUE` |
| (existing) `idx_reports_target` | `content_reports` | `target_type, target_id` | B-tree | — |

### Query Performance Notes

1. **Browse with license filter:** The partial index on `license_type` covers the common query pattern (public + not deleted). Combined with the existing `idx_designs_public` index, the planner can efficiently filter.

2. **"Allows remix" filter:** This is a disjunction across multiple `license_type` values plus a CUSTOM condition. PostgreSQL can use the `idx_designs_license_type` index for the `IN(...)` clause. For the `AND(license_type = 'CUSTOM', custom_allows_remix = TRUE)` clause, a sequential scan of the CUSTOM subset is acceptable given the expected low cardinality of CUSTOM licenses.

3. **My Published Licenses:** Query is `WHERE user_id = X AND published_at IS NOT NULL AND deleted_at IS NULL`. The existing `idx_designs_user_id` (from the `user_id` indexed column) handles this efficiently.

4. **My Remixed Licenses:** Query is `WHERE user_id = X AND remixed_from_id IS NOT NULL AND deleted_at IS NULL`. The existing `user_id` index handles the primary filter; `remixed_from_id IS NOT NULL` is a secondary filter on the small result set.

5. **License violation reports (admin):** Query is `WHERE target_type = 'license_violation' AND status = 'pending'`. Covered by `idx_reports_target` + `idx_reports_status`.

---

## 10. File Inventory

### New Files

| File | Purpose |
|------|---------|
| `backend/app/core/licenses.py` | `LicenseType` enum, `LicenseInfo` dataclass, `LICENSE_METADATA` dict, helper functions |
| `backend/app/services/license_service.py` | `LicenseService` class with all license business logic |
| `backend/app/schemas/license.py` | Pydantic schemas: `LicenseTypeResponse`, `LicenseDetailResponse`, `LicenseViolationReportCreate`, `LicenseViolationReportResponse`, `TakedownRequest`, `TakedownResponse`, `PublishedLicenseItem`, `RemixedLicenseItem`, paginated responses |
| `backend/app/api/v2/licenses.py` | License API router: `/types`, `/my/published`, `/my/remixed` |
| `backend/app/api/v2/admin_licenses.py` | Admin license router: `/license-violations`, `/designs/{id}/takedown` |
| `backend/alembic/versions/029_design_license_columns.py` | Migration: add license columns to designs |
| `backend/alembic/versions/030_content_reports_evidence_url.py` | Migration: add evidence_url to content_reports |
| `backend/tests/core/test_licenses.py` | Tests for license catalog, helpers |
| `backend/tests/services/test_license_service.py` | Tests for LicenseService methods |
| `backend/tests/api/test_marketplace_license.py` | Integration tests for license endpoints |

### Modified Files

| File | Change |
|------|--------|
| `backend/app/models/design.py` | Add `license_type`, `custom_license_text`, `custom_allows_remix` columns |
| `backend/app/models/rating.py` | Add `LicenseViolationType` enum, `evidence_url` column on `ContentReport`, `LICENSE_VIOLATION` to `ReportTargetType` |
| `backend/app/models/audit.py` | Add license-related constants to `AuditActions` |
| `backend/app/schemas/marketplace.py` | Add `license_type` to `DesignSummaryResponse`, `license_info`/`attribution` to `MarketplaceDesignResponse`, update `PublishDesignRequest`/`PublishDesignResponse` |
| `backend/app/api/v2/marketplace.py` | Update `publish_design` (license persistence), `remix_marketplace_design` (license check + attribution), `browse_designs` (license filter params) |
| `backend/app/core/rate_limiter.py` | Add `violation_report_limit` |
| `backend/app/api/v2/__init__.py` (or router registration) | Register `licenses` and `admin_licenses` routers |

### Frontend Files (Architecture Only — Not Implemented Here)

| File | Purpose |
|------|---------|
| `frontend/src/types/license.ts` | TypeScript types mirroring backend schemas |
| `frontend/src/services/licenseApi.ts` | API client for license endpoints |
| `frontend/src/components/marketplace/LicenseSelector.tsx` | License dropdown + custom text area for publish dialog |
| `frontend/src/components/marketplace/LicenseBadge.tsx` | Compact license icon badge for design cards |
| `frontend/src/components/marketplace/LicenseDetail.tsx` | Full license info section for design detail page |
| `frontend/src/components/marketplace/LicenseViolationReportModal.tsx` | Report modal |
| `frontend/src/pages/MyLicensesPage.tsx` | "My Licenses" page with Published/Remixed tabs |
| `frontend/src/assets/licenses/` | CC badge SVGs |

---

## Appendix A: Decisions Changed from Strategy Spec

| Strategy Spec Proposed | Architecture Decision | Rationale |
|------------------------|----------------------|-----------|
| New `license_violation_reports` table | **Reuse `content_reports`** with `target_type = "license_violation"` | Existing table has all needed columns. Prevents table proliferation. Keeps moderation queue unified. |
| `evidence_url` only on violation table | **Add `evidence_url` to `content_reports`** globally | Useful for all report types (content, license, etc.). One migration, shared column. |
| No explicit `custom_allows_remix` column | **Add `custom_allows_remix` boolean on `designs`** | Needed for SQL-level filtering in browse queries. `extra_data` JSONB not directly index-friendly for this boolean. |
| Violation report as standalone service | **`LicenseService.report_violation()` method** delegates to `ContentReport` model | Follows existing pattern of `DesignReportService` wrapping `ContentReport`. Simpler service topology. |
| `POST /report-violation` on marketplace router | **Placed on marketplace router** at `POST /api/v2/marketplace/designs/{id}/report-violation` | Consistent with existing `POST .../report` endpoint pattern. |
| Admin endpoints at `/api/v2/admin/...` | **Confirmed** — separate admin router | Follows existing admin endpoint patterns and enables distinct middleware/auth. |
| No specific rate limit for violation reports | **5 per user per hour** | Prevents abuse/spam of the moderation queue. More restrictive than general API limit. |
