"""Financials routes — fundamental data, financial statements, company profiles."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from dal.market_data_dal import (
    get_asset_id_by_symbol,
    get_company_profile,
    get_financial_statements,
    get_fundamentals,
)
from db import get_db
from dtos.market_data_dto import (
    CompanyProfileResponse,
    FinancialStatementResponse,
    FinancialStatementRow,
    FinancialsIngestResponse,
    FundamentalsOverviewResponse,
)
from features.data_ingestion.financials_service import ingest_financials_for_symbol
from utils.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()


async def _resolve_asset(symbol: str, session: AsyncSession) -> tuple[str, int]:
    symbol = symbol.upper()
    asset_id = await get_asset_id_by_symbol(session, symbol)
    if asset_id is None:
        raise HTTPException(status_code=404, detail=f"Asset not found: {symbol}")
    return symbol, asset_id


def _pivot_statement(rows: list[dict], stmt_type: str) -> tuple[list[str], list[FinancialStatementRow]]:
    """Pivot flat statement rows into period columns."""
    prefix = f"{stmt_type}."
    data: dict[str, dict[str, float]] = {}
    periods_set: set[str] = set()

    for row in rows:
        metric = row["metric_name"].removeprefix(prefix)
        period = row["period"] or ""
        if period:
            periods_set.add(period)
            data.setdefault(metric, {})[period] = row["value"]

    periods = sorted(periods_set, reverse=True)
    result_rows = sorted(
        [FinancialStatementRow(metric=m, values=v) for m, v in data.items()],
        key=lambda r: r.metric,
    )
    return periods, result_rows


@router.get("/{symbol}/overview", response_model=FundamentalsOverviewResponse)
async def get_overview(
    symbol: str,
    session: AsyncSession = Depends(get_db),
) -> FundamentalsOverviewResponse:
    """Return the latest snapshot of scalar fundamental metrics for a symbol."""
    symbol, asset_id = await _resolve_asset(symbol, session)
    rows = await get_fundamentals(session, asset_id)
    if not rows:
        raise HTTPException(
            status_code=404,
            detail=f"No fundamental data for {symbol}. POST /financials/{symbol}/ingest first.",
        )
    metrics = {r["metric_name"]: r["value"] for r in rows}
    fetched_at = max((r["fetched_at"] for r in rows), default=None)
    return FundamentalsOverviewResponse(
        symbol=symbol, asset_id=asset_id, metrics=metrics, fetched_at=fetched_at
    )


@router.get("/{symbol}/income-statement", response_model=FinancialStatementResponse)
async def get_income_statement(
    symbol: str,
    session: AsyncSession = Depends(get_db),
) -> FinancialStatementResponse:
    """Return income statement line items by period."""
    symbol, asset_id = await _resolve_asset(symbol, session)
    rows = await get_financial_statements(session, asset_id, "income_stmt")
    periods, result_rows = _pivot_statement(rows, "income_stmt")
    return FinancialStatementResponse(
        symbol=symbol, asset_id=asset_id,
        statement_type="income_stmt", periods=periods, rows=result_rows,
    )


@router.get("/{symbol}/balance-sheet", response_model=FinancialStatementResponse)
async def get_balance_sheet(
    symbol: str,
    session: AsyncSession = Depends(get_db),
) -> FinancialStatementResponse:
    """Return balance sheet line items by period."""
    symbol, asset_id = await _resolve_asset(symbol, session)
    rows = await get_financial_statements(session, asset_id, "balance_sheet")
    periods, result_rows = _pivot_statement(rows, "balance_sheet")
    return FinancialStatementResponse(
        symbol=symbol, asset_id=asset_id,
        statement_type="balance_sheet", periods=periods, rows=result_rows,
    )


@router.get("/{symbol}/cash-flow", response_model=FinancialStatementResponse)
async def get_cash_flow(
    symbol: str,
    session: AsyncSession = Depends(get_db),
) -> FinancialStatementResponse:
    """Return cash flow statement line items by period."""
    symbol, asset_id = await _resolve_asset(symbol, session)
    rows = await get_financial_statements(session, asset_id, "cashflow")
    periods, result_rows = _pivot_statement(rows, "cashflow")
    return FinancialStatementResponse(
        symbol=symbol, asset_id=asset_id,
        statement_type="cashflow", periods=periods, rows=result_rows,
    )


@router.get("/{symbol}/profile", response_model=CompanyProfileResponse)
async def get_profile(
    symbol: str,
    session: AsyncSession = Depends(get_db),
) -> CompanyProfileResponse:
    """Return qualitative company profile (sector, industry, summary, officers)."""
    symbol, asset_id = await _resolve_asset(symbol, session)
    profile = await get_company_profile(session, asset_id)
    if profile is None:
        raise HTTPException(
            status_code=404,
            detail=f"No profile data for {symbol}. POST /financials/{symbol}/ingest first.",
        )
    return CompanyProfileResponse(symbol=symbol, asset_id=asset_id, **profile)


@router.post("/{symbol}/ingest", response_model=FinancialsIngestResponse, status_code=202)
async def ingest_financials(
    symbol: str,
    session: AsyncSession = Depends(get_db),
) -> FinancialsIngestResponse:
    """Trigger fundamentals, financial statements, and company profile ingestion."""
    symbol = symbol.upper()
    logger.info("financials_ingest_triggered", symbol=symbol)
    try:
        result = await ingest_financials_for_symbol(session, symbol)
        return FinancialsIngestResponse(
            symbol=symbol,
            fundamentals_inserted=result["fundamentals_inserted"],
            profile_updated=result["profile_updated"],
            status="completed",
        )
    except Exception as exc:
        logger.error("financials_ingest_failed", symbol=symbol, error=str(exc))
        raise HTTPException(status_code=500, detail=str(exc))
