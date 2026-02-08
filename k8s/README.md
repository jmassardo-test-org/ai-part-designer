# Kubernetes Deployment with Kustomize

This directory contains Kubernetes manifests for deploying the AI Part Designer application across different environments using Kustomize.

## Directory Structure

```
k8s/
├── base/                          # Base Kubernetes manifests
│   ├── kustomization.yaml
│   ├── namespace.yaml
│   ├── backend/                   # Backend API service
│   │   ├── deployment.yaml
│   │   ├── service.yaml
│   │   ├── serviceaccount.yaml
│   │   ├── configmap.yaml
│   │   ├── seed-job.yaml            # Database seed Job
│   │   ├── hpa.yaml               # Horizontal Pod Autoscaler
│   │   └── pdb.yaml               # Pod Disruption Budget
│   ├── frontend/                  # Frontend (nginx serving static files)
│   │   ├── deployment.yaml
│   │   ├── service.yaml
│   │   ├── configmap.yaml
│   │   └── pdb.yaml
│   ├── celery/                    # Celery workers and scheduler
│   │   ├── serviceaccount.yaml
│   │   ├── worker-deployment.yaml
│   │   ├── beat-deployment.yaml
│   │   ├── worker-hpa.yaml
│   │   └── worker-pdb.yaml
│   ├── cert-manager/              # TLS certificate automation
│   │   └── cluster-issuer.yaml    # Let's Encrypt + self-signed issuers
│   ├── ingress/                   # External traffic routing
│   │   └── ingress.yaml           # NGINX Ingress with TLS and security
│   └── network-policies/          # Network security policies
│       ├── default-deny.yaml
│       ├── backend-ingress.yaml
│       ├── backend-egress.yaml
│       ├── frontend-ingress.yaml
│       ├── frontend-egress.yaml
│       ├── celery-worker-egress.yaml
│       └── celery-beat-egress.yaml
├── DNS_CONFIGURATION.md           # DNS setup guide for ingress
└── overlays/                      # Environment-specific configurations
    ├── dev/
    │   ├── kustomization.yaml
    │   └── patches/
    │       ├── backend-dev.yaml
    │       ├── frontend-dev.yaml
    │       └── celery-worker-dev.yaml
    ├── staging/
    │   ├── kustomization.yaml
    │   └── patches/
    │       ├── backend-staging.yaml
    │       ├── frontend-staging.yaml
    │       └── celery-worker-staging.yaml
    └── production/
        ├── kustomization.yaml
        └── patches/
            ├── backend-prod.yaml
            ├── frontend-prod.yaml
            ├── celery-worker-prod.yaml
            └── celery-beat-prod.yaml
```

## Prerequisites

1. **Kubernetes Cluster**: A running Kubernetes cluster (v1.24+)
2. **kubectl**: Kubernetes command-line tool
3. **kustomize**: Built into kubectl (v1.14+) or standalone
4. **Container Images**: Build and push Docker images to a container registry
5. **Infrastructure Services**: PostgreSQL, Redis, and S3-compatible storage (or MinIO)

## Component Overview

| Component | Type | Base Replicas | Description |
|-----------|------|---------------|-------------|
| Backend API | Deployment | 3 | FastAPI application with health checks and autoscaling |
| Frontend | Deployment | 2 | Nginx serving React static files |
| Celery Worker | Deployment | 3 | Background job processing with autoscaling |
| Celery Beat | Deployment | 1 | Task scheduler (single replica) |

## Building and Pushing Images

Before deploying, build and push the Docker images:

```bash
# Build backend image
docker build -t ghcr.io/jmassardo/ai-part-designer-backend:v1.0.0 \
  --target production \
  ./backend

# Build frontend image
docker build -t ghcr.io/jmassardo/ai-part-designer-frontend:v1.0.0 \
  --target production \
  ./frontend

# Push images to registry
docker push ghcr.io/jmassardo/ai-part-designer-backend:v1.0.0
docker push ghcr.io/jmassardo/ai-part-designer-frontend:v1.0.0
```

