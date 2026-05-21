from datetime import date

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from models.macro import MacroObservation, MacroSeries


async def upsert_series_catalog(session: AsyncSession, series: list[dict]) -> int:
    count = 0
    for s in series:
        stmt = pg_insert(MacroSeries).values(**s)
        stmt = stmt.on_conflict_do_update(
            index_elements=["series_id"],
            set_={
                "title": s["title"],
                "frequency": s.get("frequency"),
                "category": s.get("category", "general"),
            },
        )
        await session.execute(stmt)
        count += 1
    return count


async def list_series(session: AsyncSession) -> list[dict]:
    rows = (await session.execute(select(MacroSeries).order_by(MacroSeries.category))).scalars()
    return [
        {
            "series_id": r.series_id,
            "title": r.title,
            "frequency": r.frequency,
            "category": r.category,
            "is_enabled": r.is_enabled,
        }
        for r in rows
    ]


async def set_series_enabled(session: AsyncSession, series_id: str, enabled: bool) -> None:
    from sqlalchemy import update

    await session.execute(
        update(MacroSeries).where(MacroSeries.series_id == series_id).values(is_enabled=enabled)
    )


async def bulk_insert_observations(session: AsyncSession, rows: list[dict]) -> int:
    if not rows:
        return 0
    stmt = pg_insert(MacroObservation).values(rows)
    stmt = stmt.on_conflict_do_update(
        index_elements=["series_id", "obs_date"],
        set_={"value": stmt.excluded.value},
    )
    result = await session.execute(stmt)
    return result.rowcount or len(rows)


async def get_observations(
    session: AsyncSession,
    series_id: str,
    limit: int = 120,
    order: str = "desc",
) -> list[dict]:
    order_clause = (
        MacroObservation.obs_date.asc()
        if order == "asc"
        else MacroObservation.obs_date.desc()
    )
    q = (
        select(MacroObservation)
        .where(MacroObservation.series_id == series_id)
        .order_by(order_clause)
        .limit(limit)
    )
    rows = (await session.execute(q)).scalars().all()
    return [{"obs_date": r.obs_date, "value": r.value} for r in rows]


async def get_enabled_series_ids(session: AsyncSession) -> list[str]:
    q = select(MacroSeries.series_id).where(MacroSeries.is_enabled.is_(True))
    return list((await session.execute(q)).scalars().all())
