# Monitoring & Logging Quick Start Guide

This guide helps you get up and running with the AssemblematicAI monitoring stack in under 10 minutes.

## Table of Contents

- [Local Development Setup](#local-development-setup)
- [Accessing Monitoring Dashboards](#accessing-monitoring-dashboards)
- [Querying Logs](#querying-logs)
- [Viewing Traces](#viewing-traces)
- [Checking Errors](#checking-errors)
- [Common Tasks](#common-tasks)

---

## Local Development Setup

### Prerequisites

- Docker and Docker Compose installed
- At least 8GB RAM available for Docker
- 10GB free disk space

### Start Monitoring Stack

```bash
# Start all services including monitoring
make dev

# Or start monitoring separately
make monitoring-up
```

This starts:
- **Elasticsearch** (port 9200) - Log storage
- **Kibana** (port 5601) - Log exploration
- **Logstash** (port 5044) - Log processing
- **Tempo** (port 3200) - Trace storage
- **Grafana** (port 3000) - Metrics & trace visualization
- **Prometheus** (port 9090) - Metrics collection
- **Sentry** (port 9000) - Error tracking

### Verify Services are Running

```bash
# Check health of all monitoring services
make monitoring-health

# View logs
make monitoring-logs
```

Expected output:
```
✅ Elasticsearch - green
✅ Kibana - available
✅ Grafana - healthy
✅ Sentry - operational
```

---

## Accessing Monitoring Dashboards

### Kibana (Logs)

```bash
make kibana-open
# Or visit: http://localhost:5601
```

**First Time Setup:**
1. Go to "Stack Management" → "Index Patterns"
2. Create pattern: `logs-*`
3. Select timestamp field: `@timestamp`
4. Go to "Discover" to explore logs

### Grafana (Metrics & Traces)

```bash
make grafana-open
# Or visit: http://localhost:3000
```

**Default credentials:**
- Username: `admin`
- Password: `admin` (change on first login)

**Pre-configured dashboards:**
- API Performance
- System Health
- Distributed Traces
- Error Rates

### Sentry (Errors)

```bash
make sentry-open
# Or visit: http://localhost:9000
```

**First Time Setup:**
1. Create an admin account
2. Create a project: "AssemblematicAI - API"
3. Copy the DSN to `.env` file
4. Restart services

---

## Querying Logs

### Finding Logs by Request ID

In Kibana Discover:
```
request_id: "req-123e4567-e89b-12d3-a456-426614174000"
```

### Finding All Errors

```
level: ERROR OR level: CRITICAL
```

### Finding Slow Requests (>1 second)

```
duration_ms > 1000 AND path: "/api/v1/designs"
```

### Finding Logs for Specific User

```
user_id: "usr-987654321"
```

### Complex Query: Failed Design Generations

```
logger: "app.services.design" AND level: ERROR AND message: *"generation failed"*
```

### Aggregations

**Error rate over time:**
1. Go to Kibana → Analytics → Dashboard
2. Create visualization: "Vertical Bar"
3. Y-axis: Count
4. X-axis: Date Histogram on `@timestamp`
5. Filter: `level: ERROR`

**Top error messages:**
1. Create visualization: "Data Table"
2. Rows: Terms aggregation on `message.keyword`
3. Metrics: Count
4. Order: Descending

---

## Viewing Traces

### In Grafana

1. Go to **Explore** (compass icon in sidebar)
2. Select data source: **Tempo**
3. Query by:
   - **Trace ID**: `abc123def456`
   - **Service**: `assemblematic-api`
   - **Operation**: `POST /api/v1/designs`

### Understanding Traces

**Span Hierarchy:**
```
HTTP Request (100ms)
├── Database Query: Get Template (10ms)
├── Redis: Check Cache (2ms)
├── AI Generation (60ms)
│   ├── OpenAI API Call (55ms)
│   └── Response Parsing (5ms)
├── CAD Generation (20ms)
└── S3 Upload (8ms)
```

**Key Metrics:**
- **Duration**: Total time for operation
- **Start Time**: When operation began
- **Tags**: Metadata (user_id, design_id, etc.)
- **Events**: Important moments in span lifecycle

### Finding Slow Traces

1. In Grafana Explore
2. Select Tempo data source
3. Use query: `{ service.name="assemblematic-api" } | duration > 1s`

---

## Checking Errors

### In Sentry

**Dashboard shows:**
- New issues in last 24h
- Error trend graph
- Most affected users
- Release health

**Viewing an Error:**
1. Click on error from list
2. See:
   - Stack trace with highlighted code
   - Breadcrumbs (user actions before error)
   - Environment (OS, Python version, etc.)
   - Tags (user_id, endpoint, etc.)

**Useful Filters:**
- **Unresolved**: Only show active errors
- **Assigned to me**: Errors you're responsible for
- **Release**: Filter by version

### Error Alerts

Configure in Sentry → Alerts:
```yaml
Name: Critical Errors
Conditions:
  - Error level is "fatal" or "critical"
  - Occurs more than 1 times in 5 minutes
Actions:
  - Send email to engineering@assemblematic.ai
  - Post to Slack #alerts
```

---

## Common Tasks

### 1. Debug a Failed Request

**Step 1: Find the error in Sentry**
- Note the `request_id` from error context

**Step 2: Search logs in Kibana**
```
request_id: "req-xxxxx"
```
- See all logs for that request
- Check for warnings before the error

**Step 3: View trace in Grafana**
```
trace_id: "trace-xxxxx"
```
- See which operation took longest
- Identify bottlenecks

### 2. Investigate High Latency

**In Grafana:**
1. Open "API Performance" dashboard
2. Check "P99 Latency" panel
3. Look for spikes
4. Click spike → "Explore" → View traces from that time

**In Kibana:**
```
duration_ms > 5000
```
- Find slowest requests
- Group by endpoint to find problematic routes

### 3. Monitor Database Performance

**In Grafana:**
1. Open "Database Health" dashboard
2. Check:
   - Connection pool usage
   - Query duration (P95, P99)
   - Slow queries (>100ms)

**In Kibana:**
```
logger: "sqlalchemy.engine" AND duration_ms > 100
```

### 4. Track User Journey

**In Kibana:**
```
user_id: "usr-123" AND timestamp: [now-1h TO now]
```
- Sort by timestamp ascending
- See all actions user performed
- Identify where they got stuck

### 5. Find Memory Leaks

**In Grafana:**
1. Open "System Health" dashboard
2. Check "Memory Usage" over 24h
3. Look for steady increase (not normal sawtooth pattern)

**In Prometheus (port 9090):**
```promql
process_resident_memory_bytes{service="api"}
```

---

## Best Practices

### Logging

✅ **DO:**
- Use structured logging with context
- Include `request_id` in all logs within request
- Log at appropriate level (DEBUG/INFO/WARNING/ERROR)
- Add business context (user_id, design_id, etc.)

❌ **DON'T:**
- Log sensitive data (passwords, tokens, PII)
- Log at DEBUG level in production
- Use string concatenation in log messages
- Log the same event multiple times

**Example:**
```python
from app.core.logging import get_logger, log_with_context

logger = get_logger(__name__)

# ✅ Good
log_with_context(
    logger, "info",
    "Design created successfully",
    design_id=str(design.id),
    template=design.template,
    user_tier=user.tier,
    duration_ms=123
)

# ❌ Bad
logger.info(f"Design {design.id} created by {user.email}")
```

### Tracing

✅ **DO:**
- Use auto-instrumentation where available
- Add custom spans for business logic
- Include relevant tags (user_id, operation_type)
- Set span status (ok, error)

❌ **DON'T:**
- Create too many spans (overhead)
- Log in every span (use events instead)
- Ignore trace context propagation

**Example:**
```python
from app.core.telemetry import get_tracer

tracer = get_tracer(__name__)

# ✅ Good
with tracer.start_as_current_span("cad_generation") as span:
    span.set_attribute("template", template_name)
    span.set_attribute("complexity", "high")
    
    result = generate_cad(params)
    
    span.set_attribute("vertex_count", result.vertices)
    span.set_status(Status(StatusCode.OK))
```

### Metrics

✅ **DO:**
- Use descriptive metric names
- Add useful labels (but not too many)
- Use appropriate metric types (Counter, Gauge, Histogram)
- Document custom metrics

❌ **DON'T:**
- Create high-cardinality labels (user_id, request_id)
- Update metrics synchronously in critical path
- Forget to increment error counters

### Error Tracking

✅ **DO:**
- Capture errors with context
- Tag errors appropriately
- Mark errors as resolved when fixed
- Set up useful alerts

❌ **DON'T:**
- Capture the same error multiple times
- Log and capture error (creates noise)
- Ignore errors that "never happen"

---

## Troubleshooting

### Elasticsearch is slow

```bash
# Check cluster health
curl http://localhost:9200/_cluster/health?pretty

# Check indices
curl http://localhost:9200/_cat/indices?v

# Clear old indices (if needed)
curl -X DELETE http://localhost:9200/logs-*-2024.01.*
```

### Logs not appearing in Kibana

1. **Check Filebeat is running:**
   ```bash
   docker ps | grep filebeat
   docker logs ai-part-designer-filebeat
   ```

2. **Check Logstash is processing:**
   ```bash
   docker logs ai-part-designer-logstash
   ```

3. **Verify index pattern in Kibana:**
   - Stack Management → Index Patterns
   - Should see `logs-*` with documents

### Traces not appearing in Grafana

1. **Check OTEL Collector:**
   ```bash
   docker logs ai-part-designer-otel-collector
   ```

2. **Verify instrumentation:**
   ```python
   # In app code, check tracer is initialized
   from opentelemetry import trace
   print(trace.get_tracer_provider())
   ```

3. **Check Tempo data source in Grafana:**
   - Configuration → Data Sources → Tempo
   - Click "Test" - should see "Data source is working"

### Sentry not capturing errors

1. **Verify DSN is set:**
   ```bash
   echo $SENTRY_DSN
   ```

2. **Test error capture:**
   ```python
   import sentry_sdk
   sentry_sdk.capture_message("Test error")
   ```

3. **Check Sentry logs:**
   ```bash
   docker logs ai-part-designer-sentry-web
   ```

---

## Additional Resources

- [Full Implementation Specification](../architecture/monitoring-logging-implementation.md)
- [ADR-011: Monitoring and Observability](../adrs/adr-011-monitoring-observability.md)
- [Elasticsearch Query DSL](https://www.elastic.co/guide/en/elasticsearch/reference/current/query-dsl.html)
- [Grafana Documentation](https://grafana.com/docs/grafana/latest/)
- [OpenTelemetry Python](https://opentelemetry.io/docs/instrumentation/python/)
- [Sentry Documentation](https://docs.sentry.io/)

---

## Getting Help

- **Internal Wiki**: [monitoring wiki page link]
- **Slack Channel**: `#observability`
- **On-call**: `@oncall-engineering` in Slack
- **Runbooks**: `/docs/operations/runbooks/`

---

**Last Updated**: 2024-02-04  
**Maintained by**: Platform Team
