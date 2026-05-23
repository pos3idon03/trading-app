import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import type { MlLabelSearchResult } from '../../api/mlBacktestTypes';

interface MlLabelModelCompareChartProps {
  results: MlLabelSearchResult[];
}

const COLORS = ['#38bdf8', '#34d399', '#f87171', '#a78bfa', '#fbbf24'];

export default function MlLabelModelCompareChart({ results }: MlLabelModelCompareChartProps) {
  if (!results.length) {
    return null;
  }

  const horizons = [...new Set(results.map((row) => row.label_horizon))].sort((a, b) => a - b);
  const models = [...new Set(results.map((row) => row.model_label ?? row.model_type ?? 'model'))];
  const chartData = horizons.map((horizon) => {
    const point: Record<string, number | string> = { horizon: `${horizon}` };
    for (const model of models) {
      const row = results.find(
        (item) =>
          (item.model_label ?? item.model_type) === model && item.label_horizon === horizon,
      );
      point[model] = row?.accuracy ?? 0;
    }
    return point;
  });

  return (
    <div className="h-64 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={chartData}>
          <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
          <XAxis dataKey="horizon" tick={{ fill: '#94a3b8', fontSize: 11 }} />
          <YAxis domain={[0, 1]} tick={{ fill: '#94a3b8', fontSize: 11 }} />
          <Tooltip
            formatter={(value: number) => [`${(value * 100).toFixed(1)}%`, 'OOS accuracy']}
            contentStyle={{ background: '#0f172a', border: '1px solid #334155' }}
          />
          <Legend />
          {models.map((model, index) => (
            <Bar
              key={model}
              dataKey={model}
              fill={COLORS[index % COLORS.length]}
              radius={[2, 2, 0, 0]}
            />
          ))}
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
