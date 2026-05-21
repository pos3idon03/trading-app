import { useCallback, useEffect, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { marketDataApi } from '../../api/endpoints';
import type { OHLCVBar, TickerSearchResult } from '../../api/types';
import ErrorAlert from '../../components/ErrorAlert';
import Spinner from '../../components/Spinner';
import TiingoTickerSearch from '../../components/TiingoTickerSearch';
import OhlcvTimelineChart from '../../components/charts/OhlcvTimelineChart';

const TIMEFRAMES = ['1d', '1h', '5m'] as const;

interface OhlcvDashboardViewProps {
  title: string;
  description: string;
  basePath: string;
  assetTypeFilter: string[];
  searchPlaceholder: string;
}

export default function OhlcvDashboardView({
  title,
  description,
  basePath,
  assetTypeFilter,
  searchPlaceholder,
}: OhlcvDashboardViewProps) {
  const { symbol } = useParams<{ symbol?: string }>();
  const navigate = useNavigate();
  const [selected, setSelected] = useState<TickerSearchResult | null>(null);
  const [timeframe, setTimeframe] = useState<string>('1d');
  const [records, setRecords] = useState<OHLCVBar[]>([]);
  const [source, setSource] = useState<string>('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadChart = useCallback(
    async (sym: string, tf: string) => {
      setLoading(true);
      setError(null);
      try {
        const data = await marketDataApi.getOhlcv(sym, { timeframe: tf });
        setRecords(data.records);
        setSource(data.source);
      } catch (err: unknown) {
        setRecords([]);
        const status =
          err && typeof err === 'object' && 'response' in err
            ? (err as { response?: { status?: number } }).response?.status
            : undefined;
        if (status === 404) {
          setError(
            `No OHLCV data for ${sym.toUpperCase()}. Add it to the watchlist and run a backfill from Ingestion.`,
          );
        } else {
          setError('Failed to load chart data.');
        }
      } finally {
        setLoading(false);
      }
    },
    [],
  );

  useEffect(() => {
    if (!symbol) {
      setSelected(null);
      setRecords([]);
      setError(null);
      return;
    }
    setSelected({
      symbol: symbol.toUpperCase(),
      name: symbol.toUpperCase(),
      asset_type: assetTypeFilter[0] ?? 'stock',
    });
    loadChart(symbol, timeframe);
  }, [symbol, timeframe, loadChart, assetTypeFilter]);

  const handleSelect = (result: TickerSearchResult | null) => {
    setSelected(result);
    if (result) {
      navigate(`${basePath}/${result.symbol}`);
    } else {
      navigate(basePath);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-100">{title}</h1>
        <p className="text-slate-400 text-sm mt-1">{description}</p>
      </div>

      <div className="flex flex-wrap items-end gap-4">
        <TiingoTickerSearch
          selected={selected}
          onSelect={handleSelect}
          assetTypeFilter={assetTypeFilter}
          placeholder={searchPlaceholder}
        />
        <select
          value={timeframe}
          onChange={(e) => setTimeframe(e.target.value)}
          className="bg-surface-900 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-100"
        >
          {TIMEFRAMES.map((tf) => (
            <option key={tf} value={tf}>
              {tf}
            </option>
          ))}
        </select>
      </div>

      {error && (
        <ErrorAlert message={error}>
          <Link to="/ingestion/watchlist" className="text-brand-500 underline text-sm mt-1 inline-block">
            Go to Watchlist
          </Link>
        </ErrorAlert>
      )}

      {loading && (
        <div className="flex justify-center py-12">
          <Spinner />
        </div>
      )}

      {!loading && symbol && records.length > 0 && (
        <div className="space-y-2">
          <p className="text-xs text-slate-500">
            {symbol.toUpperCase()} · {timeframe} · source: {source} · {records.length} bars
          </p>
          <OhlcvTimelineChart records={records} timeframe={timeframe} />
        </div>
      )}

      {!loading && !symbol && (
        <div className="text-center py-16 text-slate-500 text-sm border border-dashed border-slate-800 rounded-lg">
          Search and select an asset to view its timeline chart.
        </div>
      )}
    </div>
  );
}
