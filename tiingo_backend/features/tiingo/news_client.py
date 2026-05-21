from datetime import datetime, timezone

import httpx

from features.tiingo.common import get_token
from utils.logging import get_logger

logger = get_logger(__name__)

_NEWS_URL = "https://api.tiingo.com/tiingo/news"


async def fetch_news(tickers: list[str], limit: int = 50) -> list[dict]:
    token = get_token()
    params = {"token": token, "limit": limit}
    if tickers:
        params["tickers"] = ",".join(t.upper() for t in tickers)

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(_NEWS_URL, params=params)
        resp.raise_for_status()
        payload = resp.json()

    articles = []
    for item in payload:
        published = item.get("publishedDate") or item.get("crawledDate")
        if not published:
            continue
        ts = datetime.fromisoformat(published.replace("Z", "+00:00"))
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        articles.append({
            "published_at": ts,
            "title": item.get("title", ""),
            "url": item.get("url", ""),
            "description": item.get("description"),
            "source": "tiingo",
            "tickers": item.get("tickers") or [],
            "tags": item.get("tags") or [],
            "raw_data": item,
        })
    logger.info("news_fetched", count=len(articles))
    return articles
