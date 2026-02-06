#!/bin/bash
# Kibana Setup Script for AI Part Designer
# Creates index patterns and imports dashboards

set -e

KIBANA_URL="${KIBANA_URL:-http://localhost:5601}"
ES_URL="${ES_URL:-http://localhost:9200}"

echo "Waiting for Kibana to be ready..."
until curl -sf "${KIBANA_URL}/api/status" > /dev/null; do
  echo "Kibana not ready yet, waiting..."
  sleep 5
done

echo "Kibana is ready! Setting up index patterns..."

# Create index pattern for AI Part Designer logs
curl -X POST "${KIBANA_URL}/api/saved_objects/index-pattern/ai-part-designer-*" \
  -H 'kbn-xsrf: true' \
  -H 'Content-Type: application/json' \
  -d '{
  "attributes": {
    "title": "ai-part-designer-*",
    "timeFieldName": "@timestamp"
  }
}'

echo ""
echo "Setting default index pattern..."
curl -X POST "${KIBANA_URL}/api/kibana/settings/defaultIndex" \
  -H 'kbn-xsrf: true' \
  -H 'Content-Type: application/json' \
  -d '{"value": "ai-part-designer-*"}'

echo ""
echo "Kibana setup complete!"
echo "Access Kibana at: ${KIBANA_URL}"
