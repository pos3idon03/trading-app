from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Integer, Numeric, SmallInteger
from sqlalchemy.orm import Mapped, mapped_column

from db import Base


class ExecutionSettings(Base):
    __tablename__ = "execution_settings"

    id: Mapped[int] = mapped_column(SmallInteger, primary_key=True, default=1)
    kill_switch_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    day_start_equity: Mapped[float | None] = mapped_column(Numeric(18, 2))
    day_start_date: Mapped[date | None] = mapped_column(Date)
    orders_this_minute: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    minute_window_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
