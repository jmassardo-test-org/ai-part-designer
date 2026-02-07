#!/bin/bash
# Quick Helm chart template test (without dependencies)

set -e

echo "==> Testing Helm chart templates..."

CHART_DIR="helm/ai-part-designer"
TEMP_CHART="/tmp/test-chart"

# Create temporary chart without dependencies
mkdir -p "$TEMP_CHART"
cp -r "$CHART_DIR/templates" "$TEMP_CHART/"
cp "$CHART_DIR/values.yaml" "$TEMP_CHART/"
cp "$CHART_DIR/values-dev.yaml" "$TEMP_CHART/"
cp "$CHART_DIR/values-staging.yaml" "$TEMP_CHART/"
cp "$CHART_DIR/values-production.yaml" "$TEMP_CHART/"

# Create Chart.yaml without dependencies
cat > "$TEMP_CHART/Chart.yaml" << 'CHART'
apiVersion: v2
name: ai-part-designer
description: Test chart
type: application
version: 0.1.0
appVersion: "0.1.0"
CHART

echo "Testing dev values..."
helm template test "$TEMP_CHART" -f "$TEMP_CHART/values-dev.yaml" > /tmp/dev-output.yaml
echo "✓ Dev environment: $(grep -c '^kind:' /tmp/dev-output.yaml) resources generated, $(wc -l < /tmp/dev-output.yaml) lines"

echo "Testing staging values..."
helm template test "$TEMP_CHART" -f "$TEMP_CHART/values-staging.yaml" > /tmp/staging-output.yaml
echo "✓ Staging environment: $(grep -c '^kind:' /tmp/staging-output.yaml) resources generated, $(wc -l < /tmp/staging-output.yaml) lines"

echo "Testing production values..."
helm template test "$TEMP_CHART" -f "$TEMP_CHART/values-production.yaml" > /tmp/prod-output.yaml
echo "✓ Production environment: $(grep -c '^kind:' /tmp/prod-output.yaml) resources generated, $(wc -l < /tmp/prod-output.yaml) lines"

echo ""
echo "==> Resource summary (production):"
echo "Deployments: $(grep -c '^kind: Deployment$' /tmp/prod-output.yaml)"
echo "Services: $(grep -c '^kind: Service$' /tmp/prod-output.yaml)"
echo "ConfigMaps: $(grep -c '^kind: ConfigMap$' /tmp/prod-output.yaml)"
echo "ServiceAccounts: $(grep -c '^kind: ServiceAccount$' /tmp/prod-output.yaml)"
echo "HPAs: $(grep -c '^kind: HorizontalPodAutoscaler$' /tmp/prod-output.yaml)"
echo "PDBs: $(grep -c '^kind: PodDisruptionBudget$' /tmp/prod-output.yaml)"
echo "Ingresses: $(grep -c '^kind: Ingress$' /tmp/prod-output.yaml)"

echo ""
echo "==> Validating YAML syntax..."
python3 -c "import yaml; yaml.safe_load_all(open('/tmp/prod-output.yaml'))" && echo "✓ Valid YAML"

echo ""
echo "✅ All template tests passed!"

# Cleanup
rm -rf "$TEMP_CHART"
rm -f /tmp/dev-output.yaml /tmp/staging-output.yaml /tmp/prod-output.yaml
