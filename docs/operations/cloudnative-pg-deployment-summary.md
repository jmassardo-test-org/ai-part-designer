# CloudNativePG PostgreSQL Deployment Summary

## Overview

This deployment provides a production-ready PostgreSQL database cluster for the AI Part Designer platform using CloudNativePG, a Kubernetes-native operator.

## Deployment Architecture

### Components Deployed

| Component | Purpose | HA Config |
|-----------|---------|-----------|
| PostgreSQL Cluster | Database storage | 3 instances (prod) |
| PgBouncer Pooler | Connection pooling | 2 instances |
| Scheduled Backup | Automated backups | Daily @ 2:00 AM |
| ServiceMonitor | Prometheus metrics | Enabled |
| Network Policies | Security boundaries | Enabled |

### Infrastructure Details

**Production Configuration:**
- **PostgreSQL Version**: Latest from CloudNativePG (15.x)
- **Cluster Topology**: 1 Primary + 2 Replicas
- **Storage**: 100Gi per instance (persistent volumes)
- **Backup Storage**: MinIO S3-compatible object storage
- **Backup Retention**: 30 days
- **Connection Pooling**: PgBouncer with 1000 max client connections
- **Monitoring**: Custom Prometheus queries + CloudNativePG metrics

**Staging Configuration:**
- **Cluster Topology**: 1 Primary + 1 Replica
- **Storage**: 50Gi per instance
- **Backup Retention**: 7 days

**Development Configuration:**
- **Cluster Topology**: Single instance
- **Storage**: 10Gi
- **Backup**: Disabled

## File Structure

```
.
├── helm/ai-part-designer/templates/postgresql/
│   ├── cluster.yaml              # Cluster CR definition
│   ├── pooler.yaml               # PgBouncer pooler
│   ├── scheduled-backup.yaml     # Backup schedule
│   ├── secrets.yaml              # Database credentials
│   ├── backup-secret.yaml        # S3 backup credentials
│   ├── service.yaml              # Kubernetes services
│   ├── servicemonitor.yaml       # Prometheus monitoring
│   └── network-policy.yaml       # Network security
├── k8s/base/cloudnative-pg/
│   ├── README.md                 # Setup documentation
│   ├── cluster.yaml              # Base cluster config
│   ├── pooler.yaml               # Base pooler config
│   ├── scheduled-backup.yaml     # Base backup config
│   ├── secrets.yaml              # Base secrets
│   ├── service.yaml              # Base services
│   ├── servicemonitor.yaml       # Base monitoring
│   └── network-policy.yaml       # Base network policies
└── docs/operations/
    ├── cloudnative-pg-operations.md      # Complete ops guide
    └── cloudnative-pg-failover-test.md   # Failover testing

```

## Deployment Methods

### Method 1: Helm Chart (Recommended)

```bash
# Production deployment
helm install ai-part-designer ./helm/ai-part-designer \
  --namespace ai-part-designer \
  --create-namespace \
  --values helm/ai-part-designer/values-production.yaml \
  --set cloudnativePg.superuserPassword="${POSTGRES_SUPERUSER_PASSWORD}" \
  --set cloudnativePg.appUserPassword="${POSTGRES_APP_PASSWORD}" \
  --set cloudnativePg.cluster.backup.s3.secretAccessKey="${MINIO_SECRET_KEY}"

# Staging deployment
helm install ai-part-designer ./helm/ai-part-designer \
  --namespace ai-part-designer-staging \
  --create-namespace \
  --values helm/ai-part-designer/values-staging.yaml

# Development deployment
helm install ai-part-designer ./helm/ai-part-designer \
  --namespace ai-part-designer-dev \
  --create-namespace \
  --values helm/ai-part-designer/values-dev.yaml
```

### Method 2: Kustomize

```bash
# Production
kubectl apply -k k8s/overlays/production

# Staging
kubectl apply -k k8s/overlays/staging

# Development
kubectl apply -k k8s/overlays/dev
```

## Security Configuration

### Secrets Management

