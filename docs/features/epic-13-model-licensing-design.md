# Epic 13: Model Licensing — Strategy & Design Specification

**Epic:** #18 · **Priority:** P2 · **Estimate:** ~13 story points
**Date:** 2026-02-25
**Status:** Draft

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Scope Recommendations](#2-scope-recommendations)
3. [License Type Catalog](#3-license-type-catalog)
4. [Refined User Stories](#4-refined-user-stories)
5. [UI/UX Design Specification](#5-uiux-design-specification)
6. [Data Model & API Design](#6-data-model--api-design)
7. [Security Considerations](#7-security-considerations)
8. [Dependency Map & Implementation Order](#8-dependency-map--implementation-order)

---

## 1. Executive Summary

This specification covers a model licensing system that allows designers to attach standard or custom licenses when publishing designs to the marketplace, surfaces license information to consumers, and enforces license terms (e.g., blocking remix when the license disallows it). The work builds on the existing remix tracking (`remixed_from_id`), marketplace publish flow, and audit logging infrastructure.

### Current State (validated against codebase)

| Capability | Status |
|---|---|
| Remix tracking (`remixed_from_id` on `Design`) | ✅ Exists |
| Content moderation (ADR-012) | ✅ Designed |
| Marketplace publish flow (`POST /api/v2/marketplace/designs/{id}/publish`) | ✅ Exists |
| Marketplace browse with filters (category, tags, search, sort) | ✅ Exists |
| Stripe payment integration (`PaymentHistory`, `PaymentService`) | ✅ Exists |
| Audit logging (`AuditLog` model with JSONB context) | ✅ Exists |
| License field on `Design` model | ❌ Missing |
| License selection in publish dialog | ❌ Missing |
| License display on marketplace cards/detail pages | ❌ Missing |
| License enforcement on remix | ❌ Missing |
| License templates | ❌ Missing |

---

## 2. Scope Recommendations

### Phase 1 — Initial Implementation (8 SP, recommended for Sprint 5-6)

| Story | SP | Rationale |
|---|---|---|
| **US-13.1** License Selection for Designs | 3 | Core feature; unblocks all other stories |
| **US-13.4** License Compliance Tracking | 3 | Enforcement must ship alongside selection; a license without enforcement is purely advisory |
| **US-13.3** License History & Downloads (partial) | 2 | Scoped to "My Licenses" view of *granted* licenses only (no purchases) |

### Phase 2 — Deferred (5 SP, Sprint 7+)

| Story | SP | Rationale |
|---|---|---|
| **US-13.2** Commercial License Purchase | 5 | Requires new Stripe product/price setup, PDF generation, email templates, and a new `LicensePurchase` table. High complexity relative to other stories. Defer until Phase 1 is validated and user demand confirmed. |
| **US-13.3** remaining scope (purchase certificates, download PDFs) | — | Depends on US-13.2 |

### Dependency Order (Phase 1)

```
US-13.1 (backend: license column + enum + schema)
    └──> US-13.1 (frontend: publish dialog + display)
            └──> US-13.4 (backend: remix enforcement + compliance logging)
                    └──> US-13.3 partial (frontend: "My Licenses" view)
```

---

## 3. License Type Catalog

### 3.1 Standard Licenses

| Key | Display Name | Permits Remix | Requires Attribution | Permits Commercial Use | Share-Alike Required |
|---|---|---|---|---|---|
| `CC-BY-4.0` | Creative Commons Attribution 4.0 | ✅ | ✅ | ✅ | ❌ |
| `CC-BY-SA-4.0` | Creative Commons Attribution-ShareAlike 4.0 | ✅ | ✅ | ✅ | ✅ |
| `CC-BY-NC-4.0` | Creative Commons Attribution-NonCommercial 4.0 | ✅ | ✅ | ❌ | ❌ |
| `CC-BY-NC-SA-4.0` | Creative Commons Attribution-NonCommercial-ShareAlike 4.0 | ✅ | ✅ | ❌ | ✅ |
| `CC-BY-ND-4.0` | Creative Commons Attribution-NoDerivatives 4.0 | ❌ | ✅ | ✅ | N/A |
| `CC-BY-NC-ND-4.0` | Creative Commons Attribution-NonCommercial-NoDerivatives 4.0 | ❌ | ✅ | ❌ | N/A |
| `CC0-1.0` | CC0 1.0 Universal (Public Domain) | ✅ | ❌ | ✅ | ❌ |
| `ALL-RIGHTS-RESERVED` | All Rights Reserved | ❌ | N/A | ❌ | N/A |

### 3.2 Custom License Option

Users may provide custom license text (up to 5 000 characters). When `license_type = "CUSTOM"`:
- `custom_license_text` is required
- Remix defaults to **blocked** unless the user explicitly opts in via `allows_remix: true`
- The platform displays the custom text on the design detail page

### 3.3 License Metadata Structure

Each license type maps to a static metadata record:

```python
LICENSE_METADATA: dict[str, LicenseInfo] = {
    "CC-BY-4.0": LicenseInfo(
        spdx_id="CC-BY-4.0",
        name="Creative Commons Attribution 4.0 International",
        url="https://creativecommons.org/licenses/by/4.0/",
        allows_remix=True,
        requires_attribution=True,
        allows_commercial=True,
        requires_share_alike=False,
        icon="cc-by",
    ),
    # ... etc.
}
```

This is a code constant (not a database table) so it ships with zero migration overhead and is easy to extend.

---

## 4. Refined User Stories

### US-13.1: License Selection for Designs (#98 — 3 SP)

> **As a designer**, I want to choose a license when publishing my design so that others know how they may use it.

#### Acceptance Criteria

**AC-1: License picker appears in publish flow**
- **Given** I am on the publish dialog for a design I own
- **When** the dialog loads
- **Then** I see a "License" section with a dropdown defaulting to "Creative Commons Attribution 4.0" (CC-BY-4.0)
- **And** the dropdown lists all 8 standard licenses plus "Custom"

**AC-2: Custom license text**
- **Given** I select "Custom" from the license dropdown
- **When** the selection changes
- **Then** a text area appears (max 5 000 chars) for custom license terms
- **And** a checkbox "Allow remixing" appears (default unchecked)
- **And** publishing is blocked until custom text is provided (validation error shown inline)

**AC-3: License persisted on publish**
- **Given** I have selected a license (standard or custom)
- **When** I submit the publish form
- **Then** the `license_type` (and optionally `custom_license_text`) is saved to the Design record
- **And** `published_at` is set

**AC-4: License displayed on marketplace design detail page**
- **Given** a published design with license_type `CC-BY-NC-4.0`
- **When** I view the design detail page
- **Then** I see the license badge icon, full name, and a link to the CC legal text
- **And** a summary line: "Remixing: Allowed · Commercial use: No · Attribution: Required"

**AC-5: License badge on marketplace cards**
- **Given** I am browsing the marketplace grid
- **When** a design card renders
- **Then** a small license icon/badge appears in the bottom-left corner of the card (e.g., CC icon)
- **And** hovering shows a tooltip with the license short name

**AC-6: License filter in marketplace browse**
- **Given** I am on the marketplace browse page
- **When** I open the filter panel
- **Then** I see a "License" multi-select filter with options: "Allow Remix", "Allow Commercial", "Public Domain", and all individual license types
- **And** selecting a filter updates the design list via the existing `browse_designs` query parameter mechanism

**AC-7: License editable before unpublish**
- **Given** a design I own is published
- **When** I navigate to its edit/publish settings
- **Then** I can change the license type
- **And** existing remixes are NOT retroactively affected (they were created under the prior license)

#### Edge Cases
- **No license selected:** Defaults to `CC-BY-4.0` — publish never proceeds without a license.
- **Re-publish after unpublish:** Previous license is pre-selected in dropdown.
- **Remix of publicly-licensed design is itself published:** The "Share-Alike" constraint is enforced (US-13.4).
- **Empty custom text with Custom selected:** Inline validation error, publish button disabled.

---

### US-13.4: License Compliance Tracking (#100 — 3 SP)

> **As a platform operator**, I want to enforce license compliance so that designers' IP is protected.

#### Acceptance Criteria

**AC-1: Remix blocked for NoDerivatives / All Rights Reserved**
- **Given** a published design with license `CC-BY-ND-4.0` or `ALL-RIGHTS-RESERVED`
- **When** a user calls `POST /api/v2/marketplace/designs/{id}/remix`
- **Then** the API returns `403 Forbidden` with body `{"detail": "This design's license does not allow remixing."}`
- **And** the frontend remix button is disabled with tooltip "Remixing not allowed by license"

**AC-2: Attribution auto-injected on remix**
- **Given** a design with any CC license that requires attribution
- **When** a remix is created
- **Then** the remix's `extra_data.attribution` is populated with:
  ```json
  {
    "original_design_id": "<uuid>",
    "original_design_name": "...",
    "original_author_name": "...",
    "license": "CC-BY-4.0",
    "attribution_text": "Based on \"<name>\" by <author>, licensed under CC-BY-4.0"
  }
  ```
- **And** this attribution is displayed on the remix's detail page

**AC-3: Share-Alike enforcement on publish**
- **Given** a remix of a design originally licensed CC-BY-SA-4.0
- **When** the remix author publishes the remix
- **Then** the license selector restricts choices to `CC-BY-SA-4.0` only (same or compatible)
- **And** a notice reads: "The original design requires Share-Alike. Your remix must use the same license."

**AC-4: License violation reporting**
- **Given** I am viewing a design that I believe violates its license
- **When** I click "Report License Violation" (in the design's action menu)
- **Then** a modal appears with fields: violation type (unauthorized remix, missing attribution, commercial misuse), description (required, max 2 000 chars)
- **And** submitting creates a `LicenseViolationReport` record and an `AuditLog` entry with `action = "license_violation_report"`

**AC-5: Compliance audit log**
- **Given** any license-related action occurs (remix blocked, attribution auto-generated, violation reported, license changed)
- **When** the action completes
- **Then** an `AuditLog` record is created with `resource_type = "license"` and relevant context JSONB

**AC-6: Admin takedown endpoint (API only — no UI in Phase 1)**
- **Given** an admin reviews a license violation report
- **When** they call `POST /api/v2/admin/designs/{id}/takedown` with reason
- **Then** the design's `is_public` is set to `false`, `published_at` is cleared
- **And** an `AuditLog` entry is created with `action = "license_takedown"`
- **And** the design owner is notified (existing notification system or log only for Phase 1)

#### Edge Cases
- **Original design deleted after remix:** Attribution still references original by ID/name. No retroactive enforcement.
- **License changed after remixes exist:** Existing remixes remain valid under the license at time of remix. New remixes follow new license.
- **Remix of a remix:** Attribution chain is maintained—`extra_data.attribution` includes the full chain.
- **User attempts to remix their own ND-licensed design:** Allowed (owner can always remix own work).

---

### US-13.3: License History & Downloads (#101 — 2 SP, Phase 1 partial)

> **As a user**, I want to see licenses associated with my designs (granted and received).

#### Acceptance Criteria (Phase 1 Scope)

**AC-1: "My Licenses" page accessible from user menu**
- **Given** I am logged in
- **When** I navigate to `/licenses` (or click "My Licenses" in the user dropdown)
- **Then** I see two tabs: "Designs I Published" and "Designs I Remixed"

**AC-2: "Designs I Published" tab**
- **Given** I have published designs with licenses
- **When** I view this tab
- **Then** I see a table: Design Name, License Type, Published Date, Remix Count, Status (Published/Unpublished)
- **And** clicking a row navigates to the marketplace detail page

**AC-3: "Designs I Remixed" tab**
- **Given** I have remixed designs from the marketplace
- **When** I view this tab
- **Then** I see a table: Remix Name, Original Design, Original Author, License, Remixed Date
- **And** the "License" column shows what terms I must follow
- **And** clicking "Original Design" navigates to it (or shows "Design removed" if deleted)

**AC-4: Filter by license type**
- **Given** I am on either tab
- **When** I use the license type filter dropdown
- **Then** the table filters to show only rows matching the selected license

**AC-5: Empty states**
- **Given** I have no published designs / no remixes
- **When** I view the respective tab
- **Then** I see a friendly empty state: "You haven't published any designs yet" / "You haven't remixed any designs yet" with a CTA to browse the marketplace

#### Deferred to Phase 2
- License certificate PDF download
- Commercial license purchase history
- License grant tracking for purchased licenses

---

### US-13.2: Commercial License Purchase (#99 — 5 SP, Deferred to Phase 2)

> **As a buyer**, I want to purchase a commercial license for a design so that I can use it in commercial products.

#### Acceptance Criteria (for Phase 2 planning)

**AC-1: Commercial license option on design**
- **Given** a designer publishes with a non-commercial license (CC-BY-NC-*)
- **When** the designer enables "Offer commercial license" and sets a price
- **Then** the design detail page shows a "Buy Commercial License" button with the price

**AC-2: Purchase flow**
- **Given** I click "Buy Commercial License"
- **When** the purchase modal opens
- **Then** I see the price, license terms summary, and a Stripe checkout
- **And** upon successful payment, a `LicensePurchase` record is created
- **And** a `PaymentHistory` record is created with `payment_type = "license_purchase"`

**AC-3: License certificate PDF**
- **Given** I have purchased a commercial license
- **When** I visit "My Licenses" → "Purchased Licenses"
- **Then** I can download a PDF certificate containing: license ID, design name, purchaser, date, terms

**AC-4: Email confirmation**
- **Given** a purchase succeeds
- **When** payment is confirmed
- **Then** I receive an email with the license certificate attached

**AC-5: Revenue tracking**
- **Given** a designer has commercial license purchases
- **When** they view their earnings dashboard
- **Then** license revenue is shown separately from other income

#### Edge Cases
- **Designer changes price** — existing purchases honored at original price
- **Designer unpublishes design** — purchased licenses remain valid
- **Refund requested** — standard Stripe refund flow; `LicensePurchase` status updated
- **Dispute** — handled via existing Stripe dispute webhook pipeline

---

## 5. UI/UX Design Specification

### 5.1 License Selection in Publish Flow

**Location:** Existing publish dialog (triggered when user clicks "Publish" on their design)

```
┌─────────────────────────────────────────────────┐
│          Publish Design to Marketplace           │
├─────────────────────────────────────────────────┤
│                                                   │
│  Category    [▼ Electronics Enclosures        ]  │
│                                                   │
│  Tags        [iot] [raspberry-pi] [x]    [+]    │
│                                                   │
│  ── License ─────────────────────────────────── │
│                                                   │
│  License Type  [▼ CC Attribution 4.0 (CC-BY)  ]  │
│                                                   │
│  ┌─────────────────────────────────────────┐     │
│  │ ✅ Allows remixing                       │     │
│  │ ✅ Allows commercial use                 │     │
│  │ ✅ Requires attribution                  │     │
│  │ ❌ Requires share-alike                  │     │
│  │                                           │     │
│  │ 🔗 View full license text                │     │
│  └─────────────────────────────────────────┘     │
│                                                   │
│  ┌─── When "Custom" selected: ──────────────┐   │
│  │ Custom License Text*                       │   │
│  │ ┌───────────────────────────────────────┐ │   │
│  │ │                                       │ │   │
│  │ │ (textarea, max 5000 chars)            │ │   │
│  │ │                                       │ │   │
│  │ └───────────────────────────────────────┘ │   │
│  │ ☐ Allow remixing of this design           │   │
│  └───────────────────────────────────────────┘   │
│                                                   │
│         [Cancel]              [Publish]           │
└─────────────────────────────────────────────────┘
```

**Behavior:**
- Dropdown changes update the permission summary box in real-time
- "View full license text" opens CC URL in new tab (standard) or expands custom text (custom)
- Default selection: `CC-BY-4.0`
- The permission summary uses green ✅ / red ❌ icons for scan-ability

### 5.2 License Display on Marketplace Cards

```
┌────────────────────────────┐
│  ┌──────────────────────┐  │
│  │                      │  │
│  │    [thumbnail]       │  │
│  │                      │  │
│  └──────────────────────┘  │
│  Pi Zero Enclosure         │
│  by DesignerName           │
│  ⭐ 4.2 · ♡ 23 · ↗ 8     │
│  [CC-BY] ·  Electronics    │  ← license icon badge
└────────────────────────────┘
```

- **Badge:** Small icon (16×16) representing the license family
  - CC licenses: official CC icon variants
  - All Rights Reserved: 🔒 lock icon
  - Custom: 📄 document icon
- **Tooltip on hover:** "Licensed under CC Attribution 4.0 — Remix allowed"

### 5.3 License Display on Design Detail Page

Below the design header (title, author, stats), add a **License section**:

```
── License ────────────────────────────────────────
[CC-BY icon]  Creative Commons Attribution 4.0

  Remixing:         ✅ Allowed
  Commercial Use:   ✅ Allowed
  Attribution:      ✅ Required
  Share-Alike:      ❌ Not required

  🔗 View full legal text
───────────────────────────────────────────────────
```

For custom licenses, replace the summary with:
```
── License ────────────────────────────────────────
[📄]  Custom License

  Remixing:  ✅ Allowed / ❌ Not allowed

  ▼ View license terms
  ┌─────────────────────────────────────────────┐
  │ [Custom license text displayed here...]      │
  └─────────────────────────────────────────────┘
───────────────────────────────────────────────────
```

### 5.4 License Filter in Marketplace Browse

Add to the existing filter sidebar (which already has Category and Sort):

```
── Filters ─────────────────
  Category  [▼ All         ]
  Sort      [▼ Popular     ]

  License Permissions:
    ☐ Allows Remix
    ☐ Allows Commercial Use
    ☐ Public Domain (CC0)

  License Type:
    ☐ CC-BY
    ☐ CC-BY-SA
    ☐ CC-BY-NC
    ☐ CC-BY-NC-SA
    ☐ CC-BY-ND
    ☐ CC-BY-NC-ND
    ☐ CC0
    ☐ All Rights Reserved
    ☐ Custom
────────────────────────────
```

**API mapping:** New query parameters on `GET /api/v2/marketplace/designs`:
- `license_type: str | None` — filter by exact license type
- `allows_remix: bool | None` — filter by remix permission
- `allows_commercial: bool | None` — filter by commercial permission

### 5.5 Remix Blocked State

When a user visits a design detail page for a non-remixable design:

```
[🔒 Remix Not Available]  (disabled button, gray)
Tooltip: "This design is licensed under All Rights Reserved
          and does not permit remixing."
```

When a user programmatically attempts remix via API:
```json
{
  "detail": "This design's license does not allow remixing.",
  "license_type": "ALL-RIGHTS-RESERVED",
  "license_url": null
}
```

### 5.6 "My Licenses" Page

**Route:** `/licenses`
**Navigation:** User dropdown menu → "My Licenses"

```
┌──────────────────────────────────────────────────────────┐
│  My Licenses                                              │
│                                                            │
│  [Designs I Published]  [Designs I Remixed]               │
│  ═══════════════════                                      │
│                                                            │
│  License Type: [▼ All  ]                                  │
│                                                            │
│  ┌──────────────────────────────────────────────────────┐ │
│  │ Name           │ License    │ Published  │ Remixes   │ │
│  ├──────────────────────────────────────────────────────┤ │
│  │ Pi Zero Case   │ CC-BY-4.0  │ 2026-01-15 │ 12       │ │
│  │ Sensor Mount   │ CC-BY-SA   │ 2026-02-01 │ 3        │ │
│  │ Custom Box     │ Custom     │ 2026-02-20 │ 0        │ │
│  └──────────────────────────────────────────────────────┘ │
│                                                            │
│  Showing 3 of 3                                           │
└──────────────────────────────────────────────────────────┘
```

**"Designs I Remixed" tab:**
```
│  │ Remix Name     │ Original       │ Author   │ License    │ Date       │
│  ├────────────────────────────────────────────────────────────────────── │
│  │ Pi Case (Remix)│ Pi Zero Case   │ @alice   │ CC-BY-4.0  │ 2026-02-10 │
│  │ My Sensor      │ Sensor Mount   │ @bob     │ CC-BY-SA   │ 2026-02-15 │
```

### 5.7 License Violation Report Modal

**Trigger:** Three-dot menu on design detail page → "Report License Violation"

```
┌──────────────────────────────────────────────┐
│  Report License Violation                     │
│                                                │
│  Design: Pi Zero Case by @alice               │
│                                                │
│  Violation Type*                               │
│  [▼ Unauthorized Remix                      ] │
│                                                │
│     Options:                                   │
│     - Unauthorized Remix                       │
│     - Missing Attribution                      │
│     - Commercial Misuse                        │
│     - Other                                    │
│                                                │
│  Description*                                  │
│  ┌──────────────────────────────────────────┐ │
│  │                                          │ │
│  │ (max 2000 chars)                         │ │
│  │                                          │ │
│  └──────────────────────────────────────────┘ │
│                                                │
│  Evidence URL (optional)                       │
│  [__________________________________________]  │
│                                                │
│         [Cancel]         [Submit Report]       │
└──────────────────────────────────────────────┘
```

---

## 6. Data Model & API Design

### 6.1 Database Changes

#### New Column on `designs` Table

```python
# backend/app/models/design.py — add to Design class

# License information
license_type: Mapped[str | None] = mapped_column(
    String(30),
    nullable=True,
    index=True,
    doc="SPDX-like license identifier or CUSTOM / ALL-RIGHTS-RESERVED",
)
custom_license_text: Mapped[str | None] = mapped_column(
    Text,
    nullable=True,
    doc="Custom license terms when license_type is CUSTOM",
)
```

**Alembic migration:** Add two nullable columns. No data backfill needed — existing published designs will have `license_type = NULL` and should be treated as unlicensed (display "No license specified" in UI).

#### New Enum (code constant, not DB enum)

```python
# backend/app/core/licenses.py

from enum import StrEnum

class LicenseType(StrEnum):
    CC_BY_4_0 = "CC-BY-4.0"
    CC_BY_SA_4_0 = "CC-BY-SA-4.0"
    CC_BY_NC_4_0 = "CC-BY-NC-4.0"
    CC_BY_NC_SA_4_0 = "CC-BY-NC-SA-4.0"
    CC_BY_ND_4_0 = "CC-BY-ND-4.0"
    CC_BY_NC_ND_4_0 = "CC-BY-NC-ND-4.0"
    CC0_1_0 = "CC0-1.0"
    ALL_RIGHTS_RESERVED = "ALL-RIGHTS-RESERVED"
    CUSTOM = "CUSTOM"
```

#### New Table: `license_violation_reports`

```python
class LicenseViolationReport(Base, TimestampMixin):
    __tablename__ = "license_violation_reports"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    reporter_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("users.id"))
    design_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("designs.id"))
    violation_type: Mapped[str] = mapped_column(String(50))  # unauthorized_remix, missing_attribution, commercial_misuse, other
    description: Mapped[str] = mapped_column(Text)
    evidence_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="open")  # open, investigating, resolved, dismissed
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolved_by: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    resolution_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
```

#### Phase 2 Only: `license_purchases` Table

```python
class LicensePurchase(Base, TimestampMixin):
    __tablename__ = "license_purchases"

    id: Mapped[UUID]  # PK
    buyer_id: Mapped[UUID]  # FK users
    design_id: Mapped[UUID]  # FK designs
    seller_id: Mapped[UUID]  # FK users (design owner)
    payment_id: Mapped[UUID]  # FK payment_history
    license_type: Mapped[str]  # "commercial"
    amount_cents: Mapped[int]
    currency: Mapped[str]
    certificate_url: Mapped[str | None]
    status: Mapped[str]  # active, revoked, refunded
```

### 6.2 Schema Changes

#### Updated `PublishDesignRequest`

```python
class PublishDesignRequest(BaseModel):
    category: Annotated[str | None, Field(max_length=50, default=None)]
    tags: list[str] = []
    is_starter: bool = False
    license_type: Annotated[str, Field(
        default="CC-BY-4.0",
        description="License for the design. One of: CC-BY-4.0, CC-BY-SA-4.0, CC-BY-NC-4.0, CC-BY-NC-SA-4.0, CC-BY-ND-4.0, CC-BY-NC-ND-4.0, CC0-1.0, ALL-RIGHTS-RESERVED, CUSTOM",
    )]
    custom_license_text: Annotated[str | None, Field(
        max_length=5000,
        default=None,
        description="Required when license_type is CUSTOM",
    )]
```

**Validation:** Custom validator ensures `custom_license_text` is provided when `license_type == "CUSTOM"`.

#### Updated Response Schemas

```python
class LicenseInfo(BaseModel):
    """License metadata for display."""
    license_type: str | None
    license_name: str | None
    license_url: str | None
    allows_remix: bool
    requires_attribution: bool
    allows_commercial: bool
    requires_share_alike: bool
    custom_license_text: str | None = None


class DesignSummaryResponse(BaseModel):
    # ... existing fields ...
    license_type: str | None = None  # Add


class MarketplaceDesignResponse(DesignSummaryResponse):
    # ... existing fields ...
    license_info: LicenseInfo | None = None  # Full license detail on detail page
```

### 6.3 API Endpoints

#### Updated Endpoints

| Method | Path | Change |
|---|---|---|
| `POST` | `/api/v2/marketplace/designs/{id}/publish` | Accept `license_type`, `custom_license_text` |
| `GET` | `/api/v2/marketplace/designs` | New query params: `license_type`, `allows_remix`, `allows_commercial` |
| `GET` | `/api/v2/marketplace/designs/{id}` | Return `license_info` in response |
| `POST` | `/api/v2/marketplace/designs/{id}/remix` | Check license before remix; inject attribution |

#### New Endpoints

| Method | Path | Description | Auth |
|---|---|---|---|
| `GET` | `/api/v2/licenses/types` | List all supported licenses with metadata | Public |
| `GET` | `/api/v2/licenses/my/published` | Paginated list of user's published designs with license info | Required |
| `GET` | `/api/v2/licenses/my/remixed` | Paginated list of user's remixed designs with original license info | Required |
| `POST` | `/api/v2/marketplace/designs/{id}/report-violation` | Report a license violation | Required |
| `POST` | `/api/v2/admin/designs/{id}/takedown` | Admin takedown for license violation | Admin |
| `GET` | `/api/v2/admin/license-violations` | List open violation reports (Phase 1: API only) | Admin |

### 6.4 Service Layer

```
backend/app/core/licenses.py          — LicenseType enum, LICENSE_METADATA constant, helper functions
backend/app/services/license_service.py — LicenseService class
  ├── validate_license_for_publish()   — Validate license selection, enforce share-alike on remixes
  ├── check_remix_allowed()            — Return bool + reason; called by remix endpoint
  ├── build_attribution()              — Generate attribution data for remix extra_data
  ├── report_violation()               — Create LicenseViolationReport + AuditLog
  └── takedown_design()                — Admin action: unpublish + audit log
```

---

## 7. Security Considerations

| Concern | Mitigation |
|---|---|
| **Input validation** | `license_type` validated against `LicenseType` enum; `custom_license_text` sanitized (strip HTML, max length); `violation_type` validated against allowed values |
| **Authorization** | Only design owner can set/change license; only authenticated users can report violations; only admins can execute takedowns |
| **Rate limiting** | Violation reports rate-limited to 5 per user per hour (prevent abuse) |
| **Data integrity** | License at time of remix is captured in remix's `extra_data.attribution`; retroactive license changes don't affect existing remixes |
| **Audit trail** | All license-related actions logged via `AuditLog` with `resource_type = "license"` |
| **XSS prevention** | Custom license text rendered as plain text (never `dangerouslySetInnerHTML`); escaped in all contexts |
| **Temporary files** | If Phase 2 PDF generation is implemented, use `tempfile.NamedTemporaryFile()` per project requirements — never `/tmp` |

---

## 8. Dependency Map & Implementation Order

### Phase 1 Implementation Sequence

```
Step 1 (Backend Foundation) ─────────────────────────────────
  ├─ Create backend/app/core/licenses.py (enum + metadata)
  ├─ Add license_type, custom_license_text columns to Design
  ├─ Alembic migration
  ├─ Update PublishDesignRequest schema (+ validation)
  ├─ Update response schemas (DesignSummaryResponse, MarketplaceDesignResponse)
  └─ GET /api/v2/licenses/types endpoint

Step 2 (Backend Enforcement) ────────────────────────────────
  ├─ Create backend/app/services/license_service.py
  ├─ Update publish endpoint to persist license
  ├─ Update remix endpoint with license check + attribution
  ├─ Update browse endpoint with license filter params
  ├─ Create LicenseViolationReport model + migration
  ├─ POST /report-violation endpoint
  └─ POST /admin/takedown endpoint

Step 3 (Frontend: Publish + Display) ───────────────────────
  ├─ Add LicenseType types to frontend/src/types/marketplace.ts
  ├─ Create LicenseSelector component
  ├─ Integrate into publish dialog
  ├─ Add license badge to DesignCard component
  ├─ Add license info section to design detail page
  ├─ Add license filters to marketplace browse

Step 4 (Frontend: My Licenses + Reporting) ─────────────────
  ├─ Create MyLicensesPage component with tabs
  ├─ Create LicenseViolationReportModal component
  ├─ Integrate report button on design detail page
  └─ Update remix button with disabled state for ND licenses

Step 5 (Testing) ───────────────────────────────────────────
  ├─ Backend: pytest for license_service, updated endpoints
  ├─ Frontend: Vitest for LicenseSelector, DesignCard badge
  └─ E2E: Playwright for publish-with-license, remix-blocked flows
```

### Test Matrix (Phase 1)

| Test | Type | File |
|---|---|---|
| License enum + metadata accessors | Unit | `backend/tests/core/test_licenses.py` |
| `validate_license_for_publish` — all standard types | Unit | `backend/tests/services/test_license_service.py` |
| `validate_license_for_publish` — custom without text → error | Unit | `backend/tests/services/test_license_service.py` |
| `check_remix_allowed` — ND license → blocked | Unit | `backend/tests/services/test_license_service.py` |
| `check_remix_allowed` — CC-BY license → allowed | Unit | `backend/tests/services/test_license_service.py` |
| `build_attribution` — correct structure | Unit | `backend/tests/services/test_license_service.py` |
| Share-alike enforcement on remix publish | Unit | `backend/tests/services/test_license_service.py` |
| Publish endpoint with license | Integration | `backend/tests/api/test_marketplace_license.py` |
| Remix endpoint blocked by license | Integration | `backend/tests/api/test_marketplace_license.py` |
| Browse with license filter | Integration | `backend/tests/api/test_marketplace_license.py` |
| Violation report creation | Integration | `backend/tests/api/test_marketplace_license.py` |
| Admin takedown | Integration | `backend/tests/api/test_marketplace_license.py` |
| `LicenseSelector` renders all options | Unit | `frontend/src/components/marketplace/LicenseSelector.test.tsx` |
| `LicenseSelector` shows custom text field | Unit | `frontend/src/components/marketplace/LicenseSelector.test.tsx` |
| `DesignCard` shows license badge | Unit | `frontend/src/components/marketplace/DesignCard.test.tsx` |
| Publish flow with license selection | E2E | `frontend/e2e/marketplace-license.spec.ts` |
| Remix blocked by license | E2E | `frontend/e2e/marketplace-license.spec.ts` |

---

## Appendix A: License Icons

Use official Creative Commons icon assets (`cc-by`, `cc-by-sa`, `cc-by-nc`, etc.) from the [CC Downloads page](https://creativecommons.org/about/downloads/). For compact badges, use 80×15 PNG or inline SVG. The project already uses `lucide-react` icons; supplement with CC-specific SVGs in `frontend/src/assets/licenses/`.

| License | Icon Strategy |
|---|---|
| CC-* variants | Official CC badge SVGs |
| CC0 | CC zero badge SVG |
| All Rights Reserved | `lucide-react` `Lock` icon |
| Custom | `lucide-react` `FileText` icon |

## Appendix B: Future Considerations (Out of Scope)

- **License versioning** — tracking license version history per design (currently, license at publish time is the record of truth)
- **License compatibility matrix** — automatic compatibility checking between licenses (e.g., can a CC-BY-NC remix be re-licensed as CC-BY?)
- **Bulk license change** — changing license on multiple designs at once
- **DMCA integration** — formal DMCA takedown process with counter-notification
- **License analytics dashboard** — statistics on license usage across the platform
