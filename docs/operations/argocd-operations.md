# ArgoCD Deployment Operations Guide

This guide provides step-by-step procedures for deploying and operating the AI Part Designer application using ArgoCD GitOps.

## Table of Contents

1. [Deployment Workflow](#deployment-workflow)
2. [Staging Deployments](#staging-deployments)
3. [Production Deployments](#production-deployments)
4. [Rollback Procedures](#rollback-procedures)
5. [Monitoring Deployments](#monitoring-deployments)
6. [Troubleshooting](#troubleshooting)
7. [Emergency Procedures](#emergency-procedures)

---

## Deployment Workflow

### Overall Flow

```
┌────────────────────────────────────────────────────────────────────┐
│ 1. Developer merges PR to main                                    │
└────────────────┬───────────────────────────────────────────────────┘
                 │
                 ▼
┌────────────────────────────────────────────────────────────────────┐
│ 2. CI Pipeline (ci.yml)                                           │
│    - Runs tests and builds                                        │
│    - Builds Docker images                                         │
│    - Pushes to GHCR with SHA tag                                  │
└────────────────┬───────────────────────────────────────────────────┘
                 │
                 ▼
┌────────────────────────────────────────────────────────────────────┐
│ 3. CD Pipeline (deploy.yml)                                       │
│    - Triggers on CI success                                       │
│    - Updates staging kustomization.yaml with new image tags       │
│    - Commits changes to main branch                               │
└────────────────┬───────────────────────────────────────────────────┘
                 │
                 ▼
┌────────────────────────────────────────────────────────────────────┐
│ 4. ArgoCD detects Git changes                                     │
│    - Staging: Auto-syncs immediately (self-heal enabled)          │
│    - Production: Shows "OutOfSync" status (manual sync required)  │
└────────────────┬───────────────────────────────────────────────────┘
                 │
                 ▼
┌────────────────────────────────────────────────────────────────────┐
│ 5. Deployment to Kubernetes                                       │
│    - ArgoCD applies Kustomize manifests                           │
│    - Rolling update of deployments                                │
│    - Health checks verify pod readiness                           │
└────────────────┬───────────────────────────────────────────────────┘
                 │
                 ▼
┌────────────────────────────────────────────────────────────────────┐
│ 6. Notifications (if configured)                                  │
│    - Slack notification on success/failure                        │
│    - Status visible in ArgoCD dashboard                           │
└────────────────────────────────────────────────────────────────────┘
```

---

## Staging Deployments

### Automatic Deployment Process

Staging deployments happen automatically when code is merged to main:

1. **Code Merge**: PR merged to main branch
2. **CI Build**: GitHub Actions CI pipeline runs
3. **Image Build**: Docker images built and tagged with commit SHA
4. **Tag Update**: CD workflow updates `k8s/overlays/staging/kustomization.yaml`
5. **Auto-Sync**: ArgoCD detects change and deploys automatically
6. **Notification**: Slack notification sent (if configured)

### Monitoring Staging Deployment

```bash
# Check application status
argocd app get ai-part-designer-staging

# Watch sync progress
argocd app sync ai-part-designer-staging --async
kubectl get pods -n ai-part-designer-staging -w

# View application logs
argocd app logs ai-part-designer-staging --follow

# Check sync history
argocd app history ai-part-designer-staging
```

### Verifying Staging Deployment

```bash
# Check all pods are running
kubectl get pods -n ai-part-designer-staging

# Verify pod health
kubectl get pods -n ai-part-designer-staging -o wide

# Check service endpoints
kubectl get endpoints -n ai-part-designer-staging

# Test application health endpoint
kubectl port-forward -n ai-part-designer-staging svc/backend-service 8000:8000
curl http://localhost:8000/health

# Check logs for errors
kubectl logs -n ai-part-designer-staging deployment/backend-staging --tail=100
```

### Manual Staging Sync (if needed)

```bash
# Refresh application state
argocd app get ai-part-designer-staging --refresh

# Manual sync
argocd app sync ai-part-designer-staging

# Force sync (override sync options)
argocd app sync ai-part-designer-staging --force

# Sync with prune (remove deleted resources)
argocd app sync ai-part-designer-staging --prune
```

---

## Production Deployments

### Pre-Deployment Checklist

Before deploying to production, verify:

- [ ] Staging deployment successful for at least 24 hours
- [ ] No critical bugs reported in staging
- [ ] All smoke tests passing in staging
- [ ] Database migrations tested (if any)
- [ ] Rollback plan documented and understood
- [ ] Deployment window confirmed (Mon-Fri 9am-5pm UTC)
- [ ] Stakeholders notified of deployment
- [ ] On-call engineer available
- [ ] Monitoring dashboards open and ready
- [ ] Rollback credentials and access verified

### Production Deployment Process

#### Step 1: Trigger Production Deployment

```bash
# Option A: Via GitHub Actions UI
# 1. Go to Actions -> CD - Deploy to Environments
# 2. Click "Run workflow"
# 3. Select:
#    - Environment: production
#    - Image tag: <sha-abc123 or v1.0.0>
# 4. Click "Run workflow"

# Option B: Via GitHub CLI
gh workflow run deploy.yml \
  -f environment=production \
  -f image_tag=sha-abc123
```

This creates a Pull Request with the production image tag updates.

#### Step 2: Review Deployment PR

1. Review the PR created by the workflow
2. Verify image tags are correct
3. Complete the pre-deployment checklist in the PR
4. Get required approvals
5. Merge the PR

#### Step 3: Login to ArgoCD

```bash
# Option A: Via CLI
argocd login argocd.yourdomain.com --username admin

# Option B: Via UI
# Open https://argocd.yourdomain.com in browser
# Login with admin credentials
```

#### Step 4: Sync Production Application

```bash
# Check application status
argocd app get ai-part-designer-production

# View diff before syncing
argocd app diff ai-part-designer-production

# Sync production (requires admin role)
argocd app sync ai-part-designer-production --prune

# Watch sync progress
watch argocd app get ai-part-designer-production
```

#### Step 5: Monitor Deployment

```bash
# Watch pod rollout
kubectl get pods -n ai-part-designer-prod -w

# Check deployment status
kubectl rollout status deployment/backend-prod -n ai-part-designer-prod
kubectl rollout status deployment/frontend-prod -n ai-part-designer-prod

# View real-time logs
kubectl logs -n ai-part-designer-prod deployment/backend-prod --follow --tail=50
```

#### Step 6: Verify Deployment

```bash
# Health check
curl https://api.yourdomain.com/health

# Check application version
curl https://api.yourdomain.com/version

# Run smoke tests
cd frontend
npm run test:e2e:prod

# Monitor metrics
# - Open Grafana dashboard
# - Check error rates
# - Verify response times
# - Check database connections
```

#### Step 7: Post-Deployment Verification

Monitor for 30 minutes:
- [ ] Error rate < 0.1%
- [ ] Response time p95 < 200ms
- [ ] All health checks passing
- [ ] No spike in error logs
- [ ] Database queries performing normally
- [ ] Redis cache hit rate normal
- [ ] No alerts triggered

If any issues detected, proceed to [Rollback Procedures](#rollback-procedures).

---

## Rollback Procedures

### When to Rollback

Initiate rollback immediately if:
- Error rate exceeds 1%
- Critical functionality broken
- Database corruption detected
- Security incident detected
- Health checks failing
- SLO breach imminent

### Rollback Methods

#### Method 1: ArgoCD UI Rollback (Recommended)

1. Login to ArgoCD UI
2. Navigate to application (staging or production)
3. Click "History" tab
4. Identify last known good deployment
5. Click on the deployment
6. Click "Rollback" button
7. Confirm rollback
8. Monitor deployment progress

**Time to rollback**: ~2-3 minutes

#### Method 2: ArgoCD CLI Rollback

```bash
# View deployment history
argocd app history ai-part-designer-production

# Rollback to specific revision
argocd app rollback ai-part-designer-production <revision-id>

# Rollback to previous revision
argocd app rollback ai-part-designer-production

# Monitor rollback
watch argocd app get ai-part-designer-production
```

**Time to rollback**: ~2-3 minutes

#### Method 3: Git Revert (Slower but Auditable)

```bash
# Find the commit that caused the issue
git log --oneline k8s/overlays/production/kustomization.yaml

# Revert the problematic commit
git revert <commit-hash>

# Push revert commit
git push origin main

# Manually sync in ArgoCD
argocd app sync ai-part-designer-production --prune
```

**Time to rollback**: ~5-10 minutes

#### Method 4: Emergency Kubectl Rollback (Last Resort)

```bash
# Rollback deployment directly with kubectl
kubectl rollout undo deployment/backend-prod -n ai-part-designer-prod
kubectl rollout undo deployment/frontend-prod -n ai-part-designer-prod

# Monitor rollout
kubectl rollout status deployment/backend-prod -n ai-part-designer-prod

# ⚠️ WARNING: This creates drift between Git and cluster
# Sync ArgoCD afterward to restore GitOps state
```

**Time to rollback**: ~1-2 minutes (but creates drift)

### Post-Rollback Actions

1. Verify application health restored
2. Update incident timeline
3. Notify stakeholders
4. Create postmortem issue
5. Analyze root cause
6. Update deployment procedures if needed

---

## Monitoring Deployments

### ArgoCD Dashboard

**URL**: https://argocd.yourdomain.com

**Key Metrics**:
- Sync Status: Shows if application is in sync with Git
- Health Status: Shows if resources are healthy
- Last Sync: Timestamp of last successful sync
- Sync History: Timeline of all deployments

### Application Health Checks

```bash
# Check application health in ArgoCD
argocd app get ai-part-designer-production

# Check Kubernetes resource health
kubectl get all -n ai-part-designer-prod

# Check pod health
kubectl describe pod <pod-name> -n ai-part-designer-prod
```

### Logs and Metrics

```bash
# Application logs
kubectl logs -n ai-part-designer-prod deployment/backend-prod --tail=100

# ArgoCD controller logs
kubectl logs -n argocd deployment/argocd-application-controller --tail=100

# Check Prometheus metrics
curl http://argocd-metrics.argocd.svc:8082/metrics
```

### Sync Status

| Status | Description | Action |
|--------|-------------|--------|
| Synced | Git matches cluster | None required |
| OutOfSync | Git differs from cluster | Sync manually (production) or wait (staging auto-syncs) |
| Unknown | Cannot determine status | Check ArgoCD logs |
| Progressing | Sync in progress | Monitor progress |

### Health Status

| Status | Description | Action |
|--------|-------------|--------|
| Healthy | All resources healthy | None required |
| Progressing | Deployment in progress | Monitor progress |
| Degraded | Some resources unhealthy | Investigate failing resources |
| Suspended | Resource suspended | Resume resource |
| Missing | Resource not found | Check if resource should exist |

---

## Troubleshooting

### Application OutOfSync

**Symptom**: ArgoCD shows "OutOfSync" status

**Diagnosis**:
```bash
# Check differences
argocd app diff ai-part-designer-production

# Check Git vs cluster state
kubectl get all -n ai-part-designer-prod
```

**Resolution**:
```bash
# Sync application
argocd app sync ai-part-designer-production

# If manual changes were made to cluster, revert them
# Or commit them to Git if they should be kept
```

### Application Unhealthy

**Symptom**: ArgoCD shows "Degraded" or "Unhealthy" status

**Diagnosis**:
```bash
# Check pod status
kubectl get pods -n ai-part-designer-prod

# Check failed pods
kubectl describe pod <failing-pod> -n ai-part-designer-prod

# Check logs
kubectl logs <failing-pod> -n ai-part-designer-prod --tail=100
```

**Common Causes**:
- Image pull errors (wrong tag or credentials)
- Resource limits too low (OOMKilled)
- Configuration errors (invalid env vars)
- Dependency failures (database, Redis)

**Resolution**:
1. Fix underlying issue (update image tag, increase limits, fix config)
2. Commit fix to Git
3. Sync application

### Sync Failing

**Symptom**: ArgoCD sync operation fails

**Diagnosis**:
```bash
# View sync status
argocd app get ai-part-designer-production

# Check ArgoCD logs
kubectl logs -n argocd deployment/argocd-application-controller --tail=100

# Check repo server logs
kubectl logs -n argocd deployment/argocd-repo-server --tail=100
```

**Common Causes**:
- Invalid Kustomize configuration
- Missing secrets or configmaps
- RBAC permission issues
- Resource quota exceeded

**Resolution**:
```bash
# Validate Kustomize locally
kustomize build k8s/overlays/production

# Fix issues in Git
# Commit and push

# Retry sync
argocd app sync ai-part-designer-production --retry-limit 3
```

### Cannot Access ArgoCD UI

**Symptom**: Cannot access ArgoCD dashboard

**Diagnosis**:
```bash
# Check ArgoCD server status
kubectl get pods -n argocd

# Check ingress
kubectl get ingress -n argocd

# Check service
kubectl get svc argocd-server -n argocd
```

**Resolution**:
```bash
# Port forward as temporary workaround
kubectl port-forward svc/argocd-server -n argocd 8080:443

# Access at https://localhost:8080
```

### Forgot ArgoCD Admin Password

**Resolution**:
```bash
# Get initial admin password
kubectl -n argocd get secret argocd-initial-admin-secret \
  -o jsonpath="{.data.password}" | base64 -d

# Reset admin password
argocd account update-password --account admin
```

---

## Emergency Procedures

### Complete Service Outage

**Immediate Actions**:
1. Notify on-call team and stakeholders
2. Check ArgoCD and Kubernetes cluster health
3. Review recent deployments in ArgoCD history
4. Initiate rollback to last known good state
5. Monitor recovery

**Commands**:
```bash
# Check cluster health
kubectl get nodes
kubectl get pods --all-namespaces

# Check ArgoCD status
kubectl get pods -n argocd

# Emergency rollback
argocd app rollback ai-part-designer-production
```

### Database Migration Failure

**Immediate Actions**:
1. Check migration logs
2. Determine if rollback is safe
3. If safe, rollback application AND database
4. If unsafe, fix forward

**Commands**:
```bash
# Check migration status
kubectl exec -n ai-part-designer-prod deployment/backend-prod -- \
  python -m alembic current

# View migration logs
kubectl logs -n ai-part-designer-prod deployment/backend-prod --tail=200 | grep migration
```

### Configuration Drift Detected

**Symptom**: Manual changes made to cluster outside of Git

**Resolution**:
```bash
# Option 1: Revert manual changes (restore GitOps)
argocd app sync ai-part-designer-production --prune

# Option 2: Capture manual changes to Git
kubectl get deployment backend-prod -n ai-part-designer-prod -o yaml > /tmp/backup.yaml
# Review changes and commit desired ones to Git
```

### ArgoCD Not Syncing

**Diagnosis**:
```bash
# Check ArgoCD components
kubectl get pods -n argocd

# Check application controller logs
kubectl logs -n argocd deployment/argocd-application-controller --tail=100

# Check repo server
kubectl logs -n argocd deployment/argocd-repo-server --tail=100
```

**Resolution**:
```bash
# Restart ArgoCD components
kubectl rollout restart deployment/argocd-application-controller -n argocd
kubectl rollout restart deployment/argocd-repo-server -n argocd
kubectl rollout restart deployment/argocd-server -n argocd

# Hard refresh application
argocd app get ai-part-designer-production --hard-refresh
```

---

## Support and Escalation

### Escalation Path

1. **Level 1**: On-call engineer
2. **Level 2**: DevOps team lead
3. **Level 3**: Platform engineering team
4. **Level 4**: CTO

### Emergency Contacts

- On-call hotline: [Configure in PagerDuty]
- Slack channel: #production-incidents
- Email: devops@yourdomain.com

### Incident Response

1. Create incident in incident management system
2. Start incident bridge/war room
3. Assign incident commander
4. Update status page
5. Communicate with stakeholders
6. Follow runbook procedures
7. Document timeline
8. Create postmortem

---

## Additional Resources

- [ArgoCD Documentation](https://argo-cd.readthedocs.io/)
- [Kubernetes Documentation](https://kubernetes.io/docs/)
- [Kustomize Documentation](https://kubectl.docs.kubernetes.io/references/kustomize/)
- [GitOps Principles](https://www.gitops.tech/)
- [Deployment.md](./deployment.md) - General deployment guide
- [Monitoring-Alerting.md](./monitoring-alerting.md) - Monitoring setup

---

**Last Updated**: 2024-02-07
**Maintained By**: DevOps Team
**Review Frequency**: Quarterly
