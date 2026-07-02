from datetime import date, datetime
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
    div_cash: float = 0
    split_factor: float = 1
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
    auto_ingest: bool = True


class InstrumentCreateResponse(InstrumentDTO):
    job_id: Optional[UUID] = None


class AssetFullIngestRequest(BaseModel):
    symbol: str


class InstrumentPatchRequest(BaseModel):
    is_active: Optional[bool] = None
    asset_type: Optional[str] = None
    name: Optional[str] = None


class OHLCVBackfillRequest(BaseModel):
    symbols: list[str] = Field(default_factory=list)
    timeframes: list[str] = Field(default_factory=lambda: ["1d", "5m"])
    sources: list[str] = Field(default_factory=lambda: ["tiingo_eod", "tiingo_iex"])
    start_date: Optional[str] = None
    refresh_corporate_actions: bool = False


class NewsRunRequest(BaseModel):
    symbols: list[str] = Field(default_factory=list)
    limit: int = Field(default=50, ge=1, le=500)


class FundamentalsRunRequest(BaseModel):
    symbols: list[str] = Field(default_factory=list)


class FundamentalsCoverageItemDTO(BaseModel):
    symbol: str
    name: Optional[str] = None
    metric_count: int
    first_report_date: datetime
    latest_report_date: datetime
    last_ingested_at: datetime


class FundamentalsCoverageResponseDTO(BaseModel):
    items: list[FundamentalsCoverageItemDTO]
    count: int


class FundamentalMetricDTO(BaseModel):
    time: datetime
    metric_name: str
    value: float
    period: Optional[str] = None
    statement_type: Optional[str] = None


class FundamentalsMetricsResponseDTO(BaseModel):
    symbol: str
    period_type: str
    metrics: list[FundamentalMetricDTO]
    count: int


class MacroBackfillRequest(BaseModel):
    series_ids: list[str] = Field(default_factory=list)


class MacroSeriesDTO(BaseModel):
    series_id: str
    title: str
    frequency: Optional[str] = None
    category: str = "general"
    is_enabled: bool = False


class MacroObservationDTO(BaseModel):
    obs_date: date
    value: Optional[float] = None


class MacroObservationsResponseDTO(BaseModel):
    series_id: str
    observations: list[MacroObservationDTO]
    count: int


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
    div_cash: float = 0
    split_factor: float = 1
    source: str


class OHLCVQueryResponse(BaseModel):
    symbol: str
    instrument_id: int
    timeframe: str
    source: str
    records: list[OHLCVBarDTO]
    count: int


class PerformancePeriodDTO(BaseModel):
    period: str
    change_pct: Optional[float] = None
    price_change_pct: Optional[float] = None
    dividend_return_pct: Optional[float] = None
    total_return_pct: Optional[float] = None
    example_investment: float = 100
    example_outcome: Optional[float] = None
    example_dividend_income: Optional[float] = None


class PerformanceResponseDTO(BaseModel):
    symbol: str
    currency: str = "USD"
    as_of: Optional[datetime] = None
    periods: list[PerformancePeriodDTO]


class StockKpiItemDTO(BaseModel):
    key: str
    label: str
    value: Optional[float] = None
    format: str


class StockKpisResponseDTO(BaseModel):
    symbol: str
    as_of: Optional[datetime] = None
    price: Optional[float] = None
    kpis: list[StockKpiItemDTO]


class MetricGrowthDTO(BaseModel):
    latest_period: Optional[str] = None
    yoy: Optional[float] = None
    qoq: Optional[float] = None
    cagr: Optional[float] = None


class AssetOverviewRowDTO(BaseModel):
    symbol: str
    name: Optional[str] = None
    as_of: Optional[datetime] = None
    pe_ratio: Optional[float] = None
    dividend_yield: Optional[float] = None
    debt_equity: Optional[float] = None
    current_ratio: Optional[float] = None
    eps_ttm: Optional[float] = None
    revenue_growth: Optional[MetricGrowthDTO] = None
    ebitda_growth: Optional[MetricGrowthDTO] = None
    ocf_growth: Optional[MetricGrowthDTO] = None
    price_change_6m: Optional[float] = None
    performance: Optional[dict[str, Optional[float]]] = None


class AssetOverviewResponseDTO(BaseModel):
    asset_type: str
    as_of: Optional[datetime] = None
    rows: list[AssetOverviewRowDTO]


class MacroOverviewRowDTO(BaseModel):
    series_id: str
    title: str
    category: str
    frequency: Optional[str] = None
    change_1m: Optional[float] = None
    change_3m: Optional[float] = None
    change_6m: Optional[float] = None
    change_ytd: Optional[float] = None
    ma50_position: str = "—"
    ma200_position: str = "—"


class MacroOverviewResponseDTO(BaseModel):
    category: str
    as_of: Optional[date] = None
    rows: list[MacroOverviewRowDTO]


class MacroBriefResponseDTO(BaseModel):
    as_of: Optional[date] = None
    situation: Optional[str] = None
    outlook: Optional[str] = None
    situation_phase: Optional[str] = None
    outlook_phase: Optional[str] = None
    generated_at: Optional[datetime] = None
    available: bool
    message: Optional[str] = None


class MarketSentimentPointDTO(BaseModel):
    recorded_at: datetime
    score: float
    article_count: int
    bullish_count: int
    bearish_count: int
    neutral_count: int


class MarketSentimentResponseDTO(BaseModel):
    window_hours: int
    current_score: float
    current_article_count: int
    points: list[MarketSentimentPointDTO]
    available: bool
    message: Optional[str] = None
