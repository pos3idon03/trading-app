from datetime import date, datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from models.execution_settings import ExecutionSettings

SETTINGS_ID = 1


async def get_settings(session: AsyncSession) -> dict:
    q = select(ExecutionSettings).where(ExecutionSettings.id == SETTINGS_ID)
    row = (await session.execute(q)).scalar_one_or_none()
    if row is None:
        raise RuntimeError("execution_settings singleton row missing")
    return _to_dict(row)


async def set_kill_switch(session: AsyncSession, enabled: bool) -> dict:
    now = datetime.now(timezone.utc)
    await session.execute(
        update(ExecutionSettings)
        .where(ExecutionSettings.id == SETTINGS_ID)
        .values(kill_switch_enabled=enabled, updated_at=now),
    )
    await session.flush()
    return await get_settings(session)


async def update_day_start_equity(
    session: AsyncSession,
    *,
    equity: float,
    day: date,
) -> dict:
    now = datetime.now(timezone.utc)
    await session.execute(
        update(ExecutionSettings)
        .where(ExecutionSettings.id == SETTINGS_ID)
        .values(day_start_equity=equity, day_start_date=day, updated_at=now),
    )
    await session.flush()
    return await get_settings(session)


async def record_order_submission(session: AsyncSession) -> dict:
    settings = await get_settings(session)
    now = datetime.now(timezone.utc)
    window_start = settings.get("minute_window_start")
    orders_count = settings.get("orders_this_minute") or 0

    if window_start is None or (now - window_start).total_seconds() >= 60:
        orders_count = 1
        window_start = now
    else:
        orders_count += 1

    await session.execute(
        update(ExecutionSettings)
        .where(ExecutionSettings.id == SETTINGS_ID)
        .values(
            orders_this_minute=orders_count,
            minute_window_start=window_start,
            updated_at=now,
        ),
    )
    await session.flush()
    return await get_settings(session)


def _to_dict(row: ExecutionSettings) -> dict:
    return {
        "id": row.id,
        "kill_switch_enabled": row.kill_switch_enabled,
        "day_start_equity": float(row.day_start_equity) if row.day_start_equity else None,
        "day_start_date": row.day_start_date,
        "orders_this_minute": row.orders_this_minute,
        "minute_window_start": row.minute_window_start,
        "updated_at": row.updated_at,
    }
