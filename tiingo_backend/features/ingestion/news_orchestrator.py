from sqlalchemy.ext.asyncio import AsyncSession

from dal import instrument_dal, news_dal
from features.tiingo import news_client
from utils.logging import get_logger
from utils.rate_limiter import check_and_increment

logger = get_logger(__name__)


async def run_news_ingest(
    session: AsyncSession,
    symbols: list[str],
    limit: int = 50,
) -> dict:
    if not symbols:
        assets = await instrument_dal.list_instruments(session, active_only=True)
        symbols = [a["symbol"] for a in assets]

    await check_and_increment(session)
    articles = await news_client.fetch_news(symbols, limit=limit)
    inserted = await news_dal.bulk_insert_news(session, articles)
    logger.info("news_ingest_done", fetched=len(articles), inserted=inserted)
    return {"fetched": len(articles), "inserted": inserted, "symbols": symbols}
