"""Pydantic schemas for execution, risk management, and portfolio."""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class OrderResponse(BaseModel):
    id: int
    symbol: str
    side: str
    qty: float
    order_type: str
    limit_price: Optional[float] = None
    stop_price: Optional[float] = None
    status: str
    alpaca_order_id: Optional[str] = None
    filled_price: Optional[float] = None
    filled_qty: Optional[float] = None
    filled_at: Optional[datetime] = None
    signal_id: Optional[int] = None
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class OrderHistoryResponse(BaseModel):
    orders: list[OrderResponse]
    total: int


class PositionDTO(BaseModel):
    symbol: str
    qty: float
    market_value: float
    avg_entry_price: float
    current_price: float
    unrealized_pnl: float
    unrealized_pnl_pct: float


class PortfolioResponse(BaseModel):
    equity: float
    cash: float
    buying_power: float
    daily_pnl: Optional[float] = None
    daily_pnl_pct: Optional[float] = None
    total_positions: int = 0
    positions: list[PositionDTO] = []
    updated_at: Optional[datetime] = None


class RiskConfigResponse(BaseModel):
    trading_mode: str
    max_position_pct: float
    max_exposure_pct: float
    daily_loss_limit_pct: float
    max_orders_per_minute: int
    kill_switch_active: bool


class RiskConfigUpdateRequest(BaseModel):
    max_position_pct: Optional[float] = Field(None, gt=0, le=100)
    max_exposure_pct: Optional[float] = Field(None, gt=0, le=100)
    daily_loss_limit_pct: Optional[float] = Field(None, gt=0, le=100)
    max_orders_per_minute: Optional[int] = Field(None, gt=0, le=1000)


class RiskEventResponse(BaseModel):
    id: int
    event_type: str
    severity: str
    symbol: Optional[str] = None
    description: str
    details: Optional[dict] = None
    created_at: datetime


class RiskEventHistoryResponse(BaseModel):
    events: list[RiskEventResponse]
    total: int


class ExecutionStatusResponse(BaseModel):
    trading_mode: str
    kill_switch_active: bool
    stream_connected: bool
    subscribed_symbols: list[str]
    recent_orders: int = 0
    portfolio: Optional[PortfolioResponse] = None
