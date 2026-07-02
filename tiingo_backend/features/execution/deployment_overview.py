from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from dal import execution_order_dal, instrument_dal, ohlcv_dal
from features.execution.deployment_metrics import compute_strategy_pnl
from features.execution.deployment_timeframes import (
    ingest_source_for_asset,
    native_fetch_timeframe,
)
from features.execution.evaluation_recorder import _thresholds
from features.execution.order_sync import sync_deployment_orders


async def resolve_latest_price(
    session: AsyncSession,
    *,
    symbol: str,
    timeframe: str,
    asset_type: str,
    alpaca_price_by_symbol: dict[str, float],
) -> tuple[float | None, datetime | None]:
    symbol_upper = symbol.upper()
    alpaca_price = alpaca_price_by_symbol.get(symbol_upper)
    if alpaca_price and alpaca_price > 0:
        return alpaca_price, None

    instrument = await instrument_dal.get_by_symbol(session, symbol_upper)
    if not instrument:
        return None, None

    native_tf = native_fetch_timeframe(timeframe)
    source = ingest_source_for_asset(asset_type, native_tf)
    bars, _ = await ohlcv_dal.get_bars(
        session,
        instrument["id"],
        native_tf,
        source=source,
        limit=1,
        fetch_tail=True,
    )
    if not bars:
        return None, None
    bar = bars[-1]
    close = float(bar.get("close") or 0)
    bar_time = bar.get("time")
    if close <= 0:
        return None, bar_time if isinstance(bar_time, datetime) else None
    return close, bar_time if isinstance(bar_time, datetime) else None


async def build_deployment_overview_row(
    session: AsyncSession,
    deployment: dict,
    *,
    alpaca_price_by_symbol: dict[str, float],
    asset_type: str,
) -> dict:
    deployment_id = deployment["id"]
    await sync_deployment_orders(session, deployment_id)

    orders = await execution_order_dal.list_orders_for_deployment(session, deployment_id)
    current_price, price_updated_at = await resolve_latest_price(
        session,
        symbol=deployment["symbol"],
        timeframe=deployment["timeframe"],
        asset_type=asset_type,
        alpaca_price_by_symbol=alpaca_price_by_symbol,
    )
    price = float(current_price or 0)
    pnl = compute_strategy_pnl(orders, price)
    position_qty = float(deployment.get("position_qty") or pnl.position_qty)
    from features.execution.deployment_reconciliation import build_deployment_readiness

    readiness = await build_deployment_readiness(
        session,
        deployment,
        datetime.now(timezone.utc),
        asset_type=asset_type,
    )
    hyperparams = deployment.get("hyperparams_snapshot") or {}
    buy_threshold, sell_threshold = _thresholds(hyperparams)

    return {
        "id": deployment_id,
        "model_id": deployment["model_id"],
        "symbol": deployment["symbol"],
        "timeframe": deployment["timeframe"],
        "status": deployment["status"],
        "model_name": deployment.get("model_name"),
        "last_error": deployment.get("last_error"),
        "last_blocked_reason": deployment.get("last_blocked_reason"),
        "last_signal": deployment.get("last_signal"),
        "last_probability": deployment.get("last_probability"),
        "buy_threshold": buy_threshold,
        "sell_threshold": sell_threshold,
        "last_explainability": deployment.get("last_explainability") or {},
        "last_evaluated_bar_time": deployment.get("last_evaluated_bar_time"),
        "last_evaluated_at": deployment.get("last_evaluated_at"),
        "current_price": current_price,
        "price_updated_at": price_updated_at,
        "round_trip_count": pnl.round_trip_count,
        "open_position_count": 1 if position_qty > 1e-8 else 0,
        "order_count": await execution_order_dal.count_orders_by_deployment(session, deployment_id),
        "open_order_count": await execution_order_dal.count_open_orders_by_deployment(
            session,
            deployment_id,
        ),
        "strategy_profit": pnl.total_profit,
        "strategy_profit_pct": pnl.profit_pct,
        "position_qty": position_qty,
        "position_side": deployment.get("position_side") or "flat",
        "update_status": readiness["update_status"],
        "expected_latest_bar_time": readiness["expected_latest_bar_time"],
        "ohlcv_latest_bar_time": readiness["ohlcv_latest_bar_time"],
        "missed_slot_count": readiness["missed_slot_count"],
    }
