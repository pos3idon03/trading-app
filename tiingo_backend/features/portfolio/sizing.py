from features.execution.sizing import compute_buy_budget
from features.portfolio.hrp import weights_for_symbols
from features.portfolio.kelly import capped_kelly_budget, kelly_from_trade_pnls


def fixed_fraction_budget(
    *,
    buying_power: float,
    account_equity: float,
    allocation_pct: float,
    max_position_pct: float,
) -> float:
    return compute_buy_budget(
        buying_power=buying_power,
        account_equity=account_equity,
        allocation_pct=allocation_pct,
        max_position_pct=max_position_pct,
    )


def compute_target_weights(
    sizing_method: str,
    *,
    symbols: list[str],
    returns_matrix: list[list[float]] | None = None,
    equity: float = 0.0,
    trade_pnls: list[float] | None = None,
    allocation_pct: float = 100.0,
    max_position_pct: float = 100.0,
    kelly_cap: float = 0.25,
    linkage_method: str = "single",
) -> dict[str, float]:
    if sizing_method == "hrp":
        if not returns_matrix or not symbols:
            return {}
        return weights_for_symbols(
            returns_matrix,
            symbols,
            linkage_method=linkage_method,
        )

    if sizing_method == "kelly" and trade_pnls:
        wr, avg_w, avg_l = kelly_from_trade_pnls(trade_pnls)
        budget = capped_kelly_budget(
            equity,
            wr,
            avg_w,
            avg_l,
            kelly_cap=kelly_cap,
            max_position_pct=max_position_pct,
        )
        if not symbols:
            return {}
        per_symbol = budget / equity if equity > 0 else 0.0
        return {symbols[0]: min(per_symbol, max_position_pct / 100.0)}

    if sizing_method == "fixed_fraction" and symbols:
        w = min(allocation_pct, max_position_pct) / 100.0
        return {symbols[0]: w}

    return {}
