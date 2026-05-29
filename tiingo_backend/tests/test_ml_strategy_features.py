from datetime import datetime, timedelta, timezone

import pytest

from features.ml.strategy_features import build_strategy_feature_matrix

ENSEMBLE_ELIGIBLE_STRATEGIES = [
    "sma_crossover",
    "ema_crossover",
    "rsi_reversion",
    "donchian_breakout",
    "bollinger_breakout",
    "stochastic_reversion",
    "mfi_reversion",
    "ts_momentum",
]


def _bars(count: int, start_price: float = 100.0) -> list[dict]:
    start = datetime(2024, 1, 1, tzinfo=timezone.utc)
    bars = []
    price = start_price
    for index in range(count):
        price += 0.5 if index % 5 else -0.2
        bars.append({
            "time": start + timedelta(days=index),
            "open": price,
            "high": price + 1,
            "low": price - 1,
            "close": price,
            "volume": 1000 + index,
        })
    return bars


def test_strategy_signal_encoding():
    bars = _bars(120)
    names, rows, _ = build_strategy_feature_matrix(bars, ["rsi_reversion"])
    assert any(name.endswith("_signal") for name in names)
    valid_rows = [row for row in rows if row is not None]
    assert valid_rows
    assert all(value in (-1.0, 0.0, 1.0) for value in valid_rows[0][:1])


@pytest.mark.parametrize("strategy_id", ENSEMBLE_ELIGIBLE_STRATEGIES)
def test_ensemble_eligible_strategy_produces_valid_rows(strategy_id: str):
    bars = _bars(200)
    names, rows, warnings = build_strategy_feature_matrix(bars, [strategy_id])
    assert f"strat_{strategy_id}_signal" in names
    assert f"strat_{strategy_id}_cont_0" in names
    valid_rows = [row for row in rows if row is not None]
    assert valid_rows, f"{strategy_id} produced no valid rows; warnings={warnings}"


def test_unknown_strategy_rejected():
    bars = _bars(80)
    try:
        build_strategy_feature_matrix(bars, ["buy_and_hold"])
    except ValueError as exc:
        assert "not eligible" in str(exc)
    else:
        raise AssertionError("Expected ValueError")
