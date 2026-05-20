import type { ReactNode } from 'react';
import {
  ComposedChart,
  Area,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
  ReferenceDot,
} from 'recharts';
import type { McBacktestExecutionEvent, TradeRecord } from '../api/types';

interface BacktestEquityCurveProps {
  data: { time: string; value: number }[];
  gradientId: string;
  tradeLog?: TradeRecord[];
  executionLog?: McBacktestExecutionEvent[];
  buyHoldData?: { time: string; value: number }[];
  compact?: boolean;
  bare?: boolean;
  syncId?: string;
}

interface ChartPoint {
  time: string;
  value: number | null;
  buyHold: number | null;
}

function buildChartData(
  equityCurve: { time: string; value: number }[],
  buyHoldData: { time: string; value: number }[] | undefined,
): ChartPoint[] {
  const buyHoldMap = new Map<string, number>();
  buyHoldData?.forEach(({ time, value }) => buyHoldMap.set(time, value));

  return equityCurve.map(({ time, value }) => ({
    time,
    value,
    buyHold: buyHoldMap.get(time) ?? null,
  }));
}

/** Round equity Y-axis to nearest $100 based on strategy + buy-and-hold values. */
export function computeEquityYDomain(values: number[]): [number, number] {
  const numeric = values.filter((v) => Number.isFinite(v));
  if (numeric.length === 0) return [0, 100];

  const rawMin = Math.min(...numeric);
  const rawMax = Math.max(...numeric);
  let yMin = Math.floor(rawMin / 100) * 100;
  let yMax = Math.ceil(rawMax / 100) * 100;

  if (yMax === yMin) {
    yMin -= 100;
    yMax += 100;
  }

  return [yMin, yMax];
}

function collectEquityValues(
  chartData: ChartPoint[],
): number[] {
  const values: number[] = [];
  for (const point of chartData) {
    if (point.value != null) values.push(point.value);
    if (point.buyHold != null) values.push(point.buyHold);
  }
  return values;
}

function dateKeyFromTimestamp(ts: string): string {
  if (!ts || ts.length < 10) return '';
  return ts.substring(0, 10);
}

function findEquityBarForTradeTime(
  equityCurve: { time: string; value: number }[],
  tradeTimestamp: string,
  equityFallback?: number,
): { time: string; value: number } | undefined {
  const exact = equityCurve.find((row) => row.time === tradeTimestamp);
  if (exact) return exact;

  const target = dateKeyFromTimestamp(tradeTimestamp);
  if (!target) return undefined;
  const byDate = equityCurve.find((row) => dateKeyFromTimestamp(row.time) === target);
  if (byDate) return byDate;

  if (equityFallback != null) {
    return { time: tradeTimestamp, value: equityFallback };
  }
  return undefined;
}

interface BuyMarkerProps {
  cx?: number;
  cy?: number;
}

function BuyMarker({ cx = 0, cy = 0 }: BuyMarkerProps) {
  const size = 7;
  const points = `${cx},${cy - size} ${cx - size},${cy + size * 0.5} ${cx + size},${cy + size * 0.5}`;
  return <polygon points={points} fill="#22c55e" stroke="#15803d" strokeWidth={1} />;
}

interface SellMarkerProps {
  cx?: number;
  cy?: number;
}

function SellMarker({ cx = 0, cy = 0 }: SellMarkerProps) {
  const size = 7;
  const points = `${cx},${cy + size} ${cx - size},${cy - size * 0.5} ${cx + size},${cy - size * 0.5}`;
  return <polygon points={points} fill="#ef4444" stroke="#b91c1c" strokeWidth={1} />;
}

function renderLegend() {
  return (
    <div className="flex items-center gap-4 justify-end mt-1 mb-2 text-xs">
      <span className="flex items-center gap-1">
        <span className="inline-block w-3 h-0.5 bg-green-500" />
        <span className="text-slate-400">Strategy</span>
      </span>
      <span className="flex items-center gap-1">
        <span className="inline-block w-3 h-0.5 bg-purple-500" style={{ borderTop: '2px dashed #a855f7', display: 'inline-block', height: 0 }} />
        <span className="text-slate-400">Buy &amp; Hold</span>
      </span>
      <span className="flex items-center gap-1">
        <svg width="10" height="10"><polygon points="5,0 0,10 10,10" fill="#22c55e" /></svg>
        <span className="text-slate-400">Buy</span>
      </span>
      <span className="flex items-center gap-1">
        <svg width="10" height="10"><polygon points="5,10 0,0 10,0" fill="#ef4444" /></svg>
        <span className="text-slate-400">Sell</span>
      </span>
    </div>
  );
}

