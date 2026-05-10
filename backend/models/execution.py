"""SQLAlchemy models for execution, risk events, and portfolio snapshots."""
from datetime import datetime

from sqlalchemy import DateTime, Double, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from db import Base


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    asset_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("assets.id", ondelete="SET NULL"), nullable=True, index=True,
    )
    symbol: Mapped[str] = mapped_column(String, nullable=False)
    side: Mapped[str] = mapped_column(String, nullable=False)
    qty: Mapped[float] = mapped_column(Double, nullable=False)
    order_type: Mapped[str] = mapped_column(String, nullable=False, default="market")
    limit_price: Mapped[float | None] = mapped_column(Double)
    stop_price: Mapped[float | None] = mapped_column(Double)
    status: Mapped[str] = mapped_column(String, nullable=False, default="pending")
    alpaca_order_id: Mapped[str | None] = mapped_column(String)
    filled_price: Mapped[float | None] = mapped_column(Double)
    filled_qty: Mapped[float | None] = mapped_column(Double)
    filled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    signal_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("trading_signals.id"))
    error_message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class RiskEvent(Base):
    __tablename__ = "risk_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    asset_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("assets.id", ondelete="SET NULL"), nullable=True, index=True,
    )
    event_type: Mapped[str] = mapped_column(String, nullable=False)
    severity: Mapped[str] = mapped_column(String, nullable=False, default="warning")
    symbol: Mapped[str | None] = mapped_column(String)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    details: Mapped[dict | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class PortfolioSnapshot(Base):
    __tablename__ = "portfolio_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    equity: Mapped[float] = mapped_column(Double, nullable=False)
    cash: Mapped[float] = mapped_column(Double, nullable=False)
    buying_power: Mapped[float] = mapped_column(Double, nullable=False)
    daily_pnl: Mapped[float | None] = mapped_column(Double)
    daily_pnl_pct: Mapped[float | None] = mapped_column(Double)
    total_positions: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    positions: Mapped[dict | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
