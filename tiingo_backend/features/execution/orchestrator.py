from datetime import date, datetime, timezone
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from config import get_settings
from dal import (
    execution_evaluation_dal,
    execution_order_dal,
    execution_settings_dal,
    instrument_dal,
    ml_model_dal,
    trading_deployment_dal,
)
from features.execution import alpaca_client
from features.execution.deployment_close import close_deployment_position
from features.execution.deployment_position import resolve_deployment_side
from features.execution.evaluation_recorder import _thresholds, record_evaluation
from features.execution.inference_runner import run_live_inference
from features.execution.order_sync import sync_deployment_orders
from features.execution.portfolio_snapshot import (
    build_portfolio_breakdown,
    build_unified_position_rows,
    compute_deployment_exposure,
    enrich_deployment_positions,
)
from features.execution.portfolio_metrics import build_portfolio_period_summary
from features.execution.risk_checker import run_risk_checks
from features.execution.signal_to_order import signal_to_order_intent
from features.execution.alpaca_symbols import execution_asset_type
from features.execution.deployment_overview import build_deployment_overview_row
from features.execution.deployment_reconciliation import build_deployment_readiness
from features.execution.market_data_gate import (
    is_ohlcv_ready_for_evaluation,
    market_data_not_ready_reason,
)
from features.execution.order_qty import alpaca_position_for_symbol
from features.execution.deployment_risk_state import refresh_deployment_peak_profit
from features.execution.deployment_timeframes import validate_execution_timeframe
from features.execution.deployment_metrics import compute_strategy_pnl
from features.execution.portfolio_snapshot import alpaca_price_by_tiingo_symbol
from features.ingestion.deployment_ohlcv_refresh import refresh_single_deployment_ohlcv
from features.ml.saved_model_metadata import extract_saved_model_metadata
from features.sentiment.sentiment_context import fetch_symbol_sentiment_context


def _sentiment_guardrail_params(hyperparams: dict) -> dict:
    return {
        "enabled": bool(hyperparams.get("sentiment_guardrail_enabled")),
        "min_score": float(hyperparams.get("sentiment_min_score") or -0.5),
        "min_articles": int(hyperparams.get("sentiment_min_articles") or 3),
    }


def _ensure_trading_enabled() -> None:
    if not get_settings().alpaca_configured:
        raise RuntimeError("Alpaca API credentials are not configured")


