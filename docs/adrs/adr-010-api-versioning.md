# ADR-010: API Versioning Strategy

## Status
Proposed

## Context
We need to define how we version our API to:
- Support backward compatibility as we evolve
- Allow deprecation of old endpoints
- Provide clear communication to API consumers
- Enable parallel development of new versions
- Support future public API access for Enterprise tier

## Decision
We will use **URL path versioning** with the format `/api/v{N}/...`.

Versioning strategy:
- **Major versions in URL**: `/api/v1/`, `/api/v2/`
- **Minor/patch changes**: Backward-compatible, no version bump
- **Breaking changes**: New major version
- **Deprecation period**: 6 months minimum before removal
- **Support window**: Current version + 1 previous version

## Consequences

### Positive
- **Clear and visible**: Version obvious in URL
- **Easy routing**: Simple to route different versions
- **Cache-friendly**: Different URLs for different versions
- **Client clarity**: Developers know exactly which version they use

### Negative
- **URL pollution**: Version in every URL
- **Code duplication**: May need parallel endpoint implementations
- **Documentation overhead**: Multiple versions to document

### Mitigation
- Use shared logic with version-specific adapters
- Automate OpenAPI doc generation per version
- Clear deprecation notices in responses

## Options Considered

| Option | Pros | Cons | Score |
|--------|------|------|-------|
| **URL Path** (/api/v1/) | Clear, cacheable, easy routing | URL pollution | ⭐⭐⭐⭐⭐ |
| Header (Accept-Version) | Clean URLs | Hidden, harder to test | ⭐⭐⭐ |
| Query param (?version=1) | Flexible | Can be forgotten, caching issues | ⭐⭐ |
| Content negotiation | RESTful | Complex, confusing | ⭐⭐ |
| No versioning | Simple | Breaking changes break clients | ⭐ |

## Technical Details

### URL Structure
```
https://api.aipartdesigner.com/v1/designs
https://api.aipartdesigner.com/v1/designs/{id}
https://api.aipartdesigner.com/v1/designs/{id}/export
https://api.aipartdesigner.com/v1/templates
https://api.aipartdesigner.com/v1/jobs
https://api.aipartdesigner.com/v1/users/me
```

### FastAPI Implementation
```python
# app/api/router.py
from fastapi import APIRouter

# Version 1 router
v1_router = APIRouter(prefix="/api/v1")

# Import version-specific routes
from app.api.v1 import auth, designs, templates, jobs, users

v1_router.include_router(auth.router, prefix="/auth", tags=["auth"])
v1_router.include_router(designs.router, prefix="/designs", tags=["designs"])
v1_router.include_router(templates.router, prefix="/templates", tags=["templates"])
v1_router.include_router(jobs.router, prefix="/jobs", tags=["jobs"])
v1_router.include_router(users.router, prefix="/users", tags=["users"])

# Future: Version 2 router
# v2_router = APIRouter(prefix="/api/v2")
# ...

# Main app
app = FastAPI(
    title="AI Part Designer API",
    version="1.0.0",
    docs_url="/api/docs",
    openapi_url="/api/openapi.json"
)

app.include_router(v1_router)
# app.include_router(v2_router)  # When v2 is ready
```

### Project Structure
```
backend/
├── app/
│   ├── api/
│   │   ├── v1/
│   │   │   ├── __init__.py
│   │   │   ├── auth.py
│   │   │   ├── designs.py
│   │   │   ├── templates.py
│   │   │   ├── jobs.py
│   │   │   ├── users.py
│   │   │   └── schemas/
│   │   │       ├── design.py
│   │   │       ├── template.py
│   │   │       └── job.py
│   │   ├── v2/  # Future version
│   │   │   └── ...
│   │   └── deps.py  # Shared dependencies
│   ├── services/  # Shared business logic
│   └── ...
```

