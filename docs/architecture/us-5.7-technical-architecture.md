# Technical Architecture: US-5.7 Org Feature Enforcement Completion

**Issue:** [#307](https://github.com/jmassardo/ai-part-designer/issues/307)  
**ADR:** [ADR-018](../adrs/adr-018-org-feature-enforcement-for-user-scoped-resources.md)  
**Date:** 2026-02-11  
**Author:** Architecture & Security Agent  

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Authorization Model](#2-authorization-model)
3. [Data Flow Architecture](#3-data-flow-architecture)
4. [Component Specifications](#4-component-specifications)
5. [API Contracts](#5-api-contracts)
6. [Data Models](#6-data-models)
7. [Security Controls](#7-security-controls)
8. [Performance Analysis](#8-performance-analysis)
9. [Testing Architecture](#9-testing-architecture)
10. [Deployment & Rollback](#10-deployment--rollback)
11. [Handoff Package for Development Agent](#11-handoff-package-for-development-agent)

---

## 1. Architecture Overview

### 1.1 Current State

The platform has a **dual-layer feature enforcement model**:

```
┌─────────────────────────────────────────────────────────────────┐
│                    FEATURE ENFORCEMENT LAYERS                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Layer 1: TIER ENFORCEMENT (require_feature)                     │
│  ├── Checked against: User's subscription tier                   │
│  ├── Scope: Global capability gate                               │
│  ├── Example: Free users can't use ai_generation                 │
│  └── Status: ✅ Fully wired on all endpoints                     │
│                                                                  │
│  Layer 2: ORG ENFORCEMENT (require_org_feature)                  │
│  ├── Checked against: Organization.settings.enabled_features     │
│  ├── Scope: Org-level policy override                            │
│  ├── Example: Org admin disables ai_chat for the org             │
│  └── Status: ⚠️  4/7 features wired, 3 MISSING                  │
│                                                                  │
│  Request must pass BOTH layers to proceed.                       │
│  Layer 2 is skipped for personal (non-org) resources.            │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 1.2 Target State

```
Enforcement Status:
  ✅ teams           → require_org_feature("teams")
  ✅ design_sharing  → require_org_feature_for_design("design_sharing")
  ✅ assemblies      → require_org_feature_for_project("assemblies")
  ✅ bom             → require_org_feature_for_assembly("bom")
  🔧 ai_chat        → require_org_feature_for_conversation("ai_chat")           [NEW]
  🔧 ai_generation  → require_org_feature_for_conversation("ai_generation")     [NEW]
  🔧 file_uploads   → require_org_feature("file_uploads") + optional org_id     [NEW]
```

### 1.3 Enforcement Decision Flow

```
                    ┌─────────────┐
                    │   Request   │
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │ Authenticate│
                    │  (JWT)      │
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐     No
                    │ Tier Check  ├──────────► 403 "feature_not_available"
                    │ (Layer 1)   │            "on {tier} tier"
                    └──────┬──────┘
                           │ Yes
                    ┌──────▼──────┐
                    │ Resolve Org │
                    │ Context     │
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐     No org context
                    │ Org found?  ├──────────► SKIP Layer 2
                    │             │            (personal resource)
                    └──────┬──────┘            │
                           │ Yes               │
                    ┌──────▼──────┐            │
                    │ Org Feature ├── No ──►   │  403 "feature_disabled"
                    │ Enabled?    │            │  "for this organization"
                    │ (Layer 2)   │            │
                    └──────┬──────┘            │
                           │ Yes               │
                    ┌──────▼──────────────◄────┘
                    │  Proceed to         │
                    │  Business Logic     │
                    └─────────────────────┘
```

---

## 2. Authorization Model

### 2.1 Ownership & Authorization Chain

```
┌─────────────────────────────────────────────────────────────────┐
│                    RESOURCE OWNERSHIP MODEL                       │
└─────────────────────────────────────────────────────────────────┘

  Organization (optional policy owner)
       │
       │ owns (organization_id FK)
       ▼
  Project
       │
       │ owns (project_id FK)
       ├──────────────────┬─────────────────┐
       ▼                  ▼                 ▼
    Design            Assembly          (other resources)
       │                  │
       │ ref (design_id)  │
       ▼                  │
  Conversation            │
       │                  │
       │ ref (user_id)    │
       ▼                  │
     File                 │
  (standalone)            │
                          │
                          ▼
                        BOM

  Resolution Chains (existing):
  ──────────────────────────────
  require_org_feature:              org_id (path param) → org
  require_org_feature_for_project:  project_id → project.org_id → org
  require_org_feature_for_design:   design_id → design.project_id → project.org_id → org
  require_org_feature_for_assembly: assembly_id → assembly.project_id → project.org_id → org

  Resolution Chains (new):
  ─────────────────────────
  require_org_feature_for_conversation:
    conversation_id → conversation.design_id → design.project_id → project.org_id → org
                      ▲
                      │ Falls back to "skip" (personal) if NULL at any point

  check_org_feature_for_design (utility, not dependency):
    design_id (from body) → design.project_id → project.org_id → org

  upload_file:
    organization_id (query param, optional) → org
    ▲
    │ Falls back to "skip" (personal) if not provided
```

### 2.2 Permission Enforcement Matrix (Updated)

| Feature | Endpoint | Auth | Tier Check | Org Check | Resolver |
|---------|----------|------|------------|-----------|----------|
| `ai_chat` | `POST /conversations` | JWT | `require_feature("ai_chat")` | Inline `check_org_feature_for_design` if `design_id` in body | Body-derived |
| `ai_chat` | `POST /conversations/{id}/messages` | JWT | `require_feature("ai_chat")` | `require_org_feature_for_conversation("ai_chat")` | Chain |
| `ai_generation` | `POST /conversations/direct-generate` | JWT | `require_feature("ai_generation")` | None (personal) | N/A |
| `ai_generation` | `POST /conversations/{id}/generate` | JWT | `require_feature("ai_generation")` | `require_org_feature_for_conversation("ai_generation")` | Chain |
| `file_uploads` | `POST /files/upload` | JWT | `require_feature("file_uploads")` | `require_org_feature("file_uploads")` via optional `organization_id` query | Query param |
| `teams` | Team CRUD endpoints | JWT | N/A | `require_org_feature("teams")` | Direct org_id |
| `design_sharing` | Share endpoints | JWT | N/A | `require_org_feature_for_design("design_sharing")` | Design chain |
| `assemblies` | Assembly endpoints | JWT | N/A | `require_org_feature_for_project("assemblies")` | Project chain |
| `bom` | BOM endpoints | JWT | N/A | `require_org_feature_for_assembly("bom")` | Assembly chain |

---

## 3. Data Flow Architecture

### 3.1 Conversation with Org Design — Send Message Flow

```
 User        Frontend       API           deps.py          Database
  │             │            │              │                │
  │  Send msg   │            │              │                │
  │────────────>│            │              │                │
  │             │  POST      │              │                │
  │             │  /convos   │              │                │
  │             │  /{id}/msg │              │                │
  │             │───────────>│              │                │
  │             │            │              │                │
  │             │            │  1. get_current_user          │
  │             │            │──────────────>│                │
  │             │            │              │  JWT validate  │
  │             │            │              │───────────────>│
  │             │            │              │  user          │
  │             │            │<──────────────│<───────────────│
  │             │            │              │                │
  │             │            │  2. require_feature("ai_chat")│
  │             │            │──────────────>│                │
  │             │            │              │  check tier    │
  │             │            │              │  has_feature() │
  │             │            │<──────────────│                │
  │             │            │              │                │
  │             │            │  3. require_org_feature_for_  │
  │             │            │     conversation("ai_chat")   │
  │             │            │──────────────>│                │
  │             │            │              │  SELECT convo  │
  │             │            │              │───────────────>│
  │             │            │              │  convo.design_id
  │             │            │              │<───────────────│
  │             │            │              │                │
  │             │            │              │  [design_id?]  │
  │             │            │              │  yes:          │
  │             │            │              │  SELECT design │
  │             │            │              │───────────────>│
  │             │            │              │  design.proj_id│
  │             │            │              │<───────────────│
  │             │            │              │                │
  │             │            │              │  SELECT project│
  │             │            │              │───────────────>│
  │             │            │              │  project.org_id│
  │             │            │              │<───────────────│
  │             │            │              │                │
  │             │            │              │  [org_id?]     │
  │             │            │              │  yes:          │
  │             │            │              │  SELECT org    │
  │             │            │              │───────────────>│
  │             │            │              │  org           │
  │             │            │              │<───────────────│
  │             │            │              │                │
  │             │            │              │  org.has_feature│
  │             │            │              │  ("ai_chat")   │
  │             │            │              │                │
  │             │            │  ✅ or 403   │                │
  │             │            │<──────────────│                │
  │             │            │              │                │
  │             │            │  [If ✅ proceed to business logic]
  │             │            │              │                │
  │             │  Response  │              │                │
  │             │<───────────│              │                │
  │  Result     │            │              │                │
  │<────────────│            │              │                │
```

### 3.2 File Upload with Org Context Flow

```
 User        Frontend       API           deps.py          Database
  │             │            │              │                │
  │  Upload     │            │              │                │
  │  in org     │            │              │                │
  │  context    │            │              │                │
  │────────────>│            │              │                │
  │             │  POST      │              │                │
  │             │  /files/   │              │                │
  │             │  upload?   │              │                │
  │             │  org_id=X  │              │                │
  │             │───────────>│              │                │
  │             │            │              │                │
  │             │            │  1. get_current_user          │
  │             │            │──────────────>│  (JWT)        │
  │             │            │<──────────────│                │
  │             │            │              │                │
  │             │            │  2. require_feature           │
  │             │            │     ("file_uploads")          │
  │             │            │──────────────>│  (tier check) │
  │             │            │<──────────────│                │
  │             │            │              │                │
  │             │            │  3. require_org_feature       │
  │             │            │     ("file_uploads")          │
  │             │            │──────────────>│                │
  │             │            │              │  org_id = X    │
  │             │            │              │  (from query)  │
  │             │            │              │                │
  │             │            │              │  SELECT org    │
  │             │            │              │───────────────>│
  │             │            │              │  org           │
  │             │            │              │<───────────────│
  │             │            │              │                │
  │             │            │              │  org.has_feature│
  │             │            │              │  ("file_uploads")
  │             │            │              │                │
  │             │            │  ✅ or 403   │                │
  │             │            │<──────────────│                │
  │             │            │              │                │
  │             │            │  [Proceed to upload logic]    │
```

### 3.3 Personal Conversation — No Org Enforcement

```
 User        Frontend       API           deps.py          Database
  │             │            │              │                │
  │  New chat   │            │              │                │
  │  (no design)│            │              │                │
  │────────────>│            │              │                │
  │             │  POST      │              │                │
  │             │  /convos   │              │                │
  │             │  body: {}  │              │                │
  │             │───────────>│              │                │
  │             │            │              │                │
  │             │            │  1. get_current_user (JWT)    │
  │             │            │  2. require_feature("ai_chat")│
  │             │            │     → tier check → ✅         │
  │             │            │              │                │
  │             │            │  3. Parse body: design_id=None│
  │             │            │     → Skip org check          │
  │             │            │     (personal resource)       │
  │             │            │              │                │
  │             │            │  [Proceed to create convo]    │
  │             │            │              │                │
  │             │  201       │              │                │
  │             │<───────────│              │                │
```

---

## 4. Component Specifications

### 4.1 New Dependency: `require_org_feature_for_conversation`

**Location:** `backend/app/api/deps.py`  
**Pattern:** Factory function returning async FastAPI dependency  
**Signature:**

```python
def require_org_feature_for_conversation(feature_name: str) -> Callable[..., None]:
```

**Input Dependencies (injected by FastAPI):**
- `conversation_id: UUID` — from path parameters
- `db: AsyncSession` — from `get_db`
- `_user: User` — from `get_current_user` (ensures auth)

**Resolution Algorithm:**

```
1. SELECT conversation WHERE id = conversation_id
   → Not found? raise 404
   → No design_id? return (skip — personal)

2. SELECT design WHERE id = conversation.design_id
   → Not found? return (skip — design deleted, treat as personal)

3. SELECT project WHERE id = design.project_id
   → Not found? return (skip — data integrity fallback)
   → No organization_id? return (skip — personal project)

4. SELECT organization WHERE id = project.organization_id
   → Not found? raise 404 (org deleted but still referenced — data integrity)

5. org.has_feature(feature_name)?
   → No? raise 403 {"error": "feature_disabled", "feature": feature_name}
   → Yes? return (allow)
```

**Query Plan:** 4 indexed primary key lookups (conversations.id, designs.id, projects.id, organizations.id). All are B-tree index scans, expected < 1ms each.

### 4.2 Utility Function: `check_org_feature_for_design`

**Location:** `backend/app/api/deps.py`  
**Purpose:** Non-dependency function for inline use when `design_id` comes from the request body  
**Signature:**

```python
async def check_org_feature_for_design(
    db: AsyncSession,
    design_id: UUID,
    feature_name: str,
) -> None:
```

**Algorithm:** Same as steps 2-5 of `require_org_feature_for_conversation`, starting from a known `design_id`.

### 4.3 Modified Endpoint: `upload_file`

**File:** `backend/app/api/v1/files.py`  
**Change:** Add `organization_id: UUID | None = Query(None, description="Organization ID for org-scoped uploads")` parameter and add `Depends(require_org_feature("file_uploads"))` dependency.

The existing `require_org_feature` resolver already handles optional `organization_id` via its parameter signature:
```python
async def dependency(
    organization_id: UUID | None = None,  # ← FastAPI binds from query param
    ...
) -> None:
```

---

## 5. API Contracts

### 5.1 Unchanged Endpoints (Backward Compatible)

All existing request/response schemas remain unchanged. The only addition is an **optional** query parameter on one endpoint.

### 5.2 Modified: `POST /api/v1/files/upload`

**New optional query parameter:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `organization_id` | `UUID` | No | `null` | When provided, enforces org-level `file_uploads` feature check |

**Example requests:**
```bash
# Personal upload (no org enforcement)
POST /api/v1/files/upload
Content-Type: multipart/form-data

# Org-scoped upload (org enforcement applied)
POST /api/v1/files/upload?organization_id=550e8400-e29b-41d4-a716-446655440000
Content-Type: multipart/form-data
```

### 5.3 Error Response Contract

All new 403 responses follow the existing error format (consistent with teams, shares, assemblies, BOM):

```json
{
  "detail": {
    "error": "feature_disabled",
    "message": "Feature 'ai_chat' is not enabled for this organization",
    "feature": "ai_chat"
  }
}
```

| HTTP Status | Condition | Response Body |
|-------------|-----------|---------------|
| 403 | Org feature disabled | `{"detail": {"error": "feature_disabled", "message": "...", "feature": "..."}}` |
| 403 | Tier feature unavailable | `{"detail": {"error": "feature_not_available", "message": "...", "required_tier": "Pro or Enterprise"}}` |
| 404 | Conversation not found | `{"detail": "Conversation not found"}` |
| 404 | Organization not found (data integrity) | `{"detail": "Organization not found"}` |

---

## 6. Data Models

### 6.1 No Model Changes Required

The implementation requires **zero** schema migrations. All enforcement is done through query-time resolution of existing foreign key relationships.

### 6.2 Entity Relationship — Enforcement Traversal

```
┌───────────────┐                       ┌──────────────────┐
│ conversations │                       │   organizations  │
├───────────────┤                       ├──────────────────┤
│ PK id         │                       │ PK id            │
│ FK user_id    │                       │    settings JSONB │
│ FK design_id ─┼──────┐               │    .enabled_features
│    status     │      │               │    .subscription_tier
│    title      │      │               └──────────────────┘
└───────────────┘      │                        ▲
                       │                        │
                       ▼                        │
                ┌──────────────┐                │ FK organization_id
                │   designs    │                │
                ├──────────────┤         ┌──────┴───────┐
                │ PK id        │         │   projects   │
                │ FK project_id├────────>│ PK id        │
                │ FK user_id   │         │ FK user_id   │
                │    name      │         │ FK org_id?   │
                └──────────────┘         │    name      │
                                         └──────────────┘

Traversal: conversation.design_id → designs.project_id → projects.organization_id → organizations.id
                                                          ▲
                                     NULL here = personal project → skip org check
```

### 6.3 Query Performance — Index Coverage

| Table | Column | Index | Type |
|-------|--------|-------|------|
| `conversations` | `id` | Primary Key | B-tree |
| `designs` | `id` | Primary Key | B-tree |
| `designs` | `project_id` | `ix_designs_project_id` | B-tree |
| `projects` | `id` | Primary Key | B-tree |
| `projects` | `organization_id` | `ix_projects_organization_id` | B-tree |
| `organizations` | `id` | Primary Key | B-tree |

All lookups are indexed primary key scans. No sequential scans, no joins.

---

## 7. Security Controls

### 7.1 Defense in Depth — Enforcement Layers

```
┌─────────────────────────────────────────────────────────────────┐
│                    SECURITY CONTROL STACK                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Layer 0: NETWORK                                                │
│  ├── TLS 1.3 mandatory                                          │
│  ├── Rate limiting (30-500 req/min by tier)                     │
│  └── IP blocking (if applicable)                                │
│                                                                  │
│  Layer 1: AUTHENTICATION                                         │
│  ├── JWT validation (HS256, 15-min expiry)                      │
│  ├── Token blacklist check (Redis)                              │
│  └── get_current_user dependency                                │
│                                                                  │
│  Layer 2: TIER AUTHORIZATION                                     │
│  ├── require_feature(feature_name)                              │
│  ├── Checks SubscriptionTier.has_feature()                      │
│  └── 403: "feature_not_available on {tier} tier"                │
│                                                                  │
│  Layer 3: ORG POLICY AUTHORIZATION  ◄── THIS CHANGE             │
│  ├── require_org_feature_for_conversation(feature_name)         │
│  ├── require_org_feature(feature_name) [for files]              │
│  ├── Resolves org through resource chain                        │
│  ├── Checks Organization.has_feature()                          │
│  ├── Skips for personal resources (no org in chain)             │
│  └── 403: "feature_disabled for this organization"              │
│                                                                  │
│  Layer 4: RESOURCE AUTHORIZATION                                 │
│  ├── Resource ownership check (user_id match)                   │
│  ├── require_org_role for org endpoints                         │
│  └── 403/404 as appropriate                                     │
│                                                                  │
│  Layer 5: INPUT VALIDATION                                       │
│  ├── Pydantic models (FastAPI auto-validation)                  │
│  ├── Size limits, type checks                                   │
│  └── 422 for invalid input                                      │
│                                                                  │
│  Layer 6: BUSINESS LOGIC                                         │
│  ├── Credit/quota checks                                        │
│  ├── Storage quota enforcement                                  │
│  └── Rate limiting at operation level                           │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 7.2 Threat Analysis (STRIDE)

| Threat | Vector | Mitigation | Residual Risk |
|--------|--------|------------|---------------|
| **Spoofing** | Attacker forges JWT to bypass auth | JWT validation, token blacklisting (existing Layer 1) | LOW — already mitigated |
| **Tampering** | Attacker modifies `organization_id` query param to bypass check | `organization_id` is used to *increase* enforcement (passing one triggers the check). Omitting it means personal upload — not an escalation. | LOW — fail-open only for personal context, which is the intended design |
| **Repudiation** | User denies they bypassed org policy | Audit logging records all 403 responses with `user_id`, `feature_name`, `org_id`. (Full tracking in #308) | MEDIUM — depends on #308 completion for comprehensive tracking |
| **Information Disclosure** | 403 error leaks org details | Error response contains only `feature_name` (public enum value) and generic message. No org name, member list, or internal state. | LOW |
| **Denial of Service** | Attacker sends many requests to trigger expensive chain resolution | Rate limiting (existing Layer 0). Chain resolution is 4 indexed PK lookups (< 5ms total). Not a significant amplification vector. | LOW |
| **Elevation of Privilege** | User in org with `ai_chat` disabled circumvents by not passing org context | For conversations: org context is *automatically* resolved from `design_id` chain — user cannot opt out if conversation is linked to org design. For file uploads: user can omit `organization_id` — mitigated by frontend always sending it in org context. Backend-only defense is acceptable given the fail-open-to-personal design. | MEDIUM for files (frontend dependency) |

### 7.3 Security Controls Checklist

| Control | Status | Implementation |
|---------|--------|----------------|
| Authentication required | ✅ Existing | `Depends(get_current_user)` on all endpoints |
| Tier authorization | ✅ Existing | `Depends(require_feature(...))` already in place |
| Org authorization | 🔧 Adding | New `require_org_feature_for_conversation` + existing `require_org_feature` for files |
| Input validation | ✅ Existing | Pydantic models validate UUID formats, string lengths |
| Rate limiting | ✅ Existing | Global + endpoint-specific rate limits |
| Error response sanitization | ✅ Verified | 403 responses contain only public enum values, no internal state |
| Audit logging | ⏳ Partial | Basic logging exists; comprehensive 403 tracking planned in #308 |
| No SQL injection | ✅ Existing | SQLAlchemy ORM with parameterized queries |
| No IDOR | ✅ Existing | Resource ownership check (`conversation.user_id == current_user.id`) on all endpoints |

### 7.4 Fail-Open vs Fail-Closed Analysis

| Scenario | Behavior | Justification |
|----------|----------|---------------|
| No `design_id` on conversation | **Skip** org check (personal) | Design intent — personal conversations are not org-governed |
| `design_id` points to deleted design | **Skip** org check | Graceful degradation — don't block user because of orphaned data |
| `design_id` → project with no org | **Skip** org check (personal project) | Consistent with all existing resolvers |
| `organization_id` not passed on upload | **Skip** org check (personal upload) | Frontend responsibility to pass in org context |
| Organization record deleted but still referenced | **404** "Organization not found" | Data integrity issue — surface for investigation |
| Feature check DB query fails | **500** Internal Server Error | FastAPI default exception handling — do not silently pass |

**Verdict:** The fail-open cases are all **intentional** and apply only to personal resources. Org-scoped resources always have the check enforced (the org is automatically resolved from the resource chain — users cannot opt out).

---

## 8. Performance Analysis

### 8.1 Query Cost

| Operation | Queries Added | Index Type | Expected Latency |
|-----------|---------------|------------|-------------------|
| `send_message` org check | +4 (conversation, design, project, org) | PK B-tree | < 5ms |
| `trigger_generation` org check | +4 (same chain) | PK B-tree | < 5ms |
| `create_conversation` inline check | +3 (design, project, org) OR 0 (no design_id) | PK B-tree | < 4ms or 0ms |
| `upload_file` org check | +1 (org) OR 0 (no org_id) | PK B-tree | < 1ms or 0ms |

### 8.2 Impact on p95 Latency

| Endpoint | Current p95 | Added Overhead | New p95 (est.) |
|----------|-------------|----------------|----------------|
| `POST /conversations` | ~80ms | 0-4ms | ~84ms |
| `POST /conversations/{id}/messages` | ~200ms | 5ms | ~205ms |
| `POST /conversations/{id}/generate` | ~2000ms | 5ms | ~2005ms |
| `POST /files/upload` | ~500ms | 0-1ms | ~501ms |

**Conclusion:** Overhead is negligible relative to the core operation time. No caching needed.

### 8.3 Database Connection Impact

Each chain resolution uses the **same** `AsyncSession` already injected into the endpoint via `Depends(get_db)`. No additional connection pool consumption. All queries execute sequentially within the existing session — no connection thrashing.

---

## 9. Testing Architecture

### 9.1 Test Fixtures Required

```python
# Existing fixtures (reused):
- test_user                    # Authenticated user
- test_org_with_features       # Org with all features enabled
- test_org_no_features         # Org with all features disabled
- test_project_in_org          # Project in org with features
- test_project_in_org_no_features  # Project in org without features

# New fixtures needed:
- test_design_in_org           # Design in org-scoped project
- test_design_in_org_no_features   # Design in org with features disabled
- test_conversation_with_org_design    # Conversation linked to org design
- test_conversation_with_org_design_no_features  # Conversation linked to org design (features off)
- test_conversation_personal   # Conversation with no design_id
```

### 9.2 Test Cases — Full Matrix

#### Conversation Feature Enforcement

| # | Test Case | Feature | Expected | Verifies |
|---|-----------|---------|----------|----------|
| 1 | Create convo with design in org, `ai_chat` disabled | `ai_chat` | 403 | Body-derived inline check |
| 2 | Create convo without `design_id`, org `ai_chat` disabled | `ai_chat` | 201 | Personal skip |
| 3 | Create convo with design in personal project | `ai_chat` | 201 | Personal project skip |
| 4 | Send message in convo linked to org design, `ai_chat` disabled | `ai_chat` | 403 | Chain resolver |
| 5 | Send message in personal convo (no design) | `ai_chat` | 200 | Personal skip |
| 6 | Trigger generation in convo linked to org design, `ai_generation` disabled | `ai_generation` | 403 | Chain resolver |
| 7 | Trigger generation in personal convo | `ai_generation` | 200 | Personal skip |
| 8 | Direct generate (no org context) | `ai_generation` | 200 | Tier-only enforcement |
| 9 | Re-enable `ai_chat`, immediately retry | `ai_chat` | 201 | Real-time toggle |

#### File Upload Feature Enforcement

| # | Test Case | Feature | Expected | Verifies |
|---|-----------|---------|----------|----------|
| 10 | Upload with `organization_id`, `file_uploads` disabled | `file_uploads` | 403 | Query param resolver |
| 11 | Upload without `organization_id` | `file_uploads` | 201 | Personal skip |
| 12 | Upload with `organization_id`, `file_uploads` enabled | `file_uploads` | 201 | Happy path |
| 13 | Upload with non-existent `organization_id` | `file_uploads` | 404 | Org not found |
| 14 | Re-enable `file_uploads`, immediately retry | `file_uploads` | 201 | Real-time toggle |

#### Resolver Unit Tests

| # | Test Case | Expected |
|---|-----------|----------|
| 15 | `require_org_feature_for_conversation` — convo not found | 404 |
| 16 | `require_org_feature_for_conversation` — convo with no design_id | allow (skip) |
| 17 | `require_org_feature_for_conversation` — design deleted | allow (skip) |
| 18 | `require_org_feature_for_conversation` — personal project | allow (skip) |
| 19 | `require_org_feature_for_conversation` — org deleted | 404 |
| 20 | `require_org_feature_for_conversation` — feature disabled | 403 |
| 21 | `require_org_feature_for_conversation` — feature enabled | allow |
| 22 | `check_org_feature_for_design` — design not found | allow (skip) |
| 23 | `check_org_feature_for_design` — personal project | allow (skip) |
| 24 | `check_org_feature_for_design` — feature disabled | 403 |

### 9.3 Test Quality Gates

| Metric | Target |
|--------|--------|
| New code coverage | ≥ 90% of new enforcement code paths |
| Overall backend coverage | Maintain ≥ 80% |
| All existing tests pass | 0 regressions |
| Linting (ruff) | 0 violations |
| Type checking (mypy) | 0 errors |
| Security scan (bandit) | 0 HIGH/MEDIUM findings |

---

## 10. Deployment & Rollback

### 10.1 Migration Requirements

**None.** Zero Alembic migrations. All changes are in application code only.

### 10.2 Deployment Steps

1. Deploy backend with new `deps.py`, `conversations.py`, `files.py` changes
2. Deploy frontend with `organization_id` query param on file uploads (can be done separately)
3. Verify via monitoring: 403 responses appear for disabled features

### 10.3 Feature Flag / Gradual Rollout

Not needed — the changes are additive dependencies that follow the existing fail-open-for-personal pattern. The worst case is a 403 for a legitimately disabled feature that was previously unblocked (which is the *intended behavior*).

### 10.4 Rollback Plan

| Severity | Action | Time to Execute |
|----------|--------|-----------------|
| Minor regression | Revert specific dependency (`git revert` on the commit) | < 5 min |
| Blocking users | Remove `Depends(require_org_feature_for_conversation(...))` from endpoint signatures | Single-line revert per endpoint, < 10 min |
| Data issue | No data changes, no rollback needed | N/A |

### 10.5 CI Pipeline Validation

| CI Stage | This Change Touches | Expected Impact |
|----------|---------------------|-----------------|
| Quick Checks (ruff, mypy, bandit) | `deps.py`, `conversations.py`, `files.py`, tests | Must pass — no type:ignore, no noqa, no security violations |
| Unit Tests | New test cases | Must pass — 24 new test cases |
| Integration Tests (PostgreSQL + Redis) | Org feature enforcement uses real DB | Must pass — fixtures create real org/project/design/conversation records |
| Migration Check | No new migrations | N/A — no Alembic changes |
| Docker Builds | No Dockerfile changes | N/A |
| E2E Tests (Playwright) | No frontend changes in this PR | Should pass — backward compatible |

---

## 11. Handoff Package for Development Agent

### Architecture Overview

Dual-layer feature enforcement (tier + org) for user-scoped endpoints. New resolver resolves org through conversation → design → project → org chain. Personal resources skip org check.

### Component Specifications

| Component | File | Action |
|-----------|------|--------|
| `require_org_feature_for_conversation` | `backend/app/api/deps.py` | **Create** — new resolver factory |
| `check_org_feature_for_design` | `backend/app/api/deps.py` | **Create** — utility function |
| `__all__` exports | `backend/app/api/deps.py` | **Update** — add new exports |
| `create_conversation` | `backend/app/api/v1/conversations.py` | **Modify** — add inline org check |
| `send_message` | `backend/app/api/v1/conversations.py` | **Modify** — add dependency |
| `trigger_generation` | `backend/app/api/v1/conversations.py` | **Modify** — add dependency |
| `upload_file` | `backend/app/api/v1/files.py` | **Modify** — add dependency + query param |
| `TestConversationFeatureEnforcement` | `backend/tests/api/test_org_feature_enforcement.py` | **Rewrite** — proper org-level tests |
| `TestFileUploadFeatureEnforcement` | `backend/tests/api/test_org_feature_enforcement.py` | **Rewrite** — proper org-level tests |

### Technology Stack

No changes to technology stack. Uses existing:
- **Backend:** Python 3.11+, FastAPI, SQLAlchemy (async), PostgreSQL
- **Testing:** pytest with async fixtures
- **Linting:** ruff, mypy, bandit

### API Contracts

Single change: optional `organization_id` query param on `POST /files/upload`. All other endpoints unchanged.

### Security Implementation Requirements

- Authentication: JWT (existing `get_current_user`)
- Tier authorization: `require_feature` (existing, keep)
- Org authorization: `require_org_feature_for_conversation` (new) + `require_org_feature` (existing, reuse)
- Error format: `{"error": "feature_disabled", "message": "...", "feature": "..."}`
- No inline ignore comments (`# type: ignore`, `# noqa`)
- All new code requires type hints and docstrings

### Development Patterns

- Follow `require_org_feature_for_design` and `require_org_feature_for_assembly` as reference implementations
- Use SQLAlchemy `select().where()` pattern (no raw SQL)
- Return `dependency` function from factory (same `# type: ignore[return-value]` annotation as existing)
- Inline imports for models inside dependency functions (same pattern as existing resolvers)

### Performance Requirements

- Chain resolution overhead: < 10ms p99
- No new database indexes needed
- Use existing `AsyncSession` from `Depends(get_db)`

### Technical Constraints

- No Alembic migrations
- No new pip dependencies
- No changes to Pydantic request/response models (except optional query param)
- `direct_generate` remains tier-only (no org enforcement)
- Must pass `ruff check .`, `mypy .`, `pytest`, `bandit -r app -ll -ii`
