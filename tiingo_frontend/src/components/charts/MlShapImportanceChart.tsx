import { useMemo } from 'react';
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
import type { MlShapImportanceItem } from '../../api/mlBacktestTypes';

const CLASS_COLORS: Record<string, string> = {
  '0': '#a3a366',
  '1': '#60a5fa',
  '2': '#f472b6',
};

interface MlShapImportanceChartProps {
  items: MlShapImportanceItem[];
  topN?: number;
}

export default function MlShapImportanceChart({ items, topN = 12 }: MlShapImportanceChartProps) {
  const chartData = useMemo(() => {
    const byFeature: Record<string, Record<string, number | string>> = {};
    for (const item of items) {
      if (!byFeature[item.feature]) {
        byFeature[item.feature] = { feature: item.feature };
      }
      byFeature[item.feature][`class_${item.class_label}`] = item.mean_abs_shap;
    }
    return Object.values(byFeature)
      .map((row) => ({
        ...row,
        total: ['0', '1', '2'].reduce(
          (sum, cls) => sum + Number(row[`class_${cls}`] ?? 0),
          0,
        ),
      }))
      .sort((a, b) => Number(b.total) - Number(a.total))
      .slice(0, topN);
  }, [items, topN]);

  if (!chartData.length) {
    return <p className="text-sm text-slate-500">No SHAP importance data for this run.</p>;
  }

  return (
    <div className="h-80 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={chartData} layout="vertical" margin={{ left: 120 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
          <XAxis type="number" tick={{ fill: '#94a3b8', fontSize: 11 }} />
          <YAxis type="category" dataKey="feature" width={110} tick={{ fill: '#cbd5e1', fontSize: 10 }} />
          <Tooltip contentStyle={{ background: '#0f172a', border: '1px solid #334155' }} />
          <Legend />
          {['0', '1', '2'].map((cls) => (
            <Bar
              key={cls}
              dataKey={`class_${cls}`}
              name={cls === '0' ? 'Ranging' : cls === '1' ? 'Sell' : 'Buy'}
              stackId="shap"
              fill={CLASS_COLORS[cls]}
            />
          ))}
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
