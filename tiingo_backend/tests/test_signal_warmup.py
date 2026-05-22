from datetime import datetime, timedelta, timezone

from features.backtesting.signal_warmup import (
    collect_warmup_bars_by_timeframe,
    collect_warmup_bars_for_standalone,
    compute_warmup_start,
)


def test_collect_warmup_bars_ensemble_leg():
    params = {
        "combine_mode": "unanimous",
        "threshold": 0.5,
        "legs": [
            {
                "strategy_id": "ema_crossover",
                "params": {"fast_period": 12, "slow_period": 26},
                "weight": 1.0,
                "signal_timeframe": "4h",
            },
            {
                "strategy_id": "rsi_reversion",
                "params": {"period": 14, "oversold": 30, "overbought": 70},
                "weight": 1.0,
                "signal_timeframe": "30m",
            },
        ],
    }
    warmup = collect_warmup_bars_by_timeframe("strategy_ensemble", params, "15m")
    assert warmup["4h"] == 26
    assert warmup["30m"] == 16


def test_collect_warmup_skips_decision_timeframe_leg():
    params = {
        "combine_mode": "unanimous",
        "threshold": 0.5,
        "legs": [
            {
                "strategy_id": "ema_crossover",
                "params": {"fast_period": 12, "slow_period": 26},
                "weight": 1.0,
                "signal_timeframe": "15m",
            },
        ],
    }
    warmup = collect_warmup_bars_by_timeframe("strategy_ensemble", params, "15m")
    assert warmup == {}


def test_standalone_warmup_when_signal_differs():
    warmup = collect_warmup_bars_for_standalone(
        "ema_crossover",
        {"fast_period": 12, "slow_period": 26},
        "15m",
        "4h",
    )
    assert warmup == {"4h": 26}


def test_compute_warmup_start_extends_backward():
    start = datetime(2024, 6, 1, tzinfo=timezone.utc)
    earliest = datetime(2024, 1, 1, tzinfo=timezone.utc)
    result = compute_warmup_start(start, "4h", 26, earliest=earliest)
    expected = start - timedelta(hours=4) * int(26 * 1.5)
    assert result == expected


def test_compute_warmup_start_clamped_to_earliest():
    start = datetime(2024, 6, 1, tzinfo=timezone.utc)
    earliest = datetime(2024, 5, 30, tzinfo=timezone.utc)
    result = compute_warmup_start(start, "4h", 26, earliest=earliest)
    assert result == earliest
