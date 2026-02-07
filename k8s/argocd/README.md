# ArgoCD GitOps Deployment Setup

This directory contains the ArgoCD configuration for GitOps-based continuous deployment of the AI Part Designer application.

## Overview

ArgoCD provides:
- **Declarative GitOps**: Git as the single source of truth
- **Automatic Sync**: Staging environment auto-syncs from main branch
- **Manual Production**: Production requires manual approval
- **Drift Detection**: Automatic detection and correction of configuration drift
- **Easy Rollbacks**: Roll back to any previous Git commit
- **Multi-environment**: Separate configurations for staging and production

## Architecture

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   PR Merge  │───▶│  CI Build   │───▶│ Push Image  │───▶│ Update Git  │
│  to main    │    │  & Test     │    │  to GHCR    │    │  (tag/hash) │
└─────────────┘    └─────────────┘    └─────────────┘    └──────┬──────┘
                                                                 │
                                                                 ▼
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│ Production  │◀───│   Manual    │◀───│   Staging   │◀───│   ArgoCD    │
│  Synced     │    │  Approval   │    │  Auto-Sync  │    │   Detects   │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
```

## Installation

### Prerequisites

- Kubernetes cluster (1.23+)
- kubectl configured with cluster access
- cert-manager installed (for SSL certificates)
- NGINX ingress controller installed

### Step 1: Install ArgoCD

```bash
# Create ArgoCD namespace
kubectl create namespace argocd

# Install ArgoCD (use the official stable release)
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/v2.10.0/manifests/install.yaml

# Wait for ArgoCD pods to be ready
kubectl wait --for=condition=ready pod -l app.kubernetes.io/name=argocd-server -n argocd --timeout=300s
```

### Step 2: Apply Custom Configurations

```bash
# Apply namespace (if not already created)
kubectl apply -f k8s/argocd/namespace.yaml

# Apply ArgoCD configuration
kubectl apply -f k8s/argocd/install.yaml

# Apply ingress configuration (update domain first!)
# Edit ingress.yaml and replace 'argocd.yourdomain.com' with your actual domain
kubectl apply -f k8s/argocd/ingress.yaml
```

### Step 3: Get Initial Admin Password

```bash
# Retrieve the initial admin password
kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath="{.data.password}" | base64 -d
echo

# Save this password - you'll need it to log in
```

### Step 4: Access ArgoCD UI

**Option A: Using Ingress (Production)**
```bash
# Access via your domain (after DNS is configured)
https://argocd.yourdomain.com
```

**Option B: Using Port Forward (Development/Testing)**
```bash
# Port forward to access locally
kubectl port-forward svc/argocd-server -n argocd 8080:443

# Access at https://localhost:8080
# Username: admin
# Password: (from step 3)
```

### Step 5: Configure Secrets

```bash
# Create GitHub webhook secret
kubectl create secret generic argocd-github-webhook-secret \
  -n argocd \
  --from-literal=secret=$(openssl rand -hex 32)

# Create Slack notifications secret (optional)
# Get token from https://api.slack.com/apps
kubectl create secret generic argocd-notifications-secret \
  -n argocd \
  --from-literal=slack-token=xoxb-your-slack-bot-token
```

### Step 6: Deploy Applications

```bash
# Deploy staging application (auto-sync enabled)
kubectl apply -f k8s/argocd/application-staging.yaml

# Deploy production application (manual sync)
kubectl apply -f k8s/argocd/application-production.yaml

# Verify applications are created
kubectl get applications -n argocd
```

## Application Configuration

### Staging Environment

- **Auto-Sync**: Enabled
- **Self-Heal**: Enabled
- **Prune**: Enabled
- **Source Branch**: main
- **Namespace**: ai-part-designer-staging

The staging application automatically syncs changes from the main branch. When CI/CD builds new images and updates the image tags in `k8s/overlays/staging/`, ArgoCD will detect and deploy the changes automatically.

### Production Environment

- **Auto-Sync**: Disabled (manual only)
- **Sync Windows**: Mon-Fri 9am-5pm UTC
- **Source Branch**: main
- **Namespace**: ai-part-designer-prod

Production deployments require manual approval through the ArgoCD UI or CLI. Sync windows restrict when production can be deployed.

## CLI Usage

### Install ArgoCD CLI

```bash
# Linux
curl -sSL -o /usr/local/bin/argocd https://github.com/argoproj/argo-cd/releases/latest/download/argocd-linux-amd64
chmod +x /usr/local/bin/argocd

# macOS
brew install argocd
```

### Login to ArgoCD

```bash
# Port forward first
kubectl port-forward svc/argocd-server -n argocd 8080:443 &

# Login
argocd login localhost:8080 --username admin --password <password>

# Or login via domain
argocd login argocd.yourdomain.com --username admin
```

### Common Commands

```bash
# List all applications
argocd app list

# Get application details
argocd app get ai-part-designer-staging

# Sync application (deploy)
argocd app sync ai-part-designer-staging

# Sync with prune (remove deleted resources)
argocd app sync ai-part-designer-staging --prune

# Rollback to previous version
argocd app rollback ai-part-designer-staging

