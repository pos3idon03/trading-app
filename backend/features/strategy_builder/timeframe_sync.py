"""Sync trading_strategies.algo_timeframe from attached algo timeframes."""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from dal.strategy_builder_dal import get_linked_algos, update_thresholds
from utils.timeframes import finest_timeframe, normalize_timeframe


def collect_attachment_timeframes(rows: list[dict]) -> list[str]:
    """Collect all signal timeframes from standalone and combo-leg attachments."""
    result: list[str] = []
    for row in rows:
        tf = normalize_timeframe(row.get("timeframe") or "1d")
        result.append(tf)
        if not str(row.get("strategy_name", "")).startswith("combo:"):
            continue
        params = row.get("params") or {}
        for leg in params.get("strategies") or []:
            leg_tf = leg.get("timeframe")
            if leg_tf:
                result.append(normalize_timeframe(leg_tf))
    return result


async def sync_algo_timeframe_from_attachments(
    session: AsyncSession,
    strategy_id: int,
) -> None:
    """Set card algo_timeframe to the finest (shortest) attached signal timeframe."""
    rows = await get_linked_algos(session, strategy_id)
    finest = finest_timeframe(collect_attachment_timeframes(rows))
    await update_thresholds(session, strategy_id, {"algo_timeframe": finest})
