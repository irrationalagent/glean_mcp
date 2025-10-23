from __future__ import annotations
import httpx, json, hashlib, time, difflib
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field, field_validator, ConfigDict
from diskcache import Cache

BASE_V2 = "https://probeinfo.telemetry.mozilla.org/v2"
BASE_V1 = "https://probeinfo.telemetry.mozilla.org"

_cache = Cache(".probeinfo-cache")

def _ck(url: str) -> str:
    """Generate cache key from URL."""
    return hashlib.sha1(url.encode()).hexdigest()

def _get(url: str, ttl: int = 86400) -> Any:
    """
    HTTP GET with disk caching.

    Args:
        url: URL to fetch
        ttl: Time-to-live in seconds (default 15 minutes)

    Returns:
        Parsed JSON response
    """
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

class AppListing(BaseModel):
    v1_name: str
    app_name: Optional[str] = None
    app_id: Optional[str] = None
    canonical_app_name: Optional[str] = None
    bq_dataset_family: Optional[str] = None
    document_namespace: Optional[str] = None

class GleanGeneral(BaseModel):
    """General scraping properties for a Glean app."""
    lastUpdate: str  # ISO-8601 timestamp

class MetricHistory(BaseModel):
    """History entry for a Glean metric."""
    model_config = ConfigDict(populate_by_name=True)

    bugs: Optional[List[str]] = None
    data_reviews: Optional[List[str]] = None
    dates: Optional[Dict[str, Any]] = None
    description: Optional[str] = None
    disabled: Optional[bool] = None
    expires: Optional[str] = None
    lifetime: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    send_in_pings: Optional[List[str]] = None
    type: Optional[str] = None
    version: Optional[Union[str, int]] = None
    extra_keys: Optional[Dict[str, Any]] = None
    # Additional fields found in the API response
    gecko_datapoint: Optional[str] = None
    source_url: Optional[str] = None
    data_sensitivity: Optional[List[str]] = None
    notification_emails: Optional[List[str]] = None
    no_lint: Optional[List[str]] = None
    reflog_index: Optional[Dict[str, int]] = Field(default=None, alias='reflog-index')
    git_commits: Optional[Dict[str, Any]] = Field(default=None, alias='git-commits')
    config: Optional[Dict[str, Any]] = Field(default=None, alias='_config')
    allow_reserved: Optional[bool] = None

    @field_validator('version', mode='before')
    @classmethod
    def convert_version_to_str(cls, v):
        """Convert version to string if it's an integer."""
        if v is not None and isinstance(v, int):
            return str(v)
        return v

    @field_validator('bugs', mode='before')
    @classmethod
    def convert_bugs_to_str(cls, v):
        """Convert bug IDs to strings if they're integers."""
        if v is None:
            return v
        if isinstance(v, list):
            return [str(item) if isinstance(item, int) else item for item in v]
        return v

    @field_validator('expires', mode='before')
    @classmethod
    def convert_expires_to_str(cls, v):
        """Convert expires to string if it's an integer."""
        if v is not None and isinstance(v, int):
            return str(v)
        return v

class GleanDependency(BaseModel):
    """Dependency information for a Glean app."""
    name: str
    type: Optional[str] = None

class GleanRepository(BaseModel):
    """Repository listing from the Glean repositories endpoint."""
    name: str
    app_id: Optional[str] = None
    canonical_app_name: Optional[str] = None
    url: Optional[str] = None
    notification_emails: Optional[List[str]] = None
    v1_name: Optional[str] = None

def list_apps() -> List[AppListing]:
    """
    Use v2 Glean app listings to expose stable identifiers and BQ dataset families.
    Fields documented: app_name, v1_name, bq_dataset_family, canonical_app_name, etc.  :contentReference[oaicite:4]{index=4}
    """
    raw = _get(f"{BASE_V2}/glean/app-listings")
    # raw is an array of flattened listings (one per app_id) in v2 docs. :contentReference[oaicite:5]{index=5}
    out: Dict[str, AppListing] = {}
    for item in raw:
        v1 = item.get("v1_name") or item.get("app_name")  # v1_name is present per docs
        if not v1:
            continue
        out[v1] = AppListing(
            v1_name=v1,
            app_name=item.get("app_name"),
            app_id=item.get("app_id"),
            canonical_app_name=item.get("canonical_app_name"),
            bq_dataset_family=item.get("bq_dataset_family"),
            document_namespace=item.get("document_namespace"),
        )
    return list(out.values())

