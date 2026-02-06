# OpenBao Secrets Management for AI Part Designer

This directory contains OpenBao deployment manifests and operational scripts for the AI Part Designer application.

## Quick Start

```bash
# Deploy everything
./deploy-openbao.sh

# Rotate secrets
./rotate-secrets.sh all

# Audit secret ages
./rotate-secrets.sh audit
```

## Directory Contents

```
openbao/
├── README.md                      # This file
├── deploy-openbao.sh             # Automated deployment script
├── rotate-secrets.sh             # Secret rotation automation
├── openbao-helm-values.yaml     # Helm chart configuration
├── initialization-job.yaml       # Post-install setup job
├── secret-store-config.yaml     # External Secrets Operator config
└── policies/                     # OpenBao access policies
    ├── api-service-policy.hcl   # API service permissions
    ├── worker-service-policy.hcl # Worker service permissions
    └── admin-access-policy.hcl   # Administrative access
```

## Architecture

```
┌─────────────────────────────────────────────────────┐
│  AI Part Designer Application (Namespace)           │
│  ┌────────────┐         ┌────────────┐            │
│  │ API Pods   │         │ Worker Pods│            │
│  │            │         │            │            │
│  │ SA: api-   │         │ SA: worker-│            │
│  │ service    │         │ service    │            │
│  └─────┬──────┘         └──────┬─────┘            │
│        │                       │                   │
│        │  Read Secrets         │                   │
│        ├───────────────────────┤                   │
│        ▼                       ▼                   │
│  ┌──────────────────────────────────────┐         │
│  │  Kubernetes Secrets                   │         │
│  │  (Synced by External Secrets Operator)│        │
│  └──────────────┬───────────────────────┘         │
└─────────────────┼───────────────────────────────────┘
                  │
                  │ Sync (1h refresh)
                  ▼
┌─────────────────────────────────────────────────────┐
│  External Secrets Operator                          │
│  ┌─────────────────────────────────────┐           │
│  │  SecretStore / ClusterSecretStore    │           │
│  │  (Kubernetes Auth to OpenBao)        │           │
│  └──────────────┬──────────────────────┘           │
└─────────────────┼──────────────────────────────────┘
                  │
                  │ Authenticate + Read
                  ▼
┌─────────────────────────────────────────────────────┐
│  OpenBao (Namespace: openbao)                       │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐   │
│  │ openbao-0  │  │ openbao-1  │  │ openbao-2  │   │
│  │ (Raft HA)  │  │ (Raft HA)  │  │ (Raft HA)  │   │
│  └────────────┘  └────────────┘  └────────────┘   │
│                                                     │
│  Secrets stored under:                              │
│  secret/ai-part-designer/*                          │
│    ├── database                                     │
│    ├── redis                                        │
│    ├── ai-services/openai                          │
│    ├── ai-services/anthropic                       │
│    ├── auth/jwt-keys                               │
│    └── storage/s3-credentials                      │
└─────────────────────────────────────────────────────┘
```

## Secret Organization

All secrets are stored under the `secret/ai-part-designer/` prefix in OpenBao:

| Path | Purpose | Accessed By |
|------|---------|-------------|
| `database` | PostgreSQL credentials | API, Worker |
| `redis` | Cache credentials | API, Worker |
| `ai-services/openai` | OpenAI API key | API, Worker |
| `ai-services/anthropic` | Anthropic API key | API, Worker |
| `auth/jwt-keys` | JWT signing secrets | API |
| `auth/session-secrets` | Session encryption | API |
| `storage/s3-credentials` | Object storage access | API, Worker |
| `email/smtp-config` | Email delivery | API, Worker |
| `payments/stripe-keys` | Payment processing | API |
| `oauth/google` | Google OAuth | API |
| `oauth/github` | GitHub OAuth | API |
| `monitoring/sentry-dsn` | Error tracking | API, Worker |
| `encryption/data-keys` | Field-level encryption | API |

## Security Model

### Access Control

- **API Service**: Read-only access to app secrets, auth, AI services
- **Worker Service**: Read-only access to app secrets, AI services (no auth)
- **Admin**: Full CRUD access to all secrets, policies, audit logs

### Authentication

Services authenticate to OpenBao using Kubernetes Service Account tokens:

1. Pod starts with ServiceAccount token mounted
2. External Secrets Operator uses token to authenticate to OpenBao
3. OpenBao validates token with K8s API server
4. If valid, grants access based on associated policy
5. ESO retrieves secrets and creates/updates K8s Secrets
6. Pods consume standard K8s Secrets (env vars or volumes)

### Audit Logging

