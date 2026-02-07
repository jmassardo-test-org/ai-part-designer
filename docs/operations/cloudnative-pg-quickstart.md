# CloudNativePG Quick Start Guide

This guide helps you quickly deploy and verify the CloudNativePG PostgreSQL cluster.

## Prerequisites

- Kubernetes cluster (v1.24+)
- kubectl configured
- Helm 3.x installed
- MinIO deployed and accessible

## Quick Deploy (Production)

### Step 1: Update Secrets

**⚠️ REQUIRED**: Generate strong passwords before deploying!

```bash
# Generate passwords
export POSTGRES_SUPERUSER_PASSWORD=$(openssl rand -base64 32)
export POSTGRES_APP_PASSWORD=$(openssl rand -base64 32)
export MINIO_SECRET_KEY=$(openssl rand -base64 32)

echo "Save these passwords in your password manager!"
echo "Superuser: $POSTGRES_SUPERUSER_PASSWORD"
echo "App User: $POSTGRES_APP_PASSWORD"
echo "MinIO: $MINIO_SECRET_KEY"
```

### Step 2: Deploy with Helm

```bash
# Deploy to production namespace
helm install ai-part-designer ./helm/ai-part-designer \
  --namespace ai-part-designer \
  --create-namespace \
  --values helm/ai-part-designer/values-production.yaml \
  --set cloudnativePg.superuserPassword="${POSTGRES_SUPERUSER_PASSWORD}" \
  --set cloudnativePg.appUserPassword="${POSTGRES_APP_PASSWORD}" \
  --set cloudnativePg.cluster.backup.s3.secretAccessKey="${MINIO_SECRET_KEY}"

# Monitor deployment
kubectl get cluster -n ai-part-designer postgres-cluster -w
```

### Step 3: Verify Deployment

```bash
# Check cluster status (should show "Cluster in healthy state")
kubectl get cluster -n ai-part-designer postgres-cluster

# Check all pods are running (should see 3 postgres + 2 pooler pods)
kubectl get pods -n ai-part-designer -l postgresql=postgres-cluster
kubectl get pods -n ai-part-designer -l cnpg.io/poolerName=postgres-pooler

# Expected output:
# NAME                 READY   STATUS    AGE
# postgres-cluster-1   1/1     Running   5m
# postgres-cluster-2   1/1     Running   5m
# postgres-cluster-3   1/1     Running   5m
# postgres-pooler-xxx  1/1     Running   5m
# postgres-pooler-yyy  1/1     Running   5m
```

### Step 4: Test Connection

```bash
# Get primary pod
PRIMARY=$(kubectl get cluster -n ai-part-designer postgres-cluster -o jsonpath='{.status.currentPrimary}')

# Test connection
kubectl exec -it -n ai-part-designer $PRIMARY -- \
  psql -U postgres -d assemblematic_ai -c "SELECT version();"

# Should output PostgreSQL version information
```

### Step 5: Verify Replication

```bash
# Check replication status
kubectl exec -it -n ai-part-designer $PRIMARY -- \
  psql -U postgres -c "SELECT client_addr, state, sync_state, replay_lag FROM pg_stat_replication;"

# Should show 2 replicas in "streaming" state with minimal lag
```

### Step 6: Verify Backup Configuration

```bash
# Check scheduled backup
kubectl get schedulebackup -n ai-part-designer postgres-backup-daily

# Trigger manual test backup
kubectl apply -f - <<EOF
apiVersion: postgresql.cnpg.io/v1
kind: Backup
metadata:
  name: postgres-test-backup
  namespace: ai-part-designer
spec:
  cluster:
    name: postgres-cluster
  method: barmanObjectStore
EOF

# Wait and verify backup completed
kubectl get backup -n ai-part-designer postgres-test-backup -w
```

## Quick Deploy (Development)

For local development or testing:

```bash
# Deploy to dev namespace
helm install ai-part-designer ./helm/ai-part-designer \
  --namespace ai-part-designer-dev \
  --create-namespace \
  --values helm/ai-part-designer/values-dev.yaml

# Single instance, no backups, minimal resources
```

## Common Operations

### Check Cluster Health

```bash
kubectl get cluster -n ai-part-designer postgres-cluster
```

### View Logs

