"""Tiingo crypto meta catalog — cached GET /tiingo/crypto."""
from datetime import datetime, timezone

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from config import get_settings
from features.tiingo.common import get_token
from utils.logging import get_logger
from utils.rate_limiter import check_and_increment

logger = get_logger(__name__)

_CRYPTO_META_URL = "https://api.tiingo.com/tiingo/crypto"
_cache_fetched_at: datetime | None = None
_cache_rows: list[dict] = []


def _cache_valid(now: datetime, ttl_seconds: int) -> bool:
    if not _cache_rows or _cache_fetched_at is None:
        return False
    age = (now - _cache_fetched_at).total_seconds()
    return age < ttl_seconds


def clear_crypto_meta_cache() -> None:
    global _cache_fetched_at, _cache_rows
    _cache_fetched_at = None
    _cache_rows = []


async def _fetch_meta(token: str, tickers: str | None = None) -> list[dict]:
    params: dict[str, str] = {"token": token}
    if tickers:
        params["tickers"] = tickers
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(_CRYPTO_META_URL, params=params)
        resp.raise_for_status()
        payload = resp.json()
    if not isinstance(payload, list):
        return []
    return [row for row in payload if isinstance(row, dict)]


async def get_crypto_meta(session: AsyncSession | None = None) -> list[dict]:
    global _cache_fetched_at, _cache_rows

    settings = get_settings()
    now = datetime.now(timezone.utc)
    if _cache_valid(now, settings.crypto_meta_cache_ttl_seconds):
        return _cache_rows

    token = get_token()
    if session is not None:
        await check_and_increment(session)
    rows = await _fetch_meta(token)
    _cache_rows = rows
    _cache_fetched_at = now
    logger.info("crypto_meta_cached", count=len(rows))
    return _cache_rows


async def get_crypto_meta_for_ticker(
    ticker: str,
    session: AsyncSession | None = None,
) -> list[dict]:
    settings = get_settings()
    now = datetime.now(timezone.utc)
    if _cache_valid(now, settings.crypto_meta_cache_ttl_seconds):
        needle = ticker.strip().lower()
        return [row for row in _cache_rows if (row.get("ticker") or "").lower() == needle]

    token = get_token()
    if session is not None:
        await check_and_increment(session)
    return await _fetch_meta(token, tickers=ticker.strip().lower())
