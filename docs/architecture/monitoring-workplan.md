# Monitoring/Logging Implementation Workplan

This is a detailed task checklist for implementing the logging and monitoring infrastructure. Use this to track progress during implementation.

**Estimated Timeline**: 6-8 weeks  
**Estimated Effort**: 80-120 story points  
**Team Size**: 1-2 engineers

---

## Pre-Implementation

### Planning & Approval
- [ ] Product Owner reviews specification documents
- [ ] Answer critical questions (see monitoring-summary.md)
- [ ] Approve ADR-011 updates
- [ ] Allocate engineering resources
- [ ] Create JIRA epic: "Logging & Monitoring Infrastructure"
- [ ] Create stories from this workplan
- [ ] Schedule kickoff meeting
- [ ] Set up #observability Slack channel

### Environment Setup
- [ ] Verify Docker has 8GB+ RAM available
- [ ] Verify 10GB+ free disk space
- [ ] Clone repository
- [ ] Review all specification documents
- [ ] Set up development branch

---

## Phase 1: Foundation (Week 1-2)

### Story 1.1: Add Python Logging Dependencies
**Effort**: 1 point  
- [ ] Add `python-json-logger` to pyproject.toml
- [ ] Add `structlog` to pyproject.toml (optional, if using)
- [ ] Run `poetry install` or `pip install -e .`
- [ ] Verify imports work

**Acceptance Criteria:**
- ✅ Dependencies install without errors
- ✅ Can import `pythonjsonlogger.jsonlogger`

---

### Story 1.2: Implement Structured Logging
**Effort**: 5 points

**Files to create:**
- [ ] `backend/app/core/logging.py`

**Tasks:**
- [ ] Create `CustomJsonFormatter` class
- [ ] Implement `setup_logging()` function
- [ ] Create context variables (request_id, trace_id, user_id)
- [ ] Add `get_logger(name)` helper function
- [ ] Add `log_with_context()` helper function
- [ ] Update `backend/app/main.py` to call `setup_logging()` on startup
- [ ] Write unit tests for logging configuration

**Acceptance Criteria:**
- ✅ Logs output in JSON format
- ✅ All logs include service, environment, version
- ✅ Context variables propagate correctly
- ✅ Log level configurable via DEBUG env var
- ✅ Tests pass

**Test Command:**
```bash
cd backend && python -m pytest tests/core/test_logging.py -v
```

---

### Story 1.3: Add Request Context Middleware
**Effort**: 3 points

**Files to create:**
- [ ] `backend/app/middleware/logging.py`

**Tasks:**
- [ ] Create `LoggingMiddleware` class
- [ ] Generate/extract request_id from headers
- [ ] Set context variables at request start
- [ ] Log request start with method, path, client_ip
- [ ] Calculate request duration
- [ ] Log request completion with status_code, duration
- [ ] Add correlation headers to response
- [ ] Handle exceptions and log errors
- [ ] Register middleware in main.py
- [ ] Write integration tests

**Acceptance Criteria:**
- ✅ Every request gets unique request_id
- ✅ Request start/end logged automatically
- ✅ Duration calculated correctly
- ✅ X-Request-ID header in response
- ✅ Exceptions logged with context
- ✅ Tests pass

**Test Command:**
```bash
cd backend && python -m pytest tests/middleware/test_logging.py -v
```

---

### Story 1.4: Update Existing Logging Calls
**Effort**: 5 points

**Tasks:**
- [ ] Audit current logging usage: `grep -r "logger\." backend/app/ --include="*.py" | wc -l`
- [ ] Identify high-priority files to update (API routes, services)
- [ ] Replace string formatting with structured context
- [ ] Add business context (user_id, design_id, etc.)
- [ ] Remove sensitive data from logs
- [ ] Test updated logging

**Example updates:**
```python
# Before
logger.info(f"Design {design_id} created by user {user.email}")

# After
log_with_context(
    logger, "info",
    "Design created",
    design_id=str(design_id),
    user_id=str(user.id),
    template=design.template
)
```

**Acceptance Criteria:**
- ✅ Top 20 files updated with structured logging
- ✅ No PII (emails, passwords, tokens) in logs
- ✅ Business context added where relevant
- ✅ Existing tests still pass

---

## Phase 2: ELK Stack (Week 3-4)

### Story 2.1: Add ELK Services to Docker Compose
**Effort**: 3 points

**Files to modify:**
- [ ] `docker-compose.yml`
- [ ] `.gitignore` (add elasticsearch_data, etc.)

