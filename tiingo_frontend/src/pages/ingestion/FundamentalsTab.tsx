import { useCallback, useEffect, useState } from 'react';
import { ingestionApi } from '../../api/endpoints';
import type { FundamentalsCoverageItem, TickerSearchResult } from '../../api/types';
import TiingoTickerSearch from '../../components/TiingoTickerSearch';
import Spinner from '../../components/Spinner';
import ErrorAlert from '../../components/ErrorAlert';

function formatDate(iso: string): string {
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? iso : d.toLocaleString();
}

export default function FundamentalsTab() {
  const [entitlement, setEntitlement] = useState<Record<string, unknown> | null>(null);
  const [coverage, setCoverage] = useState<FundamentalsCoverageItem[]>([]);
  const [selected, setSelected] = useState<TickerSearchResult | null>(null);
  const [activeSymbol, setActiveSymbol] = useState<string | null>(null);
  const [metrics, setMetrics] = useState<Record<string, unknown>[]>([]);
  const [loading, setLoading] = useState(true);
  const [metricsLoading, setMetricsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [msg, setMsg] = useState<string | null>(null);

  const loadCoverage = useCallback(async () => {
    const data = await ingestionApi.listFundamentalsCoverage();
    setCoverage(data.items);
  }, []);

  useEffect(() => {
    Promise.all([ingestionApi.getFundamentalsEntitlement(), loadCoverage()])
      .then(([ent]) => setEntitlement(ent))
      .catch((e) => setError((e as Error).message))
      .finally(() => setLoading(false));
  }, [loadCoverage]);

  const loadMetrics = async (symbol: string) => {
    setMetricsLoading(true);
    setError(null);
    try {
      const data = await ingestionApi.getFundamentals(symbol);
      setMetrics((data.metrics as Record<string, unknown>[]) ?? []);
      setActiveSymbol(symbol);
    } catch (e) {
      setError((e as Error).message);
      setMetrics([]);
    } finally {
      setMetricsLoading(false);
    }
  };

  const handleRowClick = (row: FundamentalsCoverageItem) => {
    loadMetrics(row.symbol);
  };

  const runIngest = async () => {
    if (!selected) return;
    setMsg(null);
    setError(null);
    try {
      const r = await ingestionApi.runFundamentals({ symbols: [selected.symbol] });
      setMsg(`Fundamentals job queued: ${r.job_id}`);
    } catch (e) {
      setError((e as Error).message);
    }
  };

  if (loading) {
    return (
      <div className="flex justify-center py-12">
        <Spinner />
      </div>
    );
  }

  const tier = String(entitlement?.tier ?? 'dow30');
  const addon = Boolean(entitlement?.addon_active);

  return (
    <div className="space-y-4">
      {error && <ErrorAlert message={error} />}
      {msg && <p className="text-brand-500 text-sm">{msg}</p>}

      <div className="bg-amber-900/20 border border-amber-700/50 rounded-lg p-4 text-sm text-amber-100">
        Tier: <strong>{tier}</strong>
        {addon
          ? ' (full add-on active)'
          : ' — Power plan includes DOW 30 only; add-on required for all tickers.'}
      </div>

      <div className="flex flex-wrap gap-2 items-end">
        <TiingoTickerSearch selected={selected} onSelect={setSelected} />
        <button
          type="button"
          onClick={runIngest}
          disabled={!selected}
          className="px-4 py-2 bg-brand-600 rounded-lg text-sm disabled:opacity-50 disabled:cursor-not-allowed"
        >
          Ingest
        </button>
      </div>
      <p className="text-xs text-slate-500">
        To view stored fundamentals, click a row in the table below — no search required.
      </p>

      <section>
        <h3 className="font-semibold text-slate-200 mb-2">Stored fundamentals</h3>
        {coverage.length === 0 ? (
          <p className="text-sm text-slate-500">
            No fundamentals stored yet. Add symbols to the watchlist and run Ingest or wait for
            the scheduled job.
          </p>
        ) : (
          <table className="w-full text-sm bg-surface-900 border border-slate-800 rounded-xl">
            <thead className="text-slate-500">
              <tr>
                <th className="p-2 text-left">Symbol</th>
                <th className="p-2 text-left">Name</th>
                <th className="p-2 text-left">Metrics</th>
                <th className="p-2 text-left">Latest report</th>
                <th className="p-2 text-left">Last ingested</th>
              </tr>
            </thead>
            <tbody>
              {coverage.map((row) => (
                <tr
                  key={row.symbol}
                  onClick={() => handleRowClick(row)}
                  className={`border-t border-slate-800 cursor-pointer transition-colors ${
                    activeSymbol === row.symbol
                      ? 'bg-brand-500/10'
                      : 'hover:bg-slate-800/50'
                  }`}
                >
                  <td className="p-2 font-mono text-brand-400">{row.symbol}</td>
                  <td className="p-2 text-slate-300">{row.name ?? '—'}</td>
                  <td className="p-2">{row.metric_count}</td>
                  <td className="p-2 text-slate-400">{formatDate(row.latest_report_date)}</td>
                  <td className="p-2 text-slate-400">{formatDate(row.last_ingested_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>

      {activeSymbol && (
        <section>
          <h3 className="font-semibold text-slate-200 mb-2">
            Metrics for {activeSymbol}
            {metricsLoading && <span className="ml-2 text-slate-500 text-xs">Loading…</span>}
          </h3>
          <p className="text-xs text-slate-500 mb-2">Showing up to 200 metrics</p>
          <div className="max-h-96 overflow-auto text-xs font-mono bg-surface-900 border border-slate-800 rounded-xl p-3">
            {metrics.length === 0 && !metricsLoading ? (
              <p className="text-slate-500">No metrics for this symbol.</p>
            ) : (
              metrics.slice(0, 50).map((m, i) => (
                <div key={i} className="text-slate-400 py-0.5">
                  {String(m.metric_name)} = {String(m.value)} ({String(m.period ?? '')})
                </div>
              ))
            )}
          </div>
        </section>
      )}
    </div>
  );
}
