from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from dal import job_dal
from features.foundation.orchestrator import (
    preview_foundation_forecast_for_symbol,
    run_foundation_backtest_for_symbol,
)


def _parse_datetime(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    text = str(value).replace("Z", "+00:00")
    parsed = datetime.fromisoformat(text)
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


async def _update_progress(
    session: AsyncSession,
    job_id: UUID | None,
    progress: int,
) -> None:
    if job_id is None:
        return
    await job_dal.update_job_progress(session, job_id, progress)
    await session.commit()


async def execute_foundation_job(
    session: AsyncSession,
    job_type: str,
    params: dict,
    job_id: UUID | None = None,
) -> dict:
    await _update_progress(session, job_id, 5)
    start = _parse_datetime(params.get("start"))
    end = _parse_datetime(params.get("end"))

    if job_type == "foundation_preview":
        result = await preview_foundation_forecast_for_symbol(
            session,
            symbol=params["symbol"],
            model_type=params.get("model_type", "foundation_timesfm_2_5"),
            params=params.get("params"),
            timeframe=params.get("timeframe", "1d"),
            start=start,
            end=end,
        )
        await _update_progress(session, job_id, 100)
        return result

    if job_type == "foundation_backtest":
        result = await run_foundation_backtest_for_symbol(
            session,
            symbol=params["symbol"],
            model_type=params.get("model_type", "foundation_timesfm_2_5"),
            params=params.get("params"),
            timeframe=params.get("timeframe", "1d"),
            start=start,
            end=end,
            initial_cash=float(params.get("initial_cash", 10_000)),
            commission_bps=float(params.get("commission_bps", 5)),
        )
        await _update_progress(session, job_id, 100)
        return {
            "run_id": str(result["id"]),
            "symbol": result["symbol"],
            "model_type": result["strategy"],
            "status": result["status"],
            "metrics": result.get("metrics"),
        }

    raise ValueError(f"Unknown foundation job type: {job_type}")
