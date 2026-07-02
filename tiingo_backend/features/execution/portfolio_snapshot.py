from sqlalchemy.ext.asyncio import AsyncSession

from dal import execution_order_dal, trading_deployment_dal
from features.execution.alpaca_symbols import from_alpaca_symbol
from features.execution.deployment_metrics import compute_strategy_pnl
from features.execution.deployment_position import resolve_deployment_side


async def enrich_deployment_positions(session: AsyncSession, deployments: list[dict]) -> list[dict]:
    enriched: list[dict] = []
    for deployment in deployments:
        qty = await execution_order_dal.sum_filled_qty_by_deployment(session, deployment["id"])
        enriched.append(
            {
                **deployment,
                "position_qty": qty,
                "position_side": resolve_deployment_side(qty),
            }
        )
    return enriched


def compute_attributed_qty_by_symbol(deployments: list[dict]) -> dict[str, float]:
    totals: dict[str, float] = {}
    for deployment in deployments:
        qty = float(deployment.get("position_qty") or 0)
        if qty <= 0:
            continue
        symbol = deployment["symbol"].upper()
        totals[symbol] = totals.get(symbol, 0.0) + qty
    return totals


def _alpaca_position_tiingo_key(alpaca_symbol: str) -> str:
    return from_alpaca_symbol(alpaca_symbol)


def alpaca_qty_by_symbol(alpaca_positions: list[dict]) -> dict[str, float]:
    totals: dict[str, float] = {}
    for position in alpaca_positions:
        raw_symbol = position.get("symbol") or ""
        if not raw_symbol:
            continue
        key = _alpaca_position_tiingo_key(raw_symbol)
        totals[key] = max(float(position.get("qty") or 0), totals.get(key, 0.0))
    return totals


def alpaca_available_qty_by_symbol(alpaca_positions: list[dict]) -> dict[str, float]:
    totals: dict[str, float] = {}
    for position in alpaca_positions:
        raw_symbol = position.get("symbol") or ""
        if not raw_symbol:
            continue
        key = _alpaca_position_tiingo_key(raw_symbol)
        available = position.get("qty_available")
        qty = float(available if available is not None else position.get("qty") or 0)
        totals[key] = max(qty, totals.get(key, 0.0))
    return totals


def alpaca_price_by_tiingo_symbol(alpaca_positions: list[dict]) -> dict[str, float]:
    prices: dict[str, float] = {}
    for position in alpaca_positions:
        raw_symbol = position.get("symbol") or ""
        if not raw_symbol:
            continue
        key = _alpaca_position_tiingo_key(raw_symbol)
        prices[key] = float(position.get("current_price") or 0)
    return prices


def cap_deployment_quantities(
    deployments: list[dict],
    alpaca_qty_by_symbol_map: dict[str, float],
) -> list[dict]:
    raw_totals: dict[str, float] = {}
    for deployment in deployments:
        qty = float(deployment.get("position_qty") or 0)
        if qty <= 0:
            continue
        symbol = deployment["symbol"].upper()
        raw_totals[symbol] = raw_totals.get(symbol, 0.0) + qty

    capped: list[dict] = []
    for deployment in deployments:
        qty = float(deployment.get("position_qty") or 0)
        if qty <= 0:
            capped.append({**deployment, "position_qty": 0.0, "cap_scale": 1.0})
            continue
        symbol = deployment["symbol"].upper()
        alpaca_qty = alpaca_qty_by_symbol_map.get(symbol, 0.0)
        raw_total = raw_totals.get(symbol, 0.0)
        scale = (alpaca_qty / raw_total) if raw_total > alpaca_qty + 1e-8 and raw_total > 0 else 1.0
        capped.append({**deployment, "position_qty": qty * scale, "cap_scale": scale})
    return capped


