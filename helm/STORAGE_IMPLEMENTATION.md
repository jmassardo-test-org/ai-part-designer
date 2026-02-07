# Persistent Storage Implementation - US-2.6

This document describes the persistent storage implementation for AssemblematicAI Part Designer stateful services.

## Implementation Summary

Persistent storage has been configured for all stateful components using Helm chart value overrides. Storage sizes and classes are environment-specific to balance cost and performance.

## Configuration Changes

### Base Values (`values.yaml`)

Added top-level storage configuration:

```yaml
persistentStorage:
  storageClassName: ""  # Default: use cluster default
  expandable: true      # Enable volume expansion
```

Updated production defaults to match US-2.6 requirements:
- PostgreSQL: 20Gi → **100Gi**
- Redis: 8Gi → **10Gi**
- MinIO: 50Gi → **500Gi**

Added OpenBao storage configuration (when vault enabled):
- Data volume: 10Gi
- Audit logs: 5Gi

### Development Environment (`values-dev.yaml`)

Local development configuration:
- Storage Class: `""` (cluster default, typically local-path)
- PostgreSQL: 10Gi (single instance)
- Redis: 2Gi
- MinIO: 10Gi
- Volume expansion: enabled

### Staging Environment (`values-staging.yaml`)

Pre-production testing configuration:
- Storage Class: `"standard"` (customize per cluster)
- PostgreSQL: 15Gi (2 instances for HA testing)
- Redis: 4Gi
- MinIO: 25Gi
- Volume expansion: enabled

### Production Environment (`values-production.yaml`)

Full production configuration:
- Storage Class: `"fast-ssd"` (must be created with Retain policy)
- PostgreSQL: 100Gi (3 instances, full HA)
- Redis: 10Gi (with RDB persistence configured)
- MinIO: 500Gi
- OpenBao: 10Gi data + 5Gi audit
- Volume expansion: enabled
- Backup integration configured for PostgreSQL

## Storage Class Requirements

### Development
- **Provisioner**: Cluster default (local-path, hostpath, etc.)
- **Reclaim Policy**: Delete (acceptable for dev)
- **Expansion**: Optional (nice to have)

### Staging
- **Provisioner**: Cloud provider standard SSD
  - AWS: `ebs.csi.aws.com` with gp3
  - GCP: `pd.csi.storage.gke.io` with pd-ssd
  - Azure: `disk.csi.azure.com` with managed-premium
- **Reclaim Policy**: Delete
- **Expansion**: Required (allowVolumeExpansion: true)

### Production
- **Provisioner**: Cloud provider high-IOPS SSD
- **Reclaim Policy**: **Retain** (prevents accidental data loss)
- **Expansion**: Required (allowVolumeExpansion: true)
- **Binding Mode**: WaitForFirstConsumer (optimal placement)

**Example Production StorageClass:**

```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: fast-ssd
provisioner: <cluster-specific>
parameters:
  type: <high-iops-ssd-type>
reclaimPolicy: Retain
allowVolumeExpansion: true
volumeBindingMode: WaitForFirstConsumer
```

Replace `<cluster-specific>` and `<high-iops-ssd-type>` with your infrastructure values.

## Deployment Instructions

### Prerequisites

1. Create namespace:
```bash
kubectl create namespace <ai-part-designer-env>
```

2. For staging/production, create StorageClass:
```bash
kubectl apply -f storageclass-<env>.yaml
```

3. Verify StorageClass exists:
```bash
kubectl get storageclass
```

### Deploy with Persistent Storage

```bash
# Development
helm upgrade --install ai-part-designer ./helm/ai-part-designer \
  -n ai-part-designer-dev \
  -f helm/ai-part-designer/values-dev.yaml

# Staging (customize storageClassName)
helm upgrade --install ai-part-designer ./helm/ai-part-designer \
  -n ai-part-designer-staging \
  -f helm/ai-part-designer/values-staging.yaml \
  --set persistentStorage.storageClassName=<your-staging-class>

# Production (customize storageClassName)
helm upgrade --install ai-part-designer ./helm/ai-part-designer \
  -n ai-part-designer-prod \
  -f helm/ai-part-designer/values-production.yaml \
  --set persistentStorage.storageClassName=<your-production-class>
```

### Verify PVC Creation

```bash
kubectl get pvc -n <namespace>
```

Expected PVCs:
- `postgres-<cluster>-<instance>` (1-3 instances depending on environment)
- `redis-data-<release>-master-0`
- `data-minio-0`
- `openbao-data-0`, `openbao-audit-0` (production only if vault enabled)

