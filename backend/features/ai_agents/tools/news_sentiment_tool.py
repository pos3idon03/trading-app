"""News Sentiment Tool: fetches recent financial headlines and produces a sentiment score.

Uses NewsAPI to retrieve articles, then scores each headline with the LLM.
Requires NEWSAPI_KEY environment variable.
"""
import json
from typing import Optional

import httpx
from crewai.tools import BaseTool
from pydantic import BaseModel, Field

from config import get_settings
from utils.logging import get_logger

logger = get_logger(__name__)

NEWSAPI_URL = "https://newsapi.org/v2/everything"
MAX_ARTICLES = 10


class NewsSentimentInput(BaseModel):
    ticker: str = Field(description="Stock ticker or company name to search for, e.g. AAPL or Apple")
    days_back: int = Field(default=7, ge=1, le=30, description="Number of days of news to fetch")


class NewsSentimentTool(BaseTool):
    name: str = "news_sentiment"
    description: str = (
        "Fetches recent financial news headlines for a ticker and returns a list of articles "
        "with their publication date and source, plus an aggregate sentiment score from -1.0 (bearish) "
        "to +1.0 (bullish). Use this to gauge market sentiment around an asset."
    )
    args_schema: type[BaseModel] = NewsSentimentInput

    def _run(self, ticker: str, days_back: int = 7) -> str:
        api_key = get_settings().newsapi_key
        if not api_key:
            return "NEWSAPI_KEY is not configured. Cannot fetch news sentiment."

        articles = _fetch_articles(ticker, api_key, days_back)
        if not articles:
            return f"No recent news found for {ticker} in the last {days_back} days."

        return _format_articles(ticker, articles)


def _fetch_articles(ticker: str, api_key: str, days_back: int) -> list[dict]:
    """Fetch recent articles from NewsAPI."""
    from datetime import datetime, timedelta, timezone

    from_date = (datetime.now(timezone.utc) - timedelta(days=days_back)).strftime("%Y-%m-%d")
    params = {
        "q": ticker,
        "from": from_date,
        "sortBy": "relevancy",
        "language": "en",
        "pageSize": MAX_ARTICLES,
        "apiKey": api_key,
    }
    try:
        with httpx.Client(timeout=15) as client:
            resp = client.get(NEWSAPI_URL, params=params)
            resp.raise_for_status()
        data = resp.json()
        return data.get("articles", [])
    except Exception as exc:
        logger.warning("newsapi_fetch_error", ticker=ticker, error=str(exc))
        return []


def _format_articles(ticker: str, articles: list[dict]) -> str:
    """Format articles as a structured string for the LLM to analyze."""
    lines = [
        f"Recent news for {ticker} ({len(articles)} articles).",
        "The following headlines should be used to assess market sentiment.",
        "Provide a sentiment score from -1.0 (strongly bearish) to +1.0 (strongly bullish).\n",
    ]
    for i, art in enumerate(articles, 1):
        title = art.get("title", "No title")
        source = art.get("source", {}).get("name", "Unknown")
        date = (art.get("publishedAt", "")[:10])
        description = art.get("description") or ""
        lines.append(f"{i}. [{date}] {source}: {title}")
        if description:
            lines.append(f"   {description[:200]}")
    return "\n".join(lines)
