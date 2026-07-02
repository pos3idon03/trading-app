from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from dal import universe_dal


async def resolve_universe_symbols(
    session: AsyncSession,
    *,
    universe_id: int | None,
    symbols: list[str] | None,
    as_of: date,
) -> tuple[list[str], list[str]]:
    warnings: list[str] = []
    if symbols:
        resolved = sorted({s.upper() for s in symbols if s})
        if not resolved:
            raise ValueError("symbols list is empty")
        return resolved, warnings

    if universe_id is None:
        raise ValueError("Either universe_id or symbols must be provided")

    universe = await universe_dal.get_universe(session, universe_id)
    if not universe:
        raise LookupError(f"Universe not found: {universe_id}")

    members = await universe_dal.get_members_as_of(session, universe_id, as_of)
    if not members:
        warnings.append(f"No universe members as of {as_of.isoformat()}")
    return members, warnings


async def get_members_for_range(
    session: AsyncSession,
    universe_id: int,
    start: date,
    end: date,
) -> dict[date, list[str]]:
    """Return union of members active on each rebalance date (daily keys)."""
    all_members = await universe_dal.list_all_members(session, universe_id)
    result: dict[date, list[str]] = {}
    current = start
    while current <= end:
        active = sorted({
            m["symbol"]
            for m in all_members
            if m["effective_from"] <= current
            and (m["effective_to"] is None or m["effective_to"] >= current)
        })
        result[current] = active
        current = date.fromordinal(current.toordinal() + 1)
    return result
