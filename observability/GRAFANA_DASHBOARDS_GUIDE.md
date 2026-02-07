# Grafana Dashboards Guide

This guide explains how to use the Grafana dashboards for monitoring the AI Part Designer platform.

## Overview

The monitoring stack provides two main dashboards:
1. **Part Designer - API Performance**: Application-level metrics
2. **Part Designer - Infrastructure**: System resource and dependency health

## Prerequisites

Ensure the observability stack is running:

```bash
# From project root
cd /home/runner/work/ai-part-designer/ai-part-designer

# Generate configurations (first time only)
cd observability/monitoring-setup
python3 dashboard_builder.py
python3 prometheus_builder.py
python3 grafana_provisioning_builder.py
cd ../..

# Start Prometheus and Grafana
docker compose -f docker-compose.yml -f docker-compose.observability.yml --profile observability up -d prometheus grafana
```

## Accessing Grafana

1. Open your browser to: **http://localhost:3000**
2. Log in with default credentials:
   - **Username**: `admin`
   - **Password**: `admin`
3. On first login, you'll be prompted to change the password

## Dashboard: Part Designer - API Performance

**Location**: Dashboards → Platform Monitoring → Part Designer - API Performance

### Metrics Sections

#### 1. Request Overview (Top Row)
- **Total Request Throughput**: Real-time requests per second
- **API Latency (95th Percentile)**: Response time for 95% of requests
  - 🟢 Green: < 0.5s (good)
  - 🟡 Yellow: 0.5-1.5s (acceptable)
  - 🔴 Red: > 1.5s (slow - investigate)
- **Server Error Percentage**: 5xx error rate
  - 🟢 Green: < 1% (healthy)
  - 🟡 Yellow: 1-3% (concerning)
  - 🔴 Red: > 3% (critical)
- **Concurrent Requests**: Number of requests being processed right now

#### 2. HTTP Traffic Analysis
- **Requests per Second by HTTP Status**: See 2xx, 4xx, 5xx patterns
  - Watch for spikes in 5xx (server errors)
  - 4xx spikes might indicate client issues or API misuse
- **Response Time Distribution**: P50, P90, P95, P99 latency
  - P50: Median user experience
  - P95: "Worst case" for most users
  - P99: Outliers (important for user satisfaction)

#### 3. CAD Generation Metrics
- **CAD Models Generated** (per minute by type): Track which templates are most popular
- **CAD Generation Time** (P90 by template): Identify slow templates
  - If P90 > 25s: Consider optimization
  - Compare templates to find bottlenecks

#### 4. File Export Operations
- **File Exports by Format and Status**: Success/error rates for STL, STEP, etc.
  - High error rates indicate format-specific issues

#### 5. AI Provider Integration
- **AI Provider Requests** (per minute): Track usage of Anthropic/OpenAI/etc.
  - Helps identify which providers are being used most
- **AI Token Usage Rate** (tokens per hour): Monitor costs
  - Input tokens: Data sent to AI
  - Output tokens: AI responses generated
  - Use this for cost forecasting

#### 6. User Activity
- **User Registrations and Logins**: Track platform growth
  - Distinguish between email, OAuth methods

### Common Use Cases

**Investigating Slow Responses**:
1. Check "API Latency (95th Percentile)" stat
2. Look at "Response Time Distribution" to see which percentiles are affected
3. Check "CAD Generation Time" - slow CAD operations often cause high latency
4. Review "AI Provider Requests" - AI calls can be slow

**Debugging Errors**:
1. Check "Server Error Percentage" stat
2. Look at "Requests per Second by HTTP Status" for error spikes
3. Check "File Exports by Format and Status" for export-specific errors
4. Review "CAD Models Generated" for generation failures

**Cost Monitoring**:
1. Check "AI Token Usage Rate" - multiply by provider pricing
2. Look for unusual spikes that might indicate runaway token consumption

## Dashboard: Part Designer - Infrastructure

**Location**: Dashboards → Platform Monitoring → Part Designer - Infrastructure

### Metrics Sections

#### 1. System Health Overview (Top Row)
- **Database Connection Pool Usage**: Percentage of connections in use
  - 🟢 Green: < 70% (healthy)
  - 🟡 Yellow: 70-85% (getting busy)
  - 🔴 Red: > 85% (nearing capacity - scale up)
- **Redis Cache Status**: Connected (green) / Disconnected (red)
- **Active Database Connections**: Number currently in use
- **Database Pool Overflow Count**: Connections beyond the pool limit
  - Any overflow indicates pool is too small or connections aren't being released

#### 2. Database Connection Pool Analysis
- **Database Connection Pool Metrics Over Time**:
  - Total Pool Size: Maximum connections configured
  - Connections In Use: Currently checked out
  - Connections Available: Ready for use
  - Overflow Connections: Beyond pool limit (bad sign)

**Interpreting the Chart**:
- "In Use" should be well below "Total Pool Size"
- If "In Use" approaches "Total Pool Size", increase pool size
- Any "Overflow" connections indicate a problem

#### 3. Redis Performance
- **Redis Operations per Minute**: Command execution rate by type
  - GET, SET, DEL, etc. - shows cache usage patterns
- **Redis Command Latency (P90)**: How long cache operations take
  - Should be < 10ms typically
  - Spikes indicate Redis performance issues

#### 4. Redis Health
- **Redis Connection Errors**: Rate of connection failures
  - Any errors indicate network or Redis stability issues

