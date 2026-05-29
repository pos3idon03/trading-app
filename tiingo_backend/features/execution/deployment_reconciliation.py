from datetime import datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from dal import instrument_dal, ohlcv_dal, trading_deployment_dal
from features.execution.alpaca_symbols import execution_asset_type
from features.execution.deployment_timeframes import (
    bar_time_for_evaluation_slot,
    expected_boundaries,
    ingest_source_for_asset,
    native_fetch_timeframe,
)
from utils.logging import get_logger

logger = get_logger(__name__)

DEFAULT_GRACE_MINUTES = 10


def find_missed_slots(
    deployment: dict,
    as_of: datetime,
    *,
    grace_minutes: int = DEFAULT_GRACE_MINUTES,
    asset_type: str = "stock",
) -> list[datetime]:
    if deployment.get("status") != "active":
        return []
    timeframe = deployment["timeframe"]
    last_evaluated = deployment.get("last_evaluated_bar_time")
    start = last_evaluated or deployment.get("created_at") or as_of
    end = as_of.astimezone(timezone.utc) - timedelta(minutes=grace_minutes)
    if end <= start:
        return []

    missed: list[datetime] = []
    for slot in expected_boundaries(timeframe, start, end, asset_type=asset_type):
        expected_bar = bar_time_for_evaluation_slot(slot, timeframe)
        if last_evaluated is None or expected_bar > last_evaluated.astimezone(timezone.utc):
            missed.append(slot)
    return missed


async def check_ohlcv_freshness(
    session: AsyncSession,
    *,
    symbol: str,
    timeframe: str,
    asset_type: str,
    expected_bar_time: datetime | None,
) -> datetime | None:
    instrument = await instrument_dal.get_by_symbol(session, symbol.upper())
    if not instrument:
        return None

    native_tf = native_fetch_timeframe(timeframe)
    source = ingest_source_for_asset(asset_type, native_tf)
    bars, _ = await ohlcv_dal.get_bars(
        session,
        instrument["id"],
        native_tf,
        source=source,
        limit=1,
        fetch_tail=True,
    )
    if not bars:
        return None
    bar_time = bars[-1].get("time")
    if not isinstance(bar_time, datetime):
        return None
    return bar_time.astimezone(timezone.utc)


def _latest_expected_bar(
    deployment: dict,
    as_of: datetime,
    *,
    grace_minutes: int,
    asset_type: str = "stock",
) -> datetime | None:
    missed = find_missed_slots(
        deployment,
        as_of,
        grace_minutes=grace_minutes,
        asset_type=asset_type,
    )
    if missed:
        return bar_time_for_evaluation_slot(missed[-1], deployment["timeframe"])
    last_evaluated = deployment.get("last_evaluated_bar_time")
    if last_evaluated:
        return last_evaluated.astimezone(timezone.utc)
    end = as_of.astimezone(timezone.utc) - timedelta(minutes=grace_minutes)
    boundaries = expected_boundaries(
        deployment["timeframe"],
        end - timedelta(days=7),
        end,
        asset_type=asset_type,
    )
    if not boundaries:
        return None
    return bar_time_for_evaluation_slot(boundaries[-1], deployment["timeframe"])


async def build_deployment_readiness(
    session: AsyncSession,
    deployment: dict,
    as_of: datetime,
    *,
    asset_type: str = "stock",
    grace_minutes: int = DEFAULT_GRACE_MINUTES,
) -> dict:
    if deployment.get("status") != "active":
        return {
            "update_status": "unknown",
            "expected_latest_bar_time": None,
            "ohlcv_latest_bar_time": None,
            "missed_slot_count": 0,
        }

    missed = find_missed_slots(
        deployment,
        as_of,
        grace_minutes=grace_minutes,
        asset_type=asset_type,
    )
    expected_bar = _latest_expected_bar(
        deployment,
        as_of,
        grace_minutes=grace_minutes,
        asset_type=asset_type,
    )
    ohlcv_latest = await check_ohlcv_freshness(
        session,
        symbol=deployment["symbol"],
        timeframe=deployment["timeframe"],
        asset_type=asset_type,
        expected_bar_time=expected_bar,
    )

    stale = bool(missed)
    if not stale and expected_bar and ohlcv_latest:
        stale = ohlcv_latest.astimezone(timezone.utc) < expected_bar

    last_evaluated = deployment.get("last_evaluated_bar_time")
    if not stale and expected_bar and last_evaluated:
        stale = last_evaluated.astimezone(timezone.utc) < expected_bar

    return {
        "update_status": "stale" if stale else "current",
        "expected_latest_bar_time": expected_bar,
        "ohlcv_latest_bar_time": ohlcv_latest,
        "missed_slot_count": len(missed),
    }


async def reconcile_missed_updates(
    session: AsyncSession,
    as_of: datetime | None = None,
    *,
    grace_minutes: int = DEFAULT_GRACE_MINUTES,
) -> dict:
    now = as_of or datetime.now(timezone.utc)
    active = await trading_deployment_dal.list_active_deployments_with_instrument(session)
    slots_by_tf: dict[tuple[datetime, str], None] = {}

    for deployment in active:
        tf = deployment["timeframe"]
        asset_type = execution_asset_type(deployment.get("asset_type"))
        for slot in find_missed_slots(
            deployment,
            now,
            grace_minutes=grace_minutes,
            asset_type=asset_type,
        ):
            slots_by_tf[(slot, tf)] = None

    results: list[dict] = []
    for slot, tf in sorted(slots_by_tf.keys(), key=lambda item: (item[0], item[1])):
        from features.execution.evaluation_cycle import run_deployment_cycle

        outcome = await run_deployment_cycle(
            session,
            as_of=slot,
            force_timeframes={tf},
            skip_reconciliation=True,
        )
        results.append({"slot": slot.isoformat(), "timeframe": tf, "outcome": outcome})
        logger.info(
            "deployment_reconciliation_catch_up",
            slot=slot.isoformat(),
            timeframe=tf,
            skipped=outcome.get("skipped"),
        )

    return {
        "as_of": now.isoformat(),
        "catch_up_runs": len(results),
        "results": results,
    }