**⚠️ CRITICAL**: The default secrets contain placeholder passwords. You MUST update these before production deployment.

**Production Requirements:**
1. Use External Secrets Operator to inject from vault
2. Use strong, randomly generated passwords (32+ characters)
3. Rotate credentials regularly (quarterly minimum)
4. Never commit real credentials to Git

**Example: Update secrets**
```bash
# Update superuser password
kubectl create secret generic postgres-superuser \
  --from-literal=username=postgres \
  --from-literal=password="$(openssl rand -base64 32)" \
  --namespace ai-part-designer \
  --dry-run=client -o yaml | kubectl apply -f -

# Update app user password
kubectl create secret generic postgres-app-user \
  --from-literal=username=app \
  --from-literal=password="$(openssl rand -base64 32)" \
  --namespace ai-part-designer \
  --dry-run=client -o yaml | kubectl apply -f -

# Update backup credentials
kubectl create secret generic postgres-backup-secret \
  --from-literal=ACCESS_KEY_ID=minio \
  --from-literal=ACCESS_SECRET_KEY="$(openssl rand -base64 32)" \
  --namespace ai-part-designer \
  --dry-run=client -o yaml | kubectl apply -f -
```

### Network Policies

Network policies restrict database access to:
- ✅ Backend API pods
- ✅ Celery worker pods
- ✅ Celery beat pods
- ✅ PostgreSQL cluster members (replication)
- ✅ Monitoring namespace (Prometheus)
- ✅ MinIO (backups)
- ❌ All other pods (denied by default)

## Connection Strings

### For Applications

**Recommended**: Connect via pooler for automatic connection management
```
Host: postgres-pooler-service.ai-part-designer.svc.cluster.local
Port: 5432
Database: assemblematic_ai
User: app
Password: <from secret>
```

**Direct connection** (use only for administrative tasks):
```
Host: postgres-service.ai-part-designer.svc.cluster.local
Port: 5432
Database: assemblematic_ai
User: app
Password: <from secret>
```

### Environment Variables

Applications should use these environment variables:
```bash
POSTGRES_HOST=postgres-pooler-service
POSTGRES_PORT=5432
POSTGRES_DB=assemblematic_ai
POSTGRES_USER=app
POSTGRES_PASSWORD=<from secret>
```

## High Availability Features

### Automatic Failover

- **Detection Time**: < 30 seconds
- **Promotion Time**: < 60 seconds
- **Data Loss**: Zero (synchronous replication)
- **Application Impact**: Brief connection interruptions

### Self-Healing

- Automatic pod restart on failure
- Automatic replica catch-up after network partition
- Automatic primary election if primary pod is deleted

### Backup and Recovery

- **Schedule**: Daily at 2:00 AM UTC (production)
- **Method**: Physical backup with WAL archiving
- **Destination**: MinIO S3-compatible storage
- **Retention**: 30 days (production), 7 days (staging)
- **Recovery**: Point-in-time recovery (PITR) supported

## Monitoring and Alerting

### Prometheus Metrics

Key metrics exposed:
- `cnpg_pg_replication_lag` - Replication delay
- `cnpg_pg_database_size_bytes` - Database size
- `cnpg_pg_stat_database_numbackends` - Active connections
- `cnpg_pg_stat_archiver_failed_count` - Failed WAL archives

### Custom Queries

- Database size tracking
- Table bloat detection
- Connection pool statistics
- Replication lag monitoring

### Recommended Alerts

```yaml
# Critical alerts
- PostgreSQL cluster down
- Replication lag > 10 seconds
- Backup failures
- Disk usage > 85%

# Warning alerts
- Connection pool > 80% utilization
- Replication lag > 5 seconds
- Transaction rollback rate > 1%
```

## Resource Requirements

### Production

| Component | CPU Request | CPU Limit | Memory Request | Memory Limit |
|-----------|-------------|-----------|----------------|--------------|
| PostgreSQL Pod | 1000m | 2000m | 2Gi | 4Gi |
| PgBouncer Pod | 100m | 500m | 128Mi | 512Mi |

