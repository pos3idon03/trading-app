from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator, model_validator

BacktestTimeframe = Literal["5m", "15m", "30m", "1h", "4h", "1d", "1w"]


VALID_STRATEGIES = {
    # Original
    "ma_crossover",
    "mean_reversion",
    "breakout",
    "trend_pullback",
    "gap_fade",
    "vrp_harvest",
    # MA / EMA
    "sma_cross",
    "ema_cross",
    "sma_break",
    # Momentum
    "macd",
    "rsi",
    "lrsi",
    "new_high_low",
    "momentum_rotation",
    "aroon",
    "stoch_rsi",
    # Volatility / price-level
    "atr_trailing_stop",
    "vwap_cross",
    "grid_trading",
    "wedge_compression",
    # Mean reversion
    "mean_reversion_trend",
    "mean_reversion_range",
    "reverting_market",
    # Breakout
    "range_breakout",
    "orb",
    # Seasonal
    "seasonal",
}

VALID_OPTIMIZE_METRICS = {"sharpe_ratio", "sortino_ratio", "total_return", "profit_factor"}

_STRATEGY_DESCRIPTIONS = " | ".join(sorted(VALID_STRATEGIES))


# ---------------------------------------------------------------------------
# Original strategy param models
# ---------------------------------------------------------------------------

class MACrossoverParams(BaseModel):
    fast_window: int = Field(default=10, ge=2, le=200)
    slow_window: int = Field(default=50, ge=5, le=500)


class MeanReversionParams(BaseModel):
    lookback: int = Field(default=20, ge=5, le=250)
    z_threshold: float = Field(default=2.0, ge=0.5, le=5.0)


class BreakoutParams(BaseModel):
    bb_window: int = Field(default=20, ge=5, le=200)
    bb_std: float = Field(default=2.0, ge=0.5, le=5.0)
    squeeze_lookback: int = Field(default=120, ge=20, le=500)
    donchian_window: int = Field(default=20, ge=5, le=200)


class TrendPullbackParams(BaseModel):
    adx_period: int = Field(default=14, ge=5, le=100)
    adx_threshold: float = Field(default=25.0, ge=10.0, le=60.0)
    stoch_period: int = Field(default=14, ge=5, le=100)
    stoch_smooth: int = Field(default=3, ge=1, le=20)
    oversold: float = Field(default=20.0, ge=5.0, le=40.0)
    overbought: float = Field(default=80.0, ge=60.0, le=95.0)


class GapFadeParams(BaseModel):
    gap_threshold: float = Field(default=0.03, ge=0.005, le=0.20)
    min_gap_fill_bars: int = Field(default=5, ge=1, le=50)


class VrpHarvestParams(BaseModel):
    rv_window: int = Field(default=20, ge=5, le=100)
    iv_proxy_window: int = Field(default=60, ge=20, le=252)
    z_entry: float = Field(default=-1.0, ge=-3.0, le=0.0)
    z_exit: float = Field(default=0.5, ge=0.0, le=3.0)


# ---------------------------------------------------------------------------
# New MA / EMA param models
# ---------------------------------------------------------------------------

class SMACrossParams(BaseModel):
    fast_window: int = Field(default=50, ge=2, le=300)
    slow_window: int = Field(default=200, ge=10, le=500)


class EMACrossParams(BaseModel):
    fast_span: int = Field(default=12, ge=2, le=200)
    slow_span: int = Field(default=26, ge=5, le=500)


class SMABreakParams(BaseModel):
    sma_window: int = Field(default=200, ge=5, le=500)


# ---------------------------------------------------------------------------
# New momentum param models
# ---------------------------------------------------------------------------

class MACDParams(BaseModel):
    fast: int = Field(default=12, ge=2, le=100)
    slow: int = Field(default=26, ge=5, le=200)
    signal: int = Field(default=9, ge=2, le=50)


class RSIParams(BaseModel):
    period: int = Field(default=14, ge=2, le=100)
    overbought: float = Field(default=70.0, ge=50.0, le=95.0)
    oversold: float = Field(default=30.0, ge=5.0, le=50.0)


class LRSIParams(BaseModel):
    gamma: float = Field(default=0.5, ge=0.1, le=0.9)
    overbought: float = Field(default=0.8, ge=0.5, le=0.99)
    oversold: float = Field(default=0.2, ge=0.01, le=0.5)


class NewHighLowParams(BaseModel):
    lookback: int = Field(default=252, ge=20, le=504)


