# MinIO Deployment for AI Part Designer

## Overview

This directory contains Kubernetes manifests for deploying MinIO as an S3-compatible object storage system for the AI Part Designer application.

MinIO provides cloud-agnostic object storage that can run inside Kubernetes, eliminating the need for external cloud storage services while maintaining S3 API compatibility.

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│  Application Pods (Backend, Celery Workers)            │
│                                                         │
│  Uses storage_client with S3-compatible API            │
└───────────────────┬─────────────────────────────────────┘
                    │
                    │ S3 API (HTTP Port 9000)
                    ▼
┌─────────────────────────────────────────────────────────┐
│  MinIO StatefulSet                                      │
│  ┌───────────────────────────────────────────────────┐ │
│  │  Pod: minio-0                                      │ │
│  │  - API Server (Port 9000)                         │ │
│  │  - Console UI (Port 9001)                         │ │
│  │  - Prometheus Metrics (/minio/v2/metrics/cluster) │ │
│  └───────────────────┬───────────────────────────────┘ │
│                      │                                  │
│                      ▼                                  │
│  ┌───────────────────────────────────────────────────┐ │
│  │  PersistentVolumeClaim: data (50Gi)               │ │
│  │  - Stores all bucket data                         │ │
│  │  - Survives pod restarts                          │ │
│  └───────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────┘
                    ▲
                    │
                    │ Sync credentials
                    │
