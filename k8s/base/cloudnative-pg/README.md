# CloudNativePG PostgreSQL Deployment

This directory contains the CloudNativePG PostgreSQL cluster configuration for the AI Part Designer platform.

## Overview

CloudNativePG is a Kubernetes operator that manages PostgreSQL clusters with built-in high availability, automated backups, and self-healing capabilities.

### Features

- **High Availability**: 3-node cluster with automatic failover
- **Connection Pooling**: PgBouncer integration for efficient connection management
- **Automated Backups**: Daily backups to MinIO with configurable retention
- **Monitoring**: Prometheus metrics and custom queries
- **Self-Healing**: Automatic pod recovery and replica synchronization

## Architecture

```
                                    ┌──────────────────┐
                                    │   Applications   │
                                    │ (Backend/Workers)│
                                    └────────┬─────────┘
                                             │
                                    ┌────────▼─────────┐
                                    │  PgBouncer Pool  │
                                    │    (2 pods)      │
                                    └────────┬─────────┘
                                             │
                        ┌────────────────────┼────────────────────┐
                        │                    │                    │
                   ┌────▼────┐          ┌───▼────┐          ┌────▼────┐
                   │ Primary │─────────▶│Replica │          │Replica │
                   │  (R/W)  │          │  (RO)  │          │  (RO)  │
                   └────┬────┘          └────────┘          └─────────┘
                        │
                        │ Continuous Backup
                        ▼
                   ┌─────────┐
                   │  MinIO  │
                   │  (S3)   │
                   └─────────┘
```

## Files

### Helm Templates (`helm/ai-part-designer/templates/postgresql/`)

- `cluster.yaml` - PostgreSQL Cluster custom resource
- `pooler.yaml` - PgBouncer Pooler configuration
- `scheduled-backup.yaml` - Automated backup schedule
- `secrets.yaml` - Database credentials (use external secrets in production)
- `backup-secret.yaml` - S3/MinIO credentials for backups
- `service.yaml` - Kubernetes services for database access
- `servicemonitor.yaml` - Prometheus monitoring configuration
- `network-policy.yaml` - Network security policies

### Kustomize Base (`k8s/base/cloudnative-pg/`)

Raw Kubernetes manifests for direct deployment with Kustomize (without Helm).

## Installation

### Prerequisites

1. **Kubernetes Cluster**: v1.24+
2. **CloudNativePG Operator**: Install via Helm chart dependency or separately
3. **MinIO**: For backup storage (see `k8s/base/minio/`)
4. **Prometheus Operator** (optional): For monitoring with ServiceMonitor

### Option 1: Helm Chart (Recommended)

The CloudNativePG cluster is automatically installed when deploying via Helm with `installPostgres: true`.

```bash
# Deploy production
helm install ai-part-designer ./helm/ai-part-designer \
  --namespace ai-part-designer \
  --create-namespace \
  --values helm/ai-part-designer/values-production.yaml

# Deploy staging
helm install ai-part-designer ./helm/ai-part-designer \
  --namespace ai-part-designer-staging \
  --create-namespace \
  --values helm/ai-part-designer/values-staging.yaml

# Deploy development
helm install ai-part-designer ./helm/ai-part-designer \
  --namespace ai-part-designer-dev \
  --create-namespace \
  --values helm/ai-part-designer/values-dev.yaml
```

### Option 2: Kustomize

```bash
# Deploy with kustomize
kubectl apply -k k8s/overlays/production

# Or build and review first
kubectl kustomize k8s/overlays/production
```

### Option 3: Install Operator Separately

If not using the Helm chart dependency:

```bash
# Add CloudNativePG Helm repository
helm repo add cnpg https://cloudnative-pg.github.io/charts
helm repo update

# Install operator
helm install cnpg \
  --namespace cnpg-system \
  --create-namespace \
  cnpg/cloudnative-pg

# Then apply cluster manifests
kubectl apply -f k8s/base/cloudnative-pg/
```

## Configuration

### Environment-Specific Settings

| Setting | Development | Staging | Production |
|---------|-------------|---------|------------|
| Instances | 1 | 2 | 3 |
| Storage | 10Gi | 50Gi | 100Gi |
| Backup Enabled | No | Yes (7d) | Yes (30d) |
| Pooler Enabled | No | Yes | Yes |
| Resources (CPU) | 100m/500m | 250m/1000m | 1000m/2000m |
| Resources (Mem) | 256Mi/1Gi | 512Mi/2Gi | 2Gi/4Gi |

### Connection Strings

Applications should connect via the pooler service for best performance:

```bash
# Connection via pooler (recommended)
postgres-pooler-service.ai-part-designer.svc.cluster.local:5432

# Direct connection to primary (use sparingly)
postgres-service.ai-part-designer.svc.cluster.local:5432
```

### Database Credentials

Credentials are stored in Kubernetes secrets:

- `postgres-superuser` - PostgreSQL superuser (postgres)
- `postgres-app-user` - Application user (app)
- `postgres-backup-secret` - MinIO/S3 credentials for backups

**⚠️ IMPORTANT**: In production, use External Secrets Operator or similar to inject credentials from a secure vault (OpenBao, Vault, AWS Secrets Manager, etc.).

## Backup and Recovery

### Backup Schedule

- **Production**: Daily at 2:00 AM UTC, 30-day retention
- **Staging**: Daily at 3:00 AM UTC, 7-day retention
- **Development**: Disabled

### Manual Backup

