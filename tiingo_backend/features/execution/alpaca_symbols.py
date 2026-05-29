"""Map Tiingo/watchlist symbols to Alpaca API symbols and back."""

from features.tiingo.common import normalize_crypto_symbol


def execution_asset_type(asset_type: str | None) -> str:
    if asset_type == "crypto":
        return "crypto"
    return "stock"


def to_alpaca_symbol(symbol: str, asset_type: str) -> str:
    normalized = symbol.strip().upper()
    if execution_asset_type(asset_type) != "crypto":
        return normalized
    if "/" in normalized:
        return normalized
    if "-" in normalized:
        base, quote = normalized.split("-", 1)
        return f"{base}/{quote}"
    return normalized


def from_alpaca_symbol(alpaca_symbol: str) -> str:
    raw = alpaca_symbol.strip().upper()
    if "/" in raw:
        base, quote = raw.split("/", 1)
        return f"{base}-{quote}"
    if "-" in raw:
        return raw
    try:
        return normalize_crypto_symbol(raw)
    except ValueError:
        return raw


def tiingo_symbol_key(symbol: str, asset_type: str) -> str:
    return from_alpaca_symbol(to_alpaca_symbol(symbol, asset_type))
