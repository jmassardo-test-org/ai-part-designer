# Epic 20: Marketplace & Sharing — Technical Architecture Spec

**Status:** Draft  
**Date:** 2026-02-25  
**Authors:** Architecture & Security Agent  
**Epic:** Epic 20 — Marketplace & Sharing (11 stories, 3 parallel tracks)

---

## Table of Contents

1. [Overview & Parallel Tracks](#1-overview--parallel-tracks)
2. [Data Model Design](#2-data-model-design)
3. [Migration Strategy](#3-migration-strategy)
4. [API Endpoint Design](#4-api-endpoint-design)
5. [Service Layer Design](#5-service-layer-design)
6. [Security Architecture](#6-security-architecture)
7. [Frontend Component Architecture](#7-frontend-component-architecture)
8. [Database Indexes](#8-database-indexes)
9. [File Inventory](#9-file-inventory)

---

## 1. Overview & Parallel Tracks

Three independent work streams that can proceed in parallel:

| Track | Scope | New Files | Dependencies |
|-------|-------|-----------|--------------|
| **A — Ratings & Reviews** | `DesignRating` model, rating endpoints, `RatingSummary` widget | 6 backend, 4 frontend | `Design` model `avg_rating`/`total_ratings` columns |
| **B — Comments & Threads** | `DesignComment` model, comment endpoints, `CommentSection` widget | 6 backend, 5 frontend | None (standalone) |
| **C — Remix, Report, Views** | Marketplace remix endpoint, report endpoint, view tracking | 3 backend, 3 frontend | Existing `starters.py` remix pattern |

Tracks A and B share a single migration touchpoint on the `designs` table (adding `avg_rating` and `total_ratings` columns). Coordinate via separate migrations with explicit ordering.

---

## 2. Data Model Design

### 2.1 `DesignRating` — New Model

**File:** `backend/app/models/design_rating.py`

Mirrors `TemplateRating` from [backend/app/models/rating.py](../backend/app/models/rating.py#L44).

```python
class DesignRating(Base, TimestampMixin):
    __tablename__ = "design_ratings"

    id: Mapped[UUID]              # PK, uuid4
    design_id: Mapped[UUID]       # FK → designs.id, CASCADE, indexed
    user_id: Mapped[UUID]         # FK → users.id, CASCADE, indexed
    rating: Mapped[int]           # Integer, NOT NULL
    review: Mapped[str | None]    # Text, nullable

    # Relationships
    design: Mapped["Design"]      # back_populates="ratings"
    user: Mapped["User"]          # back_populates="design_ratings"

    __table_args__ = (
        UniqueConstraint("design_id", "user_id", name="uq_design_rating_user"),
        CheckConstraint("rating >= 1 AND rating <= 5", name="ck_design_rating_range"),
        Index("idx_design_ratings_design", "design_id"),
        Index("idx_design_ratings_user", "user_id"),
    )
```

### 2.2 `DesignComment` — New Model

**File:** `backend/app/models/design_comment.py`

Mirrors `TemplateComment` from [backend/app/models/rating.py](../backend/app/models/rating.py#L166).

```python
class DesignComment(Base, TimestampMixin):
    __tablename__ = "design_comments"

    id: Mapped[UUID]                    # PK, uuid4
    design_id: Mapped[UUID]             # FK → designs.id, CASCADE, indexed
    user_id: Mapped[UUID]               # FK → users.id, CASCADE, indexed
    parent_id: Mapped[UUID | None]      # FK → design_comments.id, CASCADE, indexed (threading)
    content: Mapped[str]                # Text, NOT NULL
    is_hidden: Mapped[bool]             # default=False
    hidden_by_id: Mapped[UUID | None]   # FK → users.id, SET NULL
    hidden_at: Mapped[datetime | None]
    hidden_reason: Mapped[str | None]   # String(255)
    is_edited: Mapped[bool]             # default=False
    edited_at: Mapped[datetime | None]

    # Relationships
    design: Mapped["Design"]                    # back_populates="comments"
    user: Mapped["User"]                        # foreign_keys=[user_id]
    parent: Mapped["DesignComment | None"]      # remote_side=[id], back_populates="replies"
    replies: Mapped[list["DesignComment"]]      # back_populates="parent", cascade="all, delete-orphan"
    hidden_by: Mapped["User | None"]            # foreign_keys=[hidden_by_id]

    __table_args__ = (
        Index("idx_design_comments_design", "design_id"),
        Index("idx_design_comments_user", "user_id"),
        Index("idx_design_comments_parent", "parent_id"),
        Index("idx_design_comments_design_created", "design_id", "created_at"),
    )
```

### 2.3 `Design` Model Additions

**File:** `backend/app/models/design.py` — add two columns after existing `remix_count`:

```python
# Cached rating stats (denormalized for query performance)
avg_rating: Mapped[float | None] = mapped_column(
    nullable=True,
    default=None,
)
total_ratings: Mapped[int] = mapped_column(
    Integer,
    nullable=False,
    default=0,
)
```

Add relationships:

```python
ratings: Mapped[list["DesignRating"]] = relationship(
    "DesignRating", back_populates="design", lazy="dynamic", cascade="all, delete-orphan",
)
comments: Mapped[list["DesignComment"]] = relationship(
    "DesignComment", back_populates="design", lazy="dynamic", cascade="all, delete-orphan",
)
```

### 2.4 `User` Model Additions

Add back-populates relationships in `backend/app/models/user.py`:

```python
design_ratings: Mapped[list["DesignRating"]] = relationship(
    "DesignRating", back_populates="user", lazy="dynamic",
)
design_comments: Mapped[list["DesignComment"]] = relationship(
    "DesignComment", back_populates="user", foreign_keys="DesignComment.user_id", lazy="dynamic",
)
```

### 2.5 `ContentReport` — Extend Existing

The existing `ContentReport` model already supports `target_type = "design"` — no model changes needed. The `ReportTargetType` enum already includes `DESIGN = "design"`.

---

## 3. Migration Strategy

**Two separate migrations** for independent rollback:

### Migration 1: Ratings (`018_design_ratings.py`)

```sql
-- Up
CREATE TABLE design_ratings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    design_id UUID NOT NULL REFERENCES designs(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    rating INTEGER NOT NULL,
    review TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_design_rating_user UNIQUE (design_id, user_id),
    CONSTRAINT ck_design_rating_range CHECK (rating >= 1 AND rating <= 5)
);

CREATE INDEX idx_design_ratings_design ON design_ratings(design_id);
CREATE INDEX idx_design_ratings_user ON design_ratings(user_id);

-- Add rating cache columns to designs
ALTER TABLE designs ADD COLUMN avg_rating DOUBLE PRECISION;
ALTER TABLE designs ADD COLUMN total_ratings INTEGER NOT NULL DEFAULT 0;

-- Partial index for marketplace sort-by-rating
CREATE INDEX idx_designs_avg_rating_marketplace
    ON designs(avg_rating DESC NULLS LAST)
    WHERE is_public = TRUE AND published_at IS NOT NULL AND deleted_at IS NULL;

-- Down
DROP INDEX IF EXISTS idx_designs_avg_rating_marketplace;
ALTER TABLE designs DROP COLUMN IF EXISTS total_ratings;
ALTER TABLE designs DROP COLUMN IF EXISTS avg_rating;
DROP TABLE IF EXISTS design_ratings;
```

### Migration 2: Comments (`019_design_comments.py`)

```sql
-- Up
CREATE TABLE design_comments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    design_id UUID NOT NULL REFERENCES designs(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    parent_id UUID REFERENCES design_comments(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    is_hidden BOOLEAN NOT NULL DEFAULT FALSE,
    hidden_by_id UUID REFERENCES users(id) ON DELETE SET NULL,
    hidden_at TIMESTAMPTZ,
    hidden_reason VARCHAR(255),
    is_edited BOOLEAN NOT NULL DEFAULT FALSE,
    edited_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_design_comments_design ON design_comments(design_id);
CREATE INDEX idx_design_comments_user ON design_comments(user_id);
CREATE INDEX idx_design_comments_parent ON design_comments(parent_id);
CREATE INDEX idx_design_comments_design_created ON design_comments(design_id, created_at);

-- Down
DROP TABLE IF EXISTS design_comments;
```

**Ordering:** Migration 1 runs before Migration 2 (numbering enforces it). Migration 2 has no dependency on Migration 1.

---

## 4. API Endpoint Design

All endpoints are sub-routes of the marketplace design resource. Router prefix: `/api/v2/marketplace/designs/{design_id}`.

**Router file:** `backend/app/api/v2/marketplace_design_social.py`

### 4.1 Rating Endpoints

| Method | Path | Auth | Description | Status Codes |
|--------|------|------|-------------|--------------|
| `POST` | `/ratings` | Required | Create or update own rating | 200, 400, 401, 403, 404 |
| `GET` | `/ratings` | Public | List ratings (paginated) | 200, 404 |
| `GET` | `/ratings/summary` | Public | Avg + distribution | 200, 404 |
| `GET` | `/ratings/me` | Required | User's own rating | 200, 401, 404 |
| `DELETE` | `/ratings` | Required | Delete own rating | 204, 401, 404 |

#### Request/Response Schemas

**File:** `backend/app/schemas/design_social.py`

```python
# --- Rating Schemas ---

class DesignRatingCreate(BaseModel):
    """Create or update a design rating."""
    rating: Annotated[int, Field(ge=1, le=5, description="Rating 1-5 stars")]
    review: Annotated[str | None, Field(max_length=2000, default=None)]

class DesignRatingResponse(BaseModel):
    """Single rating response."""
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    design_id: UUID
    user_id: UUID
    rating: int
    review: str | None
    created_at: datetime
    updated_at: datetime

class DesignRatingWithUser(DesignRatingResponse):
    """Rating with author info for display."""
    user_name: str
    user_avatar_url: str | None = None

class DesignRatingSummary(BaseModel):
    """Aggregate rating stats."""
    design_id: UUID
    average_rating: float
    total_ratings: int
    rating_distribution: dict[int, int]  # {1: count, 2: count, ..., 5: count}

class PaginatedRatingsResponse(BaseModel):
    """Paginated list of ratings."""
    items: list[DesignRatingWithUser]
    total: int
    page: int
    page_size: int
```

### 4.2 Comment Endpoints

| Method | Path | Auth | Description | Status Codes |
|--------|------|------|-------------|--------------|
| `POST` | `/comments` | Required | Create top-level or reply | 201, 400, 401, 404 |
| `GET` | `/comments` | Public | List top-level (paginated) | 200, 404 |
| `GET` | `/comments/{comment_id}` | Public | Single comment with replies | 200, 404 |
| `PATCH` | `/comments/{comment_id}` | Required | Edit own comment | 200, 400, 401, 403, 404 |
| `DELETE` | `/comments/{comment_id}` | Required | Delete own (admin: any) | 204, 401, 403, 404 |

#### Request/Response Schemas

```python
# --- Comment Schemas ---

class DesignCommentCreate(BaseModel):
    """Create a comment."""
    content: Annotated[str, Field(min_length=1, max_length=5000)]
    parent_id: UUID | None = None

class DesignCommentUpdate(BaseModel):
    """Edit a comment."""
    content: Annotated[str, Field(min_length=1, max_length=5000)]

class DesignCommentResponse(BaseModel):
    """Single comment."""
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    design_id: UUID
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

class DesignCommentThread(DesignCommentResponse):
    """Comment with nested replies (1 level deep)."""
    replies: list[DesignCommentResponse] = []

class PaginatedCommentsResponse(BaseModel):
    """Paginated list of top-level comments."""
    items: list[DesignCommentResponse]
    total: int
    page: int
    page_size: int

class CommentModerationAction(BaseModel):
    """Admin moderation action."""
    action: Annotated[str, Field(pattern="^(hide|unhide|delete)$")]
    reason: Annotated[str | None, Field(max_length=255, default=None)]
```

### 4.3 Remix Endpoints

| Method | Path | Auth | Description | Status Codes |
|--------|------|------|-------------|--------------|
| `POST` | `/remix` | Required | Clone as new draft design | 201, 401, 404 |
| `GET` | `/remixes` | Public | List public remixes (paginated) | 200, 404 |

Follows existing pattern in [backend/app/api/v2/starters.py](../backend/app/api/v2/starters.py#L291). Key difference: source is any public marketplace design, not just starters.

#### Request/Response Schemas

```python
class MarketplaceRemixRequest(BaseModel):
    """Remix a marketplace design."""
    name: str | None = None  # Default: "{original} (Remix)"

class MarketplaceRemixResponse(BaseModel):
    """Remix result."""
    id: UUID
    name: str
    remixed_from_id: UUID
    remixed_from_name: str
    enclosure_spec: dict[str, Any] | None
    created_at: datetime
```

### 4.4 Report Endpoints

| Method | Path | Auth | Description | Status Codes |
|--------|------|------|-------------|--------------|
| `POST` | `/report` | Required | Report design | 201, 400, 401, 409 |
| `GET` | `/report/status` | Required | Check if already reported | 200, 401 |

Reuses existing `ReportCreate` / `ReportResponse` schemas from `backend/app/schemas/rating.py`. The endpoint automatically sets `target_type="design"` and `target_id=design_id`.

### 4.5 View Tracking Endpoint

| Method | Path | Auth | Description | Status Codes |
|--------|------|------|-------------|--------------|
| `POST` | `/view` | Public (rate-limited) | Increment view count | 204, 404, 429 |

Lightweight — increments `Design.view_count` with a Redis-backed dedup window (1 view per IP per design per hour).

---

## 5. Service Layer Design

### 5.1 `DesignRatingService`

**File:** `backend/app/services/design_rating_service.py`

Mirrors `RatingService` from [backend/app/services/rating_service.py](../backend/app/services/rating_service.py#L39).

```
class DesignRatingService:
    def __init__(self, db: AsyncSession)

    async def rate_design(design_id: UUID, user_id: UUID, data: DesignRatingCreate) -> DesignRating
        # Validates design exists, is public, user ≠ design owner
        # Upsert pattern: create or update
        # Calls _update_design_avg_rating()

    async def get_user_rating(design_id: UUID, user_id: UUID) -> DesignRating | None

    async def get_design_ratings(design_id: UUID, limit: int, offset: int)
        -> tuple[Sequence[DesignRating], int]
        # Pagination with user info eager-loaded

    async def get_rating_summary(design_id: UUID) -> DesignRatingSummary
        # AVG, COUNT, distribution {1..5}

    async def delete_rating(design_id: UUID, user_id: UUID) -> bool

    async def _update_design_avg_rating(design_id: UUID) -> None
        # Updates Design.avg_rating and Design.total_ratings
```

### 5.2 `DesignCommentService`

**File:** `backend/app/services/design_comment_service.py`

Mirrors `CommentService` from [backend/app/services/rating_service.py](../backend/app/services/rating_service.py#L387).

```
class DesignCommentService:
    def __init__(self, db: AsyncSession)

    async def create_comment(design_id: UUID, user_id: UUID, data: DesignCommentCreate) -> DesignComment
        # Validates design exists + is public
        # If parent_id set, validates parent exists and belongs to same design
        # Max nesting depth: 1 (replies to top-level only)

    async def get_design_comments(design_id: UUID, include_hidden: bool, limit: int, offset: int)
        -> tuple[Sequence[DesignComment], int]
        # Top-level only (parent_id IS NULL), paginated

    async def get_comment_with_replies(comment_id: UUID, include_hidden: bool) -> DesignComment | None
        # Eager-loads replies + user info

    async def update_comment(comment_id: UUID, user_id: UUID, data: DesignCommentUpdate)
        -> DesignComment | None
        # Only own comments, sets is_edited=True, edited_at=now()

    async def delete_comment(comment_id: UUID, user_id: UUID, is_admin: bool) -> bool
        # Own comments or admin override

    async def hide_comment(comment_id: UUID, moderator_id: UUID, reason: str | None) -> DesignComment | None
        # Admin/moderator only

    async def unhide_comment(comment_id: UUID) -> DesignComment | None

    async def get_reply_count(comment_id: UUID) -> int
```

### 5.3 Remix — Extend Existing Pattern

**No new service class.** The marketplace remix endpoint follows the inline pattern from [backend/app/api/v2/starters.py](../backend/app/api/v2/starters.py#L291-L395):

1. Validate source design is public + published + not deleted
2. Get or create user's default "My Designs" project
3. Create new `Design` with `remixed_from_id` set, `source_type="remix"`, `status="draft"`
4. Copy `enclosure_spec`, `category`, `tags`
5. Increment source `remix_count`
6. Fire `notify_design_remixed` notification

### 5.4 View Tracking — Lightweight

**Implemented inline in the route handler.** Uses Redis `SETEX` for dedup:

```python
key = f"design_view:{design_id}:{client_ip_hash}"
if not await redis.get(key):
    await redis.setex(key, 3600, "1")  # 1-hour dedup window
    design.view_count += 1
```

---

## 6. Security Architecture

### 6.1 Per-Endpoint Auth & Authorization

| Endpoint | Auth | Authorization Rules |
|----------|------|-------------------|
| `GET /ratings` | Public | Anyone can read |
| `GET /ratings/summary` | Public | Anyone can read |
| `GET /ratings/me` | `get_current_user` | Returns 404 if no rating (not 403) |
| `POST /ratings` | `get_current_user` | **Cannot rate own design** (403). Must not be banned. |
| `DELETE /ratings` | `get_current_user` | Can only delete own rating |
| `GET /comments` | Public | Hidden comments excluded unless admin |
| `GET /comments/{id}` | Public | Hidden comments excluded unless admin |
| `POST /comments` | `get_current_user` | Design must be public. Must not be banned. Max nesting depth = 1. |
| `PATCH /comments/{id}` | `get_current_user` | **Own comments only** (403 otherwise) |
| `DELETE /comments/{id}` | `get_current_user` | Own comments or `is_admin=True` |
| `POST /remix` | `get_current_user` | Design must be public + published |
| `GET /remixes` | Public | Only shows public remixes |
| `POST /report` | `get_current_user` | **Cannot report own design** (403). One report per user per target (409). |
| `GET /report/status` | `get_current_user` | Returns own report status only |
| `POST /view` | Public | Rate-limited by IP (no auth required) |

### 6.2 Rate Limiting

Add entries to `ENDPOINT_RATE_LIMITS` in [backend/app/middleware/abuse_protection.py](../backend/app/middleware/abuse_protection.py#L36):

```python
# Marketplace social — moderate limits
"/api/v2/marketplace/designs/*/ratings": (10, 60),       # 10 per minute
"/api/v2/marketplace/designs/*/comments": (15, 60),      # 15 per minute (allow rapid replies)
"/api/v2/marketplace/designs/*/remix": (5, 60),           # 5 per minute
"/api/v2/marketplace/designs/*/report": (3, 3600),        # 3 per hour
"/api/v2/marketplace/designs/*/view": (60, 60),           # 60 per minute (one per page load)
```

### 6.3 Input Validation & XSS Prevention

| Field | Validation | Sanitization |
|-------|-----------|--------------|
| `rating` | `Field(ge=1, le=5)` — Pydantic enforced | N/A (integer) |
| `review` (rating) | `max_length=2000` | Strip HTML tags server-side via `bleach.clean()` before storage |
| `content` (comment) | `min_length=1, max_length=5000` | Strip HTML tags via `bleach.clean()`. Allow only plain text. |
| `name` (remix) | `max_length=255` | Strip HTML tags |
| `description` (report) | `max_length=1000` | Strip HTML tags |

**Sanitization utility** (new file `backend/app/core/sanitize.py`):

```python
import bleach

def sanitize_text(text: str) -> str:
    """Strip all HTML tags from user-generated content."""
    return bleach.clean(text, tags=[], strip=True).strip()
```

Applied in service methods before database write.

### 6.4 CSRF Considerations

- API uses Bearer token auth (JWT) — CSRF is not applicable for token-based auth
- No cookie-based session auth on these endpoints
- `SameSite=Lax` already set on any auth cookies as defense-in-depth

### 6.5 Additional Security Controls

- **Banned user check:** Services check `UserBan` table before write operations (rate, comment, report)
- **Soft-deleted designs:** All queries filter `WHERE deleted_at IS NULL`
- **Public-only reads:** Social features only available on `is_public=True AND published_at IS NOT NULL` designs
- **SQL injection:** Prevented by SQLAlchemy parameterized queries (existing pattern)
- **Logging:** All write operations log `user_id`, `design_id`, and action to structured logger for audit trail

---

## 7. Frontend Component Architecture

### 7.1 Component Tree

```
MarketplaceDesignDetailPage (NEW — frontend/src/pages/MarketplaceDesignDetailPage.tsx)
├── DesignHeader (NEW)
│   ├── name, author avatar + name, published date
│   ├── category badge, tag chips
│   └── ShareLink button (copy URL)
├── ModelViewer (EXISTING — frontend/src/components/viewer/ModelViewer.tsx)
├── StatsBar (NEW — frontend/src/components/marketplace/StatsBar.tsx)
│   ├── views count
│   ├── saves count
│   ├── remixes count
│   └── avg_rating (star display + number)
├── ActionBar (NEW — frontend/src/components/marketplace/ActionBar.tsx)
│   ├── SaveButton (EXISTING — frontend/src/components/marketplace/SaveButton.tsx)
│   ├── RemixButton (NEW)
│   ├── ReportButton (NEW)
│   └── ShareLink (NEW — copy URL to clipboard)
├── RatingSummary (NEW — frontend/src/components/marketplace/RatingSummary.tsx)
│   ├── Average star display (large)
│   └── Distribution bar chart (5 horizontal bars)
├── WriteReviewForm (NEW — frontend/src/components/marketplace/WriteReviewForm.tsx)
│   ├── StarPicker (interactive 1-5 star selector)
│   └── Textarea (optional review text)
├── ReviewList (NEW — frontend/src/components/marketplace/ReviewList.tsx)
│   ├── ReviewCard[] (star rating + review text + author + date)
│   └── "Load more" pagination
├── CommentSection (NEW — frontend/src/components/marketplace/CommentSection.tsx)
│   ├── CommentForm (NEW — textarea + submit)
│   └── CommentThread[] (NEW — recursive, max depth 1)
│       ├── CommentCard (content, author, date, edit/delete actions)
│       └── CommentThread[] (replies — flat, not further nested)
└── RemixHistory (NEW — frontend/src/components/marketplace/RemixHistory.tsx)
    ├── "Remixed from: [Original Design]" badge (if applicable)
    └── Remix list (paginated, design cards)
```

### 7.2 Component Classification

| Component | Status | Location |
|-----------|--------|----------|
| `MarketplaceDesignDetailPage` | **New** | `frontend/src/pages/MarketplaceDesignDetailPage.tsx` |
| `DesignHeader` | **New** | `frontend/src/components/marketplace/DesignHeader.tsx` |
| `ModelViewer` | **Existing** | `frontend/src/components/viewer/ModelViewer.tsx` |
| `StatsBar` | **New** | `frontend/src/components/marketplace/StatsBar.tsx` |
| `ActionBar` | **New** | `frontend/src/components/marketplace/ActionBar.tsx` |
| `SaveButton` | **Existing** | `frontend/src/components/marketplace/SaveButton.tsx` |
| `RemixButton` | **New** | `frontend/src/components/marketplace/RemixButton.tsx` |
| `ReportButton` | **New** | `frontend/src/components/marketplace/ReportButton.tsx` |
| `ShareLink` | **New** | `frontend/src/components/marketplace/ShareLink.tsx` |
| `RatingSummary` | **New** | `frontend/src/components/marketplace/RatingSummary.tsx` |
| `WriteReviewForm` | **New** | `frontend/src/components/marketplace/WriteReviewForm.tsx` |
| `StarPicker` | **New** | `frontend/src/components/marketplace/StarPicker.tsx` |
| `ReviewList` | **New** | `frontend/src/components/marketplace/ReviewList.tsx` |
| `ReviewCard` | **New** | `frontend/src/components/marketplace/ReviewCard.tsx` |
| `CommentSection` | **New** | `frontend/src/components/marketplace/CommentSection.tsx` |
| `CommentForm` | **New** | `frontend/src/components/marketplace/CommentForm.tsx` |
| `CommentThread` | **New** | `frontend/src/components/marketplace/CommentThread.tsx` |
| `CommentCard` | **New** | `frontend/src/components/marketplace/CommentCard.tsx` |
| `RemixHistory` | **New** | `frontend/src/components/marketplace/RemixHistory.tsx` |

### 7.3 Data Flow & Hooks

**New hooks file:** `frontend/src/hooks/useDesignSocial.ts`

```typescript
// React Query hooks for marketplace social features

// --- Ratings ---
useDesignRatings(designId: string, page: number)
    → GET /api/v2/marketplace/designs/{id}/ratings
    → returns { data: PaginatedRatings, isLoading, error }

useDesignRatingSummary(designId: string)
    → GET /api/v2/marketplace/designs/{id}/ratings/summary
    → returns { data: RatingSummary, isLoading }

useMyDesignRating(designId: string)
    → GET /api/v2/marketplace/designs/{id}/ratings/me
    → returns { data: Rating | null, isLoading }

useRateDesign()
    → POST /api/v2/marketplace/designs/{id}/ratings
    → mutation, invalidates [ratings, summary] queries on success

useDeleteDesignRating()
    → DELETE /api/v2/marketplace/designs/{id}/ratings
    → mutation, invalidates [ratings, summary] queries on success

// --- Comments ---
useDesignComments(designId: string, page: number)
    → GET /api/v2/marketplace/designs/{id}/comments
    → returns { data: PaginatedComments, isLoading }

useCommentThread(commentId: string)
    → GET /api/v2/marketplace/designs/{id}/comments/{commentId}
    → returns { data: CommentThread, isLoading }

useCreateComment()
    → POST /api/v2/marketplace/designs/{id}/comments
    → mutation, invalidates comments query

useUpdateComment()
    → PATCH /api/v2/marketplace/designs/{id}/comments/{commentId}
    → mutation, invalidates comments query

useDeleteComment()
    → DELETE /api/v2/marketplace/designs/{id}/comments/{commentId}
    → mutation, invalidates comments query

// --- Remix ---
useRemixDesign()
    → POST /api/v2/marketplace/designs/{id}/remix
    → mutation, navigates to new design on success

useDesignRemixes(designId: string, page: number)
    → GET /api/v2/marketplace/designs/{id}/remixes

// --- Report ---
useReportDesign()
    → POST /api/v2/marketplace/designs/{id}/report
    → mutation

useReportStatus(designId: string)
    → GET /api/v2/marketplace/designs/{id}/report/status
```

**New API client file:** `frontend/src/lib/marketplace-social.ts`

Follows existing pattern from [frontend/src/lib/marketplace.ts](../frontend/src/lib/marketplace.ts) — plain `fetch` wrappers with token handling.

### 7.4 TypeScript Types

**File:** `frontend/src/types/marketplace-social.ts`

```typescript
// Rating types
interface DesignRating {
  id: string;
  design_id: string;
  user_id: string;
  rating: number;
  review: string | null;
  user_name: string;
  user_avatar_url: string | null;
  created_at: string;
  updated_at: string;
}

interface RatingSummary {
  design_id: string;
  average_rating: number;
  total_ratings: number;
  rating_distribution: Record<number, number>;
}

interface PaginatedRatings {
  items: DesignRating[];
  total: number;
  page: number;
  page_size: number;
}

// Comment types
interface DesignComment {
  id: string;
  design_id: string;
  user_id: string;
  parent_id: string | null;
  content: string;
  is_hidden: boolean;
  is_edited: boolean;
  edited_at: string | null;
  created_at: string;
  updated_at: string;
  user: { id: string; display_name: string } | null;
  reply_count: number;
}

interface CommentThread extends DesignComment {
  replies: DesignComment[];
}

interface PaginatedComments {
  items: DesignComment[];
  total: number;
  page: number;
  page_size: number;
}

// Remix types
interface MarketplaceRemixResponse {
  id: string;
  name: string;
  remixed_from_id: string;
  remixed_from_name: string;
  enclosure_spec: Record<string, unknown> | null;
  created_at: string;
}

// Report types
interface ReportStatus {
  has_reported: boolean;
  report_id: string | null;
  created_at: string | null;
}
```

### 7.5 Routing

Add to existing React Router configuration:

```typescript
// Route: /marketplace/:designId
<Route path="/marketplace/:designId" element={<MarketplaceDesignDetailPage />} />
```

This extends the existing navigation from `MarketplacePage` which already navigates to `/marketplace/${design.id}` (see [frontend/src/pages/MarketplacePage.tsx](../frontend/src/pages/MarketplacePage.tsx#L63)).

---

## 8. Database Indexes

### 8.1 `design_ratings` Table

| Index Name | Columns | Type | Purpose |
|-----------|---------|------|---------|
| `uq_design_rating_user` | `(design_id, user_id)` | UNIQUE | One rating per user per design |
| `idx_design_ratings_design` | `(design_id)` | B-tree | List ratings for a design |
| `idx_design_ratings_user` | `(user_id)` | B-tree | User's rating history |

### 8.2 `design_comments` Table

| Index Name | Columns | Type | Purpose |
|-----------|---------|------|---------|
| `idx_design_comments_design` | `(design_id)` | B-tree | List comments for a design |
| `idx_design_comments_user` | `(user_id)` | B-tree | User's comment history |
| `idx_design_comments_parent` | `(parent_id)` | B-tree | Load replies for a comment |
| `idx_design_comments_design_created` | `(design_id, created_at)` | B-tree | Paginated chronological listing |

### 8.3 `designs` Table (New Indexes)

| Index Name | Columns | Type | Purpose |
|-----------|---------|------|---------|
| `idx_designs_avg_rating_marketplace` | `(avg_rating DESC NULLS LAST)` | Partial B-tree (`WHERE is_public = TRUE AND published_at IS NOT NULL AND deleted_at IS NULL`) | Marketplace sort by rating |

```sql
CREATE INDEX idx_designs_avg_rating_marketplace
    ON designs(avg_rating DESC NULLS LAST)
    WHERE is_public = TRUE
      AND published_at IS NOT NULL
      AND deleted_at IS NULL;
```

---

## 9. File Inventory

### Backend — New Files

| File | Track | Purpose |
|------|-------|---------|
| `backend/app/models/design_rating.py` | A | `DesignRating` model |
| `backend/app/models/design_comment.py` | B | `DesignComment` model |
| `backend/app/schemas/design_social.py` | A+B | All request/response schemas for ratings, comments, remix, report |
| `backend/app/services/design_rating_service.py` | A | Rating business logic |
| `backend/app/services/design_comment_service.py` | B | Comment business logic |
| `backend/app/api/v2/marketplace_design_social.py` | A+B+C | All social endpoint route handlers |
| `backend/app/core/sanitize.py` | A+B | HTML sanitization utility |
| `backend/alembic/versions/018_design_ratings.py` | A | Rating table + Design columns migration |
| `backend/alembic/versions/019_design_comments.py` | B | Comment table migration |

### Backend — Modified Files

| File | Change |
|------|--------|
| `backend/app/models/design.py` | Add `avg_rating`, `total_ratings` columns + `ratings`, `comments` relationships |
| `backend/app/models/user.py` | Add `design_ratings`, `design_comments` back-populates |
| `backend/app/models/__init__.py` | Import new models |
| `backend/app/api/v2/__init__.py` | Register `marketplace_design_social` router |
| `backend/app/middleware/abuse_protection.py` | Add rate limit entries for social endpoints |

### Backend — Test Files

| File | Track |
|------|-------|
| `backend/tests/models/test_design_rating.py` | A |
| `backend/tests/models/test_design_comment.py` | B |
| `backend/tests/services/test_design_rating_service.py` | A |
| `backend/tests/services/test_design_comment_service.py` | B |
| `backend/tests/api/test_marketplace_design_social.py` | A+B+C |

### Frontend — New Files

| File | Track |
|------|-------|
| `frontend/src/pages/MarketplaceDesignDetailPage.tsx` | A+B+C |
| `frontend/src/components/marketplace/DesignHeader.tsx` | C |
| `frontend/src/components/marketplace/StatsBar.tsx` | C |
| `frontend/src/components/marketplace/ActionBar.tsx` | C |
| `frontend/src/components/marketplace/RemixButton.tsx` | C |
| `frontend/src/components/marketplace/ReportButton.tsx` | C |
| `frontend/src/components/marketplace/ShareLink.tsx` | C |
| `frontend/src/components/marketplace/RatingSummary.tsx` | A |
| `frontend/src/components/marketplace/WriteReviewForm.tsx` | A |
| `frontend/src/components/marketplace/StarPicker.tsx` | A |
| `frontend/src/components/marketplace/ReviewList.tsx` | A |
| `frontend/src/components/marketplace/ReviewCard.tsx` | A |
| `frontend/src/components/marketplace/CommentSection.tsx` | B |
| `frontend/src/components/marketplace/CommentForm.tsx` | B |
| `frontend/src/components/marketplace/CommentThread.tsx` | B |
| `frontend/src/components/marketplace/CommentCard.tsx` | B |
| `frontend/src/components/marketplace/RemixHistory.tsx` | C |
| `frontend/src/hooks/useDesignSocial.ts` | A+B+C |
| `frontend/src/lib/marketplace-social.ts` | A+B+C |
| `frontend/src/types/marketplace-social.ts` | A+B+C |

### Frontend — Test Files

| File | Track |
|------|-------|
| `frontend/src/pages/MarketplaceDesignDetailPage.test.tsx` | A+B+C |
| `frontend/src/components/marketplace/RatingSummary.test.tsx` | A |
| `frontend/src/components/marketplace/WriteReviewForm.test.tsx` | A |
| `frontend/src/components/marketplace/CommentSection.test.tsx` | B |
| `frontend/src/components/marketplace/CommentThread.test.tsx` | B |
| `frontend/src/hooks/useDesignSocial.test.ts` | A+B+C |
| `frontend/e2e/marketplace-social.spec.ts` | A+B+C |

---

## Design Decisions & Rationale

1. **Denormalized `avg_rating`/`total_ratings` on `Design`** — Avoids an `AVG()` aggregate on every marketplace browse query. Updated via service method on each rating write. Acceptable staleness for marketplace listing.

2. **Max comment nesting depth = 1** — Keeps threading simple (top-level + replies). No recursive CTE needed. Parent must have `parent_id IS NULL` (enforced in service, not DB constraint for flexibility).

3. **Separate models vs. generic polymorphic** — `DesignRating` and `DesignComment` are separate from `TemplateRating`/`TemplateComment` rather than using a polymorphic `target_type` column. This keeps queries simple, indexes optimal, and allows independent schema evolution.

4. **Reports reuse existing `ContentReport`** — Already supports `target_type="design"`. No new model needed.

5. **View dedup via Redis, not DB** — Avoids a `design_views` table and N+1 write amplification. Redis TTL key provides cheap per-IP dedup. Counter on `Design.view_count` is approximate — acceptable for analytics.

6. **`bleach.clean()` for UGC sanitization** — Industry-standard library for HTML stripping. Applied at the service layer before DB write, not at the schema layer, to keep Pydantic schemas clean.

7. **One router file for all social endpoints** — Keeps related functionality together. The router is mounted under `/api/v2/marketplace/designs/{design_id}` with sub-routers for `/ratings`, `/comments`, etc.
