# ADR-002: Backend Language and Framework Selection

## Status
Proposed

## Context
We need to select a backend language and framework for the AI Part Designer API. Requirements include:
- RESTful API with potential for GraphQL in the future
- Integration with Python-based CAD libraries (CadQuery, OpenCASCADE)
- Integration with AI/LLM APIs
- Job queue processing for async operations
- WebSocket support for real-time updates
- Strong typing for maintainability
- Good performance for file processing

## Decision
We will use **Python 3.11+** with **FastAPI** as our primary backend framework.

Supporting technology choices:
- **ASGI Server**: Uvicorn with Gunicorn
- **ORM**: SQLAlchemy 2.0 with async support
- **Migrations**: Alembic
- **Validation**: Pydantic v2
- **Task Queue**: Celery with Redis
- **WebSockets**: FastAPI native + Socket.IO (for complex real-time)
- **Testing**: pytest with pytest-asyncio

## Consequences

### Positive
- **Native CAD library support**: CadQuery, pythonocc (OpenCASCADE) are Python-native
- **AI/ML ecosystem**: Direct integration with LangChain, OpenAI SDK, transformers
- **FastAPI performance**: Comparable to Node.js/Go for I/O bound tasks
- **Automatic OpenAPI**: Built-in Swagger/ReDoc documentation
- **Type hints**: Pydantic provides runtime validation
- **Async support**: Native async/await for concurrent operations
- **Developer productivity**: Python's readability and ecosystem

### Negative
- **CPU-bound performance**: Python GIL limits true parallelism (mitigated by multiprocessing workers)
- **Deployment complexity**: Need proper ASGI server setup
- **Memory usage**: Higher than Go/Rust for same workload

### Neutral
- Team will need to maintain Python version consistency
- Some libraries may have C extension dependencies (OpenCASCADE)

## Options Considered

| Option | Pros | Cons | Score |
|--------|------|------|-------|
| **Python/FastAPI** | CAD libraries native, AI/ML ecosystem, async | GIL for CPU tasks | ⭐⭐⭐⭐⭐ |
| Node.js/NestJS | Fast I/O, TypeScript, good ecosystem | CAD libraries need bindings | ⭐⭐⭐⭐ |
| Go/Gin | Excellent performance, simple deployment | Limited CAD ecosystem | ⭐⭐⭐ |
| Rust/Axum | Best performance, memory safety | Steep learning curve, small ecosystem | ⭐⭐ |
| Python/Django | Batteries included, mature | Slower than FastAPI, monolithic | ⭐⭐⭐ |

## Technical Details

### Project Structure
```
backend/
├── app/
│   ├── api/
│   │   ├── v1/
│   │   │   ├── auth/
│   │   │   ├── designs/
│   │   │   ├── templates/
│   │   │   ├── jobs/
│   │   │   └── users/
│   │   └── deps.py
│   ├── core/
│   │   ├── config.py
│   │   ├── security.py
│   │   └── events.py
│   ├── db/
│   │   ├── models/
│   │   ├── repositories/
│   │   └── session.py
│   ├── services/
│   │   ├── cad/
│   │   ├── ai/
│   │   └── queue/
│   ├── schemas/
│   └── workers/
├── alembic/
├── tests/
└── pyproject.toml
```

### Key Dependencies
```toml
[project]
dependencies = [
    "fastapi>=0.104.0",
    "uvicorn[standard]>=0.24.0",
    "sqlalchemy[asyncio]>=2.0.0",
    "alembic>=1.12.0",
    "pydantic>=2.5.0",
    "pydantic-settings>=2.1.0",
    "celery>=5.3.0",
    "redis>=5.0.0",
    "httpx>=0.25.0",
    "python-jose[cryptography]>=3.3.0",
    "passlib[bcrypt]>=1.7.4",
    "python-multipart>=0.0.6",
]
```

### API Example
```python
from fastapi import FastAPI, Depends
from pydantic import BaseModel

app = FastAPI(title="AI Part Designer API", version="1.0.0")

class DesignCreate(BaseModel):
    description: str
    dimensions: dict | None = None

class DesignResponse(BaseModel):
    id: str
    status: str
    preview_url: str | None

@app.post("/api/v1/designs", response_model=DesignResponse)
async def create_design(
    design: DesignCreate,
    current_user: User = Depends(get_current_user)
):
    job = await design_service.submit_generation(design, current_user)
    return DesignResponse(id=job.id, status="queued")
```

## References
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [SQLAlchemy 2.0](https://docs.sqlalchemy.org/en/20/)
- [Celery Documentation](https://docs.celeryq.dev/)
- [Pydantic v2](https://docs.pydantic.dev/latest/)
