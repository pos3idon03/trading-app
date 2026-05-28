import { useMemo, useState } from 'react';
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import type { BacktestEquityPoint } from '../../api/backtestTypes';
import {
  buildEquityChartData,
  buildIndexedEquityChartData,
  formatBacktestCurrency,
} from '../../utils/backtestData';

export type EquityChartViewMode = 'indexed' | 'absolute';

interface BacktestEquityChartProps {
  strategy: BacktestEquityPoint[];
  benchmark: BacktestEquityPoint[];
  initialCash?: number;
}

interface ChartRow {
  date: string;
  strategy?: number;
  benchmark?: number;
  strategyAbsolute?: number;
  benchmarkAbsolute?: number;
}

function buildChartRows(
  strategy: BacktestEquityPoint[],
  benchmark: BacktestEquityPoint[],
  mode: EquityChartViewMode,
): ChartRow[] {
  const absolute = buildEquityChartData(strategy, benchmark);
  if (mode === 'absolute') {
    return absolute.map((row) => ({
      date: row.date,
      strategy: row.strategy,
      benchmark: row.benchmark,
    }));
  }

  const indexed = buildIndexedEquityChartData(strategy, benchmark);
  return indexed.map((row, index) => ({
    date: row.date,
    strategy: row.strategy,
    benchmark: row.benchmark,
    strategyAbsolute: absolute[index]?.strategy,
    benchmarkAbsolute: absolute[index]?.benchmark,
  }));
}

export default function BacktestEquityChart({
  strategy,
  benchmark,
  initialCash: _initialCash,
}: BacktestEquityChartProps) {
  const [viewMode, setViewMode] = useState<EquityChartViewMode>('indexed');

  const data = useMemo(
    () => buildChartRows(strategy, benchmark, viewMode),
    [strategy, benchmark, viewMode],
  );

  if (!data.length) {
    return (
      <div className="flex items-center justify-center h-64 text-slate-500 text-sm border border-slate-800 rounded-lg bg-surface-900">
        No equity curve data available.
      </div>
    );
  }

  const isIndexed = viewMode === 'indexed';

  return (
    <div className="space-y-2">
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-xs text-slate-500">View:</span>
        <button
          type="button"
          onClick={() => setViewMode('indexed')}
          className={`px-2.5 py-1 rounded-md text-xs ${
            isIndexed
              ? 'bg-brand-700 text-white'
              : 'border border-slate-700 text-slate-400 hover:text-slate-200'
          }`}
        >
          Indexed
        </button>
        <button
          type="button"
          onClick={() => setViewMode('absolute')}
          className={`px-2.5 py-1 rounded-md text-xs ${
            !isIndexed
              ? 'bg-brand-700 text-white'
              : 'border border-slate-700 text-slate-400 hover:text-slate-200'
          }`}
        >
          Absolute $
        </button>
        {isIndexed && (
          <span className="text-xs text-slate-500">Both series start at 100</span>
        )}
      </div>
      <div className="h-72 w-full border border-slate-800 rounded-lg bg-surface-900 p-4">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data}>
            <CartesianGrid stroke="#1e293b" strokeDasharray="3 3" />
            <XAxis dataKey="date" tick={{ fill: '#94a3b8', fontSize: 11 }} minTickGap={24} />
            <YAxis
              tick={{ fill: '#94a3b8', fontSize: 11 }}
              tickFormatter={(value) =>
                isIndexed ? value.toFixed(0) : `$${(value / 1000).toFixed(0)}k`
              }
            />
            <Tooltip
              contentStyle={{
                backgroundColor: '#0f172a',
                borderColor: '#334155',
                color: '#e2e8f0',
              }}
              formatter={(value: number, name: string, item) => {
                const payload = item.payload as ChartRow;
                if (isIndexed) {
                  const absKey = name === 'Strategy' ? 'strategyAbsolute' : 'benchmarkAbsolute';
                  const absValue = payload[absKey];
                  const indexLabel = `${value.toFixed(2)} (index)`;
                  if (absValue != null) {
                    return [`${indexLabel} · ${formatBacktestCurrency(absValue)}`, name];
                  }
                  return [indexLabel, name];
                }
                return [formatBacktestCurrency(value), name];
              }}
            />
            <Legend />
            <Line
              type="monotone"
              dataKey="strategy"
              name="Strategy"
              stroke="#60a5fa"
              dot={false}
              strokeWidth={2}
            />
            <Line
              type="monotone"
              dataKey="benchmark"
              name="Buy & Hold"
              stroke="#94a3b8"
              dot={false}
              strokeWidth={2}
              strokeDasharray="4 4"
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
