# Epic 20 — Marketplace & Sharing: Refined User Stories

> **Date:** 2025-02-25
> **Status:** Ready for implementation
> **Epic:** #20 — Marketplace & Sharing
> **Related issues:** #96 (Ratings & Reviews), #97 (Design Remix/Fork)

---

## Summary Table

| ID | Story Title | SP | Track | Depends On |
|----|-------------|---:|-------|------------|
| E20-S1 | Fix marketplace API client base URL | 1 | A (Foundation) | — |
| E20-S2 | Design rating models & migration | 3 | A (Foundation) | — |
| E20-S3 | Design comment models & migration | 3 | A (Foundation) | — |
| E20-S4 | Design rating API endpoints | 5 | B (Backend APIs) | E20-S2 |
| E20-S5 | Design comment API endpoints | 5 | B (Backend APIs) | E20-S3 |
| E20-S6 | Design remix API endpoint | 3 | B (Backend APIs) | — |
| E20-S7 | Content report API for designs | 2 | B (Backend APIs) | — |
| E20-S8 | Marketplace design detail page | 8 | C (Frontend) | E20-S1, E20-S4, E20-S5 |
| E20-S9 | Rating & review UI components | 5 | C (Frontend) | E20-S4 |
| E20-S10 | Report button UI component | 2 | C (Frontend) | E20-S7 |
| E20-S11 | Remix button & flow UI | 3 | C (Frontend) | E20-S6 |
| **Total** | | **40** | | |

---

## Execution Order & Dependency Graph

```
                    ┌──────────┐
          ┌────────▶│ E20-S1   │ (Fix API URL)
          │         └────┬─────┘
          │              │
          │         ┌────▼──────────────────────────────────┐
Track A   │    ┌────┤ E20-S2 (Rating Models)                │
(Foundation)   │    │    │                                   │
          │    │    │    │  E20-S3 (Comment Models)          │
          │    │    └────┼───────────────────────────────────┘
          │    │         │                │
          │    │    ┌────▼─────┐    ┌─────▼─────┐
Track B   │    │    │ E20-S4   │    │ E20-S5    │   E20-S6   E20-S7
(APIs)    │    │    │(Rating   │    │(Comment   │  (Remix)  (Report)
          │    │    │ API)     │    │ API)      │    │         │
          │    │    └────┬─────┘    └─────┬─────┘    │         │
          │    │         │                │          │         │
          │    │    ┌────▼────────────────▼──────────▼─────────▼──┐
Track C   │    │    │ E20-S8 (Detail Page)                        │
(Frontend)│    │    │ E20-S9 (Rating UI)                          │
          │    │    │ E20-S10 (Report Button)                     │
          │    │    │ E20-S11 (Remix Flow)                        │
          │    │    └─────────────────────────────────────────────┘
```

### Parallel Execution Plan

| Sprint Phase | Track A (Foundation) | Track B (Backend) | Track C (Frontend) |
|-------------|---------------------|-------------------|-------------------|
| Phase 1 (Days 1–2) | E20-S1, E20-S2, E20-S3 | — | — |
| Phase 2 (Days 3–5) | — | E20-S4, E20-S5, E20-S6, E20-S7 (all parallel) | — |
| Phase 3 (Days 6–10) | — | — | E20-S8, E20-S9, E20-S10, E20-S11 (S9/S10/S11 parallel, S8 integrates) |

*Tracks B items are independent once their Track A dependency is met.*
*Track C items S9, S10, S11 are independent components; S8 integrates them into the detail page.*

---

## Story Details

---

### E20-S1 — Fix Marketplace API Client Base URL

**User Story:**
As a frontend developer, I want the marketplace API client to point to the correct v2 endpoint, so that marketplace features work against the actual backend routes.

**What already exists:**
- [frontend/src/lib/marketplace.ts](../frontend/src/lib/marketplace.ts) — API client with `API_BASE = '/api/v1/marketplace'`
- Backend routes registered at `/api/v2/marketplace` in [backend/app/api/v2/marketplace.py](../backend/app/api/v2/marketplace.py)

**Remaining work:**
1. Change `API_BASE` from `'/api/v1/marketplace'` to `'/api/v2/marketplace'` in `frontend/src/lib/marketplace.ts`
2. Verify all 13 functions in the file still work with the v2 routes
3. Audit `browseDesigns()` — it uses `POST /browse` but v2 uses `GET /designs` with query params; fix the method signature

**Acceptance Criteria:**
```gherkin
Feature: Marketplace API client uses correct base URL

  Scenario: API calls reach v2 endpoints
    Given the marketplace API client is imported
    When any marketplace function is called
    Then the request URL begins with "/api/v2/marketplace"

  Scenario: Browse designs calls correct v2 endpoint
    Given the user opens the marketplace page
    When designs are fetched
    Then a GET request is made to "/api/v2/marketplace/designs" with query parameters
    And the response renders the design grid correctly
```

**Story Points:** 1
**Rationale:** Straightforward find-and-replace plus one method signature fix. Low risk.

**Testing Requirements:**
- File: `frontend/src/lib/marketplace.test.ts` (create)
- Tests: `test_api_base_url_points_to_v2`, `test_browse_designs_uses_get_with_params`
- Mock `fetch` to validate URLs

**Dependencies:** None

**Security Considerations:**
- Ensure no auth tokens are leaked when switching endpoint versions
- Validate CORS is configured for v2 routes

---

### E20-S2 — Design Rating Model & Database Migration

