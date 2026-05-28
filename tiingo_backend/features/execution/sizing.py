def compute_buy_budget(
    *,
    buying_power: float,
    account_equity: float,
    allocation_pct: float,
    max_position_pct: float,
) -> float:
    allocation_budget = buying_power * (allocation_pct / 100.0)
    risk_budget = account_equity * (max_position_pct / 100.0)
    return min(allocation_budget, risk_budget)
