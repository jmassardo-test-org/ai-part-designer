# AI Part Designer Helm Chart

This Helm umbrella chart deploys the complete AssemblematicAI platform stack including all infrastructure dependencies.

## Overview

The AI Part Designer is an AI-powered 3D CAD part generation platform built with:
- **Backend**: FastAPI (Python)
- **Frontend**: React + Three.js
- **Workers**: Celery for async CAD generation
- **Database**: PostgreSQL (via CloudNativePG)
- **Cache/Broker**: Redis
- **Storage**: MinIO (S3-compatible)
- **Secrets**: OpenBao (optional)

## Prerequisites

- Kubernetes 1.24+
- Helm 3.8+
- kubectl configured
- Container images built and pushed to registry

## Quick Start

### 1. Add Chart Dependencies

```bash
cd helm/ai-part-designer
helm dependency update
```

### 2. Create Secrets

Before installation, create the required secrets:

```bash
kubectl create namespace ai-part-designer

kubectl create secret generic backend-secrets \
  --namespace=ai-part-designer \
  --from-literal=postgres-user=assemblematic \
  --from-literal=postgres-password=CHANGE_ME \
  --from-literal=anthropic-api-key=sk-ant-YOUR_KEY \
  --from-literal=secret-key=YOUR_SECRET_KEY \
  --from-literal=access-key-id=minio-access-key \
  --from-literal=secret-access-key=minio-secret-key

kubectl create secret generic celery-worker-secrets \
  --namespace=ai-part-designer \
  --from-literal=access-key-id=minio-access-key \
  --from-literal=secret-access-key=minio-secret-key
```

### 3. Install the Chart

```bash
# Development environment
helm install ai-part-designer ./helm/ai-part-designer \
  --namespace ai-part-designer \
  --create-namespace \
  --values helm/ai-part-designer/values-dev.yaml

# Staging environment
helm install ai-part-designer ./helm/ai-part-designer \
  --namespace ai-part-designer-staging \
  --create-namespace \
  --values helm/ai-part-designer/values-staging.yaml

# Production environment
helm install ai-part-designer ./helm/ai-part-designer \
  --namespace ai-part-designer-prod \
  --create-namespace \
  --values helm/ai-part-designer/values-production.yaml
```

## Configuration

### Key Values

| Parameter | Description | Default |
|-----------|-------------|---------|
| `backendImage` | Backend Docker image | `ghcr.io/jmassardo/ai-part-designer-backend:latest` |
| `frontendImage` | Frontend Docker image | `ghcr.io/jmassardo/ai-part-designer-frontend:latest` |
| `backendReplicas` | Number of backend pods | `3` |
| `frontendReplicas` | Number of frontend pods | `2` |
| `workerReplicas` | Number of Celery worker pods | `3` |
| `ingressEnabled` | Enable ingress | `false` |
| `ingressHost` | Hostname for ingress | `app.example.com` |

### Resource Configuration

| Component | CPU Request | Memory Request | CPU Limit | Memory Limit |
|-----------|------------|----------------|-----------|--------------|
| Backend | 250m | 512Mi | 1000m | 2Gi |
| Frontend | 50m | 64Mi | 200m | 256Mi |
| Worker | 500m | 1Gi | 2000m | 4Gi |
| Beat | 50m | 128Mi | 200m | 512Mi |

### Database Configuration

From `values.yaml`:
```yaml
postgresHost: "postgres-service"
postgresPort: "5432"
postgresDb: "assemblematic_ai"
```

### Persistent Storage

All stateful components use PVCs with environment-specific sizes. See [Storage Implementation](../STORAGE_IMPLEMENTATION.md) for complete details.

| Component | Dev | Staging | Production |
|-----------|-----|---------|------------|
| PostgreSQL | 10Gi | 15Gi | 100Gi |
| Redis | 2Gi | 4Gi | 10Gi |
| MinIO | 10Gi | 25Gi | 500Gi |

### Storage Buckets

The chart configures MinIO with these buckets:
- `designs` - CAD design files
- `exports` - Exported STL/STEP files  
- `thumbnails` - 3D model thumbnails
- `uploads` - User uploads
- `temp` - Temporary files

### AI Configuration

```yaml
aiProvider: "anthropic"
anthropicModel: "claude-sonnet-4-20250514"
aiMaxTokens: "4096"
aiTemperature: "0.3"
```

## Dependency Management

### Included Subcharts