All OpenBao access is logged to `/openbao/audit/audit.log` with:
- Timestamp
- Requesting identity (ServiceAccount)
- Requested path
- Operation (read/write/delete)
- Result (success/failure)

## Deployment Process

### Prerequisites

- Kubernetes cluster (1.24+)
- `kubectl` configured
- `helm` 3.x installed
- `jq` for JSON processing
- Cluster-admin permissions

### Step-by-Step Deployment

1. **Deploy OpenBao**
   ```bash
   ./deploy-openbao.sh
   ```
   
   This script:
   - Deploys OpenBao via Helm (3 replicas, Raft storage)
   - Initializes OpenBao (generates unseal keys)
   - Stores unseal keys in K8s secret
   - Creates policies
   - Configures Kubernetes auth
   - Deploys External Secrets Operator
   - Creates SecretStores
   - Bootstraps initial secrets

2. **Backup Unseal Keys**
   ```bash
   kubectl get secret openbao-unseal-keys -n openbao -o yaml \
     > openbao-keys-$(date +%Y%m%d).yaml
   
   # Encrypt and store in multiple locations
   gpg --encrypt --recipient admin@example.com openbao-keys-*.yaml
   ```

3. **Add AI Service API Keys**
   ```bash
   kubectl port-forward -n openbao svc/openbao 8200:8200 &
   export VAULT_ADDR=http://localhost:8200
   export VAULT_TOKEN=$(kubectl get secret openbao-unseal-keys \
     -n openbao -o jsonpath='{.data.root-token}' | base64 -d)
   
   openbao kv put secret/ai-part-designer/ai-services/openai \
     api_key="sk-proj-..." \
     org_id="org-..." \
     model="gpt-4o"
   
   openbao kv put secret/ai-part-designer/ai-services/anthropic \
     api_key="sk-ant-..." \
     model="claude-sonnet-4-20250514"
   ```

4. **Deploy Application Workloads**
   ```bash
   # ExternalSecrets will automatically sync secrets to K8s
   kubectl apply -f ../../../k8s/overlays/production/
   ```

## Operations

### Rotating Secrets

Use the provided rotation script:

```bash
# Rotate database password
./rotate-secrets.sh database

# Rotate all secrets
./rotate-secrets.sh all

# Check secret ages
./rotate-secrets.sh audit
```

### Unsealing OpenBao

If OpenBao pods restart, they need to be unsealed:

```bash
# Check seal status
kubectl exec -n openbao openbao-0 -- openbao status

# Unseal (need 3 of 5 keys)
for i in 1 2 3; do
  KEY=$(kubectl get secret openbao-unseal-keys -n openbao \
    -o jsonpath="{.data.key-$i}" | base64 -d)
  kubectl exec -n openbao openbao-0 -- openbao operator unseal "$KEY"
done
```

### Viewing Secrets

```bash
# Port-forward to OpenBao
kubectl port-forward -n openbao svc/openbao 8200:8200 &

# Login
export VAULT_ADDR=http://localhost:8200
ROOT_TOKEN=$(kubectl get secret openbao-unseal-keys -n openbao \
  -o jsonpath='{.data.root-token}' | base64 -d)
openbao login $ROOT_TOKEN

# List all secrets
openbao kv list secret/ai-part-designer/

# Read specific secret
openbao kv get secret/ai-part-designer/database

# View secret history
openbao kv metadata get secret/ai-part-designer/database
```

## Troubleshooting

### ExternalSecret Not Syncing

```bash
# Check ExternalSecret status
kubectl describe externalsecret <name> -n ai-part-designer

# Check ESO controller logs
kubectl logs -n external-secrets-system \
  deployment/external-secrets -f

# Verify SecretStore connectivity
kubectl get secretstore -n ai-part-designer
```

### OpenBao Sealed After Restart

This is expected behavior. Follow unseal procedure above or implement auto-unseal with cloud KMS.

### Policy Permission Errors

```bash
# Check applied policies
openbao token lookup

# Test policy access
openbao kv get secret/ai-part-designer/test
```

## Security Best Practices

✅ **DO:**
- Rotate secrets quarterly minimum
- Back up unseal keys to multiple locations
- Use least-privilege policies
- Enable audit logging
- Monitor for unauthorized access
- Test disaster recovery quarterly

❌ **DON'T:**
- Store secrets in Git
- Use root token for regular operations
- Grant wildcard permissions
- Disable audit logging
- Share unseal keys insecurely

## Additional Documentation

- [Secrets Management Operations Guide](../../../docs/operations/secrets-management.md)
- [OpenBao Documentation](https://openbao.org/docs/)
- [External Secrets Operator Docs](https://external-secrets.io/)

---

*Last Updated: 2025-02-06*
