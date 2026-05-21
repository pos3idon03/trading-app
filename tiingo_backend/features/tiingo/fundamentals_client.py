from datetime import datetime, timezone

import httpx

from features.tiingo.common import get_token
from utils.logging import get_logger

logger = get_logger(__name__)

_FUND_URL = "https://api.tiingo.com/tiingo/fundamentals"


async def fetch_fundamentals_statements(symbol: str) -> list[dict]:
    token = get_token()
    url = f"{_FUND_URL}/{symbol.upper()}/statements"
    params = {"token": token}
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.get(url, params=params)
        resp.raise_for_status()
        payload = resp.json()

    rows = []
    now = datetime.now(timezone.utc)
    data = payload if isinstance(payload, list) else payload.get("statements", [])
    for stmt in data:
        report_date = stmt.get("date") or stmt.get("reportDate")
        if not report_date:
            continue
        ts = datetime.fromisoformat(str(report_date)[:10]).replace(tzinfo=timezone.utc)
        for key, val in stmt.items():
            if key in ("date", "reportDate", "fiscalYear", "fiscalQuarter"):
                continue
            if isinstance(val, (int, float)):
                rows.append({
                    "time": ts,
                    "metric_name": key,
                    "value": float(val),
                    "period": f"{stmt.get('fiscalYear', '')}-Q{stmt.get('fiscalQuarter', '')}",
                    "statement_type": stmt.get("statementType", "statements"),
                    "source": "tiingo",
                    "raw_data": stmt,
                })
    logger.info("fundamentals_fetched", symbol=symbol, metrics=len(rows))
    return rows
