from datetime import datetime

from sqlalchemy import DateTime, Double, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from db import Base


class OptimizationRun(Base):
    __tablename__ = "optimization_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    asset_id: Mapped[int] = mapped_column(Integer, ForeignKey("assets.id", ondelete="CASCADE"), nullable=False)
    strategy_name: Mapped[str] = mapped_column(String, nullable=False)
    timeframe: Mapped[str] = mapped_column(String, nullable=False)
    start_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    param_grid: Mapped[dict] = mapped_column(JSONB, nullable=False)
    n_splits: Mapped[int] = mapped_column(Integer, nullable=False)
    optimize_metric: Mapped[str] = mapped_column(String, nullable=False)
    best_params: Mapped[dict | None] = mapped_column(JSONB)
    best_metric: Mapped[float | None] = mapped_column(Double)
    all_results: Mapped[dict | None] = mapped_column(JSONB)
    duration_ms: Mapped[int | None] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String, nullable=False, default="pending")
    error_message: Mapped[str | None] = mapped_column(Text)


class Simulation(Base):
    __tablename__ = "simulations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    asset_id: Mapped[int] = mapped_column(Integer, ForeignKey("assets.id", ondelete="CASCADE"), nullable=False)
    timeframe: Mapped[str] = mapped_column(String, nullable=False, default="1d")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    calibration_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    calibration_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    params: Mapped[dict] = mapped_column(JSONB, nullable=False)
    num_paths: Mapped[int] = mapped_column(Integer, nullable=False, default=1000)
    horizon_steps: Mapped[int] = mapped_column(Integer, nullable=False)
    dt: Mapped[float] = mapped_column(Double, nullable=False)
    s0: Mapped[float] = mapped_column(Double, nullable=False)
    result_summary: Mapped[dict | None] = mapped_column(JSONB)
    percentile_paths: Mapped[dict | None] = mapped_column(JSONB)
    duration_ms: Mapped[int | None] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String, nullable=False, default="pending")
    error_message: Mapped[str | None] = mapped_column(Text)


class BacktestResult(Base):
    __tablename__ = "backtest_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    asset_id: Mapped[int] = mapped_column(Integer, ForeignKey("assets.id", ondelete="CASCADE"), nullable=False)
    strategy_name: Mapped[str] = mapped_column(String, nullable=False)
    timeframe: Mapped[str] = mapped_column(String, nullable=False)
    start_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    params: Mapped[dict] = mapped_column(JSONB, nullable=False)
    sharpe_ratio: Mapped[float | None] = mapped_column(Double)
    sortino_ratio: Mapped[float | None] = mapped_column(Double)
    max_drawdown: Mapped[float | None] = mapped_column(Double)
    win_rate: Mapped[float | None] = mapped_column(Double)
    profit_factor: Mapped[float | None] = mapped_column(Double)
    total_return: Mapped[float | None] = mapped_column(Double)
    annualized_return: Mapped[float | None] = mapped_column(Double)
    num_trades: Mapped[int | None] = mapped_column(Integer)
    equity_curve: Mapped[dict | None] = mapped_column(JSONB)
    trade_log: Mapped[dict | None] = mapped_column(JSONB)
    duration_ms: Mapped[int | None] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String, nullable=False, default="pending")
    error_message: Mapped[str | None] = mapped_column(Text)
