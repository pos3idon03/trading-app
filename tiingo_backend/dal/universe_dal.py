from datetime import date, datetime, timezone

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from models.universe import UniverseDefinition, UniverseMember


def _definition_row(row: UniverseDefinition) -> dict:
    return {
        "id": row.id,
        "name": row.name,
        "source": row.source,
        "description": row.description,
        "created_at": row.created_at,
    }


def _member_row(row: UniverseMember) -> dict:
    return {
        "id": row.id,
        "universe_id": row.universe_id,
        "symbol": row.symbol,
        "effective_from": row.effective_from,
        "effective_to": row.effective_to,
    }


async def list_universes(session: AsyncSession) -> list[dict]:
    rows = await session.execute(
        select(UniverseDefinition).order_by(UniverseDefinition.name)
    )
    return [_definition_row(r) for r in rows.scalars().all()]


async def get_universe(session: AsyncSession, universe_id: int) -> dict | None:
    row = (
        await session.execute(
            select(UniverseDefinition).where(UniverseDefinition.id == universe_id)
        )
    ).scalar_one_or_none()
    return _definition_row(row) if row else None


async def create_universe(
    session: AsyncSession,
    *,
    name: str,
    source: str | None = None,
    description: str | None = None,
) -> dict:
    now = datetime.now(timezone.utc)
    stmt = (
        pg_insert(UniverseDefinition)
        .values(name=name, source=source, description=description, created_at=now)
        .returning(UniverseDefinition)
    )
    row = (await session.execute(stmt)).scalar_one()
    return _definition_row(row)


async def upsert_members(
    session: AsyncSession,
    universe_id: int,
    members: list[dict],
) -> int:
    if not members:
        return 0
    rows = [
        {
            "universe_id": universe_id,
            "symbol": str(m["symbol"]).upper(),
            "effective_from": m["effective_from"],
            "effective_to": m.get("effective_to"),
            "created_at": datetime.now(timezone.utc),
        }
        for m in members
    ]
    stmt = pg_insert(UniverseMember).values(rows)
    stmt = stmt.on_conflict_do_nothing(
        index_elements=["universe_id", "symbol", "effective_from"],
    )
    result = await session.execute(stmt)
    return result.rowcount or len(rows)


async def get_members_as_of(
    session: AsyncSession,
    universe_id: int,
    as_of: date,
) -> list[str]:
    q = select(UniverseMember.symbol).where(
        UniverseMember.universe_id == universe_id,
        UniverseMember.effective_from <= as_of,
        (UniverseMember.effective_to.is_(None)) | (UniverseMember.effective_to >= as_of),
    )
    rows = await session.execute(q)
    return sorted({r.upper() for r in rows.scalars().all()})


async def list_all_members(session: AsyncSession, universe_id: int) -> list[dict]:
    rows = await session.execute(
        select(UniverseMember)
        .where(UniverseMember.universe_id == universe_id)
        .order_by(UniverseMember.symbol, UniverseMember.effective_from)
    )
    return [_member_row(r) for r in rows.scalars().all()]