**Tasks:**
- [ ] Add Elasticsearch service (port 9200)
- [ ] Add Logstash service (port 5044)
- [ ] Add Kibana service (port 5601)
- [ ] Add Filebeat service
- [ ] Add volume definitions
- [ ] Add network configuration
- [ ] Add monitoring profile to docker-compose
- [ ] Test services start successfully

**Acceptance Criteria:**
- ✅ `docker-compose --profile monitoring up` starts all services
- ✅ Elasticsearch responds at http://localhost:9200
- ✅ Kibana accessible at http://localhost:5601
- ✅ All services healthy: `make monitoring-health`

**Test Command:**
```bash
make monitoring-up
make monitoring-health
```

---

### Story 2.2: Configure Filebeat
**Effort**: 2 points

**Files to create:**
- [ ] `filebeat/filebeat.yml`

**Tasks:**
- [ ] Configure Docker container log input
- [ ] Add JSON decoding processor
- [ ] Add metadata (service name, environment)
- [ ] Configure Logstash output
- [ ] Test log collection

**Acceptance Criteria:**
- ✅ Filebeat collects logs from containers
- ✅ JSON logs parsed correctly
- ✅ Logs forwarded to Logstash
- ✅ No errors in Filebeat logs

---

### Story 2.3: Create Logstash Pipelines
**Effort**: 3 points

**Files to create:**
- [ ] `logstash/pipeline/main.conf`
- [ ] `logstash/pipeline/api-logs.conf`
- [ ] `logstash/pipeline/worker-logs.conf`

**Tasks:**
- [ ] Configure Beats input
- [ ] Add GeoIP filter (optional)
- [ ] Add mutate filters (type conversion)
- [ ] Add conditional filtering (drop noisy logs)
- [ ] Configure Elasticsearch output
- [ ] Test pipeline with sample logs

**Acceptance Criteria:**
- ✅ Logs processed by Logstash
- ✅ Enrichment filters work
- ✅ Noisy logs filtered out
- ✅ Logs indexed in Elasticsearch

**Test Command:**
```bash
# Generate test logs
curl http://localhost:8000/api/v1/health

# Check Elasticsearch
curl "http://localhost:9200/logs-*/_search?size=5&pretty"
```

---

### Story 2.4: Configure Elasticsearch Indices
**Effort**: 2 points

**Files to create:**
- [ ] `elasticsearch/index-templates/logs-template.json`
- [ ] `elasticsearch/ilm-policies/logs-lifecycle.json`

**Tasks:**
- [ ] Create index template for logs-*
- [ ] Define field mappings
- [ ] Set up Index Lifecycle Management (ILM)
- [ ] Configure retention policy (7/30 days)
- [ ] Test rollover works

**Acceptance Criteria:**
- ✅ Indices created with correct mapping
- ✅ ILM policy applied
- ✅ Old indices deleted after retention period
- ✅ Query performance acceptable

---

### Story 2.5: Create Kibana Dashboards
**Effort**: 8 points

**Dashboards to create:**
1. [ ] Application Overview
   - [ ] Request rate (line chart)
   - [ ] Error rate (gauge)
   - [ ] P50/P95/P99 latency (time series)
   - [ ] Top 10 errors (table)
   - [ ] Active users (counter)

2. [ ] Error Analysis
   - [ ] Errors by type (pie chart)
   - [ ] Error trend (time series)
   - [ ] Stack trace viewer (table)
   - [ ] Affected users (table)
   - [ ] Error rate by endpoint (heatmap)

3. [ ] Performance
   - [ ] Response time distribution (histogram)
   - [ ] Slow queries >1s (table)
   - [ ] Database connection pool
   - [ ] Redis hit/miss ratio
   - [ ] Celery queue depth

4. [ ] User Activity
   - [ ] Active sessions
   - [ ] User journey flow
   - [ ] Feature usage heatmap

**Tasks:**
- [ ] Create index pattern in Kibana
- [ ] Build each dashboard
- [ ] Save dashboard JSON exports
- [ ] Document dashboard usage
- [ ] Import dashboards in CI

**Acceptance Criteria:**
- ✅ All dashboards created and functional
- ✅ Dashboards exported to `kibana/dashboards/`
- ✅ Documentation in README
- ✅ Team can use dashboards effectively

---

## Phase 3: APM (Week 5)

### Story 3.1: Add OpenTelemetry Dependencies
**Effort**: 1 point

