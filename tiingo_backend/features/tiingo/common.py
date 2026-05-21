from datetime import datetime, timezone

_RESAMPLE_MAP = {
    "1m": "1min",
    "5m": "5min",
    "15m": "15min",
    "30m": "30min",
    "1h": "60min",
    "1d": "daily",
}

_REQUEST_TIMEOUT = 30.0


def parse_timestamp(raw: str) -> datetime:
    ts = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    return ts


def resample_freq(timeframe: str) -> str:
    if timeframe not in _RESAMPLE_MAP:
        raise ValueError(f"Unsupported timeframe: {timeframe}")
    return _RESAMPLE_MAP[timeframe]


_CRYPTO_QUOTES = ("USDT", "USDC", "BUSD", "USD", "EUR", "GBP", "JPY", "BTC", "ETH")


def normalize_crypto_symbol(symbol: str) -> str:
    raw = symbol.strip().upper()
    if "-" in raw:
        base, quote = raw.split("-", 1)
        return f"{base}-{quote}"
    for quote in sorted(_CRYPTO_QUOTES, key=len, reverse=True):
        if raw.endswith(quote) and len(raw) > len(quote):
            return f"{raw[: -len(quote)]}-{quote}"
    raise ValueError(f"Cannot parse crypto symbol: {symbol}")


def symbol_to_crypto_ticker(symbol: str) -> str:
    if "-" in symbol:
        base, quote = symbol.upper().split("-", 1)
        return f"{base}{quote}".lower()
    return symbol.strip().lower()


def get_token() -> str:
    from config import get_settings

    token = get_settings().tiingo_api_key
    if not token:
        raise RuntimeError("TIINGO_API_KEY is not configured")
    return token
