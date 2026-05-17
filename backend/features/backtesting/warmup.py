"""Indicator warm-up: extra OHLCV before the evaluation window for rolling indicators."""
from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd
from sqlalchemy.ext.asyncio import AsyncSession

from dal.market_data_dal import get_ohlcv, resample_ohlcv

WARMUP_BUFFER_BARS = 5

# (param_key, default) pairs — max value drives warm-up length per strategy.
_STRATEGY_WARMUP_KEYS: dict[str, tuple[tuple[str, int], ...]] = {
    "ma_crossover": (("slow_window", 50), ("fast_window", 10)),
    "sma_cross": (("slow_window", 200), ("fast_window", 50)),
    "ema_cross": (("slow_span", 26), ("fast_span", 12)),
    "sma_break": (("sma_window", 200),),
    "macd": (("slow", 26), ("signal", 9), ("fast", 12)),
    "rsi": (("period", 14),),
    "lrsi": (("gamma", 1),),  # short effective warm-up; series stabilizes quickly
    "stoch_rsi": (
        ("rsi_period", 14),
        ("stoch_period", 14),
        ("smooth_k", 3),
        ("smooth_d", 3),
    ),
    "aroon": (("period", 52),),
    "momentum_rotation": (("long_window", 60), ("short_window", 20)),
    "new_high_low": (("lookback", 252),),
    "mean_reversion": (("lookback", 20),),
    "mean_reversion_trend": (("ma_window", 50), ("adx_period", 14)),
    "mean_reversion_range": (("bb_window", 20), ("adx_period", 14)),
    "reverting_market": (("rsi_period", 14), ("adx_period", 14)),
    "breakout": (
        ("squeeze_lookback", 120),
        ("donchian_window", 20),
        ("bb_window", 20),
    ),
    "range_breakout": (("lookback", 20),),
    "trend_pullback": (
        ("adx_period", 14),
        ("stoch_period", 14),
        ("stoch_smooth", 3),
    ),
    "vrp_harvest": (("iv_proxy_window", 60), ("rv_window", 20)),
    "atr_trailing_stop": (("trend_ma", 50), ("atr_period", 14)),
    "wedge_compression": (("compression_lookback", 20), ("atr_period", 14)),
    "grid_trading": (("num_levels", 5),),
    "vwap_cross": (),
    "orb": (("opening_bars", 6),),
    "gap_fade": (),
    "seasonal": (),
}

_BAR_DURATION: dict[str, timedelta] = {
    "5m": timedelta(minutes=5),
    "15m": timedelta(minutes=15),
    "30m": timedelta(minutes=30),
    "1h": timedelta(hours=1),
    "4h": timedelta(hours=4),
    "1d": timedelta(days=1),
    "1w": timedelta(weeks=1),
}


def _max_param(params: dict, keys: tuple[tuple[str, int], ...]) -> int:
    if not keys:
        return 0
    return max(int(params.get(k, default)) for k, default in keys)


def required_warmup_bars(strategy: str, params: dict | None = None) -> int:
    """Bars of history needed before evaluation start (includes buffer)."""
    p = params or {}
    keys = _STRATEGY_WARMUP_KEYS.get(strategy, ())
    base = _max_param(p, keys)
    if strategy == "stoch_rsi":
        base = (
            int(p.get("rsi_period", 14))
            + int(p.get("stoch_period", 14))
            + int(p.get("smooth_k", 3))
            + int(p.get("smooth_d", 3))
        )
    if strategy == "grid_trading":
        base = int(p.get("num_levels", 5)) * 10
    return base + WARMUP_BUFFER_BARS


def max_warmup_bars(strategies: list[tuple[str, dict | None]]) -> int:
    if not strategies:
        return WARMUP_BUFFER_BARS
    return max(required_warmup_bars(name, params) for name, params in strategies)


def max_warmup_bars_from_grid(strategy: str, param_grid: dict) -> int:
    """Max warm-up across all combinations in an optimization grid."""
    if not param_grid:
        return required_warmup_bars(strategy, {})
    keys = list(param_grid.keys())
    max_bars = 0
    lengths = [len(v) for v in param_grid.values()]
    total = 1
    for n in lengths:
        total *= n
    if total > 500:
        merged = dict(param_grid)
        for k, vals in param_grid.items():
            merged[k] = max(vals) if vals else 0
        return required_warmup_bars(strategy, merged)
    from itertools import product

    for combo in product(*param_grid.values()):
        params = dict(zip(keys, combo))
        max_bars = max(max_bars, required_warmup_bars(strategy, params))
    return max_bars


