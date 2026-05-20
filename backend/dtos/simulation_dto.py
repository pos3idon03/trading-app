from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, Field, field_validator, model_validator

from dtos.backtest_dto import (
    BacktestMetrics,
    BacktestTimeframe,
    ComboStrategyEntry,
    ComboStrategySignal,
    CombinationMode,
    SignalPoint,
)

McModelType = Literal["vasicek", "merton", "ou_deviation", "blended"]
ThresholdMode = Literal["static", "ml_dynamic", "suggested_percentile"]
RegimeMode = Literal["adx", "ml"]


class VasicekParams(BaseModel):
    k: float = Field(..., description="Mean reversion speed")
    theta: float = Field(..., description="Long-term mean level (θ_0)")
    sigma: float = Field(..., description="Volatility (diffusion coefficient)")
    mu: float = Field(default=0.0, description="Expected drift rate for dynamic theta: θ_t = θ_0 * exp(μ * t)")


class MertonParams(BaseModel):
    mu: float = Field(..., description="Annualized drift rate (mean log-return / dt)")
    sigma: float = Field(..., description="Annualized volatility (std log-return / sqrt(dt))")


class OuDeviationParams(BaseModel):
    kappa: float = Field(..., description="Mean reversion speed on log(S/MA)")
    theta: float = Field(..., description="Long-run mean of log deviation")
    sigma: float = Field(..., description="Volatility of log deviation")
    ma_window: int = Field(default=20, description="Rolling MA window for fair value")
    ma_level: float = Field(..., description="MA level at calibration end")
    x0: float = Field(..., description="Current log(S/MA) at calibration end")


class JumpCI(BaseModel):
    """95% confidence intervals for a single jump component's log-normal parameters."""
    mu_low: float
    mu_high: float
    sigma_low: float
    sigma_high: float


class JumpParams(BaseModel):
    lambda_up: float = Field(..., description="Poisson intensity for upward jumps")
    lambda_down: float = Field(..., description="Poisson intensity for downward jumps")
    mu_up: float = Field(..., description="Mean size of upward jumps (log-normal)")
    sigma_up: float = Field(..., description="Std dev of upward jumps")
    mu_down: float = Field(..., description="Mean size of downward jumps")
    sigma_down: float = Field(..., description="Std dev of downward jumps")
    ci_up: Optional[JumpCI] = Field(default=None, description="95% CI for upward jump parameters")
    ci_down: Optional[JumpCI] = Field(default=None, description="95% CI for downward jump parameters")


class CalibratedModelParams(BaseModel):
    vasicek: VasicekParams
    jumps: JumpParams
    calibration_start: datetime
    calibration_end: datetime
    num_observations: int
    last_price: float = Field(default=0.0, description="Last observed close price; used as s0 for simulation")
    merton: Optional[MertonParams] = Field(default=None, description="Merton GBM+Jump params; populated when model_type=merton")
    ou_deviation: Optional[OuDeviationParams] = Field(
        default=None, description="OU log-deviation params for mean-reversion model",
    )


class CalibrationRequest(BaseModel):
    timeframe: str = "1d"
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None


class CalibrationResponse(BaseModel):
    asset_id: int
    symbol: str
    params: CalibratedModelParams
    message: str


class SimulationRequest(BaseModel):
    asset_id: Optional[int] = None
    symbol: Optional[str] = Field(default=None, description="Ticker symbol (alternative to asset_id)")
    timeframe: str = "1d"
    num_paths: int = Field(default=1000, ge=100, le=50000)
    horizon_steps: int = Field(default=252, ge=1, le=2520, description="Number of time steps forward")
    use_stored_params: bool = Field(default=True, description="Use previously calibrated params")
    custom_params: Optional[CalibratedModelParams] = None
    include_distribution: bool = Field(default=False, description="Include return distribution data in response")
    calibration_years: int = Field(default=10, ge=1, le=20, description="Years of historical data for calibration")
    model_type: McModelType = Field(
        default="vasicek",
        description="Simulation model: vasicek, merton, ou_deviation, or blended",
    )
    ou_ma_window: int = Field(default=20, ge=5, le=200)
    adx_period: int = Field(default=14, ge=5, le=50)
    adx_trend_threshold: float = Field(default=25.0, ge=10.0, le=60.0)

    @model_validator(mode="after")
    def require_asset_or_symbol(self) -> "SimulationRequest":
        if self.asset_id is None and self.symbol is None:
            raise ValueError("Provide either asset_id or symbol")
        return self


