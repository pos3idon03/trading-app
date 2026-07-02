import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import type { MlPartialDependenceCurve } from '../../api/mlBacktestTypes';

interface MlPartialDependenceChartProps {
  curves: MlPartialDependenceCurve[];
}

export default function MlPartialDependenceChart({ curves }: MlPartialDependenceChartProps) {
  if (!curves.length) {
    return <p className="text-sm text-slate-500">No partial dependence curves for this run.</p>;
  }

  return (
    <div className="space-y-4">
      {curves.map((curve) => {
        const data = curve.grid.map((value, index) => ({
          value,
          p_up: curve.p_up[index] ?? 0,
        }));
        return (
          <div key={curve.feature} className="space-y-1">
            <p className="text-xs font-medium text-slate-400">{curve.feature}</p>
            <div className="h-40">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={data}>
                  <CartesianGrid stroke="#334155" strokeDasharray="3 3" />
                  <XAxis dataKey="value" tick={{ fill: '#94a3b8', fontSize: 10 }} />
                  <YAxis
                    domain={[0, 1]}
                    tick={{ fill: '#94a3b8', fontSize: 10 }}
                    tickFormatter={(value) => `${(Number(value) * 100).toFixed(0)}%`}
                  />
                  <Tooltip
                    contentStyle={{ background: '#1e293b', border: '1px solid #334155' }}
                    formatter={(value: number) => [`${(value * 100).toFixed(1)}%`, 'P(up)']}
                  />
                  <Line type="monotone" dataKey="p_up" stroke="#38bdf8" dot={false} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>
        );
      })}
    </div>
  );
}