class MomentumRotationParams(BaseModel):
    short_window: int = Field(default=20, ge=5, le=100)
    long_window: int = Field(default=60, ge=20, le=252)
    threshold: float = Field(default=0.0, ge=-0.5, le=0.5)


class AroonParams(BaseModel):
    period: int = Field(default=52, ge=5, le=252)
    threshold: float = Field(default=50.0, ge=0.0, le=100.0)


class StochRSIParams(BaseModel):
    rsi_period: int = Field(default=14, ge=2, le=100)
    stoch_period: int = Field(default=14, ge=2, le=100)
    smooth_k: int = Field(default=3, ge=1, le=20)
    smooth_d: int = Field(default=3, ge=1, le=20)
    overbought: float = Field(default=0.8, ge=0.5, le=0.99)
    oversold: float = Field(default=0.2, ge=0.01, le=0.5)


# ---------------------------------------------------------------------------
# New volatility / price-level param models
# ---------------------------------------------------------------------------

class ATRTrailingStopParams(BaseModel):
    atr_period: int = Field(default=14, ge=5, le=100)
    atr_multiplier: float = Field(default=3.0, ge=0.5, le=10.0)
    trend_ma: int = Field(default=50, ge=5, le=500)


class VWAPCrossParams(BaseModel):
    band_pct: float = Field(default=0.0, ge=0.0, le=0.10)


class GridTradingParams(BaseModel):
    grid_size: float = Field(default=0.02, ge=0.001, le=0.20)
    num_levels: int = Field(default=5, ge=1, le=20)


class WedgeCompressionParams(BaseModel):
    atr_period: int = Field(default=14, ge=5, le=100)
    compression_lookback: int = Field(default=20, ge=5, le=200)
    compression_ratio: float = Field(default=0.5, ge=0.0, le=2.0)


# ---------------------------------------------------------------------------
# New mean reversion param models
# ---------------------------------------------------------------------------

class MeanReversionTrendParams(BaseModel):
    ma_window: int = Field(default=50, ge=5, le=500)
    z_threshold: float = Field(default=1.5, ge=0.5, le=5.0)
    adx_period: int = Field(default=14, ge=5, le=100)
    adx_threshold: float = Field(default=25.0, ge=10.0, le=60.0)


class MeanReversionRangeParams(BaseModel):
    bb_window: int = Field(default=20, ge=5, le=200)
    bb_std: float = Field(default=2.0, ge=0.5, le=5.0)
    adx_period: int = Field(default=14, ge=5, le=100)
    adx_max: float = Field(default=20.0, ge=5.0, le=50.0)


class RevertingMarketParams(BaseModel):
    rsi_period: int = Field(default=14, ge=2, le=100)
    rsi_upper: float = Field(default=60.0, ge=50.0, le=90.0)
    rsi_lower: float = Field(default=40.0, ge=10.0, le=50.0)
    adx_period: int = Field(default=14, ge=5, le=100)
    adx_max: float = Field(default=20.0, ge=5.0, le=50.0)


# ---------------------------------------------------------------------------
# New breakout param models
# ---------------------------------------------------------------------------

class RangeBreakoutParams(BaseModel):
    lookback: int = Field(default=20, ge=5, le=252)


class ORBParams(BaseModel):
    opening_bars: int = Field(default=6, ge=1, le=120)


# ---------------------------------------------------------------------------
# New seasonal param model
# ---------------------------------------------------------------------------

class SeasonalParams(BaseModel):
    sell_month: int = Field(default=5, ge=1, le=12)
    buy_month: int = Field(default=11, ge=1, le=12)


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

class BacktestRequest(BaseModel):
    asset_id: Optional[int] = None
    symbol: Optional[str] = Field(default=None, description="Ticker symbol (alternative to asset_id)")
    strategy_name: str = Field(..., description=_STRATEGY_DESCRIPTIONS)
    timeframe: BacktestTimeframe = "1d"
    start_date: datetime
    end_date: datetime
    strategy_params: dict = Field(default_factory=dict)
    initial_capital: float = Field(default=100_000.0, ge=1000.0)
    simulation_id: Optional[int] = Field(
        default=None, description="Run on Monte Carlo simulated data instead of OHLCV"
    )

    @model_validator(mode="after")
    def require_asset_or_symbol(self) -> "BacktestRequest":
        if self.asset_id is None and self.symbol is None and self.simulation_id is None:
            raise ValueError("Provide either asset_id, symbol, or simulation_id")
        return self


