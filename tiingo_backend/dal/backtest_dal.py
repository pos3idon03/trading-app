from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from models.backtest import BacktestRun


async def create_run(
    session: AsyncSession,
    *,
    instrument_id: int,
    symbol: str,
    strategy: str,
    params: dict,
    timeframe: str,
    start_date: datetime | None,
    end_date: datetime | None,
    initial_cash: float,
    commission_bps: float,
) -> dict:
    run_id = uuid4()
    now = datetime.now(timezone.utc)
    row = BacktestRun(
        id=run_id,
        instrument_id=instrument_id,
        symbol=symbol.upper(),
        strategy=strategy,
        params=params,
        timeframe=timeframe,
        start_date=start_date,
        end_date=end_date,
        initial_cash=initial_cash,
        commission_bps=commission_bps,
        status="running",
        created_at=now,
    )
    session.add(row)
    await session.flush()
    return _to_dict(row)


async def finish_run(
    session: AsyncSession,
    run_id: UUID,
    *,
    status: str,
    metrics: dict | None = None,
    equity_curve: list | None = None,
    trades: list | None = None,
    benchmark: dict | None = None,
    error_message: str | None = None,
) -> None:
    await session.execute(
        update(BacktestRun)
        .where(BacktestRun.id == run_id)
        .values(
            status=status,
            metrics=metrics,
            equity_curve=equity_curve,
            trades=trades,
            benchmark=benchmark,
            error_message=error_message,
            finished_at=datetime.now(timezone.utc),
        )
    )


async def get_run(session: AsyncSession, run_id: UUID) -> dict | None:
    q = select(BacktestRun).where(BacktestRun.id == run_id)
    row = (await session.execute(q)).scalar_one_or_none()
    return _to_dict(row) if row else None


def _to_dict(row: BacktestRun) -> dict:
    return {
        "id": row.id,
        "instrument_id": row.instrument_id,
        "symbol": row.symbol,
        "strategy": row.strategy,
        "params": row.params,
        "timeframe": row.timeframe,
        "start_date": row.start_date,
        "end_date": row.end_date,
        "initial_cash": float(row.initial_cash),
        "commission_bps": float(row.commission_bps),
        "status": row.status,
        "metrics": row.metrics,
        "equity_curve": row.equity_curve,
        "trades": row.trades,
        "benchmark": row.benchmark,
        "error_message": row.error_message,
        "created_at": row.created_at,
        "finished_at": row.finished_at,
    }
