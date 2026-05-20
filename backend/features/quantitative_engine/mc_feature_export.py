"""Export walk-forward feature rows for offline ML training."""
from __future__ import annotations

import csv
from pathlib import Path

import pandas as pd

from features.quantitative_engine.mc_backtest import (
    McBacktestConfig,
    McBacktestResult,
    _collect_walk_forward_rows,
)
from features.quantitative_engine.mc_features import FEATURE_NAMES


def export_backtest_features(
    full_df: pd.DataFrame,
    config: McBacktestConfig,
    out_path: Path,
) -> int:
    """Run walk-forward collection and write CSV for train_models.py."""
    rows = _collect_walk_forward_rows(full_df, config)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = (
        list(FEATURE_NAMES)
        + ["time", "label_prob", "label_buy_threshold", "label_sell_threshold", "label_w_trend"]
    )
    with out_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
    return len(rows)


def label_rows_from_result(
    result: McBacktestResult,
    config: McBacktestConfig,
) -> list[dict]:
    """Attach labels from a completed backtest signal log (for re-export)."""
    labels = []
    prior: list[float] = []
    for entry in result.signal_log:
        prob = entry.get("effective_prob") or entry.get("prob_positive")
        if prob is None:
            continue
        forward_ret = entry.get("forward_return_1")
        label_buy = config.buy_threshold
        label_sell = config.sell_threshold
        if forward_ret is not None:
            if forward_ret > 0:
                label_buy = max(0.01, float(prob) - 0.02)
            else:
                label_sell = min(0.99, float(prob) + 0.02)
        labels.append({
            "label_prob": prob,
            "label_buy_threshold": label_buy,
            "label_sell_threshold": label_sell,
            "label_w_trend": entry.get("regime_weight") or 0.5,
        })
        prior.append(float(prob))
    return labels
