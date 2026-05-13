import { useCallback, useEffect, useRef, useState } from 'react';
import { dataApi, liveApi } from '../api/endpoints';
import type {
  AssetItem,
  IndicatorSnapshotResponse,
  StrategySignalsResponse,
  StreamStatusResponse,
} from '../api/types';
import LiveStreamCard from '../components/LiveStreamCard';
import ErrorAlert from '../components/ErrorAlert';
import Spinner from '../components/Spinner';

const POLL_INTERVAL_MS = 5000;

interface StreamState {
  indicators: IndicatorSnapshotResponse | null;
  strategySignals: StrategySignalsResponse | null;
}

async function fetchStreamData(
  symbol: string,
  indicatorTimeframe: string,
): Promise<Partial<StreamState>> {
  const [ind, sig] = await Promise.allSettled([
    liveApi.getIndicators(symbol, indicatorTimeframe),
    liveApi.getStrategySignals(symbol, '1h'),
  ]);
  return {
    ...(ind.status === 'fulfilled' ? { indicators: ind.value } : {}),
    ...(sig.status === 'fulfilled' ? { strategySignals: sig.value } : {}),
  };
}

function useSymbolPolling(
  symbols: string[],
  indicatorTimeframe: string,
  onUpdate: (symbol: string, patch: Partial<StreamState>) => void,
) {
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const symbolsKey = symbols.join(',');

  useEffect(() => {
    if (pollRef.current) clearInterval(pollRef.current);
    if (symbols.length === 0) return;

    const poll = () => {
      symbols.forEach(async (sym) => {
        const patch = await fetchStreamData(sym, indicatorTimeframe);
        onUpdate(sym, patch);
      });
    };

    poll();
    pollRef.current = setInterval(poll, POLL_INTERVAL_MS);
    return () => { if (pollRef.current) clearInterval(pollRef.current); };
  }, [symbolsKey, indicatorTimeframe]); // eslint-disable-line react-hooks/exhaustive-deps
}

const TIMEFRAMES = ['30m', '1h', '4h', '1d'];

