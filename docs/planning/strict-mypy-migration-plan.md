# Strict Mypy Migration Plan

**Issue:** #278 - Enable strict mypy type checking incrementally  
**Epic:** #258 - Code Quality Improvements  
**Status:** Ready for Implementation  
**Date:** 2026-02-06

---

## Executive Summary

Enable `mypy --strict` across the entire backend codebase through an incremental, phased approach. Currently, 19 error codes are disabled and 4 global strictness flags are relaxed, resulting in 620 latent type errors across 100 of 217 source files.

### Success Metrics
- All 19 error codes removed from `disable_error_code` list
- All 4 global strictness flags enabled
- `mypy --strict` passes with zero errors
- Any remaining suppressions use inline `# type: ignore[code]` with documented rationale
- No regression in test coverage (maintain ≥80%)

---

## Current State Analysis

### Configuration Summary
**File:** `backend/pyproject.toml`

**Disabled Error Codes (19):**
```
attr-defined, union-attr, assignment, arg-type, call-arg, operator, 
index, call-overload, misc, return-value, var-annotated, name-defined, 
list-item, prop-decorator, import-untyped, truthy-function, dict-item, 
comparison-overlap, annotation-unchecked
```

**Relaxed Global Flags (4):**
```
warn_return_any = false
disallow_untyped_defs = false
disallow_incomplete_defs = false
check_untyped_defs = false
```

### Error Distribution

| Error Code | Count | Effort | Notes |
|------------|-------|--------|-------|
| `attr-defined` | 222 | High | Many are SQLAlchemy ORM false positives |
| `assignment` | 111 | Medium | Column/value type mismatches |
| `arg-type` | 91 | Medium | Function argument type mismatches |
| `union-attr` | 46 | Medium | Attribute access on union types |
| `call-arg` | 39 | Low | Incorrect function call arguments |
| `operator` | 24 | Low | Unsupported operations on types |
| `return-value` | 22 | Low | Return type mismatches |
| `index` | 20 | Low | Indexing type issues |
| `var-annotated` | 13 | Low | Missing variable annotations |
| `call-overload` | 7 | Low | Overload resolution |
| `import-untyped` | 6 | Low | Untyped library imports |
| `name-defined` | 5 | Low | Undefined names |
| `prop-decorator` | 4 | Low | Property decorator issues |
| `list-item` | 4 | Low | List item types |
| `misc` | 3 | Low | Miscellaneous |
| `truthy-function` | 1 | Trivial | Function used in boolean context |
| `dict-item` | 1 | Trivial | Dict item type |
| `comparison-overlap` | 1 | Trivial | Type comparison issue |

### Directory Distribution

| Directory | Error Count | Priority |
|-----------|-------------|----------|
| `app/api/v1` | 245 | Address with other fixes |
| `app/core` | 97 | Critical - config/auth |
| `app/worker/tasks` | 95 | Background processing |
| `app/seeds` | 57 | Low priority |
| `app/services` | 48 | Business logic |
| `app/api/v2` | 29 | Newer API |
| `app/ai` | 28 | AI integration |
| Other directories | 71 | Various |

---

## Phase 1: Enable Error Codes

### Epic 1.1: Low-Hanging Fruit (Trivial Errors)
**Estimated Effort:** 1 story point  
**Error Codes:** `truthy-function`, `dict-item`, `comparison-overlap`  
**Error Count:** 3 total

---

#### User Story 1.1.1: Enable Trivial Error Codes

**As a** developer  
**I want** trivial mypy error codes enabled  
**So that** we establish momentum and validate the migration approach

**Acceptance Criteria:**

```gherkin
Given the current mypy configuration with all error codes disabled
When I remove "truthy-function", "dict-item", and "comparison-overlap" from disable_error_code
Then mypy passes with zero errors for these codes
And all existing tests continue to pass
And the fix includes inline comments where type: ignore is necessary
```

**Definition of Done:**
- [ ] Remove 3 error codes from `disable_error_code` list
- [ ] Fix all 3 errors (or add documented `# type: ignore[code]` with rationale)
- [ ] Update pyproject.toml
- [ ] Run `make typecheck` - passes
- [ ] Run `make test-backend` - passes
- [ ] PR reviewed and merged

---

### Epic 1.2: Small Error Codes (≤20 errors each)
**Estimated Effort:** 5 story points  
**Error Codes:** `misc`, `name-defined`, `prop-decorator`, `list-item`, `import-untyped`, `call-overload`, `var-annotated`, `index`  
**Error Count:** 62 total

