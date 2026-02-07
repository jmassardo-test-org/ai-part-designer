#!/usr/bin/env python3
"""
Custom dashboard builder for AI Part Designer metrics visualization.
Generates Grafana dashboard configurations programmatically based on
the application's specific metrics schema.
"""

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class MetricQuery:
    """Represents a PromQL query for a specific metric."""
    
    expression: str
    legend_template: str = ""
    ref_identifier: str = ""


@dataclass
class PanelSpec:
    """Specification for a Grafana panel."""
    
    panel_id: int
    title: str
    visualization_type: str
    queries: list[MetricQuery]
    x_position: int = 0
    y_position: int = 0
    width: int = 12
    height: int = 8
    unit: str = "short"
    extra_config: dict[str, Any] = field(default_factory=dict)


class DashboardGenerator:
    """Generates Grafana dashboards for AI Part Designer monitoring."""
    
    def __init__(self, dashboard_name: str, uid_prefix: str):
        self.dashboard_name = dashboard_name
        self.uid = f"{uid_prefix}_{hash(dashboard_name) % 100000}"
        self.panels: list[PanelSpec] = []
        
    def add_panel(self, spec: PanelSpec) -> None:
        """Add a panel to the dashboard."""
        self.panels.append(spec)
        
    def _build_target(self, query: MetricQuery, index: int) -> dict[str, Any]:
        """Convert MetricQuery to Grafana target format."""
        target = {
            "expr": query.expression,
            "refId": query.ref_identifier or f"query_{index}",
            "interval": "",
            "legendFormat": query.legend_template,
        }
        return target
    
    def _build_panel(self, spec: PanelSpec) -> dict[str, Any]:
        """Convert PanelSpec to Grafana panel JSON."""
        base_panel = {
            "id": spec.panel_id,
            "type": spec.visualization_type,
            "title": spec.title,
            "gridPos": {
                "h": spec.height,
                "w": spec.width,
                "x": spec.x_position,
                "y": spec.y_position,
            },
            "targets": [
                self._build_target(q, idx) 
                for idx, q in enumerate(spec.queries)
            ],
            "datasource": {"type": "prometheus", "uid": "${DS_PROMETHEUS}"},
        }
        
        # Add visualization-specific configs
        if spec.visualization_type == "timeseries":
            base_panel["fieldConfig"] = {
                "defaults": {
                    "unit": spec.unit,
                    "custom": {
                        "drawStyle": "line",
                        "lineInterpolation": "linear",
                        "barAlignment": 0,
                        "fillOpacity": spec.extra_config.get("fill_opacity", 25),
                        "showPoints": "never",
                        "pointSize": 5,
                        "stacking": {"mode": "none"},
                        "axisPlacement": "auto",
                    },
                },
            }
            base_panel["options"] = {
                "legend": {
                    "showLegend": True,
                    "displayMode": spec.extra_config.get("legend_mode", "list"),
                    "placement": spec.extra_config.get("legend_placement", "bottom"),
                    "calcs": spec.extra_config.get("legend_calcs", []),
                },
                "tooltip": {"mode": "multi", "sort": "none"},
            }
        elif spec.visualization_type == "stat":
            base_panel["fieldConfig"] = {
                "defaults": {
                    "unit": spec.unit,
                    "decimals": spec.extra_config.get("decimals", 2),
                    "thresholds": spec.extra_config.get("thresholds", {
                        "mode": "absolute",
                        "steps": [{"value": 0, "color": "green"}],
                    }),
                },
            }
            base_panel["options"] = {
                "reduceOptions": {
                    "values": False,
                    "calcs": ["lastNotNull"],
                },
                "orientation": "auto",
                "textMode": spec.extra_config.get("text_mode", "auto"),
                "colorMode": spec.extra_config.get("color_mode", "value"),
                "graphMode": spec.extra_config.get("graph_mode", "area"),
            }
        elif spec.visualization_type == "gauge":
            base_panel["fieldConfig"] = {
                "defaults": {
                    "unit": spec.unit,
                    "min": spec.extra_config.get("min", 0),
                    "max": spec.extra_config.get("max", 100),
                    "thresholds": spec.extra_config.get("thresholds", {
                        "mode": "absolute",
                        "steps": [
                            {"value": 0, "color": "green"},
                            {"value": 80, "color": "yellow"},
                            {"value": 90, "color": "red"},
                        ],
                    }),
                },
            }
            base_panel["options"] = {
                "showThresholdLabels": False,
                "showThresholdMarkers": True,
            }
            
        return base_panel
    
    def generate(self) -> dict[str, Any]:
        """Generate the complete dashboard JSON."""
        return {
            "dashboard": {
                "title": self.dashboard_name,
                "uid": self.uid,
                "tags": ["ai-part-designer", "auto-generated"],
                "timezone": "browser",
                "editable": True,
                "graphTooltip": 1,
                "refresh": "30s",
                "time": {"from": "now-6h", "to": "now"},
                "timepicker": {
                    "refresh_intervals": ["10s", "30s", "1m", "5m"],
                },
                "panels": [self._build_panel(p) for p in self.panels],
                "schemaVersion": 38,
            },
            "overwrite": True,
        }
    
    def save_to_file(self, output_path: Path) -> None:
        """Save dashboard to JSON file."""
        dashboard_json = self.generate()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w') as f:
            json.dump(dashboard_json, f, indent=2)


