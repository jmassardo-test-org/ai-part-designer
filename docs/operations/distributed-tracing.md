# OpenTelemetry Distributed Tracing

## Overview

This document describes the OpenTelemetry distributed tracing implementation for the AI Part Designer platform. Distributed tracing enables debugging of cross-service issues by providing visibility into the full request path with timing information for each operation.

## Architecture

The tracing system uses **OpenTelemetry** with **Jaeger** as the backend for trace collection, storage, and visualization.

```
┌──────────────────────────────────────────────────────────────────┐
│                     AI Part Designer API                         │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  OpenTelemetry Instrumentation                          │    │
│  │  ├── FastAPI requests (HTTP traces)                     │    │
│  │  ├── Database queries (SQLAlchemy)                      │    │
│  │  ├── Cache operations (Redis)                           │    │
│  │  ├── External API calls (httpx)                         │    │
│  │  └── Custom spans for business logic                    │    │
│  └────────────────────────┬────────────────────────────────┘    │
└───────────────────────────┼─────────────────────────────────────┘
                            │
                            │ Export traces
                            ▼
                ┌──────────────────────┐
                │   Jaeger Collector   │
                │   (UDP port 6831)    │
                │   (gRPC port 14250)  │
                │   (OTLP port 4317)   │
                └──────────┬───────────┘
                           │
                           │ Store traces
                           ▼
                ┌──────────────────────┐
                │  Jaeger Storage      │
                │  (Memory/Cassandra)  │
                └──────────┬───────────┘
                           │
                           │ Query traces
                           ▼
                ┌──────────────────────┐
                │   Jaeger UI          │
                │   (Port 16686)       │
                └──────────────────────┘
```

## Components

### 1. OpenTelemetry SDK (`app/core/tracing.py`)

The core tracing module provides:
- **TracerProvider configuration** with service metadata
- **Automatic instrumentation** for FastAPI, SQLAlchemy, Redis, and httpx
- **Exporter configuration** for Jaeger and OTLP
- **Manual span creation** for custom business logic

### 2. Jaeger Backend

Jaeger provides:
- **Trace collection** via UDP (Thrift), gRPC, or OTLP protocols
- **Trace storage** in-memory (development) or persistent (production)
- **Web UI** for trace visualization and analysis
- **Service dependency graphs** showing call relationships

## Configuration

### Environment Variables

Configure tracing via these environment variables:

```bash
# Enable/disable tracing
TRACING_ENABLED=true

# Jaeger connection (primary method)
JAEGER_HOST=localhost
JAEGER_PORT=6831

# OTLP endpoint (fallback)
OTLP_ENDPOINT=http://localhost:4317

# Service identification
APP_NAME=AssemblematicAI
APP_VERSION=0.1.0
ENVIRONMENT=production
```

### Configuration in Code

Tracing is configured in `app/core/config.py`:

```python
class Settings(BaseSettings):
    # Tracing configuration
    TRACING_ENABLED: bool = True
    JAEGER_HOST: str = "localhost"
    JAEGER_PORT: int = 6831
    OTLP_ENDPOINT: str = "http://localhost:4317"
```

## Instrumentation

### Automatic Instrumentation

The following libraries are automatically instrumented:

#### 1. FastAPI (HTTP Requests)
```python
# In app/main.py
from app.core.tracing import instrument_fastapi

app = FastAPI(...)
instrument_fastapi(app)  # Traces all HTTP requests
```

**Captured data:**
- HTTP method and path
- Request headers (configurable)
- Response status code
- Request duration
- Span name: `{method} {path}`

#### 2. SQLAlchemy (Database)
```python
# In app/main.py lifespan
from app.core.tracing import instrument_database
from app.core.database import engine

await init_db()
instrument_database(engine)  # Traces all DB queries
```

**Captured data:**
- SQL statement (sanitized)
- Query duration
- Connection pool metrics
- Span name: SQL operation (SELECT, INSERT, etc.)

#### 3. Redis (Cache)
```python
# In app/main.py lifespan
from app.core.tracing import instrument_redis

await redis_client.connect()
instrument_redis()  # Traces all Redis commands
```

**Captured data:**
- Redis command name
- Command duration
- Span name: Redis command (GET, SET, etc.)

#### 4. httpx (External APIs)
```python
# In app/main.py lifespan
from app.core.tracing import instrument_httpx

instrument_httpx()  # Traces all httpx requests
```

**Captured data:**
- HTTP method and URL
- Request/response headers
- Response status code
- Request duration
- **Context propagation** to external services

### Manual Instrumentation

For custom business logic, create spans manually:

