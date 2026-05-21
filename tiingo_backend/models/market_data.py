from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Double, Integer, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from db import Base


class OHLCV(Base):
    __tablename__ = "ohlcv"

    time: Mapped[datetime] = mapped_column(DateTime(timezone=True), primary_key=True)
    instrument_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    timeframe: Mapped[str] = mapped_column(String, primary_key=True)
    source: Mapped[str] = mapped_column(String, primary_key=True)
    open: Mapped[float] = mapped_column(Double)
    high: Mapped[float] = mapped_column(Double)
    low: Mapped[float] = mapped_column(Double)
    close: Mapped[float] = mapped_column(Double)
    volume: Mapped[int] = mapped_column(BigInteger, default=0)
    vwap: Mapped[float | None] = mapped_column(Double)
    trade_count: Mapped[int | None] = mapped_column(Integer)
    div_cash: Mapped[float] = mapped_column(Double, default=0)
    split_factor: Mapped[float] = mapped_column(Double, default=1)


class Fundamental(Base):
    __tablename__ = "fundamentals"

    time: Mapped[datetime] = mapped_column(DateTime(timezone=True), primary_key=True)
    instrument_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    metric_name: Mapped[str] = mapped_column(String, primary_key=True)
    source: Mapped[str] = mapped_column(String, primary_key=True)
    value: Mapped[float] = mapped_column(Double)
    period: Mapped[str | None] = mapped_column(String)
    statement_type: Mapped[str | None] = mapped_column(String)
    raw_data: Mapped[dict | None] = mapped_column(JSONB)
    stored_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default="now()",
    )


class NewsArticle(Base):
    __tablename__ = "news_articles"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    title: Mapped[str] = mapped_column(Text)
    url: Mapped[str] = mapped_column(Text, unique=True)
    description: Mapped[str | None] = mapped_column(Text)
    source: Mapped[str] = mapped_column(String, default="tiingo")
    tickers: Mapped[list] = mapped_column(ARRAY(String))
    tags: Mapped[list] = mapped_column(ARRAY(String))
    raw_data: Mapped[dict | None] = mapped_column(JSONB)