**Tasks:**
- [ ] Add OpenTelemetry packages to pyproject.toml
- [ ] Install dependencies
- [ ] Verify imports

**Dependencies:**
```toml
"opentelemetry-api>=1.22.0",
"opentelemetry-sdk>=1.22.0",
"opentelemetry-instrumentation-fastapi>=0.43b0",
"opentelemetry-instrumentation-sqlalchemy>=0.43b0",
"opentelemetry-instrumentation-redis>=0.43b0",
"opentelemetry-instrumentation-celery>=0.43b0",
"opentelemetry-exporter-otlp>=1.22.0",
```

---

### Story 3.2: Implement Telemetry Configuration
**Effort**: 5 points

**Files to create:**
- [ ] `backend/app/core/telemetry.py`

**Tasks:**
- [ ] Create `setup_telemetry(app)` function
- [ ] Configure resource with service metadata
- [ ] Create OTLP exporter
- [ ] Add batch span processor
- [ ] Instrument FastAPI
- [ ] Instrument SQLAlchemy
- [ ] Instrument Redis
- [ ] Instrument Celery
- [ ] Create `get_tracer()` helper
- [ ] Write tests

**Acceptance Criteria:**
- ✅ Tracing configured and working
- ✅ Auto-instrumentation active
- ✅ Traces exported to OTLP endpoint
- ✅ Tests pass

---

### Story 3.3: Add Tempo and OTEL Collector
**Effort**: 3 points

**Files to create:**
- [ ] `otel-collector-config.yaml`
- [ ] `tempo/tempo.yaml`

**Tasks:**
- [ ] Add OTEL Collector to docker-compose
- [ ] Add Tempo to docker-compose
- [ ] Configure collector receivers (OTLP gRPC/HTTP)
- [ ] Configure collector processors (batch)
- [ ] Configure collector exporters (Tempo)
- [ ] Configure Tempo storage (local for dev)
- [ ] Test trace ingestion

**Acceptance Criteria:**
- ✅ OTEL Collector receives traces
- ✅ Tempo stores traces
- ✅ Can query traces via API
- ✅ Services healthy

---

### Story 3.4: Add Prometheus for Metrics
**Effort**: 5 points

**Files to create:**
- [ ] `backend/app/core/metrics.py`
- [ ] `prometheus/prometheus.yml`

**Tasks:**
- [ ] Add prometheus_client dependency
- [ ] Define metrics (counters, histograms, gauges)
- [ ] Create `/metrics` endpoint
- [ ] Add Prometheus middleware
- [ ] Add Prometheus service to docker-compose
- [ ] Configure scrape targets
- [ ] Test metrics collection

**Metrics to define:**
- [ ] `http_requests_total`
- [ ] `http_request_duration_seconds`
- [ ] `http_requests_in_progress`
- [ ] `db_queries_total`
- [ ] `db_query_duration_seconds`
- [ ] `cache_hits_total`
- [ ] `cache_misses_total`
- [ ] `designs_created_total`
- [ ] `job_queue_size`

**Acceptance Criteria:**
- ✅ Metrics endpoint returns data
- ✅ Prometheus scrapes metrics
- ✅ Can query metrics in Prometheus UI
- ✅ Tests pass

---

### Story 3.5: Create Grafana Dashboards
**Effort**: 8 points

**Tasks:**
- [ ] Add Grafana to docker-compose
- [ ] Configure Prometheus data source
- [ ] Configure Tempo data source
- [ ] Create API Performance dashboard
- [ ] Create System Health dashboard
- [ ] Create Database Metrics dashboard
- [ ] Create Trace Explorer dashboard
- [ ] Export dashboard JSON
- [ ] Document dashboards

**Acceptance Criteria:**
- ✅ Grafana accessible at localhost:3000
- ✅ Data sources configured
- ✅ All dashboards functional
- ✅ Dashboards exported
- ✅ Documentation complete

---

## Phase 4: Exception Monitoring (Week 6)

### Story 4.1: Deploy Sentry via Docker Compose
**Effort**: 5 points

**Tasks:**
- [ ] Clone Sentry self-hosted repo
- [ ] Run Sentry install script
- [ ] Add Sentry services to main docker-compose
- [ ] Configure environment variables
- [ ] Create admin user
- [ ] Create project "AssemblematicAI"
- [ ] Copy DSN to .env
- [ ] Test Sentry UI

**Acceptance Criteria:**
- ✅ Sentry accessible at localhost:9000
- ✅ Can login to Sentry
- ✅ Project created
- ✅ DSN available