**User Story:**
As a platform developer, I want a `DesignRating` model that stores 1–5 star ratings with optional review text (one per user per design), so that the rating system has persistent storage.

**What already exists:**
- `TemplateRating` model in [backend/app/models/rating.py](../backend/app/models/rating.py#L42) — exact pattern to replicate
- `Template.avg_rating` field in [backend/app/models/template.py](../backend/app/models/template.py#L169)
- Design model in [backend/app/models/design.py](../backend/app/models/design.py#L34) — missing `avg_rating` / `total_ratings`

**Remaining work:**
1. Add `DesignRating` class to `backend/app/models/rating.py`:
   - Fields: `id`, `design_id` (FK → designs.id), `user_id` (FK → users.id), `rating` (1–5), `review` (Text, nullable)
   - Unique constraint: `(design_id, user_id)`
   - Check constraint: `rating >= 1 AND rating <= 5`
   - Indexes: `design_id`, `user_id`
2. Add `avg_rating: Mapped[float | None]` and `total_ratings: Mapped[int]` columns to `Design` model
3. Add `ratings` relationship on `Design` model → `DesignRating`
4. Add `design_ratings` relationship on `User` model
5. Create Alembic migration
6. Register model in `__init__.py` exports
7. Add Pydantic schemas: `DesignRatingCreate`, `DesignRatingResponse`, `DesignRatingWithUser`, `DesignRatingSummary`

**Acceptance Criteria:**
```gherkin
Feature: Design rating model

  Scenario: Create a design rating
    Given a DesignRating instance with design_id, user_id, rating=4, review="Great"
    When the instance is persisted to the database
    Then a row exists in design_ratings with the correct values

  Scenario: Unique constraint prevents duplicate ratings
    Given user A has already rated design X
    When user A attempts to insert another rating for design X
    Then an IntegrityError is raised

  Scenario: Rating range is enforced
    Given a DesignRating with rating=0
    When the instance is persisted
    Then a CheckConstraint violation is raised

  Scenario: Design model has avg_rating field
    Given a Design row in the database
    When avg_rating is set to 4.5 and total_ratings to 10
    Then the values persist and are queryable
```

**Story Points:** 3
**Rationale:** Model creation follows the existing `TemplateRating` pattern exactly. One migration, two model changes (Design + User), plus schemas.

**Testing Requirements:**
- File: `backend/tests/models/test_design_rating.py` (create)
- Tests:
  - `test_design_rating_creation_with_valid_data`
  - `test_design_rating_unique_constraint_per_user_per_design`
  - `test_design_rating_check_constraint_range_1_to_5`
  - `test_design_rating_allows_null_review`
  - `test_design_rating_cascade_deletes_on_design_delete`
  - `test_design_avg_rating_field_on_design_model`
  - `test_design_total_ratings_defaults_to_zero`
  - `test_design_rating_repr`
- File: `backend/tests/schemas/test_design_rating_schemas.py` (create)
- Tests:
  - `test_design_rating_create_validation`
  - `test_design_rating_create_rejects_rating_out_of_range`
  - `test_design_rating_response_from_attributes`

**Dependencies:** None (can start immediately)

**Security Considerations:**
- Enforce that only authenticated users can create ratings (checked at API layer, E20-S4)
- `user_id` must come from the auth token, never from request body

---

### E20-S3 — Design Comment Model & Database Migration

**User Story:**
As a platform developer, I want a `DesignComment` model with threading and moderation support, so that users can have conversations on marketplace designs persisted in the database (replacing the current in-memory implementation).

**What already exists:**
- `TemplateComment` model in [backend/app/models/rating.py](../backend/app/models/rating.py#L170) — pattern to replicate
- In-memory `_comments` dict in [backend/app/api/v1/comments.py](../backend/app/api/v1/comments.py) — the current design comment implementation stores data in a Python dict, not the database

**Remaining work:**
1. Add `DesignComment` class to `backend/app/models/rating.py`:
   - Fields: `id`, `design_id` (FK → designs.id), `user_id` (FK → users.id), `parent_id` (FK → self, nullable), `content` (Text), `is_hidden`, `hidden_by_id`, `hidden_at`, `hidden_reason`, `is_edited`, `edited_at`
   - Self-referential relationship for threading: `parent` ↔ `replies`
   - Indexes: `design_id`, `user_id`, `parent_id`
2. Add `comments` relationship on `Design` model → `DesignComment`
3. Add `design_comments` relationship on `User` model
4. Create Alembic migration
5. Register model in `__init__.py` exports
6. Add Pydantic schemas: `DesignCommentCreate`, `DesignCommentResponse`, `DesignCommentThread`

**Acceptance Criteria:**
```gherkin
Feature: Design comment model

  Scenario: Create a top-level comment
    Given a DesignComment with design_id, user_id, content="Nice design"
    When persisted to the database
    Then a row exists in design_comments with parent_id = NULL

  Scenario: Create a threaded reply
    Given an existing comment C1 on design X
    When a new DesignComment is created with parent_id = C1.id
    Then the reply is associated with C1 via the parent relationship
    And C1.replies includes the new comment

  Scenario: Moderate a comment (hide)
    Given an existing DesignComment
    When is_hidden is set to True with hidden_by_id and hidden_reason
    Then the comment's hidden fields are populated
    And the comment content is still stored (soft-hide, not deleted)

  Scenario: Cascade delete on design deletion
    Given design X with 5 comments
    When design X is hard-deleted
    Then all 5 DesignComment rows are cascade-deleted
```

**Story Points:** 3
**Rationale:** Mirror of `TemplateComment`, same complexity as E20-S2. Slightly more fields (moderation) but the pattern is established.

**Testing Requirements:**
- File: `backend/tests/models/test_design_comment.py` (create)
- Tests:
  - `test_design_comment_creation`
  - `test_design_comment_threading_parent_child`
  - `test_design_comment_cascade_delete_replies`
  - `test_design_comment_moderation_fields`
  - `test_design_comment_edit_tracking`
  - `test_design_comment_repr`

**Dependencies:** None (can start immediately, parallel to E20-S2)

**Security Considerations:**
- Content must be sanitized (strip HTML/scripts) before storage
- Comment length limit (max 5000 chars) enforced at schema level
- Hidden comments should still be queryable by moderators

---

### E20-S4 — Design Rating API Endpoints

**User Story:**
As a marketplace user, I want to rate designs with 1–5 stars and an optional written review, so that I can share my opinion and help others find quality designs.

**What already exists:**
- Template rating endpoints in [backend/app/api/v1/ratings.py](../backend/app/api/v1/ratings.py) — pattern to replicate
- `RatingService` in [backend/app/services/rating_service.py](../backend/app/services/rating_service.py) — can extend with `DesignRatingService`
- Marketplace v2 router at [backend/app/api/v2/marketplace.py](../backend/app/api/v2/marketplace.py)

**Remaining work:**
1. Create `DesignRatingService` in `backend/app/services/rating_service.py` (or a new `design_rating_service.py`):
   - `rate_design(design_id, user_id, data)` — create or update rating
   - `get_user_rating(design_id, user_id)` — get current user's rating
   - `get_design_ratings(design_id, limit, offset)` — paginated ratings list
   - `get_rating_summary(design_id)` — avg, total, distribution
   - `delete_rating(design_id, user_id)` — remove rating
   - `_update_design_avg_rating(design_id)` — update denormalized avg_rating on Design
2. Create API endpoints at `/api/v2/marketplace/designs/{design_id}/ratings`:
   - `POST /ratings` → create/update rating (auth required)
   - `GET /ratings` → list ratings with pagination
   - `GET /ratings/summary` → rating summary
   - `GET /ratings/me` → current user's rating (auth required)
   - `DELETE /ratings` → delete own rating (auth required)
3. Wire into v2 marketplace router
4. Update `MarketplaceDesignResponse` schema to include `avg_rating` and `total_ratings`

**Acceptance Criteria:**
```gherkin
Feature: Design rating API

  Scenario: Rate a public design
    Given I am authenticated
    And design "Widget A" is published on the marketplace
    When I POST to /api/v2/marketplace/designs/{id}/ratings with {"rating": 5, "review": "Excellent"}
    Then I receive 201 Created
    And the response contains my rating

  Scenario: Update my existing rating
    Given I previously rated design "Widget A" with 3 stars
    When I POST to /api/v2/marketplace/designs/{id}/ratings with {"rating": 5}
    Then my rating is updated to 5 stars (not duplicated)

  Scenario: Cannot rate own design
    Given I am the owner of design "My Widget"
    When I POST a rating for "My Widget"
    Then I receive 403 Forbidden

  Scenario: Rating summary calculation
    Given design "Widget A" has ratings [5, 4, 4, 3, 5]
    When I GET /api/v2/marketplace/designs/{id}/ratings/summary
    Then average_rating is 4.2
    And total_ratings is 5
    And rating_distribution shows {5: 2, 4: 2, 3: 1, 2: 0, 1: 0}

  Scenario: Cannot rate private design
    Given design "Secret Widget" is private
    When I POST a rating for it
    Then I receive 404 Not Found

  Scenario: Unauthenticated user cannot rate
    Given I am not authenticated
    When I POST a rating
    Then I receive 401 Unauthorized

  Scenario: Delete my rating
    Given I have rated design "Widget A"
    When I DELETE /api/v2/marketplace/designs/{id}/ratings
    Then I receive 204 No Content
    And the design's avg_rating is recalculated
```

**Story Points:** 5
**Rationale:** 6 service methods + 5 API endpoints + schema updates + integration with existing marketplace router. Moderate complexity due to avg_rating denormalization.

**Testing Requirements:**
- File: `backend/tests/services/test_design_rating_service.py` (create)
- Tests:
  - `test_rate_design_creates_new_rating`
  - `test_rate_design_updates_existing_rating`
  - `test_rate_design_updates_avg_rating_on_design`
  - `test_get_user_rating_returns_none_when_not_rated`
  - `test_get_design_ratings_pagination`
  - `test_get_rating_summary_empty_design`
  - `test_get_rating_summary_with_ratings`
  - `test_delete_rating_recalculates_avg`
  - `test_delete_rating_nonexistent_returns_false`
- File: `backend/tests/api/test_design_ratings_api.py` (create)
- Tests:
  - `test_rate_design_success`
  - `test_rate_design_unauthenticated_returns_401`
  - `test_rate_own_design_returns_403`
  - `test_rate_private_design_returns_404`
  - `test_rate_design_invalid_rating_returns_422`
  - `test_get_rating_summary`
  - `test_get_my_rating`
  - `test_delete_rating`
  - `test_update_existing_rating`

**Dependencies:** E20-S2 (model must exist before service/API)

**Security Considerations:**
- All write endpoints require authentication (`Depends(get_current_user)`)
- Users cannot rate their own designs (ownership check)
- Rate limiting: max 60 rating operations per user per hour to prevent abuse
- `user_id` extracted from JWT token, never from request body
- Input validation: review text max 2000 chars, rating 1–5 (Pydantic enforced)
- Audit log rating operations for moderation traceability

---

### E20-S5 — Design Comment API Endpoints

**User Story:**
As a marketplace user, I want to leave comments and replies on published designs, so that I can ask questions and discuss designs with the community.

**What already exists:**
- In-memory comments in [backend/app/api/v1/comments.py](../backend/app/api/v1/comments.py) — uses dict storage, has notification wiring
- `CommentService` in [backend/app/services/rating_service.py](../backend/app/services/rating_service.py) — handles template comments
- Comment schemas in [backend/app/schemas/rating.py](../backend/app/schemas/rating.py#L91)

**Remaining work:**
1. Create `DesignCommentService` (new file `backend/app/services/design_comment_service.py` or extend rating_service.py):
   - `create_comment(design_id, user_id, data)` — create comment or reply
   - `get_comments(design_id, parent_id, limit, offset)` — paginated, threaded
   - `get_comment(comment_id)` — single comment
   - `update_comment(comment_id, user_id, data)` — edit own comment
   - `delete_comment(comment_id, user_id)` — soft-delete own comment
   - `hide_comment(comment_id, moderator_id, reason)` — moderation action
2. Create API endpoints at `/api/v2/marketplace/designs/{design_id}/comments`:
   - `POST /comments` → create comment (auth required)
   - `GET /comments` → list top-level comments (public, paginated)
   - `GET /comments/{comment_id}` → single comment with replies
   - `PATCH /comments/{comment_id}` → edit own comment (auth required)
   - `DELETE /comments/{comment_id}` → delete own comment (auth required)
3. Integrate with existing notification service (comment added, reply, @mention)
4. Wire into v2 marketplace router

**Acceptance Criteria:**
```gherkin
Feature: Design comment API

  Scenario: Add a comment to a published design
    Given I am authenticated
    And design "Widget A" is published
    When I POST to /api/v2/marketplace/designs/{id}/comments with {"content": "How did you do the rounded edges?"}
    Then I receive 201 Created
    And the response contains my comment with author info

  Scenario: Reply to a comment
    Given comment C1 exists on design "Widget A"
    When I POST with {"content": "Good question!", "parent_id": C1.id}
    Then the reply is associated with C1
    And the design owner is notified

  Scenario: Edit my comment
    Given I posted comment C2
    When I PATCH /api/v2/marketplace/designs/{did}/comments/{C2.id} with {"content": "Updated text"}
    Then the comment content is updated
    And is_edited is true

  Scenario: Cannot edit someone else's comment
    Given user B posted comment C3
    When I (user A) attempt to PATCH C3
    Then I receive 403 Forbidden

  Scenario: List comments with pagination
    Given design "Widget A" has 25 top-level comments
    When I GET /comments?page=1&page_size=10
    Then I receive 10 comments and total=25

  Scenario: Hidden comments are excluded for non-moderators
    Given comment C4 is hidden by a moderator
    When a regular user lists comments
    Then C4 is not included in the response

  Scenario: Unauthenticated users can read but not write comments
    Given I am not authenticated
    When I GET /comments
    Then I receive 200 OK with comments
    When I POST a new comment
    Then I receive 401 Unauthorized
```

**Story Points:** 5
**Rationale:** 6 service methods + 5 API endpoints + notification integration + moderation support. Similar scope to E20-S4 but with threading complexity.

**Testing Requirements:**
- File: `backend/tests/services/test_design_comment_service.py` (create)
- Tests:
  - `test_create_comment_success`
  - `test_create_reply_sets_parent_id`
  - `test_create_reply_invalid_parent_returns_error`
  - `test_get_comments_pagination`
  - `test_get_comments_excludes_hidden`
  - `test_update_comment_sets_edited_flag`
  - `test_update_comment_wrong_user_raises`
  - `test_delete_comment_soft_deletes`
  - `test_hide_comment_moderation`
- File: `backend/tests/api/test_design_comments_api.py` (create)
- Tests:
  - `test_create_comment_success`
  - `test_create_comment_unauthenticated_returns_401`
  - `test_create_comment_on_private_design_returns_404`
  - `test_reply_to_comment`
  - `test_edit_own_comment`
  - `test_edit_others_comment_returns_403`
  - `test_delete_own_comment`
  - `test_list_comments_unauthenticated_allowed`
  - `test_comment_content_sanitized`

**Dependencies:** E20-S3 (model must exist)

**Security Considerations:**
- Write operations require authentication
- Read operations are public for published designs
- Content sanitization: strip HTML tags, prevent XSS
- Rate limiting: max 30 comments per user per hour
- @mention resolution must not leak email addresses of users
- Content length validated at schema level (1–5000 chars)

---

### E20-S6 — Design Remix API Endpoint

**User Story:**
As a marketplace user, I want to remix (fork) any public design into my own workspace, so that I can build upon community designs.

**What already exists:**
- Starter remix endpoint in [backend/app/api/v2/starters.py](../backend/app/api/v2/starters.py#L300) — only for `is_starter=True` designs
- Design model fields: `remixed_from_id`, `remix_count` in [backend/app/models/design.py](../backend/app/models/design.py#L89)
- `RemixRequest`/`RemixResponse` schemas in [backend/app/schemas/marketplace.py](../backend/app/schemas/marketplace.py)
- Notification: `notify_design_remixed` already exists

**Remaining work:**
1. Add `POST /api/v2/marketplace/designs/{design_id}/remix` endpoint in marketplace router:
   - Validate design is public and not deleted
   - Prevent remixing own design (debatable — allow but track)
   - Clone design: copy name (+ " (Remix)"), description, tags, category, `enclosure_spec`, `extra_data.parameters`
   - Set `remixed_from_id` on new design
   - Increment `remix_count` on original
   - Get-or-create user's default project
   - Send `notify_design_remixed` notification
2. Reuse existing `RemixRequest`/`RemixResponse` schemas (they're general enough)
3. Add `GET /api/v2/marketplace/designs/{design_id}/remixes` — list public remixes

**Acceptance Criteria:**
```gherkin
Feature: Design remix/fork API

  Scenario: Remix a public design
    Given I am authenticated
    And design "Widget A" is public with enclosure_spec
    When I POST to /api/v2/marketplace/designs/{id}/remix
    Then I receive 201 Created
    And a new design is created in my default project
    And the new design has remixed_from_id = Widget A's id
    And Widget A's remix_count is incremented by 1

  Scenario: Remix with custom name
    When I POST with {"name": "My Custom Widget"}
    Then the new design is named "My Custom Widget"

  Scenario: Cannot remix private design
    Given design "Secret Widget" is private
    When I POST remix
    Then I receive 404 Not Found

  Scenario: Cannot remix without authentication
    Given I am not authenticated
    When I POST remix
    Then I receive 401 Unauthorized

  Scenario: List remixes of a design
    Given design "Widget A" has 3 public remixes
    When I GET /api/v2/marketplace/designs/{id}/remixes
    Then I receive a paginated list of 3 designs

  Scenario: Original design owner receives notification
    Given user B's design "Widget A" is public
    When user A remixes it
    Then user B receives a "design remixed" notification
```

**Story Points:** 3
**Rationale:** The starter remix logic already exists and can be generalized. Main work is removing the `is_starter` constraint and adding to marketplace router.

**Testing Requirements:**
- File: `backend/tests/api/test_design_remix_api.py` (create)
- Tests:
  - `test_remix_public_design_success`
  - `test_remix_creates_design_in_default_project`
  - `test_remix_sets_remixed_from_id`
  - `test_remix_increments_remix_count`
  - `test_remix_private_design_returns_404`
  - `test_remix_unauthenticated_returns_401`
  - `test_remix_with_custom_name`
  - `test_remix_copies_enclosure_spec`
  - `test_remix_notification_sent`
  - `test_list_remixes_pagination`
  - `test_list_remixes_excludes_private`

**Dependencies:** None (uses existing model fields)

**Security Considerations:**
- Authentication required for remix creation
- Rate limiting: max 10 remixes per user per hour to prevent abuse/resource exhaustion
- Validate original design exists and is public before cloning
- Do not copy sensitive `extra_data` fields (API keys, etc.) — only `parameters` and `enclosure_spec`
- Log remix operations for analytics and abuse detection

---

### E20-S7 — Content Report API for Designs (Frontend-Facing)

**User Story:**
As a marketplace user, I want to report a design that violates community guidelines, so that moderators can review and take action.

**What already exists:**
- `ContentReport` model supports `target_type="design"` in [backend/app/models/rating.py](../backend/app/models/rating.py#L310)
- `ReportService` in [backend/app/services/rating_service.py](../backend/app/services/rating_service.py) — `create_report()` method exists
- `ReportCreate` schema in [backend/app/schemas/rating.py](../backend/app/schemas/rating.py) — supports `design` target type
- Admin moderation endpoints in [backend/app/api/v1/moderation.py](../backend/app/api/v1/moderation.py)
- User's own reports endpoint exists in moderation.py

**Remaining work:**
1. Add a user-facing report endpoint at `/api/v2/marketplace/designs/{design_id}/report`:
   - `POST /report` → create a ContentReport with `target_type="design"`, `target_id=design_id`
   - Validate design exists and is public
   - Prevent duplicate reports from same user for same design
   - Return 201 with report confirmation
2. Add `GET /api/v2/marketplace/designs/{design_id}/report/status` — check if user already reported
3. Simplified schema: `DesignReportCreate` with just `reason` and optional `description` (target_type/id auto-filled from path)

**Acceptance Criteria:**
```gherkin
Feature: Report a marketplace design

  Scenario: Report a design for inappropriate content
    Given I am authenticated
    And design "Bad Widget" is published
    When I POST to /api/v2/marketplace/designs/{id}/report with {"reason": "inappropriate", "description": "Contains offensive imagery"}
    Then I receive 201 Created
    And a ContentReport row is created with target_type="design"

  Scenario: Cannot report same design twice
    Given I already reported design "Bad Widget"
    When I POST another report
    Then I receive 409 Conflict

  Scenario: Check report status
    Given I have reported design "Bad Widget"
    When I GET /api/v2/marketplace/designs/{id}/report/status
    Then I receive {"already_reported": true}

  Scenario: Cannot report without authentication
    Given I am not authenticated
    When I POST a report
    Then I receive 401 Unauthorized
```

**Story Points:** 2
**Rationale:** Most of the work (model, service, admin endpoints) already exists. This is a thin wrapper that auto-fills `target_type` and `target_id` from the URL path.

**Testing Requirements:**
- File: `backend/tests/api/test_design_report_api.py` (create)
- Tests:
  - `test_report_design_success`
  - `test_report_design_duplicate_returns_409`
  - `test_report_design_unauthenticated_returns_401`
  - `test_report_private_design_returns_404`
  - `test_report_status_check`
  - `test_report_invalid_reason_returns_422`

**Dependencies:** None (uses existing model)

**Security Considerations:**
- Authentication required
- Rate limiting: max 10 reports per user per hour
- Validate reason is from the allowed enum (`spam`, `inappropriate`, `copyright`, `misleading`, `offensive`, `other`)
- Do not reveal report count to design owner (anti-retaliation)
- Sanitize description text input

---

### E20-S8 — Marketplace Design Detail Page

**User Story:**
As a marketplace visitor, I want to view a detailed page for a published design showing its 3D preview, description, ratings, comments, remix history, and action buttons, so that I can evaluate and interact with community designs.

**What already exists:**
- `DesignDetailPage` at [frontend/src/pages/DesignDetailPage.tsx](../frontend/src/pages/DesignDetailPage.tsx) — for the user's own designs (route: `/designs/:designId`), has 3D viewer integration
- `MarketplacePage` at [frontend/src/pages/MarketplacePage.tsx](../frontend/src/pages/MarketplacePage.tsx) — cards navigate to `/marketplace/${design.id}` but **no route exists** for `/marketplace/:id`
- Marketplace detail API: `GET /api/v2/marketplace/designs/{id}` returns `MarketplaceDesignResponse` with save status, remix info, file availability
- `ModelViewer` component in `frontend/src/components/viewer/ModelViewer.tsx`
- `SaveButton` component in `frontend/src/components/marketplace/SaveButton.tsx`

**Remaining work:**
1. Create `frontend/src/pages/MarketplaceDesignDetailPage.tsx`:
   - Fetch design detail from `GET /api/v2/marketplace/designs/{id}`
   - Sections:
     - **Header**: Design name, author, published date, category badge, tags
     - **3D Preview**: ModelViewer component (use STL preview data)
     - **Description**: Full description text
     - **Stats bar**: Views, saves, remixes, avg rating
     - **Actions**: Save/unsave button, Remix button, Report button, Share link
     - **Ratings section**: Rating summary (stars distribution) + review list (uses E20-S9 component)
     - **Comments section**: Threaded comments (uses E20-S9 via separate component)
     - **Remix history**: "Remixed from" link + list of public remixes
   - Responsive layout: single column on mobile, two-column (preview + details) on desktop
2. Add route to `frontend/src/App.tsx`: `<Route path="/marketplace/:designId" element={<MarketplaceDesignDetailPage />} />`
3. Add API functions to `frontend/src/lib/marketplace.ts`:
   - `getDesignDetail(designId)` — calls `GET /api/v2/marketplace/designs/{id}`
   - `getDesignRatings(designId, page)` — calls ratings API
   - `getDesignRatingSummary(designId)` — calls ratings summary API
   - `getDesignComments(designId, page)` — calls comments API
   - `getDesignRemixes(designId, page)` — calls remixes API
4. Add TypeScript types to `frontend/src/types/marketplace.ts`:
   - `DesignRating`, `RatingSummary`, `DesignComment`, `CommentThread`
5. Increment view count on page load (backend already has `view_count` field; add `POST /api/v2/marketplace/designs/{id}/view` endpoint)

**Acceptance Criteria:**
```gherkin
Feature: Marketplace design detail page

  Scenario: View a published design
    Given design "Widget A" is published
    When I navigate to /marketplace/{Widget A's id}
    Then I see the design name, author, and description
    And I see a 3D preview of the design
    And I see the save count, remix count, and average rating

  Scenario: Rating summary is displayed
    Given "Widget A" has 10 ratings averaging 4.2 stars
    When I view the detail page
    Then I see "4.2" average with a star visualization
    And I see a distribution bar chart (5-star: X, 4-star: Y, etc.)

  Scenario: Comments are paginated
    Given "Widget A" has 30 comments
    When I view the detail page
    Then I see the first 10 comments
    And a "Load more" button is visible

  Scenario: Remix history shows lineage
    Given "Widget A" was remixed from "Original Widget"
    When I view the detail page
    Then I see "Remixed from: Original Widget" with a link

  Scenario: Private design shows 404
    Given design "Secret Widget" is private
    When I navigate to /marketplace/{Secret Widget's id}
    Then I see a "Design not found" message

  Scenario: Unauthenticated user can view but not interact
    Given I am not logged in
    When I view the detail page
    Then I see the design details and ratings
    But the "Write a review", "Remix", and "Report" buttons prompt login
```

**Story Points:** 8
**Rationale:** Largest frontend story — full page with multiple sections, 5+ API integrations, responsive design, and integration with 3 other component stories. The 3D viewer integration adds complexity.

**Testing Requirements:**
- File: `frontend/src/pages/MarketplaceDesignDetailPage.test.tsx` (create)
- Tests:
  - `test_renders_design_name_and_author`
  - `test_renders_3d_preview_when_stl_available`
  - `test_renders_placeholder_when_no_stl`
  - `test_displays_rating_summary`
  - `test_displays_comments_with_pagination`
  - `test_displays_remix_lineage`
  - `test_shows_404_for_nonexistent_design`
  - `test_shows_save_button_for_authenticated_user`
  - `test_prompts_login_for_unauthenticated_interactions`
  - `test_view_count_incremented_on_load`
  - `test_responsive_layout_mobile`
- File: `frontend/src/lib/marketplace.test.ts` (extend)
- Tests:
  - `test_get_design_detail_calls_correct_url`
  - `test_get_design_ratings_calls_correct_url`
  - `test_get_design_comments_calls_correct_url`

**Dependencies:** E20-S1, E20-S4, E20-S5 (API endpoints must exist for full integration; can scaffold UI with mocks first)

**Security Considerations:**
- Sanitize all rendered content (design descriptions, comments, reviews) to prevent XSS
- View count increment should be debounced/rate-limited to prevent inflation
- Do not expose design `extra_data` internals to the frontend beyond what `MarketplaceDesignResponse` provides

---

### E20-S9 — Rating & Review UI Components

**User Story:**
As a marketplace user, I want to see star ratings, write reviews, and browse other users' reviews on a design, so that I can make informed decisions about which designs to use.

**What already exists:**
- No rating UI components for designs currently exist
- Template rating schemas provide the data contract

**Remaining work:**
1. Create `frontend/src/components/marketplace/StarRating.tsx`:
   - Interactive star picker (1–5) for writing reviews
   - Read-only star display for showing ratings
   - Half-star support for averages
2. Create `frontend/src/components/marketplace/RatingSummary.tsx`:
   - Average rating (large number + stars)
   - Distribution bar chart (5 bars showing count per star level)
   - Total ratings count
3. Create `frontend/src/components/marketplace/ReviewCard.tsx`:
   - Author name + avatar
   - Star rating + review text
   - Timestamp
4. Create `frontend/src/components/marketplace/WriteReviewForm.tsx`:
   - Star picker + textarea
   - Submit/cancel buttons
   - Edit mode (pre-fill for existing review)
   - Loading/error states
5. Create `frontend/src/components/marketplace/ReviewList.tsx`:
   - Paginated list of `ReviewCard` components
   - Sort by: most recent, highest rated, lowest rated
6. Wire API calls: `rateDesign()`, `getMyRating()`, `deleteRating()` in marketplace.ts

**Acceptance Criteria:**
```gherkin
Feature: Rating and review UI

  Scenario: Display star rating average
    Given a design with avg_rating 4.2 and total_ratings 15
    When the RatingSummary component renders
    Then I see "4.2" with 4 full stars and 1 partial star
    And "15 ratings" text

  Scenario: Submit a new review
    Given I am authenticated and haven't rated this design
    When I click "Write a review"
    And I select 4 stars and type "Great design for my project"
    And I click "Submit"
    Then my review appears in the list
    And the average rating updates

  Scenario: Edit my existing review
    Given I previously rated this design 3 stars
    When I click "Edit my review"
    Then the form pre-fills with 3 stars and my previous text
    When I change to 5 stars and submit
    Then my review is updated

  Scenario: Delete my review
    Given I have a review on this design
    When I click "Delete review" and confirm
    Then my review is removed
    And the average rating recalculates

  Scenario: Review list pagination
    Given 25 reviews exist
    When the ReviewList renders
    Then I see 10 reviews initially
    And a "Show more" button loads the next page
```

**Story Points:** 5
**Rationale:** 5 new components with interactive state management, API integration, and form handling. Star rendering with half-star support adds visual complexity.

**Testing Requirements:**
- File: `frontend/src/components/marketplace/StarRating.test.tsx` (create)
- Tests:
  - `test_renders_correct_number_of_filled_stars`
  - `test_renders_half_star_for_fractional_rating`
  - `test_interactive_mode_fires_on_change`
  - `test_readonly_mode_prevents_interaction`
- File: `frontend/src/components/marketplace/RatingSummary.test.tsx` (create)
- Tests:
  - `test_renders_average_and_total`
  - `test_renders_distribution_bars`
- File: `frontend/src/components/marketplace/WriteReviewForm.test.tsx` (create)
- Tests:
  - `test_submit_new_review`
  - `test_edit_mode_prefills`
  - `test_validation_requires_star_selection`
  - `test_submit_shows_loading_state`
- File: `frontend/src/components/marketplace/ReviewList.test.tsx` (create)
- Tests:
  - `test_renders_reviews`
  - `test_pagination_loads_more`
  - `test_sort_options`

**Dependencies:** E20-S4 (rating API must serve data)

**Security Considerations:**
- Sanitize review text before rendering (prevent XSS)
- Disable submit button during pending request to prevent double-submission
- Client-side validation matches server-side (1–5 stars, max 2000 char review)

---

### E20-S10 — Report Button UI Component

**User Story:**
As a marketplace user, I want a "Report" button on marketplace design cards and the detail page, so that I can flag inappropriate content for moderator review.

**What already exists:**
- `ContentReport` backend supports `design` target type
- No frontend report button exists for marketplace designs
- Report API (E20-S7) will provide the endpoint

**Remaining work:**
1. Create `frontend/src/components/marketplace/ReportDesignButton.tsx`:
   - Flag icon button (low prominence — in card menu or detail page toolbar)
   - Click opens a modal/dialog
2. Create `frontend/src/components/marketplace/ReportDesignDialog.tsx`:
   - Reason selector (radio buttons): Spam, Inappropriate, Copyright, Misleading, Offensive, Other
   - Optional description textarea (max 1000 chars)
   - Submit/cancel buttons
   - Success confirmation toast
   - Duplicate report handling (show "Already reported" state)
3. Add `reportDesign()` and `checkReportStatus()` to `frontend/src/lib/marketplace.ts`
4. Integrate into marketplace DesignCard component (overflow menu) and detail page

**Acceptance Criteria:**
```gherkin
Feature: Report button UI

  Scenario: Report a design from the detail page
    Given I am viewing design "Spam Widget" on the detail page
    When I click the "Report" button
    Then a dialog appears with reason options
    When I select "Spam" and click "Submit"
    Then I see a "Report submitted" confirmation
    And the button changes to "Reported" (disabled)

  Scenario: Report from marketplace card
    Given I see "Spam Widget" in the marketplace grid
    When I click the overflow menu (⋮) on the card
    Then I see a "Report" option
    When I click it
    Then the report dialog opens

  Scenario: Already reported design
    Given I previously reported design "Spam Widget"
    When I view it again
    Then the report button shows "Reported" state
    And clicking it shows "You've already reported this design"

  Scenario: Unauthenticated user
    Given I am not logged in
    When I click the Report button
    Then I am prompted to log in
```

**Story Points:** 2
**Rationale:** Two components (button + dialog), straightforward form, and integration into existing card/page components.

**Testing Requirements:**
- File: `frontend/src/components/marketplace/ReportDesignDialog.test.tsx` (create)
- Tests:
  - `test_renders_reason_options`
  - `test_submit_report_success`
  - `test_submit_report_duplicate_shows_already_reported`
  - `test_requires_reason_selection`
  - `test_description_optional`
  - `test_close_dialog_cancels`

**Dependencies:** E20-S7 (backend endpoint must exist)

**Security Considerations:**
- Require authentication before showing report form
- Description field: sanitize input, limit to 1000 chars
- Disable submit button during request to prevent duplicate submissions
- Do not expose report count or other reports to the reporter

---

### E20-S11 — Remix Button & Flow UI

**User Story:**
As a marketplace user, I want a "Remix" button on design detail pages that creates a copy of the design in my workspace, so that I can customize community designs.

**What already exists:**
- Starter remix flow in `frontend/src/pages/StarterDetailPage.tsx` — has remix button UI pattern
- `remixStarter()` in `frontend/src/lib/marketplace.ts` — calls `POST /starters/{id}/remix`
- No general design remix function or UI exists

**Remaining work:**
1. Add `remixDesign(designId, name?)` function to `frontend/src/lib/marketplace.ts`
2. Create `frontend/src/components/marketplace/RemixButton.tsx`:
   - "Remix this design" button with fork icon
   - Click triggers confirmation dialog: "This will create a copy in your workspace"
   - Optional: text input for custom name
   - On success: navigate to the new design's editor page
   - Loading state during remix API call
3. Create `frontend/src/components/marketplace/RemixBadge.tsx`:
   - Small badge showing "Remixed from: {name}" with link to original
   - Used on detail page and optionally on design cards
4. Integrate into `MarketplaceDesignDetailPage` (E20-S8)

**Acceptance Criteria:**
```gherkin
Feature: Remix button and flow

  Scenario: Remix a design
    Given I am authenticated and viewing design "Widget A"
    When I click "Remix this design"
    Then a confirmation dialog appears
    When I click "Create Remix"
    Then I see a loading spinner
    And I am navigated to the new design's editor page
    And the new design is named "Widget A (Remix)"

  Scenario: Remix with custom name
    Given the remix confirmation dialog is open
    When I type "My Custom Widget" in the name field
    And click "Create Remix"
    Then the new design is named "My Custom Widget"

  Scenario: Remix badge on remixed design
    Given my design "Widget A (Remix)" was remixed from "Widget A"
    When I view my design in the detail page
    Then I see "Remixed from: Widget A" badge with a link

  Scenario: Unauthenticated user
    Given I am not logged in
    When I click "Remix"
    Then I am prompted to log in

  Scenario: Remix count updates
    Given "Widget A" has remix_count = 5
    When I remix it
    Then the displayed remix count becomes 6
```

**Story Points:** 3
**Rationale:** Two components + one API function. The confirmation dialog pattern exists in other parts of the app. Navigation after remix adds a small integration step.

**Testing Requirements:**
- File: `frontend/src/components/marketplace/RemixButton.test.tsx` (create)
- Tests:
  - `test_renders_remix_button`
  - `test_shows_confirmation_dialog_on_click`
  - `test_remix_api_called_on_confirm`
  - `test_navigates_to_new_design_on_success`
  - `test_shows_loading_state_during_remix`
  - `test_custom_name_supported`
  - `test_prompts_login_when_unauthenticated`
- File: `frontend/src/components/marketplace/RemixBadge.test.tsx` (create)
- Tests:
  - `test_renders_remix_lineage_link`
  - `test_hidden_when_no_remix_source`

**Dependencies:** E20-S6 (backend remix API must exist)

**Security Considerations:**
- Require authentication before initiating remix
- Client-side loading state prevents accidental double-remix
- Validate the response design ID before navigating

---

## Cross-Cutting Concerns

### Rate Limiting Summary

| Endpoint Category | Limit | Window |
|---|---|---|
| Rating write operations | 60/user | per hour |
| Comment write operations | 30/user | per hour |
| Report submissions | 10/user | per hour |
| Remix operations | 10/user | per hour |
| View count increments | 1/user/design | per session |

### Monitoring & Logging

All new endpoints should:
- Log operations at INFO level with user_id and design_id
- Emit Prometheus metrics for rating/comment/remix/report counts
- Include OpenTelemetry trace spans for service method calls

### Database Migration Strategy

- E20-S2 and E20-S3 migrations should be in **separate migration files** to enable independent rollback
- Add migration for `avg_rating`/`total_ratings` on `designs` table in E20-S2's migration
- Use `server_default` for `total_ratings = 0` and `avg_rating = NULL`

### API Versioning

All new endpoints go under `/api/v2/marketplace/` to maintain consistency with the existing v2 marketplace routes.