---

#### User Story 1.2.1: Enable misc, name-defined, prop-decorator, list-item

**As a** developer  
**I want** minor structural type errors caught at build time  
**So that** we prevent runtime AttributeErrors and NameErrors

**Acceptance Criteria:**

```gherkin
Given the mypy configuration with these codes disabled
When I remove "misc", "name-defined", "prop-decorator", "list-item" from disable_error_code
Then mypy passes with zero errors for these codes
And the fixes:
  - Add missing imports for undefined names
  - Fix property decorator usage patterns
  - Ensure list items match declared types
  - Resolve miscellaneous type issues
And all tests pass
```

**Error Count:** 16 errors to fix

**Definition of Done:**
- [ ] Fix all 16 errors across affected files
- [ ] Remove 4 error codes from `disable_error_code`
- [ ] Document any `# type: ignore` usage with specific rationale
- [ ] Tests pass

---

#### User Story 1.2.2: Enable import-untyped, call-overload

**As a** developer  
**I want** function overload and import type checking enabled  
**So that** incorrect function call patterns are caught at build time

**Acceptance Criteria:**

```gherkin
Given mypy with import-untyped and call-overload disabled
When I enable these error codes
Then all 13 errors are resolved by:
  - Installing missing type stubs OR
  - Adding py.typed markers OR
  - Adding appropriate type: ignore[import-untyped] with library name documented
  - Fixing call-overload mismatches with correct argument types
And mypy passes
```

**Error Count:** 13 errors to fix

**Definition of Done:**
- [ ] Fix or document all 13 errors
- [ ] If new type stubs needed, add to pyproject.toml [project.optional-dependencies.dev]
- [ ] Remove 2 error codes from `disable_error_code`
- [ ] Tests pass

---

#### User Story 1.2.3: Enable var-annotated, index

**As a** developer  
**I want** variable annotation and indexing type safety  
**So that** untyped variables and incorrect index access are caught

**Acceptance Criteria:**

```gherkin
Given mypy with var-annotated and index disabled
When I enable these error codes
Then all 33 errors are resolved by:
  - Adding type annotations to variables that need them
  - Using TypedDict or proper type narrowing for dict access
  - Adding Optional types where index may fail
And mypy passes
```

**Error Count:** 33 errors to fix

**Definition of Done:**
- [ ] Fix all 33 errors
- [ ] Ensure new annotations follow project conventions
- [ ] Remove 2 error codes from `disable_error_code`
- [ ] Tests pass

---

### Epic 1.3: Medium Error Codes (21-50 errors each)
**Estimated Effort:** 8 story points  
**Error Codes:** `return-value`, `operator`, `call-arg`, `union-attr`  
**Error Count:** 131 total

---

#### User Story 1.3.1: Enable return-value

**As a** developer  
**I want** return type checking enabled  
**So that** functions return the types they promise in their signatures

**Acceptance Criteria:**

```gherkin
Given mypy with return-value disabled
When I enable this error code
Then all 22 errors are resolved by:
  - Correcting function signatures to match actual returns
  - Adding proper type conversions/mappings
  - Using type narrowing where needed
  - Fixing ORM model to Pydantic schema conversions
And mypy passes
```

**Technical Notes:**
- Many errors are in API routes returning ORM models instead of Pydantic schemas
- May require explicit `model_validate()` calls or response_model mapping

**Error Count:** 22 errors to fix

**Definition of Done:**
- [ ] Fix all 22 errors
- [ ] Remove `return-value` from `disable_error_code`
- [ ] Validate API response types match OpenAPI spec
- [ ] Tests pass

---

#### User Story 1.3.2: Enable operator

**As a** developer  
**I want** operator type checking enabled  
**So that** invalid operations between types are caught

**Acceptance Criteria:**

```gherkin
Given mypy with operator disabled
When I enable this error code
Then all 24 errors are resolved by:
  - Adding proper type casts before operations
  - Fixing Optional unwrapping before comparison
  - Using appropriate operator overloads
And mypy passes
```

**Error Count:** 24 errors to fix

**Definition of Done:**
- [ ] Fix all 24 errors
- [ ] Remove `operator` from `disable_error_code`
- [ ] Tests pass

---

#### User Story 1.3.3: Enable call-arg

