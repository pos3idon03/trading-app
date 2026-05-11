from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field, model_validator


class VasicekParams(BaseModel):
    k: float = Field(..., description="Mean reversion speed")
    theta: float = Field(..., description="Long-term mean level (θ_0)")
    sigma: float = Field(..., description="Volatility (diffusion coefficient)")
    mu: float = Field(default=0.0, description="Expected drift rate for dynamic theta: θ_t = θ_0 * exp(μ * t)")


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
