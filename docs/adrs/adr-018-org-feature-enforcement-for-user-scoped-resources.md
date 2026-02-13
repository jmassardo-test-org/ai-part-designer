# ADR-018: Organization Feature Enforcement for User-Scoped Resources

## Status
Proposed

## Date
2026-02-11

## Context

Organization admins can toggle features (e.g., `ai_chat`, `ai_generation`, `file_uploads`) on/off via `PUT /organizations/{org_id}/features`. The `require_org_feature(name)` dependency factory in `deps.py` checks `org.has_feature()` and raises 403 if disabled.

**Problem:** Several endpoints that should enforce org feature flags operate on **user-scoped** resources — resources whose data models have no `organization_id` column and whose URL paths have no `org_id` parameter:

| Resource | Model FK Chain | Org Resolvable? |
|----------|---------------|-----------------|
| Conversation | `user_id`, optional `design_id` | Only if `design_id` links to an org-scoped design |
| File | `user_id` only | No inherent org relationship |
| Direct Generation | Request body only (`description`) | No org context at all |

All existing resolvers (`require_org_feature`, `require_org_feature_for_project`, `require_org_feature_for_design`, `require_org_feature_for_assembly`) depend on path parameters that resolve through a resource → project → organization chain. This chain does not exist for conversations and files.

### Constraints

1. **No schema migration** — Adding `organization_id` to `conversations` and `files` tables is a significant change requiring migration, data backfill, and would change the lifecycle semantics of these resources. Not appropriate for a security wiring task.
2. **Backward compatibility** — Existing API contracts must not break. No required fields can be added to request schemas.
3. **Personal resource semantics** — The existing architecture deliberately treats some resources as personal (not org-owned). This pattern must be preserved — personal resources are not governed by org policies.
4. **Dual enforcement model** — Tier-level (`require_feature`) and org-level (`require_org_feature`) enforcement are complementary. Tier gates capability; org gates policy. Both should apply where applicable.

## Decision

We will implement three resolution strategies, selected based on the data model characteristics of each endpoint:

### Strategy 1: Conversation Chain Resolution (for `send_message`, `trigger_generation`)

Create a new resolver `require_org_feature_for_conversation` that traverses:

```
conversation_id (path param)
    → conversation.design_id
        → design.project_id
            → project.organization_id
                → org.has_feature(name)
```

Fallback behavior (consistent with all existing resolvers):
- `conversation.design_id` is NULL → personal conversation → **skip check**
- `design.project_id` → `project.organization_id` is NULL → personal project → **skip check**
- Organization not found → **404** (data integrity issue)
- Feature disabled → **403** with `feature_disabled` error

This follows the exact same pattern as `require_org_feature_for_design` and `require_org_feature_for_assembly`.

### Strategy 2: Inline Body-Derived Resolution (for `create_conversation`)

The `create_conversation` endpoint receives `design_id` in the **request body**, not as a path parameter. FastAPI dependency injection cannot access request body fields. Therefore:

- Extract a reusable utility function `check_org_feature_for_design(db, design_id, feature_name)` that performs the same design → project → org chain check
- Call it inline within the endpoint after parsing the request body
- Only invoked when `request.design_id` is provided

### Strategy 3: Optional Query Parameter (for `upload_file`)

Files have **no** resource chain to traverse. The solution:

- Add an **optional** `organization_id: UUID | None = Query(None)` parameter to the upload endpoint
- Reuse the existing `require_org_feature("file_uploads")` resolver — it already handles optional `organization_id` (returns early if None)
- The frontend passes this parameter when uploading within an org context
- Personal uploads (no `organization_id`) skip the org check

### Strategy 4: No Change (for `direct_generate`)

`direct_generate` is a stateless, one-off generation endpoint. The request body contains only a text description. There is no org context — it is purely personal. Only tier-level enforcement applies. No org-level enforcement is added.

### Resolution Decision Matrix

| Endpoint | Strategy | Org Resolved From | Personal Fallback |
|----------|----------|-------------------|-------------------|
| `send_message` | Chain resolution | `conversation_id` → design → project → org | Skip if no design or personal project |
| `trigger_generation` | Chain resolution | Same as above | Same |
| `create_conversation` | Inline body check | `request.design_id` → design → project → org | Skip if no design_id or personal project |
| `direct_generate` | No change | N/A (tier only) | Always personal |
| `upload_file` | Optional query param | `organization_id` query param | Skip if not provided |

## Options Considered

### Option A: Add `organization_id` Column to Conversation and File Models
- **Pro:** Direct org resolution, consistent with other models
- **Con:** Requires Alembic migration, data backfill, breaks model simplicity, changes the lifecycle semantics of conversations from "personal chat" to "org-owned chat"
- **Rejected:** Over-engineering for a feature enforcement task; would require a separate ADR and migration planning

### Option B: X-Organization Header Convention
- **Pro:** Universal org context resolution without URL changes
- **Con:** Non-standard, would need to be added to every request, no existing convention in the codebase, complicates client code, easy to forget
- **Rejected:** Introduces a new cross-cutting pattern that doesn't match the existing architecture

### Option C: Look Up User's Org Memberships
- **Pro:** Works for any user-scoped endpoint
- **Con:** Which org to check if user belongs to multiple? Checking all orgs and requiring ALL to have the feature enabled is overly restrictive. Checking ANY is overly permissive.
- **Rejected:** Ambiguous semantics when user has multiple org memberships

### Option D (Chosen): Resource Chain Resolution + Optional Parameters
- **Pro:** Follows existing patterns exactly, backward compatible, no migration, clear semantics (org enforcement applies only when org context is deterministic)
- **Con:** `direct_generate` and personal conversations have no org enforcement (acceptable — they're personal resources by design)
- **Selected:** Pragmatic, consistent, minimal blast radius

## Consequences

### Positive
- 7/7 gatable features now have org-level enforcement (up from 4/7)
- New resolver follows same pattern as 4 existing resolvers — developers familiar with the pattern
- No schema migration required
- No backward compatibility breaks
- Personal resource semantics preserved
- Reusable utility function (`check_org_feature_for_design`) available for future endpoints

### Negative
- `direct_generate` has no org enforcement — acceptable since it's a stateless personal endpoint, but may need revisiting if direct-generate is later scoped to projects
- File upload org enforcement depends on frontend passing `organization_id` — if frontend omits it, the check is skipped (fail-open for personal uploads)
- Conversation chain resolution adds up to 4 DB queries (conversation → design → project → org) — mitigated by indexed lookups and should be < 50ms

### Risks
- If `direct_generate` is later connected to org-scoped projects, a new resolver will be needed
- Frontend must pass `organization_id` on file uploads for org enforcement to work — needs frontend coordination
- Conversations with deleted designs lose their org chain → treated as personal (acceptable graceful degradation)

## References
- [ADR-015: Security Architecture](adr-015-security-architecture.md)
- [Organization Feature Permissions Guide](../org-feature-permissions.md)
- [RBAC Permission Matrix](../rbac-permission-matrix.md)
- [Org RBAC Audit Report](../security/org-rbac-audit.md)
- Issue: [#307 — Wire Up Org Feature Permission Enforcement](https://github.com/jmassardo/ai-part-designer/issues/307)
- Parent Epic: [#23 — Organization Admin & RBAC](https://github.com/jmassardo/ai-part-designer/issues/23)
