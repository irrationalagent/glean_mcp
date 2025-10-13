# src/glean_mcp/glean_dictionary_client.py
from __future__ import annotations
from typing import Any, Dict, List, Optional
import httpx, urllib.parse, time, hashlib
from diskcache import Cache

# Public search service (documented in the Glean Dictionary README).
# Example: https://dictionary.telemetry.mozilla.org/api/v1/metrics_search_burnham?search=techno
# You can run the same API locally via `netlify dev`.
BASE = "https://dictionary.telemetry.mozilla.org/api/v1"  # :contentReference[oaicite:1]{index=1}

_cache = Cache(".glean-dict-cache")

def _ck(url: str) -> str:
    return hashlib.sha1(url.encode()).hexdigest()

def _get_json(url: str, ttl: int = 900) -> Any:
    now = time.time()
    key = _ck(url)
    cached = _cache.get(key)
    if cached and now - cached["ts"] < ttl:
        return cached["data"]
    with httpx.Client(timeout=30) as client:
        r = client.get(url)
        r.raise_for_status()
        data = r.json()
    _cache.set(key, {"ts": now, "data": data})
    return data

def search_metrics_dictionary(query: str, app_hint: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
    """
    Hit the Glean Dictionary search function and return normalized rows.

    app_hint:
      - If provided (e.g., "fenix"), we try an app-specific endpoint first: /metrics_search_{app_hint}
      - Fallback to the Glean endpoint for Firefox Desktop: /metrics_search_firefox_desktop
    """
    q = urllib.parse.quote_plus(query)
    candidates = []
    if app_hint:
        candidates.append(f"{BASE}/metrics_search_{app_hint}?search={q}")
    # General Glean search (as documented in the README)
    candidates.append(f"{BASE}/metrics_search_firefox_desktop?search={q}")  # :contentReference[oaicite:2]{index=2}

    payload: List[Dict[str, Any]] = []
    last_err: Optional[Exception] = None
    for url in candidates:
        try:
            data = _get_json(url)
            # The Netlify functions typically return a list of dicts; if wrapped, unwrap common keys.
            if isinstance(data, dict) and "results" in data:
                rows = data["results"]
            else:
                rows = data
            if isinstance(rows, list):
                payload = rows
                break
        except Exception as e:
            last_err = e
            continue
    if not payload and last_err:
        raise last_err

    # Normalize a few common fields; keep originals too.
    out: List[Dict[str, Any]] = []
    for r in payload[:limit]:
        # Heuristic extraction; the exact shape can vary across endpoints.
        name = r.get("name") or r.get("metric") or r.get("metric_name")
        category = r.get("category") or r.get("category_name")
        mtype = r.get("type") or r.get("metric_type")
        app = (
            r.get("app")
            or r.get("app_name")
            or r.get("application")
            or (r.get("apps") or [None])[0]
        )
        send_in_pings = r.get("send_in_pings") or r.get("pings")
        desc = r.get("description") or r.get("metric_description")
        url = r.get("url") or r.get("landing_url") or r.get("permalink")

        out.append({
            "id": f"{category}.{name}" if category and name else (name or ""),
            "name": name,
            "category": category,
            "type": mtype,
            "app": app,
            "send_in_pings": send_in_pings,
            "description": desc,
            "url": url,
            "_raw": r,  # keep full row for power users
        })
    return out
