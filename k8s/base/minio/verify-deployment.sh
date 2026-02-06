#!/bin/bash
# MinIO Deployment Verification Script
# Usage: ./verify-minio-deployment.sh

set -e

NAMESPACE="ai-part-designer"
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "========================================="
echo "MinIO Deployment Verification"
echo "========================================="
echo ""

# Function to check and print status
check_status() {
    local description=$1
    local command=$2
    local expected=$3
    
    echo -n "Checking $description... "
    if output=$(eval "$command" 2>&1); then
        if [[ -z "$expected" ]] || [[ "$output" == *"$expected"* ]]; then
            echo -e "${GREEN}✓${NC}"
            return 0
        else
            echo -e "${RED}✗${NC}"
            echo "  Expected: $expected"
            echo "  Got: $output"
            return 1
        fi
    else
        echo -e "${RED}✗${NC}"
        echo "  Error: $output"
        return 1
    fi
}

# Function to wait for condition
wait_for() {
    local description=$1
    local command=$2
    local max_wait=${3:-300}
    
    echo -n "Waiting for $description... "
    local elapsed=0
    while ! eval "$command" > /dev/null 2>&1; do
        if [ $elapsed -ge $max_wait ]; then
            echo -e "${RED}✗ Timeout${NC}"
            return 1
        fi
        sleep 5
        elapsed=$((elapsed + 5))
    done
    echo -e "${GREEN}✓${NC} (${elapsed}s)"
    return 0
}

echo "1. Pre-flight Checks"
echo "-------------------"
check_status "Kubernetes connection" "kubectl cluster-info" "Kubernetes"
check_status "Namespace exists" "kubectl get namespace $NAMESPACE" ""
echo ""

echo "2. OpenBao Integration"
echo "---------------------"
check_status "OpenBao SecretStore" "kubectl get secretstore openbao-secret-store -n $NAMESPACE" "openbao-secret-store"
check_status "MinIO credentials ExternalSecret" "kubectl get externalsecret minio-credentials -n $NAMESPACE" "minio-credentials"
check_status "MinIO app credentials ExternalSecret" "kubectl get externalsecret minio-app-credentials -n $NAMESPACE" "minio-app-credentials"
check_status "MinIO mc config ExternalSecret" "kubectl get externalsecret minio-mc-config -n $NAMESPACE" "minio-mc-config"
echo ""

echo "3. MinIO Deployment"
echo "------------------"
check_status "StatefulSet created" "kubectl get statefulset minio -n $NAMESPACE" "minio"
check_status "Service created" "kubectl get service minio -n $NAMESPACE" "minio"
check_status "ServiceMonitor created" "kubectl get servicemonitor minio -n $NAMESPACE" "minio"
check_status "NetworkPolicy created" "kubectl get networkpolicy minio-ingress -n $NAMESPACE" "minio-ingress"
echo ""

echo "4. MinIO Pod Status"
echo "------------------"
wait_for "MinIO pod to be running" "kubectl get pod minio-0 -n $NAMESPACE -o jsonpath='{.status.phase}' | grep -q Running" 120
check_status "Pod ready" "kubectl get pod minio-0 -n $NAMESPACE -o jsonpath='{.status.conditions[?(@.type==\"Ready\")].status}'" "True"

# Check container status
CONTAINER_STATUS=$(kubectl get pod minio-0 -n $NAMESPACE -o jsonpath='{.status.containerStatuses[0].ready}' 2>/dev/null || echo "false")
if [[ "$CONTAINER_STATUS" == "true" ]]; then
    echo -e "${GREEN}✓${NC} Container ready"
else
    echo -e "${RED}✗${NC} Container not ready"
    kubectl describe pod minio-0 -n $NAMESPACE | tail -20
fi
echo ""

echo "5. PersistentVolumeClaim"
echo "------------------------"
check_status "PVC created" "kubectl get pvc data-minio-0 -n $NAMESPACE" "data-minio-0"
PVC_STATUS=$(kubectl get pvc data-minio-0 -n $NAMESPACE -o jsonpath='{.status.phase}')
if [[ "$PVC_STATUS" == "Bound" ]]; then
    echo -e "${GREEN}✓${NC} PVC bound"
    PVC_SIZE=$(kubectl get pvc data-minio-0 -n $NAMESPACE -o jsonpath='{.status.capacity.storage}')
    echo "  Storage: $PVC_SIZE"
else
    echo -e "${RED}✗${NC} PVC not bound (status: $PVC_STATUS)"
fi
echo ""

