import {
  ComposedChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
  Legend,
} from 'recharts';
import type { AttachedAlgoSignal, ComboStrategySignal, SignalPoint } from '../api/types';

interface ComboSignalTimelineProps {
  strategies: ComboStrategySignal[];
  syncId?: string;
  /** Shorter chart for execution monitor cards */
  compact?: boolean;
  /** Use time-of-day x-axis labels for intraday timeframes */
  intraday?: boolean;
  /** Hide section title and description (nested per-strategy charts) */
  hideHeader?: boolean;
}

const INTRADAY_TIMEFRAMES = new Set(['5m', '15m', '30m', '1h', '3h', '4h']);

export function isIntradayTimeframe(tf: string): boolean {
  return INTRADAY_TIMEFRAMES.has(tf);
}

/** Convert live monitor signals into combo chart input shape. */
export function attachedSignalsToTimelineStrategies(
  signals: AttachedAlgoSignal[],
): ComboStrategySignal[] {
  return signals
    .filter((s) => s.signalTimeline && s.signalTimeline.length > 0)
    .map((s) => ({
      strategy_name: s.strategy,
      trade_log: [],
      indicator_series: [],
      equity_curve: [],
      signal_timeline: s.signalTimeline as SignalPoint[],
    }));
}

const STRATEGY_COLORS = [
  '#60a5fa',
  '#34d399',
  '#f59e0b',
  '#f87171',
  '#a78bfa',
  '#fb923c',
  '#38bdf8',
  '#e879f9',
];

const SIGNAL_LABELS: Record<string, string> = {
  ma_crossover: 'MA Cross',
  sma_cross: 'SMA Cross',
  ema_cross: 'EMA Cross',
  sma_break: 'SMA Break',
  macd: 'MACD',
  rsi: 'RSI',
  lrsi: 'LRSI',
  aroon: 'Aroon',
  stoch_rsi: 'StochRSI',
  momentum_rotation: 'Momentum',
  new_high_low: 'New High/Low',
  atr_trailing_stop: 'ATR Stop',
  vwap_cross: 'VWAP',
  grid_trading: 'Grid',
  wedge_compression: 'Wedge',
  mean_reversion: 'Mean Rev',
  mean_reversion_trend: 'MR Trend',
  mean_reversion_range: 'MR Range',
  reverting_market: 'Reverting',
  breakout: 'Breakout',
  range_breakout: 'Range BO',
  trend_pullback: 'Trend PB',
  vrp_harvest: 'VRP',
  orb: 'ORB',
  gap_fade: 'Gap Fade',
  seasonal: 'Seasonal',
};

function strategyLabel(name: string): string {
  return SIGNAL_LABELS[name] ?? name;
}

function normalizeSignal(signal: string): 'Buy' | 'Neutral' | 'Sell' {
  const s = signal.toUpperCase();
  if (s === 'BUY') return 'Buy';
  if (s === 'NEUTRAL' || s === 'HOLD') return 'Neutral';
  return 'Sell';
}

function signalToValue(signal: string): number {
  const norm = normalizeSignal(signal);
  if (norm === 'Buy') return 1;
  if (norm === 'Neutral') return 0.5;
  return 0;
}

function valueToSignalLabel(v: number): string {
  if (v === 1) return 'Buy';
  if (v === 0.5) return 'Neutral';
  return 'Sell';
}

function signalClass(v: number): string {
  if (v === 1) return 'text-emerald-400';
  if (v === 0.5) return 'text-amber-400';
  return 'text-red-400';
}

interface TimelinePoint {
  time: string;
  [strategyKey: string]: number | string;
}

function buildTimelineData(strategies: ComboStrategySignal[]): TimelinePoint[] {
  if (strategies.length === 0) return [];

  const timeMap = new Map<string, TimelinePoint>();

  strategies.forEach((strategy) => {
    strategy.signal_timeline.forEach(({ time, signal }) => {
      if (!timeMap.has(time)) {
        timeMap.set(time, { time });
      }
      timeMap.get(time)![strategy.strategy_name] = signalToValue(signal);
    });
  });

  return Array.from(timeMap.values()).sort((a, b) => a.time.localeCompare(b.time));
}

function formatXTick(value: string, intraday: boolean): string {
  if (!value) return '';
  const d = new Date(value);
  if (isNaN(d.getTime())) return value;
  if (intraday) {
    return d.toLocaleString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: 'numeric',
      minute: '2-digit',
    });
  }
  return d.toLocaleDateString('en-US', { month: 'short', year: '2-digit' });
}

interface CustomTooltipProps {
  active?: boolean;
  payload?: { name: string; value: number; color: string }[];
  label?: string;
}

