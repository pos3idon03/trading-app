"""Routes for trade execution, risk management, and portfolio tracking."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from config import get_settings
from dal import execution_dal
from db import get_db
from dtos.execution_dto import (
    ExecutionStatusResponse,
    OrderHistoryResponse,
    OrderResponse,
    PortfolioResponse,
    PositionDTO,
    RiskConfigResponse,
    RiskConfigUpdateRequest,
    RiskEventHistoryResponse,
    RiskEventResponse,
)
from features.execution.portfolio_tracker import get_portfolio_summary, sync_portfolio
from features.execution.risk_manager import get_risk_manager
from features.live_trading.websocket_stream import get_stream
from utils.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()


@router.post("/enable", response_model=ExecutionStatusResponse)
async def enable_execution(session: AsyncSession = Depends(get_db)):
    risk_mgr = get_risk_manager()
    risk_mgr.deactivate_kill_switch()

    portfolio = sync_portfolio()
    await execution_dal.create_risk_event(
        session,
        event_type="execution_enabled",
        description="Paper trading execution enabled",
        severity="info",
    )

    return _build_status_response(session)


@router.post("/disable", response_model=ExecutionStatusResponse)
async def disable_execution(session: AsyncSession = Depends(get_db)):
    risk_mgr = get_risk_manager()
    risk_mgr.activate_kill_switch()

    await execution_dal.create_risk_event(
        session,
        event_type="kill_switch_activated",
        description="Kill switch activated — all trading halted",
        severity="critical",
    )

    return _build_status_response(session)


@router.get("/status", response_model=ExecutionStatusResponse)
async def execution_status(session: AsyncSession = Depends(get_db)):
    return _build_status_response(session)


@router.get("/orders", response_model=OrderHistoryResponse)
async def get_orders(
    symbol: str | None = None,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    session: AsyncSession = Depends(get_db),
):
    orders, total = await execution_dal.get_order_history(
        session, symbol=symbol.upper() if symbol else None, limit=limit, offset=offset,
    )
    return OrderHistoryResponse(
        orders=[_order_to_response(o) for o in orders],
        total=total,
    )


@router.get("/portfolio", response_model=PortfolioResponse)
async def get_portfolio():
    summary = get_portfolio_summary()

    if "error" in summary:
        return PortfolioResponse(equity=0, cash=0, buying_power=0)

    positions = [
        PositionDTO(
            symbol=p["symbol"],
            qty=p["qty"],
            market_value=p["market_value"],
            avg_entry_price=p["avg_entry_price"],
            current_price=p["current_price"],
            unrealized_pnl=p["unrealized_pnl"],
            unrealized_pnl_pct=p["unrealized_pnl_pct"],
        )
        for p in summary.get("positions", [])
    ]

    return PortfolioResponse(
        equity=summary["equity"],
        cash=summary["cash"],
        buying_power=summary["buying_power"],
        daily_pnl=summary.get("daily_pnl"),
        daily_pnl_pct=summary.get("daily_pnl_pct"),
        total_positions=summary.get("total_positions", 0),
        positions=positions,
    )


@router.get("/risk/config", response_model=RiskConfigResponse)
async def get_risk_config():
    settings = get_settings()
    risk_mgr = get_risk_manager()
    cfg = risk_mgr.config
    return RiskConfigResponse(
        trading_mode=settings.trading_mode,
        max_position_pct=cfg.max_position_pct,
        max_exposure_pct=cfg.max_exposure_pct,
        daily_loss_limit_pct=cfg.daily_loss_limit_pct,
        max_orders_per_minute=cfg.max_orders_per_minute,
        kill_switch_active=cfg.kill_switch_active,
    )


@router.put("/risk/config", response_model=RiskConfigResponse)
async def update_risk_config(
    req: RiskConfigUpdateRequest,
    session: AsyncSession = Depends(get_db),
):
    risk_mgr = get_risk_manager()
    updates = req.model_dump(exclude_none=True)
    risk_mgr.update_config(**updates)

    await execution_dal.create_risk_event(
        session,
        event_type="risk_config_updated",
        description=f"Risk config updated: {updates}",
        severity="info",
        details=updates,
    )

    settings = get_settings()
    cfg = risk_mgr.config
    return RiskConfigResponse(
        trading_mode=settings.trading_mode,
        max_position_pct=cfg.max_position_pct,
        max_exposure_pct=cfg.max_exposure_pct,
        daily_loss_limit_pct=cfg.daily_loss_limit_pct,
        max_orders_per_minute=cfg.max_orders_per_minute,
        kill_switch_active=cfg.kill_switch_active,
    )


@router.get("/risk/events", response_model=RiskEventHistoryResponse)
async def get_risk_events(
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    session: AsyncSession = Depends(get_db),
):
    events, total = await execution_dal.get_risk_events(session, limit=limit, offset=offset)
    return RiskEventHistoryResponse(
        events=[
            RiskEventResponse(
                id=e.id,
                event_type=e.event_type,
                severity=e.severity,
                symbol=e.symbol,
                description=e.description,
                details=e.details,
                created_at=e.created_at,
            )
            for e in events
        ],
        total=total,
    )


def _build_status_response(session) -> ExecutionStatusResponse:
    settings = get_settings()
    risk_mgr = get_risk_manager()
    stream = get_stream()
    stream_status = stream.status

    return ExecutionStatusResponse(
        trading_mode=settings.trading_mode,
        kill_switch_active=risk_mgr.config.kill_switch_active,
        stream_connected=stream_status.connected,
        subscribed_symbols=stream_status.subscribed_symbols,
    )


def _order_to_response(order) -> OrderResponse:
    return OrderResponse(
        id=order.id,
        symbol=order.symbol,
        side=order.side,
        qty=order.qty,
        order_type=order.order_type,
        limit_price=order.limit_price,
        stop_price=order.stop_price,
        status=order.status,
        alpaca_order_id=order.alpaca_order_id,
        filled_price=order.filled_price,
        filled_qty=order.filled_qty,
        filled_at=order.filled_at,
        signal_id=order.signal_id,
        error_message=order.error_message,
        created_at=order.created_at,
        updated_at=order.updated_at,
    )