def build_application_dashboard() -> DashboardGenerator:
    """Build the application performance dashboard."""
    dashboard = DashboardGenerator(
        "Part Designer - API Performance",
        "pd_api_perf"
    )
    
    # Request throughput stat
    dashboard.add_panel(PanelSpec(
        panel_id=1,
        title="Total Request Throughput",
        visualization_type="stat",
        queries=[MetricQuery(
            expression='sum(rate(http_requests_total{job="part-designer-api"}[2m]))',
            ref_identifier="throughput",
        )],
        x_position=0, y_position=0, width=6, height=5,
        unit="reqps",
        extra_config={"decimals": 1, "color_mode": "value"},
    ))
    
    # P95 latency stat
    dashboard.add_panel(PanelSpec(
        panel_id=2,
        title="API Latency (95th Percentile)",
        visualization_type="stat",
        queries=[MetricQuery(
            expression='histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket{job="part-designer-api"}[5m])) by (le))',
            ref_identifier="p95",
        )],
        x_position=6, y_position=0, width=6, height=5,
        unit="s",
        extra_config={
            "decimals": 3,
            "thresholds": {
                "mode": "absolute",
                "steps": [
                    {"value": 0, "color": "green"},
                    {"value": 0.5, "color": "yellow"},
                    {"value": 1.5, "color": "red"},
                ],
            },
        },
    ))
    
    # Error percentage stat
    dashboard.add_panel(PanelSpec(
        panel_id=3,
        title="Server Error Percentage",
        visualization_type="stat",
        queries=[MetricQuery(
            expression='100 * (sum(rate(http_requests_total{status=~"5..",job="part-designer-api"}[5m])) / sum(rate(http_requests_total{job="part-designer-api"}[5m])))',
            ref_identifier="errors",
        )],
        x_position=12, y_position=0, width=6, height=5,
        unit="percent",
        extra_config={
            "decimals": 2,
            "thresholds": {
                "mode": "absolute",
                "steps": [
                    {"value": 0, "color": "green"},
                    {"value": 1, "color": "yellow"},
                    {"value": 3, "color": "red"},
                ],
            },
        },
    ))
    
    # In-progress requests
    dashboard.add_panel(PanelSpec(
        panel_id=4,
        title="Concurrent Requests",
        visualization_type="stat",
        queries=[MetricQuery(
            expression='sum(http_requests_inprogress{job="part-designer-api"})',
            ref_identifier="concurrent",
        )],
        x_position=18, y_position=0, width=6, height=5,
        unit="short",
        extra_config={"decimals": 0, "graph_mode": "area"},
    ))
    
    # HTTP status code distribution
    dashboard.add_panel(PanelSpec(
        panel_id=5,
        title="Requests per Second by HTTP Status",
        visualization_type="timeseries",
        queries=[MetricQuery(
            expression='sum by (status) (rate(http_requests_total{job="part-designer-api"}[2m]))',
            legend_template="HTTP {{status}}",
            ref_identifier="by_status",
        )],
        x_position=0, y_position=5, width=12, height=8,
        unit="reqps",
        extra_config={
            "fill_opacity": 20,
            "legend_mode": "table",
            "legend_placement": "right",
            "legend_calcs": ["mean", "last", "max"],
        },
    ))
    
    # Latency percentiles over time
    dashboard.add_panel(PanelSpec(
        panel_id=6,
        title="Response Time Distribution",
        visualization_type="timeseries",
        queries=[
            MetricQuery(
                expression='histogram_quantile(0.50, sum(rate(http_request_duration_seconds_bucket{job="part-designer-api"}[5m])) by (le))',
                legend_template="50th percentile",
                ref_identifier="p50",
            ),
            MetricQuery(
                expression='histogram_quantile(0.90, sum(rate(http_request_duration_seconds_bucket{job="part-designer-api"}[5m])) by (le))',
                legend_template="90th percentile",
                ref_identifier="p90",
            ),
            MetricQuery(
                expression='histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket{job="part-designer-api"}[5m])) by (le))',
                legend_template="95th percentile",
                ref_identifier="p95",
            ),
            MetricQuery(
                expression='histogram_quantile(0.99, sum(rate(http_request_duration_seconds_bucket{job="part-designer-api"}[5m])) by (le))',
                legend_template="99th percentile",
                ref_identifier="p99",
            ),
        ],
        x_position=12, y_position=5, width=12, height=8,
        unit="s",
        extra_config={"fill_opacity": 0, "legend_mode": "list"},
    ))
    
    # CAD generation rate by template
    dashboard.add_panel(PanelSpec(
        panel_id=7,
        title="CAD Models Generated (per minute by type)",
        visualization_type="timeseries",
        queries=[MetricQuery(
            expression='sum by (template_type) (rate(cad_generations_total[5m])) * 60',
            legend_template="{{template_type}}",
            ref_identifier="cad_rate",
        )],
        x_position=0, y_position=13, width=12, height=8,
        unit="cpm",
        extra_config={
            "fill_opacity": 30,
            "legend_mode": "table",
            "legend_placement": "right",
            "legend_calcs": ["mean", "max"],
        },
    ))
    
    # CAD generation duration
    dashboard.add_panel(PanelSpec(
        panel_id=8,
        title="CAD Generation Time (P90 by template)",
        visualization_type="timeseries",
        queries=[MetricQuery(
            expression='histogram_quantile(0.90, sum by (template_type, le) (rate(cad_generation_duration_seconds_bucket[10m])))',
            legend_template="{{template_type}} (P90)",
            ref_identifier="cad_duration",
        )],
        x_position=12, y_position=13, width=12, height=8,
        unit="s",
        extra_config={
            "fill_opacity": 0,
            "legend_mode": "table",
            "legend_placement": "right",
            "legend_calcs": ["mean", "last"],
        },
    ))
    
    # Export operations
    dashboard.add_panel(PanelSpec(
        panel_id=9,
        title="File Exports by Format and Status",
        visualization_type="timeseries",
        queries=[MetricQuery(
            expression='sum by (format, status) (rate(exports_total[5m])) * 60',
            legend_template="{{format}} - {{status}}",
            ref_identifier="exports",
        )],
        x_position=0, y_position=21, width=12, height=8,
        unit="ops/min",
        extra_config={"fill_opacity": 25},
    ))
    
    # AI request rate
    dashboard.add_panel(PanelSpec(
        panel_id=10,
        title="AI Provider Requests (per minute)",
        visualization_type="timeseries",
        queries=[MetricQuery(
            expression='sum by (provider, model) (rate(ai_requests_total[5m])) * 60',
            legend_template="{{provider}}/{{model}}",
            ref_identifier="ai_rate",
        )],
        x_position=12, y_position=21, width=12, height=8,
        unit="rpm",
        extra_config={
            "fill_opacity": 15,
            "legend_mode": "table",
            "legend_placement": "right",
            "legend_calcs": ["mean", "last"],
        },
    ))
    
    # AI token consumption
    dashboard.add_panel(PanelSpec(
        panel_id=11,
        title="AI Token Usage Rate (tokens per hour)",
        visualization_type="timeseries",
        queries=[MetricQuery(
            expression='sum by (provider, token_type) (rate(ai_tokens_used_total[1h])) * 3600',
            legend_template="{{provider}} {{token_type}}",
            ref_identifier="tokens",
        )],
        x_position=0, y_position=29, width=12, height=8,
        unit="short",
        extra_config={"fill_opacity": 20},
    ))
    
    # User activity
    dashboard.add_panel(PanelSpec(
        panel_id=12,
        title="User Registrations and Logins (10-min window)",
        visualization_type="timeseries",
        queries=[
            MetricQuery(
                expression='sum by (method) (rate(user_registrations_total[10m])) * 600',
                legend_template="Registrations via {{method}}",
                ref_identifier="registrations",
            ),
            MetricQuery(
                expression='sum by (method) (rate(user_logins_total{status="success"}[10m])) * 600',
                legend_template="Logins via {{method}}",
                ref_identifier="logins",
            ),
        ],
        x_position=12, y_position=29, width=12, height=8,
        unit="short",
        extra_config={"fill_opacity": 25, "decimals": 1},
    ))
    
    return dashboard


