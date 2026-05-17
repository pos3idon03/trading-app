"""In-memory chart overlay: run backtest without persisting to the database."""
from datetime import datetime

import pandas as pd
from sqlalchemy.ext.asyncio import AsyncSession

from dal.market_data_dal import get_asset_id_by_symbol, get_ohlcv, resample_ohlcv
from dtos.backtest_dto import VALID_STRATEGIES, BacktestTimeframe
from features.backtesting.runner import run_backtest
from features.backtesting.warmup import load_ohlcv_with_warmup, required_warmup_bars
from utils.logging import get_logger

logger = get_logger(__name__)


async def resolve_asset_id(
    session: AsyncSession,
    asset_id: int | None,
    symbol: str | None,
) -> int | None:
    """Return asset_id by lookup; None if not found."""
    if asset_id is not None:
        return asset_id
    if symbol is not None:
        return await get_asset_id_by_symbol(session, symbol)
    return None


async def load_ohlcv_for_overlay(
    session: AsyncSession,
    asset_id: int,
    timeframe: BacktestTimeframe,
    start=None,
    end=None,
    strategy_name: str | None = None,
    strategy_params: dict | None = None,
    query_args: dict | None = None,
) -> tuple[pd.DataFrame, datetime | None]:
    """Fetch OHLCV rows for the requested slice, with optional indicator warm-up."""
    eval_start = start
    warmup_bars = 0
    if strategy_name and start is not None:
        warmup_bars = required_warmup_bars(strategy_name, strategy_params or {})

    if warmup_bars > 0 and start is not None and query_args is not None:
        df = await load_ohlcv_with_warmup(
            session,
            asset_id=asset_id,
            start=start,
            end=end,
            timeframe=timeframe,
            warmup_bars=warmup_bars,
            query_args=query_args,
        )
        return df, eval_start

    df = await get_ohlcv(session, asset_id=asset_id, timeframe=timeframe, start=start, end=end)
    if df.empty:
        df = await resample_ohlcv(session, asset_id, timeframe, start, end)
        if not df.empty:
            logger.info(
                "chart_overlay_resampled",
                asset_id=asset_id,
                timeframe=timeframe,
            )
    return df, None


def compute_chart_overlay(
    df: pd.DataFrame,
    strategy_name: str,
    strategy_params: dict,
    timeframe: str,
    evaluation_start: datetime | None = None,
) -> dict:
    """Run backtest in-memory and return overlay payload.

    Returns a dict with keys: strategy_name, trade_log, indicator_series, duration_ms.
    Raises ValueError for unknown strategy.
    """
    if strategy_name not in VALID_STRATEGIES:
        raise ValueError(f"Unknown strategy '{strategy_name}'")

    result = run_backtest(
        df,
        strategy=strategy_name,
        params=strategy_params,
        timeframe=timeframe,
        evaluation_start=evaluation_start,
    )
    logger.info(
        "chart_overlay_computed",
        strategy=strategy_name,
        timeframe=timeframe,
        duration_ms=round(result.duration_ms, 2),
    )
    return {
        "strategy_name": strategy_name,
        "trade_log": result.trade_log,
        "indicator_series": result.indicator_series,
        "duration_ms": int(result.duration_ms),
    }
