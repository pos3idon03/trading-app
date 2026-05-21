import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { ingestionApi } from '../../api/endpoints';
import type { MacroSeries } from '../../api/types';
import Spinner from '../../components/Spinner';
import Toast from '../../components/Toast';

const CATEGORIES = ['inflation', 'labor', 'rates', 'housing', 'energy', 'goods'];

type ToastState = { message: string; variant: 'success' | 'error' };

export default function FredMacroTab() {
  const [series, setSeries] = useState<MacroSeries[]>([]);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [obs, setObs] = useState<{ obs_date: string; value: number }[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState('all');
  const [busy, setBusy] = useState(false);
  const [toast, setToast] = useState<ToastState | null>(null);

  const loadSeries = () =>
    ingestionApi.listMacroSeries().then(setSeries).finally(() => setLoading(false));

  useEffect(() => {
    loadSeries();
  }, []);

  const filtered = filter === 'all' ? series : series.filter((s) => s.category === filter);

  const toggle = (id: string) => {
    const next = new Set(selected);
    if (next.has(id)) next.delete(id);
    else next.add(id);
    setSelected(next);
  };

  const queueJob = async (label: string, run: () => Promise<{ job_id: string }>) => {
    setBusy(true);
    setToast(null);
    try {
      const { job_id } = await run();
      setToast({
        message: `${label} queued (job ${job_id.slice(0, 8)}…). Track progress in the Jobs tab.`,
        variant: 'success',
      });
    } catch (e) {
      setToast({ message: (e as Error).message, variant: 'error' });
    } finally {
      setBusy(false);
    }
  };

  const backfillSelected = () => {
    if (selected.size === 0) return;
    return queueJob('Macro backfill', () =>
      ingestionApi.macroBackfill([...selected]),
    );
  };

  const refreshAll = () => queueJob('Macro refresh', () => ingestionApi.macroRefresh());

  const seedCatalog = () => queueJob('Catalog seed', () => ingestionApi.macroSeedCatalog());

  const viewObs = async (id: string) => {
    const data = await ingestionApi.macroObservations(id);
    setObs((data.observations as { obs_date: string; value: number }[]) ?? []);
  };

  if (loading) return <div className="flex justify-center py-12"><Spinner /></div>;

  return (
    <div className="space-y-4">
      {toast && (
        <Toast
          message={toast.message}
          variant={toast.variant}
          onDismiss={() => setToast(null)}
        />
      )}
      <p className="text-xs text-slate-500">
        FRED backfill, refresh, and catalog seed run as background jobs via the ARQ worker.{' '}
        <Link to="/ingestion/jobs" className="text-brand-500 hover:text-brand-400">
          View jobs
        </Link>
      </p>
      <div className="flex flex-wrap gap-2">
        <button
          type="button"
          onClick={backfillSelected}
          disabled={busy || selected.size === 0}
          className="px-4 py-2 bg-brand-600 rounded-lg text-sm disabled:opacity-50"
        >
          Backfill Selected
        </button>
        <button
          type="button"
          onClick={refreshAll}
          disabled={busy}
          className="px-4 py-2 border border-slate-700 rounded-lg text-sm disabled:opacity-50"
        >
          Refresh Enabled
        </button>
        <button
          type="button"
          onClick={seedCatalog}
          disabled={busy}
          className="px-4 py-2 border border-slate-700 rounded-lg text-sm disabled:opacity-50"
        >
          Seed Catalog
        </button>
      </div>
      <div className="flex gap-2 flex-wrap">
        <button type="button" onClick={() => setFilter('all')} className="text-xs px-2 py-1 rounded bg-surface-800">All</button>
        {CATEGORIES.map((c) => (
          <button key={c} type="button" onClick={() => setFilter(c)} className="text-xs px-2 py-1 rounded bg-surface-800 capitalize">
            {c}
          </button>
        ))}
      </div>
      <div className="grid md:grid-cols-2 gap-4">
        <ul className="bg-surface-900 border border-slate-800 rounded-xl max-h-80 overflow-auto text-sm">
          {filtered.map((s) => (
            <li key={s.series_id} className="flex items-center gap-2 p-2 border-b border-slate-800">
              <input type="checkbox" checked={selected.has(s.series_id)} onChange={() => toggle(s.series_id)} />
              <button type="button" className="text-left flex-1 hover:text-brand-500" onClick={() => viewObs(s.series_id)}>
                <span className="font-mono text-slate-300">{s.series_id}</span>
                <span className="text-slate-500 ml-2">{s.title}</span>
              </button>
            </li>
          ))}
        </ul>
        <div className="bg-surface-900 border border-slate-800 rounded-xl p-3 max-h-80 overflow-auto text-xs font-mono">
          {obs.map((o) => (
            <div key={o.obs_date} className="text-slate-400">{o.obs_date}: {o.value}</div>
          ))}
        </div>
      </div>
    </div>
  );
}
