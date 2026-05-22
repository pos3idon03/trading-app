from datetime import date, datetime, timedelta, timezone
from typing import Any

from features.market_data.ohlcv_resample import SUPPORTED_TIMEFRAMES

_WARMUP_SAFETY_FACTOR = 1.5

_TIMEFRAME_DELTAS: dict[str, timedelta] = {
    "1m": timedelta(minutes=1),
    "5m": timedelta(minutes=5),
    "15m": timedelta(minutes=15),
    "30m": timedelta(minutes=30),
    "1h": timedelta(hours=1),
    "4h": timedelta(hours=4),
    "1d": timedelta(days=1),
    "1w": timedelta(weeks=1),
    "1mo": timedelta(days=30),
}


def _indicator_warmup_bars(strategy_id: str, params: dict[str, Any]) -> int:
    from features.backtesting.strategies.registry import resolve_strategy

    meta = resolve_strategy(strategy_id)
    minimum = int(meta["min_bars"])
    merged = {**meta.get("params", {}), **params}

    if strategy_id in ("sma_crossover", "ema_crossover"):
        return max(minimum, int(merged.get("slow_period", minimum)))
    if strategy_id in ("rsi_reversion", "mfi_reversion"):
        return max(minimum, int(merged.get("period", minimum)))
    if strategy_id == "stochastic_reversion":
        k = int(merged.get("k_period", 14))
        d = int(merged.get("d_period", 3))
        return max(minimum, k + d)
    if strategy_id == "donchian_breakout":
        return max(minimum, int(merged.get("channel_period", minimum)))
    if strategy_id == "bollinger_breakout":
        return max(minimum, int(merged.get("period", minimum)))
    if strategy_id == "ts_momentum":
        return max(minimum, int(merged.get("lookback", minimum)))
    return minimum


def collect_warmup_bars_by_timeframe(
    strategy: str,
    params: dict[str, Any],
    decision_timeframe: str,
) -> dict[str, int]:
    """Map each signal timeframe to extra bars needed before the user start date."""
    warmup: dict[str, int] = {}

    if strategy == "strategy_ensemble":
        for leg in params.get("legs", []):
            leg_tf = leg.get("signal_timeframe") or decision_timeframe
            if leg_tf == decision_timeframe:
                continue
            leg_params = leg.get("params") or {}
            needed = _indicator_warmup_bars(leg["strategy_id"], leg_params)
            warmup[leg_tf] = max(warmup.get(leg_tf, 0), needed)
        return warmup

    return {}


def collect_warmup_bars_for_standalone(
    strategy: str,
    params: dict[str, Any],
    decision_timeframe: str,
    signal_timeframe: str,
) -> dict[str, int]:
    if signal_timeframe == decision_timeframe:
        return {}
    return {signal_timeframe: _indicator_warmup_bars(strategy, params)}


def compute_warmup_start(
    requested_start: datetime,
    timeframe: str,
    warmup_bars: int,
    *,
    earliest: datetime | None = None,
) -> datetime:
    if warmup_bars <= 0 or timeframe not in _TIMEFRAME_DELTAS:
        return requested_start

    bar_delta = _TIMEFRAME_DELTAS[timeframe]
    extra = int(warmup_bars * _WARMUP_SAFETY_FACTOR)
    padded = requested_start - bar_delta * extra
    if earliest is not None and padded < earliest:
        return earliest
    return padded


def timeframe_duration(timeframe: str) -> timedelta:
    if timeframe not in SUPPORTED_TIMEFRAMES:
        raise ValueError(f"Unsupported timeframe: {timeframe}")
    return _TIMEFRAME_DELTAS[timeframe]


def merge_warmup_maps(*maps: dict[str, int]) -> dict[str, int]:
    merged: dict[str, int] = {}
    for item in maps:
        for tf, count in item.items():
            merged[tf] = max(merged.get(tf, 0), count)
    return merged
