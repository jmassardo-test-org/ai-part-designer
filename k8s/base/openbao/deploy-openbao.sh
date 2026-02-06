#!/usr/bin/env bash
# OpenBao Deployment Script for AI Part Designer
# This script automates the complete deployment and configuration of OpenBao

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
OPENBAO_NAMESPACE="openbao"
APP_NAMESPACE="ai-part-designer"
HELM_CHART="openbao/openbao"
RELEASE_NAME="openbao"

# Helper functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_prerequisites() {
    log_info "Checking prerequisites..."
    
    local missing_tools=()
    
    command -v kubectl >/dev/null 2>&1 || missing_tools+=("kubectl")
    command -v helm >/dev/null 2>&1 || missing_tools+=("helm")
    command -v jq >/dev/null 2>&1 || missing_tools+=("jq")
    
    if [ ${#missing_tools[@]} -ne 0 ]; then
        log_error "Missing required tools: ${missing_tools[*]}"
        exit 1
    fi
    
    # Check cluster connectivity
    if ! kubectl cluster-info &>/dev/null; then
        log_error "Cannot connect to Kubernetes cluster"
        exit 1
    fi
    
    log_info "All prerequisites met"
}

deploy_openbao() {
    log_info "Deploying OpenBao..."
    
    # Create namespace if it doesn't exist
    if ! kubectl get namespace "$OPENBAO_NAMESPACE" &>/dev/null; then
        kubectl create namespace "$OPENBAO_NAMESPACE"
        log_info "Created namespace: $OPENBAO_NAMESPACE"
    fi
    
    # Add Helm repo
    helm repo add openbao https://openbao.github.io/openbao-helm 2>/dev/null || true
    helm repo update
    
    # Install or upgrade OpenBao
    helm upgrade --install "$RELEASE_NAME" "$HELM_CHART" \
        --namespace "$OPENBAO_NAMESPACE" \
        --values k8s/base/openbao/openbao-helm-values.yaml \
        --wait \
        --timeout 10m
    
    log_info "OpenBao deployed successfully"
}

wait_for_openbao() {
    log_info "Waiting for OpenBao pods to be ready..."
    
    kubectl wait --for=condition=ready pod \
        -l app.kubernetes.io/name=openbao \
        -n "$OPENBAO_NAMESPACE" \
        --timeout=300s
    
    log_info "OpenBao is ready"
}

initialize_openbao() {
    log_info "Initializing OpenBao..."
    
    # Check if already initialized
    if kubectl get secret openbao-unseal-keys -n "$OPENBAO_NAMESPACE" &>/dev/null; then
        log_warn "OpenBao already initialized (unseal keys secret exists)"
        log_warn "Skipping initialization. To re-initialize, delete the cluster and secret"
        return 0
    fi
    
    # Create policy ConfigMap
    kubectl create configmap openbao-policies \
        --from-file=k8s/base/openbao/policies/ \
        --namespace="$OPENBAO_NAMESPACE" \
        --dry-run=client -o yaml | kubectl apply -f -
    
    # Apply initialization job
    kubectl apply -f k8s/base/openbao/initialization-job.yaml
    
    # Wait for job completion
    log_info "Waiting for initialization to complete..."
    kubectl wait --for=condition=complete job/openbao-init-config \
        -n "$OPENBAO_NAMESPACE" \
        --timeout=300s
    
    # Show job logs
    kubectl logs -n "$OPENBAO_NAMESPACE" job/openbao-init-config
    
    log_warn "⚠️  CRITICAL: Backup unseal keys immediately!"
    log_warn "Run: kubectl get secret openbao-unseal-keys -n $OPENBAO_NAMESPACE -o yaml > openbao-keys-backup.yaml"
}

deploy_external_secrets_operator() {
    log_info "Deploying External Secrets Operator..."
    
    # Check if already installed
    if kubectl get namespace external-secrets-system &>/dev/null; then
        log_info "External Secrets Operator already installed"
        return 0
    fi
    
    helm repo add external-secrets https://charts.external-secrets.io 2>/dev/null || true
    helm repo update
    
    helm install external-secrets external-secrets/external-secrets \
        --namespace external-secrets-system \
        --create-namespace \
        --wait
    
    log_info "External Secrets Operator deployed"
}

configure_secret_stores() {
    log_info "Configuring SecretStores..."
    
    # Create app namespace if needed
    if ! kubectl get namespace "$APP_NAMESPACE" &>/dev/null; then
        kubectl create namespace "$APP_NAMESPACE"
    fi
    
    # Create service accounts for API and Worker
    kubectl create serviceaccount api-service -n "$APP_NAMESPACE" \
        --dry-run=client -o yaml | kubectl apply -f -
    kubectl create serviceaccount worker-service -n "$APP_NAMESPACE" \
        --dry-run=client -o yaml | kubectl apply -f -
    
    # Apply SecretStore configurations
    kubectl apply -f k8s/base/openbao/secret-store-config.yaml
    
    log_info "SecretStores configured"
}

bootstrap_initial_secrets() {
    log_info "Bootstrapping initial secrets..."
    
    # Port-forward to OpenBao
    kubectl port-forward -n "$OPENBAO_NAMESPACE" svc/openbao 8200:8200 &
    PORT_FORWARD_PID=$!
    
    # Wait for port-forward to be ready
    sleep 3
    
    # Get root token
    ROOT_TOKEN=$(kubectl get secret openbao-unseal-keys -n "$OPENBAO_NAMESPACE" \
        -o jsonpath='{.data.root-token}' | base64 -d)
    
    export VAULT_ADDR="http://localhost:8200"
    export VAULT_TOKEN="$ROOT_TOKEN"
    
    # Generate secure random values
    DB_PASSWORD=$(openssl rand -base64 32)
    REDIS_PASSWORD=$(openssl rand -base64 32)
    JWT_SECRET=$(openssl rand -hex 32)
    SESSION_SECRET=$(openssl rand -hex 64)
    
    log_info "Creating initial secrets in OpenBao..."
    
    # Database credentials (placeholder - update with real values)
    openbao kv put secret/ai-part-designer/database \
        host="postgres.ai-part-designer.svc.cluster.local" \
        port="5432" \
        database="ai_part_designer" \
        username="app_user" \
        password="$DB_PASSWORD" \
        pool_size="20" \
        max_overflow="10"
    
    # Redis credentials
    openbao kv put secret/ai-part-designer/redis \
        host="redis.ai-part-designer.svc.cluster.local" \
        port="6379" \
        password="$REDIS_PASSWORD" \
        db="0" \
        cache_ttl="3600"
    
    # JWT keys
    openbao kv put secret/ai-part-designer/auth/jwt-keys \
        secret_key="$JWT_SECRET" \
        algorithm="HS256" \
        access_token_expire_minutes="15" \
        refresh_token_expire_days="7"
    
    # Session secrets
    openbao kv put secret/ai-part-designer/auth/session-secrets \
        session_secret="$SESSION_SECRET" \
        cookie_secret="$(openssl rand -hex 32)"
    
    # Cleanup
    kill $PORT_FORWARD_PID 2>/dev/null || true
    
    log_info "Initial secrets created"
    log_warn "⚠️  Update AI service API keys manually:"
    log_warn "    openbao kv put secret/ai-part-designer/ai-services/openai api_key='sk-...'"
    log_warn "    openbao kv put secret/ai-part-designer/ai-services/anthropic api_key='sk-ant-...'"
}

verify_deployment() {
    log_info "Verifying deployment..."
    
    # Check OpenBao status
    local sealed_count=$(kubectl exec -n "$OPENBAO_NAMESPACE" openbao-0 -- \
        openbao status 2>/dev/null | grep "Sealed" | grep -c "false" || echo "0")
    
    if [ "$sealed_count" -eq 0 ]; then
        log_error "OpenBao is sealed"
        return 1
    fi
    
    # Check ESO
    if ! kubectl get deployment external-secrets -n external-secrets-system &>/dev/null; then
        log_error "External Secrets Operator not found"
        return 1
    fi
    
    # Check SecretStores
    if ! kubectl get clustersecretstore openbao-ai-part-designer &>/dev/null; then
        log_error "ClusterSecretStore not found"
        return 1
    fi
    
    log_info "✅ All components verified successfully"
}

print_next_steps() {
    cat <<EOF

${GREEN}╔════════════════════════════════════════════════════════════════╗
║            OpenBao Deployment Complete!                         ║
╚════════════════════════════════════════════════════════════════╝${NC}

${YELLOW}Next Steps:${NC}

1. ${GREEN}Backup Unseal Keys${NC}
   kubectl get secret openbao-unseal-keys -n $OPENBAO_NAMESPACE -o yaml \\
     > openbao-keys-backup-\$(date +%Y%m%d).yaml
   
   Store this file in:
   - Encrypted cloud storage
   - Password manager
   - Physical safe

2. ${GREEN}Add AI Service API Keys${NC}
   kubectl port-forward -n $OPENBAO_NAMESPACE svc/openbao 8200:8200
   
   export VAULT_ADDR=http://localhost:8200
   export VAULT_TOKEN=\$(kubectl get secret openbao-unseal-keys \\
     -n $OPENBAO_NAMESPACE -o jsonpath='{.data.root-token}' | base64 -d)
   
   openbao kv put secret/ai-part-designer/ai-services/openai \\
     api_key="sk-..." org_id="org-..." model="gpt-4o"
   
   openbao kv put secret/ai-part-designer/ai-services/anthropic \\
     api_key="sk-ant-..." model="claude-sonnet-4-20250514"

3. ${GREEN}Deploy Application${NC}
   Apply ExternalSecret manifests to sync secrets to your application

4. ${GREEN}Review Documentation${NC}
   docs/operations/secrets-management.md

${YELLOW}Useful Commands:${NC}
   View OpenBao logs:  kubectl logs -n $OPENBAO_NAMESPACE -l app.kubernetes.io/name=openbao
   OpenBao UI:         kubectl port-forward -n $OPENBAO_NAMESPACE svc/openbao 8200:8200
   Check seal status:  kubectl exec -n $OPENBAO_NAMESPACE openbao-0 -- openbao status

EOF
}

main() {
    log_info "Starting OpenBao deployment for AI Part Designer"
    
    check_prerequisites
    deploy_openbao
    wait_for_openbao
    initialize_openbao
    deploy_external_secrets_operator
    configure_secret_stores
    bootstrap_initial_secrets
    verify_deployment
    print_next_steps
    
    log_info "Deployment complete!"
}

# Run main function
main "$@"
