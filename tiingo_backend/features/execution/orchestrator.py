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
from features.execution.evaluation_recorder import _thresholds, record_evaluation
from features.execution.inference_runner import run_live_inference
from features.execution.risk_checker import run_risk_checks
from features.execution.signal_to_order import resolve_position_side, signal_to_order_intent
from features.ml.saved_model_metadata import extract_saved_model_metadata


def _ensure_paper_mode() -> None:
    settings = get_settings()
    if not settings.paper_trading_only:
        raise ValueError("Live trading is not enabled in MVP; set TRADING_MODE_PAPER=true")
    if not settings.alpaca_configured:
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
    }


async def set_kill_switch(session: AsyncSession, enabled: bool) -> dict:
    row = await execution_settings_dal.set_kill_switch(session, enabled)
    await session.commit()
    return row


async def get_portfolio_snapshot() -> dict:
    _ensure_paper_mode()
    account = await alpaca_client.get_account()
    positions = await alpaca_client.get_positions()
    return {"account": account, "positions": positions}


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
    if timeframe != "1d":
        raise ValueError("Live execution MVP supports daily (1d) timeframe only")
    instrument = await instrument_dal.get_by_symbol(session, symbol)
    if not instrument:
        raise ValueError(f"Instrument {symbol} is not in the watchlist")
    return row


async def create_deployment(
    session: AsyncSession,
    *,
    model_id: UUID,
    allocation_pct: float = 100.0,
) -> dict:
    _ensure_paper_mode()
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
    return await trading_deployment_dal.list_deployments_enriched(session)


async def get_deployment(session: AsyncSession, deployment_id: UUID) -> dict | None:
    rows = await trading_deployment_dal.list_deployments_enriched(session)
    return next((row for row in rows if row["id"] == deployment_id), None)


async def activate_deployment(session: AsyncSession, deployment_id: UUID) -> dict:
    _ensure_paper_mode()
    deployment = await trading_deployment_dal.get_deployment(session, deployment_id)
    if not deployment:
        raise ValueError(f"Deployment not found: {deployment_id}")
    if deployment["status"] not in {"draft", "paused", "stopped", "error"}:
        raise ValueError(f"Cannot activate deployment in status {deployment['status']}")

    await _validate_model_for_deployment(session, deployment["model_id"])
    existing = await trading_deployment_dal.get_active_deployment_for_symbol(
        session,
        symbol=deployment["symbol"],
        trading_mode=deployment["trading_mode"],
    )
    if existing and existing["id"] != deployment_id:
        raise ValueError(
            f"Another active deployment already exists for {deployment['symbol']}"
        )

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
    limit: int = 50,
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
) -> tuple[dict | None, str | None]:
    try:
        alpaca_order = await alpaca_client.submit_market_order(
            deployment["symbol"],
            intent.qty,
            intent.side,
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
    _ensure_paper_mode()
    deployment = await trading_deployment_dal.get_deployment(session, deployment_id)
    if not deployment:
        raise ValueError(f"Deployment not found: {deployment_id}")
    if deployment["status"] != "active":
        raise ValueError("Deployment must be active to evaluate")

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

    if _same_bar_time(deployment.get("last_evaluated_bar_time"), bar_time):
        eval_row = await record_evaluation(
            session,
            deployment=deployment,
            bar_time=bar_time,
            signal=deployment.get("last_signal") or inference["signal"],
            probability=probability,
            buy_threshold=buy_threshold,
            sell_threshold=sell_threshold,
            position_side=None,
            order_intent_side=None,
            order_qty=None,
            outcome="skipped",
            blocked_reason="Already evaluated for latest bar",
            order_id=None,
            warnings=inference.get("warnings") or [],
        )
        await session.commit()
        return {
            "deployment_id": deployment_id,
            "skipped": True,
            "reason": "Already evaluated for latest bar",
            "signal": deployment.get("last_signal"),
            "bar_time": bar_time.isoformat(),
            "outcome": "skipped",
            "evaluation": eval_row,
        }

    signal = inference["signal"]
    settings = get_settings()
    result: dict = {
        "deployment_id": deployment_id,
        "skipped": False,
        "signal": signal,
        "bar_time": bar_time.isoformat(),
        "probability": probability,
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
            position_side=resolve_position_side([], deployment["symbol"]),
            order_intent_side=None,
            order_qty=None,
            outcome="hold",
            blocked_reason=None,
            order_id=None,
            warnings=result["warnings"],
        )
        await session.commit()
        result["outcome"] = "hold"
        result["evaluation"] = eval_row
        return result

    account = await alpaca_client.get_account()
    positions = await alpaca_client.get_positions()
    open_orders = await alpaca_client.get_open_orders()
    exec_settings = await _sync_day_start_equity(session, account["equity"])
    position_side = resolve_position_side(positions, deployment["symbol"])

    intent = signal_to_order_intent(
        signal,
        symbol=deployment["symbol"],
        positions=positions,
        buying_power=account["buying_power"],
        account_equity=account["equity"],
        allocation_pct=deployment["allocation_pct"],
        max_position_pct=settings.max_position_pct,
        last_price=inference.get("last_price"),
    )
    if intent is None:
        eval_row = await record_evaluation(
            session,
            deployment=deployment,
            bar_time=bar_time,
            signal=signal,
            probability=probability,
            buy_threshold=buy_threshold,
            sell_threshold=sell_threshold,
            position_side=position_side,
            order_intent_side=None,
            order_qty=None,
            outcome="blocked",
            blocked_reason="No actionable order for current position",
            order_id=None,
            warnings=result["warnings"],
        )
        await session.commit()
        result["blocked_reason"] = "No actionable order for current position"
        result["outcome"] = "blocked"
        result["evaluation"] = eval_row
        return result

    risk = run_risk_checks(
        intent,
        symbol=deployment["symbol"],
        kill_switch_enabled=exec_settings["kill_switch_enabled"],
        orders_this_minute=exec_settings.get("orders_this_minute") or 0,
        open_orders=open_orders,
        account_equity=account["equity"],
        day_start_equity=exec_settings.get("day_start_equity"),
        day_start_date=exec_settings.get("day_start_date"),
        today=date.today(),
        positions=positions,
        last_price=float(inference.get("last_price") or 0),
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
            position_side=position_side,
            order_intent_side=intent.side,
            order_qty=intent.qty,
            outcome="blocked",
            blocked_reason=risk.reason,
            order_id=None,
            warnings=result["warnings"],
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
        position_side=position_side,
        order_intent_side=intent.side,
        order_qty=intent.qty,
        outcome=outcome,
        blocked_reason=submit_error,
        order_id=order_row["id"] if order_row else None,
        warnings=result["warnings"],
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
