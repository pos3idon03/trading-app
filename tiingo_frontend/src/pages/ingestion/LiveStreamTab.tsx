import { useEffect, useState } from 'react';
import { ingestionApi } from '../../api/endpoints';
import Spinner from '../../components/Spinner';

export default function LiveStreamTab() {
  const [status, setStatus] = useState<Record<string, unknown> | null>(null);
  const [loading, setLoading] = useState(true);

  const refresh = async () => {
    setStatus(await ingestionApi.streamStatus());
    setLoading(false);
  };

  useEffect(() => {
    refresh();
    const t = setInterval(refresh, 10_000);
    return () => clearInterval(t);
  }, []);

  if (loading) return <div className="flex justify-center py-12"><Spinner /></div>;

  const running = Boolean(status?.running);
  const symbols = (status?.symbols as string[]) ?? [];
  const lastBars = (status?.last_bar_time as Record<string, string>) ?? {};

  return (
    <div className="space-y-4">
      <p className="text-slate-400 text-sm">
        1-minute IEX websocket stream for active stock watchlist symbols.
      </p>
      <div className="flex gap-2">
        <button
          type="button"
          onClick={async () => { await ingestionApi.streamStart([]); await refresh(); }}
          className="px-4 py-2 bg-brand-600 rounded-lg text-sm"
        >
          Start Stream
        </button>
        <button
          type="button"
          onClick={async () => { await ingestionApi.streamStop(); await refresh(); }}
          className="px-4 py-2 border border-slate-700 rounded-lg text-sm"
        >
          Stop Stream
        </button>
      </div>
      <div className="bg-surface-900 border border-slate-800 rounded-xl p-4">
        <p className="font-medium">Status: {running ? 'Running' : 'Stopped'}</p>
        <p className="text-sm text-slate-400 mt-2">Subscribed: {symbols.join(', ') || 'none'}</p>
        <ul className="mt-4 text-sm space-y-1">
          {Object.entries(lastBars).map(([sym, t]) => (
            <li key={sym} className="font-mono text-slate-300">{sym}: {t}</li>
          ))}
        </ul>
      </div>
    </div>
  );
}
