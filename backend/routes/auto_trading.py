"""Auto-Trading dashboard API routes."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from dal.strategy_builder_dal import (
    get_strategy,
    list_auto_trading_assets,
    update_position_sizing,
)
from db import get_db
from dtos.strategy_builder_dto import AutoTradingAssetRow, UpdatePositionSizingRequest
from features.execution.auto_trading_loop import run_auto_trading_cycle
from features.live_trading.live_engine import get_resampler
from features.live_trading.stream_orchestrator import sync_stream_with_running_assets
from utils.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()


@router.get("/assets", response_model=list[AutoTradingAssetRow])
async def list_auto_trading(
    session: AsyncSession = Depends(get_db),
) -> list[AutoTradingAssetRow]:
    """Return all assets with auto-trading enabled, enriched with latest MC/AI values."""
    rows = await list_auto_trading_assets(session)
    return [_row_to_dto(r) for r in rows]


@router.patch("/{strategy_id}/start", response_model=AutoTradingAssetRow)
async def start_auto_trading(
    strategy_id: int,
    request: UpdatePositionSizingRequest,
    session: AsyncSession = Depends(get_db),
) -> AutoTradingAssetRow:
    """Start auto-trading for an asset, persisting position sizing configuration."""
    strategy = await get_strategy(session, strategy_id)
    if strategy is None:
        raise HTTPException(status_code=404, detail=f"Strategy {strategy_id} not found")
    if not strategy.auto_trading_enabled:
        raise HTTPException(
            status_code=409,
            detail="Auto-trading is not enabled for this strategy. Enable it in Strategy Builder first.",
        )

    await update_position_sizing(
        session,
        strategy_id=strategy_id,
        started=True,
        max_amount=request.max_amount_per_position,
        max_pct=request.max_pct_of_capital,
    )

    rows = await list_auto_trading_assets(session)
    row = next((r for r in rows if r["strategy_id"] == strategy_id), None)
    if row is None:
        raise HTTPException(status_code=500, detail="Failed to reload strategy after start")
    await sync_stream_with_running_assets(session, get_resampler())
    return _row_to_dto(row)


@router.patch("/{strategy_id}/stop", response_model=AutoTradingAssetRow)
async def stop_auto_trading(
    strategy_id: int,
    session: AsyncSession = Depends(get_db),
) -> AutoTradingAssetRow:
    """Stop auto-trading for an asset."""
    strategy = await get_strategy(session, strategy_id)
    if strategy is None:
        raise HTTPException(status_code=404, detail=f"Strategy {strategy_id} not found")

    await update_position_sizing(
        session,
        strategy_id=strategy_id,
        started=False,
        max_amount=None,
        max_pct=None,
    )

    rows = await list_auto_trading_assets(session)
    row = next((r for r in rows if r["strategy_id"] == strategy_id), None)
    if row is None:
        raise HTTPException(status_code=500, detail="Failed to reload strategy after stop")
    await sync_stream_with_running_assets(session, get_resampler())
    return _row_to_dto(row)


@router.post("/evaluate", summary="Manually trigger auto-trading evaluation cycle")
async def trigger_evaluation(
    session: AsyncSession = Depends(get_db),
) -> list[dict]:
    """Run a single auto-trading evaluation cycle on demand (useful for testing)."""
    await sync_stream_with_running_assets(session, get_resampler())
    results = await run_auto_trading_cycle(session, resampler=get_resampler())
    return results


def _row_to_dto(r: dict) -> AutoTradingAssetRow:
    return AutoTradingAssetRow(
        strategy_id=r["strategy_id"],
        asset_id=r["asset_id"],
        symbol=r["symbol"],
        asset_name=r.get("asset_name"),
        asset_type=r.get("asset_type", "stock"),
        mc_prob_positive=r.get("mc_prob_positive"),
        mc_buy_prob_positive=r.get("mc_buy_prob_positive"),
        mc_sell_prob_positive=r.get("mc_sell_prob_positive"),
        ai_conviction=r.get("ai_conviction"),
        ai_sentiment=r.get("ai_sentiment"),
        ai_macro=r.get("ai_macro"),
        ai_buy_conviction=r.get("ai_buy_conviction"),
        ai_sell_conviction=r.get("ai_sell_conviction"),
        ai_buy_sentiment=r.get("ai_buy_sentiment"),
        ai_sell_sentiment=r.get("ai_sell_sentiment"),
        ai_buy_macro=r.get("ai_buy_macro"),
        ai_sell_macro=r.get("ai_sell_macro"),
        combination_mode=r.get("combination_mode", "all"),
        algo_timeframe=r.get("algo_timeframe", "1d"),
        auto_trading_started=r.get("auto_trading_started", False),
        max_amount_per_position=r.get("max_amount_per_position"),
        max_pct_of_capital=r.get("max_pct_of_capital"),
    )
