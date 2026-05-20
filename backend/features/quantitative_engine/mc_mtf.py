"""Multi-timeframe context for MC backtest: regime/structure features aligned to execution bars."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from features.quantitative_engine.regime_weight import calc_adx, trend_weight_from_adx
from utils.timeframes import finest_timeframe, normalize_timeframe, validate_signal_timeframe

_PANDAS_RULE: dict[str, str] = {
    "5m": "5min",
    "15m": "15min",
    "30m": "30min",
    "1h": "h",
    "4h": "4h",
    "1d": "D",
    "1w": "W",
}


@dataclass
class MtfBarContext:
    """Per execution-bar multi-timeframe regime context (no future leakage)."""
    regime_adx: float | None = None
    regime_w_trend: float | None = None
    structure_adx: float | None = None
    structure_w_trend: float | None = None


def mc_data_load_timeframe(
    execution_tf: str,
    regime_tf: str | None,
    structure_tf: str | None,
) -> str:
    """Finest OHLCV frequency needed for execution + optional MTF legs."""
    tfs = [normalize_timeframe(execution_tf)]
    if regime_tf:
        tfs.append(validate_signal_timeframe(regime_tf))
    if structure_tf:
        tfs.append(validate_signal_timeframe(structure_tf))
    return finest_timeframe(tfs)


def resample_ohlcv_df(df: pd.DataFrame, timeframe: str) -> pd.DataFrame:
    """Resample OHLCV rows to the target timeframe (mirrors backtesting MTF helper)."""
    tf = normalize_timeframe(timeframe)
    rule = _PANDAS_RULE.get(tf)
    if rule is None:
        return df.copy()

    work = df.copy()
    work["time"] = pd.to_datetime(work["time"], utc=True)
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
    return out


def align_series_to_execution(
    values: pd.Series,
    leg_df: pd.DataFrame,
    exec_df: pd.DataFrame,
) -> pd.Series:
    """Forward-fill per-leg values onto the execution timeframe index."""
    leg_times = pd.DatetimeIndex(pd.to_datetime(leg_df["time"], utc=True))
    st = pd.Series(values.values, index=leg_times)
    exec_times = pd.DatetimeIndex(pd.to_datetime(exec_df["time"], utc=True))
    aligned = st.reindex(exec_times, method="ffill")
    aligned.index = exec_df.index
    return aligned


def _adx_on_df(df: pd.DataFrame, period: int) -> pd.Series:
    return calc_adx(
        df["high"].astype(float),
        df["low"].astype(float),
        df["close"].astype(float),
        period=period,
    )


def _build_htf_w_trend_series(
    full_df: pd.DataFrame,
    eval_df: pd.DataFrame,
    htf: str,
    adx_period: int,
    adx_low: float,
    adx_high: float,
) -> pd.Series:
    """ADX-based trend weight on higher TF, forward-filled to execution index."""
    leg_df = resample_ohlcv_df(full_df, htf)
    if leg_df.empty:
        return pd.Series(np.nan, index=eval_df.index, dtype=float)
    adx = _adx_on_df(leg_df, adx_period)
    weights = adx.apply(lambda v: trend_weight_from_adx(float(v), low=adx_low, high=adx_high))
    stance = pd.Series(weights.values, index=pd.to_datetime(leg_df["time"], utc=True))
    exec_times = pd.DatetimeIndex(pd.to_datetime(eval_df["time"], utc=True))
    aligned = stance.reindex(exec_times, method="ffill")
    aligned.index = eval_df.index
    return aligned.astype(float)


def build_mtf_context_series(
    full_df: pd.DataFrame,
    eval_df: pd.DataFrame,
    regime_timeframe: str | None,
    structure_timeframe: str | None,
    adx_period: int,
    adx_low: float = 15.0,
    adx_high: float = 25.0,
) -> list[MtfBarContext]:
    """Build aligned MTF context for each execution bar."""
    n = len(eval_df)
    if not regime_timeframe and not structure_timeframe:
        return [MtfBarContext() for _ in range(n)]

    regime_w: pd.Series | None = None
    regime_adx_s: pd.Series | None = None
    if regime_timeframe:
        leg_df = resample_ohlcv_df(full_df, regime_timeframe)
        if not leg_df.empty:
            regime_adx_s = align_series_to_execution(
                _adx_on_df(leg_df, adx_period), leg_df, eval_df,
            )
            regime_w = _build_htf_w_trend_series(
                full_df, eval_df, regime_timeframe, adx_period, adx_low, adx_high,
            )

    struct_w: pd.Series | None = None
    struct_adx_s: pd.Series | None = None
    if structure_timeframe:
        leg_df = resample_ohlcv_df(full_df, structure_timeframe)
        if not leg_df.empty:
            struct_adx_s = align_series_to_execution(
                _adx_on_df(leg_df, adx_period), leg_df, eval_df,
            )
            struct_w = _build_htf_w_trend_series(
                full_df, eval_df, structure_timeframe, adx_period, adx_low, adx_high,
            )

    contexts: list[MtfBarContext] = []
    for i in range(n):
        ctx = MtfBarContext()
        if regime_w is not None:
            v = regime_w.iloc[i]
            ctx.regime_w_trend = float(v) if np.isfinite(v) else None
        if regime_adx_s is not None:
            v = regime_adx_s.iloc[i]
            try:
                ctx.regime_adx = float(v) if v == v else None
            except (TypeError, ValueError):
                ctx.regime_adx = None
        if struct_w is not None:
            v = struct_w.iloc[i]
            ctx.structure_w_trend = float(v) if np.isfinite(v) else None
        if struct_adx_s is not None:
            v = struct_adx_s.iloc[i]
            try:
                ctx.structure_adx = float(v) if v == v else None
            except (TypeError, ValueError):
                ctx.structure_adx = None
        contexts.append(ctx)
    return contexts


def mtf_allows_buy(
    ctx: MtfBarContext | None,
    model_type: str,
    gate_enabled: bool,
    regime_min_trend_weight: float,
    structure_veto_enabled: bool,
    structure_max_trend_weight: float,
) -> bool:
    """Return False to block a BUY based on higher-timeframe context."""
    if not gate_enabled or ctx is None:
        return True
    if ctx.regime_w_trend is not None:
        if model_type in ("merton", "vasicek", "blended"):
            if ctx.regime_w_trend < regime_min_trend_weight:
                return False
        elif model_type == "ou_deviation":
            max_rev = 1.0 - regime_min_trend_weight
            if ctx.regime_w_trend > max_rev:
                return False
    if structure_veto_enabled and ctx.structure_w_trend is not None:
        if ctx.structure_w_trend > structure_max_trend_weight:
            return False
    return True
