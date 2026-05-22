from datetime import datetime, timedelta, timezone

import pytest

from features.backtesting.bar_context import build_multi_timeframe_context
from features.backtesting.engine import run_backtest
from features.backtesting.strategies.registry import validate_params


def _bars(timeframe_minutes: int, count: int, *, start_price: float = 100.0) -> list[dict]:
    base = datetime(2024, 1, 2, 9, 0, tzinfo=timezone.utc)
    rows: list[dict] = []
    for index in range(count):
        close = start_price + index
        rows.append(
            {
                "time": base + timedelta(minutes=timeframe_minutes * index),
                "open": close,
                "high": close + 1,
                "low": close - 1,
                "close": close,
                "volume": 1000,
            }
        )
    return rows


def test_multitimeframe_ensemble_runs_on_decision_bars():
    decision_bars = _bars(15, 40)
    params = validate_params(
        "strategy_ensemble",
        {
            "combine_mode": "majority",
            "legs": [
                {
                    "strategy_id": "ema_crossover",
                    "signal_timeframe": "5m",
                    "params": {"fast_period": 12, "slow_period": 26},
                    "weight": 1.0,
                },
                {
                    "strategy_id": "rsi_reversion",
                    "signal_timeframe": "30m",
                    "params": {"period": 14, "oversold": 30, "overbought": 70},
                    "weight": 1.0,
                },
            ],
        },
    )
    bars_by_tf = {
        "15m": decision_bars,
        "5m": _bars(5, 120),
        "30m": _bars(30, 20),
    }
    context = build_multi_timeframe_context(
        decision_timeframe="15m",
        decision_bars=decision_bars,
        bars_by_timeframe=bars_by_tf,
        standalone_signal_timeframe="15m",
    )
    result = run_backtest(
        decision_bars,
        "strategy_ensemble",
        params,
        10_000.0,
        0.0,
        bar_context=context,
        decision_timeframe="15m",
    )
    assert len(result.equity_curve) == len(decision_bars)


def test_validate_ensemble_leg_signal_timeframe():
    params = validate_params(
        "strategy_ensemble",
        {
            "legs": [
                {
                    "strategy_id": "sma_crossover",
                    "signal_timeframe": "5m",
                    "params": {},
                    "weight": 1.0,
                },
                {"strategy_id": "rsi_reversion", "params": {}, "weight": 1.0},
            ]
        },
    )
    assert params["legs"][0]["signal_timeframe"] == "5m"


def test_validate_rejects_unknown_signal_timeframe():
    with pytest.raises(ValueError, match="signal timeframe"):
        validate_params(
            "strategy_ensemble",
            {
                "legs": [
                    {
                        "strategy_id": "sma_crossover",
                        "signal_timeframe": "2h",
                        "params": {},
                        "weight": 1.0,
                    },
                    {"strategy_id": "rsi_reversion", "params": {}, "weight": 1.0},
                ]
            },
        )
