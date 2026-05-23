import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import type { MlMacroCoverage } from '../../api/mlBacktestTypes';

interface MlMacroCoverageChartProps {
  coverage: MlMacroCoverage[];
}

export default function MlMacroCoverageChart({ coverage }: MlMacroCoverageChartProps) {
  const data = coverage.map((item) => ({
    series_id: item.series_id,
    pct: item.release_date_pct,
  }));

  if (!data.length) {
    return <p className="text-sm text-slate-500">No macro coverage data.</p>;
  }

  return (
    <div className="h-56 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} layout="vertical" margin={{ left: 24 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
          <XAxis type="number" domain={[0, 100]} tick={{ fill: '#94a3b8', fontSize: 11 }} />
          <YAxis
            type="category"
            dataKey="series_id"
            width={80}
            tick={{ fill: '#94a3b8', fontSize: 11 }}
          />
          <Tooltip
            formatter={(value: number) => [`${value.toFixed(1)}%`, 'ALFRED coverage']}
            contentStyle={{ background: '#0f172a', border: '1px solid #334155' }}
          />
          <Bar dataKey="pct" fill="#a78bfa" radius={[0, 4, 4, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
