# Observability Stack Configuration

This directory contains configuration files for the complete observability stack:
- **Prometheus** for metrics collection and storage
- **Grafana** for metrics visualization and dashboards
- **ELK Stack** (Elasticsearch, Logstash, Kibana) for centralized logging
- **Jaeger** for distributed tracing

## Directory Structure

```
observability/
├── monitoring-setup/              # Configuration generators (Python)
│   ├── dashboard_builder.py      # Generates Grafana dashboards
│   ├── prometheus_builder.py     # Generates Prometheus configs
│   └── grafana_provisioning_builder.py  # Generates Grafana provisioning
├── prometheus-config/             # Generated Prometheus configuration
│   ├── prometheus.yml            # Main Prometheus config
│   └── rules/
│       └── alerts.yml            # Alerting rules
├── grafana-dashboards/            # Generated Grafana dashboards
│   ├── application_performance.json
│   └── infrastructure_health.json
├── grafana-provisioning/          # Generated Grafana provisioning
│   ├── datasources/
│   │   └── prometheus.yml        # Prometheus datasource config
│   └── dashboards/
│       └── providers.yml         # Dashboard provider config
├── fluentd/
│   └── fluent.conf               # Fluentd log collection configuration
├── logstash/
│   └── ai-part-designer-pipeline.conf  # Alternative Logstash pipeline
├── kibana-setup/
│   ├── init-kibana.sh           # Kibana initialization script
│   └── dashboards.ndjson        # Pre-built dashboard definitions
└── elastic-config/
    └── (custom Elasticsearch configs if needed)
```

## Quick Start

See `/docs/operations/elk-stack-setup.md` for full logging documentation.
See `/docs/operations/distributed-tracing.md` for full tracing documentation.

### Generate Monitoring Configurations

Before starting the observability stack for the first time, generate the Prometheus and Grafana configurations:

```bash
cd observability/monitoring-setup

# Generate all configurations
python3 dashboard_builder.py
python3 prometheus_builder.py  
python3 grafana_provisioning_builder.py
```

This creates:
- Prometheus scrape configs and alerting rules
- Grafana dashboards for application and infrastructure metrics
- Grafana datasource and dashboard provisioning configs

### Start Full Observability Stack

Start all observability services (metrics, logging, tracing):

```bash
# From project root
docker compose -f docker-compose.yml -f docker-compose.observability.yml --profile observability up -d
```

This starts:
- **Prometheus** (port 9090) - Metrics collection and storage
- **Grafana** (port 3000) - Metrics visualization and dashboards
- **Elasticsearch** (port 9200) - Log storage
- **Kibana** (port 5601) - Log visualization
- **Logstash** (port 5044) - Log processing
- **Jaeger** (port 16686) - Tracing UI
  - Collector ports: 6831 (UDP), 14250 (gRPC), 4317 (OTLP)

### Start Metrics Stack Only

```bash
# From project root - Prometheus + Grafana only
docker compose -f docker-compose.yml -f docker-compose.observability.yml --profile observability up -d prometheus grafana
```

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

**Grafana (Metrics)**: Open http://localhost:3000 in your browser.
- Username: `admin`
- Password: `admin` (change on first login)
- Pre-loaded dashboards: "Part Designer - API Performance" and "Part Designer - Infrastructure"

**Prometheus (Raw Metrics)**: Open http://localhost:9090 in your browser.
- Explore metrics and test PromQL queries
- View configured alerting rules

**Kibana (Logs)**: Open http://localhost:5601 in your browser.

**Jaeger (Traces)**: Open http://localhost:16686 in your browser.

## Configuration Files

### Prometheus (metrics collection)
- **Auto-generated configuration** from `monitoring-setup/prometheus_builder.py`
- Scrapes metrics from:
  - Backend API (port 8000/metrics)
  - Celery workers (port 9808/metrics)
- **Alerting rules** configured for:
  - High API error rates (>2.5%)
  - Slow API latency (P95 > 1.5s)
  - CAD generation failures (>12%)
  - Database pool exhaustion (>80%)
  - Redis connectivity issues
  - AI provider errors

### Grafana (metrics visualization)
- **Auto-generated dashboards** from `monitoring-setup/dashboard_builder.py`
- **Application Performance Dashboard**:
  - Request throughput, latency percentiles, error rates
  - CAD generation metrics by template type
  - File export operations by format
  - AI request rates and token consumption
  - User registration and login activity
