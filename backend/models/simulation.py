from datetime import datetime

from sqlalchemy import DateTime, Double, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from db import Base


class Simulation(Base):
    __tablename__ = "simulations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    asset_id: Mapped[int] = mapped_column(Integer, ForeignKey("assets.id", ondelete="CASCADE"), nullable=False)
    timeframe: Mapped[str] = mapped_column(String, nullable=False, default="1d")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    calibration_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    calibration_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    params: Mapped[dict] = mapped_column(JSONB, nullable=False)
    num_paths: Mapped[int] = mapped_column(Integer, nullable=False, default=1000)
    horizon_steps: Mapped[int] = mapped_column(Integer, nullable=False)
    dt: Mapped[float] = mapped_column(Double, nullable=False)
    s0: Mapped[float] = mapped_column(Double, nullable=False)
    result_summary: Mapped[dict | None] = mapped_column(JSONB)
    percentile_paths: Mapped[dict | None] = mapped_column(JSONB)
    duration_ms: Mapped[int | None] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String, nullable=False, default="pending")
    error_message: Mapped[str | None] = mapped_column(Text)
