from typing import Optional

from features.backtesting.trade_exits import (
    atr_at_bar_index,
    atr_bracket_levels,
    intrabar_long_exit,
)


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

    closes = [float(b["close"]) for b in bars]
    atr = atr_at_bar_index(bars, event_index, atr_period)
    if atr is None:
        return None

    entry = closes[event_index]
    profit_level, stop_level = atr_bracket_levels(
        entry,
        atr,
        profit_atr_mult=profit_atr_mult,
        stop_atr_mult=stop_atr_mult,
    )
    end_index = min(len(bars) - 1, event_index + max_horizon_bars)

    for j in range(event_index + 1, end_index + 1):
        hit = intrabar_long_exit(
            float(bars[j]["high"]),
            float(bars[j]["low"]),
            profit_level=profit_level,
            stop_level=stop_level,
        )
        if hit == "stop":
            return 0
        if hit == "profit":
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
