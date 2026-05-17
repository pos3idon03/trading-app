"""Translate yfinance ticker symbols to Alpaca-compatible broker symbols.

yfinance and Alpaca use different ticker conventions:
  - Crypto:          BTC-USD  → BTC/USD
  - Non-US equities: BARC.L   → None (unsupported by Alpaca)
  - US equities/ETF: AAPL     → AAPL (unchanged)
  - Forex/index/etc:           → None (not tradeable on Alpaca equities API)

Returns None when a symbol cannot be traded on Alpaca, allowing callers to
skip order submission gracefully.
"""
from __future__ import annotations

import re

from utils.logging import get_logger

logger = get_logger(__name__)

# Asset types that are never tradeable on Alpaca
_UNSUPPORTED_ASSET_TYPES = frozenset({"forex", "index", "future", "option"})

# Tradeable equity/ETF types on Alpaca (US markets only)
_EQUITY_TYPES = frozenset({"stock", "etf"})

# yfinance crypto pairs are "BASE-QUOTE"; DB rows may still say stock if mis-ingested.
_CRYPTO_QUOTE_SUFFIXES = frozenset({
    "USD", "USDT", "USDC", "GBP", "EUR", "JPY", "AUD", "CAD", "CHF",
    "INR", "KRW", "TRY", "BRL", "MXN", "HKD", "NOK", "SEK", "NZD", "PLN",
    "ZAR", "SGD", "CNY", "BTC", "ETH", "DAI", "BUSD",
})

_ALPACA_COMPACT_CRYPTO = re.compile(r"^([A-Z0-9]{2,})(USD|USDT)$")


def _looks_like_yfinance_crypto_pair(symbol: str) -> bool:
    """True for tickers like BTC-USD, ETH-EUR (not BRK-B or BARC.L)."""
    if "-" not in symbol or "." in symbol:
        return False
    base, quote = symbol.split("-", 1)
    if not base or not quote:
        return False
    if len(quote) < 3:
        return False
    if not base.isalnum():
        return False
    return quote.upper() in _CRYPTO_QUOTE_SUFFIXES


def to_alpaca_symbol(yf_symbol: str, asset_type: str) -> str | None:
    """Convert a yfinance ticker to its Alpaca equivalent.

    Returns the Alpaca symbol string, or None if the asset cannot be traded
    on Alpaca (non-US equity, forex, index, etc.).
    """
    if not yf_symbol:
        return None

    asset_type = (asset_type or "stock").lower()

    if asset_type in _UNSUPPORTED_ASSET_TYPES:
        logger.info(
            "symbol_not_supported_on_alpaca",
            symbol=yf_symbol,
            asset_type=asset_type,
            reason="unsupported_asset_type",
        )
        return None

    if asset_type == "crypto" or _looks_like_yfinance_crypto_pair(yf_symbol):
        return _normalize_crypto(yf_symbol)

    if asset_type in _EQUITY_TYPES:
        return _normalize_equity(yf_symbol)

    logger.info(
        "symbol_not_supported_on_alpaca",
        symbol=yf_symbol,
        asset_type=asset_type,
        reason="unknown_asset_type",
    )
    return None


def canonical_alpaca_symbol(symbol: str) -> str:
    """Normalize broker position/order symbols to a single canonical form.

    BTCUSD and BTC/USD both become BTC/USD; equities pass through unchanged.
    """
    if not symbol:
        return symbol

    upper = symbol.upper()
    if "/" in upper:
        return upper.replace("-", "/")

    if "-" in upper and _looks_like_yfinance_crypto_pair(upper):
        return upper.replace("-", "/")

    match = _ALPACA_COMPACT_CRYPTO.match(upper)
    if match:
        return f"{match.group(1)}/{match.group(2)}"

    return upper


def _normalize_crypto(yf_symbol: str) -> str:
    """Convert yfinance crypto format to Alpaca format.

    BTC-USD  → BTC/USD
    ETH-USD  → ETH/USD
    BTC/USD  → BTC/USD  (already normalized, pass through)
    """
    return yf_symbol.replace("-", "/")


def _normalize_equity(yf_symbol: str) -> str | None:
    """Return the Alpaca symbol for a US equity/ETF, or None if non-US.

    Non-US symbols have a dot-suffix exchange code in yfinance:
      BARC.L   → London Stock Exchange
      SAP.DE   → Deutsche Börse (XETRA)
      7203.T   → Tokyo Stock Exchange
    """
    if "." in yf_symbol:
        logger.info(
            "symbol_not_supported_on_alpaca",
            symbol=yf_symbol,
            asset_type="stock",
            reason="non_us_exchange_suffix",
        )
        return None
    return yf_symbol
