#!/usr/bin/env python3
"""
Configuration generator for Prometheus monitoring in AI Part Designer.
Creates scrape configs and alerting rules programmatically.
"""

import yaml
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class ScrapeTarget:
    """Defines a metrics scraping endpoint."""
    
    job_identifier: str
    target_addresses: list[str]
    scrape_path: str = "/metrics"
    scrape_frequency: str = "15s"
    timeout: str = "10s"
    labels: dict[str, str] = field(default_factory=dict)
    relabel_rules: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class AlertRule:
    """Defines a Prometheus alerting rule."""
    
    alert_name: str
    promql_expression: str
    duration_threshold: str
    severity_level: str
    component_label: str
    summary_text: str
    description_text: str


class PrometheusConfigBuilder:
    """Builds Prometheus configuration for the AI Part Designer stack."""
    
    def __init__(self):
        self.scrape_targets: list[ScrapeTarget] = []
        self.alert_groups: dict[str, list[AlertRule]] = {}
        
    def add_scrape_target(self, target: ScrapeTarget) -> None:
        """Register a new scrape target."""
        self.scrape_targets.append(target)
        
    def add_alert_rule(self, group_name: str, rule: AlertRule) -> None:
        """Add an alerting rule to a group."""
        if group_name not in self.alert_groups:
            self.alert_groups[group_name] = []
        self.alert_groups[group_name].append(rule)
        
    def _build_scrape_config(self, target: ScrapeTarget) -> dict[str, Any]:
        """Convert ScrapeTarget to Prometheus scrape_config format."""
        config = {
            "job_name": target.job_identifier,
            "scrape_interval": target.scrape_frequency,
            "scrape_timeout": target.timeout,
            "metrics_path": target.scrape_path,
            "static_configs": [{
                "targets": target.target_addresses,
                "labels": target.labels,
            }],
        }
        
        if target.relabel_rules:
            config["relabel_configs"] = target.relabel_rules
            
        return config
    
    def _build_alert_rule(self, rule: AlertRule) -> dict[str, Any]:
        """Convert AlertRule to Prometheus rule format."""
        return {
            "alert": rule.alert_name,
            "expr": rule.promql_expression,
            "for": rule.duration_threshold,
            "labels": {
                "severity": rule.severity_level,
                "component": rule.component_label,
            },
            "annotations": {
                "summary": rule.summary_text,
                "description": rule.description_text,
            },
        }
    
    def generate_main_config(self) -> dict[str, Any]:
        """Generate the main prometheus.yml configuration."""
        return {
            "global": {
                "scrape_interval": "20s",
                "evaluation_interval": "25s",
                "external_labels": {
                    "environment": "development",
                    "application": "ai-part-designer",
                },
            },
            "rule_files": [
                "/etc/prometheus/rules/*.yml",
            ],
            "scrape_configs": [
                self._build_scrape_config(t) for t in self.scrape_targets
            ],
        }
    
    def generate_alert_rules(self) -> dict[str, Any]:
        """Generate alerting rules configuration."""
        groups = []
        for group_name, rules in self.alert_groups.items():
            groups.append({
                "name": group_name,
                "interval": "30s",
                "rules": [self._build_alert_rule(r) for r in rules],
            })
        return {"groups": groups}
    
    def save_configs(self, output_dir: Path) -> None:
        """Save configuration files."""
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Save main config
        main_config = self.generate_main_config()
        with open(output_dir / "prometheus.yml", 'w') as f:
            yaml.dump(main_config, f, default_flow_style=False, sort_keys=False)
            
        # Save alert rules
        if self.alert_groups:
            rules_dir = output_dir / "rules"
            rules_dir.mkdir(exist_ok=True)
            alert_rules = self.generate_alert_rules()
            with open(rules_dir / "alerts.yml", 'w') as f:
                yaml.dump(alert_rules, f, default_flow_style=False, sort_keys=False)


