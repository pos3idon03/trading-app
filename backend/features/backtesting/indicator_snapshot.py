"""Monthly indicator snapshots for multi-strategy combination backtests.

For each strategy in a combo, computes the key indicator readings at month-end
and the strategy's position state (Buy / Sell).  Used to populate the monthly
breakdown table returned by the /combo endpoint.
"""
import numpy as np
import pandas as pd

from features.backtesting.combo_runner import (
    ComboStrategyConfig,
    _signals_to_position,
    combine_signals,
)
from features.backtesting.indicator_functions import INDICATOR_MAP, _empty_indicators
from features.backtesting.strategies import build_signal_array


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
) -> tuple[pd.DataFrame, tuple]:
    """Compute resampled indicator+position DataFrame and raw signals for one strategy."""
    entries, exits = build_signal_array(df, cfg.strategy_name, cfg.strategy_params)
    position = _signals_to_position(entries, exits).reset_index(drop=True)
    indicator_fn = INDICATOR_MAP.get(cfg.strategy_name, _empty_indicators)
    ind_df = indicator_fn(df, cfg.strategy_params).reset_index(drop=True)
    ind_df["_position"] = position.values
    ind_df.index = time_idx
    return ind_df.resample("ME").last(), (entries, exits)


def _row_indicators(row: pd.Series) -> dict[str, float | None]:
    return {
        col: _safe_float(row[col])
        for col in row.index
        if col != "_position"
    }


def _position_label(current: bool) -> str:
    """Return Buy or Sell based on the current month-end position state.

    Buy  — strategy is currently in position (long).
    Sell — strategy is currently out of position (flat / short).
    """
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
            cur_pos = bool(row["_position"]) if "_position" in row.index else False
            strategy_states.append({
                "strategy_name": cfg.strategy_name,
                "position": _position_label(cur_pos),
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
) -> list[dict]:
    """Return one dict per calendar month with per-strategy indicator values and positions.

    Each dict matches the ComboMonthlyRow DTO shape.
    """
    time_idx = _get_time_index(df)
    strategy_dfs: list[pd.DataFrame] = []
    signal_list: list[tuple] = []

    for cfg in strategies:
        monthly_df, signals = _build_strategy_monthly_df(df, cfg, time_idx)
        strategy_dfs.append(monthly_df)
        signal_list.append(signals)

    weights = [cfg.weight for cfg in strategies]
    combo_e, combo_x = combine_signals(signal_list, mode, weights, threshold)
    combo_pos = _signals_to_position(combo_e, combo_x).reset_index(drop=True)
    combo_pos.index = time_idx
    combo_monthly = combo_pos.resample("ME").last()

    return _build_monthly_rows(strategies, strategy_dfs, combo_monthly)
