from sqlalchemy.ext.asyncio import AsyncSession

from dal import fundamentals_dal, instrument_dal
from features.market_data.fundamentals_provider import fetch_fundamentals_rows
from utils.logging import get_logger

logger = get_logger(__name__)


async def run_fundamentals_ingest(
    session: AsyncSession,
    symbols: list[str],
) -> dict:
    if not symbols:
        assets = await instrument_dal.list_instruments(session, active_only=True)
        symbols = [a["symbol"] for a in assets]

    inserted = 0
    skipped = []
    errors = []

    for sym in symbols:
        inst = await instrument_dal.get_by_symbol(session, sym)
        if not inst:
            errors.append({"symbol": sym, "error": "not found"})
            continue
        try:
            metrics = await fetch_fundamentals_rows(
                sym,
                asset_type=inst.get("asset_type", "stock"),
                session=session,
            )
            if not metrics:
                skipped.append(sym)
                continue
            await fundamentals_dal.delete_fundamentals_for_instrument(session, inst["id"])
            rows = [{**m, "instrument_id": inst["id"]} for m in metrics]
            inserted += await fundamentals_dal.bulk_insert_fundamentals(session, rows)
            source = metrics[0].get("source", "unknown")
            logger.info("fundamentals_ingested", symbol=sym, source=source, rows=len(rows))
        except Exception as exc:
            logger.error("fundamentals_error", symbol=sym, error=str(exc))
            errors.append({"symbol": sym, "error": str(exc)})

    return {"inserted": inserted, "skipped": skipped, "errors": errors}
