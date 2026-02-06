# Prometheus Metrics

The AI Part Designer application exposes Prometheus metrics at the `/metrics` endpoint for monitoring application health, performance, and business KPIs.

## Metrics Endpoint

**URL:** `GET /metrics`

**Format:** Prometheus text format

**Example:**
```bash
curl http://localhost:8000/metrics
```

## Available Metrics

### HTTP Request Metrics (Default)

These metrics are automatically collected for all HTTP requests:

- `http_requests_total` - Total number of HTTP requests by method, status, and handler
- `http_request_duration_seconds` - Request latency histogram
- `http_request_size_bytes` - Request size histogram
- `http_response_size_bytes` - Response size histogram
- `http_requests_inprogress` - Number of requests currently being processed

### CAD Generation Metrics

- `cad_generations_total{status, template_type}` - Total number of CAD model generations
- `cad_generation_duration_seconds{template_type}` - Time spent generating CAD models (histogram)

**Usage:**
```python
from app.core.metrics import cad_generations_total, cad_generation_duration

# Increment counter
cad_generations_total.labels(status="success", template_type="box").inc()

# Record duration
with cad_generation_duration.labels(template_type="box").time():
    # Generate CAD model
    pass
```

### Export Metrics

- `exports_total{format, status}` - Total number of file exports
- `export_duration_seconds{format}` - Time spent exporting files (histogram)

**Usage:**
```python
from app.core.metrics import exports_total, export_duration

exports_total.labels(format="stl", status="success").inc()

with export_duration.labels(format="stl").time():
    # Export file
    pass
```

### AI Provider Metrics

- `ai_requests_total{provider, model, status}` - Total number of AI API requests
- `ai_request_duration_seconds{provider, model}` - Time spent on AI API requests
- `ai_tokens_used_total{provider, model, token_type}` - Total AI tokens consumed

**Usage:**
```python
from app.core.metrics import ai_requests_total, ai_request_duration, ai_tokens_used

ai_requests_total.labels(provider="anthropic", model="claude-3", status="success").inc()
ai_tokens_used.labels(provider="anthropic", model="claude-3", token_type="input").inc(150)
ai_tokens_used.labels(provider="anthropic", model="claude-3", token_type="output").inc(85)
```

### User Activity Metrics

- `user_registrations_total{method}` - Total number of user registrations
- `user_logins_total{method, status}` - Total number of user logins

**Usage:**
```python
from app.core.metrics import user_registrations_total, user_logins_total

user_registrations_total.labels(method="email").inc()
user_logins_total.labels(method="email", status="success").inc()
```

### Design Metrics

- `designs_created_total{template_type}` - Total number of designs created
- `designs_shared_total` - Total number of designs shared

### Database Connection Pool Metrics

- `db_pool_size` - Current database connection pool size
- `db_pool_checked_out_connections` - Number of connections currently checked out
- `db_pool_overflow_connections` - Number of connections in the overflow pool
- `db_pool_checkedin_connections` - Number of connections checked into the pool

These metrics are collected periodically by calling:
```python
from app.core.metrics import collect_db_pool_metrics

await collect_db_pool_metrics()
```

### Redis Metrics

- `redis_connected` - Whether Redis is connected (1) or not (0)
- `redis_commands_total{command, status}` - Total number of Redis commands executed
- `redis_command_duration_seconds{command}` - Time spent executing Redis commands
- `redis_connection_errors_total` - Total number of Redis connection errors

Redis connection status is collected periodically by calling:
```python
from app.core.metrics import collect_redis_metrics

await collect_redis_metrics()
```

## Prometheus Configuration

Example Prometheus scrape configuration:

```yaml
scrape_configs:
  - job_name: 'ai-part-designer'
    scrape_interval: 15s
    static_configs:
      - targets: ['localhost:8000']
    metrics_path: '/metrics'
```

## Grafana Dashboard

Key queries for building dashboards:

**Request Rate:**
```promql
rate(http_requests_total[5m])
```

**Request Latency (p95):**
```promql
histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))
```

**Error Rate:**
```promql
rate(http_requests_total{status=~"5.."}[5m]) / rate(http_requests_total[5m])
```

**CAD Generations per Minute:**
```promql
rate(cad_generations_total[1m]) * 60
```

**AI Token Usage per Hour:**
```promql
rate(ai_tokens_used_total[1h]) * 3600
```

**Database Connection Pool Utilization:**
```promql
db_pool_checked_out_connections / db_pool_size
```

## Monitoring Best Practices

1. **Set up alerts** for:
   - High error rates (>1% of requests returning 5xx)
   - High latency (p95 > 1s for critical endpoints)
   - Database connection pool exhaustion (>90% utilization)
   - Redis connection failures

2. **Track business KPIs**:
   - Daily CAD generations
   - Export success rate
   - User registration trends
   - AI token consumption (for cost monitoring)

3. **Monitor resource usage**:
   - Database connection pool metrics
   - Redis health
   - Request throughput and latency

4. **Excluded endpoints**: The following endpoints are excluded from HTTP metrics to reduce noise:
   - `/metrics` (the metrics endpoint itself)
   - `/health` (health checks)
   - `/docs`, `/redoc`, `/openapi.json` (API documentation)
