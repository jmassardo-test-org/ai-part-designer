# Logging and Monitoring Implementation Specification

## Executive Summary

This document provides a comprehensive implementation plan for logging, monitoring, and observability infrastructure using open-source software (OSS) for the AssemblematicAI platform.

**Status**: Draft for Review  
**Target Completion**: 4-6 weeks  
**Estimated Effort**: 80-120 story points

---

## Requirements Overview

Based on the issue requirements, we need to implement:

1. **ELK Stack** - Centralized log storage, processing, and visualization
2. **APM Solution** - Application Performance Monitoring
3. **Exception Monitoring** - Error tracking and alerting

### Success Criteria

✅ All logs centralized in Elasticsearch with structured JSON format  
✅ Kibana dashboards for log exploration and analysis  
✅ Distributed tracing across API, workers, and database  
✅ Real-time exception tracking with alerts  
✅ <500ms latency overhead from instrumentation  
✅ 7-day log retention with configurable policies  
✅ All components deployed via Docker Compose (dev) and Kubernetes (prod)

---

## 1. ELK Stack for Logging

### Architecture Decision

**Components:**
- **Elasticsearch 8.x** - Log storage and search engine
- **Logstash 8.x** - Log processing and enrichment pipeline
- **Kibana 8.x** - Visualization and dashboarding
- **Filebeat 8.x** - Lightweight log shipper

**Why ELK?**
- ✅ Industry-standard OSS solution
- ✅ Powerful full-text search capabilities
- ✅ Rich visualization and dashboarding
- ✅ Scalable to millions of log events
- ✅ Large ecosystem and community support

### Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                      Application Layer                          │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐                │
│  │  FastAPI   │  │   Celery   │  │  Frontend  │                │
│  │    API     │  │   Worker   │  │   (Nginx)  │                │
│  └─────┬──────┘  └─────┬──────┘  └─────┬──────┘                │
│        │               │               │                        │
│        └───────────────┴───────────────┘                        │
│                        │                                        │
│                        ▼ (JSON logs to stdout/files)            │
└────────────────────────┼───────────────────────────────────────┘
                         │
                         ▼
              ┌──────────────────┐
              │   Filebeat       │
              │  (Log Shipper)   │
              │                  │
              │  - Parses JSON   │
              │  - Adds metadata │
              │  - Buffers logs  │
              └────────┬─────────┘
                       │
                       ▼
              ┌──────────────────┐
              │   Logstash       │
              │  (Processing)    │
              │                  │
              │  - Filters       │
              │  - Enriches      │
              │  - Transforms    │
              └────────┬─────────┘
                       │
                       ▼
              ┌──────────────────┐
              │  Elasticsearch   │
              │  (Storage)       │
              │                  │
              │  - Indexes logs  │
              │  - Full-text     │
              │  - Aggregations  │
              └────────┬─────────┘
                       │
                       ▼
              ┌──────────────────┐
              │    Kibana        │
              │  (Visualization) │
              │                  │
              │  - Dashboards    │
              │  - Queries       │
              │  - Alerts        │
              └──────────────────┘
```

### Log Format Specification

**Structured JSON Logging**

Every log entry will follow this schema:

```json
{
  "timestamp": "2024-02-04T22:48:40.123Z",
  "level": "INFO",
  "logger": "app.api.design",
  "message": "Design created successfully",
  "request_id": "req-123e4567-e89b-12d3-a456-426614174000",
  "trace_id": "trace-abc123def456",
  "span_id": "span-789ghi",
  "user_id": "usr-987654321",
  "service": "api",
  "environment": "production",
  "version": "1.2.3",
  "context": {
    "design_id": "design-123",
    "template": "box",
    "duration_ms": 1234,
    "method": "POST",
    "path": "/api/v1/designs",
    "status_code": 201
  },
  "exception": {
    "type": "ValueError",
    "message": "Invalid parameter",
    "stacktrace": "..."
  }
}
```

**Log Levels:**
- `DEBUG` - Detailed diagnostic information (disabled in production)
- `INFO` - General informational messages
- `WARNING` - Warning messages, but application continues
- `ERROR` - Error messages, operation failed but app continues
- `CRITICAL` - Critical errors, application may stop

### Elasticsearch Index Strategy

**Time-based indices** for efficient retention and rollover:

```
logs-api-2024.02.04
logs-worker-2024.02.04
logs-frontend-2024.02.04
```

**Index Lifecycle Management (ILM):**
1. Hot tier (0-2 days): Fast SSD storage, actively written
2. Warm tier (2-7 days): Regular storage, read-only
3. Delete (>7 days): Automatic cleanup

**Retention Policy:**
- Development: 3 days
- Staging: 7 days
- Production: 30 days (configurable)

### Logstash Pipeline Configuration

```ruby
# logstash/pipeline/api-logs.conf
input {
  beats {
    port => 5044
    codec => json
  }
}