### Versioned Schemas
```python
# app/api/v1/schemas/design.py
from pydantic import BaseModel
from datetime import datetime

class DesignCreateV1(BaseModel):
    """V1 design creation schema."""
    description: str
    dimensions: dict | None = None
    template_name: str | None = None

class DesignResponseV1(BaseModel):
    """V1 design response schema."""
    id: str
    name: str
    description: str | None
    status: str
    preview_url: str | None
    created_at: datetime
    
    class Config:
        from_attributes = True

# Future: V2 might add new fields or change structure
# app/api/v2/schemas/design.py
class DesignResponseV2(DesignResponseV1):
    """V2 adds more fields."""
    geometry_metadata: dict | None = None
    optimization_score: float | None = None
```

### Deprecation Headers
```python
# app/middleware/deprecation.py
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

DEPRECATED_VERSIONS = {
    "v1": {
        "deprecated": False,
        "sunset": None,
        "message": None
    },
    # When deprecating v1:
    # "v1": {
    #     "deprecated": True,
    #     "sunset": "2027-01-01",
    #     "message": "Please migrate to v2. See docs for migration guide."
    # }
}

class DeprecationMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        
        # Extract version from path
        path = request.url.path
        if "/api/v" in path:
            version = path.split("/api/")[1].split("/")[0]  # e.g., "v1"
            
            if version in DEPRECATED_VERSIONS:
                info = DEPRECATED_VERSIONS[version]
                if info["deprecated"]:
                    response.headers["Deprecation"] = "true"
                    response.headers["Sunset"] = info["sunset"]
                    response.headers["X-Deprecation-Notice"] = info["message"]
        
        return response
```

### OpenAPI Documentation per Version
```python
# app/main.py
from fastapi import FastAPI
from fastapi.openapi.docs import get_swagger_ui_html

app = FastAPI()

# Separate OpenAPI schemas per version
@app.get("/api/v1/openapi.json", include_in_schema=False)
async def get_v1_openapi():
    return get_openapi_for_version("v1")

@app.get("/api/v1/docs", include_in_schema=False)
async def get_v1_docs():
    return get_swagger_ui_html(
        openapi_url="/api/v1/openapi.json",
        title="AI Part Designer API v1"
    )
```

### Breaking vs Non-Breaking Changes

#### Non-Breaking (No version bump)
- Adding new optional fields to responses
- Adding new endpoints
- Adding new optional query parameters
- Expanding enum values (if clients handle unknown)
- Bug fixes that don't change contract

#### Breaking (Requires new version)
- Removing fields from responses
- Changing field types
- Renaming fields
- Changing endpoint paths
- Changing required/optional status of fields
- Removing endpoints
- Changing authentication mechanism

### Migration Guide Template
```markdown
# Migration Guide: v1 to v2

## Timeline
- v2 Released: January 2027
- v1 Deprecated: April 2027
- v1 Sunset: October 2027

## Breaking Changes

### 1. Design Response Structure
**v1:**
```json
{
  "id": "uuid",
  "preview_url": "/path/to/preview"
}
```

**v2:**
```json
{
  "id": "uuid",
  "previews": {
    "thumbnail": "/path/to/thumb",
    "full": "/path/to/full"
  }
}
```

### 2. Authentication
v2 requires API keys for all requests. See [API Key Setup](#).

## Migration Steps
1. Update API base URL from `/api/v1` to `/api/v2`
2. Update response parsing for changed structures
3. Generate and use API keys
4. Test thoroughly in staging
```

### Rate Limiting per Version
```python
# Different rate limits for versions
RATE_LIMITS = {
    "v1": {
        "default": "100/minute",
        "designs": "30/minute"
    },
    "v2": {
        "default": "200/minute",  # Higher for newer version
        "designs": "60/minute"
    }
}
```

## References
- [API Versioning Best Practices](https://www.postman.com/api-platform/api-versioning/)
- [Stripe API Versioning](https://stripe.com/docs/api/versioning)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
