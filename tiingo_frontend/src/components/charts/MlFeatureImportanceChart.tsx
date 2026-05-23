import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import type { MlFeatureImportanceItem } from '../../api/mlBacktestTypes';
import { topFeatureImportance } from '../../utils/mlBacktestEvaluation';

interface MlFeatureImportanceChartProps {
  items: MlFeatureImportanceItem[];
  height?: number;
}

export default function MlFeatureImportanceChart({
  items,
  height = 280,
}: MlFeatureImportanceChartProps) {
  const data = topFeatureImportance(items).map((item) => ({
    name: item.name,
    value: item.value,
    valuePct: item.value * 100,
  }));

  if (data.length === 0) {
    return (
      <div className="flex items-center justify-center h-40 text-slate-500 text-xs border border-slate-800 rounded-lg bg-surface-900">
        Feature importance is available for tree-based models only.
      </div>
    );
  }

  return (
    <div className="border border-slate-800 rounded-lg bg-surface-900 p-3">
      <p className="text-xs font-medium text-slate-300 mb-2">Feature importance</p>
      <ResponsiveContainer width="100%" height={height}>
        <BarChart data={data} layout="vertical" margin={{ top: 4, right: 8, left: 8, bottom: 4 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" horizontal={false} />
          <XAxis type="number" tick={{ fill: '#64748b', fontSize: 10 }} />
          <YAxis
            type="category"
            dataKey="name"
            width={120}
            tick={{ fill: '#94a3b8', fontSize: 10 }}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: '#1e293b',
              border: '1px solid #334155',
              borderRadius: '8px',
            }}
            formatter={(value: number) => [value.toFixed(4), 'Importance']}
          />
          <Bar dataKey="value" fill="#6366f1" radius={[0, 4, 4, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
