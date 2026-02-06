#!/usr/bin/env bash
# Secret Rotation Script for AI Part Designer
# Automates the rotation of secrets stored in OpenBao

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OPENBAO_NAMESPACE="openbao"
APP_NAMESPACE="ai-part-designer"

# Import common functions
source "$SCRIPT_DIR/common-functions.sh" 2>/dev/null || {
    # Inline common functions if file doesn't exist
    log_info() { echo "[INFO] $1"; }
    log_warn() { echo "[WARN] $1"; }
    log_error() { echo "[ERROR] $1"; exit 1; }
}

connect_to_openbao() {
    log_info "Connecting to OpenBao..."
    
    # Start port-forward in background
    kubectl port-forward -n "$OPENBAO_NAMESPACE" svc/openbao 8200:8200 &
    PORTFORWARD_PID=$!
    
    # Wait for connection
    sleep 3
    
    # Export environment variables
    export VAULT_ADDR="http://localhost:8200"
    ROOT_TOKEN=$(kubectl get secret openbao-unseal-keys \
        -n "$OPENBAO_NAMESPACE" \
        -o jsonpath='{.data.root-token}' | base64 -d)
    export VAULT_TOKEN="$ROOT_TOKEN"
    
    log_info "Connected to OpenBao"
}

cleanup() {
    if [ -n "${PORTFORWARD_PID:-}" ]; then
        kill "$PORTFORWARD_PID" 2>/dev/null || true
    fi
}

trap cleanup EXIT

rotate_database_password() {
    log_info "Rotating database password..."
    
    # Generate new password
    NEW_PASSWORD=$(openssl rand -base64 32)
    
    # Get current database info
    DB_HOST=$(openbao kv get -field=host secret/ai-part-designer/database)
    DB_USER=$(openbao kv get -field=username secret/ai-part-designer/database)
    
    # Update password in database
    log_info "Updating password in PostgreSQL..."
    kubectl exec -n "$APP_NAMESPACE" \
        "$(kubectl get pod -n "$APP_NAMESPACE" -l app=postgres -o jsonpath='{.items[0].metadata.name}')" \
        -- psql -U postgres -c "ALTER USER $DB_USER WITH PASSWORD '$NEW_PASSWORD';"
    
    # Update in OpenBao (preserving other fields)
    log_info "Updating password in OpenBao..."
    openbao kv patch secret/ai-part-designer/database password="$NEW_PASSWORD"
    
    # Force sync to Kubernetes
    log_info "Forcing secret synchronization..."
    kubectl annotate externalsecret database-credentials \
        -n "$APP_NAMESPACE" \
        force-sync="$(date +%s)" \
        --overwrite
    
    # Wait for sync
    sleep 5
    
    # Rolling restart of services
    log_info "Restarting application services..."
    kubectl rollout restart deployment/api -n "$APP_NAMESPACE"
    kubectl rollout restart deployment/worker -n "$APP_NAMESPACE"
    
    # Wait for rollout
    kubectl rollout status deployment/api -n "$APP_NAMESPACE" --timeout=300s
    kubectl rollout status deployment/worker -n "$APP_NAMESPACE" --timeout=300s
    
    log_info "Database password rotated successfully"
}

rotate_redis_password() {
    log_info "Rotating Redis password..."
    
    NEW_PASSWORD=$(openssl rand -base64 32)
    
    # Update Redis password
    kubectl exec -n "$APP_NAMESPACE" \
        "$(kubectl get pod -n "$APP_NAMESPACE" -l app=redis -o jsonpath='{.items[0].metadata.name}')" \
        -- redis-cli CONFIG SET requirepass "$NEW_PASSWORD"
    
    # Update in OpenBao
    openbao kv patch secret/ai-part-designer/redis password="$NEW_PASSWORD"
    
    # Force sync and restart
    kubectl annotate externalsecret redis-credentials \
        -n "$APP_NAMESPACE" \
        force-sync="$(date +%s)" \
        --overwrite
    
    sleep 5
    
    kubectl rollout restart deployment/api -n "$APP_NAMESPACE"
    kubectl rollout restart deployment/worker -n "$APP_NAMESPACE"
    
    log_info "Redis password rotated successfully"
}

rotate_jwt_keys() {
    log_info "Rotating JWT signing keys..."
    
    NEW_SECRET=$(openssl rand -hex 32)
    
    # Update in OpenBao
    openbao kv patch secret/ai-part-designer/auth/jwt-keys secret_key="$NEW_SECRET"
    
    # Force sync
    kubectl annotate externalsecret auth-secrets \
        -n "$APP_NAMESPACE" \
        force-sync="$(date +%s)" \
        --overwrite
    
    sleep 5
    
    # Restart API (this will invalidate existing tokens)
    log_warn "⚠️  This will invalidate all existing JWT tokens - users will need to re-login"
    read -p "Continue? (yes/no) " -r
    if [[ ! $REPLY =~ ^[Yy]es$ ]]; then
        log_info "Rotation cancelled"
        return 0
    fi
    
    kubectl rollout restart deployment/api -n "$APP_NAMESPACE"
    kubectl rollout status deployment/api -n "$APP_NAMESPACE" --timeout=300s
    
    log_info "JWT keys rotated successfully"
}

rotate_all_secrets() {
    log_info "Rotating all secrets..."
    
    rotate_database_password
    rotate_redis_password
    rotate_jwt_keys
    
    log_info "All secrets rotated successfully"
}

audit_secret_age() {
    log_info "Auditing secret ages..."
    
    echo "Secret | Last Modified | Age (days)"
    echo "-------|---------------|------------"
    
    for path in $(openbao kv list -format=json secret/ai-part-designer/ 2>/dev/null | jq -r '.[]'); do
        metadata=$(openbao kv metadata get -format=json "secret/ai-part-designer/$path" 2>/dev/null)
        
        if [ -n "$metadata" ]; then
            updated_time=$(echo "$metadata" | jq -r '.updated_time')
            updated_epoch=$(date -d "$updated_time" +%s 2>/dev/null || echo "0")
            current_epoch=$(date +%s)
            age_days=$(( (current_epoch - updated_epoch) / 86400 ))
            
            echo "$path | $updated_time | $age_days"
        fi
    done
}

usage() {
    cat <<EOF
Secret Rotation Script for AI Part Designer

Usage: $0 [COMMAND]

Commands:
    database    Rotate database password
    redis       Rotate Redis password
    jwt         Rotate JWT signing keys
    all         Rotate all secrets
    audit       Show age of all secrets
    help        Show this help message

Examples:
    $0 database
    $0 all
    $0 audit

EOF
}

main() {
    local command="${1:-help}"
    
    case "$command" in
        database)
            connect_to_openbao
            rotate_database_password
            ;;
        redis)
            connect_to_openbao
            rotate_redis_password
            ;;
        jwt)
            connect_to_openbao
            rotate_jwt_keys
            ;;
        all)
            connect_to_openbao
            rotate_all_secrets
            ;;
        audit)
            connect_to_openbao
            audit_secret_age
            ;;
        help|--help|-h)
            usage
            ;;
        *)
            log_error "Unknown command: $command"
            usage
            ;;
    esac
}

main "$@"