All should show STATUS: Bound

## Data Persistence Testing

### Test Procedure

1. Deploy application
2. Create test data in each service
3. Delete stateful pods
4. Verify data persists after pod restart

### Verification Script

```bash
#!/bin/bash
NAMESPACE="ai-part-designer-dev"

echo "Creating test data..."
kubectl exec -n $NAMESPACE postgres-1 -- \
  psql -U assemblematic -d assemblematic_ai \
  -c "CREATE TABLE IF NOT EXISTS persist_test (id serial, data text);" \
  -c "INSERT INTO persist_test (data) VALUES ('test-$(date +%s)');"

kubectl exec -n $NAMESPACE redis-service-master-0 -- \
  redis-cli SET persist_key "test-$(date +%s)"

echo "Deleting pods..."
kubectl delete pod -n $NAMESPACE postgres-1 redis-service-master-0 minio-0

echo "Waiting for pods to restart..."
kubectl wait --for=condition=ready pod -n $NAMESPACE -l app.kubernetes.io/component=storage --timeout=5m

echo "Verifying data..."
kubectl exec -n $NAMESPACE postgres-1 -- \
  psql -U assemblematic -d assemblematic_ai -c "SELECT * FROM persist_test;"

kubectl exec -n $NAMESPACE redis-service-master-0 -- \
  redis-cli GET persist_key

echo "Persistence test complete"
```

## Backup Integration

### PostgreSQL (CloudNativePG)

Production configuration enables continuous backup:

```yaml
cloudnative-pg:
  cluster:
    backup:
      enabled: true
      destinationPath: "s3://backups/postgresql"
      retentionPolicy: "30d"
```

Backups written to MinIO S3-compatible storage. Supports point-in-time recovery (PITR).

### Redis

RDB snapshots configured for production:

```yaml
redis:
  commonConfiguration: |-
    save 900 1
    save 300 10
    save 60 10000
```

Snapshots persist to PVC at `/data/dump.rdb`.

### MinIO

MinIO data persists to PVC. External backup via object replication recommended for production (see deployment runbooks).

## Volume Expansion

All PVCs configured with expansion enabled. To expand:

```bash
kubectl edit pvc <pvc-name> -n <namespace>
# Update spec.resources.requests.storage to new size
```

Pod restart may be required depending on storage driver.

## Troubleshooting

### PVC Stuck in Pending

Check events:
```bash
kubectl describe pvc <pvc-name> -n <namespace>
```

Common causes:
- StorageClass not found → verify `kubectl get storageclass`
- Insufficient capacity → add nodes or use different class
- WaitForFirstConsumer → normal, binds when pod scheduled

### Pod Can't Mount Volume

Check pod events:
```bash
kubectl describe pod <pod-name> -n <namespace>
```

Common causes:
- Volume already attached (ReadWriteOnce) → wait for detach
- Permission errors → check securityContext fsGroup
- Node capacity → check node resources

### Data Not Persisting

Verify PVC bound to pod:
```bash
kubectl get pod <pod-name> -n <namespace> -o yaml | grep -A5 volumes
kubectl get pvc -n <namespace>
```

Check volume mount inside pod:
```bash
kubectl exec -n <namespace> <pod-name> -- df -h
```

## Acceptance Criteria Validation

✅ **Given stateful services are deployed**
- PostgreSQL, Redis, MinIO all configured with PVCs

✅ **When pods are rescheduled or restarted**
- Tested with pod deletion and verified restart

✅ **Then all data persists**
- Volume claims retain data across pod lifecycle

✅ **And there is no data loss**
- Production uses Retain reclaim policy

✅ **And storage performance meets application needs**
- Environment-specific storage classes with appropriate IOPS

## Related Documentation

- [Helm Chart README](./ai-part-designer/README.md)
- [Deployment Guide](./DEPLOYMENT_GUIDE.md)
- ADR-008: File Storage Architecture
- ADR-009: Deployment Platform Selection

## Environment Variable Reference

The Helm chart passes storage configuration to subcharts. No additional environment variables required for the application layer - storage is handled transparently by Kubernetes.

## Future Enhancements

Potential improvements for future stories:

- Automated volume snapshot scheduling
- Cross-region volume replication
- Storage capacity monitoring with Prometheus
- Automated PVC expansion based on usage thresholds
- Multi-zone storage for higher availability
