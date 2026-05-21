import { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { ingestionApi } from '../api/endpoints';
import type { FundamentalMetric, FundamentalsPeriodType } from '../api/types';
import {
  FUNDAMENTAL_GROUPS,
  FUNDAMENTAL_METRIC_CODES,
  metricsByGroup,
} from '../constants/fundamentalsMetrics';
import {
  buildFundamentalsSeries,
  metricsWithChartData,
} from '../utils/fundamentalsChartData';
import FundamentalsMetricChart from './charts/FundamentalsMetricChart';
import ErrorAlert from './ErrorAlert';
import Spinner from './Spinner';

type PeriodMode = 'quarterly' | 'yearly';

interface FundamentalsPanelProps {
  symbol: string;
}

function periodTypeForMode(mode: PeriodMode): FundamentalsPeriodType {
  return mode === 'yearly' ? 'annual' : 'quarterly';
}

function extractErrorMessage(err: unknown, symbol: string): string {
  if (err && typeof err === 'object' && 'response' in err) {
    const resp = (err as { response?: { status?: number; data?: { detail?: string } } }).response;
    if (resp?.status === 404) {
      const detail = resp?.data?.detail ?? '';
      if (detail.includes('Instrument not found')) {
        return `${symbol.toUpperCase()} is not in your watchlist.`;
      }
      return `No fundamentals for ${symbol.toUpperCase()} in this period. Re-ingest from Fundamentals tab.`;
    }
    if (typeof resp?.data?.detail === 'string') {
      return resp.data.detail;
    }
  }
  return 'Failed to load fundamentals.';
}

export default function FundamentalsPanel({ symbol }: FundamentalsPanelProps) {
  const [periodMode, setPeriodMode] = useState<PeriodMode>('quarterly');
  const [metrics, setMetrics] = useState<FundamentalMetric[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadFundamentals = useCallback(async (sym: string, mode: PeriodMode) => {
    setLoading(true);
    setError(null);
    try {
      const data = await ingestionApi.getFundamentals(sym, {
        period_type: periodTypeForMode(mode),
        metric_names: FUNDAMENTAL_METRIC_CODES.join(','),
        order: 'asc',
        all: true,
      });
      setMetrics(data.metrics);
    } catch (err: unknown) {
      setMetrics([]);
      setError(extractErrorMessage(err, sym));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!symbol) return;
    loadFundamentals(symbol, periodMode);
  }, [symbol, periodMode, loadFundamentals]);

  const withData = metricsWithChartData(metrics, FUNDAMENTAL_METRIC_CODES);
  const dataCount = withData.size;

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="inline-flex rounded-lg border border-slate-700 overflow-hidden">
          <button
            type="button"
            onClick={() => setPeriodMode('quarterly')}
            className={`px-4 py-2 text-sm font-medium transition-colors ${
              periodMode === 'quarterly'
                ? 'bg-brand-600 text-white'
                : 'bg-surface-900 text-slate-400 hover:text-slate-200'
            }`}
          >
            Quarterly
          </button>
          <button
            type="button"
            onClick={() => setPeriodMode('yearly')}
            className={`px-4 py-2 text-sm font-medium transition-colors ${
              periodMode === 'yearly'
                ? 'bg-brand-600 text-white'
                : 'bg-surface-900 text-slate-400 hover:text-slate-200'
            }`}
          >
            Yearly
          </button>
        </div>
        {!loading && !error && metrics.length > 0 && (
          <p className="text-xs text-slate-500">
            {dataCount} of {FUNDAMENTAL_METRIC_CODES.length} metrics with trend data ·{' '}
            {periodMode === 'quarterly' ? 'calendar quarters' : 'calendar years (aggregated)'}
          </p>
        )}
      </div>

      {error && (
        <ErrorAlert message={error}>
          <Link
            to="/ingestion/fundamentals"
            className="text-brand-500 underline text-sm mt-1 inline-block"
          >
            Go to Fundamentals Ingestion
          </Link>
        </ErrorAlert>
      )}

      {loading && (
        <div className="flex justify-center py-8">
          <Spinner />
        </div>
      )}

      {!loading && !error && metrics.length === 0 && (
        <div className="text-center py-8 text-slate-500 text-sm border border-dashed border-slate-800 rounded-lg">
          No fundamentals data for this period.
        </div>
      )}

      {!loading && !error && metrics.length > 0 && (
        <div className="space-y-8">
          {FUNDAMENTAL_GROUPS.map((group) => {
            const defs = metricsByGroup(group);
            const chartsInGroup = defs.filter((d) => withData.has(d.dataCode));
            if (!chartsInGroup.length) return null;
            return (
              <section key={group} className="space-y-3">
                <h3 className="text-sm font-semibold text-slate-400 uppercase tracking-wider">
                  {defs[0]?.groupLabel}
                </h3>
                <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-4">
                  {chartsInGroup.map((def) => (
                    <FundamentalsMetricChart
                      key={def.dataCode}
                      label={def.label}
                      format={def.format}
                      data={buildFundamentalsSeries(metrics, def.dataCode)}
                    />
                  ))}
                </div>
              </section>
            );
          })}
        </div>
      )}
    </div>
  );
}
