import hashlib
import json
from datetime import date
from typing import Any


def _format_pct(value: float | None) -> str | None:
    if value is None:
        return None
    return f"{value:+.2f}%"


def build_macro_context(overview: dict) -> dict[str, Any]:
    rows = overview.get("rows") or []
    series = [
        {
            "series_id": row["series_id"],
            "title": row.get("title", row["series_id"]),
            "category": row.get("category", "general"),
            "frequency": row.get("frequency"),
            "trends": {
                "change_1m": _format_pct(row.get("change_1m")),
                "change_3m": _format_pct(row.get("change_3m")),
                "change_6m": _format_pct(row.get("change_6m")),
                "change_ytd": _format_pct(row.get("change_ytd")),
            },
            "ma50_position": row.get("ma50_position", "—"),
            "ma200_position": row.get("ma200_position", "—"),
        }
        for row in rows
    ]
    as_of = overview.get("as_of")
    return {
        "as_of": as_of.isoformat() if isinstance(as_of, date) else as_of,
        "category": overview.get("category", "all"),
        "series_count": len(series),
        "series": series,
    }


def rows_fingerprint(overview: dict) -> str:
    payload = build_macro_context(overview)
    canonical = json.dumps(payload, sort_keys=True, default=str)
    return hashlib.sha256(canonical.encode()).hexdigest()
