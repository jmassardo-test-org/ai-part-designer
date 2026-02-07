# Grafana Dashboards - Quick Start

Get Grafana dashboards up and running in 5 minutes.

## Step 1: Generate Configurations

```bash
cd observability/monitoring-setup
python3 dashboard_builder.py
python3 prometheus_builder.py
python3 grafana_provisioning_builder.py
cd ../..
```

Expected output:
```
✓ Generated: application_performance.json
✓ Generated: infrastructure_health.json
✓ Generated: prometheus.yml
✓ Generated: rules/alerts.yml
✓ Generated: datasources/prometheus.yml
✓ Generated: dashboards/providers.yml
```

## Step 2: Start the Monitoring Stack

```bash
docker compose -f docker-compose.yml -f docker-compose.observability.yml --profile observability up -d prometheus grafana
```

Wait for services to be healthy (~30 seconds):
```bash
docker ps --filter "name=prometheus|grafana" --format "table {{.Names}}\t{{.Status}}"
```

## Step 3: Access Grafana

1. Open browser to: **http://localhost:3000**
2. Login with:
   - Username: `admin`
   - Password: `admin`
3. Change password when prompted (or skip for dev)

## Step 4: View Dashboards

Click **Dashboards** (left sidebar) → **Platform Monitoring** folder

You'll see two dashboards:
- **Part Designer - API Performance**
- **Part Designer - Infrastructure**

## What You'll See

### Application Performance Dashboard
- Request throughput and latency
- Error rates by HTTP status
- CAD generation metrics
- AI provider usage
- User activity

### Infrastructure Health Dashboard
- Database connection pool status
- Redis cache health
- System component connectivity

## Verify Metrics Are Flowing

1. Open Prometheus: **http://localhost:9090**
2. Go to **Status** → **Targets**
3. Verify `part-designer-api` shows as **UP**
4. If backend isn't running, metrics will be empty

## Troubleshooting

**No data in dashboards?**
```bash
# Check if backend is exposing metrics
curl http://localhost:8000/metrics

# Verify Prometheus can reach backend
docker exec ai-part-designer-prometheus wget -q0- http://backend:8000/metrics
```

**Dashboards not appearing?**
```bash
# Check Grafana logs
docker logs ai-part-designer-grafana | grep -i dashboard

# Verify files are mounted
docker exec ai-part-designer-grafana ls -l /etc/grafana/dashboards/
```

**"Datasource not found" error?**
```bash
# Restart Grafana
docker compose -f docker-compose.yml -f docker-compose.observability.yml --profile observability restart grafana
```

## Next Steps

- Read the [Grafana Dashboards Guide](./GRAFANA_DASHBOARDS_GUIDE.md) for detailed dashboard usage
- Check [Monitoring Setup README](./monitoring-setup/README.md) to customize dashboards
- Configure alerting channels in Grafana (Alerting → Notification channels)

## Stopping the Monitoring Stack

```bash
docker compose -f docker-compose.yml -f docker-compose.observability.yml --profile observability stop prometheus grafana
```

## Complete Cleanup

```bash
# Stop and remove containers + volumes
docker compose -f docker-compose.yml -f docker-compose.observability.yml --profile observability down -v
```

⚠️ This deletes all Prometheus time-series data and Grafana customizations!
