import math
from dataclasses import asdict
from datetime import datetime, timezone

from features.backtesting.simulator import EquityPoint, SimulationResult, TradeRecord

TRADING_MINUTES_PER_DAY = 6.5 * 60


def compute_metrics(
    strategy: SimulationResult,
    benchmark: SimulationResult,
    initial_cash: float,
    decision_timeframe: str = "1d",
    *,
    asset_type: str = "equity",
) -> dict:
    strategy_curve = strategy.equity_curve
    if not strategy_curve:
        return _empty_metrics()

    total_return_pct = _total_return(initial_cash, strategy.final_equity)
    benchmark_return_pct = _total_return(initial_cash, benchmark.final_equity)
    years = _years_between(strategy_curve[0].date, strategy_curve[-1].date)
    annualization = bars_per_year(decision_timeframe, asset_type=asset_type)
    cagr_pct = _cagr(initial_cash, strategy.final_equity, years)
    max_drawdown_pct = _max_drawdown(strategy_curve)

    return {
        "total_return_pct": round(total_return_pct, 2),
        "benchmark_return_pct": round(benchmark_return_pct, 2),
        "alpha_pct": round(total_return_pct - benchmark_return_pct, 2),
        "cagr_pct": round(cagr_pct, 2),
        "max_drawdown_pct": round(max_drawdown_pct, 2),
        "sharpe_ratio": round(_sharpe(strategy_curve, annualization), 2),
        "sortino_ratio": round(_sortino(strategy_curve, annualization), 2),
        "profit_factor": _profit_factor(strategy.trades),
        "calmar_ratio": _calmar(cagr_pct, max_drawdown_pct),
        "win_rate_pct": round(_win_rate(strategy.trades), 2),
        "trade_count": len(strategy.trades),
        "final_equity": round(strategy.final_equity, 2),
        "initial_cash": round(initial_cash, 2),
    }


def bars_per_year(timeframe: str, *, asset_type: str = "equity") -> float:
    if timeframe == "1d":
        return 252.0 if asset_type != "crypto" else 365.0
    if timeframe == "1w":
        return 52.0
    if timeframe == "1mo":
        return 12.0

    minutes_map = {
        "1m": 1,
        "5m": 5,
        "15m": 15,
        "30m": 30,
        "1h": 60,
        "4h": 240,
    }
    bucket = minutes_map.get(timeframe)
    if bucket is None:
        return 252.0
    if asset_type == "crypto":
        return (24.0 * 365.0 * 60.0) / bucket
    bars_per_day = TRADING_MINUTES_PER_DAY / bucket
    return 252.0 * bars_per_day


def _empty_metrics() -> dict:
    return {
        "total_return_pct": None,
        "benchmark_return_pct": None,
        "alpha_pct": None,
        "cagr_pct": None,
        "max_drawdown_pct": None,
        "sharpe_ratio": None,
        "sortino_ratio": None,
        "profit_factor": None,
        "calmar_ratio": None,
        "win_rate_pct": None,
        "trade_count": 0,
        "final_equity": None,
        "initial_cash": None,
    }


def _total_return(initial_cash: float, final_equity: float) -> float:
    if initial_cash <= 0:
        return 0.0
    return ((final_equity - initial_cash) / initial_cash) * 100.0


def _parse_timestamp(value: str) -> datetime:
    if "T" in value:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    year, month, day = (int(part) for part in value.split("-"))
    return datetime(year, month, day, tzinfo=timezone.utc)


def _years_between(start: str, end: str) -> float:
    if "T" in start or "T" in end:
        delta = _parse_timestamp(end) - _parse_timestamp(start)
        return max(delta.total_seconds() / (365.25 * 24 * 3600), 1 / 365.25)

    start_year, start_month, start_day = (int(x) for x in start.split("-"))
    end_year, end_month, end_day = (int(x) for x in end.split("-"))
    start_ord = start_year * 365 + start_month * 30 + start_day
    end_ord = end_year * 365 + end_month * 30 + end_day
    days = max(end_ord - start_ord, 1)
    return days / 365.0


def _cagr(initial_cash: float, final_equity: float, years: float) -> float:
    if initial_cash <= 0 or final_equity <= 0 or years <= 0:
        return 0.0
    return (math.pow(final_equity / initial_cash, 1 / years) - 1) * 100.0


def _max_drawdown(curve: list[EquityPoint]) -> float:
    peak = curve[0].equity
    max_dd = 0.0
    for point in curve:
        peak = max(peak, point.equity)
        if peak > 0:
            dd = ((point.equity - peak) / peak) * 100.0
            max_dd = min(max_dd, dd)
    return abs(max_dd)


def _period_returns(curve: list[EquityPoint]) -> list[float]:
    returns: list[float] = []
    for i in range(1, len(curve)):
        prev = curve[i - 1].equity
        curr = curve[i].equity
        if prev > 0:
            returns.append((curr - prev) / prev)
    return returns


def _sharpe(curve: list[EquityPoint], annualization: float) -> float:
    returns = _period_returns(curve)
    if len(returns) < 2:
        return 0.0
    mean = sum(returns) / len(returns)
    variance = sum((r - mean) ** 2 for r in returns) / (len(returns) - 1)
    std = math.sqrt(variance)
    if std == 0:
        return 0.0
    return (mean / std) * math.sqrt(annualization)


def _sortino(curve: list[EquityPoint], annualization: float) -> float:
    returns = _period_returns(curve)
    if len(returns) < 2:
        return 0.0
    mean = sum(returns) / len(returns)
    downside = [min(r, 0.0) for r in returns]
    variance = sum(d ** 2 for d in downside) / (len(returns) - 1)
    downside_std = math.sqrt(variance)
    if downside_std == 0:
        return 0.0
    return (mean / downside_std) * math.sqrt(annualization)


def _profit_factor(trades: list[TradeRecord]) -> float | None:
    gross_profit = sum(trade.pnl for trade in trades if trade.pnl > 0)
    gross_loss = abs(sum(trade.pnl for trade in trades if trade.pnl < 0))
    if gross_loss == 0:
        if gross_profit == 0:
            return None
        return 999.0
    return round(gross_profit / gross_loss, 2)


def _calmar(cagr_pct: float, max_drawdown_pct: float) -> float | None:
    if max_drawdown_pct <= 0:
        return None
    return round(cagr_pct / max_drawdown_pct, 2)


def _win_rate(trades: list[TradeRecord]) -> float:
    if not trades:
        return 0.0
    wins = sum(1 for trade in trades if trade.pnl > 0)
    return (wins / len(trades)) * 100.0


def serialize_trades(trades: list[TradeRecord]) -> list[dict]:
    return [asdict(trade) for trade in trades]
