"""SQLAlchemy ORM models for trading strategy cards."""
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, Double, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from db import Base


class TradingStrategy(Base):
    __tablename__ = "trading_strategies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    asset_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("assets.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # Monte Carlo thresholds (separate BUY / SELL)
    mc_buy_prob_positive: Mapped[Optional[float]] = mapped_column(Double, nullable=True)
    mc_sell_prob_positive: Mapped[Optional[float]] = mapped_column(Double, nullable=True)

    # AI Agent thresholds (separate BUY / SELL per score)
    ai_buy_conviction: Mapped[Optional[float]] = mapped_column(Double, nullable=True)
    ai_sell_conviction: Mapped[Optional[float]] = mapped_column(Double, nullable=True)
    ai_buy_sentiment: Mapped[Optional[float]] = mapped_column(Double, nullable=True)
    ai_sell_sentiment: Mapped[Optional[float]] = mapped_column(Double, nullable=True)
    ai_buy_macro: Mapped[Optional[float]] = mapped_column(Double, nullable=True)
    ai_sell_macro: Mapped[Optional[float]] = mapped_column(Double, nullable=True)

    # Signal combination mode: 'all' | 'majority' | 'any'
    combination_mode: Mapped[str] = mapped_column(String(20), nullable=False, default="all")

    # Algo strategies: trading timeframe
    algo_timeframe: Mapped[str] = mapped_column(String(10), nullable=False, default="1d")

    # Auto-trading lifecycle
    auto_trading_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    auto_trading_started: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # Position sizing
    max_amount_per_position: Mapped[Optional[float]] = mapped_column(Double, nullable=True)
    max_pct_of_capital: Mapped[Optional[float]] = mapped_column(Double, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class StrategyBacktest(Base):
    __tablename__ = "strategy_backtests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    strategy_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("trading_strategies.id", ondelete="CASCADE"), nullable=False
    )
    strategy_name: Mapped[str] = mapped_column(Text, nullable=False)
    params: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    timeframe: Mapped[str] = mapped_column(String(10), nullable=False, default="1d")
    added_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
