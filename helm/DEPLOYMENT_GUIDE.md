# Helm Chart Deployment Guide

This guide provides step-by-step instructions for deploying the AI Part Designer using the Helm umbrella chart.

## Prerequisites

1. **Kubernetes Cluster**: Version 1.24 or higher
2. **Helm**: Version 3.8 or higher  
3. **kubectl**: Configured to access your cluster
4. **Container Registry Access**: Ability to pull images from ghcr.io

## Initial Setup

### 1. Download Chart Dependencies

```bash
cd helm/ai-part-designer
helm dependency update
```

This will download all infrastructure dependency charts:
- CloudNativePG (PostgreSQL)
- Redis
- MinIO
- OpenBao (if enabled)
- Ingress NGINX (if enabled)
- Cert-manager (if enabled)

### 2. Create Namespace

```bash
kubectl create namespace ai-part-designer
```

### 3. Create Required Secrets

**Important**: Create secrets before installing the chart.

```bash
# Generate a secure secret key
SECRET_KEY=$(openssl rand -hex 32)

# Create backend secrets
kubectl create secret generic backend-secrets \
  --namespace=ai-part-designer \
  --from-literal=postgres-user=assemblematic_user \
  --from-literal=postgres-password="$(openssl rand -base64 32)" \
  --from-literal=anthropic-api-key=sk-ant-YOUR_ACTUAL_KEY \
  --from-literal=secret-key="$SECRET_KEY" \
  --from-literal=access-key-id="$(openssl rand -hex 20)" \
  --from-literal=secret-access-key="$(openssl rand -base64 32)"

# Create celery worker secrets (same MinIO credentials)
kubectl create secret generic celery-worker-secrets \
  --namespace=ai-part-designer \
  --from-literal=access-key-id="$(kubectl get secret backend-secrets -n ai-part-designer -o jsonpath='{.data.access-key-id}' | base64 -d)" \
  --from-literal=secret-access-key="$(kubectl get secret backend-secrets -n ai-part-designer -o jsonpath='{.data.secret-access-key}' | base64 -d)"
```

## Deployment Scenarios

### Scenario 1: Development Environment

Minimal resources, single replicas, debug enabled:

```bash
helm install ai-part-designer ./helm/ai-part-designer \
  --namespace ai-part-designer \
  --values helm/ai-part-designer/values-dev.yaml \
  --wait \
  --timeout 10m
```

**Access the application:**
```bash
# Forward frontend
kubectl port-forward -n ai-part-designer svc/frontend 8080:80

# Forward backend API
kubectl port-forward -n ai-part-designer svc/backend 8000:8000

# Open browser
open http://localhost:8080
open http://localhost:8000/docs
```

### Scenario 2: Staging Environment

Production-like setup with reduced resources:

```bash
# Update values-staging.yaml with your domain
vim helm/ai-part-designer/values-staging.yaml
# Set ingressHost: "staging.yourdomain.com"

helm install ai-part-designer ./helm/ai-part-designer \
  --namespace ai-part-designer-staging \
  --create-namespace \
  --values helm/ai-part-designer/values-staging.yaml \
  --wait \
  --timeout 15m
```

### Scenario 3: Production Environment

Full HA configuration with all features:

```bash
# Update values-production.yaml
vim helm/ai-part-designer/values-production.yaml
# Set ingressHost, enable external secrets, etc.

helm install ai-part-designer ./helm/ai-part-designer \
  --namespace ai-part-designer-prod \
  --create-namespace \
  --values helm/ai-part-designer/values-production.yaml \
  --wait \
  --timeout 20m
```

### Scenario 4: Using Existing Infrastructure

If you already have PostgreSQL, Redis, or MinIO:

```bash
# Create custom values file
cat > custom-values.yaml << 'CUSTOM'
# Disable dependency installation
installPostgres: false
installRedis: false
installMinio: false

# Point to existing services
postgresHost: "my-postgres.example.com"
postgresPort: "5432"
redisHost: "my-redis.example.com"
redisPort: "6379"
minioEndpoint: "https://my-s3.example.com"

# Use defaults for everything else
CUSTOM

helm install ai-part-designer ./helm/ai-part-designer \
  --namespace ai-part-designer \
  --values custom-values.yaml
```

## Post-Installation

### Verify Deployment

```bash
# Check Helm release status
helm list -n ai-part-designer

# Check all pods are running
kubectl get pods -n ai-part-designer

# Check services
kubectl get svc -n ai-part-designer

# View deployment details
helm status ai-part-designer -n ai-part-designer
```

### Monitor Logs

