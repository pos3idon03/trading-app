from datetime import datetime, timedelta, timezone

import pytest

from features.backtesting.engine import run_backtest
from features.backtesting.strategies.registry import validate_params


def _bars(count: int, *, start_price: float = 100.0, step: float = 1.0) -> list[dict]:
    rows: list[dict] = []
    for index in range(count):
        day = datetime(2024, 1, 1, tzinfo=timezone.utc) + timedelta(days=index)
        close = start_price + index * step
        rows.append(
            {
                "time": day,
                "open": close,
                "high": close + 1,
                "low": close - 1,
                "close": close,
                "volume": 1000,
            }
        )
    return rows


def test_validate_ensemble_defaults():
    params = validate_params("strategy_ensemble", None)
    assert params["combine_mode"] == "majority"
    assert len(params["legs"]) == 2


def test_validate_ensemble_rejects_buy_and_hold_leg():
    with pytest.raises(ValueError, match="not eligible"):
        validate_params(
            "strategy_ensemble",
            {
                "legs": [
                    {"strategy_id": "buy_and_hold", "params": {}, "weight": 1.0},
                    {"strategy_id": "rsi_reversion", "params": {}, "weight": 1.0},
                ]
            },
        )


def test_validate_ensemble_requires_two_legs():
    with pytest.raises(ValueError, match="between 2 and 5"):
        validate_params(
            "strategy_ensemble",
            {"legs": [{"strategy_id": "sma_crossover", "params": {}, "weight": 1.0}]},
        )


def test_validate_ensemble_validates_nested_params():
    with pytest.raises(ValueError, match="fast_period must be less than slow_period"):
        validate_params(
            "strategy_ensemble",
            {
                "legs": [
                    {
                        "strategy_id": "sma_crossover",
                        "params": {"fast_period": 50, "slow_period": 20},
                        "weight": 1.0,
                    },
                    {"strategy_id": "rsi_reversion", "params": {}, "weight": 1.0},
                ]
            },
        )


def test_validate_ensemble_accepts_donchian_leg():
    params = validate_params(
        "strategy_ensemble",
        {
            "legs": [
                {"strategy_id": "donchian_breakout", "params": {"channel_period": 20}, "weight": 1.0},
                {"strategy_id": "ts_momentum", "params": {"lookback": 63}, "weight": 1.0},
            ]
        },
    )
    assert params["legs"][0]["strategy_id"] == "donchian_breakout"


def test_run_ensemble_backtest_produces_trades():
    bars = _bars(80)
    params = validate_params("strategy_ensemble", None)
    result = run_backtest(bars, "strategy_ensemble", params, 10_000.0, 0.0)
    assert len(result.equity_curve) == len(bars)
    assert isinstance(result.trades, list)
