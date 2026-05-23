import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { buildOosAccuracyChartData } from '../../utils/mlBacktestEvaluation';

interface MlOosAccuracyChartProps {
  accuracies: number[];
  height?: number;
}

export default function MlOosAccuracyChart({
  accuracies,
  height = 200,
}: MlOosAccuracyChartProps) {
  const data = buildOosAccuracyChartData(accuracies);

  if (data.length === 0) {
    return (
      <div className="flex items-center justify-center h-40 text-slate-500 text-xs border border-slate-800 rounded-lg bg-surface-900">
        No per-window OOS accuracy (inference runs use a frozen model).
      </div>
    );
  }

  return (
    <div className="border border-slate-800 rounded-lg bg-surface-900 p-3">
      <p className="text-xs font-medium text-slate-300 mb-2">Per-window OOS accuracy</p>
      <ResponsiveContainer width="100%" height={height}>
        <BarChart data={data} margin={{ top: 4, right: 8, left: 4, bottom: 4 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
          <XAxis
            dataKey="window"
            tick={{ fill: '#64748b', fontSize: 10 }}
            label={{ value: 'Fold', position: 'insideBottom', offset: -2, fill: '#64748b' }}
          />
          <YAxis
            tick={{ fill: '#64748b', fontSize: 10 }}
            domain={[0, 100]}
            tickFormatter={(v: number) => `${v}%`}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: '#1e293b',
              border: '1px solid #334155',
              borderRadius: '8px',
            }}
            formatter={(value: number) => [`${value.toFixed(1)}%`, 'OOS accuracy']}
            labelFormatter={(label) => `Fold ${label}`}
          />
          <Bar dataKey="accuracyPct" fill="#22c55e" radius={[4, 4, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