**As a** developer  
**I want** function call argument checking enabled  
**So that** missing or extra arguments are caught at build time

**Acceptance Criteria:**

```gherkin
Given mypy with call-arg disabled
When I enable this error code
Then all 39 errors are resolved by:
  - Adding missing required arguments
  - Removing unexpected keyword arguments
  - Fixing positional/keyword argument order
And mypy passes
```

**Error Count:** 39 errors to fix

**Definition of Done:**
- [ ] Fix all 39 errors
- [ ] Remove `call-arg` from `disable_error_code`
- [ ] Verify no runtime behavior changes
- [ ] Tests pass

---

#### User Story 1.3.4: Enable union-attr

**As a** developer  
**I want** union type attribute checking enabled  
**So that** attribute access on union types is safe

**Acceptance Criteria:**

```gherkin
Given mypy with union-attr disabled
When I enable this error code
Then all 46 errors are resolved by:
  - Adding proper type guards (isinstance checks)
  - Using TypeVar bounds where appropriate
  - Implementing Protocol types for duck typing
  - Narrowing types before attribute access
And mypy passes
```

**Technical Notes:**
- Common pattern: `x: Model | None` then accessing `x.id` without None check
- May require significant refactoring for proper type narrowing

**Error Count:** 46 errors to fix

**Definition of Done:**
- [ ] Fix all 46 errors
- [ ] Remove `union-attr` from `disable_error_code`
- [ ] Tests pass

---

### Epic 1.4: Large Error Codes (51-100 errors)
**Estimated Effort:** 8 story points  
**Error Codes:** `arg-type`  
**Error Count:** 91 total

---

#### User Story 1.4.1: Enable arg-type

**As a** developer  
**I want** argument type checking enabled  
**So that** type mismatches in function calls are caught

**Acceptance Criteria:**

```gherkin
Given mypy with arg-type disabled
When I enable this error code
Then all 91 errors are resolved by:
  - Passing correct types to functions
  - Adding explicit type conversions where needed
  - Fixing generic type parameters
  - Correcting UUID/str mismatches
And mypy passes
```

**Technical Notes:**
- Common patterns: passing str where UUID expected, dict where TypedDict expected
- May be split into multiple PRs by directory

**Error Count:** 91 errors to fix

**Recommended Split:**
- PR 1: app/api/v1 (est. 35 errors)
- PR 2: app/core, app/services (est. 30 errors)
- PR 3: app/worker, remaining (est. 26 errors)

**Definition of Done:**
- [ ] Fix all 91 errors
- [ ] Remove `arg-type` from `disable_error_code`
- [ ] All UUID/str type handling is consistent
- [ ] Tests pass

---

### Epic 1.5: Largest Error Codes (100+ errors)
**Estimated Effort:** 13 story points  
**Error Codes:** `assignment`, `attr-defined`  
**Error Count:** 333 total

---

#### User Story 1.5.1: Enable assignment

**As a** developer  
**I want** assignment type checking enabled  
**So that** variables are assigned correct types

**Acceptance Criteria:**

```gherkin
Given mypy with assignment disabled
When I enable this error code
Then all 111 errors are resolved by:
  - Using SQLAlchemy's Mapped[] type annotations
  - Fixing Column type declarations
  - Using cast() where necessary for ORM operations
  - Adding proper type annotations to reassigned variables
And mypy passes
```

**Technical Notes:**
- Most errors are SQLAlchemy Column[T] vs T mismatches
- Modern SQLAlchemy 2.0 uses `Mapped[T]` pattern instead of `Column[T]`
- May require migration to SQLAlchemy 2.0 annotation style

**Recommended Split:**
- PR 1: Models layer - update to Mapped[] pattern (est. 20 errors)
- PR 2: API routes (est. 50 errors)  
- PR 3: Services/repositories (est. 41 errors)

**Error Count:** 111 errors to fix

**Definition of Done:**
- [ ] Fix all 111 errors
- [ ] Remove `assignment` from `disable_error_code`
- [ ] Document SQLAlchemy typing pattern used
- [ ] Tests pass

---

#### User Story 1.5.2: Enable attr-defined

**As a** developer  
**I want** attribute definition checking enabled  
**So that** undefined attribute access is caught

**Acceptance Criteria:**

```gherkin
Given mypy with attr-defined disabled
When I enable this error code
Then all 222 errors are resolved by:
  - Adding missing attribute declarations to models
  - Using TYPE_CHECKING blocks for circular imports
  - Implementing __getattr__ with proper type stubs
  - Adding relationship type annotations
  - Using # type: ignore[attr-defined] ONLY for documented SQLAlchemy dynamic attrs
And mypy passes
```

