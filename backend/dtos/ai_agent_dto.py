"""DTOs for the AI Agent analysis endpoints."""
from typing import Optional

from pydantic import BaseModel, Field


class AgentAnalysisRequest(BaseModel):
    symbol: str = Field(..., description="Asset ticker symbol, e.g. AAPL")
    llm: str = Field(
        default="gpt-4o-mini",
        description=(
            "LLM model slug for CrewAI agents. "
            "OpenAI: gpt-4o-mini, gpt-4o. "
            "Gemini (Google AI Studio): gemini-3-flash-preview, gemini-3.1-pro-preview. "
            "When fallback is enabled, each model automatically falls back to its "
            "paired provider on failure."
        ),
    )


class AgentReports(BaseModel):
    fundamental: Optional[str] = None
    macro: Optional[str] = None
    sentiment: Optional[str] = None


class TradingSignal(BaseModel):
    asset: str
    bias: str = Field(description="bullish | bearish | neutral")
    conviction_score: float = Field(description="Confidence in the bias, 0.0 to 1.0")
    fundamental_summary: str
    macro_summary: str
    sentiment_score: float = Field(description="Sentiment from -1.0 (bearish) to +1.0 (bullish)")
    reasoning: str
    key_risk: str
    timestamp: str


class AgentAnalysisResponse(BaseModel):
    analysis_id: int
    symbol: str
    status: str
    signal: Optional[TradingSignal] = None
    reports: Optional[AgentReports] = None
    duration_ms: Optional[int] = None
    error_message: Optional[str] = None
    provider_used: Optional[str] = Field(
        default=None,
        description="Primary LiteLLM model ID that was used (or attempted) for this analysis.",
    )
