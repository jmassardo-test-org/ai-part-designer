# ADR-011: Monitoring and Observability Stack

## Status
Accepted (Updated 2024-02-04)

## Context
We need comprehensive monitoring and observability to:
- Track application performance and errors
- Monitor infrastructure health
- Debug production issues quickly
- Alert on critical problems
- Understand user behavior and system usage
- Meet SLA commitments (99.9% uptime)

**Key Requirement**: All solutions must be Open Source Software (OSS) for full control, portability, and cost-effectiveness.

## Decision
We will implement a **multi-layer observability stack** using 100% OSS components:
- **Logging**: ELK Stack (Elasticsearch, Logstash, Kibana) with Filebeat
- **Tracing**: OpenTelemetry + Tempo (Grafana Labs)
- **Metrics**: Prometheus + Grafana
- **Error Tracking**: Sentry (Self-Hosted OSS)
- **Correlation**: All systems connected via trace_id and request_id
- **Alerting**: Grafana Alerting + Prometheus Alertmanager

## Consequences

### Positive
- **100% OSS**: Full control, no vendor lock-in, portable across clouds
- **Self-hosted**: Complete data privacy and cost predictability
- **End-to-end visibility**: Metrics, logs, and traces correlated
- **Fast debugging**: Trace requests across services with distributed tracing
- **Proactive alerting**: Know about issues before users report
- **Cloud-agnostic**: Aligns with ADR-013 cloud-agnostic architecture
- **Community support**: Large OSS communities for all components

### Negative
- **Operational overhead**: Self-hosted requires management and updates
- **Resource requirements**: Need to provision infrastructure for monitoring stack
- **Multiple tools**: Need to learn several systems (ELK, Prometheus, Tempo, Sentry)
- **Initial setup complexity**: More complex than managed services

### Mitigation
- Use Docker Compose for local development (simple setup)
- Deploy via Helm charts in production (standardized)
- Start with essential metrics and dashboards, expand as needed
- Set log retention policies to control storage costs
- Use trace sampling (10%) in production to reduce overhead
- Document runbooks and common operations

## Options Considered

| Component | Options | Choice | Rationale |
|-----------|---------|--------|-----------|
| Logging | ELK, Loki, OpenSearch | **ELK Stack** | Industry standard, powerful queries, rich visualization |
| Tracing | Jaeger, Tempo, Zipkin | **Tempo** | S3-backed (cost-effective), native Grafana integration |
| Metrics | Prometheus, InfluxDB, VictoriaMetrics | **Prometheus** | De facto standard, CNCF graduated, huge ecosystem |
| Visualization | Grafana, Kibana | **Both** | Grafana for metrics/traces, Kibana for logs |
| Errors | Sentry OSS, GlitchTip, Rollbar | **Sentry OSS** | Best-in-class error tracking, self-hosted |
| Instrumentation | OpenTelemetry, Zipkin, Custom | **OpenTelemetry** | Vendor-neutral, CNCF standard, future-proof |

### Why Not AWS-Managed Services?
While ADR-009 chose AWS for deployment, we're using OSS monitoring tools to:
- Maintain cloud portability (can move to GCP/Azure/self-hosted)
- Avoid vendor lock-in for observability data
- Control costs (self-hosted is cheaper at scale)
- Keep data private and under our control
- Align with OSS requirement from issue

## Technical Details

