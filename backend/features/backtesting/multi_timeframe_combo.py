"""Multi-timeframe combo signal building: per-leg signal TF, execution TF alignment."""
from __future__ import annotations

import pandas as pd

from features.backtesting.combo_runner import ComboStrategyConfig, combine_signals
from features.backtesting.stance import compute_strategy_stance
from utils.timeframes import finest_timeframe, normalize_timeframe

_PANDAS_RULE: dict[str, str] = {
    "5m": "5min",
    "15m": "15min",
    "30m": "30min",
    "1h": "h",
    "4h": "4h",
    "1d": "D",
    "1w": "W",
}


def combo_data_load_timeframe(execution_tf: str, leg_timeframes: list[str]) -> str:
    """OHLCV load frequency: finest among execution and all leg signal timeframes."""
    return finest_timeframe([normalize_timeframe(execution_tf), *leg_timeframes])


def resample_ohlcv_df(df: pd.DataFrame, timeframe: str) -> pd.DataFrame:
    """Resample OHLCV rows to the target timeframe."""
    tf = normalize_timeframe(timeframe)
    rule = _PANDAS_RULE.get(tf)
    if rule is None:
        return df.copy()

    work = df.copy()
    work["time"] = pd.to_datetime(work["time"])
    indexed = work.set_index("time")
    if len(indexed) < 2:
        return work.reset_index(drop=True)

    ohlc = indexed.resample(rule).agg(
        {
            "open": "first",
            "high": "max",
            "low": "min",
            "close": "last",
            "volume": "sum",
        }
    ).dropna(how="any")
    out = ohlc.reset_index()
    out.rename(columns={"index": "time"}, inplace=True)
    return out


def align_stance_to_execution(
    stance: pd.Series,
    leg_df: pd.DataFrame,
    exec_df: pd.DataFrame,
) -> pd.Series:
    """Forward-fill per-leg stance onto the execution timeframe index."""
    leg_times = pd.to_datetime(leg_df["time"].values)
    st = pd.Series(stance.values, index=leg_times)
    exec_times = pd.to_datetime(exec_df["time"].values)
    aligned = st.reindex(exec_times, method="ffill")
    aligned.index = exec_df.index
    return aligned.fillna("Neutral").astype(str)


def build_multi_tf_combo_signals(
    base_df: pd.DataFrame,
    strategies: list[ComboStrategyConfig],
    execution_timeframe: str,
    mode: str,
    threshold: float,
) -> tuple[pd.Series, pd.Series]:
    """Build combined entry/exit bars on the execution timeframe grid."""
    exec_df = resample_ohlcv_df(base_df, execution_timeframe)
    stance_list: list[pd.Series] = []

    for cfg in strategies:
        leg_tf = normalize_timeframe(cfg.timeframe or execution_timeframe)
        leg_df = resample_ohlcv_df(base_df, leg_tf)
        stance = compute_strategy_stance(leg_df, cfg.strategy_name, cfg.strategy_params)
        stance_list.append(align_stance_to_execution(stance, leg_df, exec_df))

    weights = [cfg.weight for cfg in strategies]
    return combine_signals(stance_list, mode, weights, threshold)
