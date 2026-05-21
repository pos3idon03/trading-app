from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from db import Base


class Instrument(Base):
    __tablename__ = "instruments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    symbol: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    tiingo_ticker: Mapped[str | None] = mapped_column(String)
    name: Mapped[str | None] = mapped_column(String)
    asset_type: Mapped[str] = mapped_column(String, nullable=False, default="stock")
    exchange: Mapped[str | None] = mapped_column(String)
    currency: Mapped[str] = mapped_column(String, default="USD")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