```python
from app.core.tracing import get_tracer

tracer = get_tracer(__name__)

async def generate_cad_model(design_id: UUID) -> CADModel:
    # Create a span for this operation
    with tracer.start_as_current_span("generate_cad_model") as span:
        # Add custom attributes
        span.set_attribute("design.id", str(design_id))
        span.set_attribute("design.type", "enclosure")
        
        # Your business logic
        result = await cad_service.generate(design_id)
        
        # Add result metadata
        span.set_attribute("model.vertices", result.vertex_count)
        span.set_attribute("model.size_kb", result.size / 1024)
        
        return result
```

**Best practices for manual spans:**
- Use descriptive span names (operation names)
- Add relevant attributes for filtering/analysis
- Keep span granularity appropriate (not too fine)
- Set span status on errors: `span.set_status(Status(StatusCode.ERROR))`

## Deployment

### Development (Local)

Start Jaeger with Docker Compose:

```bash
# Start observability stack with Jaeger
docker compose -f docker-compose.yml \
  -f docker-compose.observability.yml \
  --profile observability up -d

# Verify Jaeger is running
docker ps | grep jaeger

# Access Jaeger UI
open http://localhost:16686
```

Start your application:

```bash
# Tracing is enabled by default
docker compose up -d

# Or with environment variables
TRACING_ENABLED=true \
JAEGER_HOST=localhost \
JAEGER_PORT=6831 \
uvicorn app.main:app --reload
```

### Production (Kubernetes)

#### Option 1: Jaeger Operator

Install Jaeger via the Jaeger Operator:

```bash
# Install Jaeger Operator
kubectl create namespace observability
kubectl create -f https://github.com/jaegertracing/jaeger-operator/releases/download/v1.52.0/jaeger-operator.yaml -n observability

# Deploy Jaeger instance
kubectl apply -f k8s/base/jaeger.yaml
```

**k8s/base/jaeger.yaml:**
```yaml
apiVersion: jaegertracing.io/v1
kind: Jaeger
metadata:
  name: ai-part-designer
  namespace: observability
spec:
  strategy: production
  storage:
    type: cassandra
    options:
      cassandra:
        servers: cassandra.observability.svc.cluster.local
        keyspace: jaeger_v1_production
  collector:
    resources:
      limits:
        cpu: 1000m
        memory: 1Gi
  query:
    resources:
      limits:
        cpu: 500m
        memory: 512Mi
```

Update application configuration:

```yaml
# k8s/base/backend-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: backend
spec:
  template:
    spec:
      containers:
      - name: backend
        env:
        - name: TRACING_ENABLED
          value: "true"
        - name: JAEGER_HOST
          value: "ai-part-designer-collector.observability.svc.cluster.local"
        - name: JAEGER_PORT
          value: "6831"
```

#### Option 2: OTLP Endpoint

Use OpenTelemetry Collector with OTLP:

```yaml
# k8s/base/backend-deployment.yaml
- name: TRACING_ENABLED
  value: "true"
- name: OTLP_ENDPOINT
  value: "http://otel-collector.observability.svc.cluster.local:4317"
```

## Usage

### Viewing Traces

1. **Access Jaeger UI**: http://localhost:16686 (development)

2. **Search for traces:**
   - Select service: `AssemblematicAI`
   - Choose operation: e.g., `POST /api/v1/designs`
   - Set time range
   - Click "Find Traces"

3. **Analyze a trace:**
   - Click on a trace to see the timeline
   - View span details (tags, logs, process info)
   - Inspect error spans (marked in red)
   - Check service dependencies

### Common Trace Patterns

#### Successful Request
```
HTTP POST /api/v1/designs                    [200ms]
├── SELECT user WHERE id=?                   [5ms]
├── Redis GET design:cache:user:123          [2ms]
├── generate_cad_model                       [180ms]
│   ├── SELECT template WHERE id=?           [3ms]
│   ├── compile_cad_code                     [150ms]
│   └── INSERT design ...                    [10ms]
└── Redis SET design:cache:design:456        [3ms]
```

#### Error Scenario
```
HTTP POST /api/v1/designs                    [150ms] ❌
├── SELECT user WHERE id=?                   [5ms]
├── generate_cad_model                       [140ms] ❌
│   ├── SELECT template WHERE id=?           [3ms]
│   └── compile_cad_code                     [130ms] ❌
│       └── ERROR: CadQuery compilation failed
```

### Debugging with Traces

#### 1. Identify Slow Requests
- Sort traces by duration
- Look for outliers (> 2σ from mean)
- Drill down to find slow spans

#### 2. Trace Errors
- Filter traces by error status
- Check error span attributes for details
- Follow the error propagation chain