```bash
# All PostgreSQL logs
kubectl logs -n ai-part-designer -l postgresql=postgres-cluster --tail=50

# Specific pod
kubectl logs -n ai-part-designer postgres-cluster-1 -f

# Pooler logs
kubectl logs -n ai-part-designer -l cnpg.io/poolerName=postgres-pooler --tail=20
```

### Connection String

For applications to connect:

```
Host: postgres-pooler-service.ai-part-designer.svc.cluster.local
Port: 5432
Database: assemblematic_ai
User: app
Password: <from secret postgres-app-user>
```

### Scale Cluster

```bash
# Scale to 5 instances
kubectl patch cluster -n ai-part-designer postgres-cluster --type='json' \
  -p='[{"op": "replace", "path": "/spec/instances", "value": 5}]'
```

### Trigger Manual Backup

```bash
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
```

### Test Failover

```bash
# Get current primary
PRIMARY=$(kubectl get cluster -n ai-part-designer postgres-cluster -o jsonpath='{.status.currentPrimary}')
echo "Current primary: $PRIMARY"

# Delete primary to trigger failover
kubectl delete pod -n ai-part-designer $PRIMARY

# Watch new primary being elected
kubectl get cluster -n ai-part-designer postgres-cluster -w

# Verify new primary
kubectl get cluster -n ai-part-designer postgres-cluster -o jsonpath='{.status.currentPrimary}'
```

## Troubleshooting

### Cluster Not Starting

```bash
# Check events
kubectl describe cluster -n ai-part-designer postgres-cluster

# Check pod events
kubectl describe pod -n ai-part-designer postgres-cluster-1

# Check operator logs
kubectl logs -n cnpg-system -l app.kubernetes.io/name=cloudnative-pg --tail=100
```

### Connection Issues

```bash
# Test from backend pod
BACKEND_POD=$(kubectl get pod -n ai-part-designer -l app.kubernetes.io/name=backend -o name | head -1)
kubectl exec -it -n ai-part-designer $BACKEND_POD -- \
  psql postgresql://app:PASSWORD@postgres-pooler-service:5432/assemblematic_ai -c "SELECT 1;"
```

### Backup Failures

```bash
# Check backup status
kubectl get backup -n ai-part-designer

# Check backup secret
kubectl get secret -n ai-part-designer postgres-backup-secret -o yaml

# Test MinIO connectivity
kubectl exec -it -n ai-part-designer postgres-cluster-1 -- \
  curl -I http://minio:9000/minio/health/ready
```

## Monitoring

### Prometheus Metrics

Port-forward and access metrics:

```bash
# Port-forward primary pod
kubectl port-forward -n ai-part-designer postgres-cluster-1 9187:9187

# Access metrics
curl http://localhost:9187/metrics
```

### Grafana Dashboard

Import CloudNativePG dashboard:
- Dashboard ID: **20417**
- URL: https://grafana.com/grafana/dashboards/20417

## Uninstall

### Remove Cluster (Keep Data)

```bash
# Delete cluster but keep PVCs
kubectl delete cluster -n ai-part-designer postgres-cluster
```

### Complete Removal (⚠️ DATA LOSS)

```bash
# Delete everything including data
helm uninstall ai-part-designer -n ai-part-designer
kubectl delete pvc -n ai-part-designer -l postgresql=postgres-cluster
kubectl delete namespace ai-part-designer
```

## Next Steps

1. ✅ Deploy cluster using steps above
2. ✅ Verify all pods are healthy
3. ✅ Test connection from application
4. 📖 Read full [Operations Guide](cloudnative-pg-operations.md)
5. 🧪 Perform [Failover Test](cloudnative-pg-failover-test.md)
6. 📊 Set up Prometheus alerts
7. 📈 Import Grafana dashboard
8. 🔐 Configure External Secrets Operator
9. 📝 Schedule quarterly failover tests
10. 🔍 Monitor metrics for 7 days

## Help

- **Setup Issues**: See `k8s/base/cloudnative-pg/README.md`
- **Operations**: See `docs/operations/cloudnative-pg-operations.md`
- **Failover Testing**: See `docs/operations/cloudnative-pg-failover-test.md`
- **CloudNativePG Docs**: https://cloudnative-pg.io/documentation/

---

**Need Help?** Contact Platform Operations Team
