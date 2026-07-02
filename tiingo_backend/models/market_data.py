from datetime import date, datetime

from sqlalchemy import BigInteger, Date, DateTime, Double, ForeignKey, Integer, String, Text
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
    title_fingerprint: Mapped[str | None] = mapped_column(Text)


class NewsSentiment(Base):
    __tablename__ = "news_sentiment"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    news_article_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("news_articles.id", ondelete="CASCADE"),
        nullable=False,
    )
    model_name: Mapped[str] = mapped_column(Text, nullable=False)
    model_version: Mapped[str] = mapped_column(Text, nullable=False)
    label: Mapped[str] = mapped_column(Text, nullable=False)
    score_positive: Mapped[float] = mapped_column(Double, nullable=False)
    score_negative: Mapped[float] = mapped_column(Double, nullable=False)
    score_neutral: Mapped[float] = mapped_column(Double, nullable=False)
    confidence: Mapped[float] = mapped_column(Double, nullable=False)
    text_hash: Mapped[str] = mapped_column(Text, nullable=False)
    scored_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default="now()",
    )
    error: Mapped[str | None] = mapped_column(Text)


class NewsSentimentDaily(Base):
    __tablename__ = "news_sentiment_daily"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(Text, nullable=False)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    model_name: Mapped[str] = mapped_column(Text, nullable=False)
    model_version: Mapped[str] = mapped_column(Text, nullable=False)
    article_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    avg_score: Mapped[float] = mapped_column(Double, nullable=False, default=0)
    bullish_pct: Mapped[float] = mapped_column(Double, nullable=False, default=0)
    bearish_pct: Mapped[float] = mapped_column(Double, nullable=False, default=0)


class MarketSentimentSnapshot(Base):
    __tablename__ = "market_sentiment_snapshots"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default="now()",
    )
    window_hours: Mapped[int] = mapped_column(Integer, nullable=False, default=24)
    score: Mapped[float] = mapped_column(Double, nullable=False)
    article_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    bullish_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    bearish_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    neutral_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class NewsSentimentEnrichment(Base):
    __tablename__ = "news_sentiment_enrichment"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    news_article_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("news_articles.id", ondelete="CASCADE"),
        nullable=False,
    )
    provider: Mapped[str] = mapped_column(Text, nullable=False, default="gemini")
    model_name: Mapped[str] = mapped_column(Text, nullable=False)
    model_version: Mapped[str] = mapped_column(Text, nullable=False)
    finbert_label: Mapped[str] = mapped_column(Text, nullable=False)
    refined_label: Mapped[str] = mapped_column(Text, nullable=False)
    refined_confidence: Mapped[float] = mapped_column(Double, nullable=False)
    score_positive: Mapped[float] = mapped_column(Double, nullable=False)
    score_negative: Mapped[float] = mapped_column(Double, nullable=False)
    score_neutral: Mapped[float] = mapped_column(Double, nullable=False)
    rationale: Mapped[str | None] = mapped_column(Text)
    citations: Mapped[list | None] = mapped_column(JSONB)
    search_queries: Mapped[list | None] = mapped_column(JSONB)
    raw_response: Mapped[dict | None] = mapped_column(JSONB)
    analyzed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default="now()",
    )
    error: Mapped[str | None] = mapped_column(Text)
