# ELK Stack Observability Setup

## Overview

This document describes the ELK (Elasticsearch, Logstash, Kibana) stack setup for the AI Part Designer platform. The observability stack provides centralized log aggregation, search, and visualization capabilities.

## Architecture

```
┌──────────────┐      ┌──────────────┐      ┌──────────────┐      ┌──────────────┐
│   Backend    │      │   Worker     │      │  Frontend    │      │  Other       │
│   Services   │─────▶│   Services   │─────▶│  Container   │─────▶│  Services    │
└──────────────┘      └──────────────┘      └──────────────┘      └──────────────┘
       │                      │                      │                     │
       │              Structured JSON Logs (structlog format)              │
       │                      │                      │                     │
       └──────────────────────┴──────────────────────┴─────────────────────┘
                              │
                      ┌───────▼────────┐
                      │   Fluentd      │ ◀── Log Collection & Forwarding
                      │   (Primary)    │
                      └───────┬────────┘
                              │
                      ┌───────▼────────┐
                      │ Elasticsearch  │ ◀── Storage & Indexing
                      │  (Search DB)   │
                      └───────┬────────┘
                              │
                      ┌───────▼────────┐
                      │    Kibana      │ ◀── Visualization & Analysis
                      │   (Dashboard)  │
                      └────────────────┘
```

## Components

### Elasticsearch
- **Purpose**: Stores and indexes all application logs
- **Port**: 9200 (HTTP), 9300 (Transport)
- **Index Pattern**: `ai-part-designer-YYYY.MM.DD`
- **Configuration**: `observability/elastic-config/`

### Kibana
- **Purpose**: Web interface for searching and visualizing logs
- **Port**: 5601
- **URL**: http://localhost:5601
- **Dashboards**: Pre-configured for common queries

### Fluentd (Primary Log Shipper)
- **Purpose**: Collects logs from Docker containers and forwards to Elasticsearch
- **Ports**: 24224 (Forward Protocol)
- **Configuration**: `observability/fluentd/fluent.conf`
- **Why Fluentd**: Lightweight, Ruby-based, flexible routing

### Logstash (Alternative)
- **Purpose**: Alternative log processor with more complex transformations
- **Port**: 5044 (Beats), 9600 (Monitoring)
- **Configuration**: `observability/logstash/ai-part-designer-pipeline.conf`
- **When to use**: Need complex data transformations or filtering

## Quick Start

### Local Development

1. **Start infrastructure and application**:
   ```bash
   docker compose up -d
   ```

2. **Start observability stack**:
   ```bash
   docker compose -f docker-compose.yml -f docker-compose.observability.yml --profile observability up -d
   ```

3. **Wait for services to be healthy** (check with `docker compose ps`)

4. **Initialize Kibana** (creates index patterns and dashboards):
   ```bash
   ./observability/kibana-setup/init-kibana.sh
   ```

5. **Access Kibana**:
   Open http://localhost:5601 in your browser

### Verify Log Collection

1. **Check Elasticsearch indices**:
   ```bash
   curl http://localhost:9200/_cat/indices?v
   ```

   You should see indices like: `ai-part-designer-YYYY.MM.DD` (e.g., `ai-part-designer-2026.02.06`)

2. **Query recent logs**:
   ```bash
   curl -X GET "http://localhost:9200/ai-part-designer-*/_search?pretty" \
     -H 'Content-Type: application/json' \
     -d '{"size": 10, "sort": [{"@timestamp": {"order": "desc"}}]}'
   ```

3. **Check Fluentd logs**:
   ```bash
   docker logs ai-part-designer-fluentd
   ```

## Kibana Usage

### Index Pattern
The default index pattern is `ai-part-designer-*` which matches all daily indices.

### Common Searches

#### Find API Errors
```
level:error AND logger:app.api.*
```

#### Track User Activity
```
user_id:"<user-uuid>" AND request_id:*
```

#### CAD Generation Performance
```
logger:app.cad.* AND duration_ms:*
```

#### Find Slow Requests (>1s)
```
duration_ms:>1000
```

#### Track Design Operations
```
design_id:"<design-uuid>"
```

### Time Ranges
- Use the time picker (top right) to select time ranges
- Recommended: Last 15 minutes (auto-refresh every 30s)

### Saved Searches

Pre-configured searches available in Kibana:
1. **API Requests by Endpoint** - All API activity grouped by path
2. **CAD Generation Performance** - Performance metrics for CAD operations
3. **Application Errors** - All error and critical logs
4. **User Activity Trace** - User actions with request correlation

## Log Format

The application uses `structlog` which outputs JSON logs in production. Each log entry contains:

### Standard Fields
- `@timestamp`: ISO 8601 timestamp in UTC
- `level`: Log level (debug, info, warning, error, critical)
- `event`: Event name (e.g., "design_created", "cad_generation_started")
- `logger`: Python module name (e.g., "app.api.v1.designs")
- `app_name`: "ai-part-designer"
- `environment`: "development" or "production"

### Request Context (when available)
- `request_id`: Unique request identifier for tracing
- `user_id`: Authenticated user UUID
- `path`: API endpoint path
- `method`: HTTP method

### Application-Specific Fields
- `design_id`: Design entity identifier
- `user_id`: User entity identifier
- `duration_ms`: Operation duration in milliseconds
- `error_type`: Python exception class name
- `template_id`: CAD template identifier
- Custom fields based on the event type

