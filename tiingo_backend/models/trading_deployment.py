from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from db import Base


class TradingDeployment(Base):
    __tablename__ = "trading_deployments"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    model_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("ml_models.id", ondelete="RESTRICT"),
        nullable=False,
    )
    symbol: Mapped[str] = mapped_column(String, nullable=False)
    timeframe: Mapped[str] = mapped_column(String, nullable=False, default="1d")
    status: Mapped[str] = mapped_column(String, nullable=False, default="draft")
    trading_mode: Mapped[str] = mapped_column(String, nullable=False, default="paper")
    allocation_pct: Mapped[float] = mapped_column(Numeric(8, 4), nullable=False, default=100)
    hyperparams_snapshot: Mapped[dict] = mapped_column(JSONB, default=dict)
    last_evaluated_bar_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_signal: Mapped[str | None] = mapped_column(String)
    last_error: Mapped[str | None] = mapped_column(Text)
    last_blocked_reason: Mapped[str | None] = mapped_column(Text)
    last_probability: Mapped[float | None] = mapped_column(Numeric(8, 6))
    last_outcome: Mapped[str | None] = mapped_column(String)
    activated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