┌─────────────────────────────────────────────────────────┐
│  OpenBao Secrets Management                             │
│  secret/ai-part-designer/storage/                       │
│    - minio-credentials (root user/password)             │
│    - minio-app-credentials (app access keys)            │
└─────────────────────────────────────────────────────────┘
```

## Storage Buckets

MinIO is configured with the following buckets:

| Bucket Name | Purpose | Access Policy | Lifecycle |
|-------------|---------|---------------|-----------|
| `user-uploads` | Component datasheets, images | Private | Permanent |
| `cad-exports` | Generated STL, STEP, 3MF files | Public read | Permanent |
| `design-thumbnails` | Preview images | Public read | Permanent |
| `db-backups` | CloudNativePG automated backups | Private | 30 days |

Additionally, environment-specific buckets are created with the pattern:
- `ai-part-designer-{env}-designs` (private)
- `ai-part-designer-{env}-exports` (public read)
- `ai-part-designer-{env}-thumbnails` (public read)
- `ai-part-designer-{env}-uploads` (private)
- `ai-part-designer-{env}-temp` (private, 7-day expiration)

Where `{env}` is one of: `development`, `staging`, `production`

## Components

### StatefulSet (`statefulset.yaml`)

- **Replicas:** 1 (single-node deployment)
- **Image:** `minio/minio:RELEASE.2024-02-17T01-15-57Z`
- **Persistent Storage:** 50Gi PVC
- **Resources:**
  - Requests: 512Mi RAM, 250m CPU
  - Limits: 2Gi RAM, 1000m CPU
- **Health Checks:** LivenessProbe and ReadinessProbe on `/minio/health/*`
- **Security:**
  - Non-root user (UID 1000)
  - Read-only root filesystem
  - seccomp profile enabled
  - All capabilities dropped

### Services (`service.yaml`)

1. **minio** (ClusterIP)
   - Port 9000: S3 API
   - Port 9001: Web Console

2. **minio-headless** (Headless Service)
   - For StatefulSet DNS resolution

### Initialization Job (`init-buckets-job.yaml`)

A Kubernetes Job that runs after MinIO starts to:
1. Create all required buckets
2. Set access policies (private/public read)
3. Configure lifecycle rules:
   - Temp buckets: Delete files after 7 days
   - DB backups: Delete after 30 days

**Image:** `minio/mc:RELEASE.2024-02-16T11-05-48Z` (MinIO Client)

### Secrets Management (`external-secrets.yaml`)

Three ExternalSecrets sync credentials from OpenBao:

1. **minio-credentials**
   - Root user and password for MinIO server
   - Used by StatefulSet

2. **minio-mc-config**
   - Pre-formatted connection string for mc client
   - Used by initialization job

3. **minio-app-credentials**
   - Application access key and secret
   - Used by backend and celery workers

### Network Policies (`network-policy.yaml`)

**Ingress:**
- Allow backend pods → MinIO:9000
- Allow celery workers → MinIO:9000
- Allow celery beat → MinIO:9000
- Allow init jobs → MinIO:9000
- Allow Prometheus → MinIO:9000 (metrics)
- Allow any pod → MinIO:9001 (console)

**Egress:**
- Allow DNS resolution
- Allow pod-to-pod communication (for future multi-node setup)

### Monitoring (`servicemonitor.yaml`)

Prometheus ServiceMonitor for automatic metrics scraping:
- **Endpoint:** `/minio/v2/metrics/cluster`
- **Interval:** 30 seconds
- **Port:** 9000

Metrics include:
- Bucket sizes and object counts
- Request rates and latencies
- Network throughput
- Disk usage
- Error rates

## Prerequisites

1. **Kubernetes Cluster** (v1.24+)
   - StorageClass with dynamic provisioning
   - Network policy support (optional but recommended)

2. **OpenBao** (deployed and initialized)
   - See `/k8s/base/openbao/README.md`
   - Secrets must be pre-populated (see below)

3. **External Secrets Operator**
   - Installed in cluster
   - SecretStore configured

4. **Prometheus Operator** (optional)
   - For metrics collection
   - ServiceMonitor CRD available

## Deployment

### Step 1: Store Credentials in OpenBao

```bash
# Port-forward to OpenBao
kubectl port-forward -n openbao svc/openbao 8200:8200 &
export VAULT_ADDR=http://localhost:8200
export VAULT_TOKEN=$(kubectl get secret openbao-unseal-keys \
  -n openbao -o jsonpath='{.data.root-token}' | base64 -d)

# Generate secure credentials
MINIO_ROOT_USER="admin"
MINIO_ROOT_PASSWORD=$(openssl rand -base64 32)
MINIO_APP_ACCESS_KEY=$(openssl rand -hex 20)
MINIO_APP_SECRET_KEY=$(openssl rand -base64 40)

# Store MinIO root credentials
openbao kv put secret/ai-part-designer/storage/minio-credentials \
  root_user="$MINIO_ROOT_USER" \
  root_password="$MINIO_ROOT_PASSWORD"

# Store application credentials
openbao kv put secret/ai-part-designer/storage/minio-app-credentials \
  access_key_id="$MINIO_APP_ACCESS_KEY" \
  secret_access_key="$MINIO_APP_SECRET_KEY"

# Verify secrets are stored
openbao kv get secret/ai-part-designer/storage/minio-credentials
openbao kv get secret/ai-part-designer/storage/minio-app-credentials
```

### Step 2: Update OpenBao Policies

The policies are already updated in:
- `k8s/base/openbao/policies/api-service-policy.hcl`
- `k8s/base/openbao/policies/worker-service-policy.hcl`

Apply them:

```bash
openbao policy write ai-part-designer-api k8s/base/openbao/policies/api-service-policy.hcl
openbao policy write ai-part-designer-worker k8s/base/openbao/policies/worker-service-policy.hcl
```

### Step 3: Deploy MinIO

Using kustomize:

```bash
# Apply base configuration
kubectl apply -k k8s/base/

# Or apply environment-specific overlay
kubectl apply -k k8s/overlays/staging/
```

### Step 4: Verify Deployment

```bash
# Check StatefulSet status
kubectl get statefulset minio -n ai-part-designer
kubectl get pods -n ai-part-designer -l app.kubernetes.io/name=minio

# Check PVC
kubectl get pvc -n ai-part-designer

# Check secrets synced from OpenBao
kubectl get secret minio-credentials -n ai-part-designer
kubectl get secret minio-app-credentials -n ai-part-designer

# Check initialization job
kubectl get job minio-init-buckets -n ai-part-designer
kubectl logs job/minio-init-buckets -n ai-part-designer

# Check services
kubectl get svc -n ai-part-designer -l app.kubernetes.io/name=minio
```

### Step 5: Access MinIO Console (Optional)

```bash
# Port-forward to console
kubectl port-forward -n ai-part-designer svc/minio 9001:9001

# Open browser to http://localhost:9001
# Login with root credentials from OpenBao
```

### Step 6: Create Application User in MinIO

After initial deployment, create a dedicated user for the application:

```bash
# Port-forward to MinIO API
kubectl port-forward -n ai-part-designer svc/minio 9000:9000 &

# Get root credentials
ROOT_USER=$(kubectl get secret minio-credentials -n ai-part-designer -o jsonpath='{.data.root-user}' | base64 -d)
ROOT_PASSWORD=$(kubectl get secret minio-credentials -n ai-part-designer -o jsonpath='{.data.root-password}' | base64 -d)

# Configure mc client
mc alias set k8s-minio http://localhost:9000 $ROOT_USER $ROOT_PASSWORD

# Get app credentials from OpenBao
APP_KEY=$(openbao kv get -field=access_key_id secret/ai-part-designer/storage/minio-app-credentials)
APP_SECRET=$(openbao kv get -field=secret_access_key secret/ai-part-designer/storage/minio-app-credentials)

# Create user
mc admin user add k8s-minio $APP_KEY $APP_SECRET

# Create policy for app user
cat > /tmp/app-policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:PutObject",
        "s3:DeleteObject",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::*-designs/*",
        "arn:aws:s3:::*-exports/*",
        "arn:aws:s3:::*-thumbnails/*",
        "arn:aws:s3:::*-uploads/*",
        "arn:aws:s3:::*-temp/*",
        "arn:aws:s3:::user-uploads/*",
        "arn:aws:s3:::cad-exports/*",
        "arn:aws:s3:::design-thumbnails/*"
      ]
    }
  ]
}
EOF

mc admin policy create k8s-minio app-storage-access /tmp/app-policy.json
mc admin policy attach k8s-minio app-storage-access --user=$APP_KEY

# Verify user
mc admin user list k8s-minio
```

## Testing

### Test Storage Operations

```bash
# Test from a backend pod
kubectl exec -it -n ai-part-designer deployment/backend -- python -c "
from app.core.storage import storage_client, StorageBucket
import asyncio

async def test():
    # Test upload
    url = await storage_client.upload_file(
        StorageBucket.TEMP,
        'test.txt',
        b'Hello MinIO!',
        content_type='text/plain'
    )
    print(f'Uploaded: {url}')
    
    # Test download
    data = await storage_client.download_file(StorageBucket.TEMP, 'test.txt')
    print(f'Downloaded: {data.decode()}')
    
    # Test delete
    deleted = await storage_client.delete_file(StorageBucket.TEMP, 'test.txt')
    print(f'Deleted: {deleted}')

asyncio.run(test())
"
```

### Test Bucket Lifecycle

```bash
# Upload a test file to temp bucket
echo "test" | mc pipe k8s-minio/ai-part-designer-development-temp/test-expiry.txt

# Check lifecycle rules
mc ilm ls k8s-minio/ai-part-designer-development-temp

# File should auto-delete after 7 days
```

## Backup and Restore

### Backup MinIO Data

```bash
# Using mc mirror
mc mirror --preserve k8s-minio/user-uploads ./backup/user-uploads
mc mirror --preserve k8s-minio/cad-exports ./backup/cad-exports
mc mirror --preserve k8s-minio/design-thumbnails ./backup/design-thumbnails
mc mirror --preserve k8s-minio/db-backups ./backup/db-backups

# Or using PVC snapshot (if supported by storage class)
kubectl create -f - <<EOF
apiVersion: snapshot.storage.k8s.io/v1
kind: VolumeSnapshot
metadata:
  name: minio-data-snapshot-$(date +%Y%m%d)
  namespace: ai-part-designer
spec:
  volumeSnapshotClassName: csi-snapclass
  source:
    persistentVolumeClaimName: data-minio-0
EOF
```

### Restore MinIO Data

```bash
# From mc backup
mc mirror --preserve ./backup/user-uploads k8s-minio/user-uploads
mc mirror --preserve ./backup/cad-exports k8s-minio/cad-exports
mc mirror --preserve ./backup/design-thumbnails k8s-minio/design-thumbnails
mc mirror --preserve ./backup/db-backups k8s-minio/db-backups

# From PVC snapshot
# 1. Create new PVC from snapshot
# 2. Scale down StatefulSet
# 3. Delete old PVC
# 4. Create new PVC with snapshot as source
# 5. Scale up StatefulSet
```

### Disaster Recovery

For complete disaster recovery:

1. **Regular Backups:**
   - Schedule daily `mc mirror` backups to external storage
   - Or use PVC snapshots if available
   - Store backups in different region/cluster

2. **OpenBao Secrets:**
   - Secrets are stored in OpenBao
   - Ensure OpenBao is also backed up
   - Document secret rotation procedures

3. **Recovery Steps:**
   ```bash
   # 1. Deploy new cluster
   # 2. Deploy OpenBao and restore secrets
   # 3. Deploy MinIO
   # 4. Restore data from backups
   mc mirror --preserve s3-backup/user-uploads k8s-minio/user-uploads
   # 5. Deploy application
   kubectl apply -k k8s/overlays/production/
   ```

## Monitoring and Observability

### Metrics

MinIO exposes Prometheus metrics at `/minio/v2/metrics/cluster`:

- `minio_bucket_usage_object_total`: Number of objects per bucket
- `minio_bucket_usage_total_bytes`: Total size per bucket
- `minio_s3_requests_total`: Request count by API method
- `minio_s3_errors_total`: Error count by error type
- `minio_disk_storage_used_bytes`: Disk usage
- `minio_disk_storage_available_bytes`: Available disk space
- `minio_network_received_bytes_total`: Network ingress
- `minio_network_sent_bytes_total`: Network egress

### Grafana Dashboard

Import the official MinIO dashboard:
- Dashboard ID: 13502
- URL: https://grafana.com/grafana/dashboards/13502

### Alerts

Recommended Prometheus alerts:

```yaml
groups:
- name: minio
  interval: 30s
  rules:
  - alert: MinIONodeDiskFull
    expr: minio_disk_storage_used_bytes / minio_disk_storage_total_bytes > 0.9
    for: 5m
    labels:
      severity: critical
    annotations:
      summary: "MinIO disk usage is above 90%"
      
  - alert: MinIOHighErrorRate
    expr: rate(minio_s3_errors_total[5m]) > 10
    for: 5m
    labels:
      severity: warning
    annotations:
      summary: "MinIO error rate is high"
      
  - alert: MinIODown
    expr: up{job="minio"} == 0
    for: 2m
    labels:
      severity: critical
    annotations:
      summary: "MinIO is down"
```

## Scaling

### Vertical Scaling (Increase Resources)

Edit `statefulset.yaml` to increase resource limits:

```yaml
resources:
  requests:
    memory: "1Gi"
    cpu: "500m"
  limits:
    memory: "4Gi"
    cpu: "2000m"
```

### Storage Expansion

To increase PVC size:

1. Ensure StorageClass allows volume expansion (`allowVolumeExpansion: true`)
2. Edit the PVC:
   ```bash
   kubectl edit pvc data-minio-0 -n ai-part-designer
   # Change spec.resources.requests.storage to desired size
   ```
3. Delete and recreate the pod:
   ```bash
   kubectl delete pod minio-0 -n ai-part-designer
   ```

### Multi-Node Deployment (Future)

For production workloads requiring HA:

1. Update replicas to 4 or more (must be even number)
2. Switch to distributed mode with multiple drives
3. Update service to LoadBalancer type
4. Configure MinIO in distributed mode

## Troubleshooting

### Pod Won't Start

```bash
# Check pod status
kubectl describe pod minio-0 -n ai-part-designer

# Check PVC status
kubectl describe pvc data-minio-0 -n ai-part-designer

# Check secrets
kubectl get secret minio-credentials -n ai-part-designer -o yaml

# Check logs
kubectl logs minio-0 -n ai-part-designer
```

### Bucket Initialization Failed

```bash
# Check job status
kubectl describe job minio-init-buckets -n ai-part-designer

# View job logs
kubectl logs job/minio-init-buckets -n ai-part-designer

# Manually run initialization
kubectl delete job minio-init-buckets -n ai-part-designer
kubectl apply -f k8s/base/minio/init-buckets-job.yaml
```

### Application Can't Connect

```bash
# Test connectivity from backend pod
kubectl exec -it -n ai-part-designer deployment/backend -- curl http://minio:9000/minio/health/live

# Check network policies
kubectl get networkpolicy -n ai-part-designer

# Verify secrets are mounted
kubectl exec -it -n ai-part-designer deployment/backend -- env | grep -E 'S3|STORAGE|AWS'
```

### Performance Issues

```bash
# Check resource usage
kubectl top pod minio-0 -n ai-part-designer

# Check disk I/O
kubectl exec -it minio-0 -n ai-part-designer -- df -h

# Review metrics in Grafana
# Check for high request latency or error rates
```

## Security Considerations

1. **Credentials:**
   - Root credentials stored in OpenBao
   - Application uses separate access keys with restricted permissions
   - Rotate credentials quarterly (use `/k8s/base/openbao/rotate-secrets.sh`)

2. **Network Isolation:**
   - Network policies restrict access to MinIO
   - Only authorized pods can connect
   - Console access can be further restricted if needed

3. **Encryption:**
   - Data at rest: Depends on underlying PVC encryption
   - Data in transit: Use TLS for production (configure Ingress with cert-manager)
   - Server-side encryption can be enabled with KMS integration

4. **Access Control:**
   - Bucket policies enforce public/private access
   - User policies restrict operations
   - Audit logs track all access

5. **Updates:**
   - Pin specific MinIO version in StatefulSet
   - Test updates in staging before production
   - Review MinIO security advisories

## References

- [MinIO Documentation](https://min.io/docs/minio/kubernetes/upstream/)
- [MinIO Kubernetes Operator](https://github.com/minio/operator)
- [External Secrets Operator](https://external-secrets.io/)
- [OpenBao Documentation](https://openbao.org/docs/)
- ADR-013: Cloud-Agnostic Architecture

---

*Last Updated: 2026-02-06*
