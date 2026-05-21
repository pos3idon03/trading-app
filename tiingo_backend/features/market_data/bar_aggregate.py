from datetime import datetime, timedelta, timezone

from dtos.market_data_dto import OHLCVRecord

_BUCKETS = {"4h": timedelta(hours=4)}


def _bucket_start(ts: datetime, bucket: timedelta) -> datetime:
    epoch = datetime(1970, 1, 1, tzinfo=timezone.utc)
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    seconds = int((ts - epoch).total_seconds())
    bucket_seconds = int(bucket.total_seconds())
    aligned = (seconds // bucket_seconds) * bucket_seconds
    return epoch + timedelta(seconds=aligned)


def aggregate_ohlcv_bars(records: list[OHLCVRecord], target_timeframe: str) -> list[OHLCVRecord]:
    bucket = _BUCKETS.get(target_timeframe)
    if not bucket or not records:
        return records

    groups: dict[datetime, list[OHLCVRecord]] = {}
    for rec in sorted(records, key=lambda row: row.time):
        key = _bucket_start(rec.time, bucket)
        groups.setdefault(key, []).append(rec)

    return [
        OHLCVRecord(
            time=t,
            instrument_id=bars[0].instrument_id,
            timeframe=target_timeframe,
            open=bars[0].open,
            high=max(b.high for b in bars),
            low=min(b.low for b in bars),
            close=bars[-1].close,
            volume=sum(b.volume for b in bars),
            source=bars[0].source,
        )
        for t, bars in sorted(groups.items())
    ]
