import { useCallback, useEffect, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { ingestionApi, marketDataApi } from '../../api/endpoints';
import type { Instrument, OHLCVBar } from '../../api/types';
import DateRangeControls from '../../components/DateRangeControls';
import ErrorAlert from '../../components/ErrorAlert';
import InstrumentSearch from '../../components/InstrumentSearch';
import Spinner from '../../components/Spinner';
import FundamentalsPanel from '../../components/FundamentalsPanel';
import PerformanceCards from '../../components/PerformanceCards';
import StockKpiPanel from '../../components/StockKpiPanel';
import OhlcvTimelineChart from '../../components/charts/OhlcvTimelineChart';
import {
  OHLCV_TIMEFRAMES,
  type DateRangeValue,
  buildOhlcvQuery,
  dateRangeModeForTimeframe,
  defaultDateRangeForTimeframe,
  isDailyPlusTimeframe,
} from '../../constants/timeframes';

interface OhlcvDashboardViewProps {
  title: string;
  description: string;
  basePath: string;
  assetTypeFilter: string[];
  searchPlaceholder: string;
  showFundamentals?: boolean;
}

function extractErrorMessage(err: unknown, symbol: string): string {
  if (err && typeof err === 'object' && 'response' in err) {
    const resp = (err as { response?: { status?: number; data?: { detail?: string } } }).response;
    if (resp?.status === 404) {
      return `No OHLCV data for ${symbol.toUpperCase()}. Run a backfill from Ingestion → Market Data.`;
    }
    if (typeof resp?.data?.detail === 'string') {
      return resp.data.detail;
    }
  }
  return 'Failed to load chart data.';
}

export default function OhlcvDashboardView({
  title,
  description,
  basePath,
  assetTypeFilter,
  searchPlaceholder,
  showFundamentals = false,
}: OhlcvDashboardViewProps) {
  const { symbol } = useParams<{ symbol?: string }>();
  const navigate = useNavigate();
  const [selected, setSelected] = useState<Instrument | null>(null);
  const [timeframe, setTimeframe] = useState<string>('1d');
  const [dateRange, setDateRange] = useState<DateRangeValue>(() => defaultDateRangeForTimeframe('1d'));
  const [records, setRecords] = useState<OHLCVBar[]>([]);
  const [source, setSource] = useState<string>('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadChart = useCallback(async (sym: string, tf: string, range: DateRangeValue) => {
    setLoading(true);
    setError(null);
    try {
      const query = buildOhlcvQuery(tf, range);
      const data = await marketDataApi.getOhlcv(sym, query);
      setRecords(data.records);
      setSource(data.source);
    } catch (err: unknown) {
      setRecords([]);
      setError(extractErrorMessage(err, sym));
    } finally {
      setLoading(false);
    }
  }, []);

  const handleTimeframeChange = (tf: string) => {
    setTimeframe(tf);
    setDateRange(defaultDateRangeForTimeframe(tf));
  };

  useEffect(() => {
    if (!symbol) {
      setSelected(null);
      setRecords([]);
      setError(null);
      return;
    }

    let cancelled = false;
    ingestionApi
      .searchDbInstruments(symbol, assetTypeFilter, 1)
      .then((items) => {
        if (cancelled) return;
        const match = items.find((i) => i.symbol.toUpperCase() === symbol.toUpperCase());
        setSelected(
          match ?? {
            id: 0,
            symbol: symbol.toUpperCase(),
            name: symbol.toUpperCase(),
            asset_type: assetTypeFilter[0] ?? 'stock',
            currency: 'USD',
            is_active: true,
          },
        );
      })
      .catch(() => {
        if (!cancelled) {
          setSelected({
            id: 0,
            symbol: symbol.toUpperCase(),
            name: symbol.toUpperCase(),
            asset_type: assetTypeFilter[0] ?? 'stock',
            currency: 'USD',
            is_active: true,
          });
        }
      });

    loadChart(symbol, timeframe, dateRange);
    return () => {
      cancelled = true;
    };
  }, [symbol, timeframe, dateRange, loadChart, assetTypeFilter]);

  const handleSelect = (instrument: Instrument | null) => {
    setSelected(instrument);
    if (instrument) {
      navigate(`${basePath}/${instrument.symbol}`);
    } else {
      navigate(basePath);
    }
  };

  const rangeLabel =
    dateRange.preset === 'MAX' && !dateRange.start
      ? isDailyPlusTimeframe(timeframe)
        ? 'MAX'
        : `last ${records.length} bars`
      : [dateRange.start?.slice(0, 10), dateRange.end?.slice(0, 10)].filter(Boolean).join(' → ');

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-100">{title}</h1>
        <p className="text-slate-400 text-sm mt-1">{description}</p>
      </div>

      <div className="flex flex-wrap items-end gap-4">
        <InstrumentSearch
          selected={selected}
          onSelect={handleSelect}
          assetTypeFilter={assetTypeFilter}
          placeholder={searchPlaceholder}
        />
        <select
          value={timeframe}
          onChange={(e) => handleTimeframeChange(e.target.value)}
          className="bg-surface-900 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-100"
        >
          {OHLCV_TIMEFRAMES.map((tf) => (
            <option key={tf.value} value={tf.value}>
              {tf.label}
            </option>
          ))}
        </select>
      </div>

      <DateRangeControls
        value={dateRange}
        onChange={setDateRange}
        mode={dateRangeModeForTimeframe(timeframe)}
      />

      {error && (
        <ErrorAlert message={error}>
          <Link to="/ingestion/market" className="text-brand-500 underline text-sm mt-1 inline-block">
            Go to Market Data Ingestion
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
            {symbol.toUpperCase()} · {timeframe} · source: {source} · {records.length} bars · {rangeLabel}
          </p>
          <OhlcvTimelineChart records={records} timeframe={timeframe} />
        </div>
      )}

      {showFundamentals && symbol && !loading && (
        <PerformanceCards symbol={symbol} />
      )}

      {showFundamentals && symbol && (
        <section className="space-y-4 pt-4 border-t border-slate-800">
          <h2 className="text-lg font-semibold text-slate-200">Fundamentals</h2>
          <FundamentalsPanel symbol={symbol} />
        </section>
      )}

      {showFundamentals && symbol && !loading && (
        <StockKpiPanel symbol={symbol} />
      )}

      {!loading && !symbol && (
        <div className="text-center py-16 text-slate-500 text-sm border border-dashed border-slate-800 rounded-lg">
          Search ingested instruments in your watchlist to view a timeline chart.
        </div>
      )}
    </div>
  );
}
