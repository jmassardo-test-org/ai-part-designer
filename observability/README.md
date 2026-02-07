# Observability Stack Configuration

This directory contains configuration files for the observability stack:
- **ELK Stack** (Elasticsearch, Logstash, Kibana) for centralized logging
- **Jaeger** for distributed tracing
- **Prometheus & Grafana** for metrics (configured separately)

## Directory Structure

```
observability/
├── fluentd/
│   └── fluent.conf              # Fluentd log collection configuration
├── logstash/
│   └── ai-part-designer-pipeline.conf  # Alternative Logstash pipeline
├── kibana-setup/
│   ├── init-kibana.sh          # Kibana initialization script
│   └── dashboards.ndjson       # Pre-built dashboard definitions
└── elastic-config/
    └── (custom Elasticsearch configs if needed)
```

## Quick Start

See `/docs/operations/elk-stack-setup.md` for full logging documentation.
See `/docs/operations/distributed-tracing.md` for full tracing documentation.

### Start Full Observability Stack

Start ELK + Jaeger together:

```bash
# From project root - start all observability services
docker compose -f docker-compose.yml -f docker-compose.observability.yml --profile observability up -d
```

This starts:
- **Elasticsearch** (port 9200) - Log storage
- **Kibana** (port 5601) - Log visualization
- **Logstash** (port 5044) - Log processing
- **Jaeger** (port 16686) - Tracing UI
  - Collector ports: 6831 (UDP), 14250 (gRPC), 4317 (OTLP)

### Start ELK Stack Only

```bash
# From project root - logging only
docker compose -f docker-compose.yml -f docker-compose.observability.yml --profile observability up -d elasticsearch kibana logstash
```

### Start Jaeger Only

```bash
# From project root - tracing only
docker compose -f docker-compose.yml -f docker-compose.observability.yml --profile observability up -d jaeger
```

### Initialize Kibana

```bash
# Wait for services to be healthy, then run:
./observability/kibana-setup/init-kibana.sh
```

### Access Services

**Kibana (Logs)**: Open http://localhost:5601 in your browser.

**Jaeger (Traces)**: Open http://localhost:16686 in your browser.

## Configuration Files

### Jaeger (distributed tracing)
- **All-in-one deployment** for development
- Includes collector, query, and UI components
- Supports multiple protocols: UDP, gRPC, OTLP, Zipkin
- In-memory storage (for development)
- See `/docs/operations/distributed-tracing.md` for configuration

### Fluentd (fluent.conf)
- Collects logs from Docker containers
- Filters and enriches log data
- Forwards to Elasticsearch
- Primary log shipper for this application

### Logstash (ai-part-designer-pipeline.conf)
- Alternative to Fluentd
- Processes structured JSON logs
- Includes custom filters for application-specific fields
- Use when you need more complex transformations

### Kibana Setup
- `init-kibana.sh`: Creates default index patterns
- `dashboards.ndjson`: Saved searches and dashboard configurations

## Customization

### Adding Custom Fluentd Filters

Edit `fluentd/fluent.conf` and add filters between the `<filter>` tags:

```conf
<filter docker.ai-part-designer-**>
  @type record_transformer
  <record>
    custom_field "custom_value"
  </record>
</filter>
```

### Creating Custom Kibana Dashboards

1. Create dashboards in the Kibana UI
2. Export from Management → Saved Objects
3. Save to `kibana-setup/dashboards.ndjson`

### Elasticsearch Index Templates

Place custom index templates in `elastic-config/` and they will be loaded on startup.

## Troubleshooting

### Check service logs
```bash
docker logs ai-part-designer-fluentd
docker logs ai-part-designer-elasticsearch
docker logs ai-part-designer-kibana
docker logs ai-part-designer-jaeger
```

### Verify connectivity

**Elasticsearch:**
```bash
curl http://localhost:9200/_cluster/health
curl http://localhost:9200/_cat/indices?v
```

**Jaeger:**
```bash
curl http://localhost:14269/  # Admin endpoint
curl http://localhost:16686/  # UI endpoint
```

## Production Notes

For production deployments:

**ELK Stack:**
- Enable Elasticsearch security (xpack.security)
- Configure TLS/SSL certificates
- Set up proper authentication
- Implement index lifecycle management
- Configure backups

**Jaeger:**
- Use persistent storage (Cassandra, Elasticsearch, or BadgerDB)
- Enable authentication for Jaeger UI
- Configure trace sampling (1-10% for high-traffic)
- Set up horizontal scaling for collector
- Implement trace retention policies

See full documentation:
- `/docs/operations/elk-stack-setup.md` - Logging setup
- `/docs/operations/distributed-tracing.md` - Tracing setup
- `/docs/operations/monitoring-alerting.md` - Metrics and alerting