filter {
  # Add geo-location based on IP
  geoip {
    source => "client_ip"
    target => "geoip"
  }
  
  # Parse duration to number
  mutate {
    convert => { "duration_ms" => "integer" }
  }
  
  # Add custom tags
  if [level] == "ERROR" or [level] == "CRITICAL" {
    mutate {
      add_tag => ["alert"]
    }
  }
  
  # Drop noisy logs
  if [logger] == "uvicorn.access" and [status_code] == 200 {
    drop { }
  }
}

output {
  elasticsearch {
    hosts => ["elasticsearch:9200"]
    index => "logs-%{[service]}-%{+YYYY.MM.dd}"
  }
}
```

### Kibana Dashboards

**1. Application Overview Dashboard**
- Request rate by endpoint (line chart)
- Error rate percentage (gauge)
- P50/P95/P99 latency (time series)
- Top 10 errors (table)
- Active users (counter)

**2. Error Analysis Dashboard**
- Errors by type (pie chart)
- Error trend (time series)
- Stack trace viewer
- Affected users (table)
- Error rate by endpoint (heat map)

**3. Performance Dashboard**
- Response time distribution (histogram)
- Slow queries (>1s) (table)
- Database connection pool usage
- Redis hit/miss ratio
- Celery queue depth

**4. User Activity Dashboard**
- Active sessions
- User journey flow
- Feature usage heatmap
- Conversion funnel

### Implementation Tasks - ELK Stack

#### Task 1.1: Add ELK Services to Docker Compose
**Effort**: 3 points  
**Description**: Add Elasticsearch, Logstash, Kibana, and Filebeat services

```yaml
# docker-compose.yml additions
elasticsearch:
  image: docker.elastic.co/elasticsearch/elasticsearch:8.11.3
  environment:
    - discovery.type=single-node
    - xpack.security.enabled=false
    - "ES_JAVA_OPTS=-Xms512m -Xmx512m"
  ports:
    - "9200:9200"
  volumes:
    - elasticsearch_data:/usr/share/elasticsearch/data

logstash:
  image: docker.elastic.co/logstash/logstash:8.11.3
  volumes:
    - ./logstash/pipeline:/usr/share/logstash/pipeline
  ports:
    - "5044:5044"
  depends_on:
    - elasticsearch

kibana:
  image: docker.elastic.co/kibana/kibana:8.11.3
  ports:
    - "5601:5601"
  environment:
    - ELASTICSEARCH_HOSTS=http://elasticsearch:9200
  depends_on:
    - elasticsearch

filebeat:
  image: docker.elastic.co/beats/filebeat:8.11.3
  user: root
  volumes:
    - ./filebeat/filebeat.yml:/usr/share/filebeat/filebeat.yml
    - /var/lib/docker/containers:/var/lib/docker/containers:ro
    - /var/run/docker.sock:/var/run/docker.sock:ro
  depends_on:
    - logstash
```

#### Task 1.2: Implement Structured Logging
**Effort**: 5 points  
**Files**: `backend/app/core/logging.py`

```python
"""
Structured logging configuration for the application.

Uses python-json-logger for JSON formatting and contextvars
for request correlation.
"""

import logging
import sys
from contextvars import ContextVar
from typing import Any

from pythonjsonlogger import jsonlogger

from app.core.config import get_settings

# Context variables for request correlation
request_id_var: ContextVar[str] = ContextVar("request_id", default="")
trace_id_var: ContextVar[str] = ContextVar("trace_id", default="")
user_id_var: ContextVar[str] = ContextVar("user_id", default="")


class CustomJsonFormatter(jsonlogger.JsonFormatter):
    """Custom JSON formatter with context injection."""
    
    def add_fields(self, log_record: dict, record: logging.LogRecord, message_dict: dict) -> None:
        """Add custom fields to log record."""
        super().add_fields(log_record, record, message_dict)
        
        # Add service metadata
        settings = get_settings()
        log_record["service"] = "api"  # or "worker" depending on service
        log_record["environment"] = settings.ENVIRONMENT
        log_record["version"] = settings.APP_VERSION
        
        # Add context from contextvars
        request_id = request_id_var.get()
        if request_id:
            log_record["request_id"] = request_id
        
        trace_id = trace_id_var.get()
        if trace_id:
            log_record["trace_id"] = trace_id
        
        user_id = user_id_var.get()
        if user_id:
            log_record["user_id"] = user_id
        
        # Rename level to match ELK convention
        log_record["level"] = record.levelname


