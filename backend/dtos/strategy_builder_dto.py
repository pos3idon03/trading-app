"""DTOs for the Strategy Builder and Auto-Trading endpoints."""
from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Strategy Builder – creation / listing
# ---------------------------------------------------------------------------

class CreateStrategyRequest(BaseModel):
    asset_id: int = Field(..., description="ID of the asset to create a strategy card for")


class AttachAlgoRequest(BaseModel):
    asset_id: int = Field(..., description="Asset ID — strategy card is auto-created if absent")
    strategy_name: str = Field(..., description="Strategy name (e.g. 'ma_crossover' or 'combo:majority')")
    params: Optional[dict] = Field(default=None, description="Strategy parameters used in the backtest run")


class DetachAlgoRequest(BaseModel):
    strategy_id: int
    algo_attachment_id: int = Field(..., description="Primary key of the strategy_backtests row")


class StrategyRecord(BaseModel):
    id: int
    asset_id: int
    symbol: str
    asset_name: Optional[str] = None
    is_active: bool
    # Monte Carlo thresholds (BUY / SELL)
    mc_buy_prob_positive: Optional[float] = None
    mc_sell_prob_positive: Optional[float] = None
    # AI Agent thresholds (BUY / SELL per score)
    ai_buy_conviction: Optional[float] = None
    ai_sell_conviction: Optional[float] = None
    ai_buy_sentiment: Optional[float] = None
    ai_sell_sentiment: Optional[float] = None
    ai_buy_macro: Optional[float] = None
    ai_sell_macro: Optional[float] = None
    # Signal configuration
    combination_mode: str = "all"
    algo_timeframe: str = "1d"
    # Auto-trading lifecycle
    auto_trading_enabled: bool = False
    auto_trading_started: bool = False
    # Position sizing
    max_amount_per_position: Optional[float] = None
    max_pct_of_capital: Optional[float] = None
    created_at: datetime
    updated_at: datetime


# ---------------------------------------------------------------------------
# Threshold configuration – PATCH request
# ---------------------------------------------------------------------------

class UpdateThresholdsRequest(BaseModel):
    # Monte Carlo
    mc_buy_prob_positive: Optional[float] = Field(
        None, ge=0.0, le=1.0, description="BUY when Prob. Positive Return is above this value"
    )
    mc_sell_prob_positive: Optional[float] = Field(
        None, ge=0.0, le=1.0, description="SELL when Prob. Positive Return falls below this value"
    )
    # AI Agent conviction
    ai_buy_conviction: Optional[float] = Field(
        None, ge=-1.0, le=1.0, description="BUY when Conviction Score is above this value"
    )
    ai_sell_conviction: Optional[float] = Field(
        None, ge=-1.0, le=1.0, description="SELL when Conviction Score falls below this value"
    )
    # AI Agent sentiment
    ai_buy_sentiment: Optional[float] = Field(
        None, ge=-1.0, le=1.0, description="BUY when Sentiment Score is above this value"
    )
    ai_sell_sentiment: Optional[float] = Field(
        None, ge=-1.0, le=1.0, description="SELL when Sentiment Score falls below this value"
    )
    # AI Agent macro
    ai_buy_macro: Optional[float] = Field(
        None, ge=-1.0, le=1.0, description="BUY when Macro Score is above this value"
    )
    ai_sell_macro: Optional[float] = Field(
        None, ge=-1.0, le=1.0, description="SELL when Macro Score falls below this value"
    )
    combination_mode: Optional[Literal["all", "majority", "any"]] = Field(
        None, description="How section signals are combined"
    )
    algo_timeframe: Optional[Literal["1m", "5m", "15m", "30m", "1h", "3h", "1d", "1w"]] = Field(
        None, description="Timeframe for algo strategy signal evaluation"
    )
    auto_trading_enabled: Optional[bool] = Field(
        None, description="Enable/disable appearance on Auto-Trading dashboard"
    )


# ---------------------------------------------------------------------------
# Position sizing – PATCH request (used when starting auto-trading)
# ---------------------------------------------------------------------------

class UpdatePositionSizingRequest(BaseModel):
    max_amount_per_position: Optional[float] = Field(
        None, gt=0, description="Hard dollar cap per position (takes priority over pct)"
    )
    max_pct_of_capital: Optional[float] = Field(
        None, gt=0, le=100, description="Max % of available uninvested capital per position"
    )