**Technical Notes:**
- Many are SQLAlchemy relationship/backref dynamic attributes
- Some are legitimate bugs (accessing undefined attributes)
- May need sqlalchemy-stubs or SQLAlchemy 2.0 style typing
- Expected: ~50% require code fixes, ~50% require documented ignores

**Recommended Split:**
- PR 1: app/models - add complete type annotations (est. 30 errors)
- PR 2: app/api/v1 (est. 80 errors)
- PR 3: app/api/v2, app/services (est. 50 errors)
- PR 4: app/worker, app/seeds, remaining (est. 62 errors)

**Error Count:** 222 errors to fix

**Definition of Done:**
- [ ] Fix all 222 errors
- [ ] Remove `attr-defined` from `disable_error_code`
- [ ] All `# type: ignore[attr-defined]` have documented rationale
- [ ] Relationship types are properly annotated
- [ ] Tests pass

---

## Phase 2: Enable Global Strictness Flags

### Epic 2.1: Enable Untyped Definition Checks
**Estimated Effort:** 5 story points

---

#### User Story 2.1.1: Enable check_untyped_defs

**As a** developer  
**I want** type checking inside untyped functions  
**So that** errors in function bodies are caught even without signatures

**Acceptance Criteria:**

```gherkin
Given check_untyped_defs = false in pyproject.toml
When I set check_untyped_defs = true
Then any resulting errors are fixed by:
  - Adding type annotations to function bodies
  - Fixing type mismatches inside functions
And mypy passes
```

**Pre-requisite:** All Phase 1 error codes must be enabled first

**Definition of Done:**
- [ ] Set `check_untyped_defs = true`
- [ ] Fix any resulting errors
- [ ] Tests pass

---

#### User Story 2.1.2: Enable disallow_incomplete_defs

**As a** developer  
**I want** partial type annotations disallowed  
**So that** functions are either fully typed or untyped

**Acceptance Criteria:**

```gherkin
Given disallow_incomplete_defs = false
When I set disallow_incomplete_defs = true
Then any resulting errors are fixed by:
  - Completing all partial type annotations
  - Functions have either:
    - Full type hints on all parameters and return type
    - No type hints at all (for legacy code marked for future typing)
And mypy passes
```

**Definition of Done:**
- [ ] Set `disallow_incomplete_defs = true`
- [ ] Fix any resulting errors
- [ ] Tests pass

---

#### User Story 2.1.3: Enable disallow_untyped_defs

**As a** developer  
**I want** all function definitions to require type hints  
**So that** the codebase is fully typed

**Acceptance Criteria:**

```gherkin
Given disallow_untyped_defs = false
When I set disallow_untyped_defs = true
Then all functions have complete type annotations
And mypy passes
And the patterns used are:
  - Return types on all functions (including -> None)
  - Parameter types on all function parameters
  - Class method types including self/cls
```

**Technical Notes:**
- This is the largest effort in Phase 2
- May require annotating legacy code paths
- Focus on public interfaces first

**Definition of Done:**
- [ ] Set `disallow_untyped_defs = true`
- [ ] All functions have type annotations
- [ ] Tests pass

---

#### User Story 2.1.4: Enable warn_return_any

**As a** developer  
**I want** warnings for functions returning Any  
**So that** we avoid type information loss

**Acceptance Criteria:**

```gherkin
Given warn_return_any = false
When I set warn_return_any = true
Then any resulting warnings are resolved by:
  - Adding specific return types instead of Any
  - Using TypeVar for generic returns
  - Using cast() when returning from untyped libraries
And mypy passes
```

**Definition of Done:**
- [ ] Set `warn_return_any = true`
- [ ] Fix any resulting errors  
- [ ] Tests pass

---

## Phase 3: Full Strict Mode

### Epic 3.1: Enable --strict Flag
**Estimated Effort:** 3 story points

---

#### User Story 3.1.1: Enable mypy --strict

**As a** developer  
**I want** full strict mypy checking  
**So that** we have maximum type safety

**Acceptance Criteria:**

```gherkin
Given all Phase 1 and Phase 2 work is complete
When I run `mypy --strict app`
Then mypy passes with zero errors
And the pyproject.toml is updated to use strict = true
And CI/CD runs mypy with --strict flag
```

