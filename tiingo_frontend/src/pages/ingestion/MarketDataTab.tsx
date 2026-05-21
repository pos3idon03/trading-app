import { useState } from 'react';
import { ingestionApi } from '../../api/endpoints';
import type { TickerSearchResult } from '../../api/types';
import TiingoTickerSearch from '../../components/TiingoTickerSearch';
import ErrorAlert from '../../components/ErrorAlert';

export default function MarketDataTab() {
  const [selected, setSelected] = useState<TickerSearchResult | null>(null);
  const [coverage, setCoverage] = useState<Record<string, unknown>[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [msg, setMsg] = useState<string | null>(null);

  const loadCoverage = async () => {
    if (!selected) return;
    setError(null);
    try {
      const data = await ingestionApi.getCoverage(selected.symbol, '1d');
      setCoverage(Array.isArray(data) ? data : []);
    } catch (e) {
      setError((e as Error).message);
    }
  };

  const backfillAll = async () => {
    setMsg(null);
    setError(null);
    try {
      const r = await ingestionApi.backfillOhlcv({
        symbols: [],
        timeframes: ['1d', '5m', '1m', '15m', '30m', '1h'],
        sources: ['tiingo_eod', 'tiingo_iex', 'tiingo_crypto'],
        refresh_corporate_actions: true,
      });
      setMsg(`Backfill job queued: ${r.job_id}`);
    } catch (e) {
      setError((e as Error).message);
    }
  };

  return (
    <div className="space-y-4">
      {error && <ErrorAlert message={error} />}
      {msg && <p className="text-brand-500 text-sm">{msg}</p>}
      <button
        type="button"
        onClick={backfillAll}
        className="px-4 py-2 bg-brand-600 hover:bg-brand-500 rounded-lg text-sm font-medium"
      >
        Backfill All Active (EOD + IEX)
      </button>
      <p className="text-xs text-slate-500">
        Daily EOD bars use split-adjusted prices. Each backfill also refreshes dividend and
        split markers on existing symbols.
      </p>
      <div className="flex flex-wrap gap-2 items-end">
        <TiingoTickerSearch selected={selected} onSelect={setSelected} />
        <button
          type="button"
          onClick={loadCoverage}
          disabled={!selected}
          className="px-3 py-2 border border-slate-700 rounded-lg text-sm disabled:opacity-50 disabled:cursor-not-allowed"
        >
          Coverage
        </button>
      </div>
      {coverage && (
        <table className="w-full text-sm bg-surface-900 border border-slate-800 rounded-xl">
          <thead className="text-slate-500">
            <tr>
              <th className="p-2 text-left">Source</th>
              <th className="p-2 text-left">From</th>
              <th className="p-2 text-left">To</th>
              <th className="p-2 text-left">Bars</th>
            </tr>
          </thead>
          <tbody>
            {coverage.map((row, i) => (
              <tr key={i} className="border-t border-slate-800">
                <td className="p-2">{String(row.source)}</td>
                <td className="p-2 text-slate-400">{String(row.min_time ?? '')}</td>
                <td className="p-2 text-slate-400">{String(row.max_time ?? '')}</td>
                <td className="p-2">{String(row.bar_count ?? '')}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