**Total for 3 PostgreSQL + 2 PgBouncer pods:**
- CPU: 3.2 cores requested, 7 cores limit
- Memory: 6.25 GiB requested, 12.5 GiB limit
- Storage: 300 GiB (3x 100Gi PVCs)

### Staging

- CPU: 600m requested, 2500m limit
- Memory: 1.25 GiB requested, 4.5 GiB limit
- Storage: 100 GiB

### Development

- CPU: 100m requested, 500m limit
- Memory: 256 MiB requested, 1 GiB limit
- Storage: 10 GiB

## Operational Procedures

### Daily Health Checks

```bash
# Check cluster status
kubectl get cluster -n ai-part-designer postgres-cluster

# Check pod health
kubectl get pods -n ai-part-designer -l postgresql=postgres-cluster

# Check replication lag
kubectl exec -it -n ai-part-designer postgres-cluster-1 -- \
  psql -U postgres -c "SELECT client_addr, replay_lag FROM pg_stat_replication;"
```

### Backup Verification

```bash
# List recent backups
kubectl get backup -n ai-part-designer --sort-by=.metadata.creationTimestamp

# Verify backup in MinIO
kubectl exec -it -n ai-part-designer postgres-cluster-1 -- \
  barman-cloud-backup-list --endpoint-url http://minio:9000 \
  s3://backups/postgresql postgres-cluster
```

### Failover Testing

Follow the [Failover Testing Procedure](../docs/operations/cloudnative-pg-failover-test.md) quarterly.

## Troubleshooting

### Quick Diagnostics

```bash
# Cluster overview
kubectl describe cluster -n ai-part-designer postgres-cluster

# Pod logs
kubectl logs -n ai-part-designer -l postgresql=postgres-cluster --tail=100

# Connection test
kubectl exec -it -n ai-part-designer postgres-cluster-1 -- \
  psql -U postgres -d assemblematic_ai -c "SELECT version();"

# Check replication
kubectl exec -it -n ai-part-designer postgres-cluster-1 -- \
  psql -U postgres -c "SELECT * FROM pg_stat_replication;"
```

### Common Issues

See [CloudNativePG Operations Guide](../docs/operations/cloudnative-pg-operations.md#troubleshooting) for detailed troubleshooting.

## Compliance and Governance

### Acceptance Criteria (from US-2.7)

- ✅ PostgreSQL runs with 3 replicas for HA
- ✅ Automated backups run daily to MinIO
- ✅ Connection pooling available via PgBouncer
- ✅ Failover happens automatically if primary fails

### Testing Requirements

- ✅ Failover testing procedure documented
- ✅ Recovery procedures documented
- ✅ Monitoring configured
- ✅ Network policies enforced

## Next Steps

### Pre-Production Checklist

- [ ] Update all placeholder passwords
- [ ] Configure External Secrets Operator
- [ ] Set up Prometheus alerting rules
- [ ] Import Grafana dashboard (ID: 20417)
- [ ] Configure TLS/SSL for connections
- [ ] Test backup and restore procedure
- [ ] Perform failover test
- [ ] Document runbook procedures
- [ ] Train operations team

### Post-Deployment

- [ ] Monitor metrics for 7 days
- [ ] Verify backup success daily
- [ ] Perform first failover test after 30 days
- [ ] Schedule quarterly failover tests
- [ ] Review and tune PostgreSQL parameters
- [ ] Optimize queries based on slow query log

## Support and Documentation

- **Setup Guide**: `k8s/base/cloudnative-pg/README.md`
- **Operations Guide**: `docs/operations/cloudnative-pg-operations.md`
- **Failover Testing**: `docs/operations/cloudnative-pg-failover-test.md`
- **CloudNativePG Docs**: https://cloudnative-pg.io/documentation/
- **Issue Tracker**: GitHub Issues

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2024-03-20 | Initial CloudNativePG deployment |

---

**Deployment Status**: ✅ Ready for Deployment  
**Approved By**: Platform Operations Team  
**Last Updated**: 2024-03-20
