from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator


VALID_TIMEFRAMES = {"1m", "5m", "15m", "30m", "1h", "4h", "1d", "1w"}


class OHLCVRecord(BaseModel):
    time: datetime
    asset_id: int
    timeframe: str
    open: float
    high: float
    low: float
    close: float
    volume: int = 0
    vwap: Optional[float] = None
    trade_count: Optional[int] = None
    source: str

    @field_validator("timeframe")
    @classmethod
    def validate_timeframe(cls, v: str) -> str:
        if v not in VALID_TIMEFRAMES:
            raise ValueError(f"Invalid timeframe '{v}'. Valid: {VALID_TIMEFRAMES}")
        return v

    @field_validator("high")
    @classmethod
    def high_gte_low(cls, v: float, info) -> float:
        if "low" in info.data and v < info.data["low"]:
            raise ValueError("high must be >= low")
        return v


class FundamentalRecord(BaseModel):
    time: datetime
    asset_id: Optional[int] = None
    metric_name: str
    value: float
    period: Optional[str] = None
    source: str
    raw_data: Optional[dict] = None


class AssetDTO(BaseModel):
    id: int
    symbol: str
    name: Optional[str] = None
    asset_type: str = "stock"
    exchange: Optional[str] = None
    currency: str = "USD"
    is_active: bool = True


class IngestRequest(BaseModel):
    symbols: list[str] = Field(..., min_length=1, description="List of ticker symbols")
    timeframes: list[str] = Field(default=["1d"], description="Timeframes to ingest")
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    provider: str = Field(default="polygon", description="Data provider: polygon|alpaca|yfinance|fmp")

    @field_validator("timeframes")
    @classmethod
    def validate_timeframes(cls, v: list[str]) -> list[str]:
        invalid = set(v) - VALID_TIMEFRAMES
        if invalid:
            raise ValueError(f"Invalid timeframes: {invalid}")
        return v


class IngestResponse(BaseModel):
    job_id: str
    status: str
    symbols: list[str]
    timeframes: list[str]
    message: str


class OHLCVQueryResponse(BaseModel):
    asset_id: int
    symbol: str
    timeframe: str
    records: list[OHLCVRecord]
    count: int


class AssetListResponse(BaseModel):
    assets: list[AssetDTO]
    count: int


class IngestionStatusResponse(BaseModel):
    status: str
    last_run: Optional[datetime] = None
    active_jobs: int
    scheduled_jobs: list[dict]


class TickerSearchResult(BaseModel):
    symbol: str
    name: str
    asset_type: str = "stock"
    exchange: Optional[str] = None


class TickerSearchResponse(BaseModel):
    results: list[TickerSearchResult]
    count: int