class OptimizationRequest(BaseModel):
    asset_id: Optional[int] = None
    symbol: Optional[str] = Field(default=None, description="Ticker symbol (alternative to asset_id)")
    strategy_name: str = Field(..., description=_STRATEGY_DESCRIPTIONS)
    timeframe: BacktestTimeframe = "1d"
    start_date: datetime
    end_date: datetime
    param_grid: dict = Field(
        ..., description="Param name -> list of values to sweep, e.g. {fast_window: [5,10,20]}"
    )
    n_splits: int = Field(default=5, ge=2, le=20)
    optimize_metric: str = Field(default="sharpe_ratio")
    initial_capital: float = Field(default=100_000.0, ge=1000.0)
    max_drawdown_cap: Optional[float] = Field(
        default=None,
        description=(
            "Worst allowed average OOS max drawdown (negative decimal, e.g. -0.25). "
            "Only combos with avg OOS max_drawdown >= this value are eligible."
        ),
    )

    @field_validator("max_drawdown_cap")
    @classmethod
    def validate_max_drawdown_cap(cls, v: Optional[float]) -> Optional[float]:
        if v is not None and v > 0:
            raise ValueError("max_drawdown_cap must be <= 0 (e.g. -0.25 for 25% drawdown)")
        return v

    @model_validator(mode="after")
    def require_asset_or_symbol(self) -> "OptimizationRequest":
        if self.asset_id is None and self.symbol is None:
            raise ValueError("Provide either asset_id or symbol")
        return self


class BacktestMetrics(BaseModel):
    sharpe_ratio: Optional[float] = None
    sortino_ratio: Optional[float] = None
    max_drawdown: Optional[float] = None
    win_rate: Optional[float] = None
    profit_factor: Optional[float] = None
    total_return: Optional[float] = None
    annualized_return: Optional[float] = None
    num_trades: Optional[int] = None


class OptimizationSummary(BaseModel):
    params: dict
    avg_oos_metric: float
    avg_oos_max_drawdown: Optional[float] = None


class OptimizationResponse(BaseModel):
    optimization_id: Optional[int] = None
    asset_id: int
    strategy_name: str
    status: str
    optimize_metric: Optional[str] = None
    n_splits: Optional[int] = None
    best_params: Optional[dict] = None
    best_metric: Optional[float] = None
    best_avg_oos_max_drawdown: Optional[float] = None
    all_results: Optional[list[OptimizationSummary]] = None
    full_period_metrics: Optional[BacktestMetrics] = None
    duration_ms: Optional[int] = None
    error_message: Optional[str] = None


class TradeRecord(BaseModel):
    entry_time: datetime
    exit_time: Optional[datetime] = None
    direction: str
    entry_price: float
    exit_price: Optional[float] = None
    pnl: Optional[float] = None
    return_pct: Optional[float] = None


class BacktestResponse(BaseModel):
    backtest_id: Optional[int] = None
    asset_id: int
    strategy_name: str
    strategy_params: Optional[dict] = None
    status: str
    metrics: Optional[BacktestMetrics] = None
    equity_curve: Optional[list[dict]] = None
    trade_log: Optional[list[TradeRecord]] = None
    buy_hold_curve: Optional[list[dict]] = None
    indicator_series: Optional[list[dict]] = None
    duration_ms: Optional[int] = None
    error_message: Optional[str] = None
    monthly_breakdown: Optional[list["ComboMonthlyRow"]] = None


# ---------------------------------------------------------------------------
# Monthly breakdown DTOs (combo backtest only)
# ---------------------------------------------------------------------------

class StrategyMonthlyState(BaseModel):
    strategy_name: str
    position: Literal["Buy", "Neutral", "Sell"]
    indicators: dict[str, Optional[float]]


class ComboMonthlyRow(BaseModel):
    month: str
    combined_position: Literal["Buy", "Sell"]
    strategies: list[StrategyMonthlyState]


BacktestResponse.model_rebuild()


# ---------------------------------------------------------------------------
# Per-strategy combo signal DTOs
# ---------------------------------------------------------------------------

class SignalPoint(BaseModel):
    time: str
    signal: Literal["Buy", "Neutral", "Sell"]


class ComboStrategySignal(BaseModel):
    strategy_name: str
    trade_log: list[dict]
    indicator_series: list[dict]
    equity_curve: list[dict]
    buy_hold_curve: list[dict] = []
    signal_timeline: list[SignalPoint]


class ComboSignalsResponse(BaseModel):
    strategies: list[ComboStrategySignal]


# ---------------------------------------------------------------------------
# Chart overlay DTOs
# ---------------------------------------------------------------------------

