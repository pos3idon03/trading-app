import { useCallback, useEffect, useState } from 'react';
import { marketDataApi } from '../api/endpoints';
import type { StockKpiItem } from '../api/types';
import ErrorAlert from './ErrorAlert';
import Spinner from './Spinner';
import { formatKpiValue, groupKpis } from '../utils/stockKpis';

interface StockKpiPanelProps {
  symbol: string;
}

export default function StockKpiPanel({ symbol }: StockKpiPanelProps) {
  const [kpis, setKpis] = useState<StockKpiItem[]>([]);
  const [asOf, setAsOf] = useState<string | null>(null);
  const [price, setPrice] = useState<number | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async (sym: string) => {
    setLoading(true);
    setError(null);
    try {
      const data = await marketDataApi.getKpis(sym);
      setKpis(data.kpis);
      setAsOf(data.as_of);
      setPrice(data.price);
    } catch {
      setKpis([]);
      setAsOf(null);
      setPrice(null);
      setError('Failed to load KPIs.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load(symbol);
  }, [symbol, load]);

  const groups = groupKpis(kpis);

  return (
    <section className="space-y-4 pt-4 border-t border-slate-800">
      <div className="flex flex-wrap items-baseline gap-3">
        <h2 className="text-lg font-semibold text-slate-200">KPIs &amp; Ratios</h2>
        {price != null && (
          <span className="text-sm text-slate-500">
            Last price ${price.toFixed(2)}
            {asOf ? ` · ${new Date(asOf).toLocaleDateString()}` : ''}
          </span>
        )}
      </div>

      {error && <ErrorAlert message={error} />}

      {loading ? (
        <div className="flex justify-center py-6">
          <Spinner />
        </div>
      ) : (
        <div className="space-y-6">
          {groups.map(({ title, items }) => (
            <div key={title} className="space-y-3">
              <h3 className="text-sm font-medium text-slate-400">{title}</h3>
              <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3">
                {items.map((item) => (
                  <div
                    key={item.key}
                    className="bg-surface-900 border border-slate-800 rounded-xl p-4"
                  >
                    <p className="text-xs text-slate-500 uppercase tracking-wide">{item.label}</p>
                    <p className="text-xl font-bold text-slate-100 mt-1">{formatKpiValue(item)}</p>
                  </div>
                ))}
              </div>
            </div>
          ))}
          {!groups.length && !error && (
            <p className="text-sm text-slate-500">No KPI data available for this symbol.</p>
          )}
        </div>
      )}
    </section>
  );
}
