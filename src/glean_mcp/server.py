# src/glean_mcp/server.py
from __future__ import annotations
import json
from mcp.server.fastmcp import FastMCP
from glean_mcp.probeinfo_client import list_apps   # now includes bq_dataset_family
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

def main():
    mcp.run()

if __name__ == "__main__":
    main()