echo "6. Secrets Synced"
echo "----------------"
check_status "MinIO credentials secret" "kubectl get secret minio-credentials -n $NAMESPACE" "minio-credentials"
check_status "MinIO app credentials secret" "kubectl get secret minio-app-credentials -n $NAMESPACE" "minio-app-credentials"
check_status "Backend secrets" "kubectl get secret backend-secrets -n $NAMESPACE" "backend-secrets"
check_status "Celery worker secrets" "kubectl get secret celery-worker-secrets -n $NAMESPACE" "celery-worker-secrets"
echo ""

echo "7. MinIO Health Checks"
echo "---------------------"
# Port-forward for health check
kubectl port-forward -n $NAMESPACE svc/minio 9000:9000 > /dev/null 2>&1 &
PF_PID=$!
sleep 3

if curl -f -s http://localhost:9000/minio/health/live > /dev/null 2>&1; then
    echo -e "${GREEN}✓${NC} Liveness check passed"
else
    echo -e "${RED}✗${NC} Liveness check failed"
fi

if curl -f -s http://localhost:9000/minio/health/ready > /dev/null 2>&1; then
    echo -e "${GREEN}✓${NC} Readiness check passed"
else
    echo -e "${RED}✗${NC} Readiness check failed"
fi

kill $PF_PID 2>/dev/null || true
echo ""

echo "8. Bucket Initialization"
echo "------------------------"
JOB_STATUS=$(kubectl get job minio-init-buckets -n $NAMESPACE -o jsonpath='{.status.conditions[?(@.type=="Complete")].status}' 2>/dev/null || echo "")
if [[ "$JOB_STATUS" == "True" ]]; then
    echo -e "${GREEN}✓${NC} Initialization job completed"
else
    echo -e "${YELLOW}⚠${NC} Initialization job not complete yet"
    echo "  Run: kubectl logs job/minio-init-buckets -n $NAMESPACE"
fi
echo ""

echo "9. Application Integration"
echo "-------------------------"
# Check backend pods have storage env vars
BACKEND_POD=$(kubectl get pod -n $NAMESPACE -l app.kubernetes.io/name=backend -o jsonpath='{.items[0].metadata.name}' 2>/dev/null || echo "")
if [[ -n "$BACKEND_POD" ]]; then
    check_status "Backend has STORAGE_BACKEND env" "kubectl exec $BACKEND_POD -n $NAMESPACE -- env | grep STORAGE_BACKEND" "minio"
    check_status "Backend has S3_ENDPOINT_URL env" "kubectl exec $BACKEND_POD -n $NAMESPACE -- env | grep S3_ENDPOINT_URL" "minio:9000"
    check_status "Backend has AWS credentials env" "kubectl exec $BACKEND_POD -n $NAMESPACE -- env | grep AWS_ACCESS_KEY_ID" ""
else
    echo -e "${YELLOW}⚠${NC} Backend pod not found (may not be deployed yet)"
fi
echo ""

echo "10. Network Connectivity"
echo "-----------------------"
if [[ -n "$BACKEND_POD" ]]; then
    if kubectl exec $BACKEND_POD -n $NAMESPACE -- curl -f -s http://minio:9000/minio/health/live > /dev/null 2>&1; then
        echo -e "${GREEN}✓${NC} Backend can reach MinIO"
    else
        echo -e "${RED}✗${NC} Backend cannot reach MinIO"
    fi
else
    echo -e "${YELLOW}⚠${NC} Backend pod not available for network test"
fi
echo ""

echo "11. Prometheus Metrics"
echo "---------------------"
kubectl port-forward -n $NAMESPACE svc/minio 9000:9000 > /dev/null 2>&1 &
PF_PID=$!
sleep 2

if curl -f -s http://localhost:9000/minio/v2/metrics/cluster | grep -q "minio_"; then
    echo -e "${GREEN}✓${NC} Metrics endpoint available"
    METRIC_COUNT=$(curl -s http://localhost:9000/minio/v2/metrics/cluster | grep "^minio_" | wc -l)
    echo "  Metrics exposed: $METRIC_COUNT"
else
    echo -e "${RED}✗${NC} Metrics endpoint not available"
fi

kill $PF_PID 2>/dev/null || true
echo ""

echo "========================================="
echo "Verification Complete!"
echo "========================================="
echo ""
echo "Next steps:"
echo "1. Access MinIO Console: kubectl port-forward -n $NAMESPACE svc/minio 9001:9001"
echo "   Then open: http://localhost:9001"
echo ""
echo "2. Create app user (if not already done):"
echo "   See: k8s/base/minio/README.md#step-6-create-application-user-in-minio"
echo ""
echo "3. Test storage operations from application:"
echo "   kubectl exec -it -n $NAMESPACE deployment/backend -- python -c \\"
echo "     \"from app.core.storage import storage_client, StorageBucket; import asyncio; \\"
echo "     asyncio.run(storage_client.upload_file(StorageBucket.TEMP, 'test.txt', b'Hello MinIO!'))\""
echo ""
