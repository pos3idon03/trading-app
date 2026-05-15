"""In-memory chart overlay: run backtest without persisting to the database."""
import pandas as pd
from sqlalchemy.ext.asyncio import AsyncSession

from dal.market_data_dal import get_asset_id_by_symbol, get_ohlcv, resample_ohlcv
from dtos.backtest_dto import VALID_STRATEGIES, BacktestTimeframe
from features.backtesting.runner import run_backtest
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
) -> pd.DataFrame:
    """Fetch OHLCV rows for the requested slice.

    Falls back to resampling from 5m data when no direct rows are stored for
    the requested timeframe (mirrors the OHLCV chart route behaviour).
    """
    df = await get_ohlcv(session, asset_id=asset_id, timeframe=timeframe, start=start, end=end)
    if df.empty:
        df = await resample_ohlcv(session, asset_id, timeframe, start, end)
        if not df.empty:
            logger.info(
                "chart_overlay_resampled",
                asset_id=asset_id,
                timeframe=timeframe,
            )
    return df


def compute_chart_overlay(
    df: pd.DataFrame,
    strategy_name: str,
    strategy_params: dict,
    timeframe: str,
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
