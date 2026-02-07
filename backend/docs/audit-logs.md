# Audit Log System

## Overview

The audit log system provides comprehensive tracking of all significant actions in the platform for security, compliance, and debugging purposes.

## Features

- **Comprehensive Logging**: Records user actions, system events, and API key usage
- **Rich Context**: Stores detailed context with each log entry using JSONB
- **Performance Optimized**: Indexed for common query patterns
- **Retention Policy**: Automatic archival and cleanup of old logs
- **Cold Storage**: Compressed archives in S3-compatible storage

## Audit Log Model

### Fields

| Field | Type | Description |
|-------|------|-------------|
| `id` | UUID | Unique identifier |
| `user_id` | UUID | Actor performing the action (nullable for system actions) |
| `actor_type` | String | Type of actor: `user`, `system`, `api_key`, `webhook` |
| `action` | String | Action performed (e.g., `create`, `update`, `delete`, `login`) |
| `resource_type` | String | Type of resource (e.g., `design`, `project`, `user`) |
| `resource_id` | UUID | ID of the affected resource |
| `context` | JSONB | Detailed context and changes |
| `ip_address` | String | Request IP address |
| `user_agent` | String | Request user agent |
| `status` | String | Result: `success`, `failure`, `error` |
| `error_message` | String | Error details if applicable |
| `created_at` | DateTime | Timestamp (indexed) |

### Indexes

- **Primary Index**: `created_at` for time-based queries
- **Resource Index**: `(resource_type, resource_id, created_at)` for resource history
- **User Actions Index**: `(user_id, action, created_at)` for user activity
- **Context Index**: GIN index on JSONB `context` field
- **Failures Index**: Partial index for `status != 'success'` (security focus)

## Usage

### Creating Audit Logs

```python
from app.models.audit import AuditLog

# Using the factory method
log = AuditLog.log(
    action="update",
    resource_type="design",
    resource_id=design.id,
    user_id=current_user.id,
    context={
        "changes": {
            "name": {"old": "Draft", "new": "Final Design"}
        }
    },
)
db.add(log)
await db.commit()
```

### Using the Decorator

```python
from app.core.audit import audit_log

@router.put("/{design_id}")
@audit_log(
    action="update",
    resource_type="design",
    resource_id_param="design_id",
)
async def update_design(
    design_id: UUID,
    request: DesignUpdate,
    current_user: User = Depends(get_current_user),
):
    # Your code here
    pass
```

## Retention Policy

### Configuration

The retention period is configured via environment variable:

```bash
AUDIT_LOG_RETENTION_DAYS=90  # Default: 90 days
```

### Archival Process

The `archive_old_audit_logs` Celery task runs **weekly** and:

1. **Queries** logs older than the retention period
2. **Generates** summary statistics for analytics:
   - Total logs count
   - Breakdown by action, resource type, and status
   - Time range of archived data
3. **Compresses** logs using gzip (JSON → JSON.gz)
4. **Uploads** to cold storage (ARCHIVES bucket) in batches:
   - 1000 logs per archive file
   - Organized by timestamp: `audit-logs/{timestamp}/batch_XXXX.json.gz`
5. **Saves** summary statistics: `audit-logs/{timestamp}/summary.json.gz`
6. **Deletes** archived logs from the database

### Archive Format

Each archive file contains an array of audit log entries:

```json
[
  {
    "id": "uuid",
    "user_id": "uuid",
    "actor_type": "user",
    "action": "create",
    "resource_type": "design",
    "resource_id": "uuid",
    "context": {...},
    "ip_address": "192.168.1.1",
    "user_agent": "Mozilla/5.0...",
    "status": "success",
    "error_message": null,
    "created_at": "2024-01-01T00:00:00Z"
  }
]
```

## Storage

### Buckets

Audit logs use the following storage buckets:

- **Database**: PostgreSQL for active logs (retention period)
- **ARCHIVES**: S3-compatible cold storage for archived logs (long-term)

### Storage Layout

```
archives/
└── audit-logs/
    ├── 20240101_120000/
    │   ├── batch_0000.json.gz
    │   ├── batch_0001.json.gz
    │   └── summary.json.gz
    └── 20240108_120000/
        └── ...
```

## Querying Audit Logs

### Recent Activity by User

```python
from sqlalchemy import select
from app.models.audit import AuditLog

logs = await db.execute(
    select(AuditLog)
    .where(AuditLog.user_id == user_id)
    .order_by(AuditLog.created_at.desc())
    .limit(100)
)
```

### Resource History

```python
logs = await db.execute(
    select(AuditLog)
    .where(AuditLog.resource_type == "design")
    .where(AuditLog.resource_id == design_id)
    .order_by(AuditLog.created_at)
)
```

### Failed Actions (Security)

```python
logs = await db.execute(
    select(AuditLog)
    .where(AuditLog.status == "failure")
    .where(AuditLog.created_at > cutoff_date)
    .order_by(AuditLog.created_at.desc())
)
```

## Compliance

### GDPR Considerations

- User audit logs should be included in data export requests
- Archived logs in cold storage must be accessible for compliance requests
- User deletion should retain anonymized audit logs (user_id set to NULL)

### Retention Requirements

Different compliance frameworks may require different retention periods:

- **SOC 2**: Typically 1 year minimum
- **HIPAA**: 6 years minimum
- **PCI DSS**: 1 year minimum, 3 months online

Adjust `AUDIT_LOG_RETENTION_DAYS` based on your requirements.

## Monitoring

### Key Metrics

- **Audit log growth rate**: Monitor `audit_logs` table size
- **Archival success rate**: Track successful archival task runs
- **Archive file size**: Monitor cold storage usage
- **Query performance**: Monitor audit log query latency

### Alerts

Consider alerting on:

- Failed archival tasks
- Rapid growth in audit log table size
- High number of failed actions (potential security issue)
- Storage quota warnings for ARCHIVES bucket

## Troubleshooting

### High Database Size

If the `audit_logs` table grows too large:

1. Check that the archival task is running (weekly schedule)
2. Verify `AUDIT_LOG_RETENTION_DAYS` configuration
3. Manually trigger archival: `celery -A app.worker.celery_app call app.worker.tasks.maintenance.archive_old_audit_logs`

### Missing Archived Logs

To restore archived logs:

1. Locate the archive file in the ARCHIVES bucket
2. Download and decompress: `gunzip batch_XXXX.json.gz`
3. Parse JSON and restore to database if needed

### Performance Issues

If audit log queries are slow:

1. Verify indexes are created: Check `\d+ audit_logs` in psql
2. Use appropriate index: Filter by `user_id`, `resource_type`, or `created_at`
3. Reduce retention period if table is too large
4. Consider partitioning by date for very large datasets

## Best Practices

1. **Use the decorator**: Prefer `@audit_log()` decorator over manual logging
2. **Rich context**: Include meaningful context for debugging
3. **Status tracking**: Always set appropriate status (success/failure/error)
4. **Sensitive data**: Avoid logging passwords, tokens, or PII in context
5. **Retention tuning**: Balance compliance needs with database size
6. **Archive validation**: Periodically verify archived data integrity

## Related

- [Structured Logging](./structured-logging.md) - Application logging
- [Prometheus Metrics](./prometheus-metrics.md) - Monitoring metrics
- Security Audit Service - Real-time security event tracking