# ---------------------------------------------------------------------------
# Auto-Trading dashboard – response row
# ---------------------------------------------------------------------------

class AutoTradingAssetRow(BaseModel):
    strategy_id: int
    asset_id: int
    symbol: str
    asset_name: Optional[str] = None
    asset_type: str = "stock"
    # Latest Monte Carlo value
    mc_prob_positive: Optional[float] = None
    # Configured MC thresholds
    mc_buy_prob_positive: Optional[float] = None
    mc_sell_prob_positive: Optional[float] = None
    # Latest AI Agent values
    ai_conviction: Optional[float] = None
    ai_sentiment: Optional[float] = None
    ai_macro: Optional[float] = None
    # Configured AI thresholds
    ai_buy_conviction: Optional[float] = None
    ai_sell_conviction: Optional[float] = None
    ai_buy_sentiment: Optional[float] = None
    ai_sell_sentiment: Optional[float] = None
    ai_buy_macro: Optional[float] = None
    ai_sell_macro: Optional[float] = None
    # Configuration
    combination_mode: str = "all"
    algo_timeframe: str = "1d"
    # State
    auto_trading_started: bool = False
    # Position sizing
    max_amount_per_position: Optional[float] = None
    max_pct_of_capital: Optional[float] = None


# ---------------------------------------------------------------------------
# Strategy full response (unchanged structure, kept for orchestrator)
# ---------------------------------------------------------------------------

class MonteCarloSummary(BaseModel):
    simulation_id: int
    prob_positive_return: float
    mean_max_drawdown: float
    p5: float
    p25: float
    p50: float
    p75: float
    p95: float
    mean_terminal: float
    std_terminal: float
    cached: bool = False


class AIAgentSummary(BaseModel):
    analysis_id: int
    bias: Optional[str] = None
    conviction_score: Optional[float] = None
    sentiment_score: Optional[float] = None
    macro_score: Optional[float] = None
    fundamental_summary: Optional[str] = None
    macro_summary: Optional[str] = None
    reasoning: Optional[str] = None
    key_risk: Optional[str] = None
    created_at: Optional[datetime] = None


class FinancialsSummary(BaseModel):
    revenue_growth: Optional[float] = None
    free_cash_flow: Optional[float] = None
    current_ratio: Optional[float] = None
    pe_ttm: Optional[float] = None
    pe_forward: Optional[float] = None
    pb_ratio: Optional[float] = None
    eps_ttm: Optional[float] = None
    eps_forward: Optional[float] = None
    market_cap: Optional[float] = None
    fetched_at: Optional[datetime] = None
    is_stale: bool = False


class AlgoStrategySummary(BaseModel):
    algo_attachment_id: int
    strategy_name: str
    params: Optional[dict] = None
    added_at: datetime


class StrategyFullResponse(BaseModel):
    strategy_id: int
    asset_id: int
    symbol: str
    asset_name: Optional[str] = None
    is_active: bool
    created_at: datetime
    # MC thresholds (BUY / SELL)
    mc_buy_prob_positive: Optional[float] = None
    mc_sell_prob_positive: Optional[float] = None
    # AI thresholds (BUY / SELL per score)
    ai_buy_conviction: Optional[float] = None
    ai_sell_conviction: Optional[float] = None
    ai_buy_sentiment: Optional[float] = None
    ai_sell_sentiment: Optional[float] = None
    ai_buy_macro: Optional[float] = None
    ai_sell_macro: Optional[float] = None
    # Configuration
    combination_mode: str = "all"
    algo_timeframe: str = "1d"
    auto_trading_enabled: bool = False
    auto_trading_started: bool = False
    max_amount_per_position: Optional[float] = None
    max_pct_of_capital: Optional[float] = None
    # Data sections
    monte_carlo: Optional[MonteCarloSummary] = None
    ai_agents: Optional[AIAgentSummary] = None
    financials: Optional[FinancialsSummary] = None
    algo_strategies: list[AlgoStrategySummary] = Field(default_factory=list)
    monte_carlo_error: Optional[str] = None
    ai_agents_error: Optional[str] = None
    financials_error: Optional[str] = None
