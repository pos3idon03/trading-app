from datetime import datetime, timezone

_DAILY_PLUS_TIMEFRAMES = frozenset({"1d", "1w", "1mo"})


def walk_forward_simulation_start_index(train_bars: int) -> int:
    if train_bars < 1:
        raise ValueError("train_bars must be at least 1")
    return train_bars


def slice_simulation_window(
    bars: list[dict],
    signals: list[str],
    start_index: int,
) -> tuple[list[dict], list[str]]:
    if start_index < 0:
        raise ValueError("start_index must be non-negative")
    if len(signals) != len(bars):
        raise ValueError(
            f"Signal count ({len(signals)}) must match bar count ({len(bars)})"
        )
    if start_index >= len(bars):
        raise ValueError(
            f"start_index ({start_index}) must be less than bar count ({len(bars)})"
        )
    return bars[start_index:], signals[start_index:]


def format_simulation_start_date(bar: dict, decision_timeframe: str) -> str:
    bar_time = bar["time"]
    if decision_timeframe in _DAILY_PLUS_TIMEFRAMES:
        if hasattr(bar_time, "date"):
            return bar_time.date().isoformat()
        return str(bar_time)[:10]
    if isinstance(bar_time, datetime):
        dt = bar_time if bar_time.tzinfo else bar_time.replace(tzinfo=timezone.utc)
        return dt.isoformat().replace("+00:00", "Z")
    return str(bar_time)


def build_simulation_metadata(
    *,
    bars: list[dict],
    start_index: int,
    decision_timeframe: str,
) -> dict:
    return {
        "simulation_start_bar_index": start_index,
        "simulation_start_date": format_simulation_start_date(
            bars[start_index],
            decision_timeframe,
        ),
        "pre_oos_bars_excluded": start_index,
    }
