from datetime import datetime

from sqlalchemy import DateTime, Double, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from db import Base


class McBacktestOptimizeJob(Base):
    __tablename__ = "mc_backtest_optimize_jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    asset_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("assets.id", ondelete="CASCADE"), nullable=False,
    )
    symbol: Mapped[str] = mapped_column(String, nullable=False)
    request: Mapped[dict] = mapped_column(JSONB, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False, default="pending")
    progress_pct: Mapped[float] = mapped_column(Double, nullable=False, default=0.0)
    progress_message: Mapped[str | None] = mapped_column(Text)
    completed_steps: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_steps: Mapped[int | None] = mapped_column(Integer)
    result: Mapped[dict | None] = mapped_column(JSONB)
    error_message: Mapped[str | None] = mapped_column(Text)
    duration_ms: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(),
    )