## Secret Management

⚠️ **IMPORTANT**: The example configurations include placeholder secrets. In production, use one of:

- **Sealed Secrets**: Encrypt secrets for GitOps workflows
- **External Secrets Operator**: Sync from AWS Secrets Manager, HashiCorp Vault, etc.
- **kubectl create secret**: Manually create secrets (not recommended for production)

### Creating Secrets Manually

```bash
# Create backend secrets
kubectl create secret generic backend-secrets \
  --namespace=ai-part-designer-prod \
  --from-literal=postgres-user=your-db-user \
  --from-literal=postgres-password=your-secure-password \
  --from-literal=anthropic-api-key=sk-ant-your-api-key \
  --from-literal=secret-key=your-strong-secret-key \
  --from-literal=s3-endpoint-url=https://s3.amazonaws.com \
  --from-literal=aws-access-key-id=your-access-key \
  --from-literal=aws-secret-access-key=your-secret-key
```

## Deployment Instructions

### 1. Preview Manifests (Dry Run)

```bash
# Development
kubectl kustomize k8s/overlays/dev

# Staging
kubectl kustomize k8s/overlays/staging

# Production
kubectl kustomize k8s/overlays/production
```

### 2. Deploy to Development

```bash
# Create or update secrets first
kubectl apply -k k8s/overlays/dev

# Verify deployment
kubectl get all -n ai-part-designer-dev

# Check pod status
kubectl get pods -n ai-part-designer-dev

# View logs
kubectl logs -n ai-part-designer-dev -l app.kubernetes.io/name=backend --tail=50
```

### 3. Deploy to Staging

```bash
# Update secrets for staging
kubectl apply -k k8s/overlays/staging

# Verify deployment
kubectl get all -n ai-part-designer-staging
```

### 4. Deploy to Production

```bash
# Ensure secrets are properly configured
kubectl apply -k k8s/overlays/production

# Verify deployment
kubectl get all -n ai-part-designer-prod

# Check HPA status
kubectl get hpa -n ai-part-designer-prod
```

## Database Migrations

**Run migrations before seeding.** The `db-migrate` Job runs Alembic migrations to create or update the database schema.

```bash
# Using Makefile (recommended)
make k8s-db-migrate                            # dev namespace (default)
make k8s-db-migrate NS=ai-part-designer-staging  # other namespace
make k8s-db-migrate-logs                       # tail migration logs

# Or manually
kubectl delete job db-migrate-dev -n ai-part-designer-dev --ignore-not-found
kubectl apply -k k8s/overlays/dev
kubectl wait --for=condition=complete --timeout=300s job/db-migrate-dev -n ai-part-designer-dev
```

## Database Seeding

After deploying and running migrations, seed the database with initial data (tiers, templates, components, demo users, starter designs). All seed modules are idempotent — safe to run multiple times.

### Option A: Seed Job (Recommended)

The `db-seed` Kubernetes Job runs all seed modules in sequence using the same backend image:

```bash
# Delete any previous run, then apply (kustomize auto-suffixes with -dev)
kubectl delete job db-seed-dev -n ai-part-designer-dev --ignore-not-found
kubectl apply -k k8s/overlays/dev

# Watch progress
kubectl logs -n ai-part-designer-dev -l app.kubernetes.io/name=db-seed -f

# Wait for completion
kubectl wait --for=condition=complete --timeout=300s job/db-seed-dev -n ai-part-designer-dev
```

Or use the Makefile shortcut:

```bash
make k8s-db-seed                          # dev namespace (default)
make k8s-db-seed NS=ai-part-designer-staging  # other namespace
make k8s-db-seed-logs                     # tail seed logs
make k8s-db-seed-status                   # check job status
```

### Option B: Exec into Backend Pod

