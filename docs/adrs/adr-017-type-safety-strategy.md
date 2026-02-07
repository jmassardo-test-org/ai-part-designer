# ADR-017: Type Safety Strategy

## Status

Proposed

## Date

2026-02-06

## Context

The AI Part Designer codebase needs to enable strict mypy type checking to:

1. **Catch Bugs Early** - Type errors detected at build time rather than runtime
2. **Improve IDE Support** - Better autocomplete, refactoring, and navigation
3. **Document Intent** - Types serve as always-accurate documentation
4. **Enable Safe Refactoring** - Confidence when changing code
5. **Security** - Prevent type confusion vulnerabilities

### Current State

- 620 latent type errors across 100 of 217 files
- 19 mypy error codes disabled via `disable_error_code`
- 4 global strictness flags relaxed
- SQLAlchemy 2.0 `Mapped[]` pattern already in use (positive finding)

### Challenges

1. **SQLAlchemy Dynamic Attributes** - Relationships, backrefs, and hybrid properties
2. **Generic Repository Pattern** - TypeVar doesn't express attribute requirements
3. **Third-Party Libraries** - Missing type stubs for several dependencies
4. **SQLAlchemy Expressions** - Column expressions vs Python values

## Decision

We will adopt a **strict mypy configuration** with the following strategies:

### 1. Use Protocol Types for Generic Patterns

Define Protocol types that express the requirements for generic TypeVars:

```python
from typing import Protocol, runtime_checkable
from sqlalchemy.orm import Mapped

@runtime_checkable
class StandardEntity(Protocol):
    id: Mapped[UUID]
    created_at: Mapped[datetime]
    updated_at: Mapped[datetime]
    deleted_at: Mapped[datetime | None]
```

### 2. Maintain SQLAlchemy 2.0 Mapped[] Pattern

The codebase already uses modern SQLAlchemy typing. Continue with:

```python
class User(Base, TimestampMixin, SoftDeleteMixin):
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True)
    projects: Mapped[list["Project"]] = relationship(back_populates="owner")
```

### 3. Use TypedDict for JSON Structures

Replace `dict[str, Any]` with TypedDict where structure is known:

```python
class CADMetadata(TypedDict):
    format: str
    dimensions: tuple[float, float, float]
    units: str
```

### 4. Type Alias Module

Create `app/types/` with reusable type definitions:

```python
# app/types/aliases.py
SQLFilter: TypeAlias = ColumnElement[bool]
EntityID: TypeAlias = UUID
JSONDict: TypeAlias = dict[str, Any]
```

### 5. Documented Type Suppressions

When `# type: ignore` is necessary, require:

```python
# type: ignore[error-code]  # Specific reason - e.g., "SQLAlchemy dynamic backref"
```

## Consequences

### Positive

- **Build-Time Error Detection** - Catch type errors before runtime
- **Better Developer Experience** - IDE autocomplete and type hints
- **Safer Refactoring** - Confidence when changing function signatures
- **Self-Documenting Code** - Types as always-accurate documentation
- **Reduced Test Burden** - Type system catches many error classes

### Negative

- **Initial Migration Effort** - 620 errors to fix (~43 story points)
- **Third-Party Library Friction** - Some libraries lack stubs
- **Learning Curve** - Team must understand Python typing
- **Build Time Increase** - Mypy adds ~30-60 seconds to CI

### Neutral

- **Ongoing Maintenance** - New code must be typed (enforced by CI)
- **Stub Management** - May need to update stubs with library upgrades

## Implementation

### Phase 1: Error Codes (35 story points)

Enable error codes incrementally, starting with lowest-impact:

1. Trivial codes (3 errors): `truthy-function`, `dict-item`, `comparison-overlap`
2. Small codes (62 errors): `misc`, `name-defined`, `prop-decorator`, `list-item`, etc.
3. Medium codes (131 errors): `return-value`, `operator`, `call-arg`, `union-attr`
4. Large codes (424 errors): `arg-type`, `assignment`, `attr-defined`

### Phase 2: Global Flags (5 story points)

Enable strictness flags:

1. `check_untyped_defs = true`
2. `disallow_incomplete_defs = true`
3. `disallow_untyped_defs = true`
4. `warn_return_any = true`

### Phase 3: Strict Mode (3 story points)

Enable `strict = true` and remove all overrides.

## Alternatives Considered

### 1. Keep Current Configuration

**Rejected** - Type errors will accumulate, making future migration harder.

### 2. pyright Instead of mypy

**Rejected** - mypy is already configured and has better SQLAlchemy + Pydantic support.

### 3. Gradual Typing with pytype

**Rejected** - Less mature, less community support.

### 4. Per-File strict Mode

**Considered** - Could use `# mypy: strict` per file, but inconsistent experience.

## References

- [Mypy Strict Mode Documentation](https://mypy.readthedocs.io/en/stable/command_line.html#cmdoption-mypy-strict)
- [SQLAlchemy 2.0 ORM Mapped Column](https://docs.sqlalchemy.org/en/20/orm/mapped_attributes.html)
- [PEP 544 - Protocols](https://peps.python.org/pep-0544/)
- [PEP 589 - TypedDict](https://peps.python.org/pep-0589/)

## Related ADRs

- [ADR-002: Backend Framework (FastAPI)](adr-002-backend-framework.md)
- [ADR-003: Database Technology (PostgreSQL)](adr-003-database-technology.md)
