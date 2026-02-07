# Strict Mypy Migration - Technical Architecture Specification

**Issue:** #278 - Enable strict mypy type checking incrementally  
**Status:** Architecture Complete  
**Date:** 2026-02-06  
**Author:** Architecture & Security Agent

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Architecture Patterns](#2-architecture-patterns)
3. [Type Safety Patterns](#3-type-safety-patterns)
4. [CI/CD Integration](#4-cicd-integration)
5. [Security Considerations](#5-security-considerations)
6. [Technical Specifications](#6-technical-specifications)
7. [Migration Patterns by Error Type](#7-migration-patterns-by-error-type)
8. [Non-Functional Requirements](#8-non-functional-requirements)
9. [ADR Reference](#9-adr-reference)

---

## 1. Executive Summary

This specification defines the technical architecture for migrating to strict mypy type checking. The codebase already uses modern SQLAlchemy 2.0 patterns (`Mapped[]`, `mapped_column`) consistently, which significantly reduces the migration effort.

### Key Findings

| Aspect | Current State | Target State |
|--------|--------------|--------------|
| SQLAlchemy Pattern | ✅ Already using `Mapped[]` | ✅ Maintain |
| Pydantic Version | ✅ Pydantic v2 | ✅ Maintain |
| TypeVar Usage | ⚠️ Needs Protocol bounds | Use Protocol types |
| Optional Handling | ⚠️ Inconsistent guards | Type narrowing with is None |
| Result Type Access | ⚠️ Attribute access issues | Proper CursorResult typing |

### Architecture Decision

**Use SQLAlchemy 2.0 Native Typing** - The codebase already follows this pattern. Focus on:
1. Adding Protocol bounds to generic TypeVars
2. Fixing type narrowing in optional cases
3. Correcting SQLAlchemy expression types
4. Adding missing type stubs for third-party libraries

---

## 2. Architecture Patterns

### 2.1 Repository Layer Type Pattern

**Problem:** `BaseRepository[ModelType]` TypeVar doesn't properly express that models have `.id`, `.deleted_at` attributes.

**Current Pattern (Causes attr-defined errors):**
```python
ModelType = TypeVar("ModelType", bound=Base)

class BaseRepository(Generic[ModelType]):
    model: type[ModelType]
    
    async def get_by_id(self, id: UUID) -> ModelType | None:
        query = select(self.model).where(self.model.id == id)  # Error: has no attribute "id"
```

**Target Pattern:**
```python
from typing import TYPE_CHECKING, Protocol, TypeVar, runtime_checkable

@runtime_checkable
class HasIdentity(Protocol):
    """Protocol for models with standard identity and soft-delete columns."""
    id: Mapped[UUID]
    
@runtime_checkable
class HasSoftDelete(Protocol):
    """Protocol for models with soft-delete support."""
    deleted_at: Mapped[datetime | None]

@runtime_checkable
class HasTimestamps(Protocol):
    """Protocol for models with timestamp columns."""
    created_at: Mapped[datetime]
    updated_at: Mapped[datetime]

# Combined protocol for full model requirements
class StandardModel(HasIdentity, HasSoftDelete, HasTimestamps, Protocol):
    """Protocol for standard ORM models with all mixins."""
    pass

# Bounded TypeVar
ModelType = TypeVar("ModelType", bound=Base)

class BaseRepository(Generic[ModelType]):
    """Base repository requiring StandardModel compliance."""
    model: type[ModelType]
    
    async def get_by_id(
        self,
        id: UUID,
        *,
        include_deleted: bool = False,
    ) -> ModelType | None:
        # Cast to access typed attributes on class
        model_cls = cast(type[StandardModel], self.model)
        query = select(self.model).where(model_cls.id == id)
        
        if not include_deleted and hasattr(self.model, "deleted_at"):
            query = query.where(model_cls.deleted_at.is_(None))
        
        result = await self.session.execute(query)
        return result.scalar_one_or_none()
```

### 2.2 SQLAlchemy Query Expression Pattern

**Problem:** SQLAlchemy column expressions return `ColumnElement[bool]`, not Python `bool`.

**Current Pattern (Causes arg-type errors):**
```python
# Incorrect - produces bool, not ColumnElement[bool]
conditions: list[ColumnElement[bool]] = []
conditions.append(User.is_active == True)  # arg-type error
```

**Target Pattern:**
```python
from sqlalchemy import ColumnElement
from sqlalchemy.sql.expression import BinaryExpression

# Option 1: Explicit typing
conditions: list[ColumnElement[bool]] = []
condition: ColumnElement[bool] = User.is_active == True  # Explicit annotation
conditions.append(condition)

# Option 2: Use comparison operators correctly
conditions: list[ColumnElement[bool]] = []
conditions.append(User.is_active.is_(True))  # Returns ColumnElement[bool]

# Option 3: Type assertion when needed
from typing import cast
conditions.append(cast(ColumnElement[bool], User.is_active == True))
```

### 2.3 Relationship Type Pattern

**Problem:** SQLAlchemy relationships are dynamically typed.

**Current Pattern:**
```python
class User(Base):
    projects: Mapped[list["Project"]] = relationship(back_populates="owner")
```

**Target Pattern (Already Correct):**
```python
from typing import TYPE_CHECKING
from sqlalchemy.orm import Mapped, relationship

if TYPE_CHECKING:
    from app.models.project import Project

class User(Base):
    projects: Mapped[list["Project"]] = relationship(
        back_populates="owner",
        default_factory=list,
    )
```

### 2.4 Pydantic to SQLAlchemy Conversion Pattern

**Problem:** API routes return ORM models instead of Pydantic schemas.

**Current Pattern (Causes return-value errors):**
```python
@router.get("/{id}", response_model=DesignResponse)
async def get_design(id: UUID) -> DesignResponse:
    design = await service.get_design(id)
    return design  # Error: returns Design, expected DesignResponse
```

**Target Pattern:**
```python
@router.get("/{id}", response_model=DesignResponse)
async def get_design(id: UUID) -> DesignResponse:
    design = await service.get_design(id)
    if design is None:
        raise HTTPException(status_code=404)
    return DesignResponse.model_validate(design)

# OR use FastAPI's automatic conversion with explicit return annotation
@router.get("/{id}")
async def get_design(id: UUID) -> DesignResponse:
    design = await service.get_design(id)
    if design is None:
        raise HTTPException(status_code=404)
    return DesignResponse.model_validate(design)
```

---

## 3. Type Safety Patterns

### 3.1 None Handling (union-attr fixes)

**Pattern: Early Return Guard**
```python
# Before
async def process_design(design_id: UUID) -> str:
    design = await repo.get_by_id(design_id)
    return design.name  # Error: design may be None

# After
async def process_design(design_id: UUID) -> str:
    design = await repo.get_by_id(design_id)
    if design is None:
        raise DesignNotFoundError(design_id)
    return design.name  # Narrowed to Design
```

**Pattern: Assertion for Invariants**
```python
# When you're certain the value exists (validated upstream)
async def internal_process(design: Design) -> str:
    project = design.project
    assert project is not None, "Design must have project"
    return project.name
```

**Pattern: Default Values**
```python
# When None is acceptable
def get_description(design: Design) -> str:
    return design.description or "No description provided"
```

### 3.2 Type Narrowing Patterns

**Pattern: isinstance for Union Types**
```python
from typing import Union

def process_result(result: str | dict[str, Any]) -> str:
    if isinstance(result, str):
        return result
    return json.dumps(result)
```

**Pattern: TypeGuard for Complex Checks**
```python
from typing import TypeGuard

def is_valid_design(obj: object) -> TypeGuard[Design]:
    return isinstance(obj, Design) and obj.id is not None

def process(obj: object) -> UUID:
    if is_valid_design(obj):
        return obj.id  # Narrowed to Design
    raise ValueError("Invalid design")
```

### 3.3 Generic Type Patterns

**Pattern: Bounded TypeVar**
```python
from typing import TypeVar

T = TypeVar("T", bound=BaseModel)

def serialize_many(items: Sequence[T]) -> list[dict[str, Any]]:
    return [item.model_dump() for item in items]
```

**Pattern: Constrained TypeVar**
```python
from typing import TypeVar

NumericT = TypeVar("NumericT", int, float)

def calculate_area(width: NumericT, height: NumericT) -> NumericT:
    return width * height
```

### 3.4 Callable and Higher-Order Function Patterns

**Pattern: Protocol for Callables**
```python
from typing import Protocol

class AsyncHandler(Protocol):
    async def __call__(self, request: Request) -> Response: ...

async def with_logging(handler: AsyncHandler) -> AsyncHandler:
    async def wrapper(request: Request) -> Response:
        log.info(f"Handling {request.method} {request.path}")
        return await handler(request)
    return wrapper
```

---

## 4. CI/CD Integration

### 4.1 Current CI Configuration

The CI pipeline in `.github/workflows/ci.yml` already runs mypy:

```yaml
backend-typecheck:
  name: Backend Type Check
  runs-on: ubuntu-latest
  steps:
    - name: Run MyPy
      working-directory: backend
      run: uv run mypy app --show-error-codes
```

### 4.2 Migration CI Strategy

**Phase 1-2: Incremental Enforcement**

During migration, add a shadow check that runs strict mypy without failing the build:

```yaml
backend-typecheck:
  name: Backend Type Check
  runs-on: ubuntu-latest
  steps:
    - name: Run MyPy (current config)
      working-directory: backend
      run: uv run mypy app --show-error-codes

    # Shadow check for tracking progress - does not fail build
    - name: Run MyPy Strict (progress check)
      working-directory: backend
      run: |
        uv run mypy app --strict 2>&1 | tee /tmp/mypy-strict.log || true
        echo "Strict mode errors:"
        grep -c "error:" /tmp/mypy-strict.log || echo "0"
      continue-on-error: true
```

**Phase 3: Strict Enforcement**

Final configuration after migration complete:

```yaml
backend-typecheck:
  name: Backend Type Check (Strict)
  runs-on: ubuntu-latest
  steps:
    - name: Run MyPy Strict
      working-directory: backend
      run: uv run mypy app --strict --show-error-codes
```

### 4.3 Pre-commit Hook

Add to `.pre-commit-config.yaml`:

```yaml
repos:
  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.8.0
    hooks:
      - id: mypy
        args: [--config-file=backend/pyproject.toml]
        additional_dependencies:
          - pydantic>=2.5.0
          - types-redis>=4.6.0
          - types-passlib>=1.7.7
          - boto3-stubs>=1.34.0
```

### 4.4 pyproject.toml Target Configuration

```toml
[tool.mypy]
python_version = "3.12"
strict = true
plugins = ["pydantic.mypy"]

# Allow untyped calls to third-party libraries without stubs
warn_return_any = true
warn_unused_ignores = true
no_implicit_optional = true
strict_equality = true
disallow_untyped_defs = true
disallow_incomplete_defs = true
check_untyped_defs = true

# Pydantic plugin settings
[tool.mypy.plugins.pydantic]
init_forbid_extra = true
init_typed = true
warn_required_dynamic_aliases = true

# Third-party libraries without type stubs
[[tool.mypy.overrides]]
module = [
    "fitz.*",
    "cairosvg.*",
    "ezdxf.*",
    "aiosmtplib.*",
    "pdf2image.*",
    "anthropic.*",
    "stl.*",
    "numpy.*",
    "aioboto3.*",
    "botocore.*",
    "build123d.*",
    "OCP.*",
    "cadquery.*",
    "celery.*",
    "stripe.*",
    "structlog.*",
    "prometheus_client.*",
    "prometheus_fastapi_instrumentator.*",
]
ignore_missing_imports = true
```

---

## 5. Security Considerations

### 5.1 Type Safety and Security

Strict typing provides security benefits:

| Security Benefit | How Typing Helps |
|-----------------|------------------|
| **Input Validation** | Pydantic + mypy ensures untrusted input is validated |
| **SQL Injection** | Typed SQLAlchemy prevents raw string interpolation |
| **Null Pointer** | Optional handling prevents None-related crashes |
| **Type Confusion** | Explicit types prevent type confusion vulnerabilities |

### 5.2 Ignore Comment Policy

**PROHIBITED without security review:**
```python
# type: ignore[arg-type]  # DO NOT USE without documented reason
```

**REQUIRED format for any type suppression:**
```python
# type: ignore[attr-defined]  # SQLAlchemy dynamic backref - see ADR-XXX
```

### 5.3 Security-Critical Modules

The following modules require 100% type coverage with NO suppressions:

| Module | Reason |
|--------|--------|
| `app/core/security.py` | Authentication/authorization |
| `app/core/dependencies.py` | Request validation |
| `app/api/v1/auth.py` | Login/registration |
| `app/services/payment_service.py` | Financial transactions |
| `app/middleware/rate_limit.py` | Rate limiting |

---

## 6. Technical Specifications

### 6.1 Type Stub Requirements

**Already Installed (verify in pyproject.toml):**
- `types-redis>=4.6.0`
- `types-passlib>=1.7.7`
- `boto3-stubs>=1.34.0`

**To Add if Not Present:**
```toml
[project.optional-dependencies]
dev = [
    # ... existing ...
    "types-PyYAML>=6.0.0",
    "types-python-jose>=3.3.0",
]
```

### 6.2 Protocol Definitions Module

Create `app/types/protocols.py`:

```python
"""
Type protocols for generic typing patterns.

These protocols enable proper type checking for generic
repository and service patterns.
"""

from datetime import datetime
from typing import Protocol, runtime_checkable
from uuid import UUID

from sqlalchemy.orm import Mapped


@runtime_checkable
class HasIdentity(Protocol):
    """Protocol for entities with UUID primary key."""
    
    id: Mapped[UUID]


@runtime_checkable
class HasTimestamps(Protocol):
    """Protocol for entities with audit timestamps."""
    
    created_at: Mapped[datetime]
    updated_at: Mapped[datetime]


@runtime_checkable
class HasSoftDelete(Protocol):
    """Protocol for entities with soft-delete support."""
    
    deleted_at: Mapped[datetime | None]
    
    @property
    def is_deleted(self) -> bool: ...


@runtime_checkable
class StandardEntity(HasIdentity, HasTimestamps, HasSoftDelete, Protocol):
    """Combined protocol for standard entity with all mixins."""
    pass


class Identifiable(Protocol):
    """Protocol for any object with an id attribute."""
    
    @property
    def id(self) -> UUID: ...


class Nameable(Protocol):
    """Protocol for objects with name/display attributes."""
    
    @property
    def name(self) -> str: ...


class Ownable(Protocol):
    """Protocol for objects with user ownership."""
    
    @property
    def user_id(self) -> UUID: ...
```

### 6.3 Type Aliases Module

Create `app/types/aliases.py`:

```python
"""
Common type aliases used throughout the application.
"""

from typing import Any, TypeAlias
from uuid import UUID

from sqlalchemy import ColumnElement
from sqlalchemy.ext.asyncio import AsyncSession

# Database types
AsyncDB: TypeAlias = AsyncSession
SQLFilter: TypeAlias = ColumnElement[bool]
SQLFilters: TypeAlias = list[ColumnElement[bool]]

# JSON types
JSONPrimitive: TypeAlias = str | int | float | bool | None
JSONValue: TypeAlias = JSONPrimitive | list["JSONValue"] | dict[str, "JSONValue"]
JSONDict: TypeAlias = dict[str, Any]
JSONList: TypeAlias = list[Any]

# ID types
EntityID: TypeAlias = UUID
UserID: TypeAlias = UUID
ProjectID: TypeAlias = UUID
DesignID: TypeAlias = UUID

# Pagination
PageNumber: TypeAlias = int
PageSize: TypeAlias = int
Offset: TypeAlias = int
Limit: TypeAlias = int

# CAD types  
Coordinate: TypeAlias = tuple[float, float, float]
BoundingBoxTuple: TypeAlias = tuple[Coordinate, Coordinate]
```

### 6.4 Typing Constants

Add to `app/core/constants.py`:

```python
"""
Application constants with proper typing.
"""

from typing import Final

# Pagination limits
DEFAULT_PAGE_SIZE: Final[int] = 20
MAX_PAGE_SIZE: Final[int] = 100

# String length limits
MAX_NAME_LENGTH: Final[int] = 255
MAX_DESCRIPTION_LENGTH: Final[int] = 2000

# File size limits (bytes)
MAX_UPLOAD_SIZE: Final[int] = 50 * 1024 * 1024  # 50MB
MAX_CAD_FILE_SIZE: Final[int] = 100 * 1024 * 1024  # 100MB
```

---

## 7. Migration Patterns by Error Type

### 7.1 attr-defined (222 errors)

**Pattern A: SQLAlchemy Relationship Attributes**
```python
# Before - accessing dynamic relationship
user.projects  # Error: "User" has no attribute "projects"

# After - ensure relationship is declared with Mapped type
class User(Base):
    projects: Mapped[list["Project"]] = relationship(...)
```

**Pattern B: TypeVar Class Attribute Access**
```python
# Before
query = select(self.model).where(self.model.id == id)

# After - use cast
from typing import cast
model_cls = cast(type[StandardEntity], self.model)
query = select(self.model).where(model_cls.id == id)
```

**Pattern C: Dynamic Attributes (use documented ignore)**
```python
# When attribute truly is dynamic (e.g., SQLAlchemy backref)
user.owned_designs  # type: ignore[attr-defined]  # SQLAlchemy backref
```

### 7.2 assignment (111 errors)

**Pattern A: Column Type Mismatch**
```python
# Before
component.name = request.name  # Error: str != Column[str]

# After - SQLAlchemy 2.0 Mapped[] handles this correctly
# If using old pattern, update model definition:
name: Mapped[str] = mapped_column(String(255))
```

**Pattern B: Expression Assignment**
```python
# Before
total: Column[int] = func.count(Design.id)

# After
from sqlalchemy import ColumnElement
total: ColumnElement[int] = func.count(Design.id)
```

### 7.3 arg-type (91 errors)

**Pattern A: UUID vs String**
```python
# Before
get_design(str(design_id))  # Error: expected UUID

# After
get_design(design_id)  # Pass UUID directly

# OR if API receives string
from uuid import UUID
get_design(UUID(design_id_str))
```

**Pattern B: SQLAlchemy Expression Types**
```python
# Before
conditions.append(Model.active == True)  # Error: bool != ColumnElement[bool]

# After
condition: ColumnElement[bool] = Model.active == True
conditions.append(condition)
```

### 7.4 return-value (22 errors)

**Pattern: ORM to Pydantic Conversion**
```python
# Before
async def get_user(id: UUID) -> UserResponse:
    return await repo.get_by_id(id)  # Returns User, not UserResponse

# After
async def get_user(id: UUID) -> UserResponse:
    user = await repo.get_by_id(id)
    if user is None:
        raise NotFoundError("User", id)
    return UserResponse.model_validate(user)
```

### 7.5 union-attr (46 errors)

**Pattern: Guard Clause**
```python
# Before
design.project.name  # Error: project may be None

# After
if design.project is None:
    raise InvalidStateError("Design has no project")
name = design.project.name
```

### 7.6 call-arg (39 errors)

**Pattern: Check Function Signature**
```python
# Before
func(a, b, extra_arg=True)  # Error: unexpected keyword argument

# After - verify the function signature and fix the call
func(a, b)  # Remove invalid argument
```

### 7.7 operator (24 errors)

**Pattern: Type-Safe Operations**
```python
# Before
if value > threshold:  # Error: unsupported operand types

# After
if value is not None and value > threshold:
    ...
```

### 7.8 index (20 errors)

**Pattern: Safe Dict Access**
```python
# Before
value = data["key"]  # Error if data is not Dict[str, ...]

# After
from typing import TypedDict

class ConfigData(TypedDict):
    key: str
    
def process(data: ConfigData) -> str:
    return data["key"]  # Now type-safe
```

---

## 8. Non-Functional Requirements

### 8.1 Performance

| Metric | Requirement | Measurement |
|--------|-------------|-------------|
| Mypy check time | < 60 seconds | CI job duration |
| Incremental mypy | < 10 seconds | Local development |
| No runtime overhead | 0% | Types are compile-time only |

### 8.2 Maintainability

| Requirement | Implementation |
|-------------|----------------|
| All ignores documented | Inline comment with reason |
| Ignore format | `# type: ignore[code]  # reason` |
| Protocol documentation | Docstrings on all Protocol classes |
| TypeAlias usage | Prefer aliases for complex types |

### 8.3 Testing

| Requirement | Implementation |
|-------------|----------------|
| Type stub tests | Verify stubs match runtime behavior |
| Protocol compliance | Test models implement protocols |
| Edge case coverage | Test Optional handling paths |

---

## 9. ADR Reference

This architecture aligns with:

| ADR | Relevance |
|-----|-----------|
| [ADR-002](../adrs/adr-002-backend-framework.md) | FastAPI + Pydantic v2 |
| [ADR-003](../adrs/adr-003-database-technology.md) | SQLAlchemy 2.0 with async |

Create new ADR for this migration:

### ADR-017: Type Safety Strategy

**Status:** Proposed

**Context:** Need to enable strict mypy across codebase.

**Decision:** 
- Use SQLAlchemy 2.0 native `Mapped[]` typing (already in place)
- Use Protocol types for generic repository patterns
- Use TypedDict for JSON configuration structures
- Require documented rationale for all `# type: ignore`

**Consequences:**
- Better IDE support and autocomplete
- Catch type errors at build time
- Some third-party library friction (resolve with stubs or ignores)

---

## Appendix A: Quick Reference

### File Organization

```
backend/app/
├── types/              # NEW - Type definitions
│   ├── __init__.py
│   ├── protocols.py    # Protocol definitions
│   └── aliases.py      # Type aliases
├── models/
│   ├── base.py         # Base + mixins (already typed)
│   └── *.py           # Models with Mapped[]
├── schemas/
│   └── *.py           # Pydantic models
├── repositories/
│   └── base.py        # Use Protocol-bounded TypeVar
└── services/
    └── *.py           # Service layer
```

### Import Pattern

```python
# Standard library
from typing import TYPE_CHECKING, Any, Protocol, TypeVar, cast
from uuid import UUID

# Third-party
from sqlalchemy import ColumnElement
from sqlalchemy.orm import Mapped

# Local
from app.types.protocols import StandardEntity
from app.types.aliases import SQLFilter, JSONDict

if TYPE_CHECKING:
    from app.models import User
```

---

## Handoff Ready

This technical architecture is ready for the Development Agent to implement:

- [x] SQLAlchemy typing patterns documented
- [x] Type safety patterns with examples
- [x] CI/CD integration strategy
- [x] Security considerations addressed
- [x] Migration patterns by error type
- [x] NFRs specified with measurable targets
- [x] New module structure defined (`app/types/`)
- [x] Target pyproject.toml configuration provided
