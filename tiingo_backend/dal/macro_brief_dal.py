from datetime import date, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.macro import MacroBrief


def _brief_row(row: MacroBrief) -> dict:
    return {
        "id": row.id,
        "as_of": row.as_of,
        "situation": row.situation,
        "outlook": row.outlook,
        "situation_phase": row.situation_phase,
        "outlook_phase": row.outlook_phase,
        "data_fingerprint": row.data_fingerprint,
        "model_name": row.model_name,
        "generated_at": row.generated_at,
    }


async def get_latest_brief(session: AsyncSession) -> dict | None:
    q = (
        select(MacroBrief)
        .order_by(MacroBrief.generated_at.desc())
        .limit(1)
    )
    row = (await session.execute(q)).scalar_one_or_none()
    return _brief_row(row) if row else None


async def find_brief_by_fingerprint(
    session: AsyncSession,
    fingerprint: str,
) -> dict | None:
    q = (
        select(MacroBrief)
        .where(MacroBrief.data_fingerprint == fingerprint)
        .order_by(MacroBrief.generated_at.desc())
        .limit(1)
    )
    row = (await session.execute(q)).scalar_one_or_none()
    return _brief_row(row) if row else None


async def insert_brief(
    session: AsyncSession,
    *,
    as_of: date | None,
    situation: str,
    outlook: str,
    situation_phase: str | None,
    outlook_phase: str | None,
    data_fingerprint: str,
    model_name: str,
    generated_at: datetime,
) -> dict:
    row = MacroBrief(
        as_of=as_of,
        situation=situation,
        outlook=outlook,
        situation_phase=situation_phase,
        outlook_phase=outlook_phase,
        data_fingerprint=data_fingerprint,
        model_name=model_name,
        generated_at=generated_at,
    )
    session.add(row)
    await session.flush()
    return _brief_row(row)