def setup_logging() -> None:
    """Configure structured JSON logging for the application."""
    settings = get_settings()
    
    # Create JSON formatter
    formatter = CustomJsonFormatter(
        fmt="%(timestamp)s %(level)s %(name)s %(message)s",
        rename_fields={
            "asctime": "timestamp",
            "levelname": "level",
            "name": "logger",
        },
    )
    
    # Configure handler
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    
    # Set log level based on environment
    if settings.DEBUG:
        root_logger.setLevel(logging.DEBUG)
    else:
        root_logger.setLevel(logging.INFO)
    
    # Reduce noise from third-party libraries
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance with the given name."""
    return logging.getLogger(name)


def log_with_context(logger: logging.Logger, level: str, message: str, **context: Any) -> None:
    """
    Log a message with additional context.
    
    Args:
        logger: Logger instance
        level: Log level (debug, info, warning, error, critical)
        message: Log message
        **context: Additional context fields
    """
    log_func = getattr(logger, level.lower())
    log_func(message, extra={"context": context})
```

**Acceptance Criteria:**
- ✅ All logs output in JSON format
- ✅ Request ID automatically added to all logs in request context
- ✅ Log level configurable via environment variable
- ✅ Third-party library logs filtered appropriately

#### Task 1.3: Add Request Context Middleware
**Effort**: 3 points  
**Files**: `backend/app/middleware/logging.py`

```python
"""
Logging middleware for request correlation.

