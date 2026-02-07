# CloudNativePG PostgreSQL Operations Guide

This guide provides operational procedures for managing the CloudNativePG PostgreSQL cluster in the AI Part Designer platform.

## Table of Contents

- [Overview](#overview)
- [Cluster Architecture](#cluster-architecture)
- [Daily Operations](#daily-operations)
- [Backup and Recovery](#backup-and-recovery)
- [Failover Testing](#failover-testing)
- [Monitoring and Alerting](#monitoring-and-alerting)
- [Troubleshooting](#troubleshooting)
- [Maintenance Procedures](#maintenance-procedures)

## Overview

The AI Part Designer platform uses CloudNativePG, a Kubernetes operator that manages PostgreSQL clusters with:

- **High Availability**: 3-node cluster (1 primary + 2 replicas) in production
- **Automated Failover**: Automatic primary election if primary fails
- **Connection Pooling**: PgBouncer for efficient connection management
- **Continuous Backup**: Daily backups to MinIO with 30-day retention
- **Self-Healing**: Automatic recovery from pod failures

### Key Components

| Component | Purpose | Replicas (Prod) |
|-----------|---------|-----------------|
| `postgres-cluster` | PostgreSQL database cluster | 3 |
| `postgres-pooler` | PgBouncer connection pooler | 2 |
| `postgres-service` | Service pointing to primary | 1 |
| `postgres-pooler-service` | Service for pooled connections | 1 |

## Cluster Architecture

### Replication Topology

```
┌─────────────────┐
│   Primary       │
│  (Read/Write)   │
└────────┬────────┘
         │
    ┌────┴────┐
    │         │
┌───▼───┐ ┌──▼────┐
│Replica│ │Replica│
│  (RO) │ │  (RO) │
└───────┘ └───────┘
```

### Storage

- **Primary Storage**: Persistent Volume Claim (100Gi in production)
- **Backup Storage**: MinIO S3-compatible object storage
- **WAL Archive**: Continuous archiving to MinIO

### Connection Flow

```
Application
    ↓
postgres-pooler-service (PgBouncer)
    ↓
postgres-service (Primary)
    ↓
PostgreSQL Primary Pod
```

## Daily Operations

### Check Cluster Health

```bash
# Get cluster status
kubectl get cluster -n ai-part-designer postgres-cluster

# Check all PostgreSQL pods
kubectl get pods -n ai-part-designer -l postgresql=postgres-cluster

# View cluster details
kubectl describe cluster -n ai-part-designer postgres-cluster
```

Expected output for healthy cluster:
```
NAME               AGE   INSTANCES   READY   STATUS                     PRIMARY
postgres-cluster   5d    3           3       Cluster in healthy state   postgres-cluster-1
```

### Check Connection Pooler

```bash
# Check pooler status
kubectl get pooler -n ai-part-designer postgres-pooler

# View pooler pods
kubectl get pods -n ai-part-designer -l cnpg.io/poolerName=postgres-pooler

# Check pooler logs
kubectl logs -n ai-part-designer -l cnpg.io/poolerName=postgres-pooler --tail=50
```

### View Cluster Topology

```bash
# Show primary and replicas
kubectl get pods -n ai-part-designer -l postgresql=postgres-cluster -L role
```

### Check Replication Lag

```bash
# Connect to primary and check replication status
kubectl exec -it -n ai-part-designer postgres-cluster-1 -- psql -U postgres -c "SELECT client_addr, state, sync_state, replay_lag FROM pg_stat_replication;"
```

Healthy lag should be < 100ms under normal conditions.

## Backup and Recovery

### Backup Schedule

- **Scheduled Backups**: Daily at 2:00 AM UTC
- **Retention**: 30 days (production), 7 days (staging)
- **Storage**: MinIO bucket `s3://backups/postgresql`
- **Method**: Physical backup with WAL archiving

### List Available Backups

```bash
# Get backup status
kubectl get backup -n ai-part-designer

# View scheduled backup configuration
kubectl describe schedulebackup -n ai-part-designer postgres-backup-daily
```

### Trigger Manual Backup

```bash
# Create an on-demand backup
cat <<EOF | kubectl apply -f -
apiVersion: postgresql.cnpg.io/v1
kind: Backup
metadata:
  name: postgres-manual-backup-$(date +%Y%m%d-%H%M%S)
  namespace: ai-part-designer
spec:
  cluster:
    name: postgres-cluster
  method: barmanObjectStore
EOF

# Check backup progress
kubectl get backup -n ai-part-designer
```

### Restore from Backup

**⚠️ WARNING**: This will destroy the current cluster. Only perform during maintenance windows.

#### Full Cluster Recovery

```bash
# 1. Scale down applications to prevent writes
kubectl scale deployment -n ai-part-designer backend --replicas=0
kubectl scale deployment -n ai-part-designer celery-worker --replicas=0
kubectl scale deployment -n ai-part-designer celery-beat --replicas=0

# 2. Delete existing cluster (DANGEROUS - ensure backup exists!)
kubectl delete cluster -n ai-part-designer postgres-cluster

# 3. Create new cluster with bootstrap from backup
cat <<EOF | kubectl apply -f -
apiVersion: postgresql.cnpg.io/v1
kind: Cluster
metadata:
  name: postgres-cluster
  namespace: ai-part-designer
spec:
  instances: 3
  bootstrap:
    recovery:
      source: postgres-cluster
      recoveryTarget:
        targetTime: "2024-03-20 15:30:00.00000+00"  # Optional: Point-in-time recovery
  externalClusters:
  - name: postgres-cluster
    barmanObjectStore:
      destinationPath: s3://backups/postgresql
      endpointURL: http://minio:9000
      s3Credentials:
        accessKeyId:
          name: postgres-backup-secret
          key: ACCESS_KEY_ID
        secretAccessKey:
          name: postgres-backup-secret
          key: ACCESS_SECRET_KEY
EOF

# 4. Wait for recovery to complete
kubectl get cluster -n ai-part-designer postgres-cluster -w

# 5. Verify data integrity
kubectl exec -it -n ai-part-designer postgres-cluster-1 -- psql -U postgres -d assemblematic_ai -c "SELECT COUNT(*) FROM users;"

# 6. Scale applications back up
kubectl scale deployment -n ai-part-designer backend --replicas=3
kubectl scale deployment -n ai-part-designer celery-worker --replicas=3
kubectl scale deployment -n ai-part-designer celery-beat --replicas=1
```

#### Point-in-Time Recovery (PITR)

To recover to a specific timestamp:

```yaml
bootstrap:
  recovery:
    source: postgres-cluster
    recoveryTarget:
      targetTime: "2024-03-20 15:30:00.00000+00"
      # OR use targetLSN for specific WAL position
      # targetLSN: "0/3000000"
```

### Verify Backup Configuration

```bash
# Check backup destination
kubectl exec -it -n ai-part-designer postgres-cluster-1 -- barman-cloud-backup-list \
  --endpoint-url http://minio:9000 \
  s3://backups/postgresql postgres-cluster

# Check WAL archiving
kubectl exec -it -n ai-part-designer postgres-cluster-1 -- psql -U postgres -c "SELECT archived_count, failed_count FROM pg_stat_archiver;"
```

## Failover Testing

### Automated Failover Test

CloudNativePG automatically promotes a replica to primary if the primary fails.

#### Test Procedure

```bash
# 1. Identify current primary
PRIMARY=$(kubectl get cluster -n ai-part-designer postgres-cluster -o jsonpath='{.status.currentPrimary}')
echo "Current primary: $PRIMARY"

# 2. Record replication lag
kubectl exec -it -n ai-part-designer $PRIMARY -- psql -U postgres -c "SELECT client_addr, replay_lag FROM pg_stat_replication;"

# 3. Simulate primary failure
kubectl delete pod -n ai-part-designer $PRIMARY

# 4. Monitor failover (should take < 60 seconds)
watch kubectl get cluster -n ai-part-designer postgres-cluster

# 5. Verify new primary
NEW_PRIMARY=$(kubectl get cluster -n ai-part-designer postgres-cluster -o jsonpath='{.status.currentPrimary}')
echo "New primary: $NEW_PRIMARY"

# 6. Check application connectivity
kubectl logs -n ai-part-designer -l app.kubernetes.io/name=backend --tail=20 | grep -i "database"

# 7. Verify old primary rejoins as replica
kubectl get pods -n ai-part-designer -l postgresql=postgres-cluster -L role
```

#### Expected Results

- **Failover Time**: < 60 seconds
- **Data Loss**: Zero (synchronous replication)
- **Application Impact**: Brief connection errors during switchover
- **Old Primary**: Rejoins as replica automatically

#### Rollback Failed Test

If failover fails or causes issues:

```bash
# Force promotion of specific pod
kubectl cnpg promote -n ai-part-designer postgres-cluster postgres-cluster-2

# Or restart entire cluster
kubectl delete pod -n ai-part-designer -l postgresql=postgres-cluster
```

### Manual Switchover (Planned Maintenance)

For planned maintenance, use switchover instead of failover:

```bash
# Initiate controlled switchover to specific replica
kubectl cnpg promote -n ai-part-designer postgres-cluster postgres-cluster-2

# Monitor switchover progress
kubectl get cluster -n ai-part-designer postgres-cluster -w
```

Switchover is graceful and ensures zero data loss.

## Monitoring and Alerting

### Prometheus Metrics

CloudNativePG exposes metrics for Prometheus monitoring:

**Key Metrics**:
- `cnpg_pg_replication_lag`: Replication lag in bytes
- `cnpg_pg_database_size_bytes`: Database size
- `cnpg_pg_stat_archiver_failed_count`: Failed WAL archives
- `cnpg_pg_stat_replication_replay_lag`: Replication lag in seconds
- `cnpg_pg_stat_database_xact_commit`: Transaction commits
- `cnpg_pg_stat_database_xact_rollback`: Transaction rollbacks

### View Metrics

```bash
# Port-forward Prometheus (if not exposed)
kubectl port-forward -n monitoring svc/prometheus 9090:9090

# Query metrics in browser
# http://localhost:9090/graph
```

### Custom Queries

The cluster uses custom monitoring queries defined in `postgres-monitoring-queries` ConfigMap:

```bash
# View custom queries
kubectl get configmap -n ai-part-designer postgres-monitoring-queries -o yaml
```

### Recommended Alerts

Configure these alerts in Prometheus AlertManager:

```yaml
groups:
- name: postgres
  rules:
  - alert: PostgreSQLDown
    expr: cnpg_pg_up == 0
    for: 1m
    severity: critical
    
  - alert: PostgreSQLReplicationLag
    expr: cnpg_pg_stat_replication_replay_lag > 10
    for: 5m
    severity: warning
    
  - alert: PostgreSQLConnectionsHigh
    expr: cnpg_pg_stat_database_numbackends / cnpg_pg_settings_max_connections > 0.8
    for: 5m
    severity: warning
    
  - alert: PostgreSQLBackupFailed
    expr: increase(cnpg_pg_stat_archiver_failed_count[1h]) > 0
    for: 1h
    severity: critical
```

### View Logs

```bash
# View all PostgreSQL logs
kubectl logs -n ai-part-designer -l postgresql=postgres-cluster --tail=100 -f

# View specific pod logs
kubectl logs -n ai-part-designer postgres-cluster-1 -f

# View pooler logs
kubectl logs -n ai-part-designer -l cnpg.io/poolerName=postgres-pooler --tail=50
```

## Troubleshooting

### Cluster Not Starting

**Symptoms**: Pods in CrashLoopBackOff or Pending state

**Diagnosis**:
```bash
# Check pod status
kubectl get pods -n ai-part-designer -l postgresql=postgres-cluster

# Describe problematic pod
kubectl describe pod -n ai-part-designer postgres-cluster-1

# Check events
kubectl get events -n ai-part-designer --sort-by='.lastTimestamp' | grep postgres
```

**Common Causes**:
1. **PVC binding issues**: Check PV/PVC status
2. **Resource constraints**: Check node resources
3. **Init container failures**: Check init container logs
4. **Configuration errors**: Review cluster manifest

**Solutions**:
```bash
# Check PVC status
kubectl get pvc -n ai-part-designer -l postgresql=postgres-cluster

# Check node resources
kubectl top nodes

# View init container logs
kubectl logs -n ai-part-designer postgres-cluster-1 -c bootstrap-controller
```

### Replication Lag High

**Symptoms**: `replay_lag` > 10 seconds

**Diagnosis**:
```bash
# Check replication status
kubectl exec -it -n ai-part-designer postgres-cluster-1 -- psql -U postgres -c "
  SELECT 
    client_addr, 
    state, 
    sync_state,
    pg_wal_lsn_diff(sent_lsn, replay_lsn) AS lag_bytes,
    replay_lag 
  FROM pg_stat_replication;
"
```

**Common Causes**:
1. **Network issues**: Check network latency
2. **Disk I/O saturation**: Check disk performance
3. **Heavy write load**: Check transaction rate

**Solutions**:
```bash
# Check disk I/O
kubectl exec -it -n ai-part-designer postgres-cluster-2 -- iostat -xz 5

# Increase WAL sender processes (if needed)
kubectl exec -it -n ai-part-designer postgres-cluster-1 -- psql -U postgres -c "ALTER SYSTEM SET max_wal_senders = 10;"
kubectl exec -it -n ai-part-designer postgres-cluster-1 -- psql -U postgres -c "SELECT pg_reload_conf();"
```

### Connection Pool Exhausted

**Symptoms**: Applications report "too many connections"

**Diagnosis**:
```bash
# Check current connections
kubectl exec -it -n ai-part-designer postgres-cluster-1 -- psql -U postgres -c "
  SELECT 
    datname, 
    numbackends,
    (SELECT setting::int FROM pg_settings WHERE name='max_connections') AS max_connections
  FROM pg_stat_database;
"

# Check pooler status
kubectl logs -n ai-part-designer -l cnpg.io/poolerName=postgres-pooler --tail=20 | grep -i "pool"
```

**Solutions**:

1. **Increase pooler default_pool_size**:
```bash
# Edit pooler configuration
kubectl edit pooler -n ai-part-designer postgres-pooler
# Increase default_pool_size from 25 to 50
```

2. **Scale pooler replicas**:
```bash
kubectl edit pooler -n ai-part-designer postgres-pooler
# Change instances from 2 to 3
```

3. **Increase PostgreSQL max_connections**:
```bash
kubectl exec -it -n ai-part-designer postgres-cluster-1 -- psql -U postgres -c "ALTER SYSTEM SET max_connections = 300;"
kubectl exec -it -n ai-part-designer postgres-cluster-1 -- psql -U postgres -c "SELECT pg_reload_conf();"
```

### Backup Failures

**Symptoms**: ScheduledBackup shows failed status

**Diagnosis**:
```bash
# Check backup status
kubectl get backup -n ai-part-designer

# View backup logs
kubectl logs -n ai-part-designer -l postgresql=postgres-cluster -c backup --tail=50

# Check S3 credentials
kubectl get secret -n ai-part-designer postgres-backup-secret -o yaml

# Verify MinIO connectivity
kubectl exec -it -n ai-part-designer postgres-cluster-1 -- \
  curl -I http://minio:9000/minio/health/ready
```

**Common Causes**:
1. **Invalid S3 credentials**: Update `postgres-backup-secret`
2. **MinIO unavailable**: Check MinIO service status
3. **Insufficient permissions**: Verify bucket permissions
4. **Disk space**: Check MinIO storage capacity

**Solutions**:
```bash
# Update S3 credentials
kubectl create secret generic postgres-backup-secret \
  --from-literal=ACCESS_KEY_ID=minio \
  --from-literal=ACCESS_SECRET_KEY=new-password \
  -n ai-part-designer \
  --dry-run=client -o yaml | kubectl apply -f -

# Restart cluster to pick up new credentials
kubectl rollout restart statefulset -n ai-part-designer -l postgresql=postgres-cluster
```

### Data Corruption

**Symptoms**: PostgreSQL fails to start with corruption errors

**⚠️ CRITICAL**: This requires immediate action

**Diagnosis**:
```bash
# Check pod logs for corruption messages
kubectl logs -n ai-part-designer postgres-cluster-1 | grep -i "corrupt\|panic\|fatal"

# Check PostgreSQL data directory integrity
kubectl exec -it -n ai-part-designer postgres-cluster-1 -- pg_controldata /var/lib/postgresql/data
```

**Recovery**:
```bash
# 1. Stop all writes immediately
kubectl scale deployment -n ai-part-designer backend --replicas=0
kubectl scale deployment -n ai-part-designer celery-worker --replicas=0

# 2. Assess data loss scope
# If only one replica is corrupted, promote a healthy replica

# 3. If primary is corrupted, restore from backup (see Backup and Recovery section)

# 4. If corruption is recent, use PITR to recover to point before corruption
```

## Maintenance Procedures

### Upgrade PostgreSQL Minor Version

CloudNativePG handles minor version upgrades automatically.

```bash
# Update cluster spec with new image
kubectl patch cluster -n ai-part-designer postgres-cluster --type='json' \
  -p='[{"op": "replace", "path": "/spec/imageName", "value": "ghcr.io/cloudnative-pg/postgresql:15.5"}]'

# Monitor rolling update
kubectl get pods -n ai-part-designer -l postgresql=postgres-cluster -w
```

The operator performs a rolling update, promoting replicas one at a time.

### Upgrade PostgreSQL Major Version

Major version upgrades require a new cluster with logical replication or backup/restore.

**Recommended Method**: Blue-Green deployment with logical replication

```bash
# 1. Create new cluster with new major version
kubectl apply -f postgres-cluster-v16.yaml

# 2. Set up logical replication from old to new
# 3. Verify data sync
# 4. Switch application connection strings
# 5. Decommission old cluster
```

See CloudNativePG documentation for detailed major upgrade procedures.

### Scale Cluster

```bash
# Scale to 5 replicas
kubectl patch cluster -n ai-part-designer postgres-cluster --type='json' \
  -p='[{"op": "replace", "path": "/spec/instances", "value": 5}]'

# Monitor new pods coming online
kubectl get pods -n ai-part-designer -l postgresql=postgres-cluster -w
```

### Increase Storage Size

```bash
# 1. Ensure StorageClass supports volume expansion
kubectl get storageclass

# 2. Patch PVC size
kubectl patch pvc -n ai-part-designer postgres-cluster-1 \
  -p '{"spec":{"resources":{"requests":{"storage":"200Gi"}}}}'

# 3. Repeat for all cluster PVCs
kubectl patch pvc -n ai-part-designer postgres-cluster-2 \
  -p '{"spec":{"resources":{"requests":{"storage":"200Gi"}}}}'

# 4. Update cluster spec
kubectl patch cluster -n ai-part-designer postgres-cluster --type='json' \
  -p='[{"op": "replace", "path": "/spec/storage/size", "value": "200Gi"}]'
```

### Vacuum and Analyze

```bash
# Manual vacuum (should be run during low traffic)
kubectl exec -it -n ai-part-designer postgres-cluster-1 -- psql -U postgres -d assemblematic_ai -c "VACUUM ANALYZE;"

# Enable auto-vacuum (should already be enabled)
kubectl exec -it -n ai-part-designer postgres-cluster-1 -- psql -U postgres -c "ALTER SYSTEM SET autovacuum = on;"
```

### Rotate Passwords

```bash
# 1. Update secret
kubectl create secret generic postgres-app-user \
  --from-literal=username=app \
  --from-literal=password=NEW_SECURE_PASSWORD \
  -n ai-part-designer \
  --dry-run=client -o yaml | kubectl apply -f -

# 2. Restart pooler to pick up new credentials
kubectl rollout restart deployment -n ai-part-designer -l cnpg.io/poolerName=postgres-pooler

# 3. Update application secrets
kubectl create secret generic backend-secrets \
  --from-literal=postgres-password=NEW_SECURE_PASSWORD \
  -n ai-part-designer \
  --dry-run=client -o yaml | kubectl apply -f -

# 4. Restart applications
kubectl rollout restart deployment -n ai-part-designer backend
kubectl rollout restart deployment -n ai-part-designer celery-worker
kubectl rollout restart deployment -n ai-part-designer celery-beat
```

## Emergency Procedures

### Complete Cluster Failure

If all PostgreSQL pods are down and cannot recover:

```bash
# 1. Check cluster status
kubectl get cluster -n ai-part-designer postgres-cluster

# 2. Check all pods
kubectl get pods -n ai-part-designer -l postgresql=postgres-cluster

# 3. If all pods failed, check for common issues
kubectl describe cluster -n ai-part-designer postgres-cluster

# 4. If recovery is impossible, restore from backup (see Backup and Recovery)

# 5. Create incident report with:
#    - Timeline of events
#    - Root cause analysis
#    - Data loss assessment
#    - Corrective actions
```

### Data Loss Event

If data loss is detected:

```bash
# 1. Stop all writes immediately
kubectl scale deployment -n ai-part-designer backend --replicas=0
kubectl scale deployment -n ai-part-designer celery-worker --replicas=0
kubectl scale deployment -n ai-part-designer celery-beat --replicas=0

# 2. Identify last known good backup
kubectl get backup -n ai-part-designer --sort-by=.metadata.creationTimestamp

# 3. Assess data loss window
# Time between last backup and incident

# 4. Notify stakeholders of data loss scope

# 5. Restore from backup with PITR if possible

# 6. Document incident with:
#    - Data loss assessment
#    - Affected users/transactions
#    - Recovery actions taken
#    - Prevention measures
```

## Performance Tuning

### Connection Pool Tuning

For high-traffic scenarios:

```yaml
# Adjust pooler parameters
pgbouncer:
  parameters:
    default_pool_size: "50"        # Increase from 25
    max_client_conn: "2000"        # Increase from 1000
    reserve_pool_size: "10"        # Increase from 5
```

### PostgreSQL Configuration

For production workloads:

```sql
-- Increase shared buffers for better caching
ALTER SYSTEM SET shared_buffers = '512MB';

-- Increase work memory for complex queries
ALTER SYSTEM SET work_mem = '8MB';

-- Increase effective cache size
ALTER SYSTEM SET effective_cache_size = '2GB';

-- Apply changes
SELECT pg_reload_conf();
```

### Monitoring Queries

Add custom queries to `postgres-monitoring-queries` ConfigMap for application-specific metrics.

## References

- [CloudNativePG Documentation](https://cloudnative-pg.io/documentation/)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [PgBouncer Documentation](https://www.pgbouncer.org/)
- [Kubernetes StatefulSets](https://kubernetes.io/docs/concepts/workloads/controllers/statefulset/)

## Support

For issues not covered in this guide:
1. Check CloudNativePG operator logs: `kubectl logs -n cnpg-system -l app.kubernetes.io/name=cloudnative-pg`
2. Consult [CloudNativePG GitHub Issues](https://github.com/cloudnative-pg/cloudnative-pg/issues)
3. Contact platform team via incident management system

---

**Last Updated**: 2024-03-20  
**Version**: 1.0  
**Maintainer**: Platform Operations Team
