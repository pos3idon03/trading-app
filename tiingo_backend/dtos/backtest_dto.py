from datetime import date, datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class StrategyParamConstraintDTO(BaseModel):
    min: float
    max: float


class StrategyCatalogItemDTO(BaseModel):
    id: str
    label: str
    description: str
    params: dict[str, Any]
    constraints: dict[str, StrategyParamConstraintDTO] = Field(default_factory=dict)
    ensemble_eligible: bool = False


class StrategyCatalogResponse(BaseModel):
    strategies: list[StrategyCatalogItemDTO]


class BacktestRunRequest(BaseModel):
    symbol: str
    strategy: str
    params: dict[str, Any] = Field(default_factory=dict)
    timeframe: str = "1d"
    signal_timeframe: Optional[str] = None
    start: Optional[datetime] = None
    end: Optional[datetime] = None
    initial_cash: float = Field(default=10_000.0, gt=0)
    commission_bps: float = Field(default=0.0, ge=0, le=1000)


class BacktestMetricsDTO(BaseModel):
    total_return_pct: Optional[float] = None
    benchmark_return_pct: Optional[float] = None
    alpha_pct: Optional[float] = None
    cagr_pct: Optional[float] = None
    max_drawdown_pct: Optional[float] = None
    sharpe_ratio: Optional[float] = None
    sortino_ratio: Optional[float] = None
    profit_factor: Optional[float] = None
    calmar_ratio: Optional[float] = None
    win_rate_pct: Optional[float] = None
    trade_count: int = 0
    final_equity: Optional[float] = None
    initial_cash: Optional[float] = None


class BacktestEquityPointDTO(BaseModel):
    date: str
    equity: float
    cash: float
    shares: float
    drawdown_pct: float


class BacktestTradeDTO(BaseModel):
    entry_date: str
    exit_date: str
    entry_price: float
    exit_price: float
    shares: float
    pnl: float
    pnl_pct: float


class BacktestRunResponse(BaseModel):
    id: UUID
    symbol: str
    strategy: str
    status: str
    metrics: Optional[BacktestMetricsDTO] = None


class BacktestResultsResponse(BaseModel):
    id: UUID
    symbol: str
    strategy: str
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
    error_message: Optional[str] = None
    created_at: datetime
    finished_at: Optional[datetime] = None
