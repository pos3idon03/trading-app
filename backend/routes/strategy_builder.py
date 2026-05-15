"""Strategy Builder API routes."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from dal.market_data_dal import list_assets
from dal.strategy_builder_dal import (
    attach_algo,
    create_strategy,
    delete_strategy,
    detach_algo,
    get_or_create_strategy,
    get_strategy,
    get_strategy_by_asset,
    list_strategies,
    update_thresholds,
)
from db import get_db
from dtos.strategy_builder_dto import (
    AttachAlgoRequest,
    CreateStrategyRequest,
    DetachAlgoRequest,
    StrategyFullResponse,
    StrategyRecord,
    UpdateThresholdsRequest,
)
from features.strategy_builder.orchestrator import build_full_strategy_response
from utils.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()


@router.post("/create", response_model=StrategyRecord, status_code=201)
async def create_strategy_card(
    request: CreateStrategyRequest,
    session: AsyncSession = Depends(get_db),
) -> StrategyRecord:
    """Create a strategy card for an asset. Only one card per asset is allowed."""
    existing = await get_strategy_by_asset(session, request.asset_id)
    if existing is not None:
        raise HTTPException(
            status_code=409,
            detail=f"A strategy card already exists for asset {request.asset_id}",
        )

    asset_info = await _get_asset_info(session, request.asset_id)
    strategy = await create_strategy(session, request.asset_id)

    return _to_strategy_record(strategy, asset_info)


@router.get("/strategies", response_model=list[StrategyRecord])
async def list_strategy_cards(
    session: AsyncSession = Depends(get_db),
) -> list[StrategyRecord]:
    """Return all active strategy cards."""
    rows = await list_strategies(session)
    return [_row_to_strategy_record(r) for r in rows]


@router.get("/{strategy_id}/full", response_model=StrategyFullResponse)
async def get_full_strategy(
    strategy_id: int,
    session: AsyncSession = Depends(get_db),
) -> StrategyFullResponse:
    """Return the full strategy card including MC, AI agents, financials and algo strategies."""
    strategy = await get_strategy(session, strategy_id)
    if strategy is None:
        raise HTTPException(status_code=404, detail=f"Strategy {strategy_id} not found")

    asset_info = await _get_asset_info(session, strategy.asset_id)
    return await build_full_strategy_response(
        session,
        strategy=strategy,
        symbol=asset_info["symbol"],
        asset_name=asset_info.get("name"),
    )


@router.patch("/{strategy_id}/thresholds", response_model=StrategyRecord)
async def update_strategy_thresholds(
    strategy_id: int,
    request: UpdateThresholdsRequest,
    session: AsyncSession = Depends(get_db),
) -> StrategyRecord:
    """Partially update MC/AI thresholds, combination mode, timeframe, and auto-trading flag."""
    updates = request.model_dump(exclude_none=True)
    strategy = await update_thresholds(session, strategy_id, updates)
    if strategy is None:
        raise HTTPException(status_code=404, detail=f"Strategy {strategy_id} not found")

    asset_info = await _get_asset_info(session, strategy.asset_id)
    return _to_strategy_record(strategy, asset_info)


@router.post("/attach-algo", response_model=StrategyRecord, status_code=201)
async def attach_algo_to_strategy(
    request: AttachAlgoRequest,
    session: AsyncSession = Depends(get_db),
) -> StrategyRecord:
    """Attach an algo strategy definition to a strategy card. Auto-creates the card if absent."""
    strategy = await get_or_create_strategy(session, request.asset_id)
    await attach_algo(session, strategy.id, request.strategy_name, request.params)

    asset_info = await _get_asset_info(session, request.asset_id)
    return _to_strategy_record(strategy, asset_info)


@router.delete("/detach-algo")
async def detach_algo_from_strategy(
    request: DetachAlgoRequest,
    session: AsyncSession = Depends(get_db),
) -> dict:
    """Remove an algo strategy link from a strategy card."""
    removed = await detach_algo(session, request.strategy_id, request.algo_attachment_id)
    if not removed:
        raise HTTPException(status_code=404, detail="Algo attachment not found")
    return {"removed": True}


@router.delete("/{strategy_id}")
async def delete_strategy_card(
    strategy_id: int,
    session: AsyncSession = Depends(get_db),
) -> dict:
    """Delete a strategy card and all its linked algo strategies."""
    deleted = await delete_strategy(session, strategy_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Strategy {strategy_id} not found")
    return {"deleted": True}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _get_asset_info(session: AsyncSession, asset_id: int) -> dict:
    """Resolve asset symbol and name from asset_id."""
    assets = await list_assets(session)
    for asset in assets:
        if asset["id"] == asset_id:
            return asset
    raise HTTPException(status_code=404, detail=f"Asset {asset_id} not found")


def _to_strategy_record(strategy, asset_info: dict) -> StrategyRecord:
    return StrategyRecord(
        id=strategy.id,
        asset_id=strategy.asset_id,
        symbol=asset_info["symbol"],
        asset_name=asset_info.get("name"),
        is_active=strategy.is_active,
        mc_buy_prob_positive=strategy.mc_buy_prob_positive,
        mc_sell_prob_positive=strategy.mc_sell_prob_positive,
        ai_buy_conviction=strategy.ai_buy_conviction,
        ai_sell_conviction=strategy.ai_sell_conviction,
        ai_buy_sentiment=strategy.ai_buy_sentiment,
        ai_sell_sentiment=strategy.ai_sell_sentiment,
        ai_buy_macro=strategy.ai_buy_macro,
        ai_sell_macro=strategy.ai_sell_macro,
        combination_mode=strategy.combination_mode,
        algo_timeframe=strategy.algo_timeframe,
        auto_trading_enabled=strategy.auto_trading_enabled,
        auto_trading_started=strategy.auto_trading_started,
        max_amount_per_position=strategy.max_amount_per_position,
        max_pct_of_capital=strategy.max_pct_of_capital,
        created_at=strategy.created_at,
        updated_at=strategy.updated_at,
    )


def _row_to_strategy_record(r: dict) -> StrategyRecord:
    return StrategyRecord(
        id=r["strategy_id"],
        asset_id=r["asset_id"],
        symbol=r["symbol"],
        asset_name=r.get("asset_name"),
        is_active=r["is_active"],
        mc_buy_prob_positive=r.get("mc_buy_prob_positive"),
        mc_sell_prob_positive=r.get("mc_sell_prob_positive"),
        ai_buy_conviction=r.get("ai_buy_conviction"),
        ai_sell_conviction=r.get("ai_sell_conviction"),
        ai_buy_sentiment=r.get("ai_buy_sentiment"),
        ai_sell_sentiment=r.get("ai_sell_sentiment"),
        ai_buy_macro=r.get("ai_buy_macro"),
        ai_sell_macro=r.get("ai_sell_macro"),
        combination_mode=r.get("combination_mode", "all"),
        algo_timeframe=r.get("algo_timeframe", "1d"),
        auto_trading_enabled=r.get("auto_trading_enabled", False),
        auto_trading_started=r.get("auto_trading_started", False),
        max_amount_per_position=r.get("max_amount_per_position"),
        max_pct_of_capital=r.get("max_pct_of_capital"),
        created_at=r["created_at"],
        updated_at=r["updated_at"],
    )