def _normalize_bar_time(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _same_bar_time(left: datetime | None, right: datetime) -> bool:
    normalized_left = _normalize_bar_time(left)
    normalized_right = _normalize_bar_time(right)
    if normalized_left is None or normalized_right is None:
        return False
    return normalized_left == normalized_right


async def get_execution_status(session: AsyncSession) -> dict:
    settings = get_settings()
    exec_settings = await execution_settings_dal.get_settings(session)
    return {
        "trading_mode": settings.trading_mode,
        "alpaca_configured": settings.alpaca_configured,
        "alpaca_base_url": settings.effective_alpaca_base_url,
        "kill_switch_enabled": exec_settings["kill_switch_enabled"],
        "paper_trading_only": settings.paper_trading_only,
        "trading_mode_paper": settings.trading_mode_paper,
    }


async def get_risk_config() -> dict:
    settings = get_settings()
    return {
        "max_position_pct": settings.max_position_pct,
        "max_exposure_pct": settings.max_exposure_pct,
        "daily_loss_limit_pct": settings.daily_loss_limit_pct,
        "max_orders_per_minute": settings.max_orders_per_minute,
        "deployment_max_drawdown_pct": settings.deployment_max_drawdown_pct,
        "stale_data_max_missed_slots": settings.stale_data_max_missed_slots,
        "stale_data_block_orders": settings.stale_data_block_orders,
    }


async def set_kill_switch(session: AsyncSession, enabled: bool) -> dict:
    row = await execution_settings_dal.set_kill_switch(session, enabled)
    await session.commit()
    return row


async def get_portfolio_snapshot(
    session: AsyncSession,
    *,
    start: datetime | None = None,
    end: datetime | None = None,
) -> dict:
    _ensure_trading_enabled()
    account = await alpaca_client.get_account()
    positions = await alpaca_client.get_positions()
    deployments = await trading_deployment_dal.list_deployments(session, limit=500)
    for deployment in deployments:
        await sync_deployment_orders(session, deployment["id"])
    deployment_positions, untracked_positions = await build_portfolio_breakdown(
        session,
        positions,
    )
    period_summary, period_pl_map = await build_portfolio_period_summary(
        session,
        deployment_rows=deployment_positions,
        untracked_rows=untracked_positions,
        start=start,
        end=end,
    )
    position_rows = build_unified_position_rows(
        deployment_positions,
        untracked_positions,
        period_pl_by_key=period_pl_map,
    )
    return {
        "account": account,
        "positions": positions,
        "deployment_positions": deployment_positions,
        "untracked_positions": untracked_positions,
        "position_rows": position_rows,
        "summary": {
            "closed_pnl": {
                "amount": period_summary.closed_pnl.amount,
                "pct": period_summary.closed_pnl.pct,
            },
            "open_pnl": {
                "amount": period_summary.open_pnl.amount,
                "pct": period_summary.open_pnl.pct,
            },
            "qqq_return_pct": period_summary.qqq_return_pct,
            "voo_return_pct": period_summary.voo_return_pct,
        },
        "period": {
            "start": period_summary.start,
            "end": period_summary.end,
        },
    }


async def _validate_model_for_deployment(session: AsyncSession, model_id: UUID) -> dict:
    row = await ml_model_dal.get_model(session, model_id)
    if not row:
        raise ValueError(f"Saved model not found: {model_id}")
    if not row.get("artifact_path"):
        raise ValueError(f"Saved model {model_id} has no artifact on disk")
    metadata = extract_saved_model_metadata(row)
    symbol = metadata.get("symbol")
    timeframe = metadata.get("timeframe") or "1d"
    if not symbol:
        raise ValueError("Saved model is missing training symbol metadata")
    validate_execution_timeframe(timeframe)
    instrument = await instrument_dal.get_by_symbol(session, symbol)
    if not instrument:
        raise ValueError(f"Instrument {symbol} is not in the watchlist")
    label_mode = str((row.get("hyperparams") or {}).get("label_mode") or "binary")
    asset_type = instrument.get("asset_type") or "stock"
    if label_mode == "meta_label" and asset_type != "crypto":
        raise ValueError(
            f"Meta-label deployments require a crypto instrument; {symbol} is {asset_type}"
        )
    return row


async def create_deployment(
    session: AsyncSession,
    *,
    model_id: UUID,
    allocation_pct: float = 100.0,
) -> dict:
    _ensure_trading_enabled()
    if allocation_pct <= 0 or allocation_pct > 100:
        raise ValueError("allocation_pct must be between 0 and 100")

    model = await _validate_model_for_deployment(session, model_id)
    metadata = extract_saved_model_metadata(model)
    settings = get_settings()

    row = await trading_deployment_dal.create_deployment(
        session,
        model_id=model_id,
        symbol=metadata["symbol"],
        timeframe=metadata["timeframe"] or "1d",
        trading_mode=settings.trading_mode,
        allocation_pct=allocation_pct,
        hyperparams_snapshot=model.get("hyperparams") or {},
    )
    await session.commit()
    return await get_deployment(session, row["id"]) or row


async def list_deployments(session: AsyncSession) -> list[dict]:
    rows = await trading_deployment_dal.list_deployments_enriched(session)
    return await enrich_deployment_positions(session, rows)


async def get_deployment_overview(session: AsyncSession) -> list[dict]:
    _ensure_trading_enabled()
    positions = await alpaca_client.get_positions()
    alpaca_price_by_symbol = alpaca_price_by_tiingo_symbol(positions)
    deployments = await list_deployments(session)
    overview_rows: list[dict] = []
    for deployment in deployments:
        instrument = await instrument_dal.get_by_symbol(session, deployment["symbol"])
        asset_type = (instrument or {}).get("asset_type") or "stock"
        overview_rows.append(
            await build_deployment_overview_row(
                session,
                deployment,
                alpaca_price_by_symbol=alpaca_price_by_symbol,
                asset_type=asset_type,
            ),
        )
    return overview_rows


async def get_deployment(session: AsyncSession, deployment_id: UUID) -> dict | None:
    rows = await list_deployments(session)
    return next((row for row in rows if row["id"] == deployment_id), None)


async def activate_deployment(session: AsyncSession, deployment_id: UUID) -> dict:
    _ensure_trading_enabled()
    deployment = await trading_deployment_dal.get_deployment(session, deployment_id)
    if not deployment:
        raise ValueError(f"Deployment not found: {deployment_id}")
    if deployment["status"] not in {"draft", "paused", "stopped", "error"}:
        raise ValueError(f"Cannot activate deployment in status {deployment['status']}")

    await _validate_model_for_deployment(session, deployment["model_id"])

    now = datetime.now(timezone.utc)
    await trading_deployment_dal.update_deployment_status(
        session,
        deployment_id,
        status="active",
        activated_at=now,
        last_error=None,
    )
    await session.commit()
    return await get_deployment(session, deployment_id)


async def pause_deployment(session: AsyncSession, deployment_id: UUID) -> dict:
    deployment = await trading_deployment_dal.get_deployment(session, deployment_id)
    if not deployment:
        raise ValueError(f"Deployment not found: {deployment_id}")
    await trading_deployment_dal.update_deployment_status(session, deployment_id, status="paused")
    await session.commit()
    return await get_deployment(session, deployment_id)


async def stop_deployment(session: AsyncSession, deployment_id: UUID) -> dict:
    deployment = await trading_deployment_dal.get_deployment(session, deployment_id)
    if not deployment:
        raise ValueError(f"Deployment not found: {deployment_id}")
    await trading_deployment_dal.update_deployment_status(session, deployment_id, status="stopped")
    await session.commit()
    return await get_deployment(session, deployment_id)


async def delete_deployment(
    session: AsyncSession,
    deployment_id: UUID,
    *,
    close_positions: bool = False,
) -> dict:
    _ensure_trading_enabled()
    deployment = await trading_deployment_dal.get_deployment(session, deployment_id)
    if not deployment:
        raise ValueError(f"Deployment not found: {deployment_id}")

    try:
        if deployment["status"] == "active":
            await trading_deployment_dal.update_deployment_status(session, deployment_id, status="stopped")

        closed_qty = 0.0
        close_order_id = None
        close_warning = None
        if close_positions:
            close_result = await close_deployment_position(session, deployment)
            closed_qty = float(close_result.get("qty") or 0)
            close_order_id = close_result.get("order_id")
            close_warning = close_result.get("close_warning")

        deleted = await trading_deployment_dal.delete_deployment(session, deployment_id)
        if not deleted:
            raise ValueError(f"Deployment not found: {deployment_id}")

        await session.commit()
    except Exception:
        await session.rollback()
        raise

    return {
        "deleted": True,
        "close_positions": close_positions,
        "closed_qty": closed_qty,
        "close_order_id": close_order_id,
        "close_warning": close_warning,
    }


async def list_orders(
    session: AsyncSession,
    *,
    deployment_id: UUID | None = None,
    symbol: str | None = None,
    status: str | None = None,
) -> list[dict]:
    orders = await execution_order_dal.list_orders(
        session,
        deployment_id=deployment_id,
        symbol=symbol,
        status=status,
    )
    deployments = {str(row["id"]): row for row in await list_deployments(session)}
    enriched: list[dict] = []
    for order in orders:
        dep = deployments.get(str(order["deployment_id"]))
        enriched.append(
            {
                **order,
                "model_name": dep.get("model_name") if dep else None,
                "model_id": dep.get("model_id") if dep else None,
            }
        )
    return enriched


async def list_evaluations(
    session: AsyncSession,
    *,
    deployment_id: UUID | None = None,
    symbol: str | None = None,
    limit: int = 200,
) -> list[dict]:
    rows = await execution_evaluation_dal.list_evaluations(
        session,
        deployment_id=deployment_id,
        symbol=symbol,
        limit=limit,
    )
    models = {
        str(row["id"]): row
        for row in await ml_model_dal.list_models(session, limit=500)
    }
    enriched: list[dict] = []
    for row in rows:
        model = models.get(str(row.get("model_id")))
        enriched.append(
            {
                **row,
                "model_name": model.get("name") if model else None,
                "model_type": model.get("model_type") if model else None,
            }
        )
    return enriched


async def _sync_day_start_equity(session: AsyncSession, account_equity: float) -> dict:
    settings_row = await execution_settings_dal.get_settings(session)
    today = date.today()
    if settings_row.get("day_start_date") == today:
        return settings_row
    return await execution_settings_dal.update_day_start_equity(
        session,
        equity=account_equity,
        day=today,
    )


async def _submit_order(
    session: AsyncSession,
    *,
    deployment: dict,
    intent,
    signal: str,
    bar_time: datetime,
    asset_type: str = "stock",
) -> tuple[dict | None, str | None]:
    try:
        alpaca_order = await alpaca_client.submit_market_order(
            deployment["symbol"],
            intent.qty,
            intent.side,
            asset_type=asset_type,
        )
        await execution_settings_dal.record_order_submission(session)
        order_row = await execution_order_dal.create_order(
            session,
            deployment_id=deployment["id"],
            alpaca_order_id=alpaca_order.get("id"),
            symbol=deployment["symbol"],
            side=intent.side,
            qty=intent.qty,
            order_type="market",
            status=alpaca_order.get("status") or "pending",
            signal=signal,
            bar_time=bar_time,
        )
        return order_row, None
    except Exception as exc:
        await execution_order_dal.create_order(
            session,
            deployment_id=deployment["id"],
            alpaca_order_id=None,
            symbol=deployment["symbol"],
            side=intent.side,
            qty=intent.qty,
            order_type="market",
            status="rejected",
            signal=signal,
            bar_time=bar_time,
            error_message=str(exc),
        )
        await trading_deployment_dal.update_deployment_status(
            session,
            deployment["id"],
            status="error",
            last_error=str(exc),
        )
        return None, str(exc)


async def evaluate_deployment(session: AsyncSession, deployment_id: UUID) -> dict:
    _ensure_trading_enabled()
    deployment = await trading_deployment_dal.get_deployment(session, deployment_id)
    if not deployment:
        raise ValueError(f"Deployment not found: {deployment_id}")
    if deployment["status"] not in {"active", "error"}:
        raise ValueError("Deployment must be active to evaluate")

    instrument = await instrument_dal.get_by_symbol(session, deployment["symbol"])
    asset_type = execution_asset_type((instrument or {}).get("asset_type"))

    await sync_deployment_orders(session, deployment_id)
    deployment_net_qty = await execution_order_dal.sum_filled_qty_by_deployment(
        session,
        deployment_id,
    )
    deployment_side = resolve_deployment_side(deployment_net_qty)

    await refresh_single_deployment_ohlcv(session, deployment)

    hyperparams = deployment["hyperparams_snapshot"]
    buy_threshold, sell_threshold = _thresholds(hyperparams)
    inference = await run_live_inference(
        session,
        model_id=deployment["model_id"],
        symbol=deployment["symbol"],
        timeframe=deployment["timeframe"],
        hyperparams=hyperparams,
    )
    bar_time: datetime = inference["bar_time"]
    probability = inference.get("probability")
    if isinstance(probability, (int, float)):
        probability = float(probability)
    else:
        probability = None
    explainability = inference.get("explainability") or {
        "method": "unavailable",
        "base_value": None,
        "predicted_value": None,
        "top_contributors": [],
        "ordered_contributors": [],
        "warnings": [],
    }

    if _same_bar_time(deployment.get("last_evaluated_bar_time"), bar_time):
        return {
            "deployment_id": str(deployment_id),
            "skipped": True,
            "reason": "Already evaluated for latest bar",
            "signal": deployment.get("last_signal"),
            "bar_time": bar_time.isoformat(),
            "outcome": "skipped",
            "probability": probability,
            "explainability": explainability,
        }

    now = datetime.now(timezone.utc)
    readiness = await build_deployment_readiness(
        session,
        deployment,
        now,
        asset_type=asset_type,
    )
    if not is_ohlcv_ready_for_evaluation(readiness):
        blocked_reason = market_data_not_ready_reason(readiness)
        eval_row = await record_evaluation(
            session,
            deployment=deployment,
            bar_time=bar_time,
            signal=inference["signal"],
            probability=probability,
            buy_threshold=buy_threshold,
            sell_threshold=sell_threshold,
            position_side=deployment_side,
            order_intent_side=None,
            order_qty=None,
            outcome="blocked",
            blocked_reason=blocked_reason,
            order_id=None,
            warnings=inference.get("warnings") or [],
            explainability=explainability,
            skip_last_evaluated_at=True,
        )
        await session.commit()
        return {
            "deployment_id": str(deployment_id),
            "skipped": False,
            "signal": inference["signal"],
            "bar_time": bar_time.isoformat(),
            "probability": probability,
            "explainability": explainability,
            "warnings": inference.get("warnings") or [],
            "order": None,
            "blocked_reason": blocked_reason,
            "outcome": "blocked",
            "evaluation": eval_row,
        }

    signal = inference["signal"]
    settings = get_settings()
    result: dict = {
        "deployment_id": str(deployment_id),
        "skipped": False,
        "signal": signal,
        "bar_time": bar_time.isoformat(),
        "probability": probability,
        "explainability": explainability,
        "warnings": inference.get("warnings") or [],
        "order": None,
        "blocked_reason": None,
        "outcome": "hold",
    }

    if signal == "hold":
        eval_row = await record_evaluation(
            session,
            deployment=deployment,
            bar_time=bar_time,
            signal=signal,
            probability=probability,
            buy_threshold=buy_threshold,
            sell_threshold=sell_threshold,
            position_side=deployment_side,
            order_intent_side=None,
            order_qty=None,
            outcome="hold",
            blocked_reason=None,
            order_id=None,
            warnings=result["warnings"],
            explainability=explainability,
        )
        await session.commit()
        result["outcome"] = "hold"
        result["evaluation"] = eval_row
        return result

    account = await alpaca_client.get_account()
    alpaca_positions = await alpaca_client.get_positions()
    exec_settings = await _sync_day_start_equity(session, account["equity"])
    last_price = float(inference.get("last_price") or 0)
    price_by_symbol = alpaca_price_by_tiingo_symbol(alpaca_positions)
    price_by_symbol[deployment["symbol"].upper()] = last_price
    deployment_exposure = await compute_deployment_exposure(session, price_by_symbol=price_by_symbol)
    deployment_has_open_order = await execution_order_dal.has_open_order(session, deployment_id)

    orders = await execution_order_dal.list_orders(session, deployment_id=deployment_id)
    strategy_pnl = compute_strategy_pnl(orders, last_price)
    peak_profit = await refresh_deployment_peak_profit(
        session,
        deployment,
        current_price=last_price,
    )

    position = alpaca_position_for_symbol(
        alpaca_positions,
        deployment["symbol"],
        asset_type,
    )
    position_qty = float(position.get("qty") or 0) if position else None
    qty_available = (
        float(position.get("qty_available") or position.get("qty") or 0)
        if position
        else None
    )
    intent = signal_to_order_intent(
        signal,
        deployment_net_qty=deployment_net_qty,
        buying_power=account["buying_power"],
        account_equity=account["equity"],
        allocation_pct=deployment["allocation_pct"],
        max_position_pct=settings.max_position_pct,
        last_price=inference.get("last_price"),
        asset_type=asset_type,
        position_qty=position_qty,
        qty_available=qty_available,
    )
    if intent is None:
        blocked_reason = "No actionable order for current deployment position"
        if signal.lower() == "sell" and deployment_side == "long":
            blocked_reason = "No sellable quantity available at broker"
        eval_row = await record_evaluation(
            session,
            deployment=deployment,
            bar_time=bar_time,
            signal=signal,
            probability=probability,
            buy_threshold=buy_threshold,
            sell_threshold=sell_threshold,
            position_side=deployment_side,
            order_intent_side="sell" if signal.lower() == "sell" else None,
            order_qty=None,
            outcome="blocked",
            blocked_reason=blocked_reason,
            order_id=None,
            warnings=result["warnings"],
            explainability=explainability,
        )
        await session.commit()
        result["blocked_reason"] = blocked_reason
        result["outcome"] = "blocked"
        result["evaluation"] = eval_row
        return result

    guardrail = _sentiment_guardrail_params(hyperparams)
    sentiment_context = None
    if guardrail["enabled"]:
        sentiment_context = await fetch_symbol_sentiment_context(
            session,
            symbol=deployment["symbol"],
            on_date=bar_time.date(),
        )

    risk = run_risk_checks(
        intent,
        kill_switch_enabled=exec_settings["kill_switch_enabled"],
        orders_this_minute=exec_settings.get("orders_this_minute") or 0,
        deployment_has_open_order=deployment_has_open_order,
        account_equity=account["equity"],
        day_start_equity=exec_settings.get("day_start_equity"),
        day_start_date=exec_settings.get("day_start_date"),
        today=date.today(),
        deployment_exposure=deployment_exposure,
        last_price=last_price,
        sentiment_guardrail_enabled=guardrail["enabled"],
        sentiment_avg_score_1d=(
            float(sentiment_context["avg_score"]) if sentiment_context else None
        ),
        sentiment_article_count_1d=(
            int(sentiment_context["article_count"]) if sentiment_context else 0
        ),
        sentiment_min_score=guardrail["min_score"],
        sentiment_min_articles=guardrail["min_articles"],
        strategy_profit_pct=strategy_pnl.profit_pct,
        peak_strategy_profit_pct=peak_profit,
        deployment_readiness=readiness,
    )
    if not risk.allowed:
        eval_row = await record_evaluation(
            session,
            deployment=deployment,
            bar_time=bar_time,
            signal=signal,
            probability=probability,
            buy_threshold=buy_threshold,
            sell_threshold=sell_threshold,
            position_side=deployment_side,
            order_intent_side=intent.side,
            order_qty=intent.qty,
            outcome="blocked",
            blocked_reason=risk.reason,
            order_id=None,
            warnings=result["warnings"],
            explainability=explainability,
        )
        await session.commit()
        result["blocked_reason"] = risk.reason
        result["outcome"] = "blocked"
        result["evaluation"] = eval_row
        return result

    order_row, submit_error = await _submit_order(
        session,
        deployment=deployment,
        intent=intent,
        signal=signal,
        bar_time=bar_time,
        asset_type=asset_type,
    )
    outcome = "order_submitted" if order_row else "error"
    eval_row = await record_evaluation(
        session,
        deployment=deployment,
        bar_time=bar_time,
        signal=signal,
        probability=probability,
        buy_threshold=buy_threshold,
        sell_threshold=sell_threshold,
        position_side=deployment_side,
        order_intent_side=intent.side,
        order_qty=intent.qty,
        outcome=outcome,
        blocked_reason=submit_error,
        order_id=order_row["id"] if order_row else None,
        warnings=result["warnings"],
        explainability=explainability,
    )
    await session.commit()
    result["order"] = order_row
    result["blocked_reason"] = submit_error
    result["outcome"] = outcome
    result["evaluation"] = eval_row
    return result


async def evaluate_all_active(session: AsyncSession) -> dict:
    deployments = await trading_deployment_dal.list_active_deployments(session)
    results = []
    for deployment in deployments:
        try:
            outcome = await evaluate_deployment(session, deployment["id"])
            results.append(outcome)
        except Exception as exc:
            await trading_deployment_dal.update_deployment_status(
                session,
                deployment["id"],
                status="error",
                last_error=str(exc),
            )
            await session.commit()
            results.append(
                {
                    "deployment_id": str(deployment["id"]),
                    "skipped": False,
                    "error": str(exc),
                }
            )
    return {"evaluated": len(results), "results": results}