def build_infrastructure_dashboard() -> DashboardGenerator:
    """Build the infrastructure health dashboard."""
    dashboard = DashboardGenerator(
        "Part Designer - Infrastructure",
        "pd_infrastructure"
    )
    
    # DB pool utilization percentage
    dashboard.add_panel(PanelSpec(
        panel_id=1,
        title="Database Connection Pool Usage",
        visualization_type="stat",
        queries=[MetricQuery(
            expression='100 * (db_pool_checked_out_connections / db_pool_size)',
            ref_identifier="pool_pct",
        )],
        x_position=0, y_position=0, width=6, height=6,
        unit="percent",
        extra_config={
            "decimals": 1,
            "thresholds": {
                "mode": "absolute",
                "steps": [
                    {"value": 0, "color": "green"},
                    {"value": 70, "color": "yellow"},
                    {"value": 85, "color": "red"},
                ],
            },
        },
    ))
    
    # Redis connectivity
    dashboard.add_panel(PanelSpec(
        panel_id=2,
        title="Redis Cache Status",
        visualization_type="stat",
        queries=[MetricQuery(
            expression='redis_connected',
            ref_identifier="redis_up",
        )],
        x_position=6, y_position=0, width=6, height=6,
        unit="short",
        extra_config={
            "text_mode": "value",
            "color_mode": "background",
            "thresholds": {
                "mode": "absolute",
                "steps": [
                    {"value": 0, "color": "red"},
                    {"value": 1, "color": "green"},
                ],
            },
        },
    ))
    
    # Active connections
    dashboard.add_panel(PanelSpec(
        panel_id=3,
        title="Active Database Connections",
        visualization_type="stat",
        queries=[MetricQuery(
            expression='db_pool_checked_out_connections',
            ref_identifier="active",
        )],
        x_position=12, y_position=0, width=6, height=6,
        unit="short",
        extra_config={"decimals": 0, "graph_mode": "area"},
    ))
    
    # Pool overflow
    dashboard.add_panel(PanelSpec(
        panel_id=4,
        title="Database Pool Overflow Count",
        visualization_type="stat",
        queries=[MetricQuery(
            expression='db_pool_overflow_connections',
            ref_identifier="overflow",
        )],
        x_position=18, y_position=0, width=6, height=6,
        unit="short",
        extra_config={
            "decimals": 0,
            "thresholds": {
                "mode": "absolute",
                "steps": [
                    {"value": 0, "color": "green"},
                    {"value": 1, "color": "yellow"},
                    {"value": 5, "color": "red"},
                ],
            },
        },
    ))
    
    # DB pool over time
    dashboard.add_panel(PanelSpec(
        panel_id=5,
        title="Database Connection Pool Metrics Over Time",
        visualization_type="timeseries",
        queries=[
            MetricQuery(
                expression='db_pool_size',
                legend_template="Total Pool Size",
                ref_identifier="size",
            ),
            MetricQuery(
                expression='db_pool_checked_out_connections',
                legend_template="Connections In Use",
                ref_identifier="out",
            ),
            MetricQuery(
                expression='db_pool_checkedin_connections',
                legend_template="Connections Available",
                ref_identifier="in",
            ),
            MetricQuery(
                expression='db_pool_overflow_connections',
                legend_template="Overflow Connections",
                ref_identifier="overflow_ts",
            ),
        ],
        x_position=0, y_position=6, width=12, height=10,
        unit="short",
        extra_config={
            "fill_opacity": 15,
            "legend_mode": "list",
            "legend_placement": "bottom",
        },
    ))
    
    # Redis command rate
    dashboard.add_panel(PanelSpec(
        panel_id=6,
        title="Redis Operations per Minute (by command)",
        visualization_type="timeseries",
        queries=[MetricQuery(
            expression='sum by (command) (rate(redis_commands_total{status="success"}[3m])) * 60',
            legend_template="{{command}}",
            ref_identifier="redis_ops",
        )],
        x_position=12, y_position=6, width=12, height=10,
        unit="ops/min",
        extra_config={
            "fill_opacity": 20,
            "legend_mode": "table",
            "legend_placement": "right",
            "legend_calcs": ["mean", "max"],
        },
    ))
    
    # Redis latency
    dashboard.add_panel(PanelSpec(
        panel_id=7,
        title="Redis Command Latency (P90)",
        visualization_type="timeseries",
        queries=[MetricQuery(
            expression='histogram_quantile(0.90, sum by (command, le) (rate(redis_command_duration_seconds_bucket[5m])))',
            legend_template="{{command}}",
            ref_identifier="redis_lat",
        )],
        x_position=0, y_position=16, width=12, height=8,
        unit="s",
        extra_config={
            "fill_opacity": 0,
            "decimals": 4,
            "legend_mode": "table",
            "legend_placement": "right",
            "legend_calcs": ["mean", "last"],
        },
    ))
    
    # Redis errors
    dashboard.add_panel(PanelSpec(
        panel_id=8,
        title="Redis Connection Errors (per minute)",
        visualization_type="timeseries",
        queries=[MetricQuery(
            expression='rate(redis_connection_errors_total[5m]) * 60',
            legend_template="Connection Errors",
            ref_identifier="redis_errs",
        )],
        x_position=12, y_position=16, width=12, height=8,
        unit="errors/min",
        extra_config={"fill_opacity": 30},
    ))
    
    # DB health gauge
    dashboard.add_panel(PanelSpec(
        panel_id=9,
        title="Database Pool Health Score",
        visualization_type="gauge",
        queries=[MetricQuery(
            expression='100 - (100 * (db_pool_checked_out_connections / db_pool_size))',
            ref_identifier="health",
        )],
        x_position=0, y_position=24, width=24, height=8,
        unit="percent",
        extra_config={
            "min": 0,
            "max": 100,
            "thresholds": {
                "mode": "absolute",
                "steps": [
                    {"value": 0, "color": "red"},
                    {"value": 20, "color": "yellow"},
                    {"value": 50, "color": "green"},
                ],
            },
        },
    ))
    
    return dashboard


if __name__ == "__main__":
    output_dir = Path(__file__).parent.parent / "grafana-dashboards"
    
    app_dashboard = build_application_dashboard()
    app_dashboard.save_to_file(output_dir / "application_performance.json")
    print(f"✓ Generated: application_performance.json")
    
    infra_dashboard = build_infrastructure_dashboard()
    infra_dashboard.save_to_file(output_dir / "infrastructure_health.json")
    print(f"✓ Generated: infrastructure_health.json")
    
    print(f"\nDashboards saved to: {output_dir}")