### Observability Architecture
```
┌─────────────────────────────────────────────────────────────────────────┐
│                         APPLICATION LAYER                                │
│  ┌─────────────────────────────────────────────────────────────────────┐│
│  │  FastAPI App + Celery Workers                                       ││
│  │  ├── Structured JSON logging (stdout)                               ││
│  │  ├── OpenTelemetry instrumentation (auto + manual)                  ││
│  │  ├── Prometheus metrics endpoint (/metrics)                         ││
│  │  └── Sentry error capture                                           ││
│  └─────────────────────────────────────────────────────────────────────┘│
└────────────────────────────────┬────────────────────────────────────────┘
                                 │
         ┌───────────────────────┼───────────────────────┐
         │                       │                       │
         ▼                       ▼                       ▼
┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐
│   Filebeat       │  │  OTEL Collector  │  │  Prometheus      │
│   (Shipper)      │  │  (Traces)        │  │  (Scraper)       │
│                  │  │                  │  │                  │
│  Collects logs   │  │  Receives spans  │  │  Pulls /metrics  │
│  from Docker     │  │  Batches traces  │  │  Stores TSDB     │
└────────┬─────────┘  └────────┬─────────┘  └────────┬─────────┘
         │                     │                      │
         ▼                     ▼                      │
┌──────────────────┐  ┌──────────────────┐           │
│   Logstash       │  │     Tempo        │           │
│   (Processing)   │  │  (Trace Store)   │           │
│                  │  │                  │           │
│  - Parses JSON   │  │  - S3 backend    │           │
│  - Enriches      │  │  - Query API     │           │
│  - Filters       │  │  - Compression   │           │
└────────┬─────────┘  └────────┬─────────┘           │
         │                     │                      │
         ▼                     │                      │
┌──────────────────┐           │                      │
│  Elasticsearch   │◄──────────┼──────────────────────┤
│   (Log Store)    │           │                      │
│                  │  ┌────────▼──────────┐           │
│  - Full-text     │  │    Grafana        │◄──────────┘
│  - Aggregations  │  │  (Visualization)  │
│  - Time-series   │  │                   │
└────────┬─────────┘  │  - Trace viewer   │
         │            │  - Dashboards     │
         │            │  - Alerting       │
         ▼            └───────────────────┘
┌──────────────────┐
│    Kibana        │  ┌──────────────────┐
│  (Log Explorer)  │  │  Sentry Web      │
│                  │  │  (Error Track)   │
│  - Discover      │  │                  │
│  - Dashboards    │  │  - Grouping      │
│  - Queries       │  │  - Alerts        │
└──────────────────┘  │  - Releases      │
                      └──────────────────┘
```

### Prometheus Metrics Setup
```python
# app/core/metrics.py
from prometheus_client import Counter, Histogram, Gauge, generate_latest
from fastapi import FastAPI, Request, Response
import time

# Define metrics
REQUEST_COUNT = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status']
)

REQUEST_LATENCY = Histogram(
    'http_request_duration_seconds',
    'HTTP request latency',
    ['method', 'endpoint'],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
)

ACTIVE_REQUESTS = Gauge(
    'http_requests_active',
    'Currently active HTTP requests'
)

JOB_QUEUE_SIZE = Gauge(
    'job_queue_size',
    'Number of jobs in queue',
    ['queue_name', 'priority']
)

JOB_DURATION = Histogram(
    'job_duration_seconds',
    'Job processing duration',
    ['job_type'],
    buckets=[1, 5, 10, 30, 60, 120, 300]
)

DESIGN_GENERATION_SUCCESS = Counter(
    'design_generation_total',
    'Design generation attempts',
    ['status']  # success, failure, timeout
)

def setup_metrics(app: FastAPI):
    @app.middleware("http")
    async def metrics_middleware(request: Request, call_next):
        ACTIVE_REQUESTS.inc()
        start_time = time.time()
        
        response = await call_next(request)
        
        duration = time.time() - start_time
        endpoint = request.url.path
        method = request.method
        status = response.status_code
        
        REQUEST_COUNT.labels(method=method, endpoint=endpoint, status=status).inc()
        REQUEST_LATENCY.labels(method=method, endpoint=endpoint).observe(duration)
        ACTIVE_REQUESTS.dec()
        
        return response
    
    @app.get("/metrics")
    async def metrics():
        return Response(
            content=generate_latest(),
            media_type="text/plain"
        )
```

### Structured Logging
```python
# app/core/logging.py
import structlog
import logging
from pythonjsonlogger import jsonlogger

def setup_logging():
    # Configure structlog
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer()
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
    )
    
    # Also configure standard logging for libraries
    handler = logging.StreamHandler()
    handler.setFormatter(jsonlogger.JsonFormatter(
        fmt='%(asctime)s %(levelname)s %(name)s %(message)s'
    ))
    
    root_logger = logging.getLogger()
    root_logger.handlers = [handler]
    root_logger.setLevel(logging.INFO)

# Usage in application
logger = structlog.get_logger()

async def create_design(request: DesignRequest, user: User):
    logger.info(
        "design_creation_started",
        user_id=str(user.id),
        description_length=len(request.description),
        has_template=request.template_name is not None
    )
    
    try:
        result = await generate_design(request)
        logger.info(
            "design_creation_completed",
            user_id=str(user.id),
            design_id=str(result.id),
            duration_ms=result.duration_ms
        )
        return result
    except Exception as e:
        logger.error(
            "design_creation_failed",
            user_id=str(user.id),
            error=str(e),
            exc_info=True
        )
        raise
```

### Request Context
```python
# app/middleware/context.py
import uuid
import structlog
from contextvars import ContextVar
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

request_id_var: ContextVar[str] = ContextVar("request_id", default="")

class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        request_id_var.set(request_id)
        
        # Add to structlog context
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            request_id=request_id,
            path=request.url.path,
            method=request.method
        )
        
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        
        return response
```

