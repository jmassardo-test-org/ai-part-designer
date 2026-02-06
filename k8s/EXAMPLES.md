# Quick Start Examples

This directory contains example files and quick deployment scenarios for the AI Part Designer Kubernetes manifests.

## Example: Deploy to Development

### 1. Create Namespace
```bash
kubectl create namespace ai-part-designer-dev
```

### 2. Create Secrets
```bash
# Create a file with your secrets (DO NOT commit this file)
cat <<EOF > /tmp/dev-secrets.env
postgres-user=postgres
postgres-password=your-dev-password
anthropic-api-key=sk-ant-your-dev-key
secret-key=your-dev-secret-key
s3-endpoint-url=http://minio-service.infrastructure.svc.cluster.local:9000
aws-access-key-id=minioadmin
aws-secret-access-key=minioadmin
EOF

# Create secret from file
kubectl create secret generic backend-secrets \
  --namespace=ai-part-designer-dev \
  --from-env-file=/tmp/dev-secrets.env

# Clean up
rm /tmp/dev-secrets.env
```

### 3. Deploy Application
```bash
kubectl apply -k k8s/overlays/dev
```

### 4. Verify Deployment
```bash
# Check all resources
kubectl get all -n ai-part-designer-dev

# Watch pod startup
kubectl get pods -n ai-part-designer-dev -w

# Check logs
kubectl logs -n ai-part-designer-dev -l app.kubernetes.io/name=backend --tail=50
```

## Example: Deploy to Production

### 1. Create Namespace
```bash
kubectl create namespace ai-part-designer-prod
```

### 2. Create Secrets (Using Sealed Secrets - Recommended)

If you're using [Sealed Secrets](https://github.com/bitnami-labs/sealed-secrets):

```bash
# Create sealed secret
kubectl create secret generic backend-secrets \
  --namespace=ai-part-designer-prod \
  --dry-run=client \
  --from-literal=postgres-user=your-user \
  --from-literal=postgres-password=your-secure-password \
  --from-literal=anthropic-api-key=sk-ant-your-key \
  --from-literal=secret-key=your-strong-secret \
  --from-literal=s3-endpoint-url=https://s3.amazonaws.com \
  --from-literal=aws-access-key-id=your-access-key \
  --from-literal=aws-secret-access-key=your-secret-key \
  -o yaml | \
  kubeseal -o yaml > sealed-backend-secrets.yaml

# Apply sealed secret
kubectl apply -f sealed-backend-secrets.yaml
```

Or manually (less secure):
```bash
kubectl create secret generic backend-secrets \
  --namespace=ai-part-designer-prod \
  --from-literal=postgres-user=your-user \
  --from-literal=postgres-password=your-secure-password \
  --from-literal=anthropic-api-key=sk-ant-your-key \
  --from-literal=secret-key=your-strong-secret \
  --from-literal=s3-endpoint-url=https://s3.amazonaws.com \
  --from-literal=aws-access-key-id=your-access-key \
  --from-literal=aws-secret-access-key=your-secret-key
```

### 3. Deploy Application
```bash
kubectl apply -k k8s/overlays/production
```

### 4. Monitor Deployment
```bash
# Watch rollout
kubectl rollout status deployment/backend-prod -n ai-part-designer-prod
kubectl rollout status deployment/frontend-prod -n ai-part-designer-prod
kubectl rollout status deployment/celery-worker-prod -n ai-part-designer-prod

# Check HPA
kubectl get hpa -n ai-part-designer-prod
```

## Example: Update Image Tags

To update to a new version:

```bash
# Edit the overlay kustomization.yaml
vim k8s/overlays/production/kustomization.yaml

# Change image tags:
# images:
# - name: ai-part-designer-backend
#   newName: ghcr.io/jmassardo/ai-part-designer-backend
#   newTag: v1.1.0  # <-- Update this
# - name: ai-part-designer-frontend
#   newName: ghcr.io/jmassardo/ai-part-designer-frontend
#   newTag: v1.1.0  # <-- Update this

# Apply changes
kubectl apply -k k8s/overlays/production

# Watch rollout
kubectl rollout status deployment/backend-prod -n ai-part-designer-prod
```

Or use kustomize edit:
```bash
cd k8s/overlays/production
kustomize edit set image \
  ghcr.io/jmassardo/ai-part-designer-backend:v1.1.0 \
  ghcr.io/jmassardo/ai-part-designer-frontend:v1.1.0
cd ../../..
kubectl apply -k k8s/overlays/production
```

## Example: Scale Manually

```bash
# Scale backend
kubectl scale deployment/backend-prod -n ai-part-designer-prod --replicas=5

# Scale workers
kubectl scale deployment/celery-worker-prod -n ai-part-designer-prod --replicas=8

# Note: HPA will override manual scaling if metrics exceed thresholds
```