---

### Story 4.2: Integrate Sentry SDK
**Effort**: 3 points

**Files to create:**
- [ ] `backend/app/core/sentry.py`

**Tasks:**
- [ ] Add sentry-sdk dependency
- [ ] Create `setup_sentry()` function
- [ ] Configure DSN, environment, release
- [ ] Add integrations (FastAPI, Celery, SQLAlchemy, Redis)
- [ ] Implement `filter_sensitive_data()`
- [ ] Configure sampling rates
- [ ] Call setup_sentry() in main.py
- [ ] Test error capture

**Acceptance Criteria:**
- ✅ Sentry SDK initialized
- ✅ Errors captured automatically
- ✅ PII filtered from reports
- ✅ User context attached
- ✅ Tests pass

**Test:**
```python
# Trigger test error
import sentry_sdk
sentry_sdk.capture_message("Test error from implementation")
```

---

### Story 4.3: Configure Error Alerts
**Effort**: 2 points

**Tasks:**
- [ ] Create alert rule: New Issue
- [ ] Create alert rule: High Error Rate
- [ ] Create alert rule: Critical Error
- [ ] Configure Slack integration (if available)
- [ ] Configure email notifications
- [ ] Test alerts fire correctly

**Acceptance Criteria:**
- ✅ Alert rules configured
- ✅ Notifications working
- ✅ No false positives
- ✅ Team receives alerts

---

## Phase 5: Production Deployment (Week 7)

### Story 5.1: Create Kubernetes Manifests
**Effort**: 13 points

**Files to create:**
```
k8s/monitoring/
├── namespace.yaml
├── elasticsearch/
│   ├── statefulset.yaml
│   ├── service.yaml
│   └── pvc.yaml
├── logstash/
│   ├── deployment.yaml
│   ├── configmap.yaml
│   └── service.yaml
├── kibana/
│   ├── deployment.yaml
│   ├── service.yaml
│   └── ingress.yaml
├── tempo/
│   ├── statefulset.yaml
│   ├── service.yaml
│   └── pvc.yaml
├── grafana/
│   ├── deployment.yaml
│   ├── service.yaml
│   ├── ingress.yaml
│   └── configmap.yaml
├── prometheus/
│   ├── deployment.yaml
│   ├── service.yaml
│   └── configmap.yaml
└── sentry/
    ├── deployment.yaml (web, worker, cron)
    ├── service.yaml
    └── ingress.yaml
```

**Tasks:**
- [ ] Create namespace manifest
- [ ] Create all manifests listed above
- [ ] Set resource limits appropriately
- [ ] Configure persistent volumes
- [ ] Configure ingress with TLS
- [ ] Set up RBAC if needed
- [ ] Test in staging cluster

**Acceptance Criteria:**
- ✅ All manifests valid YAML
- ✅ `kubectl apply` succeeds
- ✅ Pods running and healthy
- ✅ Services accessible
- ✅ Persistent data survives pod restarts

---

### Story 5.2: Production Configuration
**Effort**: 3 points

**Tasks:**
- [ ] Set production log retention (30 days)
- [ ] Configure Elasticsearch heap size
- [ ] Set up backup for Elasticsearch
- [ ] Configure trace sampling (10%)
- [ ] Set Sentry rate limits
- [ ] Configure alert throttling
- [ ] Set up TLS certificates
- [ ] Configure authentication

**Acceptance Criteria:**
- ✅ Production configs different from dev
- ✅ Resource limits appropriate
- ✅ Backups configured
- ✅ Security hardened

---

### Story 5.3: Deploy to Staging
**Effort**: 5 points

**Tasks:**
- [ ] Deploy to staging Kubernetes cluster
- [ ] Verify all pods running
- [ ] Import dashboards
- [ ] Configure data sources
- [ ] Run integration tests
- [ ] Load test monitoring stack
- [ ] Fix any issues
- [ ] Document deployment process

**Acceptance Criteria:**
- ✅ All services running in staging
- ✅ Logs flowing end-to-end
- ✅ Traces visible in Grafana
- ✅ Errors appearing in Sentry
- ✅ Load test passes (<2% overhead)

---

## Phase 6: Testing & Documentation (Week 8)

### Story 6.1: Integration Testing
**Effort**: 5 points

**Tests to write:**
- [ ] Test log ingestion pipeline
- [ ] Test trace propagation
- [ ] Test metric collection
- [ ] Test error capture
- [ ] Test dashboard queries
- [ ] Test alert firing

