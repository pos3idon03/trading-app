from datetime import datetime


def evaluation_row_to_activity(row: dict) -> dict:
    bar_time = row["bar_time"]
    created_at = row["created_at"]
    return {
        "id": str(row["id"]),
        "deployment_id": str(row["deployment_id"]),
        "symbol": row.get("symbol") or "",
        "model_id": str(row["model_id"]) if row.get("model_id") else None,
        "model_name": row.get("model_name"),
        "model_type": row.get("model_type"),
        "bar_time": bar_time.isoformat() if isinstance(bar_time, datetime) else str(bar_time),
        "signal": row["signal"],
        "probability": row.get("probability"),
        "buy_threshold": row.get("buy_threshold"),
        "sell_threshold": row.get("sell_threshold"),
        "position_side": row.get("position_side"),
        "order_intent_side": row.get("order_intent_side"),
        "order_qty": row.get("order_qty"),
        "outcome": row["outcome"],
        "blocked_reason": row.get("blocked_reason"),
        "order_id": str(row["order_id"]) if row.get("order_id") else None,
        "warnings": row.get("warnings") or [],
        "created_at": created_at.isoformat() if isinstance(created_at, datetime) else str(created_at),
    }
