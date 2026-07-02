from typing import Optional

from features.backtesting.bar_context import MultiTimeframeContext
from features.backtesting.indicators import compute_rsi, compute_sma
from features.ml.price_features import (
    FEATURE_WARMUP_BARS,
    _pct_return,
    _rolling_vol,
    _sma_distance,
)

_CONTEXT_SUFFIXES = ("ret_5", "ret_20", "rsi_14", "sma20_dist")


def _compact_features_for_bars(
    bars: list[dict],
    *,
    warmup_bars: int = FEATURE_WARMUP_BARS,
) -> list[Optional[list[float]]]:
    if not bars:
        return []

    closes = [float(b["close"]) for b in bars]
    rsi = compute_rsi(closes, 14)
    sma20 = compute_sma(closes, 20)
    rows: list[Optional[list[float]]] = []

    for index in range(len(bars)):
        if index < warmup_bars:
            rows.append(None)
            continue
        values = [
            _pct_return(closes, index, 5),
            _pct_return(closes, index, 20),
            rsi[index],
            _sma_distance(closes, sma20, index),
        ]
        if any(value is None for value in values):
            rows.append(None)
            continue
        rows.append([float(value) for value in values])
    return rows


def build_context_feature_matrix(
    bar_context: MultiTimeframeContext,
    context_timeframes: list[str],
    *,
    warmup_bars: int = FEATURE_WARMUP_BARS,
) -> tuple[list[str], list[Optional[list[float]]], list[str]]:
    decision_count = len(bar_context.decision_bars)
    if not context_timeframes:
        return [], [], []

    feature_names: list[str] = []
    per_tf_rows: list[list[Optional[list[float]]]] = []
    warnings: list[str] = []

    for timeframe in context_timeframes:
        if timeframe == bar_context.decision_timeframe:
            warnings.append(f"Skipping context timeframe {timeframe} (same as decision timeframe).")
            continue
        if timeframe not in bar_context.bars_by_timeframe:
            warnings.append(f"Context timeframe {timeframe} has no loaded bars; omitted.")
            continue

        tf_names = [f"ctx_{timeframe}_{suffix}" for suffix in _CONTEXT_SUFFIXES]
        tf_bars = bar_context.bars_for(timeframe)
        tf_features = _compact_features_for_bars(tf_bars, warmup_bars=warmup_bars)
        aligned: list[Optional[list[float]]] = []

        for decision_index in range(decision_count):
            signal_index = bar_context.aligned_index(decision_index, timeframe)
            if signal_index < 0 or signal_index >= len(tf_features):
                aligned.append(None)
                continue
            aligned.append(tf_features[signal_index])

        feature_names.extend(tf_names)
        per_tf_rows.append(aligned)

    if not feature_names:
        return [], [], warnings

    merged: list[Optional[list[float]]] = []
    for row_index in range(decision_count):
        combined: list[float] = []
        row_complete = True
        for tf_rows in per_tf_rows:
            row = tf_rows[row_index]
            if row is None:
                row_complete = False
                break
            combined.extend(row)
        merged.append(combined if row_complete else None)

    return feature_names, merged, warnings