def build_ai_part_designer_config() -> PrometheusConfigBuilder:
    """Build Prometheus config specific to AI Part Designer."""
    builder = PrometheusConfigBuilder()
    
    # Backend API scrape target
    builder.add_scrape_target(ScrapeTarget(
        job_identifier="part-designer-api",
        target_addresses=["backend:8000"],
        scrape_frequency="15s",
        labels={"tier": "backend", "component": "api-server"},
        relabel_rules=[
            {
                "source_labels": ["__address__"],
                "target_label": "instance",
                "replacement": "api-backend",
            },
        ],
    ))
    
    # Celery worker scrape target
    builder.add_scrape_target(ScrapeTarget(
        job_identifier="async-job-workers",
        target_addresses=["worker:9808"],
        scrape_frequency="30s",
        labels={"tier": "background", "component": "celery-worker"},
    ))
    
    # Prometheus self-monitoring
    builder.add_scrape_target(ScrapeTarget(
        job_identifier="prometheus-self",
        target_addresses=["localhost:9090"],
        scrape_frequency="30s",
        labels={"tier": "monitoring", "component": "prometheus"},
    ))
    
    # API performance alerts
    builder.add_alert_rule("api_health_monitoring", AlertRule(
        alert_name="HighServerErrorRate",
        promql_expression=(
            '(sum(rate(http_requests_total{status=~"5..",job="part-designer-api"}[5m])) '
            '/ sum(rate(http_requests_total{job="part-designer-api"}[5m]))) > 0.025'
        ),
        duration_threshold="4m",
        severity_level="warning",
        component_label="api-gateway",
        summary_text="API server error rate elevated above 2.5%",
        description_text=(
            "The API is experiencing {{ $value | humanizePercentage }} server errors. "
            "Investigate logs and recent deployments."
        ),
    ))
    
    builder.add_alert_rule("api_health_monitoring", AlertRule(
        alert_name="SlowAPILatency",
        promql_expression=(
            'histogram_quantile(0.95, '
            'sum(rate(http_request_duration_seconds_bucket{job="part-designer-api"}[8m])) by (le)) '
            '> 1.5'
        ),
        duration_threshold="6m",
        severity_level="warning",
        component_label="api-gateway",
        summary_text="API response time degraded (P95 > 1.5s)",
        description_text="95th percentile latency is {{ $value }}s. Check for slow queries or external API delays.",
    ))
    
    # CAD generation alerts
    builder.add_alert_rule("cad_generation_monitoring", AlertRule(
        alert_name="CADGenerationFailureRate",
        promql_expression=(
            '(sum(rate(cad_generations_total{status="error"}[15m])) '
            '/ sum(rate(cad_generations_total[15m]))) > 0.12'
        ),
        duration_threshold="10m",
        severity_level="critical",
        component_label="cad-engine",
        summary_text="CAD generation failure rate exceeds 12%",
        description_text=(
            "{{ $value | humanizePercentage }} of CAD generations are failing. "
            "Check CadQuery engine and parameter validation."
        ),
    ))
    
    builder.add_alert_rule("cad_generation_monitoring", AlertRule(
        alert_name="SlowCADGeneration",
        promql_expression=(
            'histogram_quantile(0.90, '
            'sum(rate(cad_generation_duration_seconds_bucket[10m])) by (le)) > 25'
        ),
        duration_threshold="8m",
        severity_level="warning",
        component_label="cad-engine",
        summary_text="CAD generation taking longer than expected",
        description_text="P90 generation time is {{ $value }}s (threshold: 25s). Check for complex models or resource constraints.",
    ))
    
    # Infrastructure alerts
    builder.add_alert_rule("infrastructure_monitoring", AlertRule(
        alert_name="DatabasePoolHighUtilization",
        promql_expression=(
            '(db_pool_checked_out_connections / db_pool_size) > 0.80'
        ),
        duration_threshold="5m",
        severity_level="warning",
        component_label="database",
        summary_text="Database connection pool at high capacity",
        description_text=(
            "Pool utilization is {{ $value | humanizePercentage }}. "
            "Consider increasing pool size or investigating connection leaks."
        ),
    ))
    
    builder.add_alert_rule("infrastructure_monitoring", AlertRule(
        alert_name="RedisDisconnected",
        promql_expression="redis_connected != 1",
        duration_threshold="90s",
        severity_level="critical",
        component_label="cache",
        summary_text="Redis cache is not connected",
        description_text="Cannot connect to Redis. Check Redis service health and network connectivity.",
    ))
    
    # AI provider monitoring
    builder.add_alert_rule("ai_integration_monitoring", AlertRule(
        alert_name="AIProviderErrorRate",
        promql_expression=(
            '(sum(rate(ai_requests_total{status="error"}[15m])) '
            '/ sum(rate(ai_requests_total[15m]))) > 0.10'
        ),
        duration_threshold="5m",
        severity_level="warning",
        component_label="ai-provider",
        summary_text="AI provider error rate elevated",
        description_text=(
            "{{ $value | humanizePercentage }} of AI requests failing. "
            "Check API keys, rate limits, and provider status."
        ),
    ))
    
    builder.add_alert_rule("ai_integration_monitoring", AlertRule(
        alert_name="HighAITokenUsage",
        promql_expression="sum(rate(ai_tokens_used_total[1h])) * 3600 > 150000",
        duration_threshold="45m",
        severity_level="info",
        component_label="ai-provider",
        summary_text="AI token consumption is high",
        description_text=(
            "Consuming {{ $value }} tokens/hour (threshold: 150k/hr). "
            "Monitor for cost implications."
        ),
    ))
    
    return builder


if __name__ == "__main__":
    output_dir = Path(__file__).parent.parent / "prometheus-config"
    
    config_builder = build_ai_part_designer_config()
    config_builder.save_configs(output_dir)
    
    print(f"✓ Generated: prometheus.yml")
    print(f"✓ Generated: rules/alerts.yml")
    print(f"\nConfiguration saved to: {output_dir}")
