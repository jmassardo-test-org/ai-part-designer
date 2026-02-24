# Disaster Recovery Runbook

## AssemblematicAI Part Designer

**Version:** 1.0
**Created:** 2026-02-24
**Owner:** Platform Operations Team
**Classification:** Internal — Do Not Distribute
**Review Cadence:** Quarterly (next review: 2026-05-24)

---

## Table of Contents

1. [Overview](#1-overview)
2. [Prerequisites](#2-prerequisites)
3. [Database Recovery](#3-database-recovery)
4. [Object Storage Recovery](#4-object-storage-recovery)
5. [Application Recovery](#5-application-recovery)
6. [Ingress & TLS Recovery](#6-ingress--tls-recovery)
7. [Secrets Recovery](#7-secrets-recovery)
8. [Full Disaster Recovery](#8-full-disaster-recovery)
9. [Post-Recovery Verification](#9-post-recovery-verification)
10. [Escalation Matrix](#10-escalation-matrix)
11. [Communication Templates](#11-communication-templates)
12. [Quarterly DR Test Plan](#12-quarterly-dr-test-plan)

---

## 1. Overview

### Purpose

This runbook consolidates all disaster recovery procedures for the AI Part Designer platform into a single operational document. It is designed to be used by on-call engineers during active incidents.

> **Consolidated from:** Fragments previously spread across
> [data-engineering.md](../architecture/data-engineering.md#7-backup--recovery),
> [INGRESS_RUNBOOK.md](../../helm/INGRESS_RUNBOOK.md#disaster-recovery),
> [secrets-management.md](./secrets-management.md#disaster-recovery), and
> [STORAGE_IMPLEMENTATION.md](../../helm/STORAGE_IMPLEMENTATION.md#backup-integration).

### Scope

| Component | Covered |
|-----------|---------|
| PostgreSQL (CloudNativePG) | Yes |
| Redis | Yes |
| MinIO / S3 object storage | Yes |
| Application pods (API, workers) | Yes |
| Ingress / TLS certificates | Yes |
| Secrets (OpenBao) | Yes |
| Observability stack | Out of scope — see [observability docs](../../observability/README.md) |

### RTO / RPO Targets

| Scenario | RTO | RPO | Backup Method |
|----------|-----|-----|---------------|
| Database corruption | 2 hours | 24 hours | pg_dump daily + WAL archiving |
| Accidental deletion | 1 hour | 15 minutes | Object versioning + WAL PITR |
| Full disaster (all systems) | 4 hours | 24 hours | Full restore sequence below |
| Ingress controller failure | 15 minutes | 0 (stateless) | Helm reinstall |
| Certificate expiration | 30 minutes | 0 | cert-manager recreation |
| Secrets store failure | 30 minutes | 0 | Raft snapshot restore |

### Backup Inventory

| Data Store | Method | Schedule | Retention | Location |
|------------|--------|----------|-----------|----------|
| PostgreSQL | Barman object-store (CloudNativePG) | Daily 2:00 AM UTC | 30 days | `s3://backups/postgresql` on MinIO |
| PostgreSQL | `pg_dump` via Celery task | Daily via `backup_database` | 30 days | MinIO `temp` bucket (`backups/` prefix) |
| PostgreSQL | Full backup via BackupService | Weekly (Sunday 3 AM) via `weekly_full_backup` | 30 days | MinIO |
| PostgreSQL | WAL archiving | Continuous | 7 days | MinIO |
| Redis | RDB snapshot | Hourly (`save 900 1`, `save 300 10`, `save 60 10000`) | 24 hours | PVC at `/data/dump.rdb` |
| Object Storage | Bucket versioning (designs, uploads, exports) | Continuous | Per-version | MinIO versioned buckets |

---

## 2. Prerequisites

### Required Access

| Access | Purpose | How to Obtain |
|--------|---------|---------------|
| `kubectl` with cluster-admin | Cluster operations | Kubeconfig from platform team |
| Helm 3.8+ | Chart deployments | `brew install helm` |
| `openbao` CLI | Secrets operations | See [secrets-management.md](./secrets-management.md#initial-setup) |
| MinIO client (`mc`) | Storage operations | `brew install minio/stable/mc` |
| PagerDuty access | Incident management | Request from platform lead |

### Required Credentials

> **⚠ NEVER hardcode credentials.** All secrets are managed via OpenBao.
> See [secrets-management.md](./secrets-management.md) for retrieval procedures.

- Kubernetes cluster credentials (kubeconfig)
- OpenBao unseal keys (stored in 3+ secure locations — see secrets-management.md)
- PostgreSQL superuser credentials (via OpenBao or `postgres-superuser` K8s secret)
- MinIO/S3 access keys (via OpenBao or `postgres-backup-secret` K8s secret)

### Key Namespaces

| Namespace | Components |
|-----------|------------|
| `ai-part-designer-prod` | API, workers, frontend, PostgreSQL, Redis, MinIO |
| `cert-manager` | cert-manager controller |
| `openbao` | OpenBao secrets vault |
| `cnpg-system` | CloudNativePG operator |

---

## 3. Database Recovery

### 3.1 CloudNativePG Backup Restore (Barman)

CloudNativePG backs up to MinIO via Barman object store. The backup schedule is defined in
[`k8s/base/cloudnative-pg/scheduled-backup.yaml`](../../k8s/base/cloudnative-pg/scheduled-backup.yaml):
daily at 2:00 AM UTC, 30-day retention.

#### List Available Backups

```bash
# List CloudNativePG backups
kubectl get backup -n ai-part-designer-prod

# Check scheduled backup status
kubectl get scheduledbackup -n ai-part-designer-prod
```

#### Trigger Manual Backup (Before Recovery)

```bash
kubectl apply -f - <<EOF
apiVersion: postgresql.cnpg.io/v1
kind: Backup
metadata:
  name: postgres-manual-$(date +%Y%m%d-%H%M%S)
  namespace: ai-part-designer-prod
spec:
  cluster:
    name: postgres-cluster
  method: barmanObjectStore
EOF

# Monitor
kubectl get backup -n ai-part-designer-prod -w
```

#### Restore Cluster from Barman Backup

This creates a **new** cluster from backup, then switches traffic.

```bash
# 1. Create restore cluster
kubectl apply -f - <<EOF
apiVersion: postgresql.cnpg.io/v1
kind: Cluster
metadata:
  name: postgres-cluster-restore
  namespace: ai-part-designer-prod
spec:
  instances: 3
  bootstrap:
    recovery:
      source: postgres-cluster
  externalClusters:
    - name: postgres-cluster
      barmanObjectStore:
        destinationPath: s3://backups/postgresql
        endpointURL: http://minio:9000
        s3Credentials:
          accessKeyId:
            name: postgres-backup-secret
            key: ACCESS_KEY_ID
          secretAccessKey:
            name: postgres-backup-secret
            key: ACCESS_SECRET_KEY
        wal:
          compression: gzip
          maxParallel: 2
  storage:
    size: 100Gi
EOF

# 2. Wait until restore cluster is healthy
kubectl get cluster -n ai-part-designer-prod postgres-cluster-restore -w
# Wait for "Cluster in healthy state"

# 3. Update services to point to restored cluster
kubectl patch svc postgres-service -n ai-part-designer-prod \
  --type=json -p='[{"op": "replace", "path": "/spec/selector/cnpg.io~1cluster", "value": "postgres-cluster-restore"}]'

# 4. Rolling restart of application pods
kubectl rollout restart deployment/backend -n ai-part-designer-prod
kubectl rollout restart deployment/celery-worker -n ai-part-designer-prod

# 5. Delete old broken cluster once confirmed
kubectl delete cluster postgres-cluster -n ai-part-designer-prod
```

#### Point-in-Time Recovery (PITR)

Use WAL archiving to restore to a specific timestamp (requires WAL logs within 7 days).

```bash
# Restore to a specific point in time
kubectl apply -f - <<EOF
apiVersion: postgresql.cnpg.io/v1
kind: Cluster
metadata:
  name: postgres-cluster-pitr
  namespace: ai-part-designer-prod
spec:
  instances: 3
  bootstrap:
    recovery:
      source: postgres-cluster
      recoveryTarget:
        targetTime: "2026-02-24T10:30:00Z"   # <-- set to target timestamp
  externalClusters:
    - name: postgres-cluster
      barmanObjectStore:
        destinationPath: s3://backups/postgresql
        endpointURL: http://minio:9000
        s3Credentials:
          accessKeyId:
            name: postgres-backup-secret
            key: ACCESS_KEY_ID
          secretAccessKey:
            name: postgres-backup-secret
            key: ACCESS_SECRET_KEY
        wal:
          compression: gzip
  storage:
    size: 100Gi
EOF

# Monitor restore progress
kubectl get cluster -n ai-part-designer-prod postgres-cluster-pitr -w
```

### 3.2 pg_dump Restore (BackupService / Celery)

The Celery task `app.worker.tasks.maintenance.backup_database` creates daily `pg_dump` backups,
compressed and uploaded to MinIO. The `DatabaseBackup` class in
[`backend/app/core/backup.py`](../../backend/app/core/backup.py) handles the operations.

#### List Available pg_dump Backups

```bash
# From a backend pod
kubectl exec -n ai-part-designer-prod deployment/backend -- \
  python -c "
import asyncio
from app.core.backup import db_backup
backups = asyncio.run(db_backup.list_backups())
for b in backups[:10]:
    print(f\"{b['key']}  {b['size']}  {b['last_modified']}\")
"
```

Or via MinIO client:

```bash
# Configure mc if not already done
mc alias set minio http://minio:9000 <ACCESS_KEY> <SECRET_KEY>

# List backup files
mc ls minio/ai-part-designer-production-temp/backups/ --recursive
```

#### Restore from pg_dump

```bash
# 1. Download backup from MinIO to a backend pod
kubectl exec -n ai-part-designer-prod deployment/backend -- \
  python -c "
import asyncio
from app.core.backup import db_backup
asyncio.run(db_backup.restore_backup(
    '/tmp/backups/backup_full_20260224_040000.sql.gz',
    drop_existing=False,
))
"
```

Or use `make` locally (with port-forward to DB and MinIO):

```bash
make backup    # creates a new backup first (safety net)
# Then restore:
cd backend && poetry run python -c "
import asyncio
from app.core.backup import db_backup
asyncio.run(db_backup.restore_backup('/tmp/backups/<backup_file>.sql.gz', drop_existing=True))
"
```

### 3.3 Verify Backup Integrity

The `app.worker.tasks.maintenance.verify_backups` Celery task runs weekly and checks:
- Backup files exist and are readable
- Checksums match recorded values
- Backups can be decompressed
- Sample data can be read

To trigger manually:

```bash
kubectl exec -n ai-part-designer-prod deployment/celery-worker -- \
  python -c "
from app.worker.tasks.maintenance import verify_backups
result = verify_backups()
print(result)
"
```

---

## 4. Object Storage Recovery

### 4.1 MinIO Restore from PVC

MinIO data lives on a PVC (`data-minio-0`). Production uses `Retain` reclaim policy to prevent accidental data loss.

```bash
# Check MinIO PVC status
kubectl get pvc -n ai-part-designer-prod -l app=minio

# If MinIO pod crashed but PVC is intact, the pod will auto-recover
kubectl get pods -n ai-part-designer-prod -l app=minio

# Force restart MinIO
kubectl delete pod -n ai-part-designer-prod -l app=minio
kubectl wait --for=condition=ready pod -n ai-part-designer-prod -l app=minio --timeout=5m
```

### 4.2 Versioning Rollback (Accidental Deletion)

Buckets `designs`, `uploads`, and `exports` have versioning enabled (configured in
[`backend/app/core/storage_init.py`](../../backend/app/core/storage_init.py)).

```bash
# List object versions
mc ls --versions minio/ai-part-designer-production-designs/<path-to-object>

# Restore a specific version
mc cp --version-id <VERSION_ID> \
  minio/ai-part-designer-production-designs/<path> \
  minio/ai-part-designer-production-designs/<path>

# Undo a delete (restore delete marker)
mc rm --version-id <DELETE_MARKER_ID> \
  minio/ai-part-designer-production-designs/<path>
```

### 4.3 Re-initialize Storage Buckets

If buckets are missing or misconfigured, run the storage initialization:

```bash
# From a backend pod
kubectl exec -n ai-part-designer-prod deployment/backend -- \
  python -c "
import asyncio
from app.core.storage_init import initialize_storage
result = asyncio.run(initialize_storage())
print(result)
"
```

This is idempotent and will:
1. Create any missing buckets
2. Enable versioning on `designs`, `uploads`, `exports`
3. Configure lifecycle policies (7-day expiry on `temp`, 180-day glacier transition on `designs`)

### 4.4 Check Storage Health

The `app.worker.tasks.maintenance.check_storage_health` Celery task verifies bucket accessibility and versioning status.

```bash
# Trigger manually
kubectl exec -n ai-part-designer-prod deployment/celery-worker -- \
  python -c "
from app.worker.tasks.maintenance import check_storage_health
result = check_storage_health()
print(result)
"
```

---

## 5. Application Recovery

### 5.1 Pod Restart

```bash
# Restart API pods
kubectl rollout restart deployment/backend -n ai-part-designer-prod
kubectl rollout status deployment/backend -n ai-part-designer-prod --timeout=5m

# Restart Celery workers
kubectl rollout restart deployment/celery-worker -n ai-part-designer-prod
kubectl rollout status deployment/celery-worker -n ai-part-designer-prod --timeout=5m

# Restart Celery beat
kubectl rollout restart deployment/celery-beat -n ai-part-designer-prod

# Restart frontend
kubectl rollout restart deployment/frontend -n ai-part-designer-prod
```

### 5.2 Helm Release Rollback

```bash
# View release history
helm history ai-part-designer -n ai-part-designer-prod

# Rollback to previous revision
helm rollback ai-part-designer -n ai-part-designer-prod

# Rollback to specific revision
helm rollback ai-part-designer <REVISION> -n ai-part-designer-prod

# Verify rollback
helm status ai-part-designer -n ai-part-designer-prod
kubectl get pods -n ai-part-designer-prod
```

### 5.3 Full Helm Redeploy

If rollback fails, redeploy from scratch:

```bash
# Update chart dependencies
cd helm/ai-part-designer && helm dependency update

# Redeploy production
helm upgrade --install ai-part-designer ./helm/ai-part-designer \
  --namespace ai-part-designer-prod \
  --values helm/ai-part-designer/values-production.yaml \
  --wait \
  --timeout 20m
```

See [Deployment Guide](../../helm/DEPLOYMENT_GUIDE.md) for full deployment scenarios.

### 5.4 Scaling

```bash
# Scale API pods
kubectl scale deployment/backend -n ai-part-designer-prod --replicas=5

# Scale workers
kubectl scale deployment/celery-worker -n ai-part-designer-prod --replicas=4

# Scale PostgreSQL replicas
kubectl patch cluster -n ai-part-designer-prod postgres-cluster \
  --type='json' -p='[{"op": "replace", "path": "/spec/instances", "value": 5}]'
```

---

## 6. Ingress & TLS Recovery

> **Full procedures:** [helm/INGRESS_RUNBOOK.md](../../helm/INGRESS_RUNBOOK.md)

### 6.1 Ingress Controller Failure

**RTO: 15 minutes | RPO: 0 (stateless)**

```bash
# 1. Verify failure
kubectl get pods -n ai-part-designer-prod -l app.kubernetes.io/name=ingress-nginx

# 2. Force reinstall via Helm
helm upgrade ai-part-designer ./helm/ai-part-designer \
  --namespace ai-part-designer-prod \
  --reuse-values \
  --force \
  --wait

# 3. Verify recovery
kubectl get svc -n ai-part-designer-prod -l app.kubernetes.io/name=ingress-nginx
curl -I https://app.assemblematic.ai

# 4. Verify DNS
dig app.assemblematic.ai +short
```

### 6.2 Certificate Expiration / Failure

**RTO: 30 minutes | RPO: 0**

```bash
# 1. Delete expired certificates (triggers recreation)
kubectl delete certificate --all -n ai-part-designer-prod

# 2. Verify DNS
dig app.assemblematic.ai +short
dig api.assemblematic.ai +short

# 3. Recreate via Kustomize overlay
kubectl apply -k k8s/overlays/production

# 4. Monitor recreation
kubectl get certificate -n ai-part-designer-prod -w
# Wait for READY=True (up to 5 minutes)

# 5. If Let's Encrypt rate limited, switch to staging issuer
kubectl patch ingress ai-part-designer-ingress -n ai-part-designer-prod \
  --type=json \
  -p='[{"op": "replace", "path": "/metadata/annotations/cert-manager.io~1cluster-issuer", "value": "letsencrypt-staging"}]'

# 6. Test HTTPS
curl -vI https://app.assemblematic.ai 2>&1 | grep "subject:\|issuer:\|expire"
```

---

## 7. Secrets Recovery

> **Full procedures:** [docs/operations/secrets-management.md](./secrets-management.md)

### 7.1 OpenBao Sealed After Restart

```bash
# Check seal status
kubectl exec -n openbao openbao-0 -- openbao status

# Unseal (requires 3 of 5 unseal keys)
for i in 1 2 3; do
  KEY=$(kubectl get secret openbao-unseal-keys -n openbao \
    -o jsonpath="{.data.key-$i}" | base64 -d)
  kubectl exec -n openbao openbao-0 -- openbao operator unseal "$KEY"
done

# Repeat for other pods (openbao-1, openbao-2)
```

### 7.2 Complete OpenBao Failure

```bash
# 1. Restore from Raft snapshot
kubectl exec -n openbao openbao-0 -- \
  openbao operator raft snapshot restore /path/to/snapshot.snap

# 2. Unseal all nodes (procedure above)

# 3. Verify secrets accessible
kubectl port-forward -n openbao svc/openbao 8200:8200 &
ROOT_TOKEN=$(kubectl get secret openbao-unseal-keys -n openbao \
  -o jsonpath='{.data.root-token}' | base64 -d)
openbao login "$ROOT_TOKEN"
openbao kv list secret/ai-part-designer/

# 4. Force sync ExternalSecrets
kubectl annotate externalsecret --all -n ai-part-designer-prod \
  force-sync="$(date +%s)" --overwrite

# 5. Rolling restart all services
kubectl rollout restart deployment/backend -n ai-part-designer-prod
kubectl rollout restart deployment/celery-worker -n ai-part-designer-prod
```

### 7.3 Compromised Secrets

```bash
# 1. Rotate the compromised secret in OpenBao
openbao kv put secret/ai-part-designer/<path> key="<new-value>"

# 2. Force sync to Kubernetes
kubectl annotate externalsecret <name> -n ai-part-designer-prod \
  force-sync="$(date +%s)" --overwrite

# 3. Rolling restart affected services
kubectl rollout restart deployment/<service> -n ai-part-designer-prod

# 4. Audit access logs
kubectl logs -n openbao openbao-0 | grep "<path>" > audit-investigation.log
```

See [secrets-management.md — Emergency Procedures](./secrets-management.md#emergency-procedures) for full details on compromised secrets and break-glass access.

---

## 8. Full Disaster Recovery

Use this section when **all systems** must be recovered from scratch. Follow steps in exact order.

**Target RTO: 4 hours | Target RPO: 24 hours**

### Step-by-Step Recovery Sequence

```
Step 1 → Infrastructure        (namespaces, storage classes)
Step 2 → Secrets               (OpenBao, K8s secrets)
Step 3 → Database              (CloudNativePG restore)
Step 4 → Object Storage        (MinIO PVC, bucket init)
Step 5 → Application           (Helm deploy)
Step 6 → Ingress & TLS         (certificates)
Step 7 → Background Workers    (Celery workers, beat)
Step 8 → Verification          (health checks)
```

---

#### Step 1: Infrastructure (15 min)

```bash
# Create namespaces
kubectl create namespace ai-part-designer-prod
kubectl create namespace openbao
kubectl create namespace cert-manager
kubectl create namespace cnpg-system

# Create production StorageClass (if not exists)
kubectl apply -f - <<EOF
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: fast-ssd
provisioner: <cluster-specific>
parameters:
  type: <high-iops-ssd-type>
reclaimPolicy: Retain
allowVolumeExpansion: true
volumeBindingMode: WaitForFirstConsumer
EOF
```

#### Step 2: Secrets (30 min)

```bash
# Install OpenBao
helm repo add openbao https://openbao.github.io/openbao-helm
helm install openbao openbao/openbao \
  --namespace openbao \
  --values k8s/base/openbao/openbao-helm-values.yaml \
  --wait --timeout 5m

# Restore from Raft snapshot (if available)
kubectl exec -n openbao openbao-0 -- \
  openbao operator raft snapshot restore /path/to/snapshot.snap

# OR re-initialize and re-populate secrets (see secrets-management.md)

# Unseal all nodes
# (see Section 7.1)

# Install External Secrets Operator
helm repo add external-secrets https://charts.external-secrets.io
helm install external-secrets external-secrets/external-secrets \
  --namespace external-secrets-system \
  --create-namespace

# Create K8s secrets required before Helm install
# (see helm/DEPLOYMENT_GUIDE.md § Create Required Secrets)
kubectl create secret generic backend-secrets \
  --namespace=ai-part-designer-prod \
  --from-literal=postgres-user=assemblematic_user \
  --from-literal=postgres-password="<from-openbao>" \
  --from-literal=anthropic-api-key="<from-openbao>" \
  --from-literal=secret-key="<from-openbao>" \
  --from-literal=access-key-id="<from-openbao>" \
  --from-literal=secret-access-key="<from-openbao>"
```

#### Step 3: Database (60 min)

```bash
# Install CloudNativePG operator
helm repo add cnpg https://cloudnative-pg.github.io/charts
helm install cnpg cnpg/cloudnative-pg \
  --namespace cnpg-system \
  --create-namespace

# Restore PostgreSQL from barman backup
# (see Section 3.1 — Restore Cluster from Barman Backup)

# If no barman backup available, restore from pg_dump
# (see Section 3.2)

# Verify database connectivity
kubectl exec -n ai-part-designer-prod postgres-cluster-1 -- \
  psql -U postgres -c "SELECT version();"
```

#### Step 4: Object Storage (15 min)

```bash
# MinIO will be deployed as part of Helm in Step 5
# After Helm deploy, re-initialize buckets:
kubectl exec -n ai-part-designer-prod deployment/backend -- \
  python -c "
import asyncio
from app.core.storage_init import initialize_storage
result = asyncio.run(initialize_storage())
print(result)
"

# If MinIO PVC data was lost, restore files from external backup
# or accept data loss within RPO window
```

#### Step 5: Application Deploy (30 min)

```bash
cd helm/ai-part-designer && helm dependency update

helm upgrade --install ai-part-designer ./helm/ai-part-designer \
  --namespace ai-part-designer-prod \
  --values helm/ai-part-designer/values-production.yaml \
  --wait \
  --timeout 20m

# Verify pods
kubectl get pods -n ai-part-designer-prod
```

#### Step 6: Ingress & TLS (15 min)

```bash
# Ingress controller deploys as part of Helm chart
# Verify certificates
kubectl get certificate -n ai-part-designer-prod

# If certificates not auto-provisioned
kubectl apply -k k8s/overlays/production

# Verify HTTPS
curl -I https://app.assemblematic.ai
```

#### Step 7: Background Workers (10 min)

```bash
# Workers deploy as part of Helm chart — verify:
kubectl get pods -n ai-part-designer-prod -l app.kubernetes.io/name=celery-worker
kubectl get pods -n ai-part-designer-prod -l app.kubernetes.io/name=celery-beat

# Verify Celery is processing
kubectl logs -n ai-part-designer-prod -l app.kubernetes.io/name=celery-worker --tail=20
```

#### Step 8: Verification (15 min)

Follow the [Post-Recovery Verification](#9-post-recovery-verification) checklist below.

---

## 9. Post-Recovery Verification

Run through this checklist after **any** recovery procedure.

### Health Check Checklist

```bash
# ── API Health ──
curl -s https://api.assemblematic.ai/api/v1/health | jq .
# Expected: {"status": "healthy"}

# ── Database Connectivity ──
kubectl exec -n ai-part-designer-prod deployment/backend -- \
  python -c "
import asyncio
from app.core.database import async_session_maker
from sqlalchemy import text
async def check():
    async with async_session_maker() as s:
        r = await s.execute(text('SELECT 1'))
        print('DB OK:', r.scalar())
asyncio.run(check())
"

# ── PostgreSQL Cluster Status ──
kubectl get cluster -n ai-part-designer-prod postgres-cluster
# Expected: "Cluster in healthy state", all instances online

# ── PostgreSQL Replication ──
kubectl exec -n ai-part-designer-prod postgres-cluster-1 -- \
  psql -U postgres -c "SELECT client_addr, state, replay_lag FROM pg_stat_replication;"

# ── Redis Connectivity ──
kubectl exec -n ai-part-designer-prod -l app=redis -- redis-cli PING
# Expected: PONG

# ── Storage Accessibility ──
kubectl exec -n ai-part-designer-prod deployment/backend -- \
  python -c "
from app.worker.tasks.maintenance import check_storage_health
result = check_storage_health()
print(result['overall_status'])
"
# Expected: "healthy"

# ── Celery Workers ──
kubectl get pods -n ai-part-designer-prod -l app.kubernetes.io/name=celery-worker
# Expected: All Running/Ready

kubectl get pods -n ai-part-designer-prod -l app.kubernetes.io/name=celery-beat
# Expected: 1 pod Running/Ready

# ── Ingress ──
curl -I https://app.assemblematic.ai
# Expected: HTTP/2 200

curl -I http://app.assemblematic.ai
# Expected: 301/308 redirect to HTTPS

# ── Certificates ──
kubectl get certificate -n ai-part-designer-prod
# Expected: READY=True, expiry > 30 days

# ── OpenBao ──
kubectl exec -n openbao openbao-0 -- openbao status
# Expected: Sealed: false

# ── External Secrets Sync ──
kubectl get externalsecret -n ai-part-designer-prod
# Expected: All SecretSynced=True

# ── PVCs ──
kubectl get pvc -n ai-part-designer-prod
# Expected: All Bound
```

### Functional Smoke Tests

| Test | Command | Expected |
|------|---------|----------|
| User login | `curl -X POST https://api.assemblematic.ai/api/v1/auth/login ...` | 200 + JWT token |
| List designs | `curl -H "Authorization: Bearer $TOKEN" https://api.assemblematic.ai/api/v1/designs` | 200 + JSON array |
| Health endpoint | `curl https://api.assemblematic.ai/api/v1/health` | `{"status": "healthy"}` |
| Frontend loads | `curl -s https://app.assemblematic.ai \| grep -c "<!DOCTYPE"` | 1 |

---

## 10. Escalation Matrix

### Severity Definitions

| Severity | Definition | Examples |
|----------|-----------|----------|
| **P1 — Full Outage** | All users affected, no workaround | Database down, cluster failure, total ingress failure |
| **P2 — Partial Outage** | Some features degraded, workaround exists | CAD generation failing, one replica down, cert warning |
| **P3 — Degraded Performance** | System functional but slow or non-critical issue | High latency, non-critical worker failures, disk warnings |

### Response & Escalation

| Severity | Initial Response | Communication | Escalation (if unresolved) | Resolution Target |
|----------|-----------------|---------------|---------------------------|-------------------|
| **P1** | 15 min | Immediately post to `#incidents` | 30 min → Tech Lead → 60 min → VP Engineering | 2 hours |
| **P2** | 30 min | Post update within 1 hour | 2 hours → Tech Lead | 4 hours |
| **P3** | 2 hours | Update in next standup | Next business day → Tech Lead | 24 hours |

### Contact Chain

| Role | Contact | Availability |
|------|---------|--------------|
| On-Call Engineer | PagerDuty rotation | 24/7 |
| Platform Tech Lead | `#platform-team` Slack | Business hours + P1 pages |
| VP Engineering | PagerDuty escalation | P1 only |
| Security Team | `#security-incidents` Slack | P1 (secrets/data breach) |
| Database Team | `#database-ops` Slack | P1/P2 DB issues |

---

## 11. Communication Templates

### 11.1 Incident Notification (Slack / Email)

```
🔴 INCIDENT — [P1/P2/P3] — [Short Title]

Status: INVESTIGATING / IDENTIFIED / MONITORING / RESOLVED
Impact: [Description of user impact]
Started: [HH:MM UTC]
Components: [Database / API / Storage / Ingress / All]

Current actions:
- [What is being done right now]

Next update: [HH:MM UTC or "in 30 minutes"]

Incident Commander: [Name]
```

### 11.2 Status Update

```
🟡 UPDATE — [Incident Title]

Status: IDENTIFIED
Root Cause: [Brief description]
Mitigation: [Steps taken or in progress]
ETA to Resolution: [Time estimate]

Next update: [HH:MM UTC]
```

### 11.3 Resolution Notification

```
🟢 RESOLVED — [Incident Title]

Duration: [Start time] – [End time] ([X]h [Y]m)
Root Cause: [Brief description]
Resolution: [What fixed it]
Data Loss: [None / Description of affected data]

Post-mortem scheduled: [Date/Time]
Post-mortem doc: [Link]
```

### 11.4 Post-Mortem Template

```markdown
# Post-Mortem: [Incident Title]

**Date:** YYYY-MM-DD
**Duration:** Xh Ym
**Severity:** P1/P2/P3
**Incident Commander:** [Name]
**Author:** [Name]

## Summary
[1-2 sentence description of what happened]

## Timeline (all times UTC)
| Time | Event |
|------|-------|
| HH:MM | [First detection / alert fired] |
| HH:MM | [Incident declared, responders paged] |
| HH:MM | [Root cause identified] |
| HH:MM | [Mitigation applied] |
| HH:MM | [Service restored] |
| HH:MM | [Incident closed] |

## Root Cause
[Detailed explanation]

## Impact
- Users affected: [count or percentage]
- Duration of impact: [time]
- Data loss: [none or description]

## What Went Well
- [Item]

## What Went Wrong
- [Item]

## Action Items
| Action | Owner | Due Date | Status |
|--------|-------|----------|--------|
| [Action item] | [Name] | [Date] | Open |

## Lessons Learned
[Key takeaways]
```

---

## 12. Quarterly DR Test Plan

### Test Schedule

| Quarter | Test Date | Test Type | Lead |
|---------|-----------|-----------|------|
| Q1 2026 | 2026-03-15 | Database restore + storage failover | Platform Lead |
| Q2 2026 | 2026-06-15 | Full disaster recovery simulation | Platform Lead |
| Q3 2026 | 2026-09-15 | Secrets rotation + ingress recovery | Security Lead |
| Q4 2026 | 2026-12-15 | Full disaster recovery simulation | Platform Lead |

### Test Procedures

#### Test 1: Database Recovery (Every Quarter)

| Step | Action | Pass Criteria |
|------|--------|---------------|
| 1 | Trigger manual CloudNativePG backup | Backup shows status=Completed |
| 2 | Create test restore cluster in staging | Cluster reaches healthy state |
| 3 | Verify data in restored cluster | `SELECT count(*) FROM designs` matches production |
| 4 | Test PITR to 1 hour ago | Restored cluster has data up to target time |
| 5 | Measure total recovery time | ≤ 2 hours (RTO target) |
| 6 | Clean up test restore cluster | Cluster deleted, no orphaned PVCs |

#### Test 2: Object Storage Recovery (Every Quarter)

| Step | Action | Pass Criteria |
|------|--------|---------------|
| 1 | Upload test file to versioned bucket | File accessible |
| 2 | Delete test file | File shows delete marker |
| 3 | Restore file via version rollback | File accessible again, content matches |
| 4 | Run `initialize_storage()` | All buckets exist, versioning enabled |
| 5 | Run `check_storage_health` task | Returns `overall_status: healthy` |

#### Test 3: Secrets Recovery (Every Quarter)

| Step | Action | Pass Criteria |
|------|--------|---------------|
| 1 | Take Raft snapshot of OpenBao | Snapshot file created |
| 2 | Simulate sealed state (in staging) | OpenBao shows Sealed: true |
| 3 | Unseal using stored keys | OpenBao shows Sealed: false |
| 4 | Verify secret access | `openbao kv list` returns expected paths |
| 5 | Rotate one non-critical secret | Service picks up new secret after sync |

#### Test 4: Full DR Simulation (Semi-Annual, Staging Only)

| Step | Action | Pass Criteria |
|------|--------|---------------|
| 1 | Delete staging namespace entirely | All pods terminated |
| 2 | Follow full recovery sequence (Section 8) | All steps succeed |
| 3 | Run post-recovery verification (Section 9) | All checks pass |
| 4 | Measure total recovery time | ≤ 4 hours (RTO target) |
| 5 | Verify data loss is within RPO | Data consistent with last backup |

### Test Log Template

```markdown
# DR Test Log

**Date:** YYYY-MM-DD
**Test Type:** [Database / Storage / Secrets / Full DR]
**Environment:** staging
**Lead:** [Name]
**Participants:** [Names]

## Results

| Step | Status | Duration | Notes |
|------|--------|----------|-------|
| 1    | ✅/❌   | Xm       |       |
| 2    | ✅/❌   | Xm       |       |
| ...  | ...    | ...      |       |

**Total Duration:** Xh Ym
**RTO Met:** Yes/No
**RPO Met:** Yes/No

## Issues Found
- [Issue and remediation]

## Follow-Up Actions
| Action | Owner | Due |
|--------|-------|-----|
| [Item] | [Name] | [Date] |

## Sign-Off
- [ ] Platform Lead
- [ ] Engineering Manager
```

---

## Appendix: Quick Reference

### Key Celery Task Names

| Task | Schedule | Purpose |
|------|----------|---------|
| `app.worker.tasks.maintenance.backup_database` | Daily | pg_dump backup to MinIO |
| `app.worker.tasks.maintenance.weekly_full_backup` | Weekly (Sun 3 AM) | Full backup via BackupService |
| `app.worker.tasks.maintenance.verify_backups` | Weekly | Validate backup integrity |
| `app.worker.tasks.maintenance.check_storage_health` | Periodic | Verify bucket health & versioning |
| `app.worker.tasks.maintenance.check_data_integrity` | Weekly | Orphan detection, referential integrity |
| `app.worker.tasks.maintenance.archive_old_designs` | Weekly | Move inactive designs to cold storage |
| `app.worker.tasks.maintenance.vacuum_database` | Periodic | PostgreSQL ANALYZE |
| `app.worker.tasks.maintenance.purge_expired_trash` | Daily | Permanent delete of expired trash |

### Key File Paths

| File | Purpose |
|------|---------|
| `backend/app/core/backup.py` | `DatabaseBackup` class — pg_dump, restore, cleanup |
| `backend/app/core/storage_init.py` | `initialize_storage()` — bucket setup, versioning, lifecycle |
| `backend/app/worker/tasks/maintenance.py` | All maintenance Celery tasks |
| `k8s/base/cloudnative-pg/cluster.yaml` | CloudNativePG cluster definition |
| `k8s/base/cloudnative-pg/scheduled-backup.yaml` | Daily 2 AM backup schedule |
| `helm/ai-part-designer/values-production.yaml` | Production Helm values |

### Make Commands

```bash
make backup               # Create database backup (pg_dump)
make export-user-data USER_ID=<uuid>   # GDPR data export
make analytics-snapshot    # Export analytics data (last 7 days)
```

---

## Related Documents

- [Data Engineering — Backup & Recovery](../architecture/data-engineering.md#7-backup--recovery)
- [Ingress Operations Runbook](../../helm/INGRESS_RUNBOOK.md)
- [Secrets Management Guide](./secrets-management.md)
- [Storage Implementation](../../helm/STORAGE_IMPLEMENTATION.md)
- [CloudNativePG README](../../k8s/base/cloudnative-pg/README.md)
- [Deployment Guide](../../helm/DEPLOYMENT_GUIDE.md)

---

*Maintained by Platform Operations. Last updated: 2026-02-24.*
