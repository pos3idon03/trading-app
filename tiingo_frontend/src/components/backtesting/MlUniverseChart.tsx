import { useEffect, useMemo, useState } from 'react';
import { marketDataApi } from '../../api/endpoints';
import type { OHLCVBar } from '../../api/types';
import type { DateRangeValue } from '../../constants/timeframes';
import { buildOhlcvQuery } from '../../constants/timeframes';
import { apiRangeFromOhlcvQuery } from '../../utils/multitimeframeBacktest';
import OhlcvTimelineChart from '../charts/OhlcvTimelineChart';
import Spinner from '../Spinner';

interface MlUniverseChartProps {
  symbol: string;
  decisionTimeframe: string;
  dateRange: DateRangeValue;
}

export default function MlUniverseChart({
  symbol,
  decisionTimeframe,
  dateRange,
}: MlUniverseChartProps) {
  const [records, setRecords] = useState<OHLCVBar[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const query = useMemo(
    () => buildOhlcvQuery(decisionTimeframe, dateRange),
    [decisionTimeframe, dateRange],
  );

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    marketDataApi
      .getOhlcv(symbol, {
        timeframe: decisionTimeframe,
        ...apiRangeFromOhlcvQuery(query),
      })
      .then((response) => {
        if (!cancelled) {
          setRecords(response.records);
        }
      })
      .catch((err: unknown) => {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : 'Failed to load price history.');
        }
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

  if (loading) {
    return (
      <div className="flex justify-center py-8">
        <Spinner />
      </div>
    );
  }

  if (error) {
    return <p className="text-sm text-red-400">{error}</p>;
  }

  if (!records.length) {
    return <p className="text-sm text-slate-500">No price history for this universe.</p>;
  }

  const startDate = records[0]?.time ?? '—';
  const endDate = records[records.length - 1]?.time ?? '—';

  return (
    <div className="space-y-2">
      <p className="text-xs text-slate-400">
        {records.length.toLocaleString()} bars · {startDate} → {endDate}
      </p>
      <OhlcvTimelineChart records={records} timeframe={decisionTimeframe} height={320} />
    </div>
  );
}
