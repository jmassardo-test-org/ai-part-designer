#!/usr/bin/env python3
"""
Grafana provisioning configuration generator for AI Part Designer.
Creates datasource and dashboard provider configurations.
"""

import yaml
from pathlib import Path
from typing import Any


def generate_datasource_provisioning() -> dict[str, Any]:
    """Create datasource provisioning for Prometheus."""
    return {
        "apiVersion": 1,
        "datasources": [{
            "name": "AIPartDesignerMetrics",
            "type": "prometheus",
            "uid": "pd_prometheus_main",
            "access": "proxy",
            "url": "http://prometheus:9090",
            "isDefault": True,
            "editable": False,
            "jsonData": {
                "timeInterval": "20s",
                "httpMethod": "POST",
                "queryTimeout": "90s",
                "incrementalQuerying": True,
                "incrementalQueryOverlapWindow": "15m",
            },
        }],
    }


def generate_dashboard_provider() -> dict[str, Any]:
    """Create dashboard provider configuration."""
    return {
        "apiVersion": 1,
        "providers": [{
            "name": "AIPartDesignerDashboards",
            "type": "file",
            "folder": "Platform Monitoring",
            "updateIntervalSeconds": 45,
            "allowUiUpdates": True,
            "options": {
                "path": "/etc/grafana/dashboards",
                "foldersFromFilesStructure": False,
            },
        }],
    }


if __name__ == "__main__":
    base_dir = Path(__file__).parent.parent / "grafana-provisioning"
    
    # Generate datasource config
    datasource_dir = base_dir / "datasources"
    datasource_dir.mkdir(parents=True, exist_ok=True)
    with open(datasource_dir / "prometheus.yml", 'w') as f:
        yaml.dump(generate_datasource_provisioning(), f,
                  default_flow_style=False, sort_keys=False)
    print(f"✓ Generated: datasources/prometheus.yml")
    
    # Generate dashboard provider config
    dashboard_dir = base_dir / "dashboards"
    dashboard_dir.mkdir(parents=True, exist_ok=True)
    with open(dashboard_dir / "providers.yml", 'w') as f:
        yaml.dump(generate_dashboard_provider(), f,
                  default_flow_style=False, sort_keys=False)
    print(f"✓ Generated: dashboards/providers.yml")
    
    print(f"\nProvisioning configs saved to: {base_dir}")