Adds unique request ID to all logs within a request context.
"""

import time
import uuid
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.logging import request_id_var, trace_id_var, log_with_context, get_logger

logger = get_logger(__name__)


class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware to add request correlation and logging."""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and add logging context."""
        # Generate or extract request ID
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        trace_id = request.headers.get("X-Trace-ID", str(uuid.uuid4()))
        
        # Set context variables
        request_id_var.set(request_id)
        trace_id_var.set(trace_id)
        
        # Log request start
        start_time = time.time()
        log_with_context(
            logger,
            "info",
            "Request started",
            method=request.method,
            path=request.url.path,
            client_ip=request.client.host if request.client else None,
        )
        
        try:
            # Process request
            response = await call_next(request)
            
            # Calculate duration
            duration_ms = int((time.time() - start_time) * 1000)
            
            # Log request completion
            log_with_context(
                logger,
                "info",
                "Request completed",
                method=request.method,
                path=request.url.path,
                status_code=response.status_code,
                duration_ms=duration_ms,
            )
            
            # Add correlation headers to response
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Trace-ID"] = trace_id
            
            return response
            
        except Exception as e:
            # Log error
            duration_ms = int((time.time() - start_time) * 1000)
            log_with_context(
                logger,
                "error",
                "Request failed",
                method=request.method,
                path=request.url.path,
                duration_ms=duration_ms,
                error=str(e),
                error_type=type(e).__name__,
            )
            raise
```

**Acceptance Criteria:**
- ✅ Unique request ID generated for each request
- ✅ Request ID propagated through all logs in request context
- ✅ Request duration logged automatically
- ✅ Errors logged with full context

#### Task 1.4: Create Logstash Pipelines
**Effort**: 2 points  
**Files**: `logstash/pipeline/*.conf`

See pipeline configuration above.

#### Task 1.5: Create Kibana Dashboards
**Effort**: 5 points  
**Deliverable**: Dashboard JSON exports in `kibana/dashboards/`

Dashboard specifications listed above.

#### Task 1.6: Production Deployment (Kubernetes)
**Effort**: 8 points  
**Files**: `k8s/monitoring/elk/*.yaml`

```yaml
# k8s/monitoring/elk/elasticsearch-statefulset.yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: elasticsearch
  namespace: monitoring
spec:
  serviceName: elasticsearch
  replicas: 3
  selector:
    matchLabels:
      app: elasticsearch
  template:
    metadata:
      labels:
        app: elasticsearch
    spec:
      containers:
      - name: elasticsearch
        image: docker.elastic.co/elasticsearch/elasticsearch:8.11.3
        resources:
          limits:
            memory: "4Gi"
            cpu: "2"
          requests:
            memory: "2Gi"
            cpu: "1"
        ports:
        - containerPort: 9200
          name: http
        - containerPort: 9300
          name: transport
        volumeMounts:
        - name: data
          mountPath: /usr/share/elasticsearch/data
        env:
        - name: cluster.name
          value: "assemblematic-logs"
        - name: node.name
          valueFrom:
            fieldRef:
              fieldPath: metadata.name
        - name: discovery.seed_hosts
          value: "elasticsearch-0.elasticsearch,elasticsearch-1.elasticsearch,elasticsearch-2.elasticsearch"
        - name: cluster.initial_master_nodes
          value: "elasticsearch-0,elasticsearch-1,elasticsearch-2"
        - name: ES_JAVA_OPTS
          value: "-Xms2g -Xmx2g"
  volumeClaimTemplates:
  - metadata:
      name: data
    spec:
      accessModes: [ "ReadWriteOnce" ]
      storageClassName: "fast-ssd"
      resources:
        requests:
          storage: 100Gi
```

**Acceptance Criteria:**
- ✅ 3-node Elasticsearch cluster for high availability
- ✅ Persistent volumes configured
- ✅ Resource limits set appropriately
- ✅ Health checks configured

---

## 2. APM (Application Performance Monitoring)

### Architecture Decision

**Solution: OpenTelemetry + Tempo**

**Components:**
- **OpenTelemetry (OTEL)** - Instrumentation framework
- **Tempo** - Distributed tracing backend (Grafana Labs)
- **Grafana** - Visualization for traces and metrics
- **Prometheus** - Metrics collection

**Why OpenTelemetry + Tempo?**
- ✅ OpenTelemetry is vendor-neutral, CNCF standard
- ✅ Tempo is OSS, S3-backed (cost-effective)
- ✅ Native Grafana integration
- ✅ Automatic instrumentation for FastAPI, SQLAlchemy, Redis
- ✅ Low overhead (<1% CPU)

### Distributed Tracing Architecture

```
┌───────────────────────────────────────────────────────────────┐
│                    Request Flow                               │
└───────────────────────────────────────────────────────────────┘
                                 │
   User Request ─────────────────┤
                                 │
                                 ▼
                    ┌────────────────────────┐
                    │  API (FastAPI)         │
                    │  Span: http_request    │
                    │  trace_id: abc123      │
                    └─────────┬──────────────┘
                              │
                ┌─────────────┼─────────────┐
                │             │             │
                ▼             ▼             ▼
    ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
    │  Database    │ │    Redis     │ │  S3 Storage  │
    │  Span: query │ │  Span: cache │ │  Span: upload│
    └──────────────┘ └──────────────┘ └──────────────┘
                              │
                              ▼
                    ┌──────────────────┐
                    │  Celery Worker   │
                    │  Span: cad_gen   │
                    └──────────────────┘
                              │
                              ▼
                    ┌──────────────────┐
                    │  OTEL Collector  │
                    │  (aggregates)    │
                    └─────────┬────────┘
                              │
                              ▼
                    ┌──────────────────┐
                    │     Tempo        │
                    │  (stores traces) │
                    └─────────┬────────┘
                              │
                              ▼
                    ┌──────────────────┐
                    │    Grafana       │
                    │ (visualizes)     │
                    └──────────────────┘
```

### Instrumentation Strategy

**Automatic Instrumentation:**
- FastAPI HTTP requests
- SQLAlchemy database queries
- Redis cache operations
- HTTP client requests (httpx)
- Celery task execution

**Manual Instrumentation:**
- CAD generation steps
- AI model inference
- File upload/download
- Custom business logic

### Key Metrics to Track

**Request Metrics:**
- `http_requests_total` - Total HTTP requests by method, endpoint, status
- `http_request_duration_seconds` - Request latency histogram
- `http_requests_in_progress` - Active requests gauge

**Database Metrics:**
- `db_queries_total` - Total queries by table, operation
- `db_query_duration_seconds` - Query latency histogram
- `db_connections_active` - Active connections gauge
- `db_connections_idle` - Idle connections gauge

**Cache Metrics:**
- `cache_hits_total` - Cache hits counter
- `cache_misses_total` - Cache misses counter
- `cache_operations_duration_seconds` - Cache operation latency

**Business Metrics:**
- `designs_created_total` - Designs created by template, tier
- `design_generation_duration_seconds` - Generation time
- `ai_tokens_used_total` - AI tokens consumed
- `exports_total` - File exports by format

### Implementation Tasks - APM

#### Task 2.1: Add OpenTelemetry Dependencies
**Effort**: 1 point

```toml
# backend/pyproject.toml
dependencies = [
    # ... existing deps
    "opentelemetry-api>=1.22.0",
    "opentelemetry-sdk>=1.22.0",
    "opentelemetry-instrumentation-fastapi>=0.43b0",
    "opentelemetry-instrumentation-sqlalchemy>=0.43b0",
    "opentelemetry-instrumentation-redis>=0.43b0",
    "opentelemetry-instrumentation-celery>=0.43b0",
    "opentelemetry-exporter-otlp>=1.22.0",
]
```

#### Task 2.2: Implement Telemetry Configuration
**Effort**: 5 points  
**Files**: `backend/app/core/telemetry.py`

```python
"""
OpenTelemetry tracing configuration.