```bash
# Trigger immediate backup
kubectl apply -f - <<EOF
apiVersion: postgresql.cnpg.io/v1
kind: Backup
metadata:
  name: postgres-manual-$(date +%Y%m%d-%H%M%S)
  namespace: ai-part-designer
spec:
  cluster:
    name: postgres-cluster
  method: barmanObjectStore
EOF

# Check backup status
kubectl get backup -n ai-part-designer
```

### Restore from Backup

See [CloudNativePG Operations Guide](../../docs/operations/cloudnative-pg-operations.md#backup-and-recovery) for detailed recovery procedures.

## Monitoring

### Prometheus Metrics

The cluster exposes Prometheus metrics on port 9187:

- `cnpg_pg_replication_lag` - Replication lag in bytes
- `cnpg_pg_database_size_bytes` - Database size
- `cnpg_pg_stat_database_xact_commit` - Transaction commits
- `cnpg_pg_stat_database_xact_rollback` - Transaction rollbacks

### Custom Queries

Custom monitoring queries are defined in `postgres-monitoring-queries` ConfigMap:

- Database size metrics
- Table bloat metrics
- Connection pool statistics
- Replication lag

### Grafana Dashboards

Import the official CloudNativePG dashboard:

```bash
# Dashboard ID: 20417
# https://grafana.com/grafana/dashboards/20417
```

## High Availability

### Automatic Failover

CloudNativePG automatically promotes a replica to primary if the primary fails:

- **Detection Time**: < 30 seconds
- **Failover Time**: < 60 seconds
- **Data Loss**: Zero (synchronous replication)

### Manual Switchover

For planned maintenance:

```bash
# Promote specific replica
kubectl cnpg promote -n ai-part-designer postgres-cluster postgres-cluster-2

# Monitor switchover
kubectl get cluster -n ai-part-designer postgres-cluster -w
```

### Scaling

```bash
# Scale to 5 instances
kubectl patch cluster -n ai-part-designer postgres-cluster --type='json' \
  -p='[{"op": "replace", "path": "/spec/instances", "value": 5}]'
```

## Troubleshooting

### Check Cluster Status

```bash
# Get cluster health
kubectl get cluster -n ai-part-designer postgres-cluster

# View all pods
kubectl get pods -n ai-part-designer -l postgresql=postgres-cluster

# Check replication status
kubectl exec -it -n ai-part-designer postgres-cluster-1 -- \
  psql -U postgres -c "SELECT * FROM pg_stat_replication;"
```

### Common Issues

#### Pods Not Starting

```bash
# Check pod events
kubectl describe pod -n ai-part-designer postgres-cluster-1

# Check PVC status
kubectl get pvc -n ai-part-designer -l postgresql=postgres-cluster

# View logs
kubectl logs -n ai-part-designer postgres-cluster-1
```

#### Replication Lag

```bash
# Check lag
kubectl exec -it -n ai-part-designer postgres-cluster-1 -- \
  psql -U postgres -c "
    SELECT client_addr, replay_lag 
    FROM pg_stat_replication;
  "
```

#### Connection Issues

```bash
# Test connection from backend pod
kubectl exec -it -n ai-part-designer $(kubectl get pod -n ai-part-designer -l app.kubernetes.io/name=backend -o name | head -1) -- \
  psql postgresql://app:PASSWORD@postgres-pooler-service:5432/assemblematic_ai -c "SELECT version();"

# Check pooler logs
kubectl logs -n ai-part-designer -l cnpg.io/poolerName=postgres-pooler
```

## Security

### Network Policies

Network policies restrict database access to:

- Backend API pods
- Celery worker pods
- Celery beat pods
- Monitoring (Prometheus)
- Cluster members (for replication)

### Security Best Practices

1. ✅ Use External Secrets Operator for credential management
2. ✅ Enable TLS/SSL for connections (configure in cluster spec)
3. ✅ Rotate passwords regularly
4. ✅ Use connection pooler to limit direct database access
5. ✅ Enable PostgreSQL audit logging
6. ✅ Restrict superuser access
7. ✅ Use read-only replicas for reporting queries
8. ✅ Encrypt backups at rest in MinIO

## Performance Tuning

### PostgreSQL Parameters

Key parameters configured for production:

```yaml
postgresql:
  parameters:
    max_connections: "200"
    shared_buffers: "512MB"
    effective_cache_size: "2GB"
    maintenance_work_mem: "128MB"
    checkpoint_completion_target: "0.9"
```

### PgBouncer Parameters

```yaml
pgbouncer:
  parameters:
    default_pool_size: "25"
    max_client_conn: "1000"
    server_idle_timeout: "600"
```

### Resource Limits

Production recommendations:

```yaml
resources:
  requests:
    memory: "2Gi"
    cpu: "1000m"
  limits:
    memory: "4Gi"
    cpu: "2000m"
```

## Upgrade Procedures

### Minor Version Upgrade

CloudNativePG handles minor version upgrades automatically via rolling updates.

### Major Version Upgrade

See [Operations Guide](../../docs/operations/cloudnative-pg-operations.md#upgrade-postgresql-major-version) for detailed procedures.

## References

- [CloudNativePG Documentation](https://cloudnative-pg.io/documentation/)
- [CloudNativePG Helm Chart](https://github.com/cloudnative-pg/charts)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [PgBouncer Documentation](https://www.pgbouncer.org/)
- [Operations Guide](../../docs/operations/cloudnative-pg-operations.md)

## Support

For operational issues, consult the [CloudNativePG Operations Guide](../../docs/operations/cloudnative-pg-operations.md) or contact the platform team.

---

**Maintained by**: Platform Operations Team  
**Last Updated**: 2024-03-20
