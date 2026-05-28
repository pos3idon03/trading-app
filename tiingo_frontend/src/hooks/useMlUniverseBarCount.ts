import { useEffect, useMemo, useState } from 'react';
import { marketDataApi } from '../api/endpoints';
import type { DateRangeValue } from '../constants/timeframes';
import { buildOhlcvQuery } from '../constants/timeframes';
import { apiRangeFromOhlcvQuery } from '../utils/multitimeframeBacktest';

export interface MlUniverseBarCount {
  barCount: number | null;
  rangeStart: string | null;
  rangeEnd: string | null;
  loading: boolean;
  error: string | null;
}

export function useMlUniverseBarCount(
  symbol: string,
  decisionTimeframe: string,
  dateRange: DateRangeValue,
): MlUniverseBarCount {
  const [barCount, setBarCount] = useState<number | null>(null);
  const [rangeStart, setRangeStart] = useState<string | null>(null);
  const [rangeEnd, setRangeEnd] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const query = useMemo(
    () => buildOhlcvQuery(decisionTimeframe, dateRange),
    [decisionTimeframe, dateRange],
  );

  useEffect(() => {
    if (!symbol) {
      setBarCount(null);
      setRangeStart(null);
      setRangeEnd(null);
      setError(null);
      return;
    }

    let cancelled = false;
    setLoading(true);
    setError(null);

    marketDataApi
      .getOhlcv(symbol, {
        timeframe: decisionTimeframe,
        ...apiRangeFromOhlcvQuery(query),
        limit: query.limit,
      })
      .then((response) => {
        if (cancelled) {
          return;
        }
        const records = response.records ?? [];
        setBarCount(response.count ?? records.length);
        setRangeStart(records[0]?.time ?? null);
        setRangeEnd(records[records.length - 1]?.time ?? null);
      })
      .catch((err: unknown) => {
        if (cancelled) {
          return;
        }
        setBarCount(null);
        setRangeStart(null);
        setRangeEnd(null);
        setError(err instanceof Error ? err.message : 'Failed to load bar count for date range.');
      })
      .finally(() => {
        if (!cancelled) {
          setLoading(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [symbol, decisionTimeframe, query]);

  return { barCount, rangeStart, rangeEnd, loading, error };
}
