"""AI Agent analysis routes."""
import asyncio
import dataclasses
from functools import partial

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from dal.ai_agent_dal import (
    create_analysis,
    get_analysis,
    update_analysis_error,
    update_analysis_result,
)
from dal.market_data_dal import get_asset_id_by_symbol
from db import get_db
from dtos.ai_agent_dto import (
    AgentAnalysisRequest,
    AgentAnalysisResponse,
    AgentReports,
    TradingSignal,
)
from features.ai_agents.crew import run_analysis_crew
from features.ai_agents.llm_error_handler import classify_llm_error
from utils.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()


@router.post("/analyze", response_model=AgentAnalysisResponse, status_code=202)
async def analyze_asset(
    request: AgentAnalysisRequest,
    session: AsyncSession = Depends(get_db),
) -> AgentAnalysisResponse:
    """Run the full multi-agent research crew for an asset and return a trading signal.

    Runs fundamental (SEC filings), macro (FRED data), and sentiment (news) agents,
    then synthesizes their outputs into a structured JSON trading signal.
    The symbol must already exist in the assets table (ingest it first).
    """
    symbol = request.symbol.upper()
    asset_id = await get_asset_id_by_symbol(session, symbol)
    if asset_id is None:
        raise HTTPException(
            status_code=404,
            detail=f"Asset '{symbol}' is not registered. Ingest it first via /ingest.",
        )

    analysis_id = await create_analysis(session, symbol=symbol, llm=request.llm, asset_id=asset_id)

    try:
        loop = asyncio.get_running_loop()
        trading_signal = await loop.run_in_executor(
            None, partial(run_analysis_crew, ticker=symbol, llm=request.llm)
        )

        signal_dict = _signal_to_dict(trading_signal)

        await update_analysis_result(
            session,
            analysis_id=analysis_id,
            signal=signal_dict,
            fundamental_report=trading_signal.fundamental_report,
            macro_report=trading_signal.macro_report,
            sentiment_report=trading_signal.sentiment_report,
            bias=trading_signal.bias,
            conviction_score=trading_signal.conviction_score,
            sentiment_score=trading_signal.sentiment_score,
            duration_ms=trading_signal.duration_ms,
            provider_used=trading_signal.provider_used,
        )

        return AgentAnalysisResponse(
            analysis_id=analysis_id,
            asset_id=asset_id,
            symbol=symbol,
            status="done",
            signal=TradingSignal(**signal_dict),
            reports=AgentReports(
                fundamental=trading_signal.fundamental_report,
                macro=trading_signal.macro_report,
                sentiment=trading_signal.sentiment_report,
            ),
            duration_ms=trading_signal.duration_ms,
            provider_used=trading_signal.provider_used,
        )
    except Exception as exc:
        user_message = classify_llm_error(exc)
        logger.error("agent_analysis_error", analysis_id=analysis_id, error=str(exc))
        await update_analysis_error(session, analysis_id, user_message)
        raise HTTPException(status_code=500, detail=user_message)


@router.get("/{analysis_id}", response_model=AgentAnalysisResponse)
async def get_agent_analysis(
    analysis_id: int,
    session: AsyncSession = Depends(get_db),
) -> AgentAnalysisResponse:
    """Retrieve a stored agent analysis result by ID."""
    record = await get_analysis(session, analysis_id)
    if record is None:
        raise HTTPException(status_code=404, detail=f"AgentAnalysis {analysis_id} not found")

    signal = TradingSignal(**record.signal) if record.signal else None
    reports = AgentReports(
        fundamental=record.fundamental_report,
        macro=record.macro_report,
        sentiment=record.sentiment_report,
    ) if record.status == "done" else None

    return AgentAnalysisResponse(
        analysis_id=record.id,
        asset_id=record.asset_id,
        symbol=record.symbol,
        status=record.status,
        signal=signal,
        reports=reports,
        duration_ms=record.duration_ms,
        error_message=record.error_message,
        provider_used=record.provider_used,
    )


def _signal_to_dict(trading_signal) -> dict:
    """Convert TradingSignal dataclass to a JSON-serializable dict."""
    d = dataclasses.asdict(trading_signal)
    for drop_key in ("raw_output", "fundamental_report", "macro_report", "sentiment_report", "duration_ms"):
        d.pop(drop_key, None)
    return d