### AWS X-Ray Integration
```python
# app/core/tracing.py
from aws_xray_sdk.core import xray_recorder, patch_all
from aws_xray_sdk.ext.fastapi.middleware import XRayMiddleware

def setup_tracing(app):
    # Patch all supported libraries (requests, httpx, sqlalchemy, etc.)
    patch_all()
    
    xray_recorder.configure(
        service="ai-part-designer-api",
        sampling=True,
        context_missing='LOG_ERROR'
    )
    
    app.add_middleware(XRayMiddleware, recorder=xray_recorder)

# Manual subsegment for detailed tracing
async def generate_cad_geometry(params):
    with xray_recorder.in_subsegment('cad_generation') as subsegment:
        subsegment.put_annotation('template', params.get('template', 'custom'))
        
        result = await cad_service.generate(params)
        
        subsegment.put_metadata('dimensions', result.dimensions)
        return result
```

### Sentry Integration
```python
# app/core/sentry.py
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.celery import CeleryIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
from sentry_sdk.integrations.redis import RedisIntegration

def setup_sentry():
    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        environment=settings.ENVIRONMENT,
        release=settings.VERSION,
        traces_sample_rate=0.1,  # 10% of transactions
        profiles_sample_rate=0.1,  # 10% of profiled transactions
        integrations=[
            FastApiIntegration(),
            CeleryIntegration(),
            SqlalchemyIntegration(),
            RedisIntegration(),
        ],
        # Don't send PII
        send_default_pii=False,
        # Filter sensitive data
        before_send=filter_sensitive_data,
    )

def filter_sensitive_data(event, hint):
    # Remove sensitive headers
    if 'request' in event:
        headers = event['request'].get('headers', {})
        headers.pop('authorization', None)
        headers.pop('cookie', None)
    return event
```

### Key Dashboards

#### API Health Dashboard
```yaml
# Grafana dashboard definition
panels:
  - title: Request Rate
    query: rate(http_requests_total[5m])
    type: graph
    
  - title: Error Rate
    query: rate(http_requests_total{status=~"5.."}[5m]) / rate(http_requests_total[5m])
    type: gauge
    thresholds: [0.01, 0.05]  # 1%, 5%
    
  - title: P50 Latency
    query: histogram_quantile(0.5, rate(http_request_duration_seconds_bucket[5m]))
    type: graph
    
  - title: P99 Latency
    query: histogram_quantile(0.99, rate(http_request_duration_seconds_bucket[5m]))
    type: graph
```

#### Job Processing Dashboard
```yaml
panels:
  - title: Queue Depth
    query: job_queue_size
    type: graph
    
  - title: Jobs/minute
    query: rate(job_duration_seconds_count[5m]) * 60
    type: stat
    
  - title: Job Duration P95
    query: histogram_quantile(0.95, rate(job_duration_seconds_bucket[5m]))
    type: graph
    
  - title: Success Rate
    query: rate(design_generation_total{status="success"}[5m]) / rate(design_generation_total[5m])
    type: gauge
```

### Alert Rules
```yaml
# CloudWatch/Prometheus alert rules
alerts:
  - name: HighErrorRate
    condition: error_rate > 0.05 for 5m
    severity: critical
    action: page_oncall
    
  - name: HighLatency
    condition: p99_latency > 5s for 10m
    severity: warning
    action: slack_alert
    
  - name: QueueBacklog
    condition: job_queue_size > 100 for 15m
    severity: warning
    action: slack_alert
    
  - name: DatabaseConnectionsHigh
    condition: db_connections > 80% for 10m
    severity: warning
    action: slack_alert
    
  - name: ServiceDown
    condition: up == 0 for 1m
    severity: critical
    action: page_oncall
```

### Cost Estimation

| Service | Configuration | Monthly Cost |
|---------|---------------|--------------|
| AWS Managed Prometheus | 10M samples | ~$30 |
| AWS Managed Grafana | 1 workspace | ~$9 |
| CloudWatch Logs | 50GB | ~$25 |
| AWS X-Ray | 1M traces | ~$5 |
| Sentry | Team plan | ~$26 |
| Uptime monitoring | External | ~$20 |
| **Total** | | **~$115/month** |

## References
- [Prometheus Documentation](https://prometheus.io/docs/)
- [AWS X-Ray](https://docs.aws.amazon.com/xray/)
- [Sentry Python SDK](https://docs.sentry.io/platforms/python/)
- [structlog](https://www.structlog.org/)
