"""Shared OHLCV bar loading and merge logic for live trading and auto-trading."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from sqlalchemy.ext.asyncio import AsyncSession

from dal.market_data_dal import get_asset_id_by_symbol, get_ohlcv, resample_ohlcv
from features.live_trading.resampler import OHLCVBar, ResamplingEngine
from features.live_trading.strategy_signals import MIN_BARS_REQUIRED

_WEEKLY_LOOKBACK = timedelta(weeks=104)
_DEFAULT_LOOKBACK = timedelta(days=365)

_RESAMPLE_FROM_5M: dict[str, timedelta] = {
    "15m": timedelta(minutes=15),
    "30m": timedelta(minutes=30),
    "1h": timedelta(hours=1),
    "3h": timedelta(hours=3),
    "4h": timedelta(hours=4),
}


def ohlcv_query_args(timeframe: str) -> dict:
    """Return get_ohlcv kwargs; bucket finer stored bars when native TF is absent."""
    if timeframe == "1w":
        return {"timeframe": "1d", "bucket_interval": timedelta(weeks=1)}
    if timeframe in _RESAMPLE_FROM_5M:
        return {"timeframe": "5m", "bucket_interval": _RESAMPLE_FROM_5M[timeframe]}
    return {"timeframe": timeframe}


def bar_timestamp_key(bar) -> str:
    """Normalize a bar timestamp for deduplication."""
    for attr in ("bar_start", "time", "timestamp"):
        val = getattr(bar, attr, None)
        if val is None:
            continue
        if hasattr(val, "isoformat"):
            return val.isoformat()
        return str(val)
    return ""


def df_rows_to_bars(df) -> list:
    """Convert a DataFrame of OHLCV rows into lightweight bar objects."""
    bars = []
    for idx, row in df.iterrows():
        bar_time = row["time"] if "time" in row.index else idx
        if hasattr(bar_time, "isoformat"):
            bar_time = bar_time.isoformat()
        else:
            bar_time = str(bar_time)
        bars.append(SimpleNamespace(
            open=float(row["open"]),
            high=float(row["high"]),
            low=float(row["low"]),
            close=float(row["close"]),
            volume=int(row.get("volume", 0)),
            bar_start=bar_time,
        ))
    return bars


def resampler_bar_to_namespace(bar: OHLCVBar) -> SimpleNamespace:
    return SimpleNamespace(
        open=bar.open,
        high=bar.high,
        low=bar.low,
        close=bar.close,
        volume=bar.volume,
        bar_start=bar.bar_start,
    )


def merge_bars(db_bars: list, resampler_bars: list[OHLCVBar]) -> list:
    """Merge DB history with resampler tail; resampler wins on duplicate timestamps."""
    by_time: dict[str, object] = {}
    for bar in db_bars:
        key = bar_timestamp_key(bar)
        if key:
            by_time[key] = bar
    for bar in resampler_bars:
        key = bar_timestamp_key(bar)
        if key:
            by_time[key] = resampler_bar_to_namespace(bar)
    return [by_time[key] for key in sorted(by_time.keys())]


async def fetch_bars_from_db(
    session: AsyncSession,
    symbol: str,
    timeframe: str,
) -> list:
    """Load historical OHLCV bars from the database for strategy evaluation."""
    asset_id = await get_asset_id_by_symbol(session, symbol)
    if asset_id is None:
        return []

    now = datetime.now(timezone.utc)
    lookback = _WEEKLY_LOOKBACK if timeframe == "1w" else _DEFAULT_LOOKBACK
    start = now - lookback

    query_args = ohlcv_query_args(timeframe)
    df = await get_ohlcv(session, asset_id, start=start, end=now, **query_args)
    if df.empty and timeframe in _RESAMPLE_FROM_5M:
        df = await resample_ohlcv(session, asset_id, timeframe, start, now)
    if df.empty:
        return []
    return df_rows_to_bars(df)


async def count_db_bars(
    session: AsyncSession,
    symbol: str,
    timeframe: str,
) -> int:
    bars = await fetch_bars_from_db(session, symbol, timeframe)
    return len(bars)


async def resolve_bars(
    session: AsyncSession,
    symbol: str,
    timeframe: str,
    resampler: ResamplingEngine | None,
) -> list:
    """Merge DB history with live resampler bars; prefer resampler for the tail."""
    resampler_bars: list[OHLCVBar] = []
    if resampler is not None:
        resampler_bars = resampler.get_bars(symbol, timeframe)

    db_bars = await fetch_bars_from_db(session, symbol, timeframe)
    merged = merge_bars(db_bars, resampler_bars)

    if len(merged) >= MIN_BARS_REQUIRED:
        return merged
    if resampler_bars:
        return [resampler_bar_to_namespace(b) for b in resampler_bars]
    return merged
