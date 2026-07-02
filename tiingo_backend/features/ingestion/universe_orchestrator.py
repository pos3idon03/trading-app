"""S&P 500 and custom universe seed ingestion."""

from __future__ import annotations

from datetime import date
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from dal import universe_dal


WIKI_SP500_URL = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"


async def fetch_sp500_symbols() -> list[str]:
    try:
        import pandas as pd

        tables = pd.read_html(WIKI_SP500_URL)
        if not tables:
            return _fallback_sp500()
        symbols = tables[0]["Symbol"].astype(str).str.upper().tolist()
        return [s.replace(".", "-") for s in symbols if s]
    except Exception:
        return _fallback_sp500()


def _fallback_sp500() -> list[str]:
    return [
        "AAPL", "MSFT", "AMZN", "NVDA", "GOOGL", "META", "BRK-B", "LLY", "AVGO", "JPM",
        "V", "UNH", "XOM", "MA", "PG", "JNJ", "HD", "COST", "MRK", "ABBV",
    ]


async def seed_universe(
    session: AsyncSession,
    *,
    name: str,
    source: str = "wikipedia",
    description: str | None = None,
    symbols: list[str] | None = None,
    effective_from: date | None = None,
) -> dict[str, Any]:
    eff = effective_from or date.today()
    if symbols:
        resolved = [s.upper() for s in symbols]
    elif name.upper() in ("SP500", "S&P500", "S&P 500"):
        resolved = await fetch_sp500_symbols()
        source = source or "wikipedia"
        description = description or "S&P 500 constituents"
    else:
        raise ValueError("Provide symbols or use name SP500")

    universe = await universe_dal.create_universe(
        session,
        name=name,
        source=source,
        description=description,
    )
    members = [
        {"symbol": sym, "effective_from": eff, "effective_to": None}
        for sym in resolved
    ]
    count = await universe_dal.upsert_members(session, universe["id"], members)
    return {
        "universe_id": universe["id"],
        "name": universe["name"],
        "member_count": count,
        "symbols": resolved,
    }
