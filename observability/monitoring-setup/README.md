# Monitoring Configuration Generators

This directory contains Python scripts that programmatically generate monitoring configurations for the AI Part Designer platform.

## Why Python Generators?

Rather than maintaining static YAML/JSON configuration files, we use Python to:
- Ensure consistency across Prometheus and Grafana configs
- Make it easy to add new metrics by editing code rather than hand-crafting JSON
- Generate dashboard panels automatically based on application metrics
- Reduce configuration errors through type-safe dataclasses
- Enable version control and code review of monitoring changes

## Scripts

### `dashboard_builder.py`

Generates Grafana dashboard JSON files.

**Output**:
- `../grafana-dashboards/application_performance.json`
- `../grafana-dashboards/infrastructure_health.json`

**What it creates**:
- Application Performance Dashboard: 12 panels covering API, CAD, exports, AI, users
- Infrastructure Health Dashboard: 10 panels covering DB pool, Redis, system health

**Key classes**:
- `MetricQuery`: Represents a PromQL query
- `PanelSpec`: Defines a dashboard panel (visualization, queries, layout)
- `DashboardGenerator`: Builds complete dashboard JSON

**Usage**:
```bash
python3 dashboard_builder.py
```

**Customization example**:
```python
# Add a new panel to application dashboard
dashboard.add_panel(PanelSpec(
    panel_id=13,
    title="User Sessions Active",
    visualization_type="stat",
    queries=[MetricQuery(
        expression='sum(active_user_sessions)',
        ref_identifier="sessions",
    )],
    x_position=0, y_position=37, width=6, height=5,
    unit="short",
))
```

### `prometheus_builder.py`

Generates Prometheus configuration files.

**Output**:
- `../prometheus-config/prometheus.yml`
- `../prometheus-config/rules/alerts.yml`

**What it creates**:
- Scrape configurations for backend API, Celery workers, Prometheus self-monitoring
- Alert rules for API health, CAD generation, infrastructure, AI integration

**Key classes**:
- `ScrapeTarget`: Defines a metrics endpoint to scrape
- `AlertRule`: Defines a Prometheus alerting rule
- `PrometheusConfigBuilder`: Assembles complete Prometheus configuration

**Usage**:
```bash
python3 prometheus_builder.py
```

**Customization example**:
```python
# Add a new scrape target
builder.add_scrape_target(ScrapeTarget(
    job_identifier="frontend-metrics",
    target_addresses=["frontend:3001"],
    scrape_frequency="30s",
    labels={"tier": "frontend", "component": "react-app"},
))

# Add a new alert
builder.add_alert_rule("custom_alerts", AlertRule(
    alert_name="HighMemoryUsage",
    promql_expression="process_resident_memory_bytes > 1e9",
    duration_threshold="10m",
    severity_level="warning",
    component_label="backend",
    summary_text="Backend memory usage is high",
    description_text="Memory usage is {{ $value | humanize }}B",
))
```

### `grafana_provisioning_builder.py`

Generates Grafana provisioning configuration files.

**Output**:
- `../grafana-provisioning/datasources/prometheus.yml`
- `../grafana-provisioning/dashboards/providers.yml`

**What it creates**:
- Datasource configuration linking Grafana to Prometheus
- Dashboard provider configuration for auto-loading dashboards

**Usage**:
```bash
python3 grafana_provisioning_builder.py
```

## Workflow

### Initial Setup

1. Generate all configurations:
```bash
cd observability/monitoring-setup
python3 dashboard_builder.py
python3 prometheus_builder.py
python3 grafana_provisioning_builder.py
```

2. Start the monitoring stack:
```bash
cd ../..
docker compose -f docker-compose.yml -f docker-compose.observability.yml --profile observability up -d prometheus grafana
```

3. Access Grafana at http://localhost:3000 (admin/admin)

### Making Changes

When you add new metrics to the application or want to modify dashboards:

1. Edit the relevant builder script:
   - `dashboard_builder.py` for new panels or dashboards
   - `prometheus_builder.py` for new scrape targets or alerts
   - `grafana_provisioning_builder.py` for datasource changes

2. Regenerate configurations:
```bash
python3 <script_name>.py
```

