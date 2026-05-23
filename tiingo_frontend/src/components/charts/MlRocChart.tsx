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
import type { MlRocCurve } from '../../api/mlBacktestTypes';
import { RANDOM_ROC_AUC, buildRocChartData } from '../../utils/mlRocChartData';

const CLASS_COLORS: Record<string, string> = {
  '0': '#94a3b8',
  '1': '#f87171',
  '2': '#34d399',
};

interface MlRocChartProps {
  curves: MlRocCurve[];
}

export default function MlRocChart({ curves }: MlRocChartProps) {
  if (!curves.length) {
    return (
      <p className="text-sm text-slate-500">No ROC curve data for this run.</p>
    );
  }

  const chartData = buildRocChartData(curves);

  return (
    <div className="h-72 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={chartData}>
          <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
          <XAxis
            type="number"
            dataKey="fpr"
            domain={[0, 1]}
            tick={{ fill: '#94a3b8', fontSize: 11 }}
            label={{ value: 'FPR', position: 'insideBottom', offset: -4, fill: '#94a3b8' }}
          />
          <YAxis
            domain={[0, 1]}
            tick={{ fill: '#94a3b8', fontSize: 11 }}
            label={{ value: 'TPR', angle: -90, position: 'insideLeft', fill: '#94a3b8' }}
          />
          <Tooltip contentStyle={{ background: '#0f172a', border: '1px solid #334155' }} />
          <Legend />
          {curves.map((curve) => (
            <Line
              key={curve.class_label}
              type="monotone"
              dataKey={`tpr_${curve.class_label}`}
              name={`Class ${curve.class_label} (AUC ${curve.auc?.toFixed(3) ?? '—'})`}
              stroke={CLASS_COLORS[curve.class_label] ?? '#60a5fa'}
              dot={false}
              strokeWidth={2}
            />
          ))}
          <Line
            type="monotone"
            dataKey="random"
            name={`Random (AUC ${RANDOM_ROC_AUC.toFixed(3)})`}
            stroke="#64748b"
            strokeDasharray="4 4"
            dot={false}
            strokeWidth={1.5}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
