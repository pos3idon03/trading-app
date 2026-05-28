from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from dtos.backtest_dto import (
    BacktestEquityPointDTO,
    BacktestMetricsDTO,
    BacktestTradeDTO,
)


class FoundationParamConstraintDTO(BaseModel):
    min: float
    max: float


class FoundationModelCatalogItemDTO(BaseModel):
    id: str
    label: str
    description: str
    params: dict[str, Any]
    constraints: dict[str, FoundationParamConstraintDTO] = Field(default_factory=dict)


class FoundationModelCatalogResponse(BaseModel):
    models: list[FoundationModelCatalogItemDTO]


class FoundationRunRequest(BaseModel):
    symbol: str
    model_type: str
    params: dict[str, Any] = Field(default_factory=dict)
    timeframe: str = "1d"
    start: Optional[datetime] = None
    end: Optional[datetime] = None
    initial_cash: float = Field(default=10_000.0, gt=0)
    commission_bps: float = Field(default=5.0, ge=0, le=1000)


class FoundationPreviewRequest(BaseModel):
    symbol: str
    model_type: str
    params: dict[str, Any] = Field(default_factory=dict)
    timeframe: str = "1d"
    start: Optional[datetime] = None
    end: Optional[datetime] = None


class FoundationJobAcceptedResponse(BaseModel):
    job_id: UUID


class FoundationForecastPointDTO(BaseModel):
    date: str
    actual: Optional[float] = None
    forecast: Optional[float] = None
    lower: Optional[float] = None
    upper: Optional[float] = None


class FoundationForecastMetricsDTO(BaseModel):
    mae: Optional[float] = None
    mape: Optional[float] = None
    directional_accuracy: Optional[float] = None
    evaluated_points: int = 0


class FoundationWalkForwardMetaDTO(BaseModel):
    context_length: int
    forecast_horizon: int
    signal_mode: str
    target_series: str
    bars_evaluated: int = 0
    warmup_bars: int = 0


class FoundationSummaryDTO(BaseModel):
    model_type: str
    signal_counts: dict[str, int] = Field(default_factory=dict)
    forecast_metrics: FoundationForecastMetricsDTO = Field(
        default_factory=FoundationForecastMetricsDTO,
    )
    walk_forward: FoundationWalkForwardMetaDTO
    simulation_start_bar_index: Optional[int] = None
    simulation_start_date: Optional[str] = None
    pre_oos_bars_excluded: Optional[int] = None
    forecast_samples: list[FoundationForecastPointDTO] = Field(default_factory=list)


class FoundationPreviewResponse(BaseModel):
    symbol: str
    model_type: str
    context_points: list[FoundationForecastPointDTO] = Field(default_factory=list)
    forecast_points: list[FoundationForecastPointDTO] = Field(default_factory=list)
    context_length: int
    forecast_horizon: int


class FoundationBacktestResultsResponse(BaseModel):
    id: UUID
    symbol: str
    model_type: str
    params: dict[str, Any]
    timeframe: str
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    initial_cash: float
    commission_bps: float
    status: str
    metrics: Optional[BacktestMetricsDTO] = None
    equity_curve: list[BacktestEquityPointDTO] = Field(default_factory=list)
    benchmark_equity_curve: list[BacktestEquityPointDTO] = Field(default_factory=list)
    trades: list[BacktestTradeDTO] = Field(default_factory=list)
    foundation_summary: Optional[FoundationSummaryDTO] = None
    error_message: Optional[str] = None
    created_at: datetime
    finished_at: Optional[datetime] = None