#### 3. Analyze Dependencies
- View the service dependency graph
- Identify chatty calls (N+1 queries)
- Find circular dependencies

#### 4. Monitor SLOs
- Track p95/p99 latencies per endpoint
- Set alerts on trace error rate
- Monitor trace sampling rate

## Trace Context Propagation

OpenTelemetry automatically propagates trace context across service boundaries using standard headers:

### W3C Trace Context (Default)
```http
traceparent: 00-{trace-id}-{span-id}-{flags}
tracestate: vendor=state
```

### HTTP Client Example
```python
import httpx
from app.core.tracing import get_tracer

async def call_external_api():
    # Context is automatically propagated
    async with httpx.AsyncClient() as client:
        response = await client.get("https://api.external.com/data")
        # External service will see the same trace ID
```

## Performance Considerations

### Sampling

For high-traffic production systems, use sampling:

```python
# In app/core/tracing.py
from opentelemetry.sdk.trace.sampling import ParentBasedTraceIdRatioBased

# Sample 10% of traces
sampler = ParentBasedTraceIdRatioBased(0.1)
provider = TracerProvider(resource=resource, sampler=sampler)
```

### Overhead

Tracing adds minimal overhead:
- **CPU**: < 1% for typical workloads
- **Memory**: ~10MB per 1000 spans in flight
- **Network**: ~1KB per span exported
- **Latency**: < 1ms per span creation

### Best Practices

1. **Use sampling in production** (1-10% trace rate)
2. **Set span attribute limits** to avoid memory issues
3. **Export in batches** (default: every 5s or 512 spans)
4. **Monitor exporter health** (queue size, drop rate)
5. **Set trace retention** based on storage capacity

## Troubleshooting

### Tracing Not Working

**Check configuration:**
```bash
# Verify tracing is enabled
curl http://localhost:8000/api/v1/health | jq .tracing

# Check environment variables
docker exec backend env | grep TRACING
```

**Check Jaeger connectivity:**
```bash
# Test UDP port
nc -zu localhost 6831

# Test gRPC port
grpcurl -plaintext localhost:14250 list

# Check Jaeger health
curl http://localhost:14269/
```

**Check application logs:**
```bash
# Look for tracing initialization
docker logs backend | grep tracing

# Expected output:
# {"event": "tracing_initialized", "exporter": "jaeger", ...}
```

### Traces Not Appearing in Jaeger

1. **Check exporter status:**
   - Look for export errors in logs
   - Verify network connectivity to Jaeger

2. **Check sampling:**
   - Verify traces are being sampled
   - Temporarily set sampling to 100%

3. **Check time synchronization:**
   - Jaeger requires synchronized clocks
   - Verify NTP is configured

4. **Check Jaeger storage:**
   - Verify storage backend is healthy
   - Check storage capacity

### High Trace Volume

**Symptoms:**
- Jaeger UI slow or unresponsive
- High memory usage in collector
- Dropped traces

**Solutions:**
1. **Reduce sampling rate** to 1-5%
2. **Exclude health check endpoints** from tracing
3. **Use tail-based sampling** for errors
4. **Scale Jaeger collector** horizontally

## Metrics

Monitor tracing health with these metrics:

```python
# Exposed on /metrics endpoint
otel_traces_exported_total{exporter="jaeger"}
otel_traces_dropped_total{reason="queue_full"}
otel_trace_exporter_queue_size
otel_span_processor_batch_size
```

## Security

### Sensitive Data

**Do not include sensitive data in spans:**
- Passwords, API keys, tokens
- PII (email, phone, SSN)
- Credit card numbers
- Session IDs

**Sanitize span attributes:**
```python
span.set_attribute("user.email", sanitize_email(user.email))  # user@***.com
span.set_attribute("api.key", "[REDACTED]")
```

### Access Control

Restrict Jaeger UI access:
- Use Kubernetes NetworkPolicies
- Add authentication (OAuth2, OIDC)
- Expose via ingress with TLS

## References

- [OpenTelemetry Python Documentation](https://opentelemetry-python.readthedocs.io/)
- [Jaeger Documentation](https://www.jaegertracing.io/docs/)
- [W3C Trace Context](https://www.w3.org/TR/trace-context/)
- [OTLP Specification](https://github.com/open-telemetry/opentelemetry-specification/blob/main/specification/protocol/otlp.md)

## Related Documentation

- [Monitoring & Alerting](monitoring-alerting.md) - Metrics and alerting setup
- [ELK Stack Setup](elk-stack-setup.md) - Centralized logging
- [ADR-011: Monitoring & Observability](../adrs/adr-011-monitoring-observability.md) - Architecture decision
