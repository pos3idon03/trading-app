import { useCallback, useEffect, useState } from 'react';
import { ingestionApi } from '../../api/endpoints';
import type { Instrument, TickerSearchResult } from '../../api/types';
import ConfirmModal from '../../components/ConfirmModal';
import TiingoTickerSearch from '../../components/TiingoTickerSearch';
import Spinner from '../../components/Spinner';
import ErrorAlert from '../../components/ErrorAlert';
import Toast from '../../components/Toast';
import {
  backfillStartedMessage,
  deleteConfirmMessage,
  deleteSuccessMessage,
} from '../../utils/watchlistMessages';

type ToastState = { message: string; variant: 'success' | 'error' };

export default function WatchlistTab() {
  const [instruments, setInstruments] = useState<Instrument[]>([]);
  const [selected, setSelected] = useState<TickerSearchResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [confirmDelete, setConfirmDelete] = useState<Instrument | null>(null);
  const [toast, setToast] = useState<ToastState | null>(null);

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
    try {
      await ingestionApi.patchInstrument(inst.symbol, { is_active: !inst.is_active });
      await load();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(null);
    }
  };

  const handleBackfill = async (sym: string) => {
    setBusy(`bf-${sym}`);
    setError(null);
    try {
      await ingestionApi.backfillOhlcv({
        symbols: [sym],
        timeframes: ['1d', '5m', '1m', '15m', '30m', '1h'],
        sources: ['tiingo_eod', 'tiingo_iex', 'tiingo_crypto'],
      });
      setToast({ message: backfillStartedMessage(sym), variant: 'success' });
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(null);
    }
  };

  const handleDeleteConfirm = async () => {
    if (!confirmDelete) return;
    const sym = confirmDelete.symbol;
    setBusy(`del-${sym}`);
    setError(null);
    try {
      await ingestionApi.deleteInstrument(sym);
      setConfirmDelete(null);
      await load();
      setToast({ message: deleteSuccessMessage(sym), variant: 'success' });
    } catch (e) {
      setToast({ message: (e as Error).message, variant: 'error' });
    } finally {
      setBusy(null);
    }
  };

  if (loading) return <div className="flex justify-center py-12"><Spinner /></div>;

  const excludeSymbols = instruments.map((i) => i.symbol);

  return (
    <div className="space-y-4">
      {error && <ErrorAlert message={error} />}
      {toast && (
        <Toast
          message={toast.message}
          variant={toast.variant}
          onDismiss={() => setToast(null)}
        />
      )}
      <ConfirmModal
        open={confirmDelete !== null}
        title="Delete instrument?"
        message={confirmDelete ? deleteConfirmMessage(confirmDelete.symbol) : ''}
        confirmLabel="Yes"
        cancelLabel="No"
        busy={confirmDelete !== null && busy === `del-${confirmDelete.symbol}`}
        onConfirm={handleDeleteConfirm}
        onCancel={() => setConfirmDelete(null)}
      />
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
                <div className="flex gap-3">
                  <button
                    type="button"
                    onClick={() => handleBackfill(i.symbol)}
                    disabled={!!busy}
                    className="text-xs text-slate-300 hover:text-white underline disabled:opacity-50"
                  >
                    Backfill
                  </button>
                  <button
                    type="button"
                    onClick={() => setConfirmDelete(i)}
                    disabled={!!busy}
                    className="text-xs text-red-400 hover:text-red-300 underline disabled:opacity-50"
                  >
                    Delete
                  </button>
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
