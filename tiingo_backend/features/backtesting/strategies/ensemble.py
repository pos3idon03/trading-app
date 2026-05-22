from typing import Any

from features.backtesting.bar_context import MultiTimeframeContext
from features.backtesting.combiner import combine_signals


def generate_signal(
    bars: list[dict],
    indicators: list[str | None],
    params: dict[str, Any],
    index: int,
) -> str:
    return generate_signal_at(bars, indicators, params, index, bar_context=None)


def generate_signal_at(
    bars: list[dict],
    indicators: list[str | None],
    params: dict[str, Any],
    index: int,
    bar_context: MultiTimeframeContext | None,
) -> str:
    from features.backtesting.strategies.registry import get_signal_fn

    legs = params["legs"]
    combine_mode = params["combine_mode"]
    threshold = float(params.get("threshold", 0.5))

    signals: list[str] = []
    weights: list[float] = []

    for leg in legs:
        strategy_id = leg["strategy_id"]
        leg_params = leg["params"]
        signal_fn = get_signal_fn(strategy_id)
        leg_index = _leg_signal_index(bars, index, leg, bar_context)
        if leg_index < 0:
            signals.append("hold")
        else:
            leg_bars = _leg_bars(bars, leg, bar_context)
            signals.append(signal_fn(leg_bars, indicators, leg_params, leg_index))
        weights.append(float(leg["weight"]))

    return combine_signals(signals, weights, combine_mode, threshold)


def _leg_bars(
    bars: list[dict],
    leg: dict[str, Any],
    bar_context: MultiTimeframeContext | None,
) -> list[dict]:
    if bar_context is None:
        return bars
    leg_tf = leg.get("signal_timeframe") or bar_context.decision_timeframe
    return bar_context.bars_for(leg_tf)


def _leg_signal_index(
    bars: list[dict],
    index: int,
    leg: dict[str, Any],
    bar_context: MultiTimeframeContext | None,
) -> int:
    if bar_context is None:
        return index
    leg_tf = leg.get("signal_timeframe") or bar_context.decision_timeframe
    return bar_context.aligned_index(index, leg_tf)


def ensemble_min_bars(legs: list[dict[str, Any]]) -> int:
    from features.backtesting.strategies.registry import resolve_strategy

    minimum = 1
    for leg in legs:
        meta = resolve_strategy(leg["strategy_id"])
        minimum = max(minimum, int(meta["min_bars"]))
    return minimum
