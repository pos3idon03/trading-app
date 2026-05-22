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
import { buildEquityChartData } from '../../utils/backtestData';

interface BacktestEquityChartProps {
  strategy: BacktestEquityPoint[];
  benchmark: BacktestEquityPoint[];
}

export default function BacktestEquityChart({ strategy, benchmark }: BacktestEquityChartProps) {
  const data = buildEquityChartData(strategy, benchmark);

  if (!data.length) {
    return (
      <div className="flex items-center justify-center h-64 text-slate-500 text-sm border border-slate-800 rounded-lg bg-surface-900">
        No equity curve data available.
      </div>
    );
  }

  return (
    <div className="h-72 w-full border border-slate-800 rounded-lg bg-surface-900 p-4">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data}>
          <CartesianGrid stroke="#1e293b" strokeDasharray="3 3" />
          <XAxis dataKey="date" tick={{ fill: '#94a3b8', fontSize: 11 }} minTickGap={24} />
          <YAxis
            tick={{ fill: '#94a3b8', fontSize: 11 }}
            tickFormatter={(value) => `$${(value / 1000).toFixed(0)}k`}
          />
          <Tooltip
            contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', color: '#e2e8f0' }}
            formatter={(value: number) => [`$${value.toFixed(2)}`, '']}
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
  );
}
