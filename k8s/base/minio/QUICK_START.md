# MinIO Quick Start Guide

> Quick reference for developers working with MinIO in the AI Part Designer application.

## TL;DR

MinIO provides S3-compatible object storage inside Kubernetes. Your application code doesn't need to change - it already uses the storage abstraction layer.

**Endpoint:** `http://minio:9000` (inside cluster)  
**Authentication:** Via environment variables (auto-configured)  
**Buckets:** Environment-specific (e.g., `ai-part-designer-development-designs`)

## For Application Developers

### Using Storage in Code

The application uses `storage_client` from `app/core/storage.py`:

```python
from app.core.storage import storage_client, StorageBucket
import asyncio

async def example():
    # Upload a file
    url = await storage_client.upload_file(
        StorageBucket.DESIGNS,
        key="user-123/project.stl",
        file=file_bytes,
        content_type="model/stl"
    )
    
    # Download a file
    data = await storage_client.download_file(
        StorageBucket.DESIGNS,
        key="user-123/project.stl"
    )
    
    # Generate presigned URL for download
    url = await storage_client.generate_presigned_download_url(
        StorageBucket.EXPORTS,
        key="design-456/output.step",
        expires_in=3600
    )
    
    # List files in a bucket
    files = await storage_client.list_files(
        StorageBucket.THUMBNAILS,
        prefix="user-123/"
    )
    
    # Delete a file
    deleted = await storage_client.delete_file(
        StorageBucket.TEMP,
        key="temp-file.txt"
    )

# Run async code
asyncio.run(example())
```

### Available Buckets

```python
from app.core.storage import StorageBucket

StorageBucket.DESIGNS      # User designs
StorageBucket.EXPORTS      # Generated CAD exports
StorageBucket.THUMBNAILS   # Preview images
StorageBucket.UPLOADS      # User-uploaded files
StorageBucket.TEMP         # Temporary files (7-day expiration)
```

The `storage_client` automatically prefixes bucket names with the environment (e.g., `ai-part-designer-development-designs`).

### Testing Locally

When running via docker-compose, MinIO is available at:
- **API:** http://localhost:9000
- **Console:** http://localhost:9001
- **Credentials:** `minioadmin` / `minioadmin`

### Testing in Kubernetes

```bash
# Port-forward to MinIO console
kubectl port-forward -n ai-part-designer svc/minio 9001:9001

# Open http://localhost:9001
# Login with credentials from OpenBao
```

## For DevOps/SRE

### Quick Health Check

```bash
# Check pod status
kubectl get pod minio-0 -n ai-part-designer

# Check health endpoints
kubectl exec minio-0 -n ai-part-designer -- wget -qO- http://localhost:9000/minio/health/live

# Check disk usage
kubectl exec minio-0 -n ai-part-designer -- df -h /data
```

### Access MinIO Console

```bash
# Port-forward
kubectl port-forward -n ai-part-designer svc/minio 9001:9001

# Get credentials
ROOT_USER=$(kubectl get secret minio-credentials -n ai-part-designer -o jsonpath='{.data.root-user}' | base64 -d)
ROOT_PASSWORD=$(kubectl get secret minio-credentials -n ai-part-designer -o jsonpath='{.data.root-password}' | base64 -d)

echo "Username: $ROOT_USER"
echo "Password: $ROOT_PASSWORD"

# Open http://localhost:9001
```

### Using MinIO Client (mc)

```bash
# Port-forward
kubectl port-forward -n ai-part-designer svc/minio 9000:9000 &

# Configure mc
ROOT_USER=$(kubectl get secret minio-credentials -n ai-part-designer -o jsonpath='{.data.root-user}' | base64 -d)
ROOT_PASSWORD=$(kubectl get secret minio-credentials -n ai-part-designer -o jsonpath='{.data.root-password}' | base64 -d)
mc alias set k8s-minio http://localhost:9000 $ROOT_USER $ROOT_PASSWORD

# List buckets
mc ls k8s-minio/

# List objects in a bucket
mc ls k8s-minio/ai-part-designer-development-designs/

# Copy file to MinIO
mc cp file.txt k8s-minio/ai-part-designer-development-uploads/

# Download file from MinIO
mc cp k8s-minio/ai-part-designer-development-designs/project.stl ./

# Get bucket statistics
mc du k8s-minio/ai-part-designer-development-designs/

# Remove old files
mc rm --recursive --force --older-than 7d k8s-minio/ai-part-designer-development-temp/
```

