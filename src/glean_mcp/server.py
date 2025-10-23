# src/glean_mcp/server.py
from __future__ import annotations
import json
from mcp.server.fastmcp import FastMCP
from glean_mcp.probeinfo_client import list_apps, get_glean_metrics   # now includes bq_dataset_family
from glean_mcp.glean_dictionary_client import search_metrics_dictionary

mcp = FastMCP("glean-mcp")

@mcp.tool()
def list_apps_tool() -> str:
    """List Glean apps with identifiers useful for BigQuery routing."""
    apps = list_apps()
    return json.dumps([a.model_dump() for a in apps], indent=2)

@mcp.tool()
def search_metrics(query: str, app_hint: str | None = None, limit: int = 25) -> str:
    """
    Search Glean metrics via the Glean Dictionary search API.

    - query: free text (e.g., "startup time", "first run")
    - app_hint: optional v1_name/app_name like "fenix" to bias search
    - limit: max results
    """
    rows = search_metrics_dictionary(query, app_hint=app_hint, limit=limit)
    # Keep the response compact but useful for agents
    compact = []
    for r in rows:
        compact.append({
            "id": r["id"],
            "name": r["name"],
            "category": r["category"],
            "type": r["type"],
            "app": r["app"],
            "send_in_pings": r["send_in_pings"],
            "description": r["description"],
            "url": r["url"],   # link back to the Dictionary page if present
        })
    return json.dumps(compact, indent=2)

@mcp.tool()
def get_metrics_for_app(v1_name: str) -> str:
    """
    Get all metric definitions and history for a Glean application from probe-info service.

    - v1_name: The v1_name identifier (e.g., "fenix", "firefox-desktop", "focus-android")

    Returns a dictionary mapping metric names to their history arrays.
    Each history entry includes:
    - bugs: List of bug URLs
    - data_reviews: List of data review URLs
    - description: Metric description
    - lifetime: Metric lifetime (e.g., "ping", "application")
    - send_in_pings: List of ping names this metric is sent in
    - type: Metric type (e.g., "counter", "string", "boolean")
    - dates: Date information for when the metric was active
    - extra_keys: Additional metadata for events
    """
    metrics = get_glean_metrics(v1_name)
    # Convert MetricHistory objects to dicts for JSON serialization
    serializable = {
        metric_name: [history.model_dump() for history in history_list]
        for metric_name, history_list in metrics.items()
    }
    return json.dumps(serializable, indent=2)

def main():
    mcp.run()

if __name__ == "__main__":
    main()
