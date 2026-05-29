from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from config import get_settings
from dal import news_sentiment_dal


async def fetch_symbol_sentiment_context(
    session: AsyncSession,
    *,
    symbol: str,
    on_date: date,
) -> dict | None:
    settings = get_settings()
    if not settings.sentiment_enabled:
        return None
    return await news_sentiment_dal.get_daily_sentiment(
        session,
        symbol=symbol,
        on_date=on_date,
        model_name=settings.sentiment_model_name,
        model_version=settings.sentiment_model_version,
    )
