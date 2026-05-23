from datetime import date, datetime, timezone

from sqlalchemy import or_, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from features.market_data.fundamentals_annual import aggregate_quarterly_to_annual
from models.market_data import Fundamental

_QUARTERLY_PERIOD = Fundamental.period.op("~")(r"^[0-9]{4}-Q[1-4]$")
_ANNUAL_PERIOD = or_(Fundamental.period.like("FY-%"), Fundamental.period.like("%-Q0"))


def _stamp_stored_at(rows: list[dict]) -> list[dict]:
    now = datetime.now(timezone.utc)
    return [{**row, "stored_at": row.get("stored_at", now)} for row in rows]


async def delete_fundamentals_for_instrument(
    session: AsyncSession,
    instrument_id: int,
) -> int:
    from sqlalchemy import delete

    result = await session.execute(
        delete(Fundamental).where(Fundamental.instrument_id == instrument_id),
    )
    return result.rowcount or 0


async def bulk_insert_fundamentals(session: AsyncSession, rows: list[dict]) -> int:
    if not rows:
        return 0
    stmt = pg_insert(Fundamental).values(_stamp_stored_at(rows))
    stmt = stmt.on_conflict_do_nothing(constraint="uq_fundamentals")
    result = await session.execute(stmt)
    return result.rowcount or 0


def _period_clause(period_type: str | None):
    if period_type == "quarterly":
        return _QUARTERLY_PERIOD
    if period_type == "annual":
        return _ANNUAL_PERIOD
    return None


def _rows_to_dicts(rows) -> list[dict]:
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


async def _query_fundamentals(
    session: AsyncSession,
    instrument_id: int,
    *,
    period_clause,
    metric_names: list[str] | None,
    order: str,
    limit: int | None,
    start: date | None = None,
    end: date | None = None,
) -> list[dict]:
    from sqlalchemy import select

    clauses = [Fundamental.instrument_id == instrument_id]
    if period_clause is not None:
        clauses.append(period_clause)
    if metric_names:
        clauses.append(Fundamental.metric_name.in_(metric_names))
    if start is not None:
        clauses.append(Fundamental.time >= datetime.combine(start, datetime.min.time(), tzinfo=timezone.utc))
    if end is not None:
        clauses.append(Fundamental.time <= datetime.combine(end, datetime.max.time(), tzinfo=timezone.utc))

    order_col = Fundamental.time.asc() if order == "asc" else Fundamental.time.desc()
    q = select(Fundamental).where(*clauses).order_by(order_col)
    if limit is not None:
        q = q.limit(limit)

    rows = (await session.execute(q)).scalars().all()
    return _rows_to_dicts(rows)


async def list_fundamentals_for_symbol(
    session: AsyncSession,
    instrument_id: int,
    *,
    period_type: str | None = None,
    metric_names: list[str] | None = None,
    order: str = "desc",
    limit: int | None = 200,
    start: date | None = None,
    end: date | None = None,
) -> list[dict]:
    if period_type == "annual":
        native = await _query_fundamentals(
            session,
            instrument_id,
            period_clause=_ANNUAL_PERIOD,
            metric_names=metric_names,
            order=order,
            limit=limit,
            start=start,
            end=end,
        )
        if native:
            return native
        quarterly = await _query_fundamentals(
            session,
            instrument_id,
            period_clause=_QUARTERLY_PERIOD,
            metric_names=metric_names,
            order="asc",
            limit=None,
            start=start,
            end=end,
        )
        annual = aggregate_quarterly_to_annual(quarterly)
        annual.sort(key=lambda r: r["time"], reverse=(order == "desc"))
        if limit is not None:
            annual = annual[:limit]
        return annual

    period_clause = _period_clause(period_type)
    return await _query_fundamentals(
        session,
        instrument_id,
        period_clause=period_clause,
        metric_names=metric_names,
        order=order,
        limit=limit,
        start=start,
        end=end,
    )


async def list_fundamentals_coverage(
    session: AsyncSession,
    limit: int = 200,
) -> list[dict]:
    q = text("""
        SELECT i.symbol,
               i.name,
               COUNT(*) AS metric_count,
               MIN(f.time) AS first_report_date,
               MAX(f.time) AS latest_report_date,
               MAX(f.stored_at) AS last_ingested_at
        FROM fundamentals f
        JOIN instruments i ON i.id = f.instrument_id
        GROUP BY i.id, i.symbol, i.name
        ORDER BY last_ingested_at DESC
        LIMIT :lim
    """)
    rows = await session.execute(q, {"lim": limit})
    return [dict(r._mapping) for r in rows]
