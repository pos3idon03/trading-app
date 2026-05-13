"""Financials fetcher for Strategy Builder cards.

Reads from the fundamentals table. Triggers a fresh ingest via yfinance
if data is missing or older than 1 day.
"""
from datetime import timedelta
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from dal.market_data_dal import get_fundamentals
from dtos.strategy_builder_dto import FinancialsSummary
from features.data_ingestion.financials_service import ingest_financials_for_symbol
from utils.logging import get_logger
from utils.time_utils import utcnow

logger = get_logger(__name__)

_STALE_THRESHOLD = timedelta(days=1)

_METRIC_MAP = {
    "revenue_growth": ["revenueGrowth", "revenue_growth"],
    "free_cash_flow": ["freeCashflow", "free_cash_flow"],
    "current_ratio": ["currentRatio", "current_ratio"],
    "pe_ttm": ["trailingPE", "trailing_pe"],
    "pe_forward": ["forwardPE", "forward_pe"],
    "pb_ratio": ["priceToBook", "price_to_book"],
    "eps_ttm": ["trailingEps", "trailing_eps"],
    "eps_forward": ["forwardEps", "forward_eps"],
    "market_cap": ["marketCap", "market_cap"],
}


async def get_financials_for_asset(
    session: AsyncSession,
    asset_id: int,
    symbol: str,
) -> FinancialsSummary:
    rows = await get_fundamentals(session, asset_id)
    fetched_at = _latest_fetched_at(rows)
    is_stale = _is_stale(fetched_at)

    if not rows or is_stale:
        rows = await _refresh_and_reload(session, symbol, asset_id)
        fetched_at = _latest_fetched_at(rows)
        is_stale = False

    metrics = {r["metric_name"]: r["value"] for r in rows}
    return _build_summary(metrics, fetched_at, is_stale)


async def _refresh_and_reload(
    session: AsyncSession,
    symbol: str,
    asset_id: int,
) -> list[dict]:
    try:
        await ingest_financials_for_symbol(session, symbol)
    except Exception as exc:
        logger.warning("financials_refresh_failed", symbol=symbol, error=str(exc))
    return await get_fundamentals(session, asset_id)


def _latest_fetched_at(rows: list[dict]):
    if not rows:
        return None
    return max((r.get("fetched_at") for r in rows if r.get("fetched_at")), default=None)


def _is_stale(fetched_at) -> bool:
    if fetched_at is None:
        return True
    now = utcnow()
    age = now - fetched_at.replace(tzinfo=fetched_at.tzinfo or None)
    return age > _STALE_THRESHOLD


def _build_summary(
    metrics: dict,
    fetched_at,
    is_stale: bool,
) -> FinancialsSummary:
    def pick(keys: list[str]) -> Optional[float]:
        for k in keys:
            if k in metrics and metrics[k] is not None:
                return float(metrics[k])
        return None

    return FinancialsSummary(
        revenue_growth=pick(_METRIC_MAP["revenue_growth"]),
        free_cash_flow=pick(_METRIC_MAP["free_cash_flow"]),
        current_ratio=pick(_METRIC_MAP["current_ratio"]),
        pe_ttm=pick(_METRIC_MAP["pe_ttm"]),
        pe_forward=pick(_METRIC_MAP["pe_forward"]),
        pb_ratio=pick(_METRIC_MAP["pb_ratio"]),
        eps_ttm=pick(_METRIC_MAP["eps_ttm"]),
        eps_forward=pick(_METRIC_MAP["eps_forward"]),
        market_cap=pick(_METRIC_MAP["market_cap"]),
        fetched_at=fetched_at,
        is_stale=is_stale,
    )