export default function LiveTradingPage() {
  const [assets, setAssets] = useState<AssetItem[]>([]);
  const [assetsLoading, setAssetsLoading] = useState(true);
  const [selectedSymbol, setSelectedSymbol] = useState('');
  const [indicatorTimeframe, setIndicatorTimeframe] = useState('1h');

  const [streams, setStreams] = useState<Map<string, StreamState>>(new Map<string, StreamState>());
  const [streamStatus, setStreamStatus] = useState<StreamStatusResponse | null>(null);
  const [running, setRunning] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const activeSymbols: string[] = [...streams.keys()];

  useEffect(() => {
    liveApi.getStatus().then(setStreamStatus).catch(() => {});
    dataApi.getAssets()
      .then((res: { assets: AssetItem[]; count: number }) => {
        const active = res.assets.filter((a) => a.is_active);
        setAssets(active);
        if (active.length > 0) setSelectedSymbol(active[0].symbol);
      })
      .catch(() => setError('Failed to load available tickers.'))
      .finally(() => setAssetsLoading(false));
  }, []);

  const updateStream = useCallback((symbol: string, patch: Partial<StreamState>) => {
    setStreams((prev: Map<string, StreamState>) => {
      const next = new Map<string, StreamState>(prev);
      const current = next.get(symbol) ?? { indicators: null, strategySignals: null };
      next.set(symbol, { ...current, ...patch });
      return next;
    });
  }, []);

  useSymbolPolling(activeSymbols, indicatorTimeframe, updateStream);

  const addStream = (symbol: string) => {
    if (!symbol || streams.has(symbol)) return;
    setStreams((prev: Map<string, StreamState>) => {
      const next = new Map<string, StreamState>(prev);
      next.set(symbol, { indicators: null, strategySignals: null });
      return next;
    });
  };

  const removeStream = (symbol: string) => {
    setStreams((prev: Map<string, StreamState>) => {
      const next = new Map<string, StreamState>(prev);
      next.delete(symbol);
      return next;
    });
  };

  const startAll = async () => {
    if (activeSymbols.length === 0) return;
    setLoading(true);
    setError(null);
    try {
      const status = await liveApi.startStream({ symbols: activeSymbols });
      setStreamStatus(status);
      setRunning(true);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setLoading(false);
    }
  };

  const stopAll = async () => {
    setRunning(false);
    try {
      const status = await liveApi.stopStream();
      setStreamStatus(status);
    } catch (err) {
      setError((err as Error).message);
    }
  };

  const handleAddStream = () => addStream(selectedSymbol);

  const connected = streamStatus?.connected ?? false;
  const availableToAdd = assets.filter((a: AssetItem) => !streams.has(a.symbol));

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-100">Live Trading</h1>
        <p className="text-slate-400 text-sm mt-1">
          Add symbols to monitor stored indicators immediately. Click "Start All" to begin the
          live Alpaca stream and accumulate real-time bars for strategy signals.
        </p>
      </div>

      {error && <ErrorAlert message={error} />}

      {/* Control panel */}
      <div className="card">
        <h2 className="text-slate-200 font-semibold mb-4">Stream Control</h2>
        <div className="flex flex-wrap gap-4 items-end">
          <div>
            <label className="metric-label block mb-1">Add Symbol</label>
            {assetsLoading ? (
              <div className="w-48 h-9 bg-surface-900 border border-slate-600 rounded-lg animate-pulse" />
            ) : availableToAdd.length === 0 && streams.size > 0 ? (
              <p className="text-slate-500 text-xs py-2">All tickers added.</p>
            ) : assets.length === 0 ? (
              <p className="text-slate-500 text-xs py-2">No tickers ingested yet.</p>
            ) : (
              <select
                className="bg-surface-900 border border-slate-600 rounded-lg px-3 py-2 text-sm text-slate-100 focus:outline-none focus:border-brand-500 w-48"
                value={selectedSymbol}
                onChange={(e) => setSelectedSymbol(e.target.value)}
              >
                {availableToAdd.map((a) => (
                  <option key={a.symbol} value={a.symbol}>{a.symbol}</option>
                ))}
              </select>
            )}
          </div>

          <div>
            <label className="metric-label block mb-1">Indicator Timeframe</label>
            <select
              className="bg-surface-900 border border-slate-600 rounded-lg px-3 py-2 text-sm text-slate-100 focus:outline-none focus:border-brand-500"
              value={indicatorTimeframe}
              onChange={(e) => setIndicatorTimeframe(e.target.value)}
            >
              {TIMEFRAMES.map((tf) => <option key={tf} value={tf}>{tf}</option>)}
            </select>
          </div>

          <button
            onClick={handleAddStream}
            disabled={!selectedSymbol || availableToAdd.length === 0}
            className="btn-primary disabled:opacity-50"
          >
            + Add Stream
          </button>

          {!running ? (
            <button
              onClick={startAll}
              disabled={loading || activeSymbols.length === 0}
              className="btn-primary disabled:opacity-50"
              title="Start the live Alpaca stream to accumulate real-time bars and compute strategy signals"
            >
              {loading ? 'Connecting…' : 'Start Live Stream'}
            </button>
          ) : (
            <button
              onClick={stopAll}
              className="px-4 py-2 rounded-lg text-sm font-medium bg-red-500/20 text-red-400 border border-red-500/40 hover:bg-red-500/30"
            >
              Stop Stream
            </button>
          )}
        </div>

        {/* Status bar */}
        <div className="mt-4 flex flex-wrap items-center gap-4 text-xs">
          <span className="flex items-center gap-1.5">
            <span className={`h-2 w-2 rounded-full ${connected ? 'bg-green-500 animate-pulse' : 'bg-slate-600'}`} />
            <span className="text-slate-400">{connected ? 'Live stream connected' : 'Live stream disconnected'}</span>
          </span>
          {activeSymbols.length > 0 && (
            <span className="text-slate-500">Monitoring: {activeSymbols.join(', ')}</span>
          )}
          {streamStatus?.last_tick_at && (
            <span className="text-slate-500">Last tick: {new Date(streamStatus.last_tick_at).toLocaleTimeString()}</span>
          )}
          {streamStatus?.error && (
            <span className="text-red-400 font-mono">Stream error: {streamStatus.error}</span>
          )}
        </div>
      </div>

      {loading && <Spinner label="Connecting to Alpaca WebSocket stream…" />}

      {/* Stream cards grid */}
      {streams.size > 0 ? (
        <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
          {[...streams.entries()].map(([symbol, state]: [string, StreamState]) => (
            <LiveStreamCard
              key={symbol}
              symbol={symbol}
              indicators={state.indicators}
              strategySignals={state.strategySignals}
              streamRunning={running}
              onRemove={removeStream}
            />
          ))}
        </div>
      ) : (
        <div className="card text-center py-12">
          <p className="text-slate-500 text-sm">
            Add a symbol above to see its stored indicators. Click "Start Live Stream" to begin
            real-time data accumulation for strategy signals.
          </p>
        </div>
      )}
    </div>
  );
}
