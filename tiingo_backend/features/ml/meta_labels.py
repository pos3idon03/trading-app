from typing import Optional

from features.backtesting.indicators import compute_atr


def _atr_at_index(
    highs: list[float],
    lows: list[float],
    closes: list[float],
    index: int,
    period: int,
) -> Optional[float]:
    atr_series = compute_atr(highs, lows, closes, period)
    value = atr_series[index]
    if value is None or value <= 0:
        return None
    return float(value)


def label_single_event(
    bars: list[dict],
    event_index: int,
    *,
    profit_atr_mult: float,
    stop_atr_mult: float,
    max_horizon_bars: int,
    atr_period: int = 14,
) -> Optional[int]:
    if event_index < 0 or event_index >= len(bars):
        return None

    highs = [float(b["high"]) for b in bars]
    lows = [float(b["low"]) for b in bars]
    closes = [float(b["close"]) for b in bars]
    atr = _atr_at_index(highs, lows, closes, event_index, atr_period)
    if atr is None:
        return None

    entry = closes[event_index]
    profit_level = entry + profit_atr_mult * atr
    stop_level = entry - stop_atr_mult * atr
    end_index = min(len(bars) - 1, event_index + max_horizon_bars)

    for j in range(event_index + 1, end_index + 1):
        if lows[j] <= stop_level:
            return 0
        if highs[j] >= profit_level:
            return 1
    return None


def build_meta_labels(
    bars: list[dict],
    event_mask: list[bool],
    *,
    profit_atr_mult: float = 2.0,
    stop_atr_mult: float = 1.5,
    max_horizon_bars: int = 48,
    atr_period: int = 14,
) -> list[Optional[int]]:
    if len(event_mask) != len(bars):
        raise ValueError("event_mask length must match bars length")

    labels: list[Optional[int]] = [None] * len(bars)
    for index, is_event in enumerate(event_mask):
        if not is_event:
            continue
        labels[index] = label_single_event(
            bars,
            index,
            profit_atr_mult=profit_atr_mult,
            stop_atr_mult=stop_atr_mult,
            max_horizon_bars=max_horizon_bars,
            atr_period=atr_period,
        )
    return labels
