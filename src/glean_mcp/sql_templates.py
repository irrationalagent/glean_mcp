from __future__ import annotations
from typing import Dict, Any

def _default_table(app_v1_name: str, ping: str) -> str:
    # Adjust to your org’s naming; many teams use mozdata union views.
    # Example: mozdata.{app}.metrics or mozdata.{app}.{ping}
    # The Glean Dictionary & docs explain ping->table mapping.  # :contentReference[oaicite:9]{index=9}
    return f"`mozdata.{app_v1_name}.`{ping}`"  # change to your preferred view

def sql_for_metric(app_v1_name: str, metric: Dict[str, Any], since_days: int = 28) -> Dict[str, str]:
    mtype = metric.get("type")
    pings = (metric.get("send_in_pings") or ["metrics"])
    ping = pings[0]  # prefer first declared ping
    column = metric.get("name")
    category = metric.get("category")
    fq = f"{category}.{column}" if category else column

    table = _default_table(app_v1_name, ping)

    if mtype in ("counter", "quantity", "memory_distribution", "timing_distribution", "custom_distribution"):
        sql = f"""
-- {fq} ({mtype}) in {ping} ping
SELECT
  submission_date,
  SUM(payload.metrics.{category}.{column}) AS value
FROM {table}
WHERE submission_date >= DATE_SUB(CURRENT_DATE(), INTERVAL {since_days} DAY)
GROUP BY 1
ORDER BY 1
"""
    elif mtype == "event":
        sql = f"""
-- {fq} (event) in {ping} ping
SELECT
  submission_date,
  event_category,
  event_name,
  COUNT(*) AS n
FROM {table}
WHERE submission_date >= DATE_SUB(CURRENT_DATE(), INTERVAL {since_days} DAY)
  AND event_category = "{category}"
  AND event_name = "{column}"
GROUP BY 1,2,3
ORDER BY 1
"""
    else:
        # fallback: treat as scalar/boolean/string
        sql = f"""
-- {fq} ({mtype}) in {ping} ping
SELECT
  submission_date,
  AVG(payload.metrics.{category}.{column}) AS value
FROM {table}
WHERE submission_date >= DATE_SUB(CURRENT_DATE(), INTERVAL {since_days} DAY)
GROUP BY 1
ORDER BY 1
"""
    return {"sql": sql.strip(), "table_hint": table, "ping": ping}