class ChartOverlayRequest(BaseModel):
    asset_id: Optional[int] = None
    symbol: Optional[str] = Field(default=None, description="Ticker symbol (alternative to asset_id)")
    strategy_name: str = Field(..., description=_STRATEGY_DESCRIPTIONS)
    timeframe: BacktestTimeframe = "1d"
    start_date: datetime
    end_date: datetime
    strategy_params: dict = Field(default_factory=dict)

    @model_validator(mode="after")
    def require_asset_or_symbol(self) -> "ChartOverlayRequest":
        if self.asset_id is None and self.symbol is None:
            raise ValueError("Provide either asset_id or symbol")
        return self

    @field_validator("strategy_name")
    @classmethod
    def validate_strategy(cls, v: str) -> str:
        if v not in VALID_STRATEGIES:
            raise ValueError(f"Unknown strategy: {v!r}. Valid: {sorted(VALID_STRATEGIES)}")
        return v


class ChartOverlayResponse(BaseModel):
    strategy_name: str
    trade_log: list[dict]
    indicator_series: list[dict]
    duration_ms: int


# ---------------------------------------------------------------------------
# Combo backtest DTOs
# ---------------------------------------------------------------------------

CombinationMode = Literal["and", "majority", "weighted"]


class ComboStrategyEntry(BaseModel):
    strategy_name: str = Field(..., description=_STRATEGY_DESCRIPTIONS)
    strategy_params: dict = Field(default_factory=dict)
    weight: float = Field(default=1.0, ge=0.0, le=1.0)

    @field_validator("strategy_name")
    @classmethod
    def validate_strategy(cls, v: str) -> str:
        if v not in VALID_STRATEGIES:
            raise ValueError(f"Unknown strategy: {v!r}. Valid: {sorted(VALID_STRATEGIES)}")
        return v


class ComboBacktestRequest(BaseModel):
    asset_id: Optional[int] = None
    symbol: Optional[str] = Field(default=None, description="Ticker symbol (alternative to asset_id)")
    simulation_id: Optional[int] = Field(default=None, description="Run on Monte Carlo simulated data")
    strategies: list[ComboStrategyEntry] = Field(..., min_length=2)
    combination_mode: CombinationMode = Field(default="majority")
    threshold: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Signal fires when weighted sum exceeds this (weighted mode only)",
    )
    timeframe: BacktestTimeframe = "1d"
    start_date: datetime
    end_date: datetime
    initial_capital: float = Field(default=100_000.0, ge=1000.0)

    @model_validator(mode="after")
    def require_asset_or_symbol(self) -> "ComboBacktestRequest":
        if self.asset_id is None and self.symbol is None and self.simulation_id is None:
            raise ValueError("Provide either asset_id, symbol, or simulation_id")
        if self.combination_mode == "weighted":
            for entry in self.strategies:
                if entry.weight == 0.0:
                    raise ValueError(
                        f"Strategy '{entry.strategy_name}' has weight 0 in weighted mode"
                    )
        return self


# ---------------------------------------------------------------------------
# Combo matrix (heatmap) DTOs
# ---------------------------------------------------------------------------

ComboMatrixMetric = Literal["sharpe_ratio", "sortino_ratio", "total_return", "profit_factor"]


class ComboMatrixRequest(BaseModel):
    asset_id: Optional[int] = None
    symbol: Optional[str] = Field(default=None, description="Ticker symbol (alternative to asset_id)")
    strategies: list[str] = Field(..., min_length=2)
    combination_mode: CombinationMode = Field(default="majority")
    threshold: float = Field(default=0.5, ge=0.0, le=1.0)
    metric: ComboMatrixMetric = Field(default="sharpe_ratio")
    timeframe: BacktestTimeframe = "1d"
    start_date: datetime
    end_date: datetime
    initial_capital: float = Field(default=100_000.0, ge=1000.0)
    strategy_params: dict[str, dict] = Field(default_factory=dict)

    @field_validator("strategies")
    @classmethod
    def validate_strategies(cls, v: list[str]) -> list[str]:
        for name in v:
            if name not in VALID_STRATEGIES:
                raise ValueError(f"Unknown strategy: {name!r}. Valid: {sorted(VALID_STRATEGIES)}")
        if len(set(v)) != len(v):
            raise ValueError("Duplicate strategy names are not allowed")
        return v

    @model_validator(mode="after")
    def require_asset_or_symbol(self) -> "ComboMatrixRequest":
        if self.asset_id is None and self.symbol is None:
            raise ValueError("Provide either asset_id or symbol")
        return self


class ComboMatrixResponse(BaseModel):
    asset_id: int
    strategies: list[str]
    metric: str
    combination_mode: str
    values: list[list[Optional[float]]]
    duration_ms: int
