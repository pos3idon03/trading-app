from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from dal import ohlcv_dal
from features.market_data.ohlcv_resample import resolve_ohlcv_query, resample_source_candidates


def _pick_best_coverage(rows: list[dict]) -> Optional[dict]:
    if not rows:
        return None
    return max(rows, key=lambda row: row.get("bar_count") or 0)


async def get_effective_coverage(
    session: AsyncSession,
    instrument_id: int,
    timeframe: str,
) -> dict[str, Any]:
    native_rows = await ohlcv_dal.get_coverage(session, instrument_id, timeframe)
    best_native = _pick_best_coverage(native_rows)
    if best_native:
        return {
            "timeframe": timeframe,
            "native": native_rows,
            "effective": {
                "min_time": best_native["min_time"],
                "max_time": best_native["max_time"],
                "bar_count": int(best_native["bar_count"]),
                "source": best_native["source"],
                "derived_from": None,
            },
        }

    plan = resolve_ohlcv_query(timeframe)
    if plan.bucket_interval is None:
        return {"timeframe": timeframe, "native": native_rows, "effective": None}

    for source_tf in resample_source_candidates(timeframe):
        source_rows = await ohlcv_dal.get_coverage(session, instrument_id, source_tf)
        best_source = _pick_best_coverage(source_rows)
        if not best_source:
            continue

        min_time = best_source["min_time"]
        max_time = best_source["max_time"]
        if not isinstance(min_time, datetime):
            min_time = datetime.fromisoformat(str(min_time).replace("Z", "+00:00"))
        if not isinstance(max_time, datetime):
            max_time = datetime.fromisoformat(str(max_time).replace("Z", "+00:00"))

        bars, resolved = await ohlcv_dal.get_bars_with_resample(
            session,
            instrument_id,
            timeframe,
            start=min_time,
            end=max_time or datetime.now(timezone.utc),
            limit=10_000,
            fetch_tail=False,
        )
        if not bars:
            continue

        return {
            "timeframe": timeframe,
            "native": native_rows,
            "effective": {
                "min_time": bars[0]["time"],
                "max_time": bars[-1]["time"],
                "bar_count": len(bars),
                "source": resolved,
                "derived_from": source_tf,
            },
        }

    return {"timeframe": timeframe, "native": native_rows, "effective": None}
