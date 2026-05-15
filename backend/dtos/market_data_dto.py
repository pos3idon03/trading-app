import math
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

    @field_validator("open", "high", "low", "close", mode="before")
    @classmethod
    def reject_non_finite_prices(cls, v: float) -> float:
        if v is not None and (math.isnan(v) or math.isinf(v)):
            raise ValueError(f"Price field contains non-finite value: {v}")
        return v

    @field_validator("vwap", mode="before")
    @classmethod
    def coerce_nan_vwap(cls, v: Optional[float]) -> Optional[float]:
        if v is None:
            return None
        try:
            return None if (math.isnan(v) or math.isinf(v)) else v
        except (TypeError, ValueError):
            return None

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
    provider: str = Field(default="yfinance", description="Data provider: yfinance|polygon|alpaca|fmp")

    @field_validator("symbols")
    @classmethod
    def uppercase_symbols(cls, v: list[str]) -> list[str]:
        return [s.strip().upper() for s in v]

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


class AssetWithPriceDTO(BaseModel):
    id: int
    symbol: str
    name: Optional[str] = None
    asset_type: str = "stock"
    exchange: Optional[str] = None
    currency: str = "USD"
    is_active: bool = True
    latest_close: Optional[float] = None
    latest_update: Optional[datetime] = None


class AssetWithPriceListResponse(BaseModel):
    assets: list[AssetWithPriceDTO]
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


# ── Financials ────────────────────────────────────────────────────────────────

class FundamentalsOverviewResponse(BaseModel):
    symbol: str
    asset_id: int
    metrics: dict[str, float]
    fetched_at: Optional[datetime] = None


class FinancialStatementRow(BaseModel):
    metric: str
    values: dict[str, float]


class FinancialStatementResponse(BaseModel):
    symbol: str
    asset_id: int
    statement_type: str
    periods: list[str]
    rows: list[FinancialStatementRow]


class CompanyProfileResponse(BaseModel):
    symbol: str
    asset_id: int
    sector: Optional[str] = None
    industry: Optional[str] = None
    business_summary: Optional[str] = None
    website: Optional[str] = None
    country: Optional[str] = None
    employees: Optional[int] = None
    officers: Optional[list[dict]] = None
    fetched_at: Optional[datetime] = None


class FinancialsIngestResponse(BaseModel):
    symbol: str
    fundamentals_inserted: int
    profile_updated: bool
    status: str


class DeleteAssetResponse(BaseModel):
    symbol: str
    deleted: bool
    message: str
