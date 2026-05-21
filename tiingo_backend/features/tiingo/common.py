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


def symbol_to_crypto_ticker(symbol: str) -> str:
    parts = symbol.upper().split("-", 1)
    if len(parts) != 2:
        raise ValueError(f"Crypto symbol must be BASE-QUOTE: {symbol}")
    return f"{parts[0]}{parts[1]}".lower()


def get_token() -> str:
    from config import get_settings

    token = get_settings().tiingo_api_key
    if not token:
        raise RuntimeError("TIINGO_API_KEY is not configured")
    return token