## Example: Rollback Deployment

```bash
# View rollout history
kubectl rollout history deployment/backend-prod -n ai-part-designer-prod

# Rollback to previous version
kubectl rollout undo deployment/backend-prod -n ai-part-designer-prod

# Rollback to specific revision
kubectl rollout undo deployment/backend-prod -n ai-part-designer-prod --to-revision=3
```

## Example: Troubleshooting

### View Logs
```bash
# Backend logs
kubectl logs -n ai-part-designer-prod -l app.kubernetes.io/name=backend --tail=100 -f

# Worker logs with errors only
kubectl logs -n ai-part-designer-prod -l app.kubernetes.io/name=celery-worker | grep ERROR

# Previous crashed container
kubectl logs -n ai-part-designer-prod <pod-name> --previous
```

### Debug Pod
```bash
# Execute shell in running pod
kubectl exec -it -n ai-part-designer-prod <pod-name> -- /bin/bash

# Run one-off command
kubectl exec -it -n ai-part-designer-prod <pod-name> -- env | sort
```

### Check Resources
```bash
# Resource usage
kubectl top pods -n ai-part-designer-prod
kubectl top nodes

# Events
kubectl get events -n ai-part-designer-prod --sort-by='.lastTimestamp' | tail -20
```

### Port Forward for Debugging
```bash
# Access backend API locally
kubectl port-forward -n ai-part-designer-prod svc/backend-prod 8000:8000

# Test in another terminal
curl http://localhost:8000/api/v1/health
```

## Example: Database Migration

Run database migrations as a Kubernetes Job:

```bash
# Create migration job
cat <<EOF | kubectl apply -f -
apiVersion: batch/v1
kind: Job
metadata:
  name: db-migration
  namespace: ai-part-designer-prod
spec:
  template:
    spec:
      serviceAccountName: backend-prod
      containers:
      - name: migration
        image: ghcr.io/jmassardo/ai-part-designer-backend:v1.0.0
        command: ["uv", "run", "alembic", "upgrade", "head"]
        envFrom:
        - configMapRef:
            name: backend-config
        - secretRef:
            name: backend-secrets
      restartPolicy: Never
  backoffLimit: 3
EOF

# Watch migration
kubectl logs -n ai-part-designer-prod -l job-name=db-migration -f

# Clean up after successful migration
kubectl delete job db-migration -n ai-part-designer-prod
```

## Example: One-off Celery Task

```bash
# Run a one-off task
kubectl run celery-task \
  --namespace=ai-part-designer-prod \
  --image=ghcr.io/jmassardo/ai-part-designer-backend:v1.0.0 \
  --restart=Never \
  --serviceaccount=celery-prod \
  --env="REDIS_HOST=redis-service.infrastructure.svc.cluster.local" \
  --command -- uv run celery -A app.worker.celery_app call app.worker.tasks.cleanup_old_jobs

# View logs
kubectl logs -n ai-part-designer-prod celery-task

# Clean up
kubectl delete pod celery-task -n ai-part-designer-prod
```

## Example: Health Check Endpoints

```bash
# Check backend health
kubectl run -it --rm debug \
  --image=curlimages/curl:latest \
  --restart=Never \
  -- curl http://backend-prod.ai-part-designer-prod.svc.cluster.local:8000/api/v1/health

# Check frontend
kubectl run -it --rm debug \
  --image=curlimages/curl:latest \
  --restart=Never \
  -- curl http://frontend-prod.ai-part-designer-prod.svc.cluster.local/health
```

## Example: Resource Cleanup

```bash
# Delete entire environment
kubectl delete namespace ai-part-designer-dev

# Or delete specific resources
kubectl delete -k k8s/overlays/dev
```

## CI/CD Integration

### GitOps with ArgoCD

```yaml
# argocd-app.yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: ai-part-designer-prod
  namespace: argocd
spec:
  project: default
  source:
    repoURL: https://github.com/jmassardo/ai-part-designer
    targetRevision: main
    path: k8s/overlays/production
  destination:
    server: https://kubernetes.default.svc
    namespace: ai-part-designer-prod
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
```

### GitHub Actions

```yaml
# .github/workflows/deploy-production.yml
name: Deploy to Production
on:
  push:
    tags:
      - 'v*'

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Update Image Tags
        run: |
          cd k8s/overlays/production
          kustomize edit set image \
            ghcr.io/jmassardo/ai-part-designer-backend:${{ github.ref_name }} \
            ghcr.io/jmassardo/ai-part-designer-frontend:${{ github.ref_name }}
      
      - name: Deploy to Kubernetes
        uses: azure/k8s-deploy@v4
        with:
          namespace: ai-part-designer-prod
          manifests: |
            kubectl apply -k k8s/overlays/production
          kubectl-version: latest
```
