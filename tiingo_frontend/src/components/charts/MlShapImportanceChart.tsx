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
import type { MlLabelMode, MlShapImportanceItem } from '../../api/mlBacktestTypes';
import {
  SHAP_CLASS_COLORS,
  buildShapChartData,
  discoverShapClassLabels,
  getMlClassDisplayName,
} from '../../utils/mlShapChartData';

interface MlShapImportanceChartProps {
  items: MlShapImportanceItem[];
  labelMode?: MlLabelMode;
  topN?: number;
}

export default function MlShapImportanceChart({
  items,
  labelMode = 'binary',
  topN = 12,
}: MlShapImportanceChartProps) {
  const classLabels = useMemo(() => discoverShapClassLabels(items), [items]);
  const chartData = useMemo(
    () => buildShapChartData(items, classLabels, topN),
    [items, classLabels, topN],
  );

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
          {classLabels.map((classLabel) => (
            <Bar
              key={classLabel}
              dataKey={`class_${classLabel}`}
              name={getMlClassDisplayName(classLabel, labelMode)}
              stackId="shap"
              fill={SHAP_CLASS_COLORS[classLabel] ?? '#94a3b8'}
            />
          ))}
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