Provides distributed tracing across API, workers, and infrastructure.
"""

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor
from opentelemetry.instrumentation.celery import CeleryInstrumentor
from opentelemetry.sdk.resources import Resource, SERVICE_NAME, SERVICE_VERSION
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from fastapi import FastAPI

from app.core.config import get_settings


def setup_telemetry(app: FastAPI) -> None:
    """
    Configure OpenTelemetry tracing for the application.
    
    Args:
        app: FastAPI application instance
    """
    settings = get_settings()
    
    # Create resource with service metadata
    resource = Resource.create({
        SERVICE_NAME: "assemblematic-api",
        SERVICE_VERSION: settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
    })
    
    # Create tracer provider
    tracer_provider = TracerProvider(resource=resource)
    
    # Configure OTLP exporter (sends to Tempo via OTEL Collector)
    otlp_exporter = OTLPSpanExporter(
        endpoint=settings.OTEL_EXPORTER_OTLP_ENDPOINT,
        insecure=settings.ENVIRONMENT == "development",
    )
    
    # Add batch processor (efficient batching)
    tracer_provider.add_span_processor(
        BatchSpanProcessor(otlp_exporter)
    )
    
    # Set global tracer provider
    trace.set_tracer_provider(tracer_provider)
    
    # Instrument frameworks
    FastAPIInstrumentor.instrument_app(app)
    SQLAlchemyInstrumentor().instrument()
    RedisInstrumentor().instrument()
    CeleryInstrumentor().instrument()


def get_tracer(name: str) -> trace.Tracer:
    """Get a tracer instance for manual instrumentation."""
    return trace.get_tracer(name)
```

**Acceptance Criteria:**
- ✅ Traces exported to OTEL Collector
- ✅ All HTTP requests automatically traced
- ✅ Database queries show up as child spans
- ✅ Sampling rate configurable

#### Task 2.3: Add Tempo and OTEL Collector to Docker Compose
**Effort**: 3 points

```yaml
# docker-compose.yml
otel-collector:
  image: otel/opentelemetry-collector-contrib:0.91.0
  command: ["--config=/etc/otel-collector-config.yaml"]
  volumes:
    - ./otel-collector-config.yaml:/etc/otel-collector-config.yaml
  ports:
    - "4317:4317"   # OTLP gRPC
    - "4318:4318"   # OTLP HTTP
  depends_on:
    - tempo

tempo:
  image: grafana/tempo:2.3.1
  command: ["-config.file=/etc/tempo.yaml"]
  volumes:
    - ./tempo/tempo.yaml:/etc/tempo.yaml
    - tempo_data:/tmp/tempo
  ports:
    - "3200:3200"   # Tempo HTTP
    - "9095:9095"   # Tempo gRPC

grafana:
  image: grafana/grafana:10.2.3
  ports:
    - "3000:3000"
  environment:
    - GF_AUTH_ANONYMOUS_ENABLED=true
    - GF_AUTH_ANONYMOUS_ORG_ROLE=Admin
  volumes:
    - grafana_data:/var/lib/grafana
    - ./grafana/provisioning:/etc/grafana/provisioning
```

#### Task 2.4: Create Grafana Dashboards for Traces
**Effort**: 3 points

**Service Map Dashboard:**
- Visualize service dependencies
- Show request flows
- Identify bottlenecks

**Latency Dashboard:**
- P50/P95/P99 latency by endpoint
- Slowest operations
- Latency over time

**Error Analysis Dashboard:**
- Errors by service
- Failed traces
- Error rate trends

#### Task 2.5: Add Prometheus for Metrics
**Effort**: 5 points

```python
# backend/app/core/metrics.py
from prometheus_client import Counter, Histogram, Gauge, generate_latest
from fastapi import FastAPI, Response

# Define metrics
http_requests_total = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status']
)

http_request_duration_seconds = Histogram(
    'http_request_duration_seconds',
    'HTTP request duration',
    ['method', 'endpoint'],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
)

# ... more metrics


def setup_metrics(app: FastAPI) -> None:
    """Configure Prometheus metrics endpoint."""
    
    @app.get("/metrics")
    async def metrics():
        """Expose Prometheus metrics."""
        return Response(
            content=generate_latest(),
            media_type="text/plain"
        )
```

---

## 3. Exception Monitoring & Alerting

### Architecture Decision

**Solution: Sentry (Self-Hosted OSS)**

**Why Sentry OSS?**
- ✅ Industry-leading error tracking
- ✅ Self-hosted = free and private
- ✅ Excellent Python/JavaScript SDKs
- ✅ Error grouping and deduplication
- ✅ Release tracking and deploy notifications
- ✅ Performance monitoring included

**Alternative Considered:**
- **GlitchTip** - Sentry-compatible, simpler but less mature

### Exception Tracking Features

1. **Automatic Error Capture**
   - Unhandled exceptions
   - HTTP errors (4xx, 5xx)
   - Database errors
   - Validation errors

2. **Context Enrichment**
   - User information
   - Request data (headers, body, query params)
   - Environment variables
   - Breadcrumbs (user actions leading to error)
   - Server context (OS, runtime, hostname)

3. **Error Grouping**
   - Similar errors grouped by stack trace
   - Fingerprinting rules
   - Ignore rules for known issues

4. **Alerting**
   - Email notifications
   - Slack/Discord webhooks
   - PagerDuty integration
   - Alert on new issues
   - Alert on spike in error rate

### Implementation Tasks - Exception Monitoring

#### Task 3.1: Deploy Sentry via Docker Compose
**Effort**: 5 points

```bash
# Use official Sentry self-hosted repository
git clone https://github.com/getsentry/self-hosted.git sentry
cd sentry
./install.sh
```

Add to main docker-compose.yml:

```yaml
# docker-compose.yml
services:
  # ... existing services
  
  # Link to Sentry via network
  sentry-postgres:
    image: postgres:15
    # ... Sentry DB config
  
  sentry-redis:
    image: redis:7-alpine
  
  sentry-web:
    image: getsentry/sentry:23.11
    depends_on:
      - sentry-postgres
      - sentry-redis
    ports:
      - "9000:9000"
    environment:
      SENTRY_SECRET_KEY: ${SENTRY_SECRET_KEY}
      SENTRY_POSTGRES_HOST: sentry-postgres
      SENTRY_REDIS_HOST: sentry-redis
```

#### Task 3.2: Integrate Sentry SDK
**Effort**: 3 points  
**Files**: `backend/app/core/sentry.py`

```python
"""
Sentry error tracking configuration.