| Chart | Version | Purpose | Toggle |
|-------|---------|---------|--------|
| cloudnative-pg | 0.22.1 | PostgreSQL operator | `installPostgres` |
| redis | 18.19.4 | Cache/message broker | `installRedis` |
| minio | 5.2.0 | S3-compatible storage | `installMinio` |
| openbao | 0.4.0 | Secrets management | `installVault` |
| ingress-nginx | 4.11.3 | Ingress controller | `installIngress` |
| cert-manager | 1.16.2 | TLS certificates | `installCerts` |

### Disabling Dependencies

If you have existing infrastructure, disable dependencies:

```yaml
installPostgres: false
installRedis: false
installMinio: false
```

Then configure connection strings to your existing services:

```yaml
postgresHost: "my-existing-postgres.example.com"
redisHost: "my-existing-redis.example.com"
minioEndpoint: "https://my-existing-s3.example.com"
```

## Environment-Specific Deployments

### Development

```bash
helm install ai-part-designer ./helm/ai-part-designer \
  -n ai-part-designer-dev \
  --create-namespace \
  -f helm/ai-part-designer/values-dev.yaml
```

Features:
- Single replicas for most services
- Debug mode enabled
- Reduced resource requests
- Smaller storage volumes

### Staging

```bash
helm install ai-part-designer ./helm/ai-part-designer \
  -n ai-part-designer-staging \
  --create-namespace \
  -f helm/ai-part-designer/values-staging.yaml
```

Features:
- 2 replicas for redundancy
- Ingress enabled
- Moderate resources
- Production-like configuration

### Production

```bash
helm install ai-part-designer ./helm/ai-part-designer \
  -n ai-part-designer-prod \
  --create-namespace \
  -f helm/ai-part-designer/values-production.yaml
```

Features:
- Full HA configuration
- Network policies enabled
- External secrets integration
- Full resource allocation
- Monitoring enabled

## Upgrading

```bash
# Update dependencies
helm dependency update ./helm/ai-part-designer

# Upgrade release
helm upgrade ai-part-designer ./helm/ai-part-designer \
  -n ai-part-designer \
  -f helm/ai-part-designer/values-production.yaml
```

## Testing

### Dry Run

```bash
helm install ai-part-designer ./helm/ai-part-designer \
  --dry-run --debug \
  -n ai-part-designer \
  -f helm/ai-part-designer/values-dev.yaml
```

### Template Output

```bash
helm template ai-part-designer ./helm/ai-part-designer \
  -n ai-part-designer \
  -f helm/ai-part-designer/values-dev.yaml > rendered-manifests.yaml
```

### Validate Manifests

```bash
helm template ai-part-designer ./helm/ai-part-designer \
  -f helm/ai-part-designer/values-dev.yaml | kubectl apply --dry-run=client -f -
```

## Uninstalling

```bash
helm uninstall ai-part-designer -n ai-part-designer
```

**Warning**: This will delete all deployed resources. Persistent volumes may be retained based on storage class reclaim policy.

## Troubleshooting

### Check Pod Status

```bash
kubectl get pods -n ai-part-designer
kubectl describe pod <pod-name> -n ai-part-designer
kubectl logs <pod-name> -n ai-part-designer
```

### Check Service Connectivity

```bash
kubectl get svc -n ai-part-designer
kubectl port-forward -n ai-part-designer svc/backend 8000:8000
kubectl port-forward -n ai-part-designer svc/frontend 8080:80
```

### Verify Secrets

```bash
kubectl get secrets -n ai-part-designer
kubectl describe secret backend-secrets -n ai-part-designer
```

### Check Dependency Charts

```bash
helm list -n ai-part-designer
kubectl get postgresql -n ai-part-designer
kubectl get all -l app.kubernetes.io/instance=ai-part-designer
```

## Security Considerations

1. **Secrets Management**: Never commit secrets to version control. Use:
   - External Secrets Operator + OpenBao
   - Sealed Secrets
   - Cloud provider secret managers (AWS Secrets Manager, Azure Key Vault, GCP Secret Manager)

2. **Network Policies**: Enable in production:
   ```yaml
   networkPoliciesEnabled: true
   ```

3. **TLS/SSL**: Configure cert-manager for automatic certificate management:
   ```yaml
   installCerts: true
   ingressCertIssuer: "letsencrypt-prod"
   ```

4. **RBAC**: The chart creates minimal service accounts. Review and enhance based on your security requirements.

## Contributing

See the main repository for contribution guidelines:
https://github.com/jmassardo/ai-part-designer

## License

See LICENSE file in the root of the repository.
