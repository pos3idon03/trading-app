from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from db import Base


class ExecutionEvaluation(Base):
    __tablename__ = "execution_evaluations"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    deployment_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("trading_deployments.id", ondelete="CASCADE"),
        nullable=False,
    )
    bar_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    signal: Mapped[str] = mapped_column(String, nullable=False)
    probability: Mapped[float | None] = mapped_column(Numeric(8, 6))
    buy_threshold: Mapped[float | None] = mapped_column(Numeric(8, 6))
    sell_threshold: Mapped[float | None] = mapped_column(Numeric(8, 6))
    position_side: Mapped[str | None] = mapped_column(String)
    order_intent_side: Mapped[str | None] = mapped_column(String)
    order_qty: Mapped[float | None] = mapped_column(Numeric(18, 6))
    outcome: Mapped[str] = mapped_column(String, nullable=False)
    blocked_reason: Mapped[str | None] = mapped_column(Text)
    order_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("execution_orders.id", ondelete="SET NULL"),
    )
    warnings: Mapped[list] = mapped_column(JSONB, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
