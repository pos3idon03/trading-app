import { useEffect, useRef, useState } from 'react';
import { liveApi } from '../api/endpoints';
import type {
  IndicatorSnapshotResponse,
  StreamStatusResponse,
  TradingSignalItem,
} from '../api/types';
import ErrorAlert from '../components/ErrorAlert';
import Spinner from '../components/Spinner';

const TIMEFRAMES = ['30m', '1h', '4h', '1d'];

function IndicatorGauge({ label, value, min, max, unit }: {
  label: string; value: number | null; min: number; max: number; unit?: string;
}) {
  const pct = value !== null ? Math.min(100, Math.max(0, ((value - min) / (max - min)) * 100)) : 0;
  const color = pct > 70 ? 'bg-red-500' : pct < 30 ? 'bg-green-500' : 'bg-yellow-500';

  return (
    <div className="space-y-1">
      <div className="flex justify-between text-xs">
        <span className="text-slate-400">{label}</span>
        <span className="text-slate-200 font-mono">
          {value !== null ? value.toFixed(2) : '—'}{unit ?? ''}
        </span>
      </div>
      <div className="h-1.5 bg-slate-700 rounded-full overflow-hidden">
        <div className={`h-full rounded-full transition-all duration-500 ${color}`} style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}

function MACDDisplay({ macd, signal, histogram }: {
  macd: number | null; signal: number | null; histogram: number | null;
}) {
  const histColor = histogram !== null && histogram > 0 ? 'text-green-400' : 'text-red-400';
  return (
    <div className="space-y-2">
      <h4 className="text-slate-400 text-xs uppercase tracking-wide">MACD</h4>
      <div className="grid grid-cols-3 gap-2 text-center">
        <div>
          <span className="text-slate-500 text-xs">Line</span>
          <p className="text-slate-200 font-mono text-sm">{macd?.toFixed(4) ?? '—'}</p>
        </div>
        <div>
          <span className="text-slate-500 text-xs">Signal</span>
          <p className="text-slate-200 font-mono text-sm">{signal?.toFixed(4) ?? '—'}</p>
        </div>
        <div>
          <span className="text-slate-500 text-xs">Histogram</span>
          <p className={`font-mono text-sm font-semibold ${histColor}`}>
            {histogram?.toFixed(4) ?? '—'}
          </p>
        </div>
      </div>
    </div>
  );
}

function BollingerDisplay({ upper, middle, lower, price, bbPct }: {
  upper: number | null; middle: number | null; lower: number | null;
  price: number; bbPct: number | null;
}) {
  return (
    <div className="space-y-2">
      <h4 className="text-slate-400 text-xs uppercase tracking-wide">Bollinger Bands</h4>
      <div className="grid grid-cols-4 gap-2 text-center">
        <div>
          <span className="text-slate-500 text-xs">Upper</span>
          <p className="text-red-400 font-mono text-sm">{upper?.toFixed(2) ?? '—'}</p>
        </div>
        <div>
          <span className="text-slate-500 text-xs">Middle</span>
          <p className="text-slate-300 font-mono text-sm">{middle?.toFixed(2) ?? '—'}</p>
        </div>
        <div>
          <span className="text-slate-500 text-xs">Lower</span>
          <p className="text-green-400 font-mono text-sm">{lower?.toFixed(2) ?? '—'}</p>
        </div>
        <div>
          <span className="text-slate-500 text-xs">%B</span>
          <p className="text-slate-200 font-mono text-sm">{bbPct?.toFixed(2) ?? '—'}</p>
        </div>
      </div>
      <div className="relative h-2 bg-slate-700 rounded-full overflow-hidden">
        {bbPct !== null && (
          <div
            className="absolute h-full w-1.5 bg-brand-500 rounded-full"
            style={{ left: `${Math.min(100, Math.max(0, bbPct * 100))}%`, transform: 'translateX(-50%)' }}
          />
        )}
      </div>
      <div className="flex justify-between text-xs text-slate-500">
        <span>Oversold</span>
        <span>Price: {price.toFixed(2)}</span>
        <span>Overbought</span>
      </div>
    </div>
  );
}

function SignalBadge({ action, confidence }: { action: string; confidence: number }) {
  const styles: Record<string, string> = {
    BUY: 'bg-green-500/20 text-green-400 border-green-500/40',
    SELL: 'bg-red-500/20 text-red-400 border-red-500/40',
    HOLD: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/40',
  };
  const s = styles[action] ?? styles.HOLD;
  return (
    <div className="flex items-center gap-3">
      <span className={`px-4 py-2 rounded-lg text-lg font-bold uppercase tracking-wide border ${s}`}>
        {action}
      </span>
      <span className="text-slate-400 text-sm">
        Confidence: <span className="text-slate-200 font-mono">{(confidence * 100).toFixed(1)}%</span>
      </span>
    </div>
  );
}

function SignalScoreBar({ label, score }: { label: string; score: number }) {
  const pct = ((score + 1) / 2) * 100;
  const color = score > 0.2 ? 'bg-green-500' : score < -0.2 ? 'bg-red-500' : 'bg-yellow-500';
  return (
    <div className="space-y-1">
      <div className="flex justify-between text-xs">
        <span className="text-slate-400">{label}</span>
        <span className="text-slate-200 font-mono">{score.toFixed(3)}</span>
      </div>
      <div className="relative h-1.5 bg-slate-700 rounded-full overflow-hidden">
        <div className="absolute left-1/2 top-0 h-full w-px bg-slate-500" />
        <div
          className={`absolute h-full rounded-full ${color}`}
          style={{
            left: score >= 0 ? '50%' : `${pct}%`,
            width: `${Math.abs(score) * 50}%`,
          }}
        />
      </div>
    </div>
  );
}

export default function LiveTradingPage() {
  const [symbols, setSymbols] = useState('AAPL');
  const [timeframe, setTimeframe] = useState('1h');
  const [streamStatus, setStreamStatus] = useState<StreamStatusResponse | null>(null);
  const [indicators, setIndicators] = useState<IndicatorSnapshotResponse | null>(null);
  const [signal, setSignal] = useState<TradingSignalItem | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    liveApi.getStatus().then(setStreamStatus).catch(() => {});
    return () => { if (pollRef.current) clearInterval(pollRef.current); };
  }, []);

  const startStream = async () => {
    setLoading(true);
    setError(null);
    try {
      const symbolList = symbols.split(',').map((s) => s.trim().toUpperCase()).filter(Boolean);
      const status = await liveApi.startStream({ symbols: symbolList });
      setStreamStatus(status);
      startPolling(symbolList[0]);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setLoading(false);
    }
  };

  const stopStream = async () => {
    if (pollRef.current) clearInterval(pollRef.current);
    try {
      const status = await liveApi.stopStream();
      setStreamStatus(status);
      setIndicators(null);
      setSignal(null);
    } catch (err) {
      setError((err as Error).message);
    }
  };

  const startPolling = (sym: string) => {
    if (pollRef.current) clearInterval(pollRef.current);
    pollRef.current = setInterval(async () => {
      try {
        const ind = await liveApi.getIndicators(sym, timeframe);
        setIndicators(ind);
        const sig = await liveApi.getLatestSignal(sym);
        if ('id' in sig) setSignal(sig as TradingSignalItem);
      } catch { /* stream might not have data yet */ }
    }, 5000);
  };

  const fetchManual = async () => {
    const sym = (streamStatus?.subscribed_symbols?.[0] ?? symbols.split(',')[0]).toUpperCase();
    try {
      const ind = await liveApi.getIndicators(sym, timeframe);
      setIndicators(ind);
      const sig = await liveApi.getLatestSignal(sym);
      if ('id' in sig) setSignal(sig as TradingSignalItem);
    } catch (err) {
      setError((err as Error).message);
    }
  };

  const connected = streamStatus?.connected ?? false;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-100">Live Trading</h1>
        <p className="text-slate-400 text-sm mt-1">
          Real-time market data streaming, technical indicators, and aggregated trading signals.
        </p>
      </div>

      {error && <ErrorAlert message={error} />}

      {/* Stream controls */}
      <div className="card">
        <h2 className="text-slate-200 font-semibold mb-4">Stream Control</h2>
        <div className="flex flex-wrap gap-4 items-end">
          <div>
            <label className="metric-label block mb-1">Symbols (comma-separated)</label>
            <input
              type="text"
              className="bg-surface-900 border border-slate-600 rounded-lg px-3 py-2 text-sm text-slate-100 focus:outline-none focus:border-brand-500 w-48 uppercase"
              value={symbols}
              onChange={(e) => setSymbols(e.target.value)}
              disabled={connected}
            />
          </div>
          <div>
            <label className="metric-label block mb-1">Indicator Timeframe</label>
            <select
              className="bg-surface-900 border border-slate-600 rounded-lg px-3 py-2 text-sm text-slate-100 focus:outline-none focus:border-brand-500"
              value={timeframe}
              onChange={(e) => setTimeframe(e.target.value)}
            >
              {TIMEFRAMES.map((tf) => <option key={tf} value={tf}>{tf}</option>)}
            </select>
          </div>

          {!connected ? (
            <button onClick={startStream} disabled={loading} className="btn-primary disabled:opacity-50">
              {loading ? 'Connecting…' : 'Start Stream'}
            </button>
          ) : (
            <button onClick={stopStream} className="px-4 py-2 rounded-lg text-sm font-medium bg-red-500/20 text-red-400 border border-red-500/40 hover:bg-red-500/30">
              Stop Stream
            </button>
          )}

          <button onClick={fetchManual} className="px-4 py-2 rounded-lg text-sm font-medium bg-surface-800 text-slate-300 hover:bg-surface-700">
            Refresh Data
          </button>
        </div>

        {/* Status */}
        <div className="mt-4 flex flex-wrap items-center gap-4 text-xs">
          <span className="flex items-center gap-1.5">
            <span className={`h-2 w-2 rounded-full ${connected ? 'bg-green-500 animate-pulse' : 'bg-slate-600'}`} />
            <span className="text-slate-400">{connected ? 'Connected' : 'Disconnected'}</span>
          </span>
          {streamStatus?.subscribed_symbols && streamStatus.subscribed_symbols.length > 0 && (
            <span className="text-slate-500">
              Streaming: {streamStatus.subscribed_symbols.join(', ')}
            </span>
          )}
          {streamStatus?.last_tick_at && (
            <span className="text-slate-500">
              Last tick: {new Date(streamStatus.last_tick_at).toLocaleTimeString()}
            </span>
          )}
          {streamStatus?.error && (
            <span className="text-red-400 font-mono">
              Stream error: {streamStatus.error}
            </span>
          )}
        </div>
      </div>

      {loading && <Spinner label="Connecting to Alpaca WebSocket stream…" />}

      {/* Indicators panel */}
      {indicators && (
        <div className="card">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-slate-200 font-semibold">
              Technical Indicators — {indicators.symbol} ({indicators.timeframe})
            </h2>
            <span className="text-slate-400 font-mono text-lg">
              ${indicators.close_price.toFixed(2)}
            </span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="space-y-4">
              <IndicatorGauge label="RSI (14)" value={indicators.rsi} min={0} max={100} />
              <div className="flex justify-between text-xs text-slate-500">
                <span>Oversold (30)</span>
                <span>Overbought (70)</span>
              </div>
            </div>

            <div>
              <h4 className="text-slate-400 text-xs uppercase tracking-wide mb-2">VWAP</h4>
              <div className="flex items-baseline gap-2">
                <span className="text-slate-200 font-mono text-xl">
                  {indicators.vwap?.toFixed(2) ?? '—'}
                </span>
                {indicators.vwap && (
                  <span className={`text-xs font-semibold ${indicators.close_price > indicators.vwap ? 'text-green-400' : 'text-red-400'}`}>
                    {indicators.close_price > indicators.vwap ? 'Above' : 'Below'} VWAP
                  </span>
                )}
              </div>
            </div>

            <MACDDisplay
              macd={indicators.macd}
              signal={indicators.macd_signal}
              histogram={indicators.macd_histogram}
            />

            <BollingerDisplay
              upper={indicators.bb_upper}
              middle={indicators.bb_middle}
              lower={indicators.bb_lower}
              price={indicators.close_price}
              bbPct={indicators.bb_percent}
            />
          </div>
        </div>
      )}

      {/* Signal panel */}
      {signal && (
        <div className="card border border-slate-600">
          <h2 className="text-slate-200 font-semibold mb-4">Aggregated Signal</h2>
          <SignalBadge action={signal.action} confidence={signal.confidence} />

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mt-4">
            <SignalScoreBar label="Technical" score={signal.technical_score} />
            <SignalScoreBar label="Risk (MC)" score={signal.risk_score} />
            <SignalScoreBar label="AI Agent" score={signal.ai_score} />
          </div>

          {signal.reasoning && (
            <div className="mt-4 p-3 bg-surface-900 rounded-lg border border-slate-700">
              <span className="text-slate-500 text-xs uppercase tracking-wide">Reasoning</span>
              <p className="text-slate-300 text-xs mt-1 font-mono leading-relaxed">{signal.reasoning}</p>
            </div>
          )}

          <p className="text-slate-500 text-xs mt-2">
            Generated: {new Date(signal.created_at).toLocaleString()}
          </p>
        </div>
      )}

      {!indicators && !loading && (
        <div className="card text-center py-12">
          <p className="text-slate-500 text-sm">
            Start a stream to see live indicators and signals, or click "Refresh Data" to fetch stored data.
          </p>
        </div>
      )}
    </div>
  );
}
