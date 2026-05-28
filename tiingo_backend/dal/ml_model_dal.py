from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.ml_model import MlModel


async def create_model(
    session: AsyncSession,
    *,
    name: str,
    model_type: str,
    feature_mode: str,
    feature_schema: dict,
    hyperparams: dict,
    train_metrics: dict | None,
    artifact_path: str | None,
) -> dict:
    model_id = uuid4()
    now = datetime.now(timezone.utc)
    row = MlModel(
        id=model_id,
        name=name,
        model_type=model_type,
        feature_mode=feature_mode,
        feature_schema=feature_schema,
        hyperparams=hyperparams,
        train_metrics=train_metrics,
        artifact_path=artifact_path,
        created_at=now,
    )
    session.add(row)
    await session.flush()
    return _to_dict(row)


async def get_model(session: AsyncSession, model_id: UUID) -> dict | None:
    q = select(MlModel).where(MlModel.id == model_id)
    row = (await session.execute(q)).scalar_one_or_none()
    return _to_dict(row) if row else None


async def list_models(session: AsyncSession, *, limit: int = 100) -> list[dict]:
    q = select(MlModel).order_by(MlModel.created_at.desc()).limit(limit)
    rows = (await session.execute(q)).scalars().all()
    return [_to_dict(row) for row in rows]


async def update_artifact_path(
    session: AsyncSession,
    model_id: UUID,
    artifact_path: str,
) -> dict | None:
    from sqlalchemy import update

    await session.execute(
        update(MlModel)
        .where(MlModel.id == model_id)
        .values(artifact_path=artifact_path),
    )
    await session.flush()
    return await get_model(session, model_id)


async def delete_model(session: AsyncSession, model_id: UUID) -> dict | None:
    q = select(MlModel).where(MlModel.id == model_id)
    row = (await session.execute(q)).scalar_one_or_none()
    if not row:
        return None
    deleted = _to_dict(row)
    await session.delete(row)
    await session.flush()
    return deleted


def _to_dict(row: MlModel) -> dict:
    return {
        "id": row.id,
        "name": row.name,
        "model_type": row.model_type,
        "feature_mode": row.feature_mode,
        "feature_schema": row.feature_schema,
        "hyperparams": row.hyperparams or {},
        "train_metrics": row.train_metrics,
        "artifact_path": row.artifact_path,
        "created_at": row.created_at,
    }