For a quick one-off seed without creating a Job:

```bash
make k8s-db-seed-exec                     # runs all 5 seed modules via exec

# Or manually:
kubectl exec -n ai-part-designer-dev deploy/backend-dev -- python -m app.seeds.tiers
kubectl exec -n ai-part-designer-dev deploy/backend-dev -- python -m app.seeds.templates
kubectl exec -n ai-part-designer-dev deploy/backend-dev -- python -m app.seeds.components_v2
kubectl exec -n ai-part-designer-dev deploy/backend-dev -- python -m app.seeds.users
kubectl exec -n ai-part-designer-dev deploy/backend-dev -- python -m app.seeds.starters
```

### Seed Modules

| Module | What It Seeds |
|--------|---------------|
| `tiers` | Subscription tiers (Free, Starter, Pro, Enterprise) |
| `templates` | Design templates library |
| `components_v2` | CAD v2 component registry |
| `users` | Demo users (`demo@example.com` / `demo123`, admin, etc.) |
| `starters` | Marketplace starter designs (Raspberry Pi cases, etc.) |

### Troubleshooting

```bash
# Check pod events if the job is stuck
kubectl describe job db-seed-dev -n ai-part-designer-dev

# Check pod logs for errors
kubectl logs -n ai-part-designer-dev -l app.kubernetes.io/name=db-seed --tail=100

# Re-run: delete the old job first (K8s won't re-create an existing job)
kubectl delete job db-seed-dev -n ai-part-designer-dev --ignore-not-found
kubectl apply -k k8s/overlays/dev
```

**Note:** The users and starters seeds are memory-intensive and may time out on resource-constrained clusters. The essential data (tiers, templates, components) typically completes successfully. If the full job times out, you can run just the essential seeds:

```bash
# Verify what's seeded
kubectl run dbcheck --rm -i --restart=Never -n ai-part-designer-dev \
  --image=postgres:16-alpine --env='PGPASSWORD=<password>' -- \
  psql -h postgres-cluster-dev-rw -U app -d assemblematic_ai \
  -c "SELECT 'tiers', COUNT(*) FROM subscription_tiers UNION ALL SELECT 'templates', COUNT(*) FROM templates;"

# Run optional seeds manually if needed
kubectl exec -n ai-part-designer-dev deploy/backend-dev -- /app/.venv/bin/python -m app.seeds.users
kubectl exec -n ai-part-designer-dev deploy/backend-dev -- /app/.venv/bin/python -m app.seeds.starters
```

## Configuration

### Environment Variables

Key configuration is managed through ConfigMaps and Secrets:

**ConfigMap (backend-config)**:
- Application settings (non-sensitive)
- Database connection parameters
- Redis configuration
- Storage bucket names
- AI model configuration
- Feature flags

**Secret (backend-secrets)**:
- Database credentials
- API keys (Anthropic)
- S3 credentials
- JWT secret key

### Resource Limits

| Component | CPU Request | CPU Limit | Memory Request | Memory Limit |
|-----------|-------------|-----------|----------------|--------------|
| Backend (Prod) | 250m | 1000m | 512Mi | 2Gi |
| Frontend (Prod) | 50m | 200m | 64Mi | 256Mi |
| Worker (Prod) | 500m | 2000m | 1Gi | 4Gi |
| Beat (Prod) | 50m | 200m | 128Mi | 512Mi |

### Autoscaling

**Backend HPA**:
- Min replicas: 2
- Max replicas: 10
- Target CPU: 70%
- Target Memory: 80%

**Celery Worker HPA**:
- Min replicas: 2
- Max replicas: 15
- Target CPU: 75%
- Target Memory: 85%

## Health Checks

All services include comprehensive health checks:

- **Startup Probe**: Allows time for application initialization
- **Liveness Probe**: Detects and restarts unhealthy containers
- **Readiness Probe**: Controls traffic routing to healthy pods

