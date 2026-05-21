from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from models.instrument import Instrument

_table = Instrument.__table__


async def list_instruments(
    session: AsyncSession,
    active_only: bool = False,
) -> list[dict]:
    q = select(Instrument).order_by(Instrument.symbol)
    if active_only:
        q = q.where(Instrument.is_active.is_(True))
    rows = await session.execute(q)
    return [_to_dict(r) for r in rows.scalars().all()]


async def get_by_symbol(session: AsyncSession, symbol: str) -> dict | None:
    q = select(Instrument).where(Instrument.symbol == symbol.upper())
    row = (await session.execute(q)).scalar_one_or_none()
    return _to_dict(row) if row else None


async def upsert_instrument(session: AsyncSession, data: dict) -> dict:
    now = datetime.now(timezone.utc)
    symbol = data["symbol"].upper()
    row = {
        _table.c.symbol: symbol,
        _table.c.tiingo_ticker: data.get("tiingo_ticker") or symbol,
        _table.c.name: data.get("name"),
        _table.c.asset_type: data.get("asset_type", "stock"),
        _table.c.exchange: data.get("exchange"),
        _table.c.currency: data.get("currency", "USD"),
        _table.c.is_active: data.get("is_active", True),
        _table.c.metadata: data.get("metadata"),
        _table.c.updated_at: now,
        _table.c.created_at: now,
    }
    update_cols = {
        k: v for k, v in row.items()
        if k not in (_table.c.symbol, _table.c.created_at)
    }
    stmt = pg_insert(_table).values(row)
    stmt = stmt.on_conflict_do_update(
        index_elements=["symbol"],
        set_=update_cols,
    ).returning(_table)
    mapping = (await session.execute(stmt)).mappings().one()
    return _row_mapping_to_dict(mapping)


async def patch_instrument(session: AsyncSession, symbol: str, patch: dict) -> dict | None:
    inst = await get_by_symbol(session, symbol)
    if not inst:
        return None
    allowed = {k: v for k, v in patch.items() if v is not None and k != "metadata"}
    if not allowed:
        return inst
    allowed["updated_at"] = datetime.now(timezone.utc)
    await session.execute(
        update(Instrument).where(Instrument.symbol == symbol.upper()).values(**allowed)
    )
    return await get_by_symbol(session, symbol)


async def delete_instrument(session: AsyncSession, symbol: str) -> bool:
    q = select(Instrument).where(Instrument.symbol == symbol.upper())
    row = (await session.execute(q)).scalar_one_or_none()
    if not row:
        return False
    await session.delete(row)
    return True


def _to_dict(row: Instrument) -> dict:
    return {
        "id": row.id,
        "symbol": row.symbol,
        "tiingo_ticker": row.tiingo_ticker,
        "name": row.name,
        "asset_type": row.asset_type,
        "exchange": row.exchange,
        "currency": row.currency,
        "is_active": row.is_active,
        "metadata": row.metadata_,
    }


def _row_mapping_to_dict(mapping: dict) -> dict:
    return {
        "id": mapping["id"],
        "symbol": mapping["symbol"],
        "tiingo_ticker": mapping["tiingo_ticker"],
        "name": mapping["name"],
        "asset_type": mapping["asset_type"],
        "exchange": mapping["exchange"],
        "currency": mapping["currency"],
        "is_active": mapping["is_active"],
        "metadata": mapping["metadata"],
    }
