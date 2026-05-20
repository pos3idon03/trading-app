"""Pure performance metric calculation functions."""
import math

import numpy as np
import pandas as pd


TRADING_DAYS = 252


def _safe_float(value: float, fallback: float = 0.0) -> float:
    """Return fallback if value is nan or infinite; otherwise return value as float."""
    try:
        v = float(value)
        return fallback if (math.isnan(v) or math.isinf(v)) else v
    except (TypeError, ValueError):
        return fallback


def calculate_sharpe(returns: pd.Series, rf: float = 0.0, periods_per_year: int = TRADING_DAYS) -> float:
    """Annualized Sharpe ratio."""
    excess = returns - rf / periods_per_year
    std = excess.std()
    if _safe_float(std) == 0.0:
        return 0.0
    return _safe_float((excess.mean() / std) * np.sqrt(periods_per_year))


def calculate_sortino(returns: pd.Series, rf: float = 0.0, periods_per_year: int = TRADING_DAYS) -> float:
    """Annualized Sortino ratio using downside deviation."""
    excess = returns - rf / periods_per_year
    downside = excess[excess < 0]
    downside_std = _safe_float(downside.std())
    if downside_std == 0.0:
        return 0.0
    return _safe_float((excess.mean() / downside_std) * np.sqrt(periods_per_year))


def calculate_max_drawdown(equity: pd.Series) -> float:
    """Maximum drawdown as a negative decimal (e.g. -0.25 = -25%)."""
    if equity.empty:
        return 0.0
    rolling_max = equity.cummax()
    drawdown = (equity - rolling_max) / rolling_max.replace(0, np.nan)
    return _safe_float(drawdown.min())


def calculate_win_rate(trades: list[dict]) -> float:
    """Win rate as fraction of profitable trades."""
    if not trades:
        return 0.0
    profitable = sum(1 for t in trades if t.get("pnl", 0) > 0)
    return profitable / len(trades)


def calculate_profit_factor(trades: list[dict]) -> float:
    """Ratio of gross profit to gross loss. Returns 0.0 when no trades or infinite."""
    gross_profit = sum(t["pnl"] for t in trades if t.get("pnl", 0) > 0)
    gross_loss = abs(sum(t["pnl"] for t in trades if t.get("pnl", 0) < 0))
    if gross_loss == 0:
        return 0.0
    return _safe_float(gross_profit / gross_loss)


def calculate_annualized_return(equity: pd.Series, periods_per_year: int = TRADING_DAYS) -> float:
    """Compound annualized growth rate."""
    if len(equity) < 2 or _safe_float(equity.iloc[0]) == 0.0:
        return 0.0
    total_return = (equity.iloc[-1] / equity.iloc[0]) - 1
    years = len(equity) / periods_per_year
    if years <= 0:
        return 0.0
    return _safe_float((1 + total_return) ** (1 / years) - 1)


def _safe_total_return(equity: pd.Series) -> float:
    """Total return as decimal, guarded against NaN/inf."""
    if len(equity) < 2 or _safe_float(equity.iloc[0]) == 0.0:
        return 0.0
    return _safe_float(equity.iloc[-1] / equity.iloc[0] - 1)


def compile_all_metrics(
    returns: pd.Series,
    equity: pd.Series,
    trades: list[dict],
    rf: float = 0.0,
    periods_per_year: int = TRADING_DAYS,
) -> dict:
    """Compute and return all performance metrics as a dict.

    All float values are sanitized — nan/inf are replaced with 0.0 so the
    result is always JSON-serializable.
    """
    return {
        "sharpe_ratio": calculate_sharpe(returns, rf, periods_per_year),
        "sortino_ratio": calculate_sortino(returns, rf, periods_per_year),
        "max_drawdown": calculate_max_drawdown(equity),
        "win_rate": calculate_win_rate(trades),
        "profit_factor": calculate_profit_factor(trades),
        "total_return": _safe_total_return(equity),
        "annualized_return": calculate_annualized_return(equity, periods_per_year),
        "num_trades": len(trades),
    }
