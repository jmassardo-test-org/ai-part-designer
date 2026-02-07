# Rollback Runbook

**Purpose**: Step-by-step guide for rolling back deployments in production or staging

**When to Use**: When a deployment causes issues that require immediate reverting to a previous stable version

**Expected Time**: 2-5 minutes for rollback, 10-15 minutes for verification

---

## Decision Tree

```
┌─────────────────────────────────────────────────┐
│ Is the issue affecting production?              │
└─────────────┬───────────────────────────────────┘
              │
              ├── NO (Staging only)
              │   └─> Wait for next deployment or
              │       use Method 1 (ArgoCD UI) if urgent
              │
              └── YES (Production affected)
                  └─> Proceed to Severity Assessment
                      │
                      ├── SEV1 (Complete outage)
                      │   └─> Use Method 4 (Emergency kubectl)
                      │       Then restore GitOps with Method 2
                      │
                      ├── SEV2 (Partial outage)
                      │   └─> Use Method 1 (ArgoCD UI) or
                      │       Method 2 (ArgoCD CLI)
                      │
                      └── SEV3 (Degraded performance)
                          └─> Use Method 1 (ArgoCD UI)
                              Coordinate with team
```

---

## Prerequisites

Before starting rollback, ensure you have:

- [ ] ArgoCD access (UI or CLI login)
- [ ] kubectl access to production cluster
- [ ] Incident ticket created
- [ ] Team notified in Slack #production-incidents
- [ ] Monitoring dashboards open (Grafana, ArgoCD)
- [ ] Approval from incident commander (for production)

---

## Method 1: ArgoCD UI Rollback (Recommended)

**Best For**: Standard rollbacks, good audit trail, easy to execute

**Time**: ~2-3 minutes

### Steps

1. **Login to ArgoCD UI**
   ```
   URL: https://argocd.yourdomain.com
   Username: admin
   Password: [Get from password manager]
   ```

2. **Navigate to Application**
   - Click on `ai-part-designer-production` or `ai-part-designer-staging`
   - Verify you're looking at the correct environment (check namespace)

3. **Open History**
   - Click the "History and Rollback" tab
   - Review the list of previous deployments
   - Each entry shows:
     - Revision number
     - Git commit SHA
     - Timestamp
     - Sync status

4. **Identify Target Revision**
   - Look for the last deployment marked "Succeeded" before the issue started
   - Note the revision number (e.g., `revision 42`)
   - Verify the timestamp matches your expectations

5. **Preview Rollback**
   - Click on the target revision
   - Review the "App Diff" to see what will change
   - Confirm resources match expected state

6. **Execute Rollback**
   - Click "Rollback" button
   - Confirm the action in the popup dialog
   - Wait for sync to complete (status changes to "Synced")

7. **Monitor Progress**
   - Watch the sync status in ArgoCD UI
   - Status should progress: Progressing → Synced
   - Health should show: Progressing → Healthy

8. **Verify in Kubernetes**
   ```bash
   kubectl get pods -n ai-part-designer-prod -w
   ```
   - Watch pods terminate and restart with old version
   - Wait for all pods to be "Running" and "Ready"

---

## Method 2: ArgoCD CLI Rollback

**Best For**: Automation, scripting, when UI is unavailable

**Time**: ~2-3 minutes

### Steps

1. **Login to ArgoCD CLI**
   ```bash
   argocd login argocd.yourdomain.com --username admin
   # Enter password when prompted
   ```

2. **List Recent Revisions**
   ```bash
   argocd app history ai-part-designer-production
   ```
   
   Output example:
   ```
   ID  DATE                           REVISION
   10  2024-02-07 15:30:00 +0000 UTC  abc123 (HEAD -> main)
   9   2024-02-07 14:00:00 +0000 UTC  def456
   8   2024-02-07 12:00:00 +0000 UTC  ghi789  ← Last known good
   ```

3. **Identify Target Revision**
   - Choose the revision ID before the problematic deployment
   - In example above, revision `8` is target

4. **Preview Rollback (Optional)**
   ```bash
   # Show what will change
   argocd app diff ai-part-designer-production
   ```

5. **Execute Rollback**
   ```bash
   # Rollback to specific revision
   argocd app rollback ai-part-designer-production 8
   
   # OR rollback to immediately previous revision
   argocd app rollback ai-part-designer-production
   ```

6. **Monitor Progress**
   ```bash
   # Watch sync status
   watch argocd app get ai-part-designer-production
   
   # Watch pods
   kubectl get pods -n ai-part-designer-prod -w
   ```

7. **Wait for Sync Completion**
   - Sync status should be "Synced"
   - Health status should be "Healthy"
   - All pods should be "Running"

---

## Method 3: Git Revert Rollback

**Best For**: Auditable rollbacks, when you want explicit Git history

**Time**: ~5-10 minutes

