# Data Engineering Documentation
# AI Part Designer

**Version:** 1.0  
**Date:** 2026-01-24  
**Owner:** Data Engineering Team  

---

## Table of Contents
1. [Data Architecture Overview](#1-data-architecture-overview)
2. [Data Flows](#2-data-flows)
3. [Storage Architecture](#3-storage-architecture)
4. [Data Quality Framework](#4-data-quality-framework)
5. [ETL/ELT Pipelines](#5-etlelt-pipelines)
6. [Analytics Infrastructure](#6-analytics-infrastructure)
7. [Backup & Recovery](#7-backup--recovery)
8. [Data Governance](#8-data-governance)

---

## 1. Data Architecture Overview

### 1.1 High-Level Data Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         DATA ARCHITECTURE OVERVIEW                           │
└─────────────────────────────────────────────────────────────────────────────┘

 ┌──────────────────┐
 │   Data Sources   │
 ├──────────────────┤
 │ • User Actions   │
 │ • CAD Operations │
 │ • AI Generations │
 │ • System Events  │
 └────────┬─────────┘
          │
          ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           INGESTION LAYER                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│  REST API → FastAPI → Event Tracker → Redis Queue                           │
│                              ↓                                               │
│                    Celery Workers (batch processing)                         │
└─────────────────────────────────────────────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                          STORAGE LAYER                                       │
├──────────────────┬──────────────────┬──────────────────┬────────────────────┤
│    PostgreSQL    │      Redis       │   Object Storage │   Analytics DW     │
│  (Operational)   │   (Cache/Queue)  │    (S3/MinIO)    │   (Future)         │
├──────────────────┼──────────────────┼──────────────────┼────────────────────┤
│ • Users          │ • Session cache  │ • CAD files      │ • Aggregated       │
│ • Designs        │ • Rate limits    │ • Exports        │   metrics          │
│ • Jobs           │ • Event queue    │ • Thumbnails     │ • User behavior    │
│ • Audit logs     │ • Job results    │ • Backups        │ • Usage trends     │
└──────────────────┴──────────────────┴──────────────────┴────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                        CONSUMPTION LAYER                                     │
├──────────────────┬──────────────────┬──────────────────────────────────────┤
│   Application    │    Analytics     │          ML/AI                        │
├──────────────────┼──────────────────┼──────────────────────────────────────┤
│ • API responses  │ • Dashboards     │ • Training data                      │
│ • File downloads │ • Reports        │ • Feature store                      │
│ • Real-time UX   │ • Alerts         │ • Model inference                    │
└──────────────────┴──────────────────┴──────────────────────────────────────┘
```

### 1.2 Data Stores Summary

| Store | Technology | Purpose | Data Type |
|-------|------------|---------|-----------|
| **Primary DB** | PostgreSQL 15+ | Operational data | Structured |
| **Cache** | Redis 7 | Sessions, rate limits, queues | Key-value |
| **Object Storage** | S3/MinIO | Files, backups | Unstructured |
| **Event Queue** | Redis Lists | Analytics events | Semi-structured |

---

## 2. Data Flows

### 2.1 Design Creation Flow

```
User Request → API Validation → Create Design Record → Queue CAD Job
                                        ↓
                               Template Repository
                                        ↓
                               Parameter Validation
                                        ↓
                              Celery Worker (CAD)
                                        ↓
                    ┌───────────────────┴───────────────────┐
                    ↓                                       ↓
            Generate Model                           Create Thumbnail
                    ↓                                       ↓
            Upload to S3                            Upload to S3
                    ↓                                       ↓
                    └───────────────────┬───────────────────┘
                                        ↓
                            Update Design Record
                                        ↓
                              Track Analytics Event
                                        ↓
                              Audit Log Entry
```

### 2.2 Event Tracking Flow

```
User Action → Event Tracker → Buffer (in-memory)
                                    ↓
                            Auto-flush (batch)
                                    ↓
                         Redis Queue (analytics:events)
                                    ↓
                    Celery Beat (process_pending_events)
                                    ↓
               ┌────────────────────┼────────────────────┐
               ↓                    ↓                    ↓
        Log to File          Export to DW         Real-time Alert
```

---

## 3. Storage Architecture

### 3.1 PostgreSQL Schema Organization

```sql
-- Core schema (public)
public.users
public.user_settings
public.subscriptions
public.projects
public.designs
public.design_versions
public.design_shares
public.templates
public.jobs
public.api_keys

-- Audit schema
public.audit_logs
public.moderation_logs
```

### 3.2 Object Storage Buckets

| Bucket | Purpose | Retention | Access |
|--------|---------|-----------|--------|
| `designs` | CAD model files | Permanent | Private |
| `exports` | User exports | 30 days | Private |
| `thumbnails` | Preview images | Permanent | Public |
| `uploads` | User uploads | 7 days | Private |
| `temp` | Temporary files | 24 hours | Private |
| `backups` | DB backups | 30 days | Private |

### 3.3 Redis Key Patterns

```
# Session cache
session:{user_id}                    # User session data (TTL: 30min)

# Rate limiting
ratelimit:{endpoint}:{user_id}       # Request count (TTL: 1min)

# Job results
job:{job_id}:result                  # Job result cache (TTL: 1hour)

# Analytics events
analytics:events                      # Event queue (list)

# Distributed locks
lock:{resource}:{id}                  # Resource lock (TTL: 30sec)

# Cache invalidation
cache:{entity}:{id}                   # Entity cache (TTL: varies)
```

---

## 4. Data Quality Framework

### 4.1 Validation Layers

| Layer | Location | Checks |
|-------|----------|--------|
| **Input** | API endpoints | Schema validation (Pydantic) |
| **Business** | Services | CAD parameter validation |
| **Persistence** | Repository | Referential integrity |
| **Output** | Response | Data sanitization |

### 4.2 Quality Rules

```python
# Example validation configuration
from app.core.validation import DataValidator, Rules

user_validator = DataValidator()
user_validator.add_rule("email", Rules.email())
user_validator.add_rule("email", Rules.max_length(255))
user_validator.add_rule("full_name", Rules.min_length(2))
user_validator.add_rule("tier", Rules.in_list(["free", "hobby", "pro", "enterprise"]))
```

### 4.3 Data Quality Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| **Completeness** | > 99.9% | Non-null required fields |
| **Accuracy** | > 99.5% | Validation pass rate |
| **Timeliness** | < 5min | Event processing latency |
| **Consistency** | 100% | Referential integrity |

---

## 5. ETL/ELT Pipelines

### 5.1 Pipeline Inventory

| Pipeline | Schedule | Type | Description |
|----------|----------|------|-------------|
| `process_pending_events` | Every 1 min | Streaming | Process analytics events |
| `generate_daily_report` | Daily 2 AM | Batch | Aggregate daily metrics |
| `export_to_warehouse` | Daily 3 AM | Batch | Export to analytics DW |
| `backup_database` | Daily 4 AM | Batch | Full database backup |
| `cleanup_old_jobs` | Hourly | Maintenance | Remove old job records |
| `update_search_vectors` | Hourly | Batch | Update FTS indexes |

### 5.2 Pipeline Configuration

```python
# Celery Beat schedule (app/worker/celery.py)
beat_schedule = {
    "process-analytics-events": {
        "task": "app.worker.tasks.analytics.process_pending_events",
        "schedule": 60.0,  # Every minute
    },
    "backup-database": {
        "task": "app.worker.tasks.maintenance.backup_database",
        "schedule": 86400.0,  # Daily
    },
    # ... additional schedules
}
```

### 5.3 Error Handling

| Error Type | Strategy | Retry Policy |
|------------|----------|--------------|
| Transient | Exponential backoff | 3 retries, 60s delay |
| Data Quality | Log + Alert | No retry |
| Infrastructure | Circuit breaker | Manual intervention |

---

## 6. Analytics Infrastructure

### 6.1 Event Schema

```json
{
  "event_id": "uuid",
  "event_name": "design_created",
  "event_category": "design",
  "timestamp": "2026-01-24T10:30:00Z",
  "user_id": "uuid",
  "session_id": "string",
  "properties": {
    "design_id": "uuid",
    "source_type": "template",
    "template_id": "uuid"
  },
  "ip_address": "1.2.3.4",
  "user_agent": "Mozilla/5.0...",
  "environment": "production",
  "app_version": "0.1.0"
}
```

### 6.2 Key Events Tracked

| Event | Category | Properties |
|-------|----------|------------|
| `user_signup` | user | signup_method, referral_source |
| `user_login` | user | login_method |
| `design_created` | design | source_type, template_id |
| `design_exported` | design | export_format |
| `template_used` | template | template_slug |
| `job_completed` | job | job_type, duration_ms, success |
| `subscription_changed` | billing | from_tier, to_tier, change_type |

### 6.3 Metrics & Dashboards

| Metric | Aggregation | Dimension |
|--------|-------------|-----------|
| Daily Active Users | Count distinct | user_id by day |
| Designs Created | Count | source_type, template |
| Job Success Rate | Percentage | job_type |
| Avg Generation Time | Mean | job_type |
| Revenue by Tier | Sum | tier, period |

---

## 7. Backup & Recovery

### 7.1 Backup Strategy

| Data Store | Method | Frequency | Retention |
|------------|--------|-----------|-----------|
| PostgreSQL | pg_dump | Daily | 30 days |
| PostgreSQL | WAL archiving | Continuous | 7 days |
| Redis | RDB snapshot | Hourly | 24 hours |
| Object Storage | Cross-region replication | Continuous | N/A |

### 7.2 Recovery Procedures

```bash
# Restore from backup
make db-restore BACKUP=backup_full_20260124_040000.sql.gz

# Point-in-time recovery (requires WAL)
pg_restore --target-time="2026-01-24 10:30:00" ...
```

### 7.3 Recovery Time Objectives

| Scenario | RTO | RPO |
|----------|-----|-----|
| Database corruption | 2 hours | 24 hours |
| Accidental deletion | 1 hour | 15 minutes |
| Full disaster | 4 hours | 24 hours |

---

## 8. Data Governance

### 8.1 Data Classification

| Classification | Examples | Controls |
|----------------|----------|----------|
| **Public** | Templates, public designs | None |
| **Internal** | Aggregate analytics | Auth required |
| **Confidential** | User PII, designs | Encryption, access logs |
| **Restricted** | Passwords, API keys | Hashing, limited access |

### 8.2 Access Control

```python
# Repository-level access control
class DesignRepository(BaseRepository[Design]):
    async def get_user_designs(self, user_id: UUID) -> list[Design]:
        # Only returns designs owned by user
        return await self.get_many(filters={"user_id": user_id})
```

### 8.3 Compliance Requirements

| Requirement | Implementation |
|-------------|----------------|
| GDPR Data Export | `data_exporter.export_user_data()` |
| GDPR Right to Delete | Soft delete + anonymization |
| Audit Trail | `audit_logs` table |
| Data Retention | Automated cleanup tasks |

### 8.4 Data Lineage

```
Source → Transform → Target

users (PostgreSQL)
    ↓ [daily aggregate]
user_metrics (Analytics DW)
    ↓ [dashboard query]
Active Users Dashboard (Grafana)
```

---

## Appendix: Make Commands

```bash
# Database operations
make db-migrate          # Run migrations
make db-rollback         # Rollback last migration
make db-seed             # Seed templates
make db-reset            # Full reset
make db-shell            # Open psql

# Worker operations
make worker              # Start all workers
make worker-cad          # CAD queue only
make worker-ai           # AI queue only
make worker-beat         # Scheduled tasks
make worker-flower       # Monitoring UI

# Data operations
make backup              # Create database backup
make export-user-data USER_ID=xxx   # GDPR export
make analytics-snapshot  # Export analytics data
```

---

*This documentation is maintained by the Data Engineering team. For questions, contact data-eng@aipartdesigner.com*