**Configuration Changes:**
```toml
[tool.mypy]
strict = true
plugins = ["pydantic.mypy"]
# Only keep ignores for external untyped libraries
```

**Definition of Done:**
- [ ] `mypy --strict app` passes
- [ ] Update pyproject.toml with `strict = true`
- [ ] Update CI workflow to use --strict
- [ ] Remove all override sections with `disable_error_code`
- [ ] Document remaining `# type: ignore` usage
- [ ] Tests pass

---

#### User Story 3.1.2: Enable warn_unused_ignores

**As a** developer  
**I want** unused type ignores flagged  
**So that** we remove stale suppressions

**Acceptance Criteria:**

```gherkin
Given strict mode is enabled
When I set warn_unused_ignores = true
Then all unused type: ignore comments are removed
And mypy passes
```

**Definition of Done:**
- [ ] Set `warn_unused_ignores = true`
- [ ] Remove all unused `# type: ignore` comments
- [ ] Tests pass

---

## Work Breakdown Summary

| Phase | Epic | Stories | Est. Points | Error Count |
|-------|------|---------|-------------|-------------|
| 1 | 1.1 Trivial | 1 | 1 | 3 |
| 1 | 1.2 Small | 3 | 5 | 62 |
| 1 | 1.3 Medium | 4 | 8 | 131 |
| 1 | 1.4 Large | 1 | 8 | 91 |
| 1 | 1.5 Largest | 2 | 13 | 333 |
| 2 | 2.1 Global Flags | 4 | 5 | TBD |
| 3 | 3.1 Strict Mode | 2 | 3 | TBD |
| **Total** | **7 Epics** | **17 Stories** | **43 Points** | **620+** |

---

## Dependencies & Sequencing

```
Phase 1 (Error Codes) - Can be parallelized somewhat
├── Epic 1.1 (Trivial) - Start here
├── Epic 1.2 (Small) - After 1.1
├── Epic 1.3 (Medium) - After 1.2
├── Epic 1.4 (Large) - After 1.3
└── Epic 1.5 (Largest) - After 1.4

Phase 2 (Global Flags) - Sequential
├── Story 2.1.1 check_untyped_defs - After Phase 1 complete
├── Story 2.1.2 disallow_incomplete_defs - After 2.1.1
├── Story 2.1.3 disallow_untyped_defs - After 2.1.2
└── Story 2.1.4 warn_return_any - After 2.1.3

Phase 3 (Strict Mode) - Final
├── Story 3.1.1 Enable --strict - After Phase 2 complete
└── Story 3.1.2 Enable warn_unused_ignores - After 3.1.1
```

---

## Non-Functional Requirements

### Performance
- Mypy check time should not exceed 60 seconds on CI
- No runtime performance impact (types are compile-time only)

### Maintainability  
- All `# type: ignore` comments must include specific error code
- All `# type: ignore` comments must have inline rationale comment
- Pattern: `# type: ignore[attr-defined]  # SQLAlchemy dynamic relationship`

### Testing
- All type fixes must pass existing test suite
- No reduction in test coverage
- Add property-based tests (Hypothesis) for complex type narrowing

### Documentation
- Update project README with typing guidelines
- Document SQLAlchemy typing patterns used
- Add CONTRIBUTING.md section on type annotations

---

## Risks & Mitigations

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| SQLAlchemy type complexity | High | Medium | Use SQLAlchemy 2.0 Mapped[] patterns, document idioms |
| Scope creep from cascading fixes | Medium | High | Fix one error code at a time, separate PRs |
| CI/CD breaks during migration | Medium | High | Use feature branches, incremental merges |
| Developer productivity during migration | Medium | Medium | Clear documentation, pair programming on complex fixes |
| False positives requiring ignores | High | Low | Document all ignores, review quarterly for removal |

---

## Handoff Checklist

- [x] All user stories meet INVEST criteria
- [x] Acceptance criteria use Given-When-Then format
- [x] Error counts quantified per story
- [x] Dependencies documented
- [x] Non-functional requirements specified with measurable targets
- [x] Work breakdown ≤3 days per task (each PR within a story)
- [x] Risks identified with mitigations

---

## Ready for Architecture Review

This plan is ready for handoff to the Architecture & Security Agent for:
- Review of SQLAlchemy typing approach
- Validation of phased migration strategy
- Security implications of type changes
- CI/CD integration planning
