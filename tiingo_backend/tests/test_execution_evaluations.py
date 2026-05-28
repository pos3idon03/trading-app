from features.execution.activity_format import evaluation_row_to_activity


def test_evaluation_row_to_activity_formats_payload():
    row = {
        "id": "eval-1",
        "deployment_id": "dep-1",
        "symbol": "AAPL",
        "model_id": "model-1",
        "model_name": "AAPL rf prices_only",
        "model_type": "ml_random_forest",
        "bar_time": "2026-05-22T03:00:00+00:00",
        "signal": "buy",
        "probability": 0.61,
        "buy_threshold": 0.55,
        "sell_threshold": 0.45,
        "position_side": "flat",
        "order_intent_side": "buy",
        "order_qty": 5.0,
        "outcome": "blocked",
        "blocked_reason": "Position size 100.00% exceeds max 5.0%",
        "order_id": None,
        "warnings": [],
        "created_at": "2026-05-28T10:00:00+00:00",
    }
    payload = evaluation_row_to_activity(row)
    assert payload["symbol"] == "AAPL"
    assert payload["model_name"] == "AAPL rf prices_only"
    assert payload["outcome"] == "blocked"
    assert payload["blocked_reason"].startswith("Position size")
