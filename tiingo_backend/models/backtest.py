from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from db import Base
from models.universe import UniverseDefinition  # noqa: F401 — register FK target table


class BacktestRun(Base):
    __tablename__ = "backtest_runs"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    instrument_id: Mapped[int] = mapped_column(Integer, ForeignKey("instruments.id", ondelete="CASCADE"))
    symbol: Mapped[str] = mapped_column(String)
    strategy: Mapped[str] = mapped_column(String)
    params: Mapped[dict] = mapped_column(JSONB, default=dict)
    timeframe: Mapped[str] = mapped_column(String, default="1d")
    start_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    end_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    initial_cash: Mapped[float] = mapped_column(Numeric(18, 2), default=10000)
    commission_bps: Mapped[float] = mapped_column(Numeric(10, 4), default=0)
    status: Mapped[str] = mapped_column(String, default="pending")
    metrics: Mapped[dict | None] = mapped_column(JSONB)
    equity_curve: Mapped[list | None] = mapped_column(JSONB)
    trades: Mapped[list | None] = mapped_column(JSONB)
    benchmark: Mapped[dict | None] = mapped_column(JSONB)
    universe_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("universe_definitions.id", ondelete="SET NULL"))
    symbol_list: Mapped[list | None] = mapped_column(JSONB)
    error_message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
