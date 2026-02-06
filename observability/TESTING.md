# ELK Stack Testing Guide

This document describes how to test the ELK stack setup.

## Prerequisites

The ELK stack must be running:
```bash
make elk-up
make elk-init
```

## Test 1: Send a Test Log Entry

Send a test JSON log to Logstash:

```bash
echo '{"timestamp": "2026-02-06T03:15:00.000000Z", "level": "info", "event": "test_event", "logger": "test.script", "app_name": "ai-part-designer", "environment": "development", "message": "Test log entry"}' | nc localhost 5044
```

## Test 2: Verify Log in Elasticsearch

Check that the log was indexed:

```bash
curl -s http://localhost:9200/_cat/indices?v | grep ai-part-designer
```

Query the logs:

```bash
curl -s "http://localhost:9200/ai-part-designer-*/_search?pretty" | grep -A 20 '"hits"'
```

## Test 3: Search in Kibana

1. Open Kibana: http://localhost:5601
2. Go to "Discover" (hamburger menu → Analytics → Discover)
3. Select the `ai-part-designer-*` index pattern
4. You should see your test log entries

## Test 4: Verify with Running Application

Start the main application to generate real logs:

```bash
# In one terminal
docker compose up -d api

# Wait for it to start, then check logs are being collected
sleep 30
curl "http://localhost:9200/ai-part-designer-*/_search?q=logger:app.*&pretty" | head -50
```

## Test 5: Search Examples in Kibana

Try these searches in Kibana's Discover view:

1. **All logs**: `*`
2. **Error logs**: `level:error`
3. **API logs**: `logger:app.api.*`
4. **Specific event**: `event:"design_created"`
5. **User activity**: `user_id:* AND request_id:*`

## Expected Results

After running the tests:

- ✅ Elasticsearch should have indices named `ai-part-designer-YYYY.MM.DD`
- ✅ Kibana Discover should show logs with proper timestamps
- ✅ Log fields should be searchable (level, logger, event, etc.)
- ✅ Kibana visualizations should work

## Troubleshooting

### No logs appearing

1. Check Logstash is running:
   ```bash
   docker ps | grep logstash
   ```

2. Check Logstash logs for errors:
   ```bash
   docker logs ai-part-designer-logstash
   ```

3. Verify Elasticsearch is healthy:
   ```bash
   curl http://localhost:9200/_cluster/health
   ```

### Kibana not loading

1. Wait 30-60 seconds after starting for initialization
2. Check Kibana logs:
   ```bash
   docker logs ai-part-designer-kibana
   ```

3. Verify Kibana can reach Elasticsearch:
   ```bash
   curl http://localhost:5601/api/status | jq '.status.overall'
   ```

## Performance Testing

To generate load for testing:

```bash
# Send 100 test logs
for i in {1..100}; do
  echo "{\"timestamp\": \"$(date -u +%Y-%m-%dT%H:%M:%S.000000Z)\", \"level\": \"info\", \"event\": \"load_test_$i\", \"logger\": \"test.script\", \"app_name\": \"ai-part-designer\", \"environment\": \"development\", \"iteration\": $i}" | nc localhost 5044
  sleep 0.1
done

# Check document count
curl "http://localhost:9200/ai-part-designer-*/_count?pretty"
```

## Cleanup

To remove test data:

```bash
# Delete test indices
curl -X DELETE "http://localhost:9200/ai-part-designer-*"

# Stop ELK stack
make elk-down
```
