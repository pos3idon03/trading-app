from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Double, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from db import Base


class OHLCV(Base):
    __tablename__ = "ohlcv"

    time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, primary_key=True)
    asset_id: Mapped[int] = mapped_column(Integer, ForeignKey("assets.id", ondelete="CASCADE"), nullable=False, primary_key=True)
    timeframe: Mapped[str] = mapped_column(String, nullable=False, primary_key=True)
    source: Mapped[str] = mapped_column(String, nullable=False, primary_key=True)
    open: Mapped[float] = mapped_column(Double, nullable=False)
    high: Mapped[float] = mapped_column(Double, nullable=False)
    low: Mapped[float] = mapped_column(Double, nullable=False)
    close: Mapped[float] = mapped_column(Double, nullable=False)
    volume: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    vwap: Mapped[float | None] = mapped_column(Double)
    trade_count: Mapped[int | None] = mapped_column(Integer)

    __table_args__ = (
        UniqueConstraint("time", "asset_id", "timeframe", "source", name="uq_ohlcv"),
    )


class Fundamental(Base):
    __tablename__ = "fundamentals"

    time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, primary_key=True)
    asset_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("assets.id", ondelete="CASCADE"), primary_key=True, nullable=True)
    metric_name: Mapped[str] = mapped_column(String, nullable=False, primary_key=True)
    source: Mapped[str] = mapped_column(String, nullable=False, primary_key=True)
    value: Mapped[float] = mapped_column(Double, nullable=False)
    period: Mapped[str | None] = mapped_column(String)

    __table_args__ = (
        UniqueConstraint("time", "asset_id", "metric_name", "source", name="uq_fundamentals"),
    )


class CompanyProfile(Base):
    __tablename__ = "company_profiles"

    asset_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("assets.id", ondelete="CASCADE"), primary_key=True
    )
    sector: Mapped[str | None] = mapped_column(String)
    industry: Mapped[str | None] = mapped_column(String)
    business_summary: Mapped[str | None] = mapped_column(Text)
    website: Mapped[str | None] = mapped_column(String)
    country: Mapped[str | None] = mapped_column(String)
    employees: Mapped[int | None] = mapped_column(Integer)
    officers: Mapped[list | None] = mapped_column(JSONB, default=list)
    source: Mapped[str] = mapped_column(String, nullable=False, default="yfinance")
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
