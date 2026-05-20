import {
  ComposedChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
  ReferenceLine,
} from 'recharts';
import type { McBacktestSignalPoint } from '../api/types';

interface McProbPositiveChartProps {
  signalLog: McBacktestSignalPoint[];
  buyThreshold: number;
  sellThreshold: number;
  syncId?: string;
}

interface ChartPoint {
  time: string;
  probPct: number | null;
  probTrendPct: number | null;
  probReversionPct: number | null;
  regimeWeightPct: number | null;
}

export function buildChartData(signalLog: McBacktestSignalPoint[]): ChartPoint[] {
  return signalLog.map((entry) => ({
    time: entry.time,
    probPct: entry.prob_positive != null ? entry.prob_positive * 100 : null,
    probTrendPct: entry.prob_trend != null ? entry.prob_trend * 100 : null,
    probReversionPct: entry.prob_reversion != null ? entry.prob_reversion * 100 : null,
    regimeWeightPct: entry.regime_weight != null ? entry.regime_weight * 100 : null,
  }));
}

function hasProbData(data: ChartPoint[]): boolean {
  return data.some((p) => p.probPct != null);
}

function roundDownToDozen(value: number): number {
  return Math.floor(value / 10) * 10;
}

function roundUpToDozen(value: number): number {
  return Math.ceil(value / 10) * 10;
}

export function computeYDomain(
  chartData: ChartPoint[],
  buyPct: number,
  sellPct: number,
): [number, number] {
  const probValues = chartData
    .map((p) => p.probPct)
    .filter((v): v is number => v != null);
  const allValues = [...probValues, buyPct, sellPct];
  const rawMin = Math.min(...allValues);
  const rawMax = Math.max(...allValues);

  let yMin = roundDownToDozen(rawMin);
  let yMax = roundUpToDozen(rawMax);

  if (yMax - yMin < 10) {
    yMin = roundDownToDozen(rawMin - 5);
    yMax = roundUpToDozen(rawMax + 5);
  }

  yMin = Math.max(0, yMin);
  yMax = Math.min(100, yMax);
  if (yMax <= yMin) {
    yMax = Math.min(100, yMin + 10);
  }

  return [yMin, yMax];
}

function ProbTooltip({
  active,
  payload,
  label,
}: {
  active?: boolean;
  payload?: { payload: ChartPoint }[];
  label?: string;
}) {
  if (!active || !payload?.length) return null;
  const point = payload[0].payload;
  return (
    <div
      style={{
        background: '#1e293b',
        border: '1px solid #334155',
        borderRadius: 8,
        fontSize: 11,
        padding: '6px 8px',
      }}
    >
      <div style={{ color: '#94a3b8', marginBottom: 4 }}>{String(label).substring(0, 10)}</div>
      <div style={{ color: '#c4b5fd' }}>
        Prob: {point.probPct != null ? `${point.probPct.toFixed(1)}%` : '—'}
      </div>
      {point.probTrendPct != null && (
        <div style={{ color: '#86efac' }}>Trend: {point.probTrendPct.toFixed(1)}%</div>
      )}
      {point.probReversionPct != null && (
        <div style={{ color: '#fca5a5' }}>Reversion: {point.probReversionPct.toFixed(1)}%</div>
      )}
      {point.regimeWeightPct != null && (
        <div style={{ color: '#94a3b8' }}>Trend weight: {point.regimeWeightPct.toFixed(0)}%</div>
      )}
    </div>
  );
}

function renderLegend(buyPct: number, sellPct: number) {
  return (
    <div className="flex items-center gap-4 justify-end mb-2 text-xs flex-wrap">
      <span className="flex items-center gap-1">
        <span className="inline-block w-3 h-0.5 bg-purple-400" />
        <span className="text-slate-400">Prob. Positive Return</span>
      </span>
      <span className="flex items-center gap-1">
        <span className="inline-block w-3 h-0.5 bg-green-500" style={{ borderTop: '2px dashed #22c55e', height: 0 }} />
        <span className="text-slate-400">Buy {buyPct}%</span>
      </span>
      <span className="flex items-center gap-1">
        <span className="inline-block w-3 h-0.5 bg-red-500" style={{ borderTop: '2px dashed #ef4444', height: 0 }} />
        <span className="text-slate-400">Sell {sellPct}%</span>
      </span>
    </div>
  );
}

export default function McProbPositiveChart({
  signalLog,
  buyThreshold,
  sellThreshold,
  syncId,
}: McProbPositiveChartProps) {
  const chartData = buildChartData(signalLog);
  if (chartData.length === 0 || !hasProbData(chartData)) return null;

  const buyPct = Math.round(buyThreshold * 100);
  const sellPct = Math.round(sellThreshold * 100);
  const [yMin, yMax] = computeYDomain(chartData, buyPct, sellPct);

  return (
    <div className="border-t border-slate-700 pt-4 mt-2">
      <h3 className="text-slate-200 font-semibold text-sm mb-1">Prob. Positive Return</h3>
      {renderLegend(buyPct, sellPct)}
      <ResponsiveContainer width="100%" height={160}>
        <ComposedChart data={chartData} margin={{ top: 4, right: 10, bottom: 4, left: 0 }} syncId={syncId}>
          <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
          <XAxis
            dataKey="time"
            stroke="#475569"
            tick={{ fontSize: 8, fill: '#64748b' }}
            tickFormatter={(v: string) => v.substring(0, 10)}
          />
          <YAxis
            stroke="#475569"
            tick={{ fontSize: 8, fill: '#64748b' }}
            domain={[yMin, yMax]}
            tickFormatter={(v: number) => `${v}`}
            width={38}
          />
          <Tooltip content={<ProbTooltip />} />
          <ReferenceLine
            y={buyPct}
            stroke="#22c55e"
            strokeDasharray="4 2"
            label={{ value: `Buy ${buyPct}%`, fill: '#22c55e', fontSize: 8, position: 'insideTopRight' }}
          />
          <ReferenceLine
            y={sellPct}
            stroke="#ef4444"
            strokeDasharray="4 2"
            label={{ value: `Sell ${sellPct}%`, fill: '#ef4444', fontSize: 8, position: 'insideTopRight' }}
          />
          <Line
            type="monotone"
            dataKey="probPct"
            stroke="#a78bfa"
            strokeWidth={1.5}
            dot={false}
            isAnimationActive={false}
            connectNulls={false}
          />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}
