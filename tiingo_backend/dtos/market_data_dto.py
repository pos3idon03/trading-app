from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class OHLCVRecord(BaseModel):
    time: datetime
    instrument_id: int
    timeframe: str
    open: float
    high: float
    low: float
    close: float
    volume: int = 0
    vwap: Optional[float] = None
    trade_count: Optional[int] = None
    source: str


class InstrumentDTO(BaseModel):
    id: int
    symbol: str
    tiingo_ticker: Optional[str] = None
    name: Optional[str] = None
    asset_type: str = "stock"
    exchange: Optional[str] = None
    currency: str = "USD"
    is_active: bool = True
    metadata: Optional[dict[str, Any]] = None


class InstrumentCreateRequest(BaseModel):
    symbol: str
    asset_type: str = "stock"
    tiingo_ticker: Optional[str] = None
    name: Optional[str] = None
    exchange: Optional[str] = None


class InstrumentPatchRequest(BaseModel):
    is_active: Optional[bool] = None
    asset_type: Optional[str] = None
    name: Optional[str] = None


class OHLCVBackfillRequest(BaseModel):
    symbols: list[str] = Field(default_factory=list)
    timeframes: list[str] = Field(default_factory=lambda: ["1d", "5m"])
    sources: list[str] = Field(default_factory=lambda: ["tiingo_eod", "tiingo_iex"])
    start_date: Optional[str] = None


class NewsRunRequest(BaseModel):
    symbols: list[str] = Field(default_factory=list)
    limit: int = Field(default=50, ge=1, le=500)


class FundamentalsRunRequest(BaseModel):
    symbols: list[str] = Field(default_factory=list)


class MacroBackfillRequest(BaseModel):
    series_ids: list[str] = Field(default_factory=list)


class MacroSeriesDTO(BaseModel):
    series_id: str
    title: str
    frequency: Optional[str] = None
    category: str = "general"
    is_enabled: bool = False


class JobDTO(BaseModel):
    id: UUID
    job_type: str
    status: str
    progress: int
    params: Optional[dict[str, Any]] = None
    result: Optional[dict[str, Any]] = None
    error_message: Optional[str] = None
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    created_at: datetime


class IngestionStatusResponse(BaseModel):
    scheduler_jobs: list[dict[str, Any]]
    api_usage: dict[str, int]
    stream_status: dict[str, Any]
    instrument_count: int
    active_instrument_count: int


class StreamControlRequest(BaseModel):
    symbols: list[str] = Field(default_factory=list)


class TickerSearchResultDTO(BaseModel):
    symbol: str
    name: str
    asset_type: str = "stock"
    exchange: Optional[str] = None
    tiingo_ticker: Optional[str] = None


class TickerSearchResponseDTO(BaseModel):
    results: list[TickerSearchResultDTO]
    count: int


class OHLCVBarDTO(BaseModel):
    time: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int = 0
    source: str


class OHLCVQueryResponse(BaseModel):
    symbol: str
    instrument_id: int
    timeframe: str
    source: str
    records: list[OHLCVBarDTO]
    count: int
