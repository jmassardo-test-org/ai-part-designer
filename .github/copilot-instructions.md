# AssemblematicAI Part Designer - Copilot Instructions

## Summary

This is an AI-powered 3D part generation platform with:
- **Backend:** Python 3.11+, FastAPI, SQLAlchemy (async), PostgreSQL, Redis, Celery
- **Frontend:** React 18, TypeScript, Vite, TailwindCSS, React Three Fiber
- **Testing:** pytest (backend), Vitest (frontend unit), Playwright (E2E)

---

## ⚠️ MANDATORY REQUIREMENTS

**You MUST follow these rules for EVERY code change. No exceptions.**

### 1. Tests Are Non-Negotiable

**ALWAYS create tests for any new code.** This is not optional.

- **Backend:** Write pytest tests in `backend/tests/` for every new function, class, endpoint, or service
- **Frontend:** Write Vitest tests in `frontend/src/**/*.test.ts(x)` for every new component, hook, or utility
- **E2E:** Add Playwright tests in `frontend/e2e/` for new user flows
- **Test naming:** `test_<method>_<scenario>_<expected_result>`
- **Coverage:** Maintain ≥80% coverage; critical paths require 100%

```python
# Example: If you create a new service method...
# backend/app/services/design_service.py
async def duplicate_design(self, design_id: UUID, user: User) -> Design:
    ...

# ...you MUST also create:
# backend/tests/services/test_design_service.py
async def test_duplicate_design_with_valid_id_returns_new_design(): ...
async def test_duplicate_design_with_invalid_id_raises_not_found(): ...
async def test_duplicate_design_without_permission_raises_forbidden(): ...
```

### 2. Type Safety Is Required

- **Python:** Use type hints for ALL function signatures, return types, and class attributes
- **TypeScript:** Use proper types; avoid `any` unless absolutely necessary
- **Pydantic:** Use Pydantic models for all API request/response schemas

```python
# ✅ Required
async def get_design_by_id(design_id: UUID, db: AsyncSession) -> Design | None:
    ...

# ❌ Unacceptable
async def get_design_by_id(design_id, db):
    ...
```

### 3. Documentation Is Required

- **Python:** Add docstrings to all public functions, classes, and modules
- **TypeScript:** Add JSDoc comments to exported functions and components
- **Complex logic:** Add inline comments explaining the "why"

```python
async def generate_cad_model(
    design: Design,
    parameters: dict[str, Any],
) -> CADResult:
    """Generate a CAD model from design parameters.
    
    Args:
        design: The design entity containing template reference.
        parameters: User-provided parameter values.
    
    Returns:
        CADResult containing the generated model and metadata.
    
    Raises:
        ValidationError: If parameters don't match template constraints.
        CADGenerationError: If CadQuery fails to generate the model.
    """
```

---

## Code Style & Conventions

### Python (Backend)

- Follow PEP 8 with Ruff enforcement
- Max line length: 100 characters
- Use 4-space indentation
- Async/await for all database and I/O operations
- Use dependency injection via FastAPI's `Depends()`

**Import order:**
```python
# 1. Standard library
from datetime import datetime
from uuid import UUID

# 2. Third-party
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

# 3. Local
from app.core.config import settings
from app.services.design import DesignService
```

**Naming:**
| Type | Convention | Example |
|------|------------|---------|
| Variables/Functions | snake_case | `user_id`, `get_design()` |
| Classes | PascalCase | `DesignService` |
| Constants | SCREAMING_SNAKE | `MAX_FILE_SIZE` |
| Private | underscore prefix | `_validate_input()` |

### TypeScript (Frontend)

- Use functional components with hooks
- Use TypeScript interfaces over types where possible
- Use React Query for server state
- Use Zod for runtime validation

**Naming:**
| Type | Convention | Example |
|------|------------|---------|
| Components | PascalCase | `DesignCard.tsx` |
| Hooks | camelCase with `use` | `useDesignQuery` |
| Utilities | camelCase | `formatDate.ts` |
| Types/Interfaces | PascalCase | `DesignResponse` |

---

## Project Structure

### Backend Files
```
backend/app/
├── api/routes/          # FastAPI route handlers
├── services/            # Business logic layer
├── repositories/        # Data access layer
├── models/              # SQLAlchemy ORM models
├── schemas/             # Pydantic request/response models
├── core/                # Config, security, dependencies
└── worker/              # Celery background tasks
```

### Frontend Files
```
frontend/src/
├── components/          # Reusable UI components
├── pages/               # Route page components
├── hooks/               # Custom React hooks
├── services/            # API client functions
├── types/               # TypeScript type definitions
└── utils/               # Helper functions
```

---

## Testing Checklist

Before completing ANY task, verify:

- [ ] Unit tests written for new functions/methods
- [ ] Edge cases covered (null, empty, invalid inputs)
- [ ] Error cases tested (exceptions, error responses)
- [ ] Mocks used appropriately for external dependencies
- [ ] Tests follow AAA pattern (Arrange, Act, Assert)
- [ ] All existing tests still pass
- [ ] Test file is in the correct location mirroring source structure

---

## API Design

- Use RESTful conventions
- Return appropriate HTTP status codes
- Use Pydantic models for request validation
- Include proper error responses with detail messages

```python
# Endpoint structure
@router.post("/", response_model=DesignResponse, status_code=status.HTTP_201_CREATED)
async def create_design(
    request: DesignCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DesignResponse:
    """Create a new design."""
```

---

## Error Handling

- Use custom exception classes
- Always provide meaningful error messages
- Log errors with appropriate context
- Never expose internal details in API responses

```python
# ✅ Good
raise DesignNotFoundError(f"Design with ID {design_id} not found")

# ❌ Bad
raise Exception("Not found")
```

---

## Security Requirements

- Never hardcode secrets or credentials
- Use environment variables via `app.core.config.settings`
- Validate and sanitize all user inputs
- Use parameterized queries (SQLAlchemy handles this)
- Apply proper authorization checks on all endpoints
- **NEVER use `/tmp`, `/var/tmp`, or hardcoded system temp directory paths** — use secure alternatives instead

### Temporary File Handling

**NEVER write to `/tmp` or any hardcoded system temporary directory.** This is a security and reliability requirement.

| Context | Use Instead |
|---------|-------------|
| Python code | `tempfile.mkdtemp()`, `tempfile.NamedTemporaryFile()` |
| pytest tests | `tmp_path` or `tmp_path_factory` fixtures |
| TypeScript/Node | `os.tmpdir()` with unique subdirs, or `fs.mkdtemp()` |
| Shell scripts | `mktemp -d` for unique directories |
| CI/CD pipelines | Runner workspace dirs or `$RUNNER_TEMP` |
| Build artifacts | Project-local dirs (`build/`, `dist/`, `.cache/`) |

---

## Before Submitting Code

Run these checks (or ensure they pass):

```bash
# Backend
cd backend
ruff check .
mypy .
pytest --cov=app --cov-report=term-missing

# Frontend
cd frontend
npm run lint
npm run test
npm run test:e2e
```

---

## Remember

1. **Tests are required** - Not "nice to have"
2. **Types are required** - No untyped code
3. **Docs are required** - Future you will thank you
4. **Follow existing patterns** - Consistency matters
5. **When in doubt, look at existing code** - Mirror the style

---

## GitHub PR & Issue Formatting

When creating or updating pull requests and issues via GitHub tools, **never use escaped `\n` sequences** in the body text. Always use actual newlines. Escaped `\n` renders as literal text on GitHub instead of line breaks.