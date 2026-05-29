from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from dtos.execution_explainability_dto import ProbabilityExplainabilityDTO


class ExecutionStatusDTO(BaseModel):
    trading_mode: str
    alpaca_configured: bool
    alpaca_base_url: str
    kill_switch_enabled: bool
    paper_trading_only: bool
    trading_mode_paper: bool


class KillSwitchRequest(BaseModel):
    enabled: bool


class KillSwitchResponse(BaseModel):
    kill_switch_enabled: bool
    updated_at: datetime


class RiskConfigDTO(BaseModel):
    max_position_pct: float
    max_exposure_pct: float
    daily_loss_limit_pct: float
    max_orders_per_minute: int
    deployment_max_drawdown_pct: float
    stale_data_max_missed_slots: int
    stale_data_block_orders: bool


class CreateDeploymentRequest(BaseModel):
    model_id: UUID
    allocation_pct: float = Field(default=100.0, ge=0.01, le=100.0)


class TradingDeploymentDTO(BaseModel):
    id: UUID
    model_id: UUID
    symbol: str
    timeframe: str
    status: str
    trading_mode: str
    allocation_pct: float
    hyperparams_snapshot: dict
    model_name: str | None = None
    model_type: str | None = None
    feature_mode: str | None = None
    last_evaluated_bar_time: datetime | None = None
    last_signal: str | None = None
    last_error: str | None = None
    last_blocked_reason: str | None = None
    last_probability: float | None = None
    last_outcome: str | None = None
    position_qty: float = 0.0
    position_side: str = "flat"
    activated_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class TradingDeploymentsResponse(BaseModel):
    deployments: list[TradingDeploymentDTO]


class DeleteDeploymentRequest(BaseModel):
    close_positions: bool = False


class DeleteDeploymentResponse(BaseModel):
    deleted: bool
    close_positions: bool
    closed_qty: float = 0
    close_order_id: UUID | None = None


class EvaluateDeploymentResponse(BaseModel):
    deployment_id: UUID
    skipped: bool
    signal: str | None = None
    bar_time: str | None = None
    probability: float | None = None
    explainability: ProbabilityExplainabilityDTO | None = None
    warnings: list[str] = Field(default_factory=list)
    order: dict | None = None
    blocked_reason: str | None = None
    outcome: str | None = None
    error: str | None = None


class ExecutionActivityEventDTO(BaseModel):
    id: str
    deployment_id: str
    symbol: str
    model_id: str | None = None
    model_name: str | None = None
    model_type: str | None = None
    bar_time: str
    signal: str
    probability: float | None = None
    buy_threshold: float | None = None
    sell_threshold: float | None = None
    position_side: str | None = None
    order_intent_side: str | None = None
    order_qty: float | None = None
    outcome: str
    blocked_reason: str | None = None
    order_id: str | None = None
    warnings: list[str] = Field(default_factory=list)
    explainability: ProbabilityExplainabilityDTO | None = None
    created_at: str


class ExecutionEvaluationsResponse(BaseModel):
    evaluations: list[ExecutionActivityEventDTO]


class EvaluateAllResponse(BaseModel):
    evaluated: int
    results: list[dict]


class EnqueueJobResponse(BaseModel):
    job_id: str
    status: str


class DeploymentCycleEnqueueRequest(BaseModel):
    scheduled_at: datetime | None = None


class DeploymentRefreshResponse(BaseModel):
    deployment_id: UUID
    results: list[dict]


class ReconciliationResponse(BaseModel):
    as_of: str
    catch_up_runs: int
    results: list[dict]


class ExecutionOrderDTO(BaseModel):
    id: UUID
    deployment_id: UUID
    alpaca_order_id: str | None = None
    symbol: str
    side: str
    qty: float
    order_type: str
    status: str
    signal: str
    bar_time: datetime
    filled_avg_price: float | None = None
    submitted_at: datetime
    filled_at: datetime | None = None
    error_message: str | None = None
    model_name: str | None = None
    model_id: UUID | None = None


class ExecutionOrdersResponse(BaseModel):
    orders: list[ExecutionOrderDTO]


class AccountSnapshotDTO(BaseModel):
    equity: float
    cash: float
    buying_power: float
    portfolio_value: float
    status: str | None = None
    currency: str | None = None


class PositionSnapshotDTO(BaseModel):
    symbol: str | None = None
    qty: float
    side: str | None = None
    market_value: float
    avg_entry_price: float
    unrealized_pl: float
    current_price: float


class DeploymentPositionSnapshotDTO(BaseModel):
    deployment_id: UUID
    symbol: str
    model_name: str | None = None
    model_id: UUID | None = None
    qty: float
    side: str
    market_value: float
    current_price: float
    avg_entry_price: float = 0.0
    unrealized_pl: float = 0.0


class UntrackedPositionSnapshotDTO(BaseModel):
    symbol: str
    qty: float
    side: str | None = None
    market_value: float
    avg_entry_price: float
    unrealized_pl: float
    current_price: float


class PortfolioPeriodPnlDTO(BaseModel):
    amount: float
    pct: float | None = None


class PortfolioSummaryDTO(BaseModel):
    closed_pnl: PortfolioPeriodPnlDTO
    open_pnl: PortfolioPeriodPnlDTO
    qqq_return_pct: float | None = None
    voo_return_pct: float | None = None


class PortfolioPeriodDTO(BaseModel):
    start: datetime
    end: datetime


class PortfolioPositionRowDTO(BaseModel):
    symbol: str
    source: str
    deployment_id: UUID | None = None
    qty: float
    side: str
    market_value: float
    unrealized_pl: float
    period_pl: float = 0.0
    current_price: float = 0.0
    avg_entry_price: float = 0.0


class PortfolioResponse(BaseModel):
    account: AccountSnapshotDTO
    positions: list[PositionSnapshotDTO]
    deployment_positions: list[DeploymentPositionSnapshotDTO] = Field(default_factory=list)
    untracked_positions: list[UntrackedPositionSnapshotDTO] = Field(default_factory=list)
    position_rows: list[PortfolioPositionRowDTO] = Field(default_factory=list)
    summary: PortfolioSummaryDTO | None = None
    period: PortfolioPeriodDTO | None = None


class DeploymentOverviewDTO(BaseModel):
    id: UUID
    model_id: UUID
    symbol: str
    timeframe: str
    status: str
    model_name: str | None = None
    last_error: str | None = None
    last_signal: str | None = None
    last_probability: float | None = None
    buy_threshold: float | None = None
    sell_threshold: float | None = None
    last_explainability: ProbabilityExplainabilityDTO | None = None
    last_evaluated_bar_time: datetime | None = None
    current_price: float | None = None
    price_updated_at: datetime | None = None
    round_trip_count: int = 0
    open_position_count: int = 0
    order_count: int = 0
    open_order_count: int = 0
    strategy_profit: float = 0.0
    strategy_profit_pct: float | None = None
    position_qty: float = 0.0
    position_side: str = "flat"
    update_status: str = "unknown"
    expected_latest_bar_time: datetime | None = None
    ohlcv_latest_bar_time: datetime | None = None
    missed_slot_count: int = 0


class DeploymentOverviewResponse(BaseModel):
    deployments: list[DeploymentOverviewDTO]