async def compute_deployment_exposure(
    session: AsyncSession,
    *,
    price_by_symbol: dict[str, float],
) -> float:
    deployments = await enrich_deployment_positions(
        session,
        await trading_deployment_dal.list_deployments_enriched(session, limit=500),
    )
    exposure = 0.0
    for deployment in deployments:
        qty = float(deployment.get("position_qty") or 0)
        if qty <= 0:
            continue
        price = price_by_symbol.get(deployment["symbol"].upper(), 0.0)
        exposure += qty * price
    return exposure


async def build_deployment_position_rows(
    session: AsyncSession,
    deployments: list[dict],
    *,
    price_by_symbol: dict[str, float],
) -> list[dict]:
    rows: list[dict] = []
    for deployment in deployments:
        qty = float(deployment.get("position_qty") or 0)
        if qty <= 0:
            continue
        symbol = deployment["symbol"].upper()
        price = price_by_symbol.get(symbol, 0.0)
        orders = await execution_order_dal.list_orders_for_deployment(session, deployment["id"])
        pnl = compute_strategy_pnl(orders, price)
        avg_entry = pnl.avg_entry_price if pnl.position_qty > 1e-8 else 0.0
        unrealized = qty * (price - avg_entry) if avg_entry > 0 else pnl.unrealized_profit
        rows.append(
            {
                "deployment_id": deployment["id"],
                "symbol": symbol,
                "model_name": deployment.get("model_name"),
                "model_id": deployment.get("model_id"),
                "qty": qty,
                "side": deployment.get("position_side") or "long",
                "market_value": qty * price,
                "current_price": price,
                "avg_entry_price": avg_entry,
                "unrealized_pl": unrealized,
            }
        )
    return rows


def build_untracked_position_rows(
    alpaca_positions: list[dict],
    attributed_by_symbol: dict[str, float],
) -> list[dict]:
    rows: list[dict] = []
    for position in alpaca_positions:
        raw_symbol = position.get("symbol") or ""
        if not raw_symbol:
            continue
        symbol = _alpaca_position_tiingo_key(raw_symbol)
        alpaca_qty = max(float(position.get("qty") or 0), 0.0)
        attributed = attributed_by_symbol.get(symbol, 0.0)
        untracked_qty = alpaca_qty - attributed
        if untracked_qty <= 1e-8:
            continue
        current_price = float(position.get("current_price") or 0)
        ratio = untracked_qty / alpaca_qty if alpaca_qty > 0 else 1.0
        rows.append(
            {
                "symbol": symbol,
                "qty": untracked_qty,
                "side": position.get("side"),
                "market_value": float(position.get("market_value") or 0) * ratio,
                "avg_entry_price": float(position.get("avg_entry_price") or 0),
                "unrealized_pl": float(position.get("unrealized_pl") or 0) * ratio,
                "current_price": current_price,
            }
        )
    return rows


def _format_qty(qty: float) -> str:
    if abs(qty - round(qty)) < 1e-6:
        return str(int(round(qty)))
    return f"{qty:.4f}".rstrip("0").rstrip(".")


def _build_source_label(deployment_rows: list[dict], untracked_rows: list[dict]) -> str:
    parts: list[str] = []
    for row in deployment_rows:
        name = row.get("model_name") or "Deployment"
        parts.append(f"{name} ({_format_qty(float(row.get('qty') or 0))})")
    for row in untracked_rows:
        parts.append(f"Untracked ({_format_qty(float(row.get('qty') or 0))})")
    return " + ".join(parts)


