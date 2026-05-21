from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from models.market_data import Fundamental


async def bulk_insert_fundamentals(session: AsyncSession, rows: list[dict]) -> int:
    if not rows:
        return 0
    stmt = pg_insert(Fundamental).values(rows)
    stmt = stmt.on_conflict_do_nothing(constraint="uq_fundamentals")
    result = await session.execute(stmt)
    return result.rowcount or 0


async def list_fundamentals_for_symbol(
    session: AsyncSession,
    instrument_id: int,
    limit: int = 200,
) -> list[dict]:
    from sqlalchemy import select

    q = (
        select(Fundamental)
        .where(Fundamental.instrument_id == instrument_id)
        .order_by(Fundamental.time.desc())
        .limit(limit)
    )
    rows = (await session.execute(q)).scalars().all()
    return [
        {
            "time": r.time,
            "metric_name": r.metric_name,
            "value": r.value,
            "period": r.period,
            "statement_type": r.statement_type,
        }
        for r in rows
    ]
