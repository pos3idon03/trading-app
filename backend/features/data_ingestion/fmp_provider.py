from datetime import datetime, timezone
from typing import Optional

from config import get_settings
from dtos.market_data_dto import FundamentalRecord, OHLCVRecord
from utils.api_client import fetch_json
from utils.logging import get_logger

from .base_provider import DataProvider

logger = get_logger(__name__)
FMP_BASE = "https://financialmodelingprep.com/api/v3"


class FMPProvider(DataProvider):
    """Financial Modeling Prep — primary for fundamentals and macro data."""

    def __init__(self) -> None:
        self._api_key = get_settings().fmp_api_key

    @property
    def name(self) -> str:
        return "fmp"

    async def fetch_ohlcv(
        self,
        symbol: str,
        timeframe: str,
        start: datetime,
        end: datetime,
        asset_id: Optional[int] = None,
        asset_type: Optional[str] = None,
    ) -> list[OHLCVRecord]:
        """FMP OHLCV is available but Polygon is preferred. Provided for completeness."""
        tf_map = {"1m": "1min", "5m": "5min", "15m": "15min", "30m": "30min", "1h": "1hour", "4h": "4hour", "1d": "daily"}
        fmp_tf = tf_map.get(timeframe, "daily")
        if fmp_tf == "daily":
            url = f"{FMP_BASE}/historical-price-full/{symbol}"
        else:
            url = f"{FMP_BASE}/historical-chart/{fmp_tf}/{symbol}"
        params = {
            "from": start.strftime("%Y-%m-%d"),
            "to": end.strftime("%Y-%m-%d"),
            "apikey": self._api_key,
        }
        data = await fetch_json(url, params=params)
        raw = data if isinstance(data, list) else data.get("historical", [])
        records = [self._bar_to_record(bar, timeframe, asset_id) for bar in raw]
        logger.info("fmp_ohlcv_fetched", symbol=symbol, timeframe=timeframe, count=len(records))
        return records

    async def fetch_fundamentals(
        self,
        symbol: str,
        asset_id: Optional[int] = None,
    ) -> list[FundamentalRecord]:
        records = []
        records.extend(await self._fetch_income_statement(symbol, asset_id))
        records.extend(await self._fetch_balance_sheet(symbol, asset_id))
        records.extend(await self._fetch_key_metrics(symbol, asset_id))
        logger.info("fmp_fundamentals_fetched", symbol=symbol, count=len(records))
        return records

    async def _fetch_income_statement(self, symbol: str, asset_id: Optional[int]) -> list[FundamentalRecord]:
        url = f"{FMP_BASE}/income-statement/{symbol}"
        data = await fetch_json(url, params={"limit": 8, "apikey": self._api_key})
        return self._statements_to_records(data, asset_id, "income")

    async def _fetch_balance_sheet(self, symbol: str, asset_id: Optional[int]) -> list[FundamentalRecord]:
        url = f"{FMP_BASE}/balance-sheet-statement/{symbol}"
        data = await fetch_json(url, params={"limit": 8, "apikey": self._api_key})
        return self._statements_to_records(data, asset_id, "balance")

    async def _fetch_key_metrics(self, symbol: str, asset_id: Optional[int]) -> list[FundamentalRecord]:
        url = f"{FMP_BASE}/key-metrics/{symbol}"
        data = await fetch_json(url, params={"limit": 8, "apikey": self._api_key})
        return self._statements_to_records(data, asset_id, "metrics")

    def _statements_to_records(self, data: list, asset_id: Optional[int], prefix: str) -> list[FundamentalRecord]:
        records = []
        skip = {"symbol", "reportedCurrency", "cik", "fillingDate", "acceptedDate", "calendarYear", "period", "date", "link", "finalLink"}
        for item in data:
            date_str = item.get("date") or item.get("fillingDate", "")
            period = f"{item.get('period', '')}-{item.get('calendarYear', '')}"
            try:
                time = datetime.fromisoformat(date_str + "T00:00:00+00:00")
            except ValueError:
                time = datetime.now(timezone.utc)
            for key, value in item.items():
                if key in skip or value is None:
                    continue
                try:
                    records.append(FundamentalRecord(
                        time=time,
                        asset_id=asset_id,
                        metric_name=f"{prefix}.{key}",
                        value=float(value),
                        period=period,
                        source=self.name,
                    ))
                except (ValueError, TypeError):
                    continue
        return records

    def _bar_to_record(self, bar: dict, timeframe: str, asset_id: Optional[int]) -> OHLCVRecord:
        date_str = bar.get("date", "")
        try:
            ts = datetime.fromisoformat(date_str).replace(tzinfo=timezone.utc)
        except ValueError:
            ts = datetime.now(timezone.utc)
        return OHLCVRecord(
            time=ts,
            asset_id=asset_id or 0,
            timeframe=timeframe,
            open=float(bar.get("open", 0)),
            high=float(bar.get("high", 0)),
            low=float(bar.get("low", 0)),
            close=float(bar.get("close", 0)),
            volume=int(bar.get("volume", 0)),
            vwap=bar.get("vwap"),
            source=self.name,
        )
