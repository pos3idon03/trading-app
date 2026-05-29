from datetime import date, datetime

from sqlalchemy import BigInteger, Boolean, Date, DateTime, Double, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from db import Base


class MacroSeries(Base):
    __tablename__ = "macro_series"

    series_id: Mapped[str] = mapped_column(String, primary_key=True)
    title: Mapped[str] = mapped_column(String)
    frequency: Mapped[str | None] = mapped_column(String)
    category: Mapped[str] = mapped_column(String, default="general")
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class MacroObservation(Base):
    __tablename__ = "macro_observations"

    series_id: Mapped[str] = mapped_column(String, primary_key=True)
    obs_date: Mapped[date] = mapped_column(Date, primary_key=True)
    value: Mapped[float | None] = mapped_column(Double)
    release_date: Mapped[date | None] = mapped_column(Date, nullable=True)


class MacroBrief(Base):
    __tablename__ = "macro_briefs"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    as_of: Mapped[date | None] = mapped_column(Date, nullable=True)
    situation: Mapped[str] = mapped_column(Text)
    outlook: Mapped[str] = mapped_column(Text)
    situation_phase: Mapped[str | None] = mapped_column(String, nullable=True)
    outlook_phase: Mapped[str | None] = mapped_column(String, nullable=True)
    data_fingerprint: Mapped[str] = mapped_column(String)
    model_name: Mapped[str] = mapped_column(String)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