3. Restart affected services:
```bash
# For dashboard changes
docker compose -f ../../docker-compose.yml -f ../../docker-compose.observability.yml --profile observability restart grafana

# For Prometheus changes
docker compose -f ../../docker-compose.yml -f ../../docker-compose.observability.yml --profile observability restart prometheus
```

## Configuration Reference

### Panel Visualization Types

The `dashboard_builder.py` supports these visualization types:

- **timeseries**: Line/area charts for metrics over time
- **stat**: Single-value display with optional sparkline
- **gauge**: Semi-circle gauge with thresholds
- **table**: Tabular data display
- **heatmap**: Color-coded matrix (not currently used)
- **bargauge**: Horizontal/vertical bar gauges

### PromQL Examples

Common patterns used in the dashboards:

```promql
# Request rate
sum(rate(http_requests_total[2m]))

# Error rate percentage
100 * (sum(rate(http_requests_total{status=~"5.."}[5m])) / sum(rate(http_requests_total[5m])))

# P95 latency
histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket[5m])) by (le))

# Operations per minute
sum by (label) (rate(metric_total[5m])) * 60

# Pool utilization
(db_pool_checked_out_connections / db_pool_size) * 100
```

### Alert Severity Levels

Used in `prometheus_builder.py`:

- **critical**: Immediate action required (page on-call)
- **warning**: Degraded performance, investigate soon
- **info**: Informational, no immediate action needed

### Panel Units

Common units for `PanelSpec`:

- `short`: Generic numbers (1234)
- `percent`: Percentage (0-100)
- `s`, `ms`: Time duration
- `reqps`, `ops`, `rpm`, `cpm`: Rates
- `bytes`, `kbytes`, `mbytes`: Data sizes
- `errors/min`: Error rates

## Extending the Generators

### Adding a New Dashboard

In `dashboard_builder.py`:

```python
def build_my_new_dashboard() -> DashboardGenerator:
    """Build a custom dashboard."""
    dashboard = DashboardGenerator(
        "My Custom Dashboard",
        "my_dashboard_uid"
    )
    
    # Add panels...
    dashboard.add_panel(PanelSpec(...))
    
    return dashboard

# In __main__:
if __name__ == "__main__":
    # ... existing dashboards ...
    
    custom_dashboard = build_my_new_dashboard()
    custom_dashboard.save_to_file(output_dir / "my_custom_dashboard.json")
```

### Adding Alert Groups

In `prometheus_builder.py`:

```python
# Create a new alert group
builder.add_alert_rule("my_custom_alerts", AlertRule(
    alert_name="MyAlert",
    promql_expression="my_metric > 100",
    duration_threshold="5m",
    severity_level="warning",
    component_label="my-component",
    summary_text="My metric is high",
    description_text="Value: {{ $value }}",
))

builder.add_alert_rule("my_custom_alerts", AlertRule(
    # ... another alert in the same group ...
))
```

## Testing

Before committing changes:

1. Validate generated YAML:
```bash
python3 -c "import yaml; yaml.safe_load(open('../prometheus-config/prometheus.yml')); print('✓ Valid')"
```

2. Validate generated JSON:
```bash
python3 -c "import json; json.load(open('../grafana-dashboards/application_performance.json')); print('✓ Valid')"
```

3. Test in Prometheus:
```bash
# Check config syntax
docker exec ai-part-designer-prometheus promtool check config /etc/prometheus/prometheus.yml

# Check alert rules
docker exec ai-part-designer-prometheus promtool check rules /etc/prometheus/rules/alerts.yml
```

4. Test in Grafana:
   - Import generated dashboard JSON via UI
   - Verify all panels load without errors
   - Check that metrics are being displayed

## Dependencies

These scripts require:
- Python 3.11+
- PyYAML (for YAML generation)
- Standard library: json, pathlib, dataclasses, typing

Install dependencies:
```bash
pip install pyyaml
```

## Maintenance

When adding new metrics to the application:

1. Document metrics in `/backend/docs/prometheus-metrics.md`
2. Add visualization panels in `dashboard_builder.py`
3. Add relevant alerts in `prometheus_builder.py`
4. Regenerate configurations
5. Test the new panels/alerts
6. Commit all generated files along with the builder changes

This ensures monitoring stays in sync with application changes.
