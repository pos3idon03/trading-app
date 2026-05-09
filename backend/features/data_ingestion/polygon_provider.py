from datetime import datetime
from typing import Optional

from config import get_settings
from dtos.market_data_dto import FundamentalRecord, OHLCVRecord
from utils.api_client import fetch_json
from utils.logging import get_logger
from utils.time_utils import utcnow

from .base_provider import DataProvider

logger = get_logger(__name__)
POLYGON_BASE = "https://api.polygon.io"


class PolygonProvider(DataProvider):
    """Polygon.io REST provider — primary for live and historical OHLCV."""

    def __init__(self) -> None:
        self._api_key = get_settings().polygon_api_key

    @property
    def name(self) -> str:
        return "polygon"

    async def fetch_ohlcv(
        self,
        symbol: str,
        timeframe: str,
        start: datetime,
        end: datetime,
        asset_id: Optional[int] = None,
    ) -> list[OHLCVRecord]:
        multiplier, timespan = self._timeframe_to_provider_params(timeframe)
        url = (
            f"{POLYGON_BASE}/v2/aggs/ticker/{symbol}/range"
            f"/{multiplier}/{timespan}"
            f"/{start.strftime('%Y-%m-%d')}/{end.strftime('%Y-%m-%d')}"
        )
        params = {"adjusted": "true", "sort": "asc", "limit": 50000, "apiKey": self._api_key}
        records: list[OHLCVRecord] = []
        while url:
            data = await fetch_json(url, params=params)
            results = data.get("results") or []
            for bar in results:
                records.append(self._bar_to_record(bar, symbol, timeframe, asset_id))
            url = data.get("next_url")
            params = {"apiKey": self._api_key} if url else {}
        logger.info("polygon_ohlcv_fetched", symbol=symbol, timeframe=timeframe, count=len(records))
        return records

    async def fetch_fundamentals(
        self,
        symbol: str,
        asset_id: Optional[int] = None,
    ) -> list[FundamentalRecord]:
        """Polygon offers basic financials — use FMP for deep fundamentals."""
        url = f"{POLYGON_BASE}/vX/reference/financials"
        params = {"ticker": symbol, "limit": 10, "apiKey": self._api_key}
        data = await fetch_json(url, params=params)
        records = []
        for item in (data.get("results") or []):
            records.extend(self._financials_to_records(item, symbol, asset_id))
        return records

    def _bar_to_record(self, bar: dict, symbol: str, timeframe: str, asset_id: Optional[int]) -> OHLCVRecord:
        from datetime import timezone
        ts = datetime.fromtimestamp(bar["t"] / 1000, tz=timezone.utc)
        return OHLCVRecord(
            time=ts,
            asset_id=asset_id or 0,
            timeframe=timeframe,
            open=bar["o"],
            high=bar["h"],
            low=bar["l"],
            close=bar["c"],
            volume=int(bar.get("v", 0)),
            vwap=bar.get("vw"),
            trade_count=bar.get("n"),
            source=self.name,
        )

    def _financials_to_records(self, item: dict, symbol: str, asset_id: Optional[int]) -> list[FundamentalRecord]:
        records = []
        period = item.get("fiscal_period", "") + "-" + str(item.get("fiscal_year", ""))
        filing_date = item.get("filing_date") or item.get("start_date") or str(utcnow().date())
        time = datetime.fromisoformat(filing_date + "T00:00:00+00:00")
        financials = item.get("financials", {})
        for category, metrics in financials.items():
            for metric_name, meta in metrics.items():
                value = meta.get("value")
                if value is not None:
                    records.append(FundamentalRecord(
                        time=time,
                        asset_id=asset_id,
                        metric_name=f"{category}.{metric_name}",
                        value=float(value),
                        period=period,
                        source=self.name,
                    ))
        return records
