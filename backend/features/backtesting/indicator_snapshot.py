"""Monthly indicator snapshots for multi-strategy combination backtests.

For each strategy in a combo, computes the key indicator readings at month-end
and the strategy's stance (Buy / Neutral / Sell).  Used to populate the monthly
breakdown table returned by the /combo endpoint.
"""
import numpy as np
import pandas as pd

from features.backtesting.combo_runner import ComboStrategyConfig
from features.backtesting.indicator_functions import INDICATOR_MAP, _empty_indicators
from datetime import datetime

from features.backtesting.stance import (
    STANCE_BUY,
    STANCE_SELL,
    combine_stances,
    compute_strategy_stance,
)
from features.backtesting.warmup import filter_monthly_rows


# ---------------------------------------------------------------------------
# Monthly breakdown computation
# ---------------------------------------------------------------------------

def _safe_float(value) -> float | None:
    """Convert to float, returning None for NaN / inf / non-numeric."""
    try:
        f = float(value)
        return None if not np.isfinite(f) else round(f, 2)
    except (TypeError, ValueError):
        return None


def _get_time_index(df: pd.DataFrame) -> pd.DatetimeIndex:
    if "time" in df.columns:
        return pd.DatetimeIndex(pd.to_datetime(df["time"]).values)
    return pd.DatetimeIndex(pd.to_datetime(df.index))


def _build_strategy_monthly_df(
    df: pd.DataFrame,
    cfg: ComboStrategyConfig,
    time_idx: pd.DatetimeIndex,
) -> pd.DataFrame:
    """Compute resampled indicator + stance DataFrame for one strategy."""
    stance = compute_strategy_stance(df, cfg.strategy_name, cfg.strategy_params)
    indicator_fn = INDICATOR_MAP.get(cfg.strategy_name, _empty_indicators)
    ind_df = indicator_fn(df, cfg.strategy_params).reset_index(drop=True)
    ind_df["_stance"] = stance.reset_index(drop=True).values
    ind_df.index = time_idx
    return ind_df.resample("ME").last()


def _row_indicators(row: pd.Series) -> dict[str, float | None]:
    return {
        col: _safe_float(row[col])
        for col in row.index
        if col not in ("_position", "_stance")
    }


def _stance_label(stance: str) -> str:
    return stance if stance in (STANCE_BUY, STANCE_SELL, "Neutral") else "Neutral"


def _position_label(current: bool) -> str:
    return "Buy" if current else "Sell"


def _build_monthly_rows(
    strategies: list[ComboStrategyConfig],
    strategy_dfs: list[pd.DataFrame],
    combo_monthly: pd.Series,
) -> list[dict]:
    month_index = strategy_dfs[0].index
    rows = []
    for month_ts in month_index:
        strategy_states = []
        for cfg, sdf in zip(strategies, strategy_dfs):
            if month_ts not in sdf.index:
                continue
            row = sdf.loc[month_ts]
            cur_stance = str(row["_stance"]) if "_stance" in row.index else "Neutral"
            strategy_states.append({
                "strategy_name": cfg.strategy_name,
                "position": _stance_label(cur_stance),
                "indicators": _row_indicators(row),
            })
        cur_combo = month_ts in combo_monthly.index and bool(combo_monthly.loc[month_ts])
        rows.append({
            "month": month_ts.strftime("%Y-%m"),
            "combined_position": _position_label(cur_combo),
            "strategies": strategy_states,
        })
    return rows


def compute_monthly_breakdown(
    df: pd.DataFrame,
    strategies: list[ComboStrategyConfig],
    mode: str,
    threshold: float = 0.5,
    evaluation_start: datetime | None = None,
) -> list[dict]:
    """Return one dict per calendar month with per-strategy indicator values and positions.

    Each dict matches the ComboMonthlyRow DTO shape.
    """
    time_idx = _get_time_index(df)
    strategy_dfs: list[pd.DataFrame] = []
    stance_list: list[pd.Series] = []

    for cfg in strategies:
        strategy_dfs.append(_build_strategy_monthly_df(df, cfg, time_idx))
        stance_list.append(
            compute_strategy_stance(df, cfg.strategy_name, cfg.strategy_params)
        )

    weights = [cfg.weight for cfg in strategies]
    combo_pos = combine_stances(stance_list, mode, weights, threshold)
    combo_pos.index = time_idx
    combo_monthly = combo_pos.resample("ME").last()

    rows = _build_monthly_rows(strategies, strategy_dfs, combo_monthly)
    if evaluation_start is not None:
        return filter_monthly_rows(rows, evaluation_start)
    return rows