class SimulationStats(BaseModel):
    mean_terminal: float
    std_terminal: float
    p5: float
    p25: float
    p50: float
    p75: float
    p95: float
    prob_positive_return: float
    mean_max_drawdown: float


class DistributionPoint(BaseModel):
    """A single (x, density) point for a density curve or histogram bar."""
    x: float
    density: float


class ReturnDistribution(BaseModel):
    """Decomposed return distribution: histogram + three density curves."""
    histogram: List[DistributionPoint]
    mr_density: List[DistributionPoint]
    jump_up_density: List[DistributionPoint]
    jump_down_density: List[DistributionPoint]


class SimulationResponse(BaseModel):
    simulation_id: int
    asset_id: int
    status: str
    params: dict
    stats: Optional[SimulationStats] = None
    percentile_paths: Optional[dict] = None
    duration_ms: Optional[int] = None
    return_distribution: Optional[ReturnDistribution] = None


class McBacktestSignalPoint(BaseModel):
    time: str
    prob_positive: Optional[float] = None
    effective_prob: Optional[float] = None
    prob_trend: Optional[float] = None
    prob_reversion: Optional[float] = None
    regime_weight: Optional[float] = None
    regime_w_trend_htf: Optional[float] = None
    buy_threshold_effective: Optional[float] = None
    sell_threshold_effective: Optional[float] = None
    signal: str


class McBacktestZoneStats(BaseModel):
    entry_zone_pct: float = 0.0
    exit_zone_pct: float = 0.0
    middle_zone_pct: float = 0.0
    bars_with_prob: int = 0
    prob_min: float = 0.0
    prob_p25: float = 0.0
    prob_median: float = 0.0
    prob_p75: float = 0.0
    prob_max: float = 0.0
    suggested_buy_threshold: Optional[float] = None
    suggested_sell_threshold: Optional[float] = None


class McBacktestExecutionEvent(BaseModel):
    time: str
    side: Literal["buy", "sell"]
    price: float
    equity: float


