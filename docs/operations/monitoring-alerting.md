# Monitoring & Alerting Configuration

## AI Part Designer - Production Monitoring

**Version:** 1.0.0  
**Last Updated:** January 26, 2026

---

## Overview

This document describes the monitoring and alerting setup for the AI Part Designer platform. We use a combination of tools to ensure visibility into application health, performance, and business metrics.

---

## Monitoring Stack

| Component | Tool | Purpose |
|-----------|------|---------|
| Error Tracking | Sentry | Exception tracking and debugging |
| APM | Sentry Performance | Transaction tracing and performance |
| Logs | Structured JSON logging | Application logs |
| Metrics | Prometheus | System and application metrics |
| Dashboards | Grafana | Visualization and alerting |
| Uptime | UptimeRobot / Pingdom | External availability monitoring |

---

## Sentry Configuration

### Backend Setup

```python
# backend/app/core/monitoring.py

import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
from sentry_sdk.integrations.celery import CeleryIntegration
from sentry_sdk.integrations.redis import RedisIntegration

def init_sentry(dsn: str, environment: str):
    """Initialize Sentry SDK for error and performance monitoring."""
    sentry_sdk.init(
        dsn=dsn,
        environment=environment,
        integrations=[
            FastApiIntegration(transaction_style="endpoint"),
            SqlalchemyIntegration(),
            CeleryIntegration(),
            RedisIntegration(),
        ],
        traces_sample_rate=0.1,  # 10% of transactions
        profiles_sample_rate=0.1,  # 10% of profiles
        send_default_pii=False,
        before_send=filter_sensitive_data,
    )

def filter_sensitive_data(event, hint):
    """Filter sensitive data before sending to Sentry."""
    if "request" in event and "data" in event["request"]:
        data = event["request"]["data"]
        if isinstance(data, dict):
            # Mask sensitive fields
            for field in ["password", "credit_card", "ssn", "api_key"]:
                if field in data:
                    data[field] = "[FILTERED]"
    return event
```

### Frontend Setup

```typescript
// frontend/src/lib/sentry.ts

import * as Sentry from "@sentry/react";

export function initSentry() {
  Sentry.init({
    dsn: import.meta.env.VITE_SENTRY_DSN,
    environment: import.meta.env.VITE_ENVIRONMENT,
    integrations: [
      new Sentry.BrowserTracing({
        tracePropagationTargets: ["localhost", /^https:\/\/api\.aipartdesigner\.com/],
      }),
      new Sentry.Replay({
        maskAllText: true,
        blockAllMedia: true,
      }),
    ],
    tracesSampleRate: 0.1,
    replaysSessionSampleRate: 0.1,
    replaysOnErrorSampleRate: 1.0,
  });
}
```

---

## Prometheus Metrics

### Application Metrics

```python
# backend/app/core/metrics.py

from prometheus_client import Counter, Histogram, Gauge, generate_latest

# Request metrics
http_requests_total = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status"]
)

http_request_duration_seconds = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration",
    ["method", "endpoint"],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
)

# Business metrics
active_users = Gauge(
    "active_users",
    "Number of active users (last 24h)"
)

designs_generated_total = Counter(
    "designs_generated_total",
    "Total designs generated",
    ["tier", "status"]
)

jobs_in_queue = Gauge(
    "jobs_in_queue",
    "Number of jobs currently in queue",
    ["queue"]
)

# Payment metrics
payments_total = Counter(
    "payments_total",
    "Total payment transactions",
    ["tier", "status"]
)

subscription_mrr = Gauge(
    "subscription_mrr",
    "Monthly recurring revenue",
    ["tier"]
)

# WebSocket metrics
websocket_connections = Gauge(
    "websocket_connections",
    "Active WebSocket connections"
)

# AI metrics
ai_generation_duration_seconds = Histogram(
    "ai_generation_duration_seconds",
    "AI generation duration",
    ["model"],
    buckets=[5, 10, 30, 60, 120, 300]
)

openai_tokens_used = Counter(
    "openai_tokens_used",
    "OpenAI tokens consumed",
    ["model", "type"]
)
```