### Example Log Entry
```json
{
  "@timestamp": "2024-01-15T10:30:45.123456Z",
  "level": "info",
  "event": "design_created",
  "logger": "app.services.design",
  "app_name": "ai-part-designer",
  "environment": "production",
  "request_id": "XyZ789AbC123",
  "user_id": "user-456",
  "path": "/api/v1/designs",
  "method": "POST",
  "design_id": "123e4567-e89b-12d3-a456-426614174000",
  "template_id": "template-abc"
}
```

## Production Deployment

### Resource Requirements

Minimum recommendations for production:

- **Elasticsearch**: 4GB RAM, 2 CPU cores, 50GB disk
- **Kibana**: 2GB RAM, 1 CPU core
- **Fluentd**: 512MB RAM, 0.5 CPU cores
- **Total**: ~7GB RAM, 3.5 CPU cores

### Security Hardening

For production deployments:

1. **Enable Elasticsearch security**:
   ```yaml
   environment:
     - xpack.security.enabled=true
     - ELASTIC_PASSWORD=<strong-password>
   ```

2. **Configure TLS/SSL**:
   - Generate certificates for Elasticsearch nodes
   - Enable HTTPS for Kibana
   - Configure Fluentd to use secure connections

3. **Network isolation**:
   - Use internal Docker networks
   - Only expose Kibana port (5601) to users
   - Restrict Elasticsearch access to internal services

4. **Authentication**:
   - Enable Kibana authentication
   - Create read-only users for viewing logs
   - Create admin users for configuration

### Backup and Retention

1. **Index Lifecycle Management (ILM)**:
   ```json
   {
     "policy": {
       "phases": {
         "hot": {
           "actions": {}
         },
         "warm": {
           "min_age": "7d",
           "actions": {
             "shrink": { "number_of_shards": 1 }
           }
         },
         "delete": {
           "min_age": "30d",
           "actions": { "delete": {} }
         }
       }
     }
   }
   ```

2. **Snapshot backups**:
   - Configure snapshot repository
   - Schedule daily snapshots
   - Retain snapshots for 90 days

### Performance Tuning

1. **Adjust JVM heap** based on available memory:
   ```yaml
   environment:
     - "ES_JAVA_OPTS=-Xms4g -Xmx4g"  # Half of available RAM
   ```

2. **Configure Fluentd buffer**:
   ```conf
   <buffer>
     chunk_limit_size 5M
     flush_interval 10s
     retry_max_times 5
   </buffer>
   ```

3. **Optimize index settings**:
   ```json
   {
     "number_of_shards": 3,
     "number_of_replicas": 1,
     "refresh_interval": "30s"
   }
   ```

## Troubleshooting

### Logs Not Appearing in Kibana

1. **Check Fluentd is running**:
   ```bash
   docker ps | grep fluentd
   ```

2. **Verify Fluentd can reach Elasticsearch**:
   ```bash
   docker exec ai-part-designer-fluentd curl -f http://elasticsearch:9200
   ```

3. **Check for JSON parsing errors**:
   ```bash
   docker logs ai-part-designer-fluentd | grep ERROR
   ```

4. **Verify application is logging**:
   ```bash
   docker logs ai-part-designer-api | head -20
   ```

### Elasticsearch Out of Memory

1. **Increase heap size** in `docker-compose.observability.yml`:
   ```yaml
   - "ES_JAVA_OPTS=-Xms1g -Xmx1g"
   ```

2. **Clear old indices**:
   ```bash
   curl -X DELETE "http://localhost:9200/ai-part-designer-2024.01.*"
   ```

### Kibana Not Loading

1. **Check Elasticsearch is healthy**:
   ```bash
   curl http://localhost:9200/_cluster/health
   ```

2. **Restart Kibana**:
   ```bash
   docker compose -f docker-compose.observability.yml restart kibana
   ```

3. **Check Kibana logs**:
   ```bash
   docker logs ai-part-designer-kibana
   ```

### High Disk Usage

1. **Check index sizes**:
   ```bash
   curl http://localhost:9200/_cat/indices?v&h=index,store.size
   ```

2. **Delete old indices manually**:
   ```bash
   curl -X DELETE "http://localhost:9200/ai-part-designer-2024.01.01"
   ```

3. **Implement ILM policy** (see Production Deployment section)

## Monitoring the ELK Stack

### Health Checks

```bash
# Elasticsearch cluster health
curl http://localhost:9200/_cluster/health?pretty

# Node stats
curl http://localhost:9200/_nodes/stats?pretty

# Kibana status
curl http://localhost:5601/api/status
```

### Metrics to Watch

1. **Elasticsearch**:
   - Cluster status (green/yellow/red)
   - JVM heap usage
   - Query latency
   - Index rate

2. **Fluentd**:
   - Buffer queue length
   - Retry counts
   - Output errors

3. **Disk Space**:
   - Elasticsearch data volume usage
   - Fluentd buffer volume usage

## Alternative: Using Logstash

If you prefer Logstash over Fluentd:

1. **Start with Logstash profile**:
   ```bash
   docker compose -f docker-compose.yml -f docker-compose.observability.yml --profile observability --profile logstash up -d
   ```

2. **Configure application to send logs to Logstash**:
   Update your logging configuration to send to `logstash:5044`

3. **Monitor Logstash**:
   ```bash
   curl http://localhost:9600/_node/stats/pipelines?pretty
   ```

## References

- [Elasticsearch Documentation](https://www.elastic.co/guide/en/elasticsearch/reference/current/index.html)
- [Kibana Guide](https://www.elastic.co/guide/en/kibana/current/index.html)
- [Fluentd Documentation](https://docs.fluentd.org/)
- [Structlog Documentation](https://www.structlog.org/)
- Backend logging configuration: `backend/app/core/logging.py`
- Logging guide: `backend/docs/structured-logging.md`