Backend health endpoint: `GET /api/v1/health`

## Network Policies

Network policies enforce pod-to-pod security:

1. **Default Deny**: Blocks all ingress/egress by default
2. **Backend Ingress**: Allows traffic from frontend and ingress controller
3. **Backend Egress**: Allows access to database, Redis, and external APIs
4. **Frontend Ingress**: Allows traffic from ingress controller
5. **Frontend Egress**: Allows access to backend API
6. **Celery Worker Egress**: Allows access to database, Redis, and external APIs
7. **Celery Beat Egress**: Allows access to Redis and database

## Monitoring and Observability

### Prometheus Metrics

Backend and worker pods expose Prometheus metrics:

```yaml
annotations:
  prometheus.io/scrape: "true"
  prometheus.io/port: "8000"
  prometheus.io/path: "/metrics"
```

### Viewing Logs

```bash
# Backend logs
kubectl logs -n ai-part-designer-prod -l app.kubernetes.io/name=backend --tail=100 -f

# Worker logs
kubectl logs -n ai-part-designer-prod -l app.kubernetes.io/name=celery-worker --tail=100 -f

# Frontend logs
kubectl logs -n ai-part-designer-prod -l app.kubernetes.io/name=frontend --tail=100 -f
```

## Troubleshooting

### Check Pod Status

```bash
# Get all resources
kubectl get all -n ai-part-designer-prod

# Describe pod for detailed info
kubectl describe pod <pod-name> -n ai-part-designer-prod

# Check events
kubectl get events -n ai-part-designer-prod --sort-by='.lastTimestamp'
```

### Check ConfigMaps and Secrets

```bash
# List ConfigMaps
kubectl get configmaps -n ai-part-designer-prod

# View ConfigMap contents
kubectl describe configmap backend-config -n ai-part-designer-prod

# List Secrets
kubectl get secrets -n ai-part-designer-prod
```

### Debug Container Issues

```bash
# Execute shell in running pod
kubectl exec -it <pod-name> -n ai-part-designer-prod -- /bin/bash

# Port forward for local access
kubectl port-forward -n ai-part-designer-prod svc/backend 8000:8000
```

### Check HPA Status

```bash
# View HPA metrics
kubectl get hpa -n ai-part-designer-prod

# Describe HPA for detailed metrics
kubectl describe hpa backend -n ai-part-designer-prod
```

## Rollback

To rollback a deployment:

```bash
# View deployment history
kubectl rollout history deployment/backend -n ai-part-designer-prod

# Rollback to previous version
kubectl rollout undo deployment/backend -n ai-part-designer-prod

# Rollback to specific revision
kubectl rollout undo deployment/backend -n ai-part-designer-prod --to-revision=2
```

## Scaling

### Manual Scaling

```bash
# Scale backend replicas
kubectl scale deployment/backend -n ai-part-designer-prod --replicas=5

# Scale workers
kubectl scale deployment/celery-worker -n ai-part-designer-prod --replicas=8
```

### HPA Autoscaling

HPA is configured by default. Monitor with:

```bash
kubectl get hpa -n ai-part-designer-prod -w
```

## Maintenance

### Update Configuration

1. Edit the appropriate kustomization.yaml or patch file
2. Apply changes:
   ```bash
   kubectl apply -k k8s/overlays/production
   ```

### Update Images

1. Update image tags in `k8s/overlays/<env>/kustomization.yaml`
2. Apply changes:
   ```bash
   kubectl apply -k k8s/overlays/production
   ```

### Rolling Restart

```bash
# Restart all backend pods
kubectl rollout restart deployment/backend -n ai-part-designer-prod
```

## Infrastructure Dependencies

These manifests assume the following infrastructure services are available:

1. **PostgreSQL Database**
   - Service name: `postgres-service.infrastructure.svc.cluster.local`
   - Port: 5432

2. **Redis Cache**
   - Service name: `redis-service.infrastructure.svc.cluster.local`
   - Port: 6379

