import type { IndicatorSnapshotResponse, LiveStrategySignalItem, StrategySignalsResponse } from '../api/types';

// ── Indicator sub-components ─────────────────────────────────────────────────

function IndicatorGauge({ label, value, min, max, unit }: {
  label: string; value: number | null; min: number; max: number; unit?: string;
}) {
  const pct = value !== null ? Math.min(100, Math.max(0, ((value - min) / (max - min)) * 100)) : 0;
  const color = pct > 70 ? 'bg-red-500' : pct < 30 ? 'bg-green-500' : 'bg-yellow-500';
  return (
    <div className="space-y-1">
      <div className="flex justify-between text-xs">
        <span className="text-slate-400">{label}</span>
        <span className="text-slate-200 font-mono">{value !== null ? value.toFixed(2) : '—'}{unit ?? ''}</span>
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
          <p className={`font-mono text-sm font-semibold ${histColor}`}>{histogram?.toFixed(4) ?? '—'}</p>
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
        <div><span className="text-slate-500 text-xs">Upper</span><p className="text-red-400 font-mono text-sm">{upper?.toFixed(2) ?? '—'}</p></div>
        <div><span className="text-slate-500 text-xs">Middle</span><p className="text-slate-300 font-mono text-sm">{middle?.toFixed(2) ?? '—'}</p></div>
        <div><span className="text-slate-500 text-xs">Lower</span><p className="text-green-400 font-mono text-sm">{lower?.toFixed(2) ?? '—'}</p></div>
        <div><span className="text-slate-500 text-xs">%B</span><p className="text-slate-200 font-mono text-sm">{bbPct?.toFixed(2) ?? '—'}</p></div>
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

// ── Strategy signals panel ────────────────────────────────────────────────────

const SIGNAL_STYLES: Record<string, string> = {
  BUY:     'bg-green-500/20 text-green-400 border-green-500/40',
  SELL:    'bg-red-500/20 text-red-400 border-red-500/40',
  NEUTRAL: 'bg-slate-700/40 text-slate-400 border-slate-600/40',
};

function SignalBadge({ signal }: { signal: string }) {
  const s = SIGNAL_STYLES[signal] ?? SIGNAL_STYLES.NEUTRAL;
  return (
    <span className={`px-1.5 py-0.5 rounded text-xs font-semibold border ${s}`}>{signal}</span>
  );
}

function StrategySignalsPanel({ data }: { data: StrategySignalsResponse }) {
  const groups = data.strategies.reduce<Record<string, LiveStrategySignalItem[]>>((acc, s) => {
    (acc[s.group] ??= []).push(s);
    return acc;
  }, {});

  const buys = data.strategies.filter((s) => s.signal === 'BUY').length;
  const sells = data.strategies.filter((s) => s.signal === 'SELL').length;

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-4 text-xs">
        <span className="text-green-400 font-semibold">{buys} BUY</span>
        <span className="text-red-400 font-semibold">{sells} SELL</span>
        <span className="text-slate-500">{data.strategies.length - buys - sells} NEUTRAL</span>
        <span className="ml-auto text-slate-500">{data.bar_count} bars @ {data.timeframe}</span>
      </div>
      {Object.entries(groups).map(([group, items]) => (
        <div key={group}>
          <p className="text-slate-500 text-xs uppercase tracking-wide mb-1.5">{group}</p>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-1.5">
            {items.map((s) => (
              <div key={s.strategy} className="flex items-center justify-between bg-surface-900 rounded px-2 py-1">
                <span className="text-slate-300 text-xs truncate mr-2">{s.label}</span>
                <SignalBadge signal={s.signal} />
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}

// ── Indicators panel ──────────────────────────────────────────────────────────

function IndicatorsPanel({ indicators }: { indicators: IndicatorSnapshotResponse }) {
  if (indicators.close_price === 0) return null;
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
      <div className="space-y-4">
        <IndicatorGauge label="RSI (14)" value={indicators.rsi} min={0} max={100} />
        <div className="flex justify-between text-xs text-slate-500">
          <span>Oversold (30)</span><span>Overbought (70)</span>
        </div>
      </div>
      <div>
        <h4 className="text-slate-400 text-xs uppercase tracking-wide mb-2">VWAP</h4>
        <div className="flex items-baseline gap-2">
          <span className="text-slate-200 font-mono text-xl">{indicators.vwap?.toFixed(2) ?? '—'}</span>
          {indicators.vwap && (
            <span className={`text-xs font-semibold ${indicators.close_price > indicators.vwap ? 'text-green-400' : 'text-red-400'}`}>
              {indicators.close_price > indicators.vwap ? 'Above' : 'Below'} VWAP
            </span>
          )}
        </div>
      </div>
      <MACDDisplay macd={indicators.macd} signal={indicators.macd_signal} histogram={indicators.macd_histogram} />
      <BollingerDisplay
        upper={indicators.bb_upper} middle={indicators.bb_middle} lower={indicators.bb_lower}
        price={indicators.close_price} bbPct={indicators.bb_percent}
      />
    </div>
  );
}

// ── Main StreamCard ───────────────────────────────────────────────────────────

export interface StreamCardProps {
  symbol: string;
  indicators: IndicatorSnapshotResponse | null;
  strategySignals: StrategySignalsResponse | null;
  streamRunning: boolean;
  onRemove: (symbol: string) => void;
}

function strategySignalsEmptyMessage(
  streamRunning: boolean,
  strategySignals: StrategySignalsResponse | null,
): string {
  if (!streamRunning) return 'Click "Start Live Stream" to accumulate real-time bars for strategy signals.';
  if (!strategySignals) return 'Waiting for live bars…';
  return `Accumulating bars (${strategySignals.bar_count}/30 needed) — strategy signals appear once enough data is available.`;
}

export default function LiveStreamCard({ symbol, indicators, strategySignals, streamRunning, onRemove }: StreamCardProps) {
  const hasSignals = strategySignals !== null && strategySignals.strategies.length > 0;

  return (
    <div className="card space-y-5">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <span className="text-lg font-bold text-slate-100">{symbol}</span>
          {indicators && indicators.close_price > 0 && (
            <span className="text-slate-400 font-mono text-lg">${indicators.close_price.toFixed(2)}</span>
          )}
          {streamRunning && (
            <span className="flex items-center gap-1 text-xs text-green-400">
              <span className="h-1.5 w-1.5 rounded-full bg-green-400 animate-pulse" />
              Live
            </span>
          )}
        </div>
        <button
          onClick={() => onRemove(symbol)}
          className="text-slate-500 hover:text-red-400 transition-colors text-sm px-2 py-1 rounded hover:bg-red-500/10"
          aria-label={`Remove ${symbol} stream`}
        >
          ✕ Remove
        </button>
      </div>

      {/* Technical Indicators */}
      {indicators && indicators.close_price > 0 ? (
        <div>
          <h3 className="text-slate-400 text-xs uppercase tracking-wide mb-3">
            Technical Indicators ({indicators.timeframe})
          </h3>
          <IndicatorsPanel indicators={indicators} />
        </div>
      ) : (
        <p className="text-slate-500 text-xs">Fetching stored indicator data…</p>
      )}

      {/* Strategy Signals */}
      <div>
        <h3 className="text-slate-400 text-xs uppercase tracking-wide mb-3">
          Strategy Signals — 1h
        </h3>
        {hasSignals ? (
          <StrategySignalsPanel data={strategySignals!} />
        ) : (
          <p className="text-slate-500 text-xs italic">
            {strategySignalsEmptyMessage(streamRunning, strategySignals)}
          </p>
        )}
      </div>
    </div>
  );
}