# ============================================================================
# Probe Info Service v1 API Functions
# Documentation: https://mozilla.github.io/probe-scraper/#tag/v1
# ============================================================================

def get_glean_general(v1_name: str) -> GleanGeneral:
    """
    Get general scraping properties for a Glean application.

    Args:
        v1_name: The v1_name identifier from repositories.yaml (e.g., "fenix", "firefox-desktop")

    Returns:
        GleanGeneral object containing last update timestamp

    Example:
        >>> info = get_glean_general("fenix")
        >>> print(info.lastUpdate)
        '2025-10-23T12:34:56Z'
    """
    url = f"{BASE_V1}/glean/{v1_name}/general"
    data = _get(url)
    return GleanGeneral(**data)

def get_glean_metrics(v1_name: str) -> Dict[str, List[MetricHistory]]:
    """
    Get metric definitions and history for a Glean application.

    Args:
        v1_name: The v1_name identifier from repositories.yaml

    Returns:
        Dictionary mapping metric names to their history arrays.
        Each history entry is a MetricHistory object containing:
        - bugs: List of bug URLs
        - data_reviews: List of data review URLs
        - dates: Date information
        - description: Metric description
        - lifetime: Metric lifetime (e.g., "ping", "application")
        - send_in_pings: List of ping names this metric is sent in
        - type: Metric type (e.g., "counter", "string", "boolean")
        - extra_keys: Additional metadata for events

    Example:
        >>> metrics = get_glean_metrics("fenix")
        >>> for metric_name, history in metrics.items():
        >>>     print(f"{metric_name}: {history[0].type}")
    """
    url = f"{BASE_V1}/glean/{v1_name}/metrics"

    try:
        raw = _get(url)
    except httpx.HTTPStatusError as e:
        # If we get a 404, try to find the closest matching v1_name
        if e.response.status_code == 404:
            apps = list_apps()
            available_names = [app.v1_name for app in apps]

            # Use difflib to find the closest match
            matches = difflib.get_close_matches(v1_name, available_names, n=1, cutoff=0.6)

            if matches:
                closest_match = matches[0]
                # Retry with the closest match
                url = f"{BASE_V1}/glean/{closest_match}/metrics"
                raw = _get(url)
            else:
                # No close match found, re-raise the original error
                raise
        else:
            # Not a 404, re-raise the error
            raise

    # Parse each metric's history into MetricHistory objects
    result: Dict[str, List[MetricHistory]] = {}
    for metric_name, metric_data in raw.items():
        parsed_history = []
        # The v1 API returns each metric as a dict with a "history" key
        if isinstance(metric_data, dict) and "history" in metric_data:
            history_list = metric_data["history"]
            for entry in history_list:
                # Handle case where entry might be a string or dict
                if isinstance(entry, dict):
                    parsed_history.append(MetricHistory(**entry))
                elif isinstance(entry, str):
                    # Skip string entries or handle them appropriately
                    continue
        result[metric_name] = parsed_history

    return result

def get_glean_dependencies(v1_name: str) -> List[GleanDependency]:
    """
    Get dependency information for a Glean application.

    Args:
        v1_name: The v1_name identifier from repositories.yaml

    Returns:
        List of GleanDependency objects containing dependency name and type

    Example:
        >>> deps = get_glean_dependencies("fenix")
        >>> for dep in deps:
        >>>     print(f"{dep.name}: {dep.type}")
    """
    url = f"{BASE_V1}/glean/{v1_name}/dependencies"
    raw = _get(url)
    return [GleanDependency(**item) for item in raw]

def get_glean_repositories() -> List[Dict[str, Any]]:
    """
    Get all Glean repository listings.

    Returns an array of repository objects including:
    - app metadata (name, app_id, canonical_app_name)
    - channels information
    - repository URLs
    - pipeline configuration for applications and libraries

    Returns:
        List of repository dictionaries with full metadata

    Example:
        >>> repos = get_glean_repositories()
        >>> for repo in repos:
        >>>     print(f"{repo.get('name')}: {repo.get('url')}")
    """
    url = f"{BASE_V1}/glean/repositories"
    return _get(url)
