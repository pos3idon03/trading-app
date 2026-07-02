from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from models.trading_deployment import TradingDeployment

DEPLOYMENT_STATUSES = frozenset({"draft", "active", "paused", "stopped", "error"})


async def create_deployment(
    session: AsyncSession,
    *,
    model_id: UUID,
    symbol: str,
    timeframe: str,
    trading_mode: str,
    allocation_pct: float,
    hyperparams_snapshot: dict,
) -> dict:
    now = datetime.now(timezone.utc)
    row = TradingDeployment(
        id=uuid4(),
        model_id=model_id,
        symbol=symbol.upper(),
        timeframe=timeframe,
        status="draft",
        trading_mode=trading_mode,
        allocation_pct=allocation_pct,
        hyperparams_snapshot=hyperparams_snapshot,
        created_at=now,
        updated_at=now,
    )
    session.add(row)
    await session.flush()
    return _to_dict(row)


async def get_deployment(session: AsyncSession, deployment_id: UUID) -> dict | None:
    q = select(TradingDeployment).where(TradingDeployment.id == deployment_id)
    row = (await session.execute(q)).scalar_one_or_none()
    return _to_dict(row) if row else None


async def list_deployments(
    session: AsyncSession,
    *,
    status: str | None = None,
    limit: int = 100,
) -> list[dict]:
    q = select(TradingDeployment).order_by(TradingDeployment.created_at.desc()).limit(limit)
    if status:
        q = q.where(TradingDeployment.status == status)
    rows = (await session.execute(q)).scalars().all()
    return [_to_dict(row) for row in rows]


async def get_active_deployment_for_symbol(
    session: AsyncSession,
    *,
    symbol: str,
    trading_mode: str,
) -> dict | None:
    q = select(TradingDeployment).where(
        TradingDeployment.symbol == symbol.upper(),
        TradingDeployment.trading_mode == trading_mode,
        TradingDeployment.status == "active",
    )
    row = (await session.execute(q)).scalar_one_or_none()
    return _to_dict(row) if row else None


async def list_active_deployments(session: AsyncSession) -> list[dict]:
    q = select(TradingDeployment).where(TradingDeployment.status == "active")
    rows = (await session.execute(q)).scalars().all()
    return [_to_dict(row) for row in rows]


async def list_error_deployments_with_instrument(session: AsyncSession) -> list[dict]:
    from models.instrument import Instrument

    q = (
        select(TradingDeployment, Instrument)
        .join(Instrument, TradingDeployment.symbol == Instrument.symbol)
        .where(TradingDeployment.status == "error")
    )
    rows = (await session.execute(q)).all()
    result: list[dict] = []
    for dep, inst in rows:
        base = _to_dict(dep)
        base["asset_type"] = inst.asset_type
        result.append(base)
    return result


async def list_active_deployments_with_instrument(session: AsyncSession) -> list[dict]:
    from models.instrument import Instrument

    q = (
        select(TradingDeployment, Instrument)
        .join(Instrument, TradingDeployment.symbol == Instrument.symbol)
        .where(TradingDeployment.status == "active")
    )
    rows = (await session.execute(q)).all()
    result: list[dict] = []
    for dep, inst in rows:
        base = _to_dict(dep)
        base["asset_type"] = inst.asset_type
        result.append(base)
    return result


async def list_active_deployment_requirements(session: AsyncSession) -> list[dict]:
    return await list_deployments_for_ohlcv_refresh(session, statuses=("active",))


async def list_deployments_for_ohlcv_refresh(
    session: AsyncSession,
    *,
    statuses: tuple[str, ...] = ("active", "error"),
) -> list[dict]:
    from models.instrument import Instrument

    q = (
        select(TradingDeployment, Instrument)
        .join(Instrument, TradingDeployment.symbol == Instrument.symbol)
        .where(TradingDeployment.status.in_(statuses))
    )
    rows = (await session.execute(q)).all()
    return [
        {
            "deployment_id": dep.id,
            "symbol": dep.symbol,
            "timeframe": dep.timeframe,
            "asset_type": inst.asset_type,
        }
        for dep, inst in rows
    ]


