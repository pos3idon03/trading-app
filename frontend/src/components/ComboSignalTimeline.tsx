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
import type { ComboStrategySignal } from '../api/types';

interface ComboSignalTimelineProps {
  strategies: ComboStrategySignal[];
  syncId?: string;
}

const STRATEGY_COLORS = [
  '#60a5fa', // blue-400
  '#34d399', // emerald-400
  '#f59e0b', // amber-400
  '#f87171', // red-400
  '#a78bfa', // violet-400
  '#fb923c', // orange-400
  '#38bdf8', // sky-400
  '#e879f9', // fuchsia-400
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

// 3-state numeric mapping: Buy=1, Neutral=0.5, Sell=0
function signalToValue(signal: string): number {
  if (signal === 'Buy') return 1;
  if (signal === 'Neutral') return 0.5;
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

function formatXTick(value: string): string {
  if (!value) return '';
  const d = new Date(value);
  if (isNaN(d.getTime())) return value;
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

export function ComboSignalTimeline({ strategies, syncId }: ComboSignalTimelineProps) {
  if (strategies.length === 0) return null;

  const data = buildTimelineData(strategies);

  return (
    <div className="mt-6">
      <h3 className="text-sm font-semibold text-slate-300 mb-1">Signal Agreement Timeline</h3>
      <p className="text-xs text-slate-500 mb-3">
        Per-bar stance from each indicator (Buy / Neutral / Sell). Unanimous combo mode requires every leg to match, not a mix with Neutral.
      </p>
      <SignalAgreementBanner data={data} strategies={strategies} />
      <div className="bg-slate-800/50 rounded-lg border border-slate-700 p-4">
        <ResponsiveContainer width="100%" height={180}>
          <ComposedChart data={data} margin={{ top: 8, right: 16, left: 0, bottom: 4 }} syncId={syncId}>
            <CartesianGrid strokeDasharray="3 3" stroke="#334155" vertical={false} />
            <XAxis
              dataKey="time"
              tickFormatter={formatXTick}
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
