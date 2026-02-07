# ArgoCD Quick Start Guide

**For**: DevOps Engineers, SREs, Platform Engineers
**Time to Complete**: 30-60 minutes
**Prerequisites**: Kubernetes cluster, kubectl configured, cluster-admin access

---

## 🚀 Installation (15 minutes)

### Step 1: Install ArgoCD

```bash
# Create ArgoCD namespace
kubectl create namespace argocd

# Install ArgoCD stable release
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/v2.10.0/manifests/install.yaml

# Wait for pods to be ready (may take 2-3 minutes)
kubectl wait --for=condition=ready pod -l app.kubernetes.io/name=argocd-server -n argocd --timeout=300s
```

### Step 2: Apply Custom Configuration

```bash
# Apply custom RBAC, notifications, and settings
kubectl apply -f k8s/argocd/install.yaml

# Apply ingress (update domain first!)
# Edit k8s/argocd/ingress.yaml and replace 'argocd.yourdomain.com' with your domain
kubectl apply -f k8s/argocd/ingress.yaml
```

### Step 3: Get Admin Password

```bash
# Retrieve initial admin password
kubectl -n argocd get secret argocd-initial-admin-secret \
  -o jsonpath="{.data.password}" | base64 -d
echo

# Save this password securely!
```

### Step 4: Access ArgoCD

**Option A: Port Forward (Quick Test)**
```bash
kubectl port-forward svc/argocd-server -n argocd 8080:443 &
# Access at https://localhost:8080
```

**Option B: Ingress (Production)**
```bash
# Access at https://argocd.yourdomain.com
# (Requires DNS configured and ingress controller installed)
```

**Login**: Username `admin`, Password from Step 3

---

## 📦 Deploy Applications (10 minutes)

### Step 1: Create Secrets

```bash
# GitHub webhook secret
kubectl create secret generic argocd-github-webhook-secret \
  -n argocd \
  --from-literal=secret=$(openssl rand -hex 32)

# Slack notifications (optional)
kubectl create secret generic argocd-notifications-secret \
  -n argocd \
  --from-literal=slack-token=xoxb-your-slack-bot-token
```

### Step 2: Deploy Staging Application

```bash
kubectl apply -f k8s/argocd/application-staging.yaml

# Verify application created
kubectl get application -n argocd ai-part-designer-staging

# Watch sync (may take 1-2 minutes)
kubectl get application -n argocd ai-part-designer-staging -w
```

### Step 3: Deploy Production Application

```bash
kubectl apply -f k8s/argocd/application-production.yaml

# Verify application created
kubectl get application -n argocd ai-part-designer-production

# Note: Production won't auto-sync (manual approval required)
```

---

## 🔧 Install ArgoCD CLI (5 minutes)

### Linux

```bash
curl -sSL -o /tmp/argocd https://github.com/argoproj/argo-cd/releases/latest/download/argocd-linux-amd64
sudo install -m 755 /tmp/argocd /usr/local/bin/argocd
argocd version
```

### macOS

```bash
brew install argocd
argocd version
```

### Login

```bash
# If using port-forward
argocd login localhost:8080 --insecure

# If using ingress
argocd login argocd.yourdomain.com

# Enter username: admin
# Enter password: <from installation step>
```

---

## 🎯 Common Operations (5 minutes each)

### View Application Status

```bash
# List all applications
argocd app list

# Get detailed status
argocd app get ai-part-designer-staging

# Watch sync progress
watch argocd app get ai-part-designer-staging
```

### Sync Application

```bash
# Sync staging (developers can do this)
argocd app sync ai-part-designer-staging

# Sync production (requires admin role)
argocd app sync ai-part-designer-production --prune
```

### View Logs

```bash
# Application logs
argocd app logs ai-part-designer-staging --follow

# Specific pod logs
kubectl logs -n ai-part-designer-staging deployment/backend-staging --follow
```

### Rollback

```bash
# View history
argocd app history ai-part-designer-staging

# Rollback to previous
argocd app rollback ai-part-designer-staging

# Rollback to specific revision
argocd app rollback ai-part-designer-staging 5
```

---

## 🔍 Troubleshooting

### Application OutOfSync

```bash
# Refresh application state
argocd app get ai-part-designer-staging --refresh

# View differences
argocd app diff ai-part-designer-staging

# Force sync
argocd app sync ai-part-designer-staging --force
```

### Application Unhealthy

```bash
# Check pod status
kubectl get pods -n ai-part-designer-staging

# Check failed pods
kubectl describe pod <pod-name> -n ai-part-designer-staging

# Check logs
kubectl logs <pod-name> -n ai-part-designer-staging
```

### Can't Access UI

```bash
# Check ArgoCD pods
kubectl get pods -n argocd

# Check logs
kubectl logs -n argocd deployment/argocd-server

# Use port-forward as workaround
kubectl port-forward svc/argocd-server -n argocd 8080:443
```

### Forgot Admin Password

```bash
# Get initial password
kubectl -n argocd get secret argocd-initial-admin-secret \
  -o jsonpath="{.data.password}" | base64 -d

# Or reset password (requires login first)
argocd account update-password
```

---

## ✅ Verification Checklist

After installation, verify:

- [ ] ArgoCD pods running: `kubectl get pods -n argocd`
- [ ] Can access ArgoCD UI (port-forward or ingress)
- [ ] Can login with admin credentials
- [ ] Applications deployed: `argocd app list`
- [ ] Staging app shows "Synced" and "Healthy"
- [ ] Production app shows "OutOfSync" (expected)
- [ ] Can sync staging: `argocd app sync ai-part-designer-staging`
- [ ] ArgoCD CLI working: `argocd version`
- [ ] Notifications configured (if using Slack)

---

## 📚 Next Steps

1. **Read Full Documentation**:
   - [k8s/argocd/README.md](../../k8s/argocd/README.md) - Complete setup guide
   - [argocd-operations.md](./argocd-operations.md) - Operations procedures
   - [rollback-runbook.md](./rollback-runbook.md) - Rollback procedures

2. **Test Deployment Workflow**:
   - Make a code change and merge to main
   - Watch staging auto-sync
   - Test production manual sync
   - Practice rollback

3. **Configure Notifications**:
   - Set up Slack workspace integration
   - Test notification delivery

4. **Train Team**:
   - Share ArgoCD dashboard access
   - Walk through common operations
   - Practice emergency rollback

---

## 🆘 Getting Help

- **Documentation**: See [argocd-operations.md](./argocd-operations.md)
- **Rollback Help**: See [rollback-runbook.md](./rollback-runbook.md)
- **ArgoCD Docs**: https://argo-cd.readthedocs.io/
- **Slack**: #devops channel
- **On-call**: Use PagerDuty for emergencies

---

## 🎓 Learning Resources

- [ArgoCD Getting Started](https://argo-cd.readthedocs.io/en/stable/getting_started/)
- [ArgoCD Best Practices](https://argo-cd.readthedocs.io/en/stable/user-guide/best_practices/)
- [GitOps Principles](https://www.gitops.tech/)
- [Kustomize Tutorial](https://kubectl.docs.kubernetes.io/guides/introduction/kustomize/)

---

**Time Saved**: After initial setup, deployments go from 30 minutes to 3 minutes!

**Happy GitOpsing! 🚀**