- **Infrastructure Health Dashboard**:
  - Database connection pool utilization and status
  - Redis connectivity, command latency, error rates
  - System component health scores

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

### Regenerating Monitoring Configurations

If you modify the application metrics or want to change dashboard layouts:

```bash
cd observability/monitoring-setup

# Edit the Python builders as needed
vim dashboard_builder.py       # Modify dashboard panels
vim prometheus_builder.py       # Modify scrape targets or alerts

# Regenerate configurations
python3 dashboard_builder.py
python3 prometheus_builder.py
python3 grafana_provisioning_builder.py

# Restart services to pick up changes
docker compose -f docker-compose.yml -f docker-compose.observability.yml --profile observability restart prometheus grafana
```

### Adding New Prometheus Scrape Targets

Edit `monitoring-setup/prometheus_builder.py` and add a new `ScrapeTarget`:

```python
builder.add_scrape_target(ScrapeTarget(
    job_identifier="my-new-service",
    target_addresses=["service:9100"],
    scrape_frequency="30s",
    labels={"tier": "backend", "component": "my-service"},
))
```

### Adding New Alert Rules

Edit `monitoring-setup/prometheus_builder.py` and add a new `AlertRule`:

```python
builder.add_alert_rule("my_alert_group", AlertRule(
    alert_name="MyCustomAlert",
    promql_expression="my_metric > 100",
    duration_threshold="5m",
    severity_level="warning",
    component_label="my-component",
    summary_text="Custom alert summary",
    description_text="Detailed description with {{ $value }}",
))
```

### Creating Custom Grafana Panels

Edit `monitoring-setup/dashboard_builder.py` and add panels to dashboards:

```python
dashboard.add_panel(PanelSpec(
    panel_id=99,
    title="My Custom Metric",
    visualization_type="timeseries",  # or "stat", "gauge", etc.
    queries=[MetricQuery(
        expression='rate(my_custom_metric[5m])',
        legend_template="{{label}}",
        ref_identifier="custom",
    )],
    x_position=0, y_position=40, width=12, height=8,
    unit="ops",
))
```

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
docker logs ai-part-designer-prometheus
docker logs ai-part-designer-grafana
docker logs ai-part-designer-fluentd
docker logs ai-part-designer-elasticsearch
docker logs ai-part-designer-kibana
docker logs ai-part-designer-jaeger
```

### Verify connectivity

**Prometheus:**
```bash
curl http://localhost:9090/-/healthy
curl http://localhost:9090/api/v1/targets  # Check scrape targets
curl http://localhost:9090/api/v1/rules    # Check alert rules
```

**Grafana:**
```bash
curl http://localhost:3000/api/health
```

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

### Grafana Dashboard Not Loading

If dashboards don't appear:
1. Check Grafana logs: `docker logs ai-part-designer-grafana`
2. Verify provisioning config: `docker exec ai-part-designer-grafana ls -la /etc/grafana/provisioning/dashboards`
3. Verify dashboard files: `docker exec ai-part-designer-grafana ls -la /etc/grafana/dashboards`
4. Regenerate configurations and restart

### Prometheus Not Scraping Metrics

If metrics aren't appearing:
1. Check targets status: http://localhost:9090/targets
2. Verify backend is exposing metrics: `curl http://localhost:8000/metrics`
3. Check Prometheus config: `docker exec ai-part-designer-prometheus cat /etc/prometheus/prometheus.yml`
4. Restart Prometheus: `docker compose -f docker-compose.yml -f docker-compose.observability.yml --profile observability restart prometheus`

## Production Notes

For production deployments:

**Prometheus:**
- Configure persistent volume for time-series data
- Set appropriate retention policies (default: 30 days)
- Enable remote write to long-term storage (Thanos, Cortex, etc.)
- Secure API endpoints with authentication
- Configure high-availability setup with multiple replicas
- Set up alertmanager for alert routing and notification

**Grafana:**
- Change default admin password immediately
- Configure OAuth or LDAP authentication
- Set up SMTP for alert notifications
- Use persistent volume for dashboard customizations
- Configure user roles and permissions
- Enable HTTPS/TLS
- Set up backup for dashboards and datasources

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
