from sqlalchemy.ext.asyncio import AsyncSession

from config import get_settings
from dal import fundamentals_dal, instrument_dal
from features.tiingo import fundamentals_client
from features.tiingo.entitlement import is_fundamentals_entitled
from utils.logging import get_logger
from utils.rate_limiter import check_and_increment

logger = get_logger(__name__)


async def run_fundamentals_ingest(
    session: AsyncSession,
    symbols: list[str],
) -> dict:
    settings = get_settings()
    if not symbols:
        assets = await instrument_dal.list_instruments(session, active_only=True)
        symbols = [a["symbol"] for a in assets]

    inserted = 0
    skipped = []
    errors = []

    for sym in symbols:
        if not is_fundamentals_entitled(sym, settings.tiingo_fundamentals_tier):
            skipped.append(sym)
            continue
        inst = await instrument_dal.get_by_symbol(session, sym)
        if not inst:
            errors.append({"symbol": sym, "error": "not found"})
            continue
        try:
            await check_and_increment(session)
            metrics = await fundamentals_client.fetch_fundamentals_statements(sym)
            rows = [{**m, "instrument_id": inst["id"]} for m in metrics]
            inserted += await fundamentals_dal.bulk_insert_fundamentals(session, rows)
        except Exception as exc:
            logger.error("fundamentals_error", symbol=sym, error=str(exc))
            errors.append({"symbol": sym, "error": str(exc)})

    return {"inserted": inserted, "skipped": skipped, "errors": errors}
