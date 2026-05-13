"""AI Agents data fetcher for Strategy Builder cards.

Reads the most recent completed agent analysis for the given asset.
"""
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from dtos.strategy_builder_dto import AIAgentSummary
from models.ai_agent import AgentAnalysis
from utils.logging import get_logger

logger = get_logger(__name__)


async def get_latest_agent_analysis(
    session: AsyncSession,
    asset_id: int,
) -> Optional[AIAgentSummary]:
    """Return the most recent completed agent analysis for an asset, or None."""
    stmt = (
        select(AgentAnalysis)
        .where(
            AgentAnalysis.asset_id == asset_id,
            AgentAnalysis.status == "done",
        )
        .order_by(AgentAnalysis.created_at.desc())
        .limit(1)
    )
    result = await session.execute(stmt)
    record = result.scalars().first()

    if record is None:
        return None

    return _build_summary(record)


def _build_summary(record: AgentAnalysis) -> AIAgentSummary:
    signal = record.signal or {}
    return AIAgentSummary(
        analysis_id=record.id,
        bias=record.bias,
        conviction_score=record.conviction_score,
        macro_score=_resolve_macro_score(record, signal),
        sentiment_score=record.sentiment_score,
        fundamental_summary=signal.get("fundamental_summary"),
        macro_summary=signal.get("macro_summary"),
        reasoning=signal.get("reasoning"),
        key_risk=signal.get("key_risk"),
        created_at=record.created_at,
    )


def _resolve_macro_score(record: AgentAnalysis, signal: dict) -> Optional[float]:
    """Return macro_score from the dedicated column, falling back to the signal blob for older rows."""
    if record.macro_score is not None:
        return record.macro_score
    blob_value = signal.get("macro_score")
    if blob_value is None:
        blob_value = signal.get("macro_sentiment_score")
    return float(blob_value) if blob_value is not None else None
