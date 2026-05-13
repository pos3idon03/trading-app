"""DAL for AI agent analysis records."""
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from models.ai_agent import AgentAnalysis
from utils.logging import get_logger

logger = get_logger(__name__)


async def create_analysis(
    session: AsyncSession,
    symbol: str,
    llm: str,
    asset_id: int | None = None,
) -> int:
    record = AgentAnalysis(symbol=symbol, llm=llm, status="running", asset_id=asset_id)
    session.add(record)
    await session.flush()
    return record.id


async def update_analysis_result(
    session: AsyncSession,
    analysis_id: int,
    signal: dict,
    fundamental_report: str,
    macro_report: str,
    sentiment_report: str,
    bias: str,
    conviction_score: float,
    macro_score: float,
    sentiment_score: float,
    duration_ms: int,
    provider_used: str = "",
    status: str = "done",
    error_message: Optional[str] = None,
) -> None:
    record = await session.get(AgentAnalysis, analysis_id)
    if record is None:
        raise ValueError(f"AgentAnalysis {analysis_id} not found")
    record.signal = signal
    record.fundamental_report = fundamental_report
    record.macro_report = macro_report
    record.sentiment_report = sentiment_report
    record.bias = bias
    record.conviction_score = conviction_score
    record.macro_score = macro_score
    record.sentiment_score = sentiment_score
    record.duration_ms = duration_ms
    record.provider_used = provider_used or None
    record.status = status
    record.error_message = error_message


async def update_analysis_error(
    session: AsyncSession,
    analysis_id: int,
    error_message: str,
) -> None:
    record = await session.get(AgentAnalysis, analysis_id)
    if record is None:
        return
    record.status = "error"
    record.error_message = error_message


async def get_analysis(session: AsyncSession, analysis_id: int) -> Optional[AgentAnalysis]:
    return await session.get(AgentAnalysis, analysis_id)