#### 5. Overall Health
- **Database Pool Health Score**: 100% = fully available, 0% = exhausted
  - This is essentially 100% minus the utilization percentage

### Common Use Cases

**Database Performance Issues**:
1. Check "Database Connection Pool Usage" - high usage can cause timeouts
2. Look at "Database Connection Pool Metrics Over Time" for trends
3. Check for "Overflow Connections" - indicates pool exhaustion
4. If consistently high: increase pool size in database configuration

**Cache Problems**:
1. Check "Redis Cache Status" - must be green
2. Look at "Redis Connection Errors" - any errors need investigation
3. Check "Redis Command Latency" - high latency affects app performance
4. Review "Redis Operations per Minute" - very low might mean cache isn't being used

**Capacity Planning**:
1. Monitor "Database Connection Pool Usage" over days/weeks
2. If trending upward, plan to increase pool size before hitting limits
3. Watch "Redis Operations per Minute" - rapid growth may require Redis scaling

## Alerting Rules

Prometheus is configured with alerts that trigger when thresholds are exceeded. These appear in the Grafana alerting interface and can be routed to notification channels.

**Configured Alerts**:
- **HighServerErrorRate**: API errors > 2.5% for 4 minutes
- **SlowAPILatency**: P95 latency > 1.5s for 6 minutes
- **CADGenerationFailureRate**: CAD failures > 12% for 10 minutes
- **SlowCADGeneration**: P90 generation time > 25s for 8 minutes
- **DatabasePoolHighUtilization**: Pool usage > 80% for 5 minutes
- **RedisDisconnected**: Redis not connected for 90 seconds
- **AIProviderErrorRate**: AI errors > 10% for 5 minutes
- **HighAITokenUsage**: > 150k tokens/hour for 45 minutes (cost alert)

## Customizing Dashboards

### Using the Dashboard Builder

The dashboards are generated programmatically. To customize:

1. Edit the dashboard builder:
```bash
cd observability/monitoring-setup
vim dashboard_builder.py
```

2. Add or modify panels in the relevant dashboard function:
   - `build_application_dashboard()` for API Performance
   - `build_infrastructure_dashboard()` for Infrastructure Health

3. Regenerate dashboards:
```bash
python3 dashboard_builder.py
```

4. Restart Grafana to reload:
```bash
docker compose -f docker-compose.yml -f docker-compose.observability.yml --profile observability restart grafana
```

### Example: Adding a Custom Panel

```python
# In dashboard_builder.py, inside build_application_dashboard()
dashboard.add_panel(PanelSpec(
    panel_id=99,  # Use a unique ID
    title="Designs Created per Hour",
    visualization_type="timeseries",
    queries=[MetricQuery(
        expression='sum(rate(designs_created_total[1h])) * 3600',
        legend_template="New Designs",
        ref_identifier="designs",
    )],
    x_position=0, y_position=50,  # Position on grid
    width=12, height=8,
    unit="short",  # Can be: short, percent, s, ops, etc.
    extra_config={"fill_opacity": 20},
))
```

## Tips and Best Practices

1. **Set Your Time Range**: Use the time picker (top right) to adjust the view
   - Last 6 hours: Good for current operations
   - Last 24 hours: Daily patterns
   - Last 7 days: Weekly trends

2. **Use Variables**: Dashboards support variables for filtering (if configured)

3. **Create Annotations**: Mark deployments or incidents as annotations to correlate with metric changes

4. **Export Dashboards**: After making UI changes, export via Settings → JSON Model

5. **Set Up Alerts**: Configure notification channels (Slack, email, PagerDuty) in Alerting → Notification Channels

6. **Refresh Interval**: Default is 30s - adjust in dashboard settings if needed

## Troubleshooting

### No Data Appearing

1. Check Prometheus is scraping:
   - Visit http://localhost:9090/targets
   - Ensure "part-designer-api" target is UP
   - Check "Last Scrape" time is recent

2. Verify backend is exposing metrics:
```bash
curl http://localhost:8000/metrics
```

3. Check Grafana datasource:
   - Settings → Data Sources → AIPartDesignerMetrics
   - Click "Test" button - should show "Data source is working"

### Dashboard Not Loading

1. Check Grafana logs:
```bash
docker logs ai-part-designer-grafana
```

2. Verify dashboard files are mounted:
```bash
docker exec ai-part-designer-grafana ls -la /etc/grafana/dashboards/
```

3. Regenerate and restart:
```bash
cd observability/monitoring-setup
python3 dashboard_builder.py
cd ../..
docker compose -f docker-compose.yml -f docker-compose.observability.yml --profile observability restart grafana
```

### Panels Showing "No Data"

1. Check the metric exists in Prometheus:
   - Visit http://localhost:9090
   - Go to Graph tab
   - Enter the metric name (e.g., `http_requests_total`)
   - Click "Execute"

2. Verify time range - some metrics may not have historical data

3. Check metric labels match the query - view raw metric in Prometheus to see available labels

## Further Reading

- [Prometheus Query Language (PromQL)](https://prometheus.io/docs/prometheus/latest/querying/basics/)
- [Grafana Dashboard Best Practices](https://grafana.com/docs/grafana/latest/dashboards/build-dashboards/best-practices/)
- Backend metrics documentation: `/backend/docs/prometheus-metrics.md`
