import math

from features.execution.alpaca_symbols import (
    execution_asset_type,
    from_alpaca_symbol,
    tiingo_symbol_key,
)

CRYPTO_QTY_DECIMALS = 9
BUY_QTY_DECIMALS = 2
STOCK_QTY_DECIMALS = 6
_MIN_CRYPTO_SELL_QTY = 10 ** -CRYPTO_QTY_DECIMALS
_MIN_STOCK_SELL_QTY = 10 ** -STOCK_QTY_DECIMALS


def floor_crypto_sell_qty(qty: float) -> float:
    if qty <= 0:
        return 0.0
    factor = 10**CRYPTO_QTY_DECIMALS
    return math.floor(qty * factor) / factor


def floor_stock_sell_qty(qty: float) -> float:
    if qty <= 0:
        return 0.0
    return round(qty, STOCK_QTY_DECIMALS)


def format_order_qty_string(qty: float, *, asset_type: str, side: str) -> str:
    if execution_asset_type(asset_type) == "crypto":
        if side.lower() == "sell":
            qty = floor_crypto_sell_qty(qty)
            return f"{qty:.{CRYPTO_QTY_DECIMALS}f}".rstrip("0").rstrip(".")
        qty = round(qty, BUY_QTY_DECIMALS)
        return f"{qty:.{BUY_QTY_DECIMALS}f}".rstrip("0").rstrip(".")
    return str(floor_stock_sell_qty(qty))


def resolve_sell_qty(
    deployment_net_qty: float,
    *,
    asset_type: str = "stock",
    position_qty: float | None = None,
    qty_available: float | None = None,
) -> float:
    if deployment_net_qty <= 0:
        return 0.0

    caps = [deployment_net_qty]
    if position_qty is not None and position_qty > 0:
        caps.append(position_qty)
    if qty_available is not None and qty_available > 0:
        caps.append(qty_available)

    raw = min(caps)
    if execution_asset_type(asset_type) == "crypto":
        floored = floor_crypto_sell_qty(raw)
        if floored < _MIN_CRYPTO_SELL_QTY:
            return 0.0
        return floored

    floored = floor_stock_sell_qty(raw)
    if floored < _MIN_STOCK_SELL_QTY:
        return 0.0
    return floored


def alpaca_position_for_symbol(
    alpaca_positions: list[dict],
    symbol: str,
    asset_type: str,
) -> dict | None:
    key = tiingo_symbol_key(symbol, asset_type).upper()
    for position in alpaca_positions:
        raw = (position.get("symbol") or "").strip()
        if not raw:
            continue
        pos_key = tiingo_symbol_key(from_alpaca_symbol(raw), asset_type).upper()
        if pos_key == key:
            return position
    return None