def build_consolidated_position_rows(
    deployment_rows: list[dict],
    untracked_rows: list[dict],
    *,
    period_pl_by_key: dict[str, float] | None = None,
) -> list[dict]:
    period_pl_by_key = period_pl_by_key or {}
    by_symbol: dict[str, dict] = {}

    def _ensure_bucket(symbol: str) -> dict:
        if symbol not in by_symbol:
            by_symbol[symbol] = {
                "symbol": symbol,
                "deployment_slices": [],
                "untracked_slices": [],
                "qty": 0.0,
                "market_value": 0.0,
                "unrealized_pl": 0.0,
                "period_pl": 0.0,
                "current_price": 0.0,
                "avg_entry_basis": 0.0,
                "side": "long",
            }
        return by_symbol[symbol]

    for row in deployment_rows:
        symbol = row["symbol"].upper()
        bucket = _ensure_bucket(symbol)
        bucket["deployment_slices"].append(row)
        key = str(row["deployment_id"])
        qty = float(row.get("qty") or 0)
        bucket["qty"] += qty
        bucket["market_value"] += float(row.get("market_value") or 0)
        bucket["unrealized_pl"] += float(row.get("unrealized_pl") or 0)
        bucket["period_pl"] += period_pl_by_key.get(key, 0.0)
        bucket["current_price"] = float(row.get("current_price") or 0)
        avg_entry = float(row.get("avg_entry_price") or 0)
        if avg_entry > 0:
            bucket["avg_entry_basis"] += qty * avg_entry
        bucket["side"] = row.get("side") or "long"

    for index, row in enumerate(untracked_rows):
        symbol = row["symbol"].upper()
        bucket = _ensure_bucket(symbol)
        bucket["untracked_slices"].append(row)
        key = f"untracked:{row['symbol']}:{index}"
        qty = float(row.get("qty") or 0)
        bucket["qty"] += qty
        bucket["market_value"] += float(row.get("market_value") or 0)
        bucket["unrealized_pl"] += float(row.get("unrealized_pl") or 0)
        bucket["period_pl"] += period_pl_by_key.get(key, 0.0)
        bucket["current_price"] = float(row.get("current_price") or 0)
        avg_entry = float(row.get("avg_entry_price") or 0)
        if avg_entry > 0:
            bucket["avg_entry_basis"] += qty * avg_entry
        bucket["side"] = row.get("side") or bucket["side"]

    consolidated: list[dict] = []
    for symbol in sorted(by_symbol):
        bucket = by_symbol[symbol]
        qty = bucket["qty"]
        avg_entry = bucket["avg_entry_basis"] / qty if qty > 1e-8 else 0.0
        consolidated.append(
            {
                "symbol": symbol,
                "source": _build_source_label(
                    bucket["deployment_slices"],
                    bucket["untracked_slices"],
                ),
                "deployment_id": None,
                "qty": qty,
                "side": bucket["side"],
                "market_value": bucket["market_value"],
                "unrealized_pl": bucket["unrealized_pl"],
                "period_pl": bucket["period_pl"],
                "current_price": bucket["current_price"],
                "avg_entry_price": avg_entry,
            }
        )
    return consolidated


def build_unified_position_rows(
    deployment_rows: list[dict],
    untracked_rows: list[dict],
    *,
    period_pl_by_key: dict[str, float] | None = None,
) -> list[dict]:
    return build_consolidated_position_rows(
        deployment_rows,
        untracked_rows,
        period_pl_by_key=period_pl_by_key,
    )


async def build_portfolio_breakdown(
    session: AsyncSession,
    alpaca_positions: list[dict],
) -> tuple[list[dict], list[dict]]:
    price_by_symbol = {
        _alpaca_position_tiingo_key(row.get("symbol") or ""): float(row.get("current_price") or 0)
        for row in alpaca_positions
        if row.get("symbol")
    }
    alpaca_qty_map = alpaca_qty_by_symbol(alpaca_positions)
    raw_deployments = await enrich_deployment_positions(
        session,
        await trading_deployment_dal.list_deployments_enriched(session, limit=500),
    )
    deployments = cap_deployment_quantities(raw_deployments, alpaca_qty_map)
    attributed = compute_attributed_qty_by_symbol(deployments)
    deployment_rows = await build_deployment_position_rows(
        session,
        deployments,
        price_by_symbol=price_by_symbol,
    )
    untracked_rows = build_untracked_position_rows(alpaca_positions, attributed)
    return deployment_rows, untracked_rows
