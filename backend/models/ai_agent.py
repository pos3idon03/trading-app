"""SQLAlchemy model for AI agent analysis records."""
from datetime import datetime

from sqlalchemy import DateTime, Double, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from db import Base


class AgentAnalysis(Base):
    __tablename__ = "agent_analyses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    asset_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("assets.id", ondelete="SET NULL"), nullable=True, index=True,
    )
    symbol: Mapped[str] = mapped_column(String, nullable=False)
    llm: Mapped[str] = mapped_column(String, nullable=False, default="gpt-4o-mini")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    signal: Mapped[dict | None] = mapped_column(JSONB)
    fundamental_report: Mapped[str | None] = mapped_column(Text)
    macro_report: Mapped[str | None] = mapped_column(Text)
    sentiment_report: Mapped[str | None] = mapped_column(Text)
    bias: Mapped[str | None] = mapped_column(String)
    conviction_score: Mapped[float | None] = mapped_column(Double)
    sentiment_score: Mapped[float | None] = mapped_column(Double)
    duration_ms: Mapped[int | None] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String, nullable=False, default="pending")
    error_message: Mapped[str | None] = mapped_column(Text)
    provider_used: Mapped[str | None] = mapped_column(String)
