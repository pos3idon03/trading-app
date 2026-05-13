"""Pydantic schemas for live trading indicators and signals."""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class StreamStartRequest(BaseModel):
    symbols: list[str] = Field(..., min_length=1, description="Symbols to stream")
    timeframes: list[str] = Field(
        default=["30m", "1h", "4h", "1d"],
        description="Timeframes to resample into",
    )


class StreamStatusResponse(BaseModel):
    connected: bool
    subscribed_symbols: list[str]
    last_tick_at: Optional[datetime] = None
    error: Optional[str] = None
    reconnect_count: int = 0


class IndicatorSnapshotResponse(BaseModel):
    asset_id: Optional[int] = None
    symbol: str
    timeframe: str
    close_price: float
    rsi: Optional[float] = None
    macd: Optional[float] = None
    macd_signal: Optional[float] = None
    macd_histogram: Optional[float] = None
    bb_upper: Optional[float] = None
    bb_middle: Optional[float] = None
    bb_lower: Optional[float] = None
    vwap: Optional[float] = None
    bb_percent: Optional[float] = None
    created_at: Optional[datetime] = None


class TradingSignalResponse(BaseModel):
    id: int
    asset_id: Optional[int] = None
    symbol: str
    timeframe: str
    action: str
    confidence: float
    technical_score: float
    risk_score: float
    ai_score: float
    reasoning: Optional[str] = None
    indicator_snapshot: Optional[dict] = None
    risk_data: Optional[dict] = None
    ai_signal: Optional[dict] = None
    created_at: datetime


class SignalHistoryResponse(BaseModel):
    signals: list[TradingSignalResponse]
    total: int


class LiveDataUpdate(BaseModel):
    """WebSocket message pushed to the frontend."""
    event_type: str  # "tick", "bar", "indicator", "signal"
    symbol: str
    data: dict
    timestamp: datetime


class StrategySignalItem(BaseModel):
    strategy: str
    label: str
    group: str
    signal: str  # BUY | SELL | NEUTRAL


class StrategySignalsResponse(BaseModel):
    symbol: str
    timeframe: str
    bar_count: int
    strategies: list[StrategySignalItem]