class McBacktestRequest(BaseModel):
    asset_id: Optional[int] = None
    symbol: Optional[str] = Field(default=None, description="Ticker symbol (alternative to asset_id)")
    timeframe: BacktestTimeframe = "1d"
    start_date: datetime
    end_date: datetime
    model_type: McModelType = "merton"
    calibration_years: int = Field(default=10, ge=1, le=20)
    calibration_days: Optional[int] = Field(
        default=None,
        ge=7,
        le=90,
        description="Calibration window in days for intraday timeframes (5m–4h). Ignored for 1d/1w.",
    )
    num_paths: int = Field(default=500, ge=100, le=5000)
    buy_threshold: float = Field(default=0.65, ge=0.0, le=1.0)
    sell_threshold: float = Field(default=0.40, ge=0.0, le=1.0)
    initial_capital: float = Field(default=1000.0, ge=100.0)
    prob_smoothing_bars: int = Field(default=0, ge=0, le=20)
    entry_confirmation_bars: int = Field(default=1, ge=1, le=10)
    min_hold_bars: int = Field(default=0, ge=0, le=50)
    cooldown_bars: int = Field(default=0, ge=0, le=50)
    ou_ma_window: int = Field(default=20, ge=5, le=200)
    adx_period: int = Field(default=14, ge=5, le=50)
    adx_trend_threshold: float = Field(default=25.0, ge=10.0, le=60.0)
    combo_enabled: bool = Field(
        default=False,
        description="Combine MC prob signal with classic algo strategies",
    )
    combination_mode: CombinationMode = Field(default="and")
    threshold: float = Field(default=0.5, ge=0.0, le=1.0)
    mc_leg_weight: float = Field(default=1.0, ge=0.0, le=1.0)
    algo_strategies: list[ComboStrategyEntry] = Field(default_factory=list)
    regime_timeframe: Optional[BacktestTimeframe] = Field(
        default=None,
        description="Higher timeframe for regime (e.g. 4h when executing on 15m)",
    )
    structure_timeframe: Optional[BacktestTimeframe] = Field(
        default=None,
        description="Optional mid timeframe for structure veto",
    )
    mtf_gate_enabled: bool = Field(
        default=True,
        description="Block entries when higher-TF regime disagrees with model type",
    )
    regime_min_trend_weight: float = Field(default=0.3, ge=0.0, le=1.0)
    structure_veto_enabled: bool = Field(default=False)
    structure_max_trend_weight: float = Field(default=0.7, ge=0.0, le=1.0)
    threshold_mode: ThresholdMode = Field(default="static")
    ml_threshold_model_path: Optional[str] = Field(
        default=None, description="Pickled threshold model (ml_dynamic mode)",
    )
    regime_mode: RegimeMode = Field(default="adx")
    ml_regime_model_path: Optional[str] = Field(
        default=None, description="Pickled regime model (regime_mode=ml)",
    )
    use_surrogate: bool = Field(default=False)
    ml_surrogate_model_path: Optional[str] = Field(default=None)
    surrogate_sample_pct: float = Field(default=0.05, ge=0.0, le=1.0)

    @model_validator(mode="after")
    def require_asset_or_symbol(self) -> "McBacktestRequest":
        if self.asset_id is None and self.symbol is None:
            raise ValueError("Provide either asset_id or symbol")
        return self

    @model_validator(mode="after")
    def validate_threshold_order(self) -> "McBacktestRequest":
        if self.sell_threshold >= self.buy_threshold:
            raise ValueError(
                "Thresholds must satisfy: sell_threshold < buy_threshold"
            )
        if self.start_date >= self.end_date:
            raise ValueError("start_date must be before end_date")
        return self

    @model_validator(mode="after")
    def validate_combo(self) -> "McBacktestRequest":
        if self.combo_enabled and len(self.algo_strategies) < 1:
            raise ValueError("combo_enabled requires at least one algo strategy")
        return self


class McBacktestResponse(BaseModel):
    asset_id: int
    symbol: str
    status: str
    metrics: Optional[BacktestMetrics] = None
    equity_curve: list[dict] = Field(default_factory=list)
    buy_hold_curve: list[dict] = Field(default_factory=list)
    trade_log: list[dict] = Field(default_factory=list)
    execution_log: list[McBacktestExecutionEvent] = Field(default_factory=list)
    signal_log: list[McBacktestSignalPoint] = Field(default_factory=list)
    zone_stats: Optional[McBacktestZoneStats] = None
    combo_signals: list[ComboStrategySignal] = Field(default_factory=list)
    combined_signal_timeline: list[SignalPoint] = Field(default_factory=list)
    bars_evaluated: int = 0
    duration_ms: int = 0
    error_message: Optional[str] = None


class McSimulationOptimizeRequest(BaseModel):
    asset_id: Optional[int] = None
    symbol: Optional[str] = Field(default=None, description="Ticker symbol (alternative to asset_id)")
    timeframe: str = "1d"
    start_date: datetime
    end_date: datetime
    model_type: McModelType = "merton"
    horizon_steps: int = Field(default=252, ge=1, le=2520)
    param_grid: dict = Field(
        ...,
        description="Param name -> list of values, e.g. {num_paths: [500, 1000], calibration_years: [5, 10]}",
    )
    n_splits: int = Field(default=5, ge=2, le=20)
    optimize_metric: str = Field(default="prob_positive_return")
    max_drawdown_cap: Optional[float] = Field(
        default=None,
        description="Worst allowed average OOS max drawdown (negative decimal, e.g. -0.25).",
    )

    @field_validator("max_drawdown_cap")
    @classmethod
    def validate_max_drawdown_cap(cls, v: Optional[float]) -> Optional[float]:
        if v is not None and v > 0:
            raise ValueError("max_drawdown_cap must be <= 0 (e.g. -0.25 for 25% drawdown)")
        return v

    @model_validator(mode="after")
    def require_asset_or_symbol(self) -> "McSimulationOptimizeRequest":
        if self.asset_id is None and self.symbol is None:
            raise ValueError("Provide either asset_id or symbol")
        return self

    @model_validator(mode="after")
    def validate_dates(self) -> "McSimulationOptimizeRequest":
        if self.start_date >= self.end_date:
            raise ValueError("start_date must be before end_date")
        return self