### Restart MinIO

```bash
# Delete pod (StatefulSet will recreate)
kubectl delete pod minio-0 -n ai-part-designer

# Wait for ready
kubectl wait --for=condition=ready pod/minio-0 -n ai-part-designer --timeout=2m
```

### View Logs

```bash
# Real-time logs
kubectl logs -f minio-0 -n ai-part-designer

# Last 100 lines
kubectl logs --tail=100 minio-0 -n ai-part-designer

# Search for errors
kubectl logs minio-0 -n ai-part-designer | grep -i error
```

### Check Metrics

```bash
# Port-forward
kubectl port-forward -n ai-part-designer svc/minio 9000:9000 &

# Fetch metrics
curl http://localhost:9000/minio/v2/metrics/cluster

# Count metrics
curl -s http://localhost:9000/minio/v2/metrics/cluster | grep "^minio_" | wc -l
```

## Common Issues

### Issue: "Access Denied" errors

**Cause:** Application credentials not set or incorrect.

**Fix:**
```bash
# Check if secrets are synced
kubectl get secret backend-secrets -n ai-part-designer
kubectl describe externalsecret minio-app-credentials -n ai-part-designer

# Force secret sync
kubectl annotate externalsecret minio-app-credentials -n ai-part-designer force-sync="$(date +%s)"

# Restart backend pods
kubectl rollout restart deployment/backend -n ai-part-designer
```

### Issue: MinIO pod not starting

**Cause:** PVC not bound or insufficient resources.

**Fix:**
```bash
# Check PVC status
kubectl get pvc data-minio-0 -n ai-part-designer
kubectl describe pvc data-minio-0 -n ai-part-designer

# Check node resources
kubectl describe node | grep -A 5 "Allocated resources"

# Check pod events
kubectl describe pod minio-0 -n ai-part-designer
```

### Issue: Disk full

**Cause:** Storage usage exceeded 50Gi.

**Fix:**
```bash
# Check usage
kubectl exec minio-0 -n ai-part-designer -- df -h /data

# Expand PVC (see RUNBOOK.md SOP-4)
kubectl edit pvc data-minio-0 -n ai-part-designer
# Increase spec.resources.requests.storage

# Delete pod to apply
kubectl delete pod minio-0 -n ai-part-designer
```

### Issue: Can't connect to MinIO from application

**Cause:** Network policy blocking or service not ready.

**Fix:**
```bash
# Test connectivity from backend pod
BACKEND_POD=$(kubectl get pod -n ai-part-designer -l app.kubernetes.io/name=backend -o jsonpath='{.items[0].metadata.name}')
kubectl exec $BACKEND_POD -n ai-part-designer -- curl http://minio:9000/minio/health/live

# Check network policies
kubectl get networkpolicy -n ai-part-designer

# Check service endpoints
kubectl get endpoints minio -n ai-part-designer
```

## Quick Commands Reference

```bash
# Status
kubectl get statefulset,pod,pvc,svc -n ai-part-designer -l app.kubernetes.io/name=minio

# Logs
kubectl logs minio-0 -n ai-part-designer --tail=50 -f

# Exec into pod
kubectl exec -it minio-0 -n ai-part-designer -- /bin/sh

# Port-forward API
kubectl port-forward -n ai-part-designer svc/minio 9000:9000

# Port-forward Console
kubectl port-forward -n ai-part-designer svc/minio 9001:9001

# Restart
kubectl delete pod minio-0 -n ai-part-designer

# Check secrets
kubectl get secret -n ai-part-designer | grep minio

# View externalsecret status
kubectl get externalsecret -n ai-part-designer
```

## Further Reading

- **Full Documentation:** [README.md](./README.md)
- **Operations Guide:** [RUNBOOK.md](./RUNBOOK.md)
- **Deployment Details:** [DEPLOYMENT_SUMMARY.md](./DEPLOYMENT_SUMMARY.md)
- **MinIO Documentation:** https://min.io/docs/minio/kubernetes/upstream/

---

*Last Updated: 2026-02-06*
