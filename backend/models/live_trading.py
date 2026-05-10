"""SQLAlchemy models for live trading indicators and signals."""
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Double, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from db import Base


class LiveIndicator(Base):
    __tablename__ = "live_indicators"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    asset_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("assets.id", ondelete="SET NULL"), nullable=True, index=True,
    )
    symbol: Mapped[str] = mapped_column(String, nullable=False)
    timeframe: Mapped[str] = mapped_column(String, nullable=False)
    rsi: Mapped[float | None] = mapped_column(Double)
    macd: Mapped[float | None] = mapped_column(Double)
    macd_signal: Mapped[float | None] = mapped_column(Double)
    macd_histogram: Mapped[float | None] = mapped_column(Double)
    bb_upper: Mapped[float | None] = mapped_column(Double)
    bb_middle: Mapped[float | None] = mapped_column(Double)
    bb_lower: Mapped[float | None] = mapped_column(Double)
    vwap: Mapped[float | None] = mapped_column(Double)
    close_price: Mapped[float | None] = mapped_column(Double)
    volume: Mapped[int | None] = mapped_column(BigInteger)
    raw_data: Mapped[dict | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class TradingSignal(Base):
    __tablename__ = "trading_signals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    asset_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("assets.id", ondelete="SET NULL"), nullable=True, index=True,
    )
    symbol: Mapped[str] = mapped_column(String, nullable=False)
    timeframe: Mapped[str] = mapped_column(String, nullable=False)
    action: Mapped[str] = mapped_column(String, nullable=False)
    confidence: Mapped[float | None] = mapped_column(Double)
    technical_score: Mapped[float | None] = mapped_column(Double)
    risk_score: Mapped[float | None] = mapped_column(Double)
    ai_score: Mapped[float | None] = mapped_column(Double)
    indicator_snapshot: Mapped[dict | None] = mapped_column(JSONB)
    risk_data: Mapped[dict | None] = mapped_column(JSONB)
    ai_signal: Mapped[dict | None] = mapped_column(JSONB)
    reasoning: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