# View application logs
argocd app logs ai-part-designer-staging

# View sync history
argocd app history ai-part-designer-staging

# Manually sync production (requires admin role)
argocd app sync ai-part-designer-production --prune
```

## Deployment Workflow

### Deploying to Staging

1. Merge PR to main branch
2. CI/CD pipeline builds and pushes images to GHCR
3. CI/CD updates image tags in `k8s/overlays/staging/kustomization.yaml`
4. ArgoCD detects changes and auto-syncs to staging cluster
5. Notifications sent to Slack (if configured)

### Deploying to Production

1. Verify staging deployment is successful
2. Update image tags in `k8s/overlays/production/kustomization.yaml`
3. Commit and push changes to main branch
4. Login to ArgoCD UI or CLI
5. Navigate to ai-part-designer-production application
6. Click "Sync" or run `argocd app sync ai-part-designer-production`
7. Review changes in the diff view
8. Confirm sync to deploy
9. Monitor deployment progress in ArgoCD UI

## Rollback Procedures

### Rollback via ArgoCD UI

1. Navigate to the application in ArgoCD UI
2. Click "History" tab
3. Select a previous successful deployment
4. Click "Rollback"
5. Confirm rollback

### Rollback via CLI

```bash
# View deployment history
argocd app history ai-part-designer-production

# Rollback to specific revision
argocd app rollback ai-part-designer-production <revision-id>

# Rollback to previous revision
argocd app rollback ai-part-designer-production
```

### Rollback via Git

```bash
# Revert the Git commit that caused the issue
git revert <commit-hash>
git push origin main

# ArgoCD will sync to the reverted state
```

## Monitoring & Notifications

### ArgoCD Dashboard

Access the ArgoCD dashboard to:
- View application sync status
- See deployment history
- View resource health
- Examine detailed logs
- Compare Git state vs cluster state

### Slack Notifications

Configure Slack notifications in `k8s/argocd/install.yaml`:

1. Create a Slack app and bot token
2. Create the secret with your token
3. Applications will send notifications on:
   - Sync success
   - Sync failure
   - Health degradation
   - Deployment events

### Prometheus Metrics

ArgoCD exposes Prometheus metrics at:
- `argocd-metrics:8082/metrics` - Application controller metrics
- `argocd-server-metrics:8083/metrics` - API server metrics
- `argocd-repo-server:8084/metrics` - Repository server metrics

## RBAC Configuration

### Roles

- **Admin**: Full access, can sync production
- **Developer**: Can view and sync staging, read-only for production
- **Readonly**: Can view all applications and logs

### Managing Users

```bash
# Add local user
argocd account update-password --account <username> --new-password <password>

# List users
argocd account list

# Disable user
argocd account update-password --account <username> --current-password <old> --new-password <new>
```

## Troubleshooting

### Application OutOfSync

```bash
# Check differences
argocd app diff ai-part-designer-staging

# Force sync
argocd app sync ai-part-designer-staging --force
```

### Application Unhealthy

```bash
# Check resource status
kubectl get pods -n ai-part-designer-staging

# View ArgoCD logs
kubectl logs -n argocd deployment/argocd-application-controller

# View application events
argocd app get ai-part-designer-staging
```

### Sync Failing

```bash
# View sync operation details
argocd app get ai-part-designer-staging --refresh

# Check repository connection
argocd repo list

# View detailed error logs
kubectl logs -n argocd deployment/argocd-repo-server
```

### Reset to Known Good State

```bash
# Hard refresh from Git
argocd app get ai-part-designer-staging --hard-refresh

# Delete and recreate application (nuclear option)
kubectl delete application ai-part-designer-staging -n argocd
kubectl apply -f k8s/argocd/application-staging.yaml
```

## Security Best Practices

1. **Use RBAC**: Restrict production sync to admin role only
2. **Enable MFA**: Configure SSO with MFA for production access
3. **Rotate Secrets**: Regularly rotate admin password and webhook secrets
4. **Audit Logs**: Enable and monitor ArgoCD audit logs
5. **Network Policies**: Restrict ArgoCD namespace access
6. **Webhook Security**: Use secret validation for GitHub webhooks
7. **TLS**: Always use TLS for ArgoCD server access
8. **Sync Windows**: Restrict production deployments to business hours

## Maintenance

### Upgrading ArgoCD

```bash
# Check current version
argocd version

# Upgrade to new version
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/v2.11.0/manifests/install.yaml

# Reapply custom configurations
kubectl apply -f k8s/argocd/install.yaml
```

### Backup ArgoCD

```bash
# Export all applications
argocd app list -o yaml > argocd-apps-backup.yaml

# Export application definitions from Git
# (Declarative apps are automatically backed up in Git!)
```

## References

- [ArgoCD Documentation](https://argo-cd.readthedocs.io/)
- [ArgoCD Best Practices](https://argo-cd.readthedocs.io/en/stable/user-guide/best_practices/)
- [GitOps Principles](https://www.gitops.tech/)
- [Kustomize Documentation](https://kubectl.docs.kubernetes.io/references/kustomize/)
