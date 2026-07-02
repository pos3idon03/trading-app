from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from models.rl_model import RlModel


async def create_model(
    session: AsyncSession,
    *,
    model_id: UUID,
    name: str,
    model_type: str,
    symbol: str | None,
    timeframe: str,
    hyperparams: dict,
    state_schema: dict,
    train_metrics: dict | None,
    artifact_path: str,
) -> dict:
    now = datetime.now(timezone.utc)
    row = RlModel(
        id=model_id,
        name=name,
        model_type=model_type,
        symbol=symbol,
        timeframe=timeframe,
        hyperparams=hyperparams,
        state_schema=state_schema,
        train_metrics=train_metrics,
        artifact_path=artifact_path,
        created_at=now,
    )
    session.add(row)
    await session.flush()
    return _to_dict(row)


async def list_models(session: AsyncSession, limit: int = 100) -> list[dict]:
    from sqlalchemy import select

    rows = await session.execute(
        select(RlModel).order_by(RlModel.created_at.desc()).limit(limit)
    )
    return [_to_dict(r) for r in rows.scalars().all()]


async def get_model(session: AsyncSession, model_id: UUID) -> dict | None:
    from sqlalchemy import select

    row = (
        await session.execute(select(RlModel).where(RlModel.id == model_id))
    ).scalar_one_or_none()
    return _to_dict(row) if row else None


def _to_dict(row: RlModel) -> dict:
    return {
        "id": row.id,
        "name": row.name,
        "model_type": row.model_type,
        "symbol": row.symbol,
        "timeframe": row.timeframe,
        "hyperparams": row.hyperparams,
        "state_schema": row.state_schema,
        "train_metrics": row.train_metrics,
        "artifact_path": row.artifact_path,
        "created_at": row.created_at,
    }