```bash
# Backend logs
kubectl logs -n ai-part-designer -l app.kubernetes.io/name=backend -f

# Worker logs
kubectl logs -n ai-part-designer -l app.kubernetes.io/name=celery-worker -f

# Frontend logs
kubectl logs -n ai-part-designer -l app.kubernetes.io/name=frontend -f
```

### Access the Application

**With Ingress:**
```bash
# Application should be accessible at configured domain
curl https://your-domain.com
```

**Without Ingress (port-forward):**
```bash
kubectl port-forward -n ai-part-designer svc/frontend 8080:80 &
kubectl port-forward -n ai-part-designer svc/backend 8000:8000 &
```

## Upgrading

### Update Application Version

```bash
# Edit values to use new image tags
vim helm/ai-part-designer/values.yaml
# Change backendImage and frontendImage tags

# Perform upgrade
helm upgrade ai-part-designer ./helm/ai-part-designer \
  --namespace ai-part-designer \
  --values helm/ai-part-designer/values-production.yaml \
  --wait
```

### Update Configuration

```bash
# Edit configuration values
vim helm/ai-part-designer/values-production.yaml

# Apply changes
helm upgrade ai-part-designer ./helm/ai-part-designer \
  --namespace ai-part-designer \
  --values helm/ai-part-designer/values-production.yaml \
  --reuse-values
```

### Rollback

```bash
# View release history
helm history ai-part-designer -n ai-part-designer

# Rollback to previous revision
helm rollback ai-part-designer -n ai-part-designer

# Rollback to specific revision
helm rollback ai-part-designer 3 -n ai-part-designer
```

## Troubleshooting

### Pods Not Starting

```bash
# Check pod events
kubectl describe pod <pod-name> -n ai-part-designer

# Check pod logs
kubectl logs <pod-name> -n ai-part-designer

# Common issues:
# - Missing secrets: Create backend-secrets and celery-worker-secrets
# - Image pull errors: Check imagePullSecrets configuration
# - Resource limits: Adjust values.yaml resource requests/limits
```

### Database Connection Issues

```bash
# Check PostgreSQL pod
kubectl get pods -n ai-part-designer -l app=postgres

# Check connectivity from backend pod
kubectl exec -n ai-part-designer deployment/backend -- nc -zv postgres-service 5432

# Verify secret values
kubectl get secret backend-secrets -n ai-part-designer -o yaml
```

### Storage Issues

```bash
# Check MinIO pod
kubectl get pods -n ai-part-designer -l app=minio

# Check MinIO logs
kubectl logs -n ai-part-designer -l app=minio

# Verify buckets were created (from MinIO pod)
kubectl exec -n ai-part-designer deployment/backend -- \
  aws --endpoint-url http://minio:9000 s3 ls
```

### Ingress Issues

```bash
# Check ingress resource
kubectl get ingress -n ai-part-designer

# Describe ingress
kubectl describe ingress ai-part-designer-ingress -n ai-part-designer

# Check ingress controller logs
kubectl logs -n ingress-nginx -l app.kubernetes.io/component=controller
```

## Uninstalling

### Remove Helm Release

```bash
helm uninstall ai-part-designer -n ai-part-designer
```

**Note**: This removes the application but may retain:
- PersistentVolumeClaims (check reclaim policy)
- Secrets
- Namespace

### Complete Cleanup

```bash
# Remove all resources including PVCs
helm uninstall ai-part-designer -n ai-part-designer
kubectl delete pvc -n ai-part-designer --all
kubectl delete secret -n ai-part-designer --all
kubectl delete namespace ai-part-designer
```

## Security Best Practices

1. **Never commit secrets**: Use secret management tools
2. **Use External Secrets Operator**: Integrate with OpenBao/Vault in production
3. **Enable TLS**: Always use HTTPS in production
4. **Network Policies**: Enable networkPoliciesEnabled=true in production
5. **RBAC**: Review and enhance service account permissions
6. **Image Scanning**: Scan container images for vulnerabilities
7. **Resource Limits**: Set appropriate resource limits to prevent resource exhaustion

## Performance Tuning

### Backend Scaling

```yaml
# Adjust in values file
backendHpaMin: 5
backendHpaMax: 20
backendCpuTarget: 60
```

### Worker Scaling

```yaml
# Adjust in values file
workerReplicas: 5
workerConcurrency: 8
workerHpaMax: 15
```

### Database Tuning

```yaml
cloudnative-pg:
  cluster:
    postgresql:
      parameters:
        max_connections: "500"
        shared_buffers: "512MB"
        effective_cache_size: "2GB"
```

## Support

For issues or questions:
- GitHub Issues: https://github.com/jmassardo/ai-part-designer/issues
- Documentation: https://github.com/jmassardo/ai-part-designer