Captures and reports application errors to Sentry.
"""

import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.celery import CeleryIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
from sentry_sdk.integrations.redis import RedisIntegration

from app.core.config import get_settings


def setup_sentry() -> None:
    """Configure Sentry error tracking."""
    settings = get_settings()
    
    if not settings.SENTRY_DSN:
        return  # Sentry disabled
    
    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        environment=settings.ENVIRONMENT,
        release=f"assemblematic@{settings.APP_VERSION}",
        
        # Performance monitoring
        traces_sample_rate=0.1 if settings.ENVIRONMENT == "production" else 1.0,
        profiles_sample_rate=0.1,
        
        # Integrations
        integrations=[
            FastApiIntegration(),
            CeleryIntegration(),
            SqlalchemyIntegration(),
            RedisIntegration(),
        ],
        
        # Privacy
        send_default_pii=False,
        before_send=filter_sensitive_data,
        
        # Performance
        max_breadcrumbs=50,
    )


def filter_sensitive_data(event: dict, hint: dict) -> dict:
    """Remove sensitive data from Sentry events."""
    # Remove authorization headers
    if 'request' in event:
        headers = event['request'].get('headers', {})
        headers.pop('Authorization', None)
        headers.pop('Cookie', None)
    
    # Scrub sensitive fields from context
    if 'extra' in event:
        sensitive_keys = ['password', 'token', 'secret', 'api_key']
        for key in sensitive_keys:
            event['extra'].pop(key, None)
    
    return event
```

**Acceptance Criteria:**
- ✅ All unhandled exceptions captured
- ✅ User context attached to errors
- ✅ PII filtered from error reports
- ✅ Breadcrumbs show user actions

#### Task 3.3: Configure Error Alerts
**Effort**: 2 points

**Alert Rules:**
1. **New Issue Alert** - Notify on first occurrence
2. **High Error Rate Alert** - >10 errors/minute
3. **Critical Error Alert** - CRITICAL log level
4. **User Impact Alert** - Error affects >10 users

**Notification Channels:**
- Email to engineering team
- Slack #alerts channel
- PagerDuty for critical issues

#### Task 3.4: Create Error Dashboard in Grafana
**Effort**: 2 points

Visualize:
- Error rate over time
- Error breakdown by type
- Most affected users
- Error frequency by release

---

## 4. Integration & Configuration

### Environment Variables

Add to `.env`:

```bash
# ============================================
# Logging & Monitoring
# ============================================

# Elasticsearch
ELASTICSEARCH_HOST=elasticsearch:9200
ELASTICSEARCH_USERNAME=elastic
ELASTICSEARCH_PASSWORD=changeme

# Logstash
LOGSTASH_HOST=logstash:5044

# OpenTelemetry
OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector:4317
OTEL_TRACES_SAMPLER=parentbased_traceidratio
OTEL_TRACES_SAMPLER_ARG=0.1  # 10% sampling

# Sentry
SENTRY_DSN=http://public@sentry-web:9000/1
SENTRY_TRACES_SAMPLE_RATE=0.1

# Prometheus
PROMETHEUS_ENABLED=true
PROMETHEUS_PORT=9090

# Grafana
GRAFANA_ADMIN_PASSWORD=admin
```

### Makefile Targets

Add monitoring commands:

```makefile
# Makefile additions

# ============================================================================
# Monitoring
# ============================================================================

monitoring-up:
	docker compose --profile monitoring up -d

monitoring-down:
	docker compose --profile monitoring down

monitoring-logs:
	docker compose logs -f elasticsearch logstash kibana tempo grafana sentry-web

kibana-open:
	@echo "Opening Kibana..."
	@open http://localhost:5601 || xdg-open http://localhost:5601

grafana-open:
	@echo "Opening Grafana..."
	@open http://localhost:3000 || xdg-open http://localhost:3000

sentry-open:
	@echo "Opening Sentry..."
	@open http://localhost:9000 || xdg-open http://localhost:9000

monitoring-health:
	@echo "Checking monitoring stack health..."
	@curl -s http://localhost:9200/_cluster/health | jq '.status' && echo "✅ Elasticsearch" || echo "❌ Elasticsearch"
	@curl -s http://localhost:5601/api/status | jq '.status.overall.level' && echo "✅ Kibana" || echo "❌ Kibana"
	@curl -s http://localhost:3000/api/health && echo "✅ Grafana" || echo "❌ Grafana"
	@curl -s http://localhost:9000/api/0/organizations/ && echo "✅ Sentry" || echo "❌ Sentry"
```

---

## 5. Testing Plan

### Unit Tests

**Test Coverage:**
- [ ] Structured logging outputs JSON format
- [ ] Request context properly propagated
- [ ] Sensitive data filtered from logs
- [ ] OpenTelemetry spans created correctly
- [ ] Prometheus metrics incremented
- [ ] Sentry captures exceptions

### Integration Tests

- [ ] Logs flow from application → Filebeat → Logstash → Elasticsearch
- [ ] Kibana can query logs
- [ ] Traces visible in Grafana
- [ ] Errors appear in Sentry
- [ ] Alerts triggered correctly

### Load Tests

- [ ] <2% CPU overhead from instrumentation
- [ ] <50ms latency overhead from logging
- [ ] Elasticsearch handles 10K logs/second
- [ ] No memory leaks from tracing

---

## 6. Production Deployment Checklist

### Pre-Deployment

- [ ] All monitoring services tested in staging
- [ ] Resource limits configured
- [ ] Persistent volumes provisioned
- [ ] Backup strategy defined
- [ ] Retention policies set
- [ ] Security hardened (TLS, authentication)

### Kubernetes Manifests

Create in `k8s/monitoring/`:
- [ ] `namespace.yaml` - monitoring namespace
- [ ] `elasticsearch/` - StatefulSet, Service, PVC
- [ ] `logstash/` - Deployment, ConfigMap
- [ ] `kibana/` - Deployment, Service, Ingress
- [ ] `tempo/` - StatefulSet, Service
- [ ] `grafana/` - Deployment, Service, Ingress
- [ ] `sentry/` - Deployment, Service, Ingress
- [ ] `prometheus/` - Deployment, Service
- [ ] `otel-collector/` - Deployment, ConfigMap

### Helm Charts

Consider using official Helm charts:
- `elastic/elasticsearch`
- `elastic/logstash`
- `elastic/kibana`
- `grafana/tempo`
- `grafana/grafana`
- `sentry/sentry`

### Infrastructure Requirements

**Development:**
- CPU: +2 cores
- Memory: +4GB
- Storage: +10GB

**Production:**
- Elasticsearch cluster: 3 nodes, 4GB RAM each, 100GB SSD
- Logstash: 2 nodes, 2GB RAM each
- Tempo: 2 nodes, 2GB RAM each, 50GB SSD
- Grafana: 1 node, 1GB RAM
- Sentry: 3 services (web, worker, cron), 6GB total

**Monthly Cost Estimate (AWS):**
- Elasticsearch (3 x t3.medium): ~$150
- Other services (t3.small): ~$50
- Storage (200GB): ~$40
- **Total: ~$240/month**

---

## 7. Documentation Deliverables

### User Guides

1. **Monitoring Setup Guide** (`docs/operations/monitoring-setup.md`)
   - Installation instructions
   - Configuration options
   - Troubleshooting

2. **Log Query Cookbook** (`docs/operations/log-queries.md`)
   - Common query patterns
   - Kibana tips
   - Performance optimization

3. **Alerting Runbook** (`docs/operations/alerting-runbook.md`)
   - Alert definitions
   - Response procedures
   - Escalation paths

4. **Dashboard Guide** (`docs/operations/dashboards.md`)
   - Dashboard descriptions
   - Key metrics explained
   - When to use which dashboard

### Developer Guides

1. **Structured Logging Best Practices** (`docs/guides/logging-best-practices.md`)
   - When to log
   - Log levels
   - Context enrichment
   - Performance considerations

2. **Tracing Guide** (`docs/guides/distributed-tracing.md`)
   - Manual instrumentation
   - Custom spans
   - Trace analysis

3. **Metrics Guide** (`docs/guides/custom-metrics.md`)
   - Creating custom metrics
   - Metric types
   - Naming conventions

---

## 8. Timeline & Milestones

### Week 1-2: Foundation
- [ ] Update ADR-011
- [ ] Add monitoring services to docker-compose
- [ ] Implement structured logging
- [ ] Create logging middleware

### Week 3-4: ELK Stack
- [ ] Configure Logstash pipelines
- [ ] Set up Elasticsearch indices
- [ ] Create Kibana dashboards
- [ ] Test log ingestion

### Week 5: APM
- [ ] Add OpenTelemetry instrumentation
- [ ] Deploy Tempo
- [ ] Create tracing dashboards
- [ ] Add Prometheus metrics

### Week 6: Exception Monitoring
- [ ] Deploy Sentry
- [ ] Integrate Sentry SDK
- [ ] Configure alerts
- [ ] Test error capture

### Week 7: Testing & Documentation
- [ ] Integration testing
- [ ] Load testing
- [ ] Write documentation
- [ ] Create runbooks

### Week 8: Production Deployment
- [ ] Create Kubernetes manifests
- [ ] Deploy to staging
- [ ] Validate and tune
- [ ] Deploy to production

---

## 9. Success Metrics

### Quantitative
- ✅ 99.9% log capture rate
- ✅ <500ms p99 latency overhead
- ✅ <2% CPU overhead from instrumentation
- ✅ 0 data loss in log pipeline
- ✅ <60s from error occurrence to Sentry notification

### Qualitative
- ✅ Engineers can debug production issues from logs alone
- ✅ Dashboards provide actionable insights
- ✅ Alerting reduces MTTR (Mean Time To Resolution)
- ✅ No false positive alerts

---

## 10. Questions for Product Owner

Please provide answers to guide implementation:

### Scale & Retention
1. **Expected log volume?** (e.g., 1GB/day, 10GB/day, 100GB/day)
2. **Log retention period?** (Development: 3d, Staging: 7d, Production: 30d?)
3. **Trace sampling rate?** (Recommend 10% production, 100% development)

### Operations
4. **On-call rotation?** Do we have one, or need to set up?
5. **Alerting channels?** (Slack, PagerDuty, email, Discord?)
6. **Incident response SLA?** (e.g., critical: 15min, high: 1hr)

### Compliance & Security
7. **PII in logs?** Should we automatically redact certain fields?
8. **Compliance requirements?** (HIPAA, GDPR, SOC2?)
9. **Log audit trail?** Need immutable logs for compliance?

### Budget & Infrastructure
10. **Budget constraints?** Maximum monthly cost for monitoring?
11. **Cloud provider?** AWS, GCP, Azure, or self-hosted?
12. **Shared services?** Can we use existing Elasticsearch/Prometheus?

### Prioritization
13. **What's most critical?** Logs, APM, or exception monitoring?
14. **Deployment timeline?** Need all in 4 weeks, or can phase?
15. **Production first?** Or develop/test locally before prod deployment?

---

## Appendix A: OSS Tool Comparison

### Logging Solutions

| Tool | Pros | Cons | Score |
|------|------|------|-------|
| **ELK Stack** | Industry standard, powerful | Resource heavy | ⭐⭐⭐⭐⭐ |
| Loki (Grafana) | Lightweight, cost-effective | Less powerful queries | ⭐⭐⭐⭐ |
| OpenSearch | AWS fork of Elasticsearch | Less ecosystem | ⭐⭐⭐⭐ |

### APM Solutions

| Tool | Pros | Cons | Score |
|------|------|------|-------|
| **OpenTelemetry + Tempo** | Vendor-neutral, efficient | Newer | ⭐⭐⭐⭐⭐ |
| Jaeger | Mature, CNCF graduated | More complex | ⭐⭐⭐⭐ |
| Zipkin | Simple, battle-tested | Less features | ⭐⭐⭐ |

### Exception Monitoring

| Tool | Pros | Cons | Score |
|------|------|------|-------|
| **Sentry OSS** | Best-in-class, self-hosted | Resource hungry | ⭐⭐⭐⭐⭐ |
| GlitchTip | Sentry-compatible, simpler | Less mature | ⭐⭐⭐⭐ |
| Rollbar OSS | Good features | Limited OSS | ⭐⭐⭐ |

---

## Appendix B: References

### Documentation
- [Elasticsearch Documentation](https://www.elastic.co/guide/en/elasticsearch/reference/current/index.html)
- [Logstash Configuration](https://www.elastic.co/guide/en/logstash/current/configuration.html)
- [Kibana User Guide](https://www.elastic.co/guide/en/kibana/current/index.html)
- [OpenTelemetry Python](https://opentelemetry.io/docs/instrumentation/python/)
- [Grafana Tempo](https://grafana.com/docs/tempo/latest/)
- [Sentry Self-Hosted](https://develop.sentry.dev/self-hosted/)

### Best Practices
- [12-Factor App: Logs](https://12factor.net/logs)
- [Google SRE Book: Monitoring Distributed Systems](https://sre.google/sre-book/monitoring-distributed-systems/)
- [Structured Logging Best Practices](https://stackify.com/what-is-structured-logging-and-why-developers-need-it/)

---

**Document Version**: 1.0  
**Last Updated**: 2024-02-04  
**Author**: Strategy & Design Agent  
**Status**: Ready for Review
