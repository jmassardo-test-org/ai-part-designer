# US-5.7: Complete Org Feature Permission Enforcement — Design Specification

**Issue:** [#307](https://github.com/jmassardo/ai-part-designer/issues/307)
**Epic:** [#23 — Organization Admin & RBAC](https://github.com/jmassardo/ai-part-designer/issues/23)
**Status:** In Progress — 4/7 features done, 3 remaining
**Priority:** P1 (Security)

---

## 1. Problem Statement

Organization admins can toggle features on/off via `PUT /organizations/{org_id}/features` and the frontend `OrganizationSettingsPage.tsx`. However, three gatable features — `ai_chat`, `ai_generation`, and `file_uploads` — only have **tier-level** enforcement (`require_feature`), not **org-level** enforcement (`require_org_feature`). This means:

- Toggling `ai_chat` off for an org has **zero effect** on conversation endpoints
- Toggling `ai_generation` off has **zero effect** on generation endpoints
- Toggling `file_uploads` off has **zero effect** on file upload endpoints

### What's Already Done (4/7 Features)

| Feature | Resolver Used | Endpoint File | Status |
|---------|---------------|---------------|--------|
| `teams` | `require_org_feature("teams")` | `teams.py` | ✅ Done |
| `design_sharing` | `require_org_feature_for_design("design_sharing")` | `shares.py` | ✅ Done |
| `assemblies` | `require_org_feature_for_project("assemblies")` | `assemblies.py` | ✅ Done |
| `bom` | `require_org_feature_for_assembly("bom")` | `bom.py` | ✅ Done |

### What's Missing (3/7 Features)

| Feature | Current State | Endpoint File | Endpoints Affected |
|---------|---------------|---------------|--------------------|
| `ai_chat` | `require_feature("ai_chat")` only (tier) | `conversations.py` | `create_conversation`, `send_message` |
| `ai_generation` | `require_feature("ai_generation")` only (tier) | `conversations.py` | `direct_generate`, `trigger_generation` |
| `file_uploads` | `require_feature("file_uploads")` only (tier) | `files.py` | `upload_file` |

---

## 2. Architecture Constraint: User-Scoped Endpoints

The core architectural challenge is that **conversations and files are user-scoped, not org-scoped**:

- `Conversation` model has `user_id` + optional `design_id` — **NO** `organization_id` or `project_id`
- `File` model has only `user_id` — **NO** `organization_id` or `project_id`
- No `X-Organization` header convention exists in the application
- No `organization_id` path parameter exists on these routes

### Existing Resolver Patterns

All existing `require_org_feature*` resolvers use a resource → project → org traversal chain:

| Resolver | Chain | Defined In |
|----------|-------|------------|
| `require_org_feature(name)` | `org_id` from path param | `deps.py:198` |
| `require_org_feature_for_project(name)` | `project_id` → `project.organization_id` | `deps.py:271` |
| `require_org_feature_for_design(name)` | `design_id` → `design.project_id` → `project.organization_id` | `deps.py:345` |
| `require_org_feature_for_assembly(name)` | `assembly_id` → `assembly.project_id` → `project.organization_id` | `deps.py:432` |

All resolvers have the **same fallback behavior**: if the resource is personal (no org in the chain), the check is **skipped**. This is the correct pattern — personal resources are not governed by org policies.

---

## 3. Design Decision: Resolution Strategy

### 3.1 Conversations with `design_id` → Design Chain Resolution

When a conversation has a `design_id`, the org can be resolved through:
**`conversation.design_id` → `design.project_id` → `project.organization_id`**

This applies to:
- `send_message` (has `conversation_id` path param → can look up conversation → get `design_id`)
- `trigger_generation` (has `conversation_id` path param → same chain)
- `create_conversation` (has `design_id` in request body)

### 3.2 Conversations without `design_id` → Personal Resource, Skip Check

When a conversation has **no** `design_id`:
- It's a standalone chat (not attached to any org resource)
- Following the existing "personal resources skip the check" pattern, the org feature check is skipped
- **Tier-level** enforcement (`require_feature`) still applies

This is correct behavior: if a user starts a personal conversation not tied to any org's design, the org shouldn't have control over that.

### 3.3 File Uploads → Optional `organization_id` Query Parameter

File uploads have **no** resource chain to traverse. The solution:
- Accept an **optional** `organization_id: UUID | None` query parameter on the upload endpoint
- If provided, check org features
- If not provided, it's a personal upload — skip (tier-level still applies)
- The frontend passes this param when the user is uploading within an org context

### 3.4 New Resolver: `require_org_feature_for_conversation`

Create a **new dependency factory** in `deps.py` that:
1. Takes `conversation_id` from path params
2. Queries the conversation to get `design_id`
3. If `design_id` exists, follows the design → project → org chain (reuses `require_org_feature_for_design` logic)
4. If no `design_id`, skips the org check (personal conversation)

---

## 4. User Stories

### US-5.7a: Org Feature Enforcement on Conversation Endpoints

> **As** an organization admin who has disabled the `ai_chat` feature,
> **I want** conversation creation and messaging to be blocked for users operating within my org's context,
> **So that** feature toggles have real enforcement, not just UI decoration.

**Acceptance Criteria:**

```gherkin
Scenario: Create conversation with design in org that disables ai_chat
  Given I am a member of an organization
  And the organization has "ai_chat" disabled
  And I have a design in a project belonging to that organization
  When I POST /api/v1/conversations with design_id pointing to that design
  Then I receive 403 with detail.error = "feature_disabled"
  And detail.feature = "ai_chat"

Scenario: Create conversation without design_id (personal) when org disables ai_chat
  Given I am a member of an organization
  And the organization has "ai_chat" disabled
  When I POST /api/v1/conversations with no design_id
  Then the request succeeds (200/201) if my subscription tier allows it
  Because personal conversations are not governed by org policies

Scenario: Send message in conversation linked to org design with ai_chat disabled
  Given I have an existing conversation linked to a design in an org
  And the organization has "ai_chat" disabled
  When I POST /api/v1/conversations/{id}/messages
  Then I receive 403 with detail.error = "feature_disabled"

Scenario: Trigger generation in conversation linked to org design with ai_generation disabled
  Given I have an existing conversation linked to a design in an org
  And the organization has "ai_generation" disabled
  When I POST /api/v1/conversations/{id}/generate
  Then I receive 403 with detail.error = "feature_disabled"

Scenario: Direct generate (personal) when org disables ai_generation
  Given I am a member of an organization
  And the organization has "ai_generation" disabled
  When I POST /api/v1/conversations/direct-generate
  Then the request succeeds if my subscription tier allows it
  Because direct-generate has no org context (personal one-off generation)

Scenario: Re-enable ai_chat unblocks immediately
  Given I am in an org where "ai_chat" was disabled
  When the admin re-enables "ai_chat"
  And I immediately retry creating a conversation with a design in that org
  Then the request succeeds
```

**Edge Cases:**
- Conversation has a `design_id` pointing to a design whose project has no org → skip org check (personal project)
- Conversation has a `design_id` pointing to a design whose project's org was deleted → return 404 "Organization not found"
- User is not a member of the org but has access to the design via sharing → org feature still applies (the feature gate is on the org, not the user's membership)

### US-5.7b: Org Feature Enforcement on File Upload Endpoint

> **As** an organization admin who has disabled the `file_uploads` feature,
> **I want** file uploads made within my org's context to be blocked,
> **So that** I can control storage usage and feature access for my organization.

**Acceptance Criteria:**

```gherkin
Scenario: Upload file with organization_id where file_uploads is disabled
  Given I am a member of an organization
  And the organization has "file_uploads" disabled
  When I POST /api/v1/files/upload?organization_id={org_id}
  Then I receive 403 with detail.error = "feature_disabled"
  And detail.feature = "file_uploads"

Scenario: Upload file without organization_id (personal) when org disables file_uploads
  Given I am a member of an organization
  And the organization has "file_uploads" disabled
  When I POST /api/v1/files/upload (no organization_id param)
  Then the request succeeds if my subscription tier allows it
  Because personal uploads are not governed by org policies

Scenario: Upload file with organization_id where file_uploads is enabled
  Given I am a member of an organization
  And the organization has "file_uploads" enabled
  When I POST /api/v1/files/upload?organization_id={org_id}
  Then the request proceeds normally

Scenario: Re-enable file_uploads unblocks immediately
  Given file_uploads was disabled for my org
  When the admin re-enables "file_uploads"
  And I immediately retry uploading with organization_id
  Then the upload succeeds
```

**Edge Cases:**
- `organization_id` provided but user is not a member → should still enforce (feature gate is on the org resource, not membership; membership check is separate if needed)
- `organization_id` provided but org does not exist → 404 "Organization not found"
- `organization_id` provided with invalid UUID → 422 validation error (FastAPI handles automatically)

---

## 5. Technical Design

### 5.1 New Resolver: `require_org_feature_for_conversation`

**Location:** `backend/app/api/deps.py`

```python
def require_org_feature_for_conversation(feature_name: str) -> Callable[..., None]:
    """
    Dependency to require an organization feature for conversation-scoped operations.

    Resolution chain: conversation_id → conversation.design_id → design.project_id
    → project.organization_id → org.has_feature()

    If the conversation has no design_id, or the design's project has no org,
    this is a personal resource — the check is skipped.
    """
    async def dependency(
        conversation_id: UUID,
        db: AsyncSession = Depends(get_db),
        _user: User = Depends(get_current_user),
    ) -> None:
        # 1. Get conversation
        conversation = (await db.execute(
            select(Conversation).where(Conversation.id == conversation_id)
        )).scalar_one_or_none()

        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")

        # 2. If no design linked, this is personal — skip
        if not conversation.design_id:
            return

        # 3. Get design → project → org (same chain as require_org_feature_for_design)
        design = (await db.execute(
            select(Design).where(Design.id == conversation.design_id)
        )).scalar_one_or_none()

        if not design:
            return  # Design was deleted, treat as personal

        project = (await db.execute(
            select(Project).where(Project.id == design.project_id)
        )).scalar_one_or_none()

        if not project or not project.organization_id:
            return  # Personal project

        org = (await db.execute(
            select(Organization).where(Organization.id == project.organization_id)
        )).scalar_one_or_none()

        if not org:
            raise HTTPException(status_code=404, detail="Organization not found")

        if not org.has_feature(feature_name):
            raise HTTPException(
                status_code=403,
                detail={
                    "error": "feature_disabled",
                    "message": f"Feature '{feature_name}' is not enabled for this organization",
                    "feature": feature_name,
                },
            )

    return dependency
```

### 5.2 Inline Check for `create_conversation`

The `create_conversation` endpoint takes `design_id` from the **request body**, not a path param. Dependency injection can't access body params. Two options:

**Option A (Recommended): Inline check after body parsing**
Add the org feature check inline inside the endpoint function, after parsing the request body and resolving the design. This is pragmatic and follows the principle of least surprise — the dependency injection layer handles what it can, and the endpoint handles what requires body data.

```python
@router.post("/", ...)
async def create_conversation(
    request: CreateConversationRequest,
    db: ...,
    current_user: ...,
    _feature: None = Depends(require_feature("ai_chat")),  # tier check (keep)
) -> ConversationResponse:
    if request.design_id:
        # Resolve org through design → project → org
        await _check_org_feature_for_design(db, request.design_id, "ai_chat")
    ...
```

**Option B: Add `design_id` as optional query param too**
Not recommended — duplicates the body param, confusing API contract.

### 5.3 Changes to `conversations.py`

| Endpoint | Line | Current | Change |
|----------|------|---------|--------|
| `create_conversation` | 328 | `require_feature("ai_chat")` | Keep + add inline org check for `design_id` |
| `send_message` | 558 | `require_feature("ai_chat")` | Keep + add `Depends(require_org_feature_for_conversation("ai_chat"))` |
| `direct_generate` | 453 | `require_feature("ai_generation")` | Keep (no org context — personal) |
| `trigger_generation` | 910 | `require_feature("ai_generation")` | Keep + add `Depends(require_org_feature_for_conversation("ai_generation"))` |

### 5.4 Changes to `files.py`

| Endpoint | Line | Current | Change |
|----------|------|---------|--------|
| `upload_file` | 189 | `require_feature("file_uploads")` | Keep + add `Depends(require_org_feature("file_uploads"))` with optional `organization_id` query param |

Since `require_org_feature` already handles optional `organization_id` (returns early if None), this is a drop-in addition. The frontend passes `organization_id` as a query param when uploading within an org context.

### 5.5 Helper Function: `_check_org_feature_for_design`

For the inline check in `create_conversation`, add a reusable async helper in `conversations.py` (or in `deps.py` as a non-dependency utility):

```python
async def _check_org_feature_for_design(
    db: AsyncSession, design_id: UUID, feature_name: str
) -> None:
    """Check org feature enforcement through design → project → org chain."""
    design = (await db.execute(
        select(Design).where(Design.id == design_id)
    )).scalar_one_or_none()
    if not design:
        return

    project = (await db.execute(
        select(Project).where(Project.id == design.project_id)
    )).scalar_one_or_none()
    if not project or not project.organization_id:
        return

    org = (await db.execute(
        select(Organization).where(Organization.id == project.organization_id)
    )).scalar_one_or_none()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    if not org.has_feature(feature_name):
        raise HTTPException(
            status_code=403,
            detail={
                "error": "feature_disabled",
                "message": f"Feature '{feature_name}' is not enabled for this organization",
                "feature": feature_name,
            },
        )
```

---

## 6. Files to Modify

| File | Changes |
|------|---------|
| `backend/app/api/deps.py` | Add `require_org_feature_for_conversation` resolver; add `check_org_feature_for_design` utility; update `__all__` |
| `backend/app/api/v1/conversations.py` | Import new deps; add `require_org_feature_for_conversation` to `send_message` and `trigger_generation`; add inline check in `create_conversation` |
| `backend/app/api/v1/files.py` | Import `require_org_feature`; add `Depends(require_org_feature("file_uploads"))` to `upload_file` |
| `backend/tests/api/test_org_feature_enforcement.py` | Replace loose assertions with proper org-level tests for `ai_chat`, `ai_generation`, `file_uploads` |

---

## 7. Work Breakdown

### Task 1: Add `require_org_feature_for_conversation` resolver (≤1 day)
- Add new resolver in `deps.py` following existing pattern
- Add `check_org_feature_for_design` utility function
- Export both in `__all__`
- Unit test the resolver with mocked DB

### Task 2: Wire up `conversations.py` endpoints (≤1 day)
- Import new resolver and utility
- Add `Depends(require_org_feature_for_conversation("ai_chat"))` to `send_message`
- Add `Depends(require_org_feature_for_conversation("ai_generation"))` to `trigger_generation`
- Add inline `check_org_feature_for_design` call in `create_conversation` after `design_id` validation
- `direct_generate` stays unchanged (personal, no org context)

### Task 3: Wire up `files.py` upload endpoint (≤0.5 day)
- Import `require_org_feature` from deps
- Add `Depends(require_org_feature("file_uploads"))` to `upload_file`
- Add optional `organization_id: UUID | None = Query(None)` parameter

### Task 4: Update tests (≤1.5 days)
- Replace `TestConversationFeatureEnforcement` tests with proper org-level assertions
- Replace `TestFileUploadFeatureEnforcement` tests with proper org-level assertions
- Add new test fixtures: conversation linked to design in org, conversation without design
- Test cases:
  - `test_create_conversation_with_org_design_feature_disabled_returns_403`
  - `test_create_conversation_without_design_skips_org_check`
  - `test_send_message_org_feature_disabled_returns_403`
  - `test_trigger_generation_org_feature_disabled_returns_403`
  - `test_direct_generate_no_org_check_personal`
  - `test_upload_file_with_org_id_feature_disabled_returns_403`
  - `test_upload_file_without_org_id_skips_org_check`
  - `test_re_enable_ai_chat_unblocks_immediately`
  - `test_re_enable_file_uploads_unblocks_immediately`

### Task 5: Verify and close (≤0.5 day)
- Run `ruff check .` and `mypy .` for lint/type safety
- Run `pytest --cov=app` to verify all tests pass
- Update issue #307 with completion status
- Close issue #307

**Total estimate:** 4.5 days (~5 story points, consistent with original estimate)

---

## 8. Non-Functional Requirements

| Requirement | Target |
|-------------|--------|
| **Response time** | Org feature check adds ≤3 additional DB queries (conversation → design → project → org); p95 < 50ms overhead |
| **Security** | 403 response must not leak org internal details; error payload follows existing `{"error": "feature_disabled", "message": "...", "feature": "..."}` format |
| **Backward compatibility** | All changes are additive — existing tier-level enforcement (`require_feature`) remains; no API contract changes for existing callers |
| **Idempotency** | Feature checks are read-only; no side effects on retry |
| **Observability** | 403 responses logged at WARN level with org_id, feature_name, user_id for audit trail (aligns with #308 403-tracking work) |

---

## 9. Dependencies & Constraints

- **No schema migration required** — no new columns, no model changes
- **Frontend change optional** — `file_uploads` org enforcement via query param requires the frontend to pass `organization_id` when uploading in an org context. If not passed, the upload proceeds as personal (existing behavior, non-breaking).
- **Blocked by nothing** — `deps.py` already has all the resolver infrastructure; this is purely wiring
- **Related to #308** — 403-tracking (`_track_failed_authorization`) is a separate concern. This PR does not add tracking; #308 will add it after these enforcement checks are in place.

---

## 10. Test Strategy

### Unit Tests (New/Updated in `test_org_feature_enforcement.py`)

| Test | Validates |
|------|-----------|
| `test_create_conversation_with_org_design_ai_chat_disabled` | 403 when org disables `ai_chat` and `design_id` points to org design |
| `test_create_conversation_personal_skips_org_check` | 200/201 when no `design_id`, even if user's org disables `ai_chat` |
| `test_create_conversation_personal_project_design_skips_org_check` | 200/201 when `design_id` points to personal project design |
| `test_send_message_org_ai_chat_disabled` | 403 when conversation linked to org design, `ai_chat` disabled |
| `test_send_message_personal_conversation` | 200 when conversation has no `design_id` |
| `test_trigger_generation_org_ai_generation_disabled` | 403 when conversation linked to org design, `ai_generation` disabled |
| `test_direct_generate_no_org_enforcement` | Confirm tier-only check; no org feature gate |
| `test_upload_file_org_feature_disabled` | 403 when `organization_id` query param passed and `file_uploads` disabled |
| `test_upload_file_personal_no_org_param` | 200/201 when no `organization_id` param |
| `test_re_enable_ai_chat_unblocks` | After re-enabling, org-scoped conversation creation succeeds |
| `test_re_enable_file_uploads_unblocks` | After re-enabling, org-scoped file upload succeeds |

### Integration Tests

Existing E2E Playwright tests should not be affected (all changes are additive with backward-compatible defaults).

---

## 11. Rollback Plan

If issues arise:
1. Remove `Depends(require_org_feature_for_conversation(...))` from endpoint signatures — single-line revert per endpoint
2. Remove inline `check_org_feature_for_design` call from `create_conversation`
3. Remove `Depends(require_org_feature("file_uploads"))` from `upload_file`
4. Tier-level enforcement remains intact as fallback

---

## 12. Success Metrics

| Metric | Target |
|--------|--------|
| All 7 gatable features have org-level enforcement | 7/7 (currently 4/7) |
| Org admin toggles `ai_chat` off → users get 403 on org-scoped conversations | Verified in tests |
| Personal resource operations unaffected by org toggles | Verified in tests |
| No regression in existing tier-level enforcement | All existing tests pass |
| Test coverage for org feature enforcement | ≥90% of enforcement paths |