### Metrics Endpoint

```python
# backend/app/api/v1/metrics.py

from fastapi import APIRouter, Response
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

router = APIRouter()

@router.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint."""
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST
    )
```

---

## Grafana Dashboards

### Application Overview Dashboard

```json
{
  "title": "AI Part Designer - Application Overview",
  "panels": [
    {
      "title": "Request Rate",
      "type": "graph",
      "targets": [
        {
          "expr": "rate(http_requests_total[5m])",
          "legendFormat": "{{method}} {{endpoint}}"
        }
      ]
    },
    {
      "title": "Response Time (p95)",
      "type": "graph",
      "targets": [
        {
          "expr": "histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))",
          "legendFormat": "{{endpoint}}"
        }
      ]
    },
    {
      "title": "Error Rate",
      "type": "stat",
      "targets": [
        {
          "expr": "sum(rate(http_requests_total{status=~\"5..\"}[5m])) / sum(rate(http_requests_total[5m])) * 100"
        }
      ]
    },
    {
      "title": "Active WebSocket Connections",
      "type": "stat",
      "targets": [
        {
          "expr": "websocket_connections"
        }
      ]
    }
  ]
}
```

### Business Metrics Dashboard

```json
{
  "title": "AI Part Designer - Business Metrics",
  "panels": [
    {
      "title": "Designs Generated (24h)",
      "type": "stat",
      "targets": [
        {
          "expr": "increase(designs_generated_total[24h])"
        }
      ]
    },
    {
      "title": "Active Users (24h)",
      "type": "stat",
      "targets": [
        {
          "expr": "active_users"
        }
      ]
    },
    {
      "title": "MRR by Tier",
      "type": "piechart",
      "targets": [
        {
          "expr": "subscription_mrr",
          "legendFormat": "{{tier}}"
        }
      ]
    },
    {
      "title": "Generation Success Rate",
      "type": "gauge",
      "targets": [
        {
          "expr": "sum(designs_generated_total{status='success'}) / sum(designs_generated_total) * 100"
        }
      ]
    }
  ]
}
```

---

## Alerting Rules

### Prometheus Alerting Rules

```yaml
# prometheus/alerts.yml

groups:
  - name: ai-part-designer
    rules:
      # High Error Rate
      - alert: HighErrorRate
        expr: |
          sum(rate(http_requests_total{status=~"5.."}[5m])) 
          / sum(rate(http_requests_total[5m])) > 0.05
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "High error rate detected"
          description: "Error rate is {{ $value | printf \"%.2f\" }}%"

      # Slow Response Time
      - alert: SlowResponseTime
        expr: |
          histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m])) > 0.5
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "Slow API response time"
          description: "p95 latency is {{ $value | printf \"%.2f\" }}s"

      # High Queue Depth
      - alert: HighQueueDepth
        expr: jobs_in_queue > 100
        for: 15m
        labels:
          severity: warning
        annotations:
          summary: "High job queue depth"
          description: "{{ $value }} jobs waiting in queue"

      # Payment Failures
      - alert: PaymentFailures
        expr: |
          sum(rate(payments_total{status="failed"}[1h])) 
          / sum(rate(payments_total[1h])) > 0.1
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "High payment failure rate"
          description: "Payment failure rate is {{ $value | printf \"%.2f\" }}%"

      # WebSocket Connection Drop
      - alert: WebSocketConnectionDrop
        expr: |
          (websocket_connections - websocket_connections offset 5m) 
          / websocket_connections offset 5m < -0.5
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Significant WebSocket connection drop"
          description: "WebSocket connections dropped by {{ $value | printf \"%.0f\" }}%"

      # Low Disk Space
      - alert: LowDiskSpace
        expr: |
          (node_filesystem_avail_bytes / node_filesystem_size_bytes) < 0.1
        for: 15m
        labels:
          severity: critical
        annotations:
          summary: "Low disk space"
          description: "Less than 10% disk space remaining"

      # Database Connection Pool Exhausted
      - alert: DatabaseConnectionPoolExhausted
        expr: |
          pg_stat_activity_count / pg_settings_max_connections > 0.9
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "Database connection pool near exhaustion"
          description: "Using {{ $value | printf \"%.0f\" }}% of max connections"
```

