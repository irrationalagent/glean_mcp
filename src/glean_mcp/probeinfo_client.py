from __future__ import annotations
import httpx, json, hashlib, time
from typing import Any, Dict, List, Optional
from pydantic import BaseModel
from diskcache import Cache

BASE = "https://probeinfo.telemetry.mozilla.org/v2"  # :contentReference[oaicite:3]{index=3}

class AppListing(BaseModel):
    v1_name: str
    app_name: Optional[str] = None
    app_id: Optional[str] = None
    canonical_app_name: Optional[str] = None
    bq_dataset_family: Optional[str] = None
    document_namespace: Optional[str] = None

def list_apps() -> List[AppListing]:
    """
    Use v2 Glean app listings to expose stable identifiers and BQ dataset families.
    Fields documented: app_name, v1_name, bq_dataset_family, canonical_app_name, etc.  :contentReference[oaicite:4]{index=4}
    """
    raw = _get(f"{BASE}/glean/app-listings")
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