**Acceptance Criteria:**
- ✅ All integration tests pass
- ✅ CI runs tests automatically
- ✅ Tests documented

---

### Story 6.2: Load Testing
**Effort**: 3 points

**Tasks:**
- [ ] Create load test script (Locust/k6)
- [ ] Run 1000 req/s for 10 minutes
- [ ] Measure latency overhead
- [ ] Measure CPU overhead
- [ ] Measure memory usage
- [ ] Optimize if needed
- [ ] Document results

**Acceptance Criteria:**
- ✅ <500ms p99 latency overhead
- ✅ <2% CPU overhead
- ✅ No memory leaks
- ✅ All logs captured

---

### Story 6.3: Write Operations Documentation
**Effort**: 5 points

**Documents to create:**
- [ ] `docs/operations/monitoring-setup.md` - Deployment guide
- [ ] `docs/operations/log-queries.md` - Query cookbook
- [ ] `docs/operations/alerting-runbook.md` - Alert response
- [ ] `docs/operations/troubleshooting.md` - Common issues
- [ ] `docs/operations/backup-restore.md` - Backup procedures

**Acceptance Criteria:**
- ✅ Documentation complete
- ✅ Examples tested
- ✅ Team reviewed docs

---

### Story 6.4: Team Training
**Effort**: 3 points

**Tasks:**
- [ ] Schedule training session
- [ ] Create training slides
- [ ] Demo Kibana queries
- [ ] Demo Grafana dashboards
- [ ] Demo Sentry usage
- [ ] Hands-on exercises
- [ ] Q&A session
- [ ] Record session

**Acceptance Criteria:**
- ✅ Team trained on all tools
- ✅ Feedback collected
- ✅ Training recorded

---

## Phase 7: Production Rollout

### Story 7.1: Deploy to Production
**Effort**: 8 points

**Tasks:**
- [ ] Review all configurations
- [ ] Get approval from tech lead
- [ ] Schedule deployment window
- [ ] Deploy to production
- [ ] Verify all services healthy
- [ ] Import dashboards
- [ ] Configure alerts
- [ ] Monitor for 24h
- [ ] Fix any issues
- [ ] Announce to team

**Acceptance Criteria:**
- ✅ All services running in production
- ✅ Logs, traces, errors flowing
- ✅ No critical issues
- ✅ Team notified

---

### Story 7.2: Post-Deployment Validation
**Effort**: 3 points

**Tasks:**
- [ ] Verify log volume as expected
- [ ] Verify trace sampling working
- [ ] Verify errors being captured
- [ ] Verify dashboards accurate
- [ ] Verify alerts working
- [ ] Check performance impact
- [ ] Review with team
- [ ] Create follow-up tickets

**Acceptance Criteria:**
- ✅ All success criteria met
- ✅ No production issues
- ✅ Team satisfied

---

## Ongoing Maintenance

### Weekly
- [ ] Check Elasticsearch disk usage
- [ ] Review error trends in Sentry
- [ ] Check for alerts needing tuning
- [ ] Review slow queries

### Monthly
- [ ] Review retention policies
- [ ] Optimize dashboard queries
- [ ] Update documentation
- [ ] Review costs

### Quarterly
- [ ] Upgrade components
- [ ] Review and tune alert rules
- [ ] Collect team feedback
- [ ] Plan improvements

---

## Success Metrics

Track these metrics throughout implementation:

- [ ] **Log Capture Rate**: ≥99%
- [ ] **Trace Availability**: <10s from occurrence
- [ ] **Error Detection**: <5s in Sentry
- [ ] **Latency Overhead**: <500ms p99
- [ ] **CPU Overhead**: <2%
- [ ] **Uptime**: ≥99.9%
- [ ] **MTTR Reduction**: 50%
- [ ] **False Positive Alerts**: 0
- [ ] **Team Adoption**: 100% using dashboards

---

## Risk Register

| Risk | Probability | Impact | Mitigation | Owner |
|------|-------------|--------|------------|-------|
| Elasticsearch disk full | Medium | High | ILM, disk monitoring | TBD |
| Monitoring stack down | Low | High | HA deployment, separate infra | TBD |
| Log volume too high | Medium | Medium | Sampling, filtering | TBD |
| Team learning curve | High | Low | Training, documentation | TBD |
| Cost overruns | Low | Medium | Resource monitoring, optimization | TBD |

---

**Last Updated**: 2024-02-04  
**Status**: Ready for kickoff  
**Next Review**: After Phase 1 completion
