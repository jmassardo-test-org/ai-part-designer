# ADR-004: Queue System Technology Selection

## Status
Proposed

## Context
We need a robust queue system for asynchronous job processing. Requirements include:
- Design generation jobs (30-120 seconds)
- File conversion jobs (5-30 seconds)
- Design analysis jobs (10-45 seconds)
- Priority queuing based on subscription tier
- Job status tracking and progress updates
- Retry logic for failed jobs
- Horizontal scaling of workers
- Visibility into queue metrics

## Decision
We will use **Celery** with **Redis** as the message broker and result backend.

Supporting technology choices:
- **Broker**: Redis (also used for caching)
- **Result Backend**: Redis (short-term) + PostgreSQL (long-term persistence)
- **Monitoring**: Flower for real-time monitoring
- **Scheduling**: Celery Beat for periodic tasks
- **Priority Queues**: Celery's built-in priority support

## Consequences

### Positive
- **Python native**: Seamless integration with FastAPI backend
- **Mature ecosystem**: Well-documented, battle-tested at scale
- **Flexible routing**: Route jobs to specialized workers (CAD, AI, general)
- **Priority support**: Built-in priority queues for tier-based processing
- **Retry logic**: Configurable retry with exponential backoff
- **Monitoring**: Flower provides real-time visibility
- **Horizontal scaling**: Easy to add workers

### Negative
- **Complexity**: More moving parts than simpler solutions
- **Redis dependency**: Need to manage Redis availability
- **Memory**: Redis is in-memory (mitigated by persistence options)
- **Celery overhead**: Can be overkill for simple use cases

### Neutral
- Learning curve for Celery's task patterns
- Need to handle task serialization carefully

## Options Considered

| Option | Pros | Cons | Score |
|--------|------|------|-------|
| **Celery + Redis** | Mature, flexible, Python-native | Complexity | ⭐⭐⭐⭐⭐ |
| RQ (Redis Queue) | Simple, lightweight | Less features, no priority | ⭐⭐⭐ |
| AWS SQS + Lambda | Serverless, managed | Vendor lock-in, cold starts | ⭐⭐⭐⭐ |
| RabbitMQ | Robust, advanced routing | More operational overhead | ⭐⭐⭐⭐ |
| Dramatiq | Modern Celery alternative | Smaller ecosystem | ⭐⭐⭐ |
| Temporal | Workflow orchestration | Complex for our needs | ⭐⭐⭐ |

## Technical Details

### Queue Architecture
```
┌─────────────────────────────────────────────────────────────┐
│                        CLIENTS                               │
│  (Web App, API)                                             │
└─────────────────────────────┬───────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                     FastAPI Backend                          │
│  - Submit jobs to Celery                                    │
│  - Query job status                                         │
│  - WebSocket updates                                        │
└─────────────────────────────┬───────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                     Redis (Broker)                           │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐           │
│  │  Priority   │ │  Standard   │ │    Low      │           │
│  │   Queue     │ │   Queue     │ │   Queue     │           │
│  │ (Pro/Ent)   │ │   (Free)    │ │  (Batch)    │           │
│  └─────────────┘ └─────────────┘ └─────────────┘           │
└─────────────────────────────┬───────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        ▼                     ▼                     ▼
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│ CAD Worker   │    │  AI Worker   │    │ General      │
│ (CadQuery)   │    │  (LLM API)   │    │ Worker       │
│ - generate   │    │ - parse_desc │    │ - convert    │
│ - modify     │    │ - optimize   │    │ - analyze    │
└──────────────┘    └──────────────┘    └──────────────┘
```

### Celery Configuration
```python
# app/core/celery_app.py
from celery import Celery

celery_app = Celery(
    "ai_part_designer",
    broker="redis://localhost:6379/0",
    backend="redis://localhost:6379/1",
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    
    # Priority queues
    task_queues={
        "priority": {"exchange": "priority", "routing_key": "priority"},
        "standard": {"exchange": "standard", "routing_key": "standard"},
        "low": {"exchange": "low", "routing_key": "low"},
    },
    task_default_queue="standard",
    
    # Retry settings
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    
    # Rate limits
    task_annotations={
        "tasks.generate_design": {"rate_limit": "10/m"},
    },
    
    # Result expiration
    result_expires=86400,  # 24 hours
)
```

### Task Definition Example
```python
# app/workers/tasks.py
from celery import shared_task
from app.services.cad import CADService

@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},
)
def generate_design(self, job_id: str, description: str, parameters: dict):
    """Generate a 3D design from description."""
    try:
        # Update status to processing
        update_job_status(job_id, "processing", progress=0)
        
        # Parse description with AI
        parsed = ai_service.parse_design_description(description)
        update_job_status(job_id, "processing", progress=25)
        
        # Generate CAD geometry
        cad_service = CADService()
        geometry = cad_service.generate(parsed, parameters)
        update_job_status(job_id, "processing", progress=75)
        
        # Export and upload
        file_url = storage.upload(geometry.export_step())
        thumbnail_url = storage.upload(geometry.render_thumbnail())
        update_job_status(job_id, "processing", progress=90)
        
        # Complete
        complete_job(job_id, file_url, thumbnail_url)
        
    except Exception as e:
        fail_job(job_id, str(e))
        raise

@shared_task
def analyze_design(job_id: str, design_id: str):
    """Analyze design for optimization suggestions."""
    # ... implementation
```

### Priority Queue Routing
```python
# app/services/queue.py
def submit_generation_job(user: User, description: str, params: dict) -> str:
    job = create_job(user, "generate")
    
    # Determine queue based on subscription
    if user.subscription_tier in ["pro", "enterprise"]:
        queue = "priority"
    else:
        queue = "standard"
    
    # Submit to Celery
    generate_design.apply_async(
        args=[job.id, description, params],
        queue=queue,
        priority=get_priority_level(user.subscription_tier),
    )
    
    return job.id
```

### Worker Startup
```bash
# Start CAD workers (require OpenCASCADE)
celery -A app.workers worker -Q priority,standard -c 4 --hostname=cad@%h

# Start general workers
celery -A app.workers worker -Q low -c 2 --hostname=general@%h

# Start Flower monitoring
celery -A app.workers flower --port=5555
```

## Scaling Strategy

| Scale | Workers | Configuration |
|-------|---------|---------------|
| MVP | 2-4 | Single server, multiple processes |
| Growth | 8-16 | Multiple servers, dedicated CAD workers |
| Scale | 20+ | Auto-scaling worker pool, queue metrics triggers |

## References
- [Celery Documentation](https://docs.celeryq.dev/)
- [Celery Best Practices](https://docs.celeryq.dev/en/stable/userguide/tasks.html#best-practices)
- [Flower Monitoring](https://flower.readthedocs.io/)
- [Redis Documentation](https://redis.io/documentation)