### Alert Notification Channels

```yaml
# alertmanager/config.yml

global:
  resolve_timeout: 5m
  slack_api_url: "${SLACK_WEBHOOK_URL}"

route:
  group_by: ['alertname', 'severity']
  group_wait: 30s
  group_interval: 5m
  repeat_interval: 4h
  receiver: 'default'
  routes:
    - match:
        severity: critical
      receiver: 'critical-alerts'
    - match:
        severity: warning
      receiver: 'warning-alerts'

receivers:
  - name: 'default'
    slack_configs:
      - channel: '#alerts'
        send_resolved: true

  - name: 'critical-alerts'
    slack_configs:
      - channel: '#alerts-critical'
        send_resolved: true
    pagerduty_configs:
      - service_key: "${PAGERDUTY_SERVICE_KEY}"
        send_resolved: true

  - name: 'warning-alerts'
    slack_configs:
      - channel: '#alerts'
        send_resolved: true
```

---

## Logging Configuration

### Structured Logging

```python
# backend/app/core/logging.py

import structlog
import logging

def setup_logging(log_level: str = "INFO", json_logs: bool = True):
    """Configure structured logging."""
    
    processors = [
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
    ]
    
    if json_logs:
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer())
    
    structlog.configure(
        processors=processors,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
    
    logging.basicConfig(
        format="%(message)s",
        level=getattr(logging, log_level.upper()),
    )
```

### Log Format

```json
{
  "timestamp": "2026-01-26T12:00:00.000Z",
  "level": "info",
  "logger": "app.api.designs",
  "message": "Design created",
  "user_id": "user_123",
  "design_id": "design_456",
  "duration_ms": 245,
  "request_id": "req_789"
}
```

---

## Health Checks

### Health Check Endpoint

```python
# backend/app/api/v1/health.py

from fastapi import APIRouter, status
from pydantic import BaseModel

router = APIRouter()

class HealthStatus(BaseModel):
    status: str
    version: str
    database: str
    redis: str
    celery: str

@router.get("/health")
async def health_check() -> HealthStatus:
    """Comprehensive health check."""
    return HealthStatus(
        status="healthy",
        version="1.0.0",
        database=check_database(),
        redis=check_redis(),
        celery=check_celery(),
    )

@router.get("/health/live")
async def liveness():
    """Kubernetes liveness probe."""
    return {"status": "ok"}

@router.get("/health/ready")
async def readiness():
    """Kubernetes readiness probe."""
    # Check all dependencies
    if not all([check_database(), check_redis()]):
        return Response(status_code=status.HTTP_503_SERVICE_UNAVAILABLE)
    return {"status": "ready"}
```

---

## Runbook

### High Error Rate

1. Check Sentry for error details
2. Review recent deployments
3. Check database connectivity
4. Check external service status (OpenAI, Stripe)
5. Scale up if load-related

### Slow Response Time

1. Check database query performance
2. Review slow query logs
3. Check Redis cache hit rate
4. Scale up application servers
5. Review recent code changes

### Payment Failures

1. Check Stripe dashboard for issues
2. Review error messages in logs
3. Verify webhook delivery
4. Contact Stripe support if needed
5. Notify affected users

### WebSocket Issues

1. Check Redis pub/sub connectivity
2. Review connection logs
3. Check for memory leaks
4. Restart WebSocket servers
5. Scale up if connection limited

---

## Contact Information

| Role | Contact |
|------|---------|
| On-Call Engineer | PagerDuty rotation |
| DevOps Lead | devops@aipartdesigner.com |
| Engineering Manager | eng-manager@aipartdesigner.com |

---

**Document Version:** 1.0.0  
**Last Updated:** January 26, 2026