### Steps

1. **Clone Repository**
   ```bash
   git clone https://github.com/jmassardo/ai-part-designer.git
   cd ai-part-designer
   git checkout main
   ```

2. **Identify Problematic Commit**
   ```bash
   # Show recent commits to kustomization
   git log --oneline k8s/overlays/production/kustomization.yaml
   ```
   
   Output example:
   ```
   abc123 chore(production): update image tags to sha-xyz789
   def456 chore(production): update image tags to sha-abc456  ← Rollback to this
   ghi789 feat: add new feature
   ```

3. **Revert the Commit**
   ```bash
   # Revert the bad commit (creates new commit)
   git revert abc123
   
   # Review the revert
   git show HEAD
   ```

4. **Push Revert**
   ```bash
   # Push to main branch
   git push origin main
   ```

5. **Wait for ArgoCD Detection**
   - ArgoCD polls Git every 3 minutes (default)
   - Or force refresh:
     ```bash
     argocd app get ai-part-designer-production --refresh
     ```

6. **Sync Application**
   ```bash
   # Manual sync (production requires this)
   argocd app sync ai-part-designer-production --prune
   ```

7. **Monitor Deployment**
   ```bash
   kubectl get pods -n ai-part-designer-prod -w
   ```

---

## Method 4: Emergency kubectl Rollback (Last Resort)

**Best For**: SEV1 incidents, when ArgoCD is unavailable or too slow

**Time**: ~1-2 minutes

**⚠️ WARNING**: This creates drift between Git and cluster! Must sync ArgoCD afterward.

### Steps

1. **Rollback Deployments**
   ```bash
   # Rollback backend
   kubectl rollout undo deployment/backend-prod -n ai-part-designer-prod
   
   # Rollback frontend
   kubectl rollout undo deployment/frontend-prod -n ai-part-designer-prod
   
   # Rollback worker
   kubectl rollout undo deployment/celery-worker-prod -n ai-part-designer-prod
   
   # Rollback beat (if applicable)
   kubectl rollout undo deployment/celery-beat-prod -n ai-part-designer-prod
   ```

2. **Monitor Rollout**
   ```bash
   # Check status
   kubectl rollout status deployment/backend-prod -n ai-part-designer-prod
   kubectl rollout status deployment/frontend-prod -n ai-part-designer-prod
   
   # Watch pods
   kubectl get pods -n ai-part-designer-prod -w
   ```

3. **Verify Rollback**
   ```bash
   # Check running image versions
   kubectl get deployment backend-prod -n ai-part-designer-prod -o jsonpath='{.spec.template.spec.containers[0].image}'
   ```

4. **Restore GitOps State**
   ```bash
   # Get current running image tag
   CURRENT_TAG=$(kubectl get deployment backend-prod -n ai-part-designer-prod -o jsonpath='{.spec.template.spec.containers[0].image}' | cut -d: -f2)
   
   # Update Git to match cluster
   cd ai-part-designer
   cd k8s/overlays/production
   kustomize edit set image \
     ai-part-designer-backend=ghcr.io/jmassardo/ai-part-designer-production:${CURRENT_TAG}
   kustomize edit set image \
     ai-part-designer-frontend=ghcr.io/jmassardo/ai-part-designer-frontend:${CURRENT_TAG}
   
   git add kustomization.yaml
   git commit -m "chore(production): restore GitOps state after emergency rollback to ${CURRENT_TAG}"
   git push origin main
   ```

5. **Sync ArgoCD**
   ```bash
   # Sync to restore GitOps alignment
   argocd app sync ai-part-designer-production
   ```

---

## Verification Steps

After rollback (regardless of method), verify:

### 1. Pod Status
```bash
# All pods should be Running and Ready
kubectl get pods -n ai-part-designer-prod

# Check pod ages (should be recent)
kubectl get pods -n ai-part-designer-prod -o wide
```

Expected output:
```
NAME                            READY   STATUS    RESTARTS   AGE
backend-prod-xxx                2/2     Running   0          2m
frontend-prod-xxx               1/1     Running   0          2m
celery-worker-prod-xxx          1/1     Running   0          2m
```

### 2. Image Versions
```bash
# Verify correct image tags
kubectl get deployment backend-prod -n ai-part-designer-prod \
  -o jsonpath='{.spec.template.spec.containers[0].image}'

kubectl get deployment frontend-prod -n ai-part-designer-prod \
  -o jsonpath='{.spec.template.spec.containers[0].image}'
```

### 3. Health Checks
```bash
# Port forward to backend
kubectl port-forward -n ai-part-designer-prod svc/backend-service 8000:8000 &

# Test health endpoint
curl http://localhost:8000/health

# Expected: {"status": "healthy", "version": "..."}

# Kill port forward
kill %1
```