function renderExecutionMarkers(
  data: { time: string; value: number }[],
  executionLog: McBacktestExecutionEvent[],
): ReactNode[] {
  return executionLog.flatMap((event, i) => {
    const bar = findEquityBarForTradeTime(data, event.time, event.equity);
    if (!bar) return [];
    const Marker = event.side === 'buy' ? BuyMarker : SellMarker;
    return [
      <ReferenceDot
        key={`exec-${event.side}-${i}`}
        x={bar.time}
        y={bar.value}
        shape={<Marker />}
      />,
    ];
  });
}

function renderTradeLogMarkers(
  data: { time: string; value: number }[],
  tradeLog: TradeRecord[],
): ReactNode[] {
  return tradeLog.flatMap((trade, i) => {
    const entryBar = findEquityBarForTradeTime(data, trade.entry_time);
    const exitTs = trade.exit_time?.trim();
    const exitBar =
      exitTs && exitTs.length >= 10
        ? findEquityBarForTradeTime(data, exitTs)
        : undefined;
    const nodes: ReactNode[] = [];
    if (entryBar) {
      nodes.push(
        <ReferenceDot
          key={`buy-${i}`}
          x={entryBar.time}
          y={entryBar.value}
          shape={<BuyMarker />}
        />,
      );
    }
    if (exitBar) {
      nodes.push(
        <ReferenceDot
          key={`sell-${i}`}
          x={exitBar.time}
          y={exitBar.value}
          shape={<SellMarker />}
        />,
      );
    }
    return nodes;
  });
}

export default function BacktestEquityCurve({
  data,
  gradientId,
  tradeLog,
  executionLog,
  buyHoldData,
  compact = false,
  bare = false,
  syncId,
}: BacktestEquityCurveProps) {
  const height = compact ? 200 : 320;
  const chartData = buildChartData(data, buyHoldData);
  const [yMin, yMax] = computeEquityYDomain(collectEquityValues(chartData));

  const hasBuyHold = (buyHoldData ?? []).length > 0;
  const hasExecutions = (executionLog ?? []).length > 0;
  const hasTrades = !hasExecutions && (tradeLog ?? []).length > 0;

  const chart = (
    <>
      {!compact && <h2 className="text-slate-200 font-semibold mb-2">Equity Curve</h2>}
      {renderLegend()}
      <ResponsiveContainer width="100%" height={height}>
        <ComposedChart data={chartData} margin={{ top: 5, right: 20, bottom: 5, left: 0 }} syncId={syncId}>
          <defs>
            <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%"  stopColor="#22c55e" stopOpacity={0.3} />
              <stop offset="95%" stopColor="#22c55e" stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
          <XAxis
            dataKey="time"
            stroke="#475569"
            tick={{ fontSize: 9, fill: '#64748b' }}
            tickFormatter={(v) => v.substring(0, 10)}
          />
          <YAxis
            stroke="#475569"
            tick={{ fontSize: 9, fill: '#64748b' }}
            domain={[yMin, yMax]}
            tickFormatter={(v) => `$${(v / 1000).toFixed(0)}k`}
          />
          <Tooltip
            contentStyle={{ background: '#1e293b', border: '1px solid #334155', borderRadius: 8 }}
            labelStyle={{ color: '#94a3b8' }}
            labelFormatter={(v: string) => v.substring(0, 10)}
            formatter={(v: number, name: string) => {
              if (name === 'value') return [`$${v.toFixed(2)}`, 'Strategy'];
              if (name === 'buyHold') return [`$${v.toFixed(2)}`, 'Buy & Hold'];
              return [v, name];
            }}
          />
          <Area
            type="monotone"
            dataKey="value"
            stroke="#22c55e"
            strokeWidth={2}
            fill={`url(#${gradientId})`}
            dot={false}
            isAnimationActive={false}
          />
          {hasBuyHold && (
            <Line
              type="monotone"
              dataKey="buyHold"
              stroke="#a855f7"
              strokeWidth={1.5}
              strokeDasharray="5 3"
              dot={false}
              isAnimationActive={false}
            />
          )}
          {hasExecutions && renderExecutionMarkers(data, executionLog!)}
          {hasTrades && renderTradeLogMarkers(data, tradeLog!)}
        </ComposedChart>
      </ResponsiveContainer>
    </>
  );

  if (bare) return chart;
  return <div className="card">{chart}</div>;
}
