#!/bin/bash
# Helm chart validation script

set -e

CHART_DIR="./ai-part-designer"
TEMP_DIR=$(mktemp -d)

echo "==> Validating Helm chart structure..."

# Check required files exist
echo "Checking required files..."
required_files=(
    "$CHART_DIR/Chart.yaml"
    "$CHART_DIR/values.yaml"
    "$CHART_DIR/values-dev.yaml"
    "$CHART_DIR/values-staging.yaml"
    "$CHART_DIR/values-production.yaml"
    "$CHART_DIR/README.md"
    "$CHART_DIR/templates/_helpers.tpl"
    "$CHART_DIR/templates/NOTES.txt"
)

for file in "${required_files[@]}"; do
    if [[ ! -f "$file" ]]; then
        echo "ERROR: Required file missing: $file"
        exit 1
    fi
    echo "✓ $file"
done

echo ""
echo "==> Testing template rendering (dev)..."
helm template test-release "$CHART_DIR" \
    --values "$CHART_DIR/values-dev.yaml" \
    --set installPostgres=false \
    --set installRedis=false \
    --set installMinio=false \
    --set installVault=false \
    --set installIngress=false \
    --set installCerts=false \
    > "$TEMP_DIR/rendered-dev.yaml"
echo "✓ Dev templates render successfully ($(wc -l < "$TEMP_DIR/rendered-dev.yaml") lines)"

echo ""
echo "==> Testing template rendering (staging)..."
helm template test-release "$CHART_DIR" \
    --values "$CHART_DIR/values-staging.yaml" \
    --set installPostgres=false \
    --set installRedis=false \
    --set installMinio=false \
    --set installVault=false \
    --set installIngress=false \
    --set installCerts=false \
    > "$TEMP_DIR/rendered-staging.yaml"
echo "✓ Staging templates render successfully ($(wc -l < "$TEMP_DIR/rendered-staging.yaml") lines)"

echo ""
echo "==> Testing template rendering (production)..."
helm template test-release "$CHART_DIR" \
    --values "$CHART_DIR/values-production.yaml" \
    --set installPostgres=false \
    --set installRedis=false \
    --set installMinio=false \
    --set installVault=false \
    --set installIngress=false \
    --set installCerts=false \
    > "$TEMP_DIR/rendered-prod.yaml"
echo "✓ Production templates render successfully ($(wc -l < "$TEMP_DIR/rendered-prod.yaml") lines)"

echo ""
echo "==> Validating rendered manifests with kubectl..."
kubectl apply --dry-run=client -f "$TEMP_DIR/rendered-dev.yaml" > /dev/null
echo "✓ Dev manifests are valid Kubernetes resources"

kubectl apply --dry-run=client -f "$TEMP_DIR/rendered-staging.yaml" > /dev/null
echo "✓ Staging manifests are valid Kubernetes resources"

kubectl apply --dry-run=client -f "$TEMP_DIR/rendered-prod.yaml" > /dev/null
echo "✓ Production manifests are valid Kubernetes resources"

echo ""
echo "==> Checking Chart.yaml structure..."
helm show chart "$CHART_DIR"

echo ""
echo "==> Summary of generated resources:"
echo "Dev environment:"
grep "^kind:" "$TEMP_DIR/rendered-dev.yaml" | sort | uniq -c
echo ""
echo "Staging environment:"
grep "^kind:" "$TEMP_DIR/rendered-staging.yaml" | sort | uniq -c
echo ""
echo "Production environment:"
grep "^kind:" "$TEMP_DIR/rendered-prod.yaml" | sort | uniq -c

# Cleanup
rm -rf "$TEMP_DIR"

echo ""
echo "==> ✅ All validations passed!"
echo ""
echo "Next steps:"
echo "1. Run: helm dependency update $CHART_DIR"
echo "2. Install: helm install ai-part-designer $CHART_DIR -n ai-part-designer --create-namespace"
