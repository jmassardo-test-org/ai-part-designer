# Secrets Management Operations Guide

## Overview

AI Part Designer uses OpenBao (open-source Vault fork) for secure secrets management. This guide covers operational procedures for managing secrets in production.

## Table of Contents

- [Initial Setup](#initial-setup)
- [Daily Operations](#daily-operations)
- [Secret Lifecycle](#secret-lifecycle)
- [Troubleshooting](#troubleshooting)
- [Emergency Procedures](#emergency-procedures)
- [Audit and Compliance](#audit-and-compliance)

---

## Initial Setup

### Step 1: Deploy OpenBao

OpenBao runs in the `openbao` namespace with 3 replicas for high availability.

```bash
# Add OpenBao Helm repository
helm repo add openbao https://openbao.github.io/openbao-helm
helm repo update

# Create namespace
kubectl create namespace openbao

# Install with custom values
helm install openbao openbao/openbao \
  --namespace openbao \
  --values k8s/base/openbao/openbao-helm-values.yaml \
  --wait --timeout 5m

# Verify deployment
kubectl get pods -n openbao
```

Expected output: 3 pods in Running state.

### Step 2: Initialize OpenBao

⚠️ **CRITICAL**: This is a one-time operation. Store the unseal keys securely!

```bash
# Apply initialization job
kubectl apply -f k8s/base/openbao/initialization-job.yaml

# Monitor initialization
kubectl logs -n openbao job/openbao-init-config -f

# Extract and backup unseal keys
kubectl get secret openbao-unseal-keys -n openbao -o yaml > /secure/backup/openbao-keys-$(date +%Y%m%d).yaml

# Store backup in multiple secure locations:
# 1. Encrypted cloud storage (S3 with KMS)
# 2. Password manager (1Password/LastPass)
# 3. Physical safe (printed, sealed envelope)
```

### Step 3: Install External Secrets Operator

ESO synchronizes secrets from OpenBao into Kubernetes Secrets.

```bash
# Install via Helm
helm repo add external-secrets https://charts.external-secrets.io
helm install external-secrets external-secrets/external-secrets \
  --namespace external-secrets-system \
  --create-namespace

# Verify installation
kubectl get pods -n external-secrets-system
```

### Step 4: Configure Secret Stores

```bash
# Deploy secret store configurations
kubectl apply -f k8s/base/openbao/secret-store-config.yaml

# Verify connectivity
kubectl get clustersecretstore openbao-ai-part-designer
kubectl get secretstore -n ai-part-designer
```

---

## Daily Operations

### Checking OpenBao Health

```bash
# Check pod status
kubectl get pods -n openbao

# Check seal status (should show "Sealed: false")
kubectl exec -n openbao openbao-0 -- openbao status

# Check replication status
kubectl exec -n openbao openbao-0 -- openbao operator raft list-peers
```

### Viewing Audit Logs

```bash
# Tail audit logs from OpenBao pods
kubectl logs -n openbao openbao-0 -f | grep audit

# Export audit logs for compliance
kubectl exec -n openbao openbao-0 -- cat /openbao/audit/audit.log > audit-$(date +%Y%m%d).log
```

### Monitoring Secret Synchronization

```bash
# Check ExternalSecret status
kubectl get externalsecret -n ai-part-designer

# View sync details
kubectl describe externalsecret database-credentials -n ai-part-designer

# Force immediate refresh
kubectl annotate externalsecret database-credentials \
  -n ai-part-designer \
  force-sync="$(date +%s)" \
  --overwrite
```

---

## Secret Lifecycle

### Creating New Secrets

#### Database Credentials

```bash
# Login to OpenBao
export VAULT_ADDR=http://localhost:8200
kubectl port-forward -n openbao svc/openbao 8200:8200 &

# Get root token
ROOT_TOKEN=$(kubectl get secret openbao-unseal-keys -n openbao -o jsonpath='{.data.root-token}' | base64 -d)
openbao login $ROOT_TOKEN

# Store database credentials
openbao kv put secret/ai-part-designer/database \
  host="postgres-primary.ai-part-designer.svc.cluster.local" \
  port="5432" \
  database="ai_part_designer_prod" \
  username="app_user_$(openssl rand -hex 4)" \
  password="$(openssl rand -base64 32)" \
  pool_size="20" \
  max_overflow="10"
```

#### AI Service API Keys

```bash
# OpenAI credentials
openbao kv put secret/ai-part-designer/ai-services/openai \
  api_key="sk-proj-..." \
  org_id="org-..." \
  model="gpt-4o" \
  max_tokens="8000"

# Anthropic credentials
openbao kv put secret/ai-part-designer/ai-services/anthropic \
  api_key="sk-ant-api03-..." \
  model="claude-sonnet-4-20250514" \
  max_tokens="4096" \
  temperature="0.3"
```

#### Application Secrets

```bash
# JWT signing keys
openbao kv put secret/ai-part-designer/auth/jwt-keys \
  secret_key="$(openssl rand -hex 32)" \
  algorithm="HS256" \
  access_token_expire_minutes="15" \
  refresh_token_expire_days="7"

# Session secrets
openbao kv put secret/ai-part-designer/auth/session-secrets \
  session_secret="$(openssl rand -hex 64)" \
  cookie_secret="$(openssl rand -hex 32)"

# Encryption keys for sensitive data
openbao kv put secret/ai-part-designer/encryption/data-keys \
  master_key="$(openssl rand -base64 32)" \
  field_encryption_key="$(openssl rand -base64 32)"
```

#### Storage Credentials

```bash
# S3/MinIO credentials
openbao kv put secret/ai-part-designer/storage/s3-credentials \
  access_key_id="AKIA..." \
  secret_access_key="$(openssl rand -base64 40)" \
  bucket_name="ai-part-designer-files-prod" \
  region="us-east-1" \
  endpoint="https://s3.amazonaws.com"
```

### Rotating Secrets

#### Manual Rotation Process

```bash
# 1. Generate new secret value
NEW_PASSWORD=$(openssl rand -base64 32)

# 2. Update in OpenBao
openbao kv put secret/ai-part-designer/database \
  password="$NEW_PASSWORD" \
  # ... other fields remain the same

# 3. Update actual service (e.g., PostgreSQL)
kubectl exec -n ai-part-designer postgres-0 -- psql -U postgres -c \
  "ALTER USER app_user WITH PASSWORD '$NEW_PASSWORD';"

# 4. ExternalSecret will sync automatically within refresh interval
# Or force immediate sync:
kubectl annotate externalsecret database-credentials \
  -n ai-part-designer \
  force-sync="$(date +%s)" \
  --overwrite

# 5. Rolling restart of dependent services
kubectl rollout restart deployment/api -n ai-part-designer
kubectl rollout restart deployment/worker -n ai-part-designer
```

#### Automated Rotation with OpenBao Database Engine

For database credentials, OpenBao can generate dynamic, time-limited credentials:

```bash
# Enable database secrets engine
openbao secrets enable database

# Configure PostgreSQL connection
openbao write database/config/ai-part-designer-postgres \
  plugin_name=postgresql-database-plugin \
  allowed_roles="api-role,worker-role" \
  connection_url="postgresql://{{username}}:{{password}}@postgres:5432/ai_part_designer" \
  username="openbao_admin" \
  password="openbao_admin_password"

# Create role for API service
openbao write database/roles/api-role \
  db_name=ai-part-designer-postgres \
  creation_statements="CREATE USER \"{{name}}\" WITH PASSWORD '{{password}}' VALID UNTIL '{{expiration}}'; \
    GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO \"{{name}}\";" \
  default_ttl="1h" \
  max_ttl="24h"

# API pods will now get fresh credentials automatically
```

### Deleting Secrets

```bash
# Soft delete (can be recovered)
openbao kv delete secret/ai-part-designer/obsolete-service/credentials

# View deleted versions
openbao kv metadata get secret/ai-part-designer/obsolete-service/credentials

# Permanent deletion (cannot be recovered)
openbao kv destroy -versions=1,2,3 secret/ai-part-designer/obsolete-service/credentials
openbao kv metadata delete secret/ai-part-designer/obsolete-service/credentials
```

---

## Troubleshooting

### OpenBao is Sealed

If OpenBao pods restart, they may be sealed. Unseal manually:

```bash
# Check seal status
kubectl exec -n openbao openbao-0 -- openbao status

# Unseal (requires 3 of 5 unseal keys)
for i in 1 2 3; do
  KEY=$(kubectl get secret openbao-unseal-keys -n openbao -o jsonpath="{.data.key-$i}" | base64 -d)
  kubectl exec -n openbao openbao-0 -- openbao operator unseal "$KEY"
done

# Repeat for other pods
kubectl exec -n openbao openbao-1 -- openbao operator unseal ...
kubectl exec -n openbao openbao-2 -- openbao operator unseal ...
```

### ExternalSecret Not Syncing

```bash
# Check ExternalSecret status
kubectl describe externalsecret <name> -n ai-part-designer

# Common issues:
# 1. ServiceAccount missing or wrong permissions
kubectl get sa -n ai-part-designer

# 2. SecretStore not connected
kubectl get secretstore -n ai-part-designer

# 3. Path or key name incorrect in OpenBao
openbao kv get secret/ai-part-designer/<path>

# 4. ESO controller issues
kubectl logs -n external-secrets-system deployment/external-secrets
```

### Application Cannot Access Secrets

```bash
# 1. Verify Secret exists
kubectl get secret <name> -n ai-part-designer
kubectl describe secret <name> -n ai-part-designer

# 2. Check pod has secret mounted/referenced
kubectl describe pod <pod-name> -n ai-part-designer | grep -A5 "Mounts:\|Env:"

# 3. Verify pod service account has access
kubectl get pod <pod-name> -n ai-part-designer -o jsonpath='{.spec.serviceAccountName}'

# 4. Test OpenBao policy
openbao token create -policy=ai-part-designer-api -format=json
# Use token to test access
```

### Raft Storage Issues

```bash
# Check Raft cluster health
kubectl exec -n openbao openbao-0 -- openbao operator raft list-peers

# Remove dead peer
kubectl exec -n openbao openbao-0 -- openbao operator raft remove-peer <peer-id>

# Take snapshot for backup
kubectl exec -n openbao openbao-0 -- openbao operator raft snapshot save /tmp/snapshot.snap
kubectl cp openbao/openbao-0:/tmp/snapshot.snap ./openbao-snapshot-$(date +%Y%m%d).snap
```

---

## Emergency Procedures

### Break-Glass Access

If normal authentication fails, use the root token:

```bash
# Retrieve root token from secure backup
# NEVER store root token in git or unsecured locations

# Login with root token
ROOT_TOKEN=$(kubectl get secret openbao-unseal-keys -n openbao -o jsonpath='{.data.root-token}' | base64 -d)
kubectl port-forward -n openbao svc/openbao 8200:8200 &
openbao login $ROOT_TOKEN

# Perform emergency operations
# ...

# IMPORTANT: Revoke root token after use
openbao token revoke -self

# Audit the emergency access
kubectl logs -n openbao openbao-0 | grep "root token" > emergency-access-$(date +%Y%m%d).log
```

### Disaster Recovery

#### Complete OpenBao Failure

```bash
# 1. Restore from Raft snapshot
kubectl exec -n openbao openbao-0 -- openbao operator raft snapshot restore /path/to/snapshot.snap

# 2. Unseal all nodes
# (follow unseal procedure above)

# 3. Verify all secrets are accessible
openbao kv list secret/ai-part-designer/
```

#### Lost Unseal Keys

⚠️ **If all unseal keys are lost, data CANNOT be recovered.**

Prevention:
- Store keys in 3+ secure, separate locations
- Use auto-unseal with cloud KMS (AWS KMS, GCP Cloud KMS, Azure Key Vault)
- Regular testing of key recovery procedures

#### Compromised Secrets

```bash
# 1. Immediately rotate compromised secrets
openbao kv put secret/ai-part-designer/<path> key="new_value"

# 2. Force sync to Kubernetes
kubectl annotate externalsecret <name> -n ai-part-designer force-sync="$(date +%s)" --overwrite

# 3. Rolling restart affected services
kubectl rollout restart deployment/<service> -n ai-part-designer

# 4. Audit access logs
openbao audit list
kubectl logs -n openbao openbao-0 | grep "<path>" > audit-investigation.log

# 5. Revoke old credentials in external services
# (e.g., revoke old API keys, change database passwords)
```

---

## Audit and Compliance

### Audit Log Export

```bash
# Export OpenBao audit logs
kubectl exec -n openbao openbao-0 -- cat /openbao/audit/audit.log | \
  jq 'select(.time >= "2025-01-01")' > audit-january-2025.json

# Common audit queries:

# Who accessed database credentials?
cat audit.json | jq 'select(.request.path | contains("database"))'

# Failed authentication attempts
cat audit.json | jq 'select(.error != null and .type == "request")'

# Root token usage (should be rare)
cat audit.json | jq 'select(.auth.token_policies[] == "root")'
```

### Compliance Reports

```bash
# List all secrets
openbao kv list -format=json secret/ai-part-designer/ | jq -r '.[]'

# Secret metadata (last rotation, access count)
openbao kv metadata get secret/ai-part-designer/database

# Policy review
openbao policy list
openbao policy read ai-part-designer-api
```

### Access Review

```bash
# List active tokens
openbao list auth/token/accessors

# Review service account bindings
kubectl get rolebinding -n ai-part-designer
kubectl describe role <role-name> -n ai-part-designer

# Review OpenBao policies
openbao policy list
```

---

## Security Best Practices

### DO

✅ Use least-privilege policies for each service
✅ Rotate secrets regularly (quarterly minimum)
✅ Enable audit logging
✅ Back up unseal keys to multiple secure locations
✅ Use dynamic secrets where possible
✅ Monitor for unauthorized access attempts
✅ Test disaster recovery procedures quarterly

### DON'T

❌ Store secrets in Git repositories
❌ Share root token
❌ Use same credentials across environments
❌ Disable audit logging
❌ Grant wildcard access (`*`) in policies
❌ Store unseal keys on the same system as OpenBao
❌ Ignore audit log alerts

---

## Appendix A: Secret Inventory

| Secret Path | Purpose | Rotation Period | Owner |
|-------------|---------|-----------------|-------|
| `ai-part-designer/database` | PostgreSQL connection | 90 days | Database team |
| `ai-part-designer/redis` | Cache connection | 90 days | Platform team |
| `ai-part-designer/ai-services/openai` | AI generation | API key rotation | AI team |
| `ai-part-designer/ai-services/anthropic` | AI generation | API key rotation | AI team |
| `ai-part-designer/auth/jwt-keys` | Authentication | 180 days | Security team |
| `ai-part-designer/storage/s3-credentials` | File storage | 90 days | Platform team |
| `ai-part-designer/email/smtp-config` | Email delivery | As needed | Platform team |
| `ai-part-designer/payments/stripe-keys` | Payment processing | API key rotation | Finance team |

---

## Appendix B: Contact Information

- **OpenBao Issues**: DevOps team (#devops-alerts Slack)
- **Security Incidents**: Security team (#security-incidents Slack)
- **After-Hours**: On-call engineer (PagerDuty)

---

## Appendix C: Change Log

| Date | Change | Author |
|------|--------|--------|
| 2025-02-06 | Initial documentation | DevOps |

---

*Last Updated: 2025-02-06*
