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
import type { MlThresholdSearchResult } from '../../api/mlBacktestTypes';
import { formatMetricPercent } from '../../utils/mlBacktestConfig';

interface MlThresholdSweepChartProps {
  results: MlThresholdSearchResult[];
}

export default function MlThresholdSweepChart({ results }: MlThresholdSweepChartProps) {
  if (!results.length) {
    return <p className="text-sm text-slate-500">Run threshold sweep to compare buy/sell pairs.</p>;
  }

  const chartData = results.map((row, index) => ({
    key: `${row.buy_threshold ?? '—'}/${row.sell_threshold ?? '—'}`,
    index,
    buy: row.buy_threshold ?? 0,
    sell: row.sell_threshold ?? 0,
    f1: row.f1_macro ?? row.f1 ?? 0,
  }));

  return (
    <div className="h-64 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={chartData}>
          <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
          <XAxis
            dataKey="key"
            tick={{ fill: '#94a3b8', fontSize: 10 }}
            interval={0}
            angle={-25}
            textAnchor="end"
            height={60}
          />
          <YAxis domain={[0, 1]} tick={{ fill: '#94a3b8', fontSize: 11 }} />
          <Tooltip
            formatter={(value: number) => [formatMetricPercent(value), 'F1 macro']}
            contentStyle={{ background: '#0f172a', border: '1px solid #334155' }}
          />
          <Legend />
          <Line
            type="monotone"
            dataKey="f1"
            name="F1 macro"
            stroke="#38bdf8"
            strokeWidth={2}
            dot
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