async def update_deployment_status(
    session: AsyncSession,
    deployment_id: UUID,
    *,
    status: str,
    last_error: str | None = None,
    activated_at: datetime | None = None,
) -> dict | None:
    if status not in DEPLOYMENT_STATUSES:
        raise ValueError(f"Invalid deployment status: {status}")
    values: dict = {"status": status, "updated_at": datetime.now(timezone.utc)}
    if last_error is not None:
        values["last_error"] = last_error
    if activated_at is not None:
        values["activated_at"] = activated_at
    await session.execute(
        update(TradingDeployment)
        .where(TradingDeployment.id == deployment_id)
        .values(**values),
    )
    await session.flush()
    return await get_deployment(session, deployment_id)


async def update_peak_strategy_profit_pct(
    session: AsyncSession,
    deployment_id: UUID,
    peak_strategy_profit_pct: float | None,
) -> None:
    await session.execute(
        update(TradingDeployment)
        .where(TradingDeployment.id == deployment_id)
        .values(
            peak_strategy_profit_pct=peak_strategy_profit_pct,
            updated_at=datetime.now(timezone.utc),
        ),
    )
    await session.flush()


async def update_deployment_evaluation(
    session: AsyncSession,
    deployment_id: UUID,
    *,
    last_evaluated_bar_time: datetime,
    last_evaluated_at: datetime | None = None,
    last_signal: str,
    last_error: str | None = None,
    last_blocked_reason: str | None = None,
    last_probability: float | None = None,
    last_explainability: dict | None = None,
    last_outcome: str | None = None,
    status: str | None = None,
    clear_last_error: bool = False,
    skip_last_evaluated_at: bool = False,
) -> dict | None:
    values: dict = {
        "last_evaluated_bar_time": last_evaluated_bar_time,
        "last_signal": last_signal,
        "last_blocked_reason": last_blocked_reason,
        "last_probability": last_probability,
        "last_outcome": last_outcome,
        "updated_at": datetime.now(timezone.utc),
    }
    if not skip_last_evaluated_at:
        values["last_evaluated_at"] = last_evaluated_at or datetime.now(timezone.utc)
    if clear_last_error:
        values["last_error"] = None
    elif last_error is not None:
        values["last_error"] = last_error
    if last_explainability is not None:
        values["last_explainability"] = last_explainability
    if status:
        values["status"] = status
    await session.execute(
        update(TradingDeployment)
        .where(TradingDeployment.id == deployment_id)
        .values(**values),
    )
    await session.flush()
    return await get_deployment(session, deployment_id)


async def delete_deployment(session: AsyncSession, deployment_id: UUID) -> bool:
    q = select(TradingDeployment).where(TradingDeployment.id == deployment_id)
    row = (await session.execute(q)).scalar_one_or_none()
    if not row:
        return False
    await session.delete(row)
    await session.flush()
    return True


async def list_deployments_enriched(
    session: AsyncSession,
    *,
    status: str | None = None,
    limit: int = 100,
) -> list[dict]:
    from models.ml_model import MlModel

    q = (
        select(TradingDeployment, MlModel)
        .join(MlModel, TradingDeployment.model_id == MlModel.id)
        .order_by(TradingDeployment.created_at.desc())
        .limit(limit)
    )
    if status:
        q = q.where(TradingDeployment.status == status)
    rows = (await session.execute(q)).all()
    return [_to_enriched_dict(dep, model) for dep, model in rows]


def _to_enriched_dict(dep: TradingDeployment, model: object) -> dict:
    base = _to_dict(dep)
    base["model_name"] = model.name
    base["model_type"] = model.model_type
    base["feature_mode"] = model.feature_mode
    return base


def _to_dict(row: TradingDeployment) -> dict:
    return {
        "id": row.id,
        "model_id": row.model_id,
        "symbol": row.symbol,
        "timeframe": row.timeframe,
        "status": row.status,
        "trading_mode": row.trading_mode,
        "allocation_pct": float(row.allocation_pct),
        "hyperparams_snapshot": row.hyperparams_snapshot or {},
        "last_evaluated_bar_time": row.last_evaluated_bar_time,
        "last_evaluated_at": row.last_evaluated_at,
        "last_signal": row.last_signal,
        "last_error": row.last_error,
        "last_blocked_reason": row.last_blocked_reason,
        "last_probability": float(row.last_probability) if row.last_probability is not None else None,
        "last_explainability": row.last_explainability or {},
        "last_outcome": row.last_outcome,
        "peak_strategy_profit_pct": (
            float(row.peak_strategy_profit_pct)
            if getattr(row, "peak_strategy_profit_pct", None) is not None
            else None
        ),
        "activated_at": row.activated_at,
        "created_at": row.created_at,
        "updated_at": row.updated_at,
    }
