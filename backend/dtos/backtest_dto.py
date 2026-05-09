from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, model_validator


VALID_STRATEGIES = {
    "ma_crossover",
    "mean_reversion",
    "breakout",
    "trend_pullback",
    "gap_fade",
    "vrp_harvest",
}

VALID_OPTIMIZE_METRICS = {"sharpe_ratio", "sortino_ratio", "total_return", "profit_factor"}


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


_STRATEGY_DESCRIPTIONS = (
    "ma_crossover | mean_reversion | breakout | trend_pullback | gap_fade | vrp_harvest"
)


class BacktestRequest(BaseModel):
    asset_id: Optional[int] = None
    symbol: Optional[str] = Field(default=None, description="Ticker symbol (alternative to asset_id)")
    strategy_name: str = Field(..., description=_STRATEGY_DESCRIPTIONS)
    timeframe: str = "1d"
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
    timeframe: str = "1d"
    start_date: datetime
    end_date: datetime
    param_grid: dict = Field(
        ..., description="Param name -> list of values to sweep, e.g. {fast_window: [5,10,20]}"
    )
    n_splits: int = Field(default=5, ge=2, le=20)
    optimize_metric: str = Field(default="sharpe_ratio")
    initial_capital: float = Field(default=100_000.0, ge=1000.0)

    @model_validator(mode="after")
    def require_asset_or_symbol(self) -> "OptimizationRequest":
        if self.asset_id is None and self.symbol is None:
            raise ValueError("Provide either asset_id or symbol")
        return self


class OptimizationSummary(BaseModel):
    params: dict
    avg_oos_metric: float


class OptimizationResponse(BaseModel):
    optimization_id: int
    asset_id: int
    strategy_name: str
    status: str
    optimize_metric: Optional[str] = None
    n_splits: Optional[int] = None
    best_params: Optional[dict] = None
    best_metric: Optional[float] = None
    all_results: Optional[list[OptimizationSummary]] = None
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


class BacktestMetrics(BaseModel):
    sharpe_ratio: Optional[float] = None
    sortino_ratio: Optional[float] = None
    max_drawdown: Optional[float] = None
    win_rate: Optional[float] = None
    profit_factor: Optional[float] = None
    total_return: Optional[float] = None
    annualized_return: Optional[float] = None
    num_trades: Optional[int] = None


class BacktestResponse(BaseModel):
    backtest_id: int
    asset_id: int
    strategy_name: str
    status: str
    metrics: Optional[BacktestMetrics] = None
    equity_curve: Optional[list[dict]] = None
    trade_log: Optional[list[TradeRecord]] = None
    duration_ms: Optional[int] = None
    error_message: Optional[str] = None
