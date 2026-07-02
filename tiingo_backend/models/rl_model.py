from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from db import Base


class RlModel(Base):
    __tablename__ = "rl_models"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    model_type: Mapped[str] = mapped_column(String, default="rl_ddqn")
    symbol: Mapped[str | None] = mapped_column(String)
    timeframe: Mapped[str] = mapped_column(String, default="1d")
    hyperparams: Mapped[dict] = mapped_column(JSONB, default=dict)
    state_schema: Mapped[dict] = mapped_column(JSONB, default=dict)
    train_metrics: Mapped[dict | None] = mapped_column(JSONB)
    artifact_path: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
