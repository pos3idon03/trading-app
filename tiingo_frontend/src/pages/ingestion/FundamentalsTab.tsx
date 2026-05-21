import { useEffect, useState } from 'react';
import { ingestionApi } from '../../api/endpoints';
import type { TickerSearchResult } from '../../api/types';
import TiingoTickerSearch from '../../components/TiingoTickerSearch';
import Spinner from '../../components/Spinner';

export default function FundamentalsTab() {
  const [entitlement, setEntitlement] = useState<Record<string, unknown> | null>(null);
  const [selected, setSelected] = useState<TickerSearchResult | null>(null);
  const [metrics, setMetrics] = useState<Record<string, unknown>[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    ingestionApi.getFundamentalsEntitlement().then(setEntitlement).finally(() => setLoading(false));
  }, []);

  const runIngest = async () => {
    if (!selected) return;
    await ingestionApi.runFundamentals({ symbols: [selected.symbol] });
    alert('Fundamentals job queued');
  };

  const loadMetrics = async () => {
    if (!selected) return;
    const data = await ingestionApi.getFundamentals(selected.symbol);
    setMetrics((data.metrics as Record<string, unknown>[]) ?? []);
  };

  if (loading) return <div className="flex justify-center py-12"><Spinner /></div>;

  const tier = String(entitlement?.tier ?? 'dow30');
  const addon = Boolean(entitlement?.addon_active);

  return (
    <div className="space-y-4">
      <div className="bg-amber-900/20 border border-amber-700/50 rounded-lg p-4 text-sm text-amber-100">
        Tier: <strong>{tier}</strong>
        {addon ? ' (full add-on active)' : ' — Power plan includes DOW 30 only; add-on required for all tickers.'}
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
        <button
          type="button"
          onClick={loadMetrics}
          disabled={!selected}
          className="px-4 py-2 border border-slate-700 rounded-lg text-sm disabled:opacity-50 disabled:cursor-not-allowed"
        >
          View Stored
        </button>
      </div>
      <p className="text-xs text-slate-500">Showing up to 200 metrics</p>
      <div className="max-h-96 overflow-auto text-xs font-mono bg-surface-900 border border-slate-800 rounded-xl p-3">
        {metrics.slice(0, 50).map((m, i) => (
          <div key={i} className="text-slate-400 py-0.5">
            {String(m.metric_name)} = {String(m.value)} ({String(m.period ?? '')})
          </div>
        ))}
      </div>
    </div>
  );
}