3. **S3-Compatible Storage**
   - AWS S3, MinIO, or compatible service
   - Buckets: designs, exports, thumbnails

4. **Ingress Controller**
   - For external traffic routing
   - NGINX Ingress Controller (recommended)
   - See [INGRESS.md](INGRESS.md) for examples

5. **cert-manager (optional)**
   - For automatic TLS certificate provisioning
   - ClusterIssuers in `base/cert-manager/cluster-issuer.yaml`
   - See [DNS_CONFIGURATION.md](DNS_CONFIGURATION.md) for setup

## External Access with Ingress

The base manifests include pre-configured Ingress resources with TLS and security features:

- **Location**: `k8s/base/ingress/ingress.yaml`
- **Certificate Issuers**: `k8s/base/cert-manager/cluster-issuer.yaml`

### Quick Setup

1. **Install NGINX Ingress Controller**:
   ```bash
   # Via Helm (recommended)
   helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx
   helm install ingress-nginx ingress-nginx/ingress-nginx \
     --namespace ingress-nginx \
     --create-namespace
   ```

2. **Install cert-manager**:
   ```bash
   helm repo add jetstack https://charts.jetstack.io
   helm install cert-manager jetstack/cert-manager \
     --namespace cert-manager \
     --create-namespace \
     --set installCRDs=true
   ```

3. **Apply base manifests** (includes ingress):
   ```bash
   kubectl apply -k k8s/overlays/production
   ```

4. **Configure DNS** - See [DNS_CONFIGURATION.md](DNS_CONFIGURATION.md)

### Ingress Features

- ✅ Automatic TLS with Let's Encrypt
- ✅ HTTP to HTTPS redirect
- ✅ Rate limiting (100 req/s per IP)
- ✅ Request size limits (100MB for CAD uploads)
- ✅ Security headers (HSTS, X-Frame-Options, etc.)
- ✅ WebSocket support for real-time updates
- ✅ Extended timeouts for AI CAD generation
- ✅ Health check endpoints

### Customization

To customize ingress settings, edit `k8s/base/ingress/ingress.yaml`:

```yaml
# Change rate limits
nginx.ingress.kubernetes.io/limit-rps: "200"

# Change certificate issuer
cert-manager.io/cluster-issuer: "letsencrypt-staging"

# Change max upload size
nginx.ingress.kubernetes.io/proxy-body-size: "200m"
```

## Security Best Practices

1. ✅ Use specific image tags (not `latest`) in production
2. ✅ Encrypt secrets using Sealed Secrets or External Secrets Operator
3. ✅ Enable NetworkPolicies for pod-to-pod security
4. ✅ Run containers as non-root users
5. ✅ Use read-only root filesystems where possible
6. ✅ Set resource limits to prevent resource exhaustion
7. ✅ Configure Pod Security Standards/Policies
8. ✅ Regularly scan images for vulnerabilities
9. ✅ Rotate secrets and credentials regularly
10. ✅ Use RBAC for access control

## Next Steps

1. **External Access**: Configure ingress and DNS - see [DNS_CONFIGURATION.md](DNS_CONFIGURATION.md)
2. **Monitoring**: Deploy Prometheus and Grafana for metrics
3. **Logging**: Configure centralized logging (EFK/ELK stack)
4. **Backup Strategy**: Implement database and volume backups
5. **Disaster Recovery**: Document and test DR procedures
6. **CI/CD Integration**: Automate deployments with GitOps (ArgoCD/Flux)

## References

- [Kustomize Documentation](https://kustomize.io/)
- [Kubernetes Best Practices](https://kubernetes.io/docs/concepts/configuration/overview/)
- [Pod Security Standards](https://kubernetes.io/docs/concepts/security/pod-security-standards/)
- [Network Policies](https://kubernetes.io/docs/concepts/services-networking/network-policies/)
