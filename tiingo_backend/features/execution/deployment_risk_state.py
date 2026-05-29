from sqlalchemy.ext.asyncio import AsyncSession

from dal import execution_order_dal, trading_deployment_dal
from features.execution.deployment_metrics import compute_strategy_pnl


async def refresh_deployment_peak_profit(
    session: AsyncSession,
    deployment: dict,
    *,
    current_price: float,
) -> float | None:
    orders = await execution_order_dal.list_orders(
        session,
        deployment_id=deployment["id"],
    )
    pnl = compute_strategy_pnl(orders, current_price)
    current_pct = pnl.profit_pct
    if current_pct is None:
        return deployment.get("peak_strategy_profit_pct")

    peak = deployment.get("peak_strategy_profit_pct")
    new_peak = current_pct if peak is None else max(float(peak), current_pct)
    if peak is None or new_peak > float(peak):
        await trading_deployment_dal.update_peak_strategy_profit_pct(
            session,
            deployment["id"],
            new_peak,
        )
    return new_peak
