import { useEffect, useRef, useState } from 'react';
import ErrorAlert from '../components/ErrorAlert';
import Spinner from '../components/Spinner';
import { useExecutionActivityLog } from '../hooks/useExecutionActivityLog';
import { useExecutionMonitor } from '../hooks/useExecutionMonitor';
import { useLiveStreamSync } from '../hooks/useLiveStreamSync';
import type { ExecutionLogLine, LogSeverity } from '../utils/executionActivityLog';

const SEVERITY_COLORS: Record<LogSeverity, string> = {
  info: 'text-slate-300',
  warn: 'text-amber-400',
  success: 'text-green-400',
  error: 'text-red-400',
};

const LIVE_POLL_MAX_MS = 60_000;

function formatLogTimestamp(iso: string): string {
  try {
    return new Date(iso).toLocaleTimeString(undefined, { hour12: false });
  } catch {
    return iso;
  }
}

function LogLine({ line }: { line: ExecutionLogLine }) {
  const color = SEVERITY_COLORS[line.severity ?? 'info'];
  return (
    <div className="flex gap-2 leading-relaxed">
      <span className="text-slate-600 shrink-0">[{formatLogTimestamp(line.tsISO)}]</span>
      <span className="text-brand-400 shrink-0">{line.symbol}</span>
      <span className={color}>{line.text}</span>
    </div>
  );
}

function EmptyMonitor() {
  return (
    <div className="card text-center py-12">
      <p className="text-slate-400 text-sm">No auto-trading assets are currently running.</p>
      <p className="text-slate-600 text-xs mt-1">
        Start an asset from the Auto-Trading page to see live activity here.
      </p>
    </div>
  );
}

function hasCryptoSymbol(symbols: string[]): boolean {
  return symbols.some((s) => s.includes('-') && /-(USD|USDT|USDC)$/i.test(s));
}

function StreamStatusBar({
  connected,
  stockConnected,
  cryptoConnected,
  starting,
  streamSymbols,
  error,
}: {
  connected: boolean;
  stockConnected: boolean;
  cryptoConnected: boolean;
  starting: boolean;
  streamSymbols: string[];
  error: string | null;
}) {
  if (starting) {
    return (
      <span className="text-xs text-amber-400" data-testid="stream-status">
        Stream: connecting…
      </span>
    );
  }
  const wantsCrypto = hasCryptoSymbol(streamSymbols);
  const cryptoDown = wantsCrypto && !cryptoConnected;
  const stocksDown = streamSymbols.some((s) => !s.includes('-')) && !stockConnected;

  if (connected && streamSymbols.length > 0) {
    const color = cryptoDown || stocksDown ? 'text-amber-400' : 'text-green-400';
    const detail =
      cryptoDown && stockConnected
        ? ' — crypto feed down, using DB for BTC'
        : stocksDown && cryptoConnected
          ? ' — stock feed down'
          : '';
    return (
      <span className={`text-xs ${color}`} data-testid="stream-status">
        Stream: {cryptoDown || stocksDown ? 'partial' : 'connected'} ({streamSymbols.join(', ')})
        {detail}
      </span>
    );
  }
  if (error) {
    return (
      <span className="text-xs text-red-400" data-testid="stream-status">
        Stream: error — {error}
      </span>
    );
  }
  return (
    <span className="text-xs text-slate-500" data-testid="stream-status">
      Stream: off (prices from DB until Alpaca connects)
    </span>
  );
}

function ActivityTerminal({
  lines,
  symbolFilter,
}: {
  lines: ExecutionLogLine[];
  symbolFilter: string;
}) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const stickToBottomRef = useRef(true);

  const filtered =
    symbolFilter === 'ALL'
      ? lines
      : lines.filter((l) => l.symbol === symbolFilter || l.symbol === 'SYSTEM');

  useEffect(() => {
    const el = scrollRef.current;
    if (!el || !stickToBottomRef.current) return;
    el.scrollTop = el.scrollHeight;
  }, [filtered]);

  const onScroll = () => {
    const el = scrollRef.current;
    if (!el) return;
    const atBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 48;
    stickToBottomRef.current = atBottom;
  };

  return (
    <div
      ref={scrollRef}
      onScroll={onScroll}
      className="bg-surface-950 border border-slate-800 rounded-lg p-4 h-[min(70vh,640px)] overflow-y-auto font-mono text-xs"
      data-testid="activity-terminal"
    >
      {filtered.length === 0 ? (
        <p className="text-slate-600">Waiting for activity…</p>
      ) : (
        <div className="space-y-1">
          {filtered.map((line) => (
            <LogLine key={line.id} line={line} />
          ))}
        </div>
      )}
    </div>
  );
}

