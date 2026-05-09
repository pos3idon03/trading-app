"""Portfolio tracker: syncs positions and account state from Alpaca."""
from __future__ import annotations

from features.execution.broker_client import AccountInfo, Position, get_account, get_positions
from features.execution.risk_manager import PortfolioState, get_risk_manager
from utils.logging import get_logger

logger = get_logger(__name__)


def sync_portfolio() -> PortfolioState:
    """Fetch live account + positions from Alpaca and update the risk manager."""
    account = get_account()
    positions = get_positions()

    state = _build_portfolio_state(account, positions)
    get_risk_manager().update_portfolio(state)
    logger.info(
        "portfolio_synced",
        equity=state.equity,
        positions=len(state.position_values),
        daily_pnl_pct=state.daily_pnl_pct,
    )
    return state


def _build_portfolio_state(
    account: AccountInfo | None, positions: list[Position],
) -> PortfolioState:
    if account is None:
        return PortfolioState(equity=0.0, cash=0.0, buying_power=0.0)

    position_values: dict[str, float] = {}
    total_exposure = 0.0

    for pos in positions:
        position_values[pos.symbol] = abs(pos.market_value)
        total_exposure += abs(pos.market_value)

    daily_pnl = _calculate_daily_pnl(positions)
    daily_pnl_pct = (daily_pnl / account.equity * 100) if account.equity > 0 else 0.0

    return PortfolioState(
        equity=account.equity,
        cash=account.cash,
        buying_power=account.buying_power,
        daily_pnl=daily_pnl,
        daily_pnl_pct=daily_pnl_pct,
        position_values=position_values,
        total_exposure=total_exposure,
    )


def _calculate_daily_pnl(positions: list[Position]) -> float:
    return sum(pos.unrealized_pnl for pos in positions)


def get_portfolio_summary() -> dict:
    """Get a serializable portfolio summary for API responses."""
    account = get_account()
    positions = get_positions()

    if account is None:
        return {"error": "Could not fetch account data"}

    position_list = [
        {
            "symbol": p.symbol,
            "qty": p.qty,
            "market_value": p.market_value,
            "avg_entry_price": p.avg_entry_price,
            "current_price": p.current_price,
            "unrealized_pnl": p.unrealized_pnl,
            "unrealized_pnl_pct": p.unrealized_pnl_pct,
        }
        for p in positions
    ]

    daily_pnl = _calculate_daily_pnl(positions)
    daily_pnl_pct = (daily_pnl / account.equity * 100) if account.equity > 0 else 0.0

    return {
        "equity": account.equity,
        "cash": account.cash,
        "buying_power": account.buying_power,
        "portfolio_value": account.portfolio_value,
        "daily_pnl": round(daily_pnl, 2),
        "daily_pnl_pct": round(daily_pnl_pct, 4),
        "total_positions": len(positions),
        "positions": position_list,
    }