class McSimulationOptimizeSummary(BaseModel):
    params: dict
    avg_oos_metric: float
    avg_oos_max_drawdown: Optional[float] = None


class McSimulationOptimizeResponse(BaseModel):
    asset_id: int
    symbol: str
    status: str
    optimize_metric: str
    n_splits: int
    best_params: Optional[dict] = None
    best_metric: Optional[float] = None
    best_avg_oos_max_drawdown: Optional[float] = None
    all_results: Optional[List[McSimulationOptimizeSummary]] = None
    best_run_stats: Optional[SimulationStats] = None
    best_run_percentile_paths: Optional[dict] = None
    duration_ms: int = 0
    error_message: Optional[str] = None


class McBacktestOptimizeRequest(BaseModel):
    asset_id: Optional[int] = None
    symbol: Optional[str] = Field(default=None, description="Ticker symbol (alternative to asset_id)")
    timeframe: BacktestTimeframe = "1d"
    start_date: datetime
    end_date: datetime
    model_type: McModelType = "merton"
    param_grid: dict = Field(
        ...,
        description=(
            "Param grid: buy_threshold, sell_threshold (0–1 or 0–100), "
            "num_paths, calibration_years, calibration_days (intraday), "
            "prob_smoothing_bars, entry_confirmation_bars, min_hold_bars, cooldown_bars"
        ),
    )
    n_splits: int = Field(default=5, ge=2, le=20)
    optimize_metric: str = Field(default="sortino_ratio")
    initial_capital: float = Field(default=1000.0, ge=100.0)
    calibration_days: Optional[int] = Field(
        default=None,
        ge=7,
        le=90,
        description="Default calibration window (days) for intraday when not in param_grid.",
    )
    min_trades: int = Field(
        default=5,
        ge=0,
        le=100,
        description="Minimum average OOS closed trades per combo to be feasible.",
    )
    max_drawdown_cap: Optional[float] = Field(
        default=None,
        description="Worst allowed average OOS max drawdown (negative decimal, e.g. -0.25).",
    )

    @field_validator("max_drawdown_cap")
    @classmethod
    def validate_max_drawdown_cap_bt(cls, v: Optional[float]) -> Optional[float]:
        if v is not None and v > 0:
            raise ValueError("max_drawdown_cap must be <= 0 (e.g. -0.25 for 25% drawdown)")
        return v

    @model_validator(mode="after")
    def require_asset_or_symbol_bt(self) -> "McBacktestOptimizeRequest":
        if self.asset_id is None and self.symbol is None:
            raise ValueError("Provide either asset_id or symbol")
        return self

    @model_validator(mode="after")
    def validate_dates_bt(self) -> "McBacktestOptimizeRequest":
        if self.start_date >= self.end_date:
            raise ValueError("start_date must be before end_date")
        return self


class McBacktestOptimizeSummary(BaseModel):
    params: dict
    avg_oos_metric: float
    avg_oos_max_drawdown: Optional[float] = None
    avg_oos_trades: Optional[float] = None


class McBacktestOptimizeResponse(BaseModel):
    asset_id: int
    symbol: str
    status: str
    optimize_metric: str
    n_splits: int
    best_params: Optional[dict] = None
    best_metric: Optional[float] = None
    best_avg_oos_max_drawdown: Optional[float] = None
    all_results: Optional[List[McBacktestOptimizeSummary]] = None
    full_period_metrics: Optional[BacktestMetrics] = None
    holdout_metrics: Optional[BacktestMetrics] = None
    duration_ms: int = 0
    error_message: Optional[str] = None


class McBacktestOptimizeJobStartResponse(BaseModel):
    job_id: int
    status: str = "pending"


class McBacktestOptimizeJobStatusResponse(McBacktestOptimizeResponse):
    job_id: int
    progress_pct: float = 0.0
    progress_message: Optional[str] = None
    completed_steps: int = 0
    total_steps: Optional[int] = None