### 4. Application Functionality
```bash
# Test critical endpoints
curl https://api.yourdomain.com/health
curl https://api.yourdomain.com/version

# Test UI
# Open https://yourdomain.com in browser
# Verify main functionality works
```

### 5. Logs Check
```bash
# Check for errors in logs
kubectl logs -n ai-part-designer-prod deployment/backend-prod --tail=50 | grep -i error

# Should see minimal or no errors
```

### 6. Metrics Check
- Open Grafana dashboard
- Verify metrics:
  - Error rate < 0.1%
  - Response time p95 < 200ms
  - Request rate normal
  - Database connections healthy

### 7. ArgoCD Status
```bash
argocd app get ai-part-designer-production
```

Expected:
- Sync Status: Synced
- Health Status: Healthy

---

## Post-Rollback Actions

### Immediate (Within 5 minutes)

1. **Update Incident Timeline**
   - Document rollback time
   - Note rollback method used
   - Record verification results

2. **Notify Stakeholders**
   - Post in #production-incidents Slack channel:
     ```
     ✅ Rollback completed successfully at [TIME]
     - Method: [ArgoCD UI/CLI/Git/kubectl]
     - Previous version: [SHA/TAG]
     - Rolled back to: [SHA/TAG]
     - All health checks passing
     - Continuing to monitor
     ```

3. **Continue Monitoring**
   - Watch for 30 minutes
   - Monitor error rates
   - Check logs periodically
   - Verify metrics stable

### Short Term (Within 1 hour)

4. **Incident Documentation**
   - Update incident ticket with details
   - Include root cause (if known)
   - Document rollback steps taken
   - Note any issues during rollback

5. **Team Notification**
   - Notify development team
   - Explain what was rolled back and why
   - Share timeline of events

### Long Term (Within 24 hours)

6. **Root Cause Analysis**
   - Investigate what caused the issue
   - Review failed deployment logs
   - Check configuration changes
   - Identify contributing factors

7. **Create Postmortem**
   - Use incident postmortem template
   - Timeline of events
   - Root cause
   - Impact assessment
   - Action items to prevent recurrence

8. **Update Procedures**
   - If rollback process had issues, update runbook
   - Add any new learnings
   - Update deployment checklist if needed

---

## Common Issues During Rollback

### Issue: "Application is already at target revision"

**Cause**: Trying to rollback to current revision

**Solution**:
```bash
# Check history to find correct target revision
argocd app history ai-part-designer-production

# Specify exact revision number
argocd app rollback ai-part-designer-production <older-revision-id>
```

### Issue: Pods stuck in "Terminating"

**Cause**: Graceful shutdown timeout or finalizers

**Solution**:
```bash
# Check pod status
kubectl describe pod <pod-name> -n ai-part-designer-prod

# Force delete if stuck (use cautiously)
kubectl delete pod <pod-name> -n ai-part-designer-prod --grace-period=0 --force
```

### Issue: "Health check failed" after rollback

**Cause**: Database migration incompatibility or dependency issue

**Solution**:
1. Check if database migration needs rollback
2. Verify external dependencies (Redis, S3, etc.)
3. Check logs for specific errors
4. May need to rollback database separately

### Issue: "Sync operation failed"

**Cause**: Invalid Kustomize config or missing resources

**Solution**:
```bash
# Check ArgoCD logs
kubectl logs -n argocd deployment/argocd-application-controller --tail=100

# Validate Kustomize locally
git checkout <target-commit>
kustomize build k8s/overlays/production

# Fix any issues and commit
```

---

## Rollback Checklist

Use this checklist during rollback:

- [ ] Incident ticket created
- [ ] Team notified in Slack
- [ ] Monitoring dashboards open
- [ ] ArgoCD access verified
- [ ] Target revision identified
- [ ] Rollback executed
- [ ] Pods restarted successfully
- [ ] Health checks passing
- [ ] Metrics verified normal
- [ ] Logs checked for errors
- [ ] GitOps state restored (if kubectl method)
- [ ] Incident timeline updated
- [ ] Stakeholders notified
- [ ] Monitoring continued for 30 min
- [ ] Postmortem scheduled

---

## Escalation

If rollback fails or issues persist:

1. **Page on-call engineer**: Use PagerDuty
2. **Escalate to DevOps lead**: Slack @devops-lead
3. **Start incident bridge**: Use incident.io or Zoom
4. **Notify CTO**: For SEV1 incidents only

---

## Additional Resources

- [ArgoCD Operations Guide](./argocd-operations.md)
- [Deployment Guide](./deployment.md)
- [Incident Response Procedures](./incident-response.md)
- [ArgoCD Documentation](https://argo-cd.readthedocs.io/en/stable/user-guide/commands/argocd_app_rollback/)

---

**Last Updated**: 2024-02-07
**Maintained By**: DevOps Team
**Review After**: Every production incident involving rollback