export default function LiveTradingPage() {
  const { monitors, assetsLoading, assetsError, refreshAll } = useExecutionMonitor({
    livePollMaxIntervalMs: LIVE_POLL_MAX_MS,
  });

  const logCallbacksRef = useRef<{
    append?: (text: string, severity?: 'info' | 'warn' | 'error') => void;
  }>({});

  const { streamStatus, streamStarting, streamSymbols } = useLiveStreamSync(monitors, {
    onStreamEvent: (text, severity) => {
      logCallbacksRef.current.append?.(text, severity);
    },
  });

  const { lines, clear, paused, togglePaused, appendSystemLine } = useExecutionActivityLog(
    monitors,
    {
      logPollEvaluations: true,
      streamStatus,
    },
  );

  logCallbacksRef.current.append = appendSystemLine;

  const [symbolFilter, setSymbolFilter] = useState('ALL');
  const symbols = [...new Set(monitors.map((m) => m.symbol))].sort();

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-100">Live Trading</h1>
        <p className="text-slate-400 text-sm mt-1">
          Terminal log of auto-trading activity: prices, criteria, strategy signals, and orders
          for assets with auto-trading started (same data as the Execution monitor).
        </p>
        <p className="text-slate-600 text-xs mt-1">
          Full evaluation block every 60s per asset. Criteria refresh with the asset list (~30s).
          Alpaca stream starts automatically on the backend when auto-trading is running.
        </p>
      </div>

      {assetsError && <ErrorAlert message={assetsError} />}

      <div className="card">
        <div className="flex flex-wrap items-center gap-3 mb-4">
          <button
            type="button"
            onClick={() => refreshAll()}
            className="px-3 py-2 rounded-lg text-sm bg-surface-800 text-slate-300 hover:bg-surface-700"
          >
            Refresh
          </button>
          <button
            type="button"
            onClick={clear}
            className="px-3 py-2 rounded-lg text-sm bg-surface-800 text-slate-300 hover:bg-surface-700"
          >
            Clear log
          </button>
          <button
            type="button"
            onClick={togglePaused}
            className={`px-3 py-2 rounded-lg text-sm border ${
              paused
                ? 'bg-amber-500/20 text-amber-300 border-amber-500/40'
                : 'bg-surface-800 text-slate-300 border-slate-700 hover:bg-surface-700'
            }`}
          >
            {paused ? 'Resume logging' : 'Pause logging'}
          </button>

          <StreamStatusBar
            connected={streamStatus?.connected ?? false}
            stockConnected={streamStatus?.stock_connected ?? false}
            cryptoConnected={streamStatus?.crypto_connected ?? false}
            starting={streamStarting}
            streamSymbols={streamSymbols}
            error={streamStatus?.error ?? null}
          />

          {symbols.length > 0 && (
            <div className="flex items-center gap-2 ml-auto">
              <label htmlFor="symbol-filter" className="text-xs text-slate-500">
                Symbol
              </label>
              <select
                id="symbol-filter"
                className="bg-surface-900 border border-slate-600 rounded-lg px-3 py-2 text-sm text-slate-100"
                value={symbolFilter}
                onChange={(e) => setSymbolFilter(e.target.value)}
              >
                <option value="ALL">All</option>
                {symbols.map((sym) => (
                  <option key={sym} value={sym}>
                    {sym}
                  </option>
                ))}
              </select>
            </div>
          )}

          {monitors.length > 0 && (
            <span className="text-xs text-slate-500 w-full sm:w-auto">
              {monitors.length} asset{monitors.length !== 1 ? 's' : ''} running
              {paused ? ' · logging paused' : ''}
            </span>
          )}
        </div>

        {assetsLoading ? (
          <div className="flex justify-center py-12">
            <Spinner />
          </div>
        ) : monitors.length === 0 ? (
          <EmptyMonitor />
        ) : (
          <ActivityTerminal lines={lines} symbolFilter={symbolFilter} />
        )}
      </div>
    </div>
  );
}
