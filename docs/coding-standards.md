# Coding Standards & Best Practices
# AI Part Designer

**Version:** 1.0  
**Date:** 2026-01-24  

---

## Table of Contents
1. [General Principles](#1-general-principles)
2. [Python Standards (Backend & Worker)](#2-python-standards)
3. [TypeScript Standards (Frontend)](#3-typescript-standards)
4. [API Design Standards](#4-api-design-standards)
5. [Database Standards](#5-database-standards)
6. [Testing Standards](#6-testing-standards)
7. [Git Workflow](#7-git-workflow)
8. [Code Review Guidelines](#8-code-review-guidelines)
9. [Security Standards](#9-security-standards)

---

## 1. General Principles

### Core Values
1. **Readability over cleverness** - Code is read more than written
2. **Explicit over implicit** - Be clear about intent
3. **Fail fast, fail loud** - Errors should be obvious
4. **DRY (Don't Repeat Yourself)** - But not at the expense of clarity
5. **YAGNI (You Aren't Gonna Need It)** - Don't over-engineer

### Code Quality Gates
All code must pass these checks before merge:
- ✅ Type checking passes (mypy/tsc)
- ✅ Linting passes (ruff/eslint)
- ✅ Unit tests pass with ≥80% coverage
- ✅ No security vulnerabilities (Snyk/Dependabot)
- ✅ Code review approved

---

## 2. Python Standards

### Style Guide
- Follow [PEP 8](https://peps.python.org/pep-0008/) with Ruff enforcement
- Maximum line length: 100 characters
- Use 4 spaces for indentation (no tabs)

### Type Hints
**Always use type hints** for function signatures and class attributes.

```python
# ✅ Good
def get_design_by_id(design_id: UUID, db: AsyncSession) -> Design | None:
    ...

class DesignService:
    def __init__(self, repository: DesignRepository) -> None:
        self._repository = repository

# ❌ Bad
def get_design_by_id(design_id, db):
    ...
```

### Imports Organization
```python
# 1. Standard library imports
from datetime import datetime
from typing import Optional, List
from uuid import UUID

# 2. Third-party imports
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

# 3. Local imports
from app.core.config import settings
from app.services.design import DesignService
```

### Naming Conventions
| Type | Convention | Example |
|------|------------|---------|
| Variables | snake_case | `user_id`, `design_count` |
| Functions | snake_case | `get_design_by_id()` |
| Classes | PascalCase | `DesignService` |
| Constants | SCREAMING_SNAKE | `MAX_FILE_SIZE` |
| Private | underscore prefix | `_validate_input()` |
| Module | snake_case | `design_service.py` |

### Function Design
```python
# ✅ Good - Single responsibility, clear purpose
async def validate_design_parameters(
    template: Template,
    parameters: dict[str, Any],
) -> ValidationResult:
    """Validate parameters against template constraints.
    
    Args:
        template: Template containing parameter definitions.
        parameters: User-provided parameter values.
    
    Returns:
        ValidationResult with errors if any.
        
    Raises:
        ValidationError: If parameters are fundamentally invalid.
    """
    errors: list[ParameterError] = []
    
    for name, definition in template.parameters.items():
        if name not in parameters and definition.required:
            errors.append(ParameterError(name, "Required parameter missing"))
            continue
        
        if error := _validate_parameter(definition, parameters.get(name)):
            errors.append(error)
    
    return ValidationResult(valid=len(errors) == 0, errors=errors)

# ❌ Bad - Does too many things
async def process_design(design_id, user_id, action, data, db, s3, redis):
    # 100+ lines doing validation, processing, storage, notification...
    pass
```

### Error Handling
```python
# ✅ Good - Specific exceptions, clear handling
from app.core.exceptions import DesignNotFoundError, PermissionDeniedError

async def get_design(design_id: UUID, user_id: UUID) -> Design:
    design = await self._repository.get_by_id(design_id)
    
    if design is None:
        raise DesignNotFoundError(design_id)
    
    if not self._has_access(design, user_id):
        raise PermissionDeniedError(f"User {user_id} cannot access design {design_id}")
    
    return design

# ❌ Bad - Generic exceptions, poor error messages
async def get_design(design_id, user_id):
    design = await self._repository.get_by_id(design_id)
    if not design:
        raise Exception("Not found")
    if design.user_id != user_id:
        raise Exception("Access denied")
    return design
```

### Async/Await Patterns
```python
# ✅ Good - Concurrent operations when possible
async def get_design_with_versions(design_id: UUID) -> DesignWithVersions:
    design, versions = await asyncio.gather(
        self._design_repo.get_by_id(design_id),
        self._version_repo.get_by_design_id(design_id),
    )
    return DesignWithVersions(design=design, versions=versions)

# ❌ Bad - Sequential when not necessary
async def get_design_with_versions(design_id: UUID) -> DesignWithVersions:
    design = await self._design_repo.get_by_id(design_id)
    versions = await self._version_repo.get_by_design_id(design_id)
    return DesignWithVersions(design=design, versions=versions)
```

### Pydantic Models
```python
from pydantic import BaseModel, Field, field_validator
from datetime import datetime
from uuid import UUID

class DesignCreate(BaseModel):
    """Request model for creating a new design."""
    
    name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Display name for the design"
    )
    description: str | None = Field(
        default=None,
        max_length=2000,
        description="Optional description"
    )
    template_id: UUID = Field(..., description="Template to base design on")
    parameters: dict[str, Any] = Field(
        default_factory=dict,
        description="Template parameters"
    )
    
    @field_validator("name")
    @classmethod
    def name_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Name cannot be empty or whitespace")
        return v.strip()
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "name": "My Custom Bracket",
                    "template_id": "123e4567-e89b-12d3-a456-426614174000",
                    "parameters": {"length": 100, "width": 50}
                }
            ]
        }
    }
```

---

## 3. TypeScript Standards

### Style Guide
- Follow ESLint + Prettier configuration
- Maximum line length: 100 characters
- Use 2 spaces for indentation
- Use single quotes for strings
- Always use semicolons

### Type Definitions
**Never use `any`** except in truly dynamic scenarios (and document why).

```typescript
// ✅ Good
interface Design {
  id: string;
  name: string;
  status: DesignStatus;
  metadata: DesignMetadata;
  createdAt: Date;
}

type DesignStatus = 'draft' | 'processing' | 'ready' | 'failed';

interface DesignMetadata {
  parameters: Record<string, unknown>;
  dimensions: Dimensions;
}

// ❌ Bad
interface Design {
  id: any;
  name: any;
  status: string;
  metadata: any;
  createdAt: any;
}
```

### React Component Patterns

#### Functional Components
```typescript
// ✅ Good - Typed props, clear structure
interface DesignCardProps {
  design: Design;
  onSelect?: (id: string) => void;
  isSelected?: boolean;
}

export function DesignCard({
  design,
  onSelect,
  isSelected = false,
}: DesignCardProps) {
  const handleClick = useCallback(() => {
    onSelect?.(design.id);
  }, [design.id, onSelect]);

  return (
    <div
      className={cn('design-card', isSelected && 'design-card--selected')}
      onClick={handleClick}
    >
      <img src={design.thumbnailUrl} alt={design.name} />
      <h3>{design.name}</h3>
      <StatusBadge status={design.status} />
    </div>
  );
}
```

#### Custom Hooks
```typescript
// ✅ Good - Encapsulated logic, clear return type
interface UseDesignsOptions {
  projectId?: string;
  status?: DesignStatus;
}

interface UseDesignsResult {
  designs: Design[];
  isLoading: boolean;
  error: Error | null;
  refetch: () => void;
}

export function useDesigns(options: UseDesignsOptions = {}): UseDesignsResult {
  const { projectId, status } = options;

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['designs', projectId, status],
    queryFn: () => designsApi.list({ projectId, status }),
  });

  return {
    designs: data?.data ?? [],
    isLoading,
    error: error ?? null,
    refetch,
  };
}
```

### State Management (Zustand)
```typescript
import { create } from 'zustand';
import { persist } from 'zustand/middleware';

interface DesignState {
  selectedDesignId: string | null;
  viewMode: 'grid' | 'list';
  
  // Actions
  selectDesign: (id: string | null) => void;
  setViewMode: (mode: 'grid' | 'list') => void;
}

export const useDesignStore = create<DesignState>()(
  persist(
    (set) => ({
      selectedDesignId: null,
      viewMode: 'grid',
      
      selectDesign: (id) => set({ selectedDesignId: id }),
      setViewMode: (mode) => set({ viewMode: mode }),
    }),
    {
      name: 'design-store',
      partialize: (state) => ({ viewMode: state.viewMode }),
    }
  )
);
```

### Import Aliases
```typescript
// Use path aliases for cleaner imports
// tsconfig.json: { "paths": { "@/*": ["./src/*"] } }

// ✅ Good
import { Button } from '@/components/ui/button';
import { useAuth } from '@/features/auth/useAuth';
import type { Design } from '@/types';

// ❌ Bad
import { Button } from '../../../components/ui/button';
import { useAuth } from '../../auth/useAuth';
```

---

## 4. API Design Standards

### URL Structure
```
GET    /api/v1/designs              # List designs
POST   /api/v1/designs              # Create design
GET    /api/v1/designs/{id}         # Get design
PATCH  /api/v1/designs/{id}         # Update design
DELETE /api/v1/designs/{id}         # Delete design
POST   /api/v1/designs/{id}/modify  # Action on design
```

### Response Format
```json
// Success - Single resource
{
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "name": "My Design",
  "status": "ready",
  "createdAt": "2024-01-24T12:00:00Z"
}

// Success - Collection
{
  "data": [...],
  "pagination": {
    "page": 1,
    "limit": 20,
    "total": 150,
    "totalPages": 8,
    "hasNext": true,
    "hasPrev": false
  }
}

// Error
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Request validation failed",
    "details": {
      "name": "Name is required"
    },
    "requestId": "req-123456"
  }
}
```

### HTTP Status Codes
| Code | Meaning | When to Use |
|------|---------|-------------|
| 200 | OK | Successful GET, PATCH |
| 201 | Created | Successful POST creating resource |
| 202 | Accepted | Async operation started |
| 204 | No Content | Successful DELETE |
| 400 | Bad Request | Validation error |
| 401 | Unauthorized | Missing/invalid token |
| 403 | Forbidden | Valid token, no permission |
| 404 | Not Found | Resource doesn't exist |
| 409 | Conflict | Resource conflict (duplicate email) |
| 422 | Unprocessable | Business rule violation |
| 429 | Too Many Requests | Rate limited |
| 500 | Internal Error | Server error (log, alert) |

---

## 5. Database Standards

### Naming Conventions
```sql
-- Tables: plural, snake_case
designs, design_versions, users

-- Columns: snake_case
created_at, user_id, is_active

-- Primary keys: id (UUID)
-- Foreign keys: <table>_id (singular)
user_id, design_id

-- Indexes: idx_<table>_<columns>
idx_designs_user_id, idx_designs_status_created

-- Constraints: <table>_<type>_<columns>
designs_pkey, designs_fk_user_id, designs_unique_slug
```

### Query Patterns
```python
# ✅ Good - Specific columns, proper filtering
async def get_user_designs(
    user_id: UUID,
    status: DesignStatus | None = None,
    limit: int = 20,
    offset: int = 0,
) -> list[Design]:
    query = (
        select(Design)
        .where(Design.user_id == user_id)
        .where(Design.deleted_at.is_(None))
        .order_by(Design.updated_at.desc())
        .limit(limit)
        .offset(offset)
    )
    
    if status:
        query = query.where(Design.status == status)
    
    result = await self._session.execute(query)
    return list(result.scalars().all())

# ❌ Bad - Select *, no pagination
async def get_user_designs(user_id):
    return await self._session.query(Design).filter(Design.user_id == user_id).all()
```

---

## 6. Testing Standards

### Test Organization
```
tests/
├── unit/                 # Fast, isolated tests
│   ├── services/
│   │   └── test_design_service.py
│   └── utils/
│       └── test_validation.py
├── integration/          # Database, external services
│   ├── api/
│   │   └── test_designs_api.py
│   └── repositories/
│       └── test_design_repository.py
├── e2e/                  # Full stack tests
│   └── test_design_flow.py
├── conftest.py           # Shared fixtures
└── factories.py          # Test data factories
```

### Test Structure (AAA Pattern)
```python
async def test_create_design_from_template_succeeds(
    design_service: DesignService,
    sample_template: Template,
    sample_user: User,
):
    # Arrange
    create_request = DesignCreate(
        name="Test Design",
        template_id=sample_template.id,
        parameters={"length": 100, "width": 50},
    )
    
    # Act
    result = await design_service.create_from_template(
        request=create_request,
        user=sample_user,
    )
    
    # Assert
    assert result.id is not None
    assert result.name == "Test Design"
    assert result.status == DesignStatus.PROCESSING
    assert result.source_type == SourceType.TEMPLATE
```

### Naming Conventions
```python
# test_<method>_<scenario>_<expected_result>
def test_get_design_with_valid_id_returns_design(): ...
def test_get_design_with_invalid_id_raises_not_found(): ...
def test_create_design_without_name_raises_validation_error(): ...
```

### Coverage Requirements
| Category | Minimum | Target |
|----------|---------|--------|
| Unit tests | 80% | 90% |
| Integration tests | 60% | 80% |
| Critical paths | 100% | 100% |

---

## 7. Git Workflow

### Branch Naming
```
feature/APD-123-add-design-export
bugfix/APD-456-fix-thumbnail-generation
hotfix/APD-789-security-patch
chore/update-dependencies
docs/add-api-documentation
```

### Commit Messages
Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <description>

[optional body]

[optional footer(s)]
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation only
- `style`: Formatting, no code change
- `refactor`: Code change, no feature/fix
- `perf`: Performance improvement
- `test`: Adding tests
- `chore`: Build, CI, dependencies

**Examples:**
```
feat(designs): add version history endpoint

- Add GET /designs/{id}/versions endpoint
- Include pagination support
- Add related tests

Closes #123

---

fix(auth): prevent token refresh after logout

The refresh token was still valid after logout, allowing
unauthorized access. Now invalidating tokens on logout.

Fixes #456

---

chore(deps): update fastapi to 0.109.0
```

### Pull Request Requirements
- [ ] Descriptive title with ticket reference
- [ ] Description of changes and why
- [ ] Screenshots for UI changes
- [ ] Tests added/updated
- [ ] Documentation updated
- [ ] Self-review completed
- [ ] At least 1 approval required

---

## 8. Code Review Guidelines

### Reviewer Checklist
- [ ] Code follows style guide
- [ ] Logic is correct and handles edge cases
- [ ] Error handling is appropriate
- [ ] Tests cover new functionality
- [ ] No security vulnerabilities
- [ ] No performance concerns
- [ ] Documentation is adequate
- [ ] Changes are backwards compatible (or noted)

### Review Comments
```
# ✅ Good - Specific, actionable, respectful
"Consider using `asyncio.gather` here for concurrent DB calls - 
it would reduce latency from ~200ms to ~100ms in this endpoint."

# ❌ Bad - Vague, unconstructive
"This is wrong."
"I don't like this approach."
```

---

## 9. Security Standards

### Input Validation
- **Always validate** user input at API boundary
- Use Pydantic models for request validation
- Sanitize input for SQL, HTML, filesystem operations

### Authentication & Authorization
- Verify JWT on every protected endpoint
- Check resource ownership before operations
- Use rate limiting on sensitive endpoints

### Secrets Management
- **Never** commit secrets to git
- Use environment variables
- Rotate secrets regularly
- Use AWS Secrets Manager in production

### OWASP Top 10 Awareness
1. **Injection**: Parameterized queries only
2. **Broken Auth**: Proper session management
3. **Sensitive Data**: Encrypt at rest and in transit
4. **XXE**: Disable external entities
5. **Broken Access Control**: Check permissions
6. **Security Misconfiguration**: Secure defaults
7. **XSS**: Escape output, CSP headers
8. **Insecure Deserialization**: Validate types
9. **Vulnerable Components**: Keep updated
10. **Insufficient Logging**: Log security events

---

*End of Document*