def warmup_start_datetime(
    start: datetime,
    bars: int,
    timeframe: str,
) -> datetime:
    """Earliest timestamp to request from OHLCV store for warm-up."""
    if bars <= 0:
        return _ensure_utc(start)
    start = _ensure_utc(start)
    if timeframe in ("1d", "1w"):
        days = int(bars * 1.5) + 5
        if timeframe == "1w":
            days = int(bars * 7 * 1.2) + 7
        return start - timedelta(days=days)
    bar_td = _BAR_DURATION.get(timeframe, timedelta(days=1))
    return start - bar_td * (bars + 10)


def _ensure_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def evaluation_mask(df: pd.DataFrame, evaluation_start: datetime) -> pd.Series:
    times = pd.to_datetime(df["time"], utc=True)
    start = pd.Timestamp(_ensure_utc(evaluation_start))
    return times >= start


def slice_series_by_time(
    series: pd.Series,
    df: pd.DataFrame,
    evaluation_start: datetime,
) -> pd.Series:
    mask = evaluation_mask(df, evaluation_start)
    out = series.loc[mask].reset_index(drop=True)
    out.index = df.loc[mask].index
    return out


def slice_time_series_rows(rows: list[dict], evaluation_start: datetime) -> list[dict]:
    start = pd.Timestamp(_ensure_utc(evaluation_start))
    return [r for r in rows if pd.Timestamp(r["time"], tz="UTC") >= start]


def slice_trade_log(trades: list[dict], evaluation_start: datetime) -> list[dict]:
    start = pd.Timestamp(_ensure_utc(evaluation_start))
    out = []
    for t in trades:
        entry = t.get("entry_time", "")
        if not entry:
            continue
        try:
            if pd.Timestamp(entry, tz="UTC") >= start:
                out.append(t)
        except (TypeError, ValueError):
            out.append(t)
    return out


def filter_monthly_rows(rows: list[dict], evaluation_start: datetime) -> list[dict]:
    start_month = _ensure_utc(evaluation_start).strftime("%Y-%m")
    return [r for r in rows if r.get("month", "") >= start_month]


async def load_ohlcv_with_warmup(
    session: AsyncSession,
    asset_id: int,
    start: datetime,
    end: datetime,
    timeframe: str,
    warmup_bars: int,
    query_args: dict,
) -> pd.DataFrame:
    """Load OHLCV including pre-start bars for indicator warm-up."""
    query_start = warmup_start_datetime(start, warmup_bars, timeframe)
    df = await get_ohlcv(
        session,
        asset_id=asset_id,
        start=query_start,
        end=end,
        **query_args,
    )
    if df.empty:
        df = await resample_ohlcv(
            session, asset_id, query_args.get("timeframe", timeframe), query_start, end
        )
    return df


def count_evaluation_rows(df: pd.DataFrame, evaluation_start: datetime | None) -> int:
    if evaluation_start is None:
        return len(df)
    return int(evaluation_mask(df, evaluation_start).sum())


def slice_df_segment(
    df: pd.DataFrame,
    segment_start: datetime,
    segment_end: datetime,
    warmup_bars: int,
) -> tuple[pd.DataFrame, datetime]:
    """Return df rows from warm-up through segment_end; evaluation starts at segment_start."""
    times = pd.to_datetime(df["time"], utc=True)
    seg_start = pd.Timestamp(_ensure_utc(segment_start))
    seg_end = pd.Timestamp(_ensure_utc(segment_end))
    in_seg = (times >= seg_start) & (times <= seg_end)
    if not in_seg.any():
        return df.iloc[0:0], segment_start
    positions = np.where(in_seg.values)[0]
    start_pos = max(0, int(positions[0]) - warmup_bars)
    end_pos = int(positions[-1]) + 1
    chunk = df.iloc[start_pos:end_pos].reset_index(drop=True)
    return chunk, segment_start
