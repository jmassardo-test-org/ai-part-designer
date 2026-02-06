# Observability Stack Configuration

This directory contains configuration files for the ELK (Elasticsearch, Logstash, Kibana) observability stack.

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

See `/docs/operations/elk-stack-setup.md` for full documentation.

### Start ELK Stack

```bash
# From project root
docker compose -f docker-compose.yml -f docker-compose.observability.yml --profile observability up -d
```

### Initialize Kibana

```bash
# Wait for services to be healthy, then run:
./observability/kibana-setup/init-kibana.sh
```

### Access Kibana

Open http://localhost:5601 in your browser.

## Configuration Files

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

Check service logs:
```bash
docker logs ai-part-designer-fluentd
docker logs ai-part-designer-elasticsearch
docker logs ai-part-designer-kibana
```

Verify connectivity:
```bash
# Check Elasticsearch
curl http://localhost:9200/_cluster/health

# Check indices
curl http://localhost:9200/_cat/indices?v
```

## Production Notes

For production deployments:
- Enable Elasticsearch security (xpack.security)
- Configure TLS/SSL certificates
- Set up proper authentication
- Implement index lifecycle management
- Configure backups

See full documentation at `/docs/operations/elk-stack-setup.md`