function CustomTooltip({ active, payload, label }: CustomTooltipProps) {
  if (!active || !payload || !label) return null;
  return (
    <div className="bg-slate-800 border border-slate-600 rounded-lg p-3 shadow-lg text-xs">
      <p className="text-slate-300 font-medium mb-2">{label}</p>
      {payload.map((entry) => {
        const name = strategyLabel(entry.name);
        const sigLabel = valueToSignalLabel(entry.value);
        const cls = signalClass(entry.value);
        return (
          <div key={entry.name} className="flex items-center gap-2 mb-1">
            <span className="w-2 h-2 rounded-full flex-shrink-0" style={{ backgroundColor: entry.color }} />
            <span className="text-slate-400">{name}:</span>
            <span className={`font-semibold ${cls}`}>{sigLabel}</span>
          </div>
        );
      })}
    </div>
  );
}

function getLatestSignal(point: TimelinePoint, strategyName: string): string {
  const v = point[strategyName] as number;
  return valueToSignalLabel(v);
}

function SignalAgreementBanner({
  data,
  strategies,
}: {
  data: TimelinePoint[];
  strategies: ComboStrategySignal[];
}) {
  if (data.length === 0 || strategies.length < 2) return null;

  const latestPoint = data[data.length - 1];
  const signals = strategies.map((s) => getLatestSignal(latestPoint, s.strategy_name));
  const allBuy = signals.every((s) => s === 'Buy');
  const allSell = signals.every((s) => s === 'Sell');
  const allNeutral = signals.every((s) => s === 'Neutral');

  if (!allBuy && !allSell && !allNeutral) return null;

  const bannerClass = allBuy
    ? 'bg-emerald-500/10 border border-emerald-500/30 text-emerald-400'
    : allSell
    ? 'bg-red-500/10 border border-red-500/30 text-red-400'
    : 'bg-amber-500/10 border border-amber-500/30 text-amber-400';

  const bannerLabel = allBuy
    ? 'All strategies agree: Buy'
    : allSell
    ? 'All strategies agree: Sell'
    : 'All strategies are Neutral';

  return (
    <div className={`rounded-lg px-4 py-2 text-xs font-semibold mb-3 ${bannerClass}`}>
      {bannerLabel}
    </div>
  );
}

export function ComboSignalTimeline({
  strategies,
  syncId,
  compact = false,
  intraday = false,
  hideHeader = false,
}: ComboSignalTimelineProps) {
  if (strategies.length === 0) return null;

  const data = buildTimelineData(strategies);
  const chartHeight = compact ? 120 : 180;

  return (
    <div className={hideHeader ? '' : compact ? 'mt-2' : 'mt-6'}>
      {!hideHeader && (
        <>
          <h3 className="text-sm font-semibold text-slate-300 mb-1">Signal Agreement Timeline</h3>
          <p className="text-xs text-slate-500 mb-3">
            Per-bar stance from each indicator (Buy / Neutral / Sell). Unanimous combo mode requires every leg to match, not a mix with Neutral.
          </p>
        </>
      )}
      <SignalAgreementBanner data={data} strategies={strategies} />
      <div className={`bg-slate-800/50 rounded-lg border border-slate-700 ${compact ? 'p-2' : 'p-4'}`}>
        <ResponsiveContainer width="100%" height={chartHeight}>
          <ComposedChart data={data} margin={{ top: 8, right: 16, left: 0, bottom: 4 }} syncId={syncId}>
            <CartesianGrid strokeDasharray="3 3" stroke="#334155" vertical={false} />
            <XAxis
              dataKey="time"
              tickFormatter={(v) => formatXTick(v, intraday)}
              tick={{ fill: '#94a3b8', fontSize: 10 }}
              axisLine={{ stroke: '#475569' }}
              tickLine={false}
              interval="preserveStartEnd"
            />
            <YAxis
              domain={[-0.15, 1.15]}
              ticks={[0, 0.5, 1]}
              tickFormatter={(v: number) => {
                if (v === 1) return 'Buy';
                if (v === 0.5) return 'Neutral';
                return 'Sell';
              }}
              tick={{ fill: '#94a3b8', fontSize: 10 }}
              axisLine={false}
              tickLine={false}
              width={44}
            />
            <Tooltip content={<CustomTooltip />} />
            <Legend
              formatter={(value: string) => (
                <span className="text-xs text-slate-400">{strategyLabel(value)}</span>
              )}
            />
            {strategies.map((strategy, idx) => (
              <Line
                key={strategy.strategy_name}
                type="stepAfter"
                dataKey={strategy.strategy_name}
                name={strategy.strategy_name}
                stroke={STRATEGY_COLORS[idx % STRATEGY_COLORS.length]}
                strokeWidth={2}
                dot={false}
                isAnimationActive={false}
              />
            ))}
          </ComposedChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
