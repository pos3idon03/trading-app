import { useCallback, useEffect, useState } from 'react';
import { ingestionApi } from '../../api/endpoints';
import type { Instrument, TickerSearchResult } from '../../api/types';
import TiingoTickerSearch from '../../components/TiingoTickerSearch';
import Spinner from '../../components/Spinner';
import ErrorAlert from '../../components/ErrorAlert';

export default function WatchlistTab() {
  const [instruments, setInstruments] = useState<Instrument[]>([]);
  const [selected, setSelected] = useState<TickerSearchResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      setInstruments(await ingestionApi.listInstruments());
      setError(null);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const handleAdd = async () => {
    if (!selected) return;
    setBusy('add');
    try {
      await ingestionApi.createInstrument({
        symbol: selected.symbol,
        asset_type: selected.asset_type,
        name: selected.name,
        exchange: selected.exchange,
        tiingo_ticker: selected.tiingo_ticker ?? selected.symbol,
      });
      setSelected(null);
      await load();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(null);
    }
  };

  const toggleActive = async (inst: Instrument) => {
    setBusy(inst.symbol);
    await ingestionApi.patchInstrument(inst.symbol, { is_active: !inst.is_active });
    await load();
    setBusy(null);
  };

  const handleBackfill = async (sym: string) => {
    setBusy(`bf-${sym}`);
    await ingestionApi.backfillOhlcv({
      symbols: [sym],
      timeframes: ['1d', '5m'],
      sources: ['tiingo_eod', 'tiingo_iex', 'tiingo_crypto'],
    });
    setBusy(null);
  };

  if (loading) return <div className="flex justify-center py-12"><Spinner /></div>;

  const excludeSymbols = instruments.map((i) => i.symbol);

  return (
    <div className="space-y-4">
      {error && <ErrorAlert message={error} />}
      <div className="flex flex-wrap gap-2 items-end">
        <TiingoTickerSearch
          selected={selected}
          onSelect={setSelected}
          excludeSymbols={excludeSymbols}
        />
        <button
          type="button"
          onClick={handleAdd}
          disabled={busy === 'add' || !selected}
          className="px-4 py-2 bg-brand-600 hover:bg-brand-500 rounded-lg text-sm font-medium disabled:opacity-50 disabled:cursor-not-allowed"
        >
          Add to Watchlist
        </button>
      </div>
      <p className="text-xs text-slate-500">
        Search by company name or ticker, then select from the dropdown. Manual ticker entry is not allowed.
      </p>

      <table className="w-full text-sm bg-surface-900 border border-slate-800 rounded-xl overflow-hidden">
        <thead className="bg-surface-800 text-slate-400">
          <tr>
            <th className="text-left p-3">Symbol</th>
            <th className="text-left p-3">Name</th>
            <th className="text-left p-3">Type</th>
            <th className="text-left p-3">Active</th>
            <th className="text-left p-3">Actions</th>
          </tr>
        </thead>
        <tbody>
          {instruments.map((i) => (
            <tr key={i.symbol} className="border-t border-slate-800">
              <td className="p-3 font-mono">{i.symbol}</td>
              <td className="p-3 text-slate-400">{i.name ?? '—'}</td>
              <td className="p-3 text-slate-400">{i.asset_type}</td>
              <td className="p-3">
                <button type="button" onClick={() => toggleActive(i)} className="text-brand-500">
                  {i.is_active ? 'Yes' : 'No'}
                </button>
              </td>
              <td className="p-3">
                <button
                  type="button"
                  onClick={() => handleBackfill(i.symbol)}
                  disabled={!!busy}
                  className="text-xs text-slate-300 hover:text-white underline"
                >
                  Backfill
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
